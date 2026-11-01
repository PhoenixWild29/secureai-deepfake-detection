"""Verify Clerk session JWTs and Pro/Team API keys.

AUTH_MODE=dev accepts the literal bearer ``dev``. A bearer that starts with
``sai_`` is an API key in every mode, including dev. Other bearers in dev
mode are rejected. Clerk verification is unchanged.
"""

from __future__ import annotations

import logging
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException, Request, status

from app.tenancy import WORKSPACE_MANAGER_ROLES, active_org
from secureai_shared.models import AuthContext
from secureai_shared.settings import Settings

logger = logging.getLogger("secureai.api.auth")


class AuthError(Exception):
    """The bearer token is missing, malformed, or not a valid Clerk session JWT."""


def verify_clerk_token(
    token: str,
    settings: Settings,
    fetch_jwks: Callable[[], dict[str, object]],
) -> AuthContext:
    """Validate signature, expiry, issuer, and subject. Do not log `token`."""

    try:
        header = jwt.get_unverified_header(token)
    except jwt.PyJWTError as exc:
        raise AuthError("malformed token") from exc
    if header.get("alg") != "RS256":
        raise AuthError("unexpected algorithm")

    try:
        jwks = fetch_jwks()
    except AuthError:
        raise
    except Exception as exc:
        raise AuthError("jwks unavailable") from exc

    if _key_list(jwks) is None:
        raise AuthError("jwks unavailable")
    kid = header.get("kid")
    match = _matching_key(jwks, kid)
    if match is None:
        refresh = getattr(fetch_jwks, "refresh", None)
        if callable(refresh):
            try:
                jwks = refresh()
            except AuthError:
                raise
            except Exception as exc:
                raise AuthError("jwks unavailable") from exc
            if _key_list(jwks) is None:
                raise AuthError("jwks unavailable")
            match = _matching_key(jwks, kid)
    if match is None:
        raise AuthError("signing key not found")

    try:
        signing = jwt.PyJWK.from_dict(match)
        claims = jwt.decode(
            token,
            signing.key,
            algorithms=["RS256"],
            issuer=settings.clerk_issuer,
            options={"require": ["exp", "sub", "iss"], "verify_aud": False},
        )
    except jwt.PyJWTError as exc:
        raise AuthError("invalid token") from exc

    # An empty allow-list skips azp. That is for local Clerk only.
    # Production sets CLERK_AUTHORIZED_PARTIES and this check rejects other azp values.
    parties = settings.clerk_authorized_parties
    if parties:
        azp = claims.get("azp")
        if not isinstance(azp, str) or azp not in parties:
            raise AuthError("authorized party rejected")

    subject = claims.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AuthError("missing subject")
    return AuthContext(subject=subject, mode="clerk")


def require_user(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> AuthContext:
    """Require a bearer credential. Anonymous callers are rejected in every mode."""

    settings: Settings = request.app.state.settings
    token = _bearer(authorization)
    if token.startswith("sai_"):
        user = _user_from_api_key(request, token)
        logger.debug("auth subject=%s mode=%s", user.subject, user.mode)
        return user
    if settings.auth_mode == "dev":
        if token != "dev":
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Authentication required",
            )
        user = AuthContext(subject=settings.dev_subject, mode="dev")
        logger.debug("auth subject=%s mode=%s", user.subject, user.mode)
        return user

    try:
        user = verify_clerk_token(token, settings, request.app.state.fetch_jwks)
    except AuthError as exc:
        if str(exc) == "jwks unavailable":
            logger.exception("clerk jwks fetch failed")
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Authentication service unavailable",
            ) from exc
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        ) from exc
    logger.debug("auth subject=%s mode=%s", user.subject, user.mode)
    return user


def require_session(
    user: Annotated[AuthContext, Depends(require_user)],
) -> AuthContext:
    """Clerk session or the dev bypass. An API key cannot mint or revoke keys."""

    if user.mode == "api_key":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Sign in to manage API keys.",
        )
    return user


def require_admin(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> AuthContext:
    """Allow only Clerk sessions, or the dev bearer, listed in ``ADMIN_USER_IDS``.

    An API key is never an admin credential, even when its subject is listed.
    An empty list allows nobody. A signed-in caller who fails this check gets
    the same 404 as an unknown path, so the response does not name the route
    or echo the allow list. Anonymous callers still get 401 from
    ``require_user``. In dev mode the subject is ``DEV_AUTH_SUBJECT``.
    """

    if user.mode == "api_key" or user.subject not in request.app.state.settings.admin_user_ids:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Not Found",
        )
    return user


def _user_from_api_key(request: Request, token: str) -> AuthContext:
    """Resolve a ``sai_`` bearer to the same subject the key was minted for.

    Unknown and revoked secrets are 401. The plan gate is the workspace
    plan when ``X-Org-Id`` is set or the key is bound to a workspace, and
    the personal plan otherwise. A free effective plan is 402. A workspace
    key whose minter is no longer an owner or admin is revoked and 401.
    The secret is not logged.
    """

    record = request.app.state.api_keys.authenticate(token)
    if record is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    org_id = record.org_id
    if org_id is not None:
        _reject_workspace_key_without_manager(request, record.id, record.user_id, org_id)
    user = AuthContext(
        subject=record.user_id,
        mode="api_key",
        api_key_id=record.id,
        api_key_org_id=org_id,
    )
    # Resolves X-Org-Id / the bound workspace and applies ensure_api_key_plan.
    active_org(request, user)
    request.app.state.api_keys.mark_used(record.id)
    return user


def _reject_workspace_key_without_manager(
    request: Request,
    key_id: str,
    user_id: str,
    org_id: str,
) -> None:
    """Revoke a workspace key whose minter is not currently a manager.

    The key is a credential for that workspace, not a personal token. It
    keeps working only while the minter is an owner or admin. Removal and
    demotion to member both revoke it on the next use, so promoting the
    minter later does not bring the same secret back. A current manager
    mints a replacement. The row stays so the revocation is visible.
    """

    role = request.app.state.billing.membership(org_id, user_id)
    if role in WORKSPACE_MANAGER_ROLES:
        return
    request.app.state.api_keys.revoke(key_id, user_id=user_id, org_id=org_id)
    logger.info(
        "api key revoked id=%s subject=%s org_id=%s reason=minter_not_manager",
        key_id,
        user_id,
        org_id,
    )
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required",
    )


def _key_list(jwks: object) -> list[object] | None:
    if isinstance(jwks, dict) and isinstance(jwks.get("keys"), list):
        return jwks["keys"]
    return None


def _matching_key(jwks: object, kid: object) -> dict[str, object] | None:
    if not isinstance(jwks, dict):
        return None
    keys = jwks.get("keys")
    if not isinstance(keys, list):
        return None
    for key in keys:
        if isinstance(key, dict) and kid and key.get("kid") == kid:
            return key
    if not kid and len(keys) == 1 and isinstance(keys[0], dict):
        return keys[0]
    return None


def _bearer(authorization: str | None) -> str:
    if authorization is None or not authorization.startswith("Bearer "):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    token = authorization.removeprefix("Bearer ").strip()
    if not token or any(char.isspace() for char in token):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required",
        )
    return token
