"""Subscriptions: who pays for what, behind one interface so the payment processor can be swapped.

Today the only provider is `mock` (BILLING_PROVIDER=mock): checkout activates the plan at once and
nothing is charged. A real processor (Paddle, Lemon Squeezy, Recurrente...) plugs in by:
1. implementing `BillingProvider.start_checkout` to return the processor's hosted checkout URL;
2. adding a webhook route that verifies the processor's signature and calls `activate_plan` /
   `cancel_plan` with the user id it put in the checkout's metadata.
Routes and the user's plan fields never change.
"""

from dataclasses import dataclass
from datetime import timedelta
from typing import Protocol

from app.core.config import settings
from app.domain.plans import PLAN_PERIODS, PLANS, Period, Region
from app.repositories import Repository, UserRecord
from app.repositories.base import utcnow

PERIOD_LENGTH = {"monthly": timedelta(days=30), "yearly": timedelta(days=365)}


class BillingError(Exception):
    """A checkout that cannot be started (unknown plan, period not offered...)."""


@dataclass
class CheckoutResult:
    provider: str
    # Where to send the browser to pay; None when the plan was activated directly (mock).
    checkout_url: str | None
    activated: bool


async def activate_plan(user: UserRecord, plan: str, period: Period, provider: str, repository: Repository) -> UserRecord:
    """Gives the user a paid plan. Called by the mock checkout now and by the processor's webhook later."""
    now = utcnow()
    user.plan = plan
    user.plan_period = period
    user.plan_provider = provider
    user.plan_started_at = now
    user.plan_renews_at = now + PERIOD_LENGTH[period] if period in PERIOD_LENGTH else None
    await repository.save_user(user)
    return user


async def cancel_plan(user: UserRecord, repository: Repository) -> UserRecord:
    """Back to Gratis. Saved progressions are kept; only new saves above the limit are blocked."""
    user.plan = "free"
    user.plan_period = None
    user.plan_provider = None
    user.plan_started_at = None
    user.plan_renews_at = None
    await repository.save_user(user)
    return user


def validate_checkout(plan: str, period: Period) -> None:
    if plan not in PLAN_PERIODS:
        raise BillingError(f"El plan {plan!r} no se puede comprar")
    if period not in PLAN_PERIODS[plan]:
        offered = ", ".join(PLAN_PERIODS[plan])
        raise BillingError(f"El plan {PLANS[plan].name} se compra con periodo: {offered}")


class BillingProvider(Protocol):
    name: str

    async def start_checkout(
        self, user: UserRecord, plan: str, period: Period, region: Region, repository: Repository
    ) -> CheckoutResult: ...

    async def cancel(self, user: UserRecord, repository: Repository) -> UserRecord: ...


class MockBillingProvider:
    """Simulated payments: the plan is activated immediately and nothing is charged."""

    name = "mock"

    async def start_checkout(self, user: UserRecord, plan: str, period: Period, region: Region, repository: Repository) -> CheckoutResult:
        validate_checkout(plan, period)
        await activate_plan(user, plan, period, self.name, repository)
        return CheckoutResult(provider=self.name, checkout_url=None, activated=True)

    async def cancel(self, user: UserRecord, repository: Repository) -> UserRecord:
        return await cancel_plan(user, repository)


PROVIDERS: dict[str, BillingProvider] = {"mock": MockBillingProvider()}


def get_billing_provider() -> BillingProvider:
    """FastAPI dependency: the provider named by BILLING_PROVIDER."""
    return PROVIDERS[settings.billing_provider]
