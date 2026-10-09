"""Plans and prices. The single source of truth: the web's pricing page reads them from /api/v1/plans."""

from dataclasses import dataclass, field
from typing import Literal

PlanId = Literal["free", "pro", "lifetime"]
Period = Literal["monthly", "yearly", "once"]
Region = Literal["global", "latam"]

FREE_SAVE_LIMIT = 5


@dataclass(frozen=True)
class Price:
    period: Period
    amount: float  # USD
    region: Region = "global"


@dataclass(frozen=True)
class Plan:
    id: PlanId
    name: str
    tagline: str
    save_limit: int | None  # None = unlimited
    features: tuple[str, ...]
    prices: tuple[Price, ...] = field(default_factory=tuple)

    def price(self, period: Period, region: Region = "global") -> Price | None:
        """The price for a period in a region, falling back to the global price."""
        matches = [price for price in self.prices if price.period == period]
        return next((price for price in matches if price.region == region), None) or next(
            (price for price in matches if price.region == "global"), None
        )


PLANS: dict[str, Plan] = {
    "free": Plan(
        id="free",
        name="Gratis",
        tagline="Para analizar canciones y aprender por qué suenan así.",
        save_limit=FREE_SAVE_LIMIT,
        features=(
            "Analizador, explorador, mástil y piano sin límite",
            f"Guarda hasta {FREE_SAVE_LIMIT} progresiones",
            "Comparte progresiones con un enlace",
            "Sin anuncios ni pop-ups",
        ),
    ),
    "pro": Plan(
        id="pro",
        name="Pro",
        tagline="Para quien toca, enseña o compone todas las semanas.",
        save_limit=None,
        features=(
            "Todo lo del plan Gratis",
            "Progresiones guardadas sin límite",
            "Acceso anticipado a lo nuevo: modo alabanza y modo docente",
            "Soporte prioritario por correo",
            "Apoyas una herramienta de música hecha en español",
        ),
        prices=(
            Price("monthly", 4.99),
            Price("yearly", 29.99),
            Price("yearly", 19.99, "latam"),
        ),
    ),
    "lifetime": Plan(
        id="lifetime",
        name="Vitalicio fundador",
        tagline="Un solo pago, para los primeros usuarios.",
        save_limit=None,
        features=(
            "Todo lo del plan Pro, para siempre",
            "Precio de fundador: no se repetirá",
            "Insignia de fundador en tu cuenta",
        ),
        prices=(
            Price("once", 69.0),
            Price("once", 39.0, "latam"),
        ),
    ),
}

# Periods each paid plan can be bought with.
PLAN_PERIODS: dict[str, tuple[Period, ...]] = {"pro": ("monthly", "yearly"), "lifetime": ("once",)}


def get_plan(plan_id: str | None) -> Plan:
    """The plan for a stored id; unknown or missing ids fall back to Gratis."""
    return PLANS.get(plan_id or "free", PLANS["free"])
