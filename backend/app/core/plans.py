"""Rules of each Plan: its limits, when a Subscription makes a user Pro and the month of its Allowance."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo

from app.core.config import get_settings
from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH

PlanName = Literal["free", "pro"]
BillingInterval = Literal["month", "year"]
# Features a Plan grants or denies, the boolean fields of PlanLimits.
Feature = Literal[
    "files", "history_tools", "dashboard", "csv_export", "share", "mcp", "pdf"
]

# Stripe statuses that keep Pro, where past_due keeps it during payment retries.
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
    """A Stripe Subscription as stored in the subscriptions table."""

    stripe_subscription_id: str
    user_id: str
    status: str
    price_id: str
    billing_interval: BillingInterval
    current_period_end: datetime
    cancel_at: datetime | None


def is_pro(subscription: SubscriptionRow | None) -> bool:
    """Tell whether the Subscription is in a Pro status and on one of the two Pro prices."""
    if subscription is None or subscription.status not in PRO_STATUSES:
        return False
    settings = get_settings()
    return subscription.price_id in {
        settings.stripe_price_pro_monthly,
        settings.stripe_price_pro_yearly,
    }


def limits_for(subscription: SubscriptionRow | None) -> PlanLimits:
    """Return the limits of the Plan the user's Subscription gives, or Free without one."""
    return PRO if is_pro(subscription) else FREE


def remaining(limits: PlanLimits, used: int, pending: int) -> int:
    """Analyses that still fit in the month's Allowance, counting pending ones as consumed."""
    return max(0, limits.analyses_per_month - used - pending)


def month_window(now: datetime) -> tuple[datetime, datetime]:
    """Return the start of the Madrid month containing ``now`` and of the next one."""
    local = now.astimezone(MADRID)
    start = datetime(local.year, local.month, 1, tzinfo=MADRID)
    if local.month == 12:
        return start, datetime(local.year + 1, 1, 1, tzinfo=MADRID)
    return start, datetime(local.year, local.month + 1, 1, tzinfo=MADRID)


def history_floor(limits: PlanLimits, now: datetime) -> datetime | None:
    """Return the oldest instant of its History the Plan sees, or None when it sees all of it."""
    if limits.history_days is None:
        return None
    return now - timedelta(days=limits.history_days)
