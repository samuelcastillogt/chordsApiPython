"""Plans, prices and the signed-in user's subscription."""

from fastapi import APIRouter, Depends, HTTPException

from app.api.schemas import CheckoutRequest, CheckoutResponse, PlansResponse, SubscriptionResponse
from app.billing import BillingError, BillingProvider, get_billing_provider
from app.core.config import settings
from app.core.security import get_current_user
from app.domain.plans import PLANS, get_plan
from app.repositories import Repository, UserRecord, get_repository

router = APIRouter()


def serialize_plan(plan_id: str) -> dict:
    plan = PLANS[plan_id]
    return {
        "id": plan.id,
        "name": plan.name,
        "tagline": plan.tagline,
        "saveLimit": plan.save_limit,
        "features": list(plan.features),
        "prices": [{"period": price.period, "amount": price.amount, "currency": "USD", "region": price.region} for price in plan.prices],
    }


async def serialize_subscription(user: UserRecord, repository: Repository) -> dict:
    plan = get_plan(user.plan)
    return {
        "plan": plan.id,
        "planName": plan.name,
        "period": user.plan_period,
        "provider": user.plan_provider,
        "startedAt": user.plan_started_at.isoformat() if user.plan_started_at else None,
        "renewsAt": user.plan_renews_at.isoformat() if user.plan_renews_at else None,
        "saved": await repository.count_progressions(user.id),
        "saveLimit": plan.save_limit,
    }


@router.get("/plans", response_model=PlansResponse)
async def list_plans():
    """Public price list. `provider` is "mock" while payments are simulated (nothing is charged)."""
    return {"provider": settings.billing_provider, "plans": [serialize_plan(plan_id) for plan_id in PLANS]}


@router.get("/billing/subscription", response_model=SubscriptionResponse)
async def subscription(user: UserRecord = Depends(get_current_user), repository: Repository = Depends(get_repository)):
    return await serialize_subscription(user, repository)


@router.post("/billing/checkout", response_model=CheckoutResponse)
async def checkout(
    request: CheckoutRequest,
    user: UserRecord = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
    provider: BillingProvider = Depends(get_billing_provider),
):
    """Starts a purchase. With a real processor the response carries `checkoutUrl`; with the mock the plan is already active."""
    try:
        result = await provider.start_checkout(user, request.plan, request.period, request.region, repository)
    except BillingError as error:
        raise HTTPException(status_code=400, detail=str(error)) from error
    return {
        "provider": result.provider,
        "checkoutUrl": result.checkout_url,
        "activated": result.activated,
        "subscription": await serialize_subscription(user, repository),
    }


@router.post("/billing/cancel", response_model=SubscriptionResponse)
async def cancel(
    user: UserRecord = Depends(get_current_user),
    repository: Repository = Depends(get_repository),
    provider: BillingProvider = Depends(get_billing_provider),
):
    """Ends the subscription and returns to Gratis. Saved progressions are kept."""
    if user.plan == "free":
        raise HTTPException(status_code=400, detail="No tienes una suscripción activa")
    return await serialize_subscription(await provider.cancel(user, repository), repository)
