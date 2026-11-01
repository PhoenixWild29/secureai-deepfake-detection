"""Verify Clerk session JWTs. AUTH_MODE=dev accepts only the literal bearer `dev`."""

from __future__ import annotations

import logging
from typing import Annotated, Callable

import jwt
from fastapi import Depends, Header, HTTPException, Request, status

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


def require_admin(
    request: Request,
    user: Annotated[AuthContext, Depends(require_user)],
) -> AuthContext:
    """Allow only subjects listed in ``ADMIN_USER_IDS``.

    An empty list allows nobody. The response does not echo the list.
    In dev mode the subject is ``DEV_AUTH_SUBJECT``.
    """

    if user.subject not in request.app.state.settings.admin_user_ids:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required",
        )
    return user


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
