"""Reglas de cada Plan: sus límites, cuándo una Subscription hace Pro a un usuario y el mes de su Allowance."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH

PlanName = Literal["free", "pro"]
BillingInterval = Literal["month", "year"]
# Funciones que un Plan concede o niega: los campos booleanos de PlanLimits
Feature = Literal[
    "files", "history_tools", "dashboard", "csv_export", "share", "mcp", "pdf"
]

# Estados de Stripe que mantienen Pro; past_due lo conserva durante los reintentos de cobro
PRO_STATUSES = frozenset({"active", "trialing", "past_due"})

MADRID = ZoneInfo("Europe/Madrid")


@dataclass(frozen=True)
class PlanLimits:
    """Lo que un Plan permite a su usuario."""

    name: PlanName
    analyses_per_month: int
    max_input_chars: int
    history_days: int | None
    files: bool
    history_tools: bool
    dashboard: bool
    csv_export: bool
    share: bool
    mcp: bool
    pdf: bool


FREE = PlanLimits(
    name="free",
    analyses_per_month=10,
    max_input_chars=3000,
    history_days=30,
    files=False,
    history_tools=False,
    dashboard=False,
    csv_export=False,
    share=False,
    mcp=False,
    pdf=False,
)

PRO = PlanLimits(
    name="pro",
    analyses_per_month=300,
    max_input_chars=MAX_INPUT_TEXT_LENGTH,
    history_days=None,
    files=True,
    history_tools=True,
    dashboard=True,
    csv_export=True,
    share=True,
    mcp=True,
    pdf=True,
)


@dataclass(frozen=True)
class SubscriptionRow:
    """Una Subscription de Stripe tal como se guarda en la tabla subscriptions."""

    stripe_subscription_id: str
    user_id: str
    status: str
    price_id: str
    billing_interval: BillingInterval
    current_period_end: datetime
    cancel_at: datetime | None


@dataclass(frozen=True)
class Allowance:
    """Runs done que el Plan permite en un mes de Madrid, con el inicio y el fin de ese mes."""

    runs: int
    month_start: datetime
    month_end: datetime


def pro_price_ids() -> list[str]:
    """Los dos precios de Stripe que hacen Pro a una Subscription."""
    settings = get_settings()
    return [settings.stripe_price_pro_monthly, settings.stripe_price_pro_yearly]


def is_pro(subscription: SubscriptionRow | None) -> bool:
    """Indica si la Subscription está en un estado Pro y sobre uno de los dos precios Pro."""
    if subscription is None or subscription.status not in PRO_STATUSES:
        return False
    return subscription.price_id in pro_price_ids()


def limits_for(subscription: SubscriptionRow | None) -> PlanLimits:
    """Devuelve los límites del Plan que da la Subscription del usuario, o Free sin ella."""
    return PRO if is_pro(subscription) else FREE


def remaining(limits: PlanLimits, used: int, pending: int) -> int:
    """Análisis que aún caben en la Allowance del mes, contando los pendientes como consumidos."""
    return max(0, limits.analyses_per_month - used - pending)


def month_window(now: datetime) -> tuple[datetime, datetime]:
    """Devuelve el inicio del mes de Madrid que contiene ``now`` y el del siguiente."""
    local = now.astimezone(MADRID)
    start = datetime(local.year, local.month, 1, tzinfo=MADRID)
    if local.month == 12:
        return start, datetime(local.year + 1, 1, 1, tzinfo=MADRID)
    return start, datetime(local.year, local.month + 1, 1, tzinfo=MADRID)


def allowance_for(limits: PlanLimits, now: datetime) -> Allowance:
    """Devuelve la Allowance del Plan en el mes de Madrid que contiene ``now``."""
    start, end = month_window(now)
    return Allowance(runs=limits.analyses_per_month, month_start=start, month_end=end)


def history_floor(limits: PlanLimits, now: datetime) -> datetime | None:
    """Devuelve el instante más antiguo que el Plan ve de su History, o None si lo ve todo."""
    if limits.history_days is None:
        return None
    return now - timedelta(days=limits.history_days)
