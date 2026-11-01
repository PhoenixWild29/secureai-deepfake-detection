"""Stripe Checkout, Customer Portal, and webhook signature checks.

Calls stay in this module so tests can replace them without hitting Stripe.
"""

from __future__ import annotations

import logging

from secureai_shared.settings import Settings

logger = logging.getLogger("secureai.api.stripe")


class StripeNotConfigured(Exception):
    """A secret or price id required for this call is empty."""


class StripeSignatureError(Exception):
    """The webhook signature is missing or does not match the payload."""


class StripeProviderError(Exception):
    """Stripe returned an error or an incomplete object."""


class StripeBilling:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def checkout_ready(self, plan: str) -> bool:
        return bool(self.settings.stripe_secret_key and self.price_for(plan))

    def portal_ready(self) -> bool:
        return bool(self.settings.stripe_secret_key)

    def price_for(self, plan: str) -> str:
        if plan == "pro":
            return self.settings.stripe_price_pro
        if plan == "team":
            return self.settings.stripe_price_team
        return ""

    def ensure_customer(self, *, existing: str | None, user_id: str, org_id: str | None) -> str:
        if existing:
            return existing
        if not self.settings.stripe_secret_key:
            raise StripeNotConfigured("secret")
        import stripe

        scope = org_id or user_id
        try:
            customer = stripe.Customer.create(
                metadata={"user_id": user_id, "org_id": org_id or ""},
                api_key=self.settings.stripe_secret_key,
                idempotency_key=f"secureai-customer-{scope}",
            )
        except stripe.StripeError as exc:
            raise StripeProviderError("customer") from exc
        customer_id = customer["id"]
        if not isinstance(customer_id, str) or not customer_id:
            raise StripeProviderError("customer id")
        return customer_id

    def checkout_url(
        self,
        *,
        customer_id: str,
        price_id: str,
        user_id: str,
        org_id: str | None,
        plan: str,
    ) -> str:
        if not self.settings.stripe_secret_key or not price_id:
            raise StripeNotConfigured("checkout")
        import stripe

        metadata = {"user_id": user_id, "org_id": org_id or "", "plan": plan}
        try:
            session = stripe.checkout.Session.create(
                mode="subscription",
                customer=customer_id,
                client_reference_id=org_id or user_id,
                line_items=[{"price": price_id, "quantity": 1}],
                success_url=f"{self.settings.public_app_url}/billing?checkout=success",
                cancel_url=f"{self.settings.public_app_url}/billing?checkout=cancel",
                metadata=metadata,
                subscription_data={"metadata": metadata},
                api_key=self.settings.stripe_secret_key,
            )
        except stripe.StripeError as exc:
            raise StripeProviderError("checkout") from exc
        url = session["url"]
        if not isinstance(url, str) or not url:
            raise StripeProviderError("checkout url")
        return url

    def portal_url(self, *, customer_id: str) -> str:
        if not self.settings.stripe_secret_key:
            raise StripeNotConfigured("portal")
        import stripe

        try:
            session = stripe.billing_portal.Session.create(
                customer=customer_id,
                return_url=f"{self.settings.public_app_url}/billing",
                api_key=self.settings.stripe_secret_key,
            )
        except stripe.StripeError as exc:
            raise StripeProviderError("portal") from exc
        url = session["url"]
        if not isinstance(url, str) or not url:
            raise StripeProviderError("portal url")
        return url

    def parse_event(self, payload: bytes, signature: str | None) -> dict[str, object]:
        if not self.settings.stripe_webhook_secret:
            raise StripeNotConfigured("webhook")
        if not signature:
            raise StripeSignatureError("missing signature")
        import stripe
        from stripe import SignatureVerificationError

        try:
            event = stripe.Webhook.construct_event(
                payload,
                signature,
                self.settings.stripe_webhook_secret,
            )
        except (ValueError, SignatureVerificationError) as exc:
            raise StripeSignatureError("invalid signature") from exc
        plain = event.to_dict()
        if not isinstance(plain, dict):
            raise StripeSignatureError("unreadable event")
        return plain
