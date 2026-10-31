"""Case tables of ``app/core/plans.py``: which Subscription gives Pro and the Allowance month."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest

from app.core.plans import (
    FREE,
    MADRID,
    PRO,
    Feature,
    PlanLimits,
    history_floor,
    limits_for,
    month_window,
    remaining,
)
from app.schemas.analysis import MAX_INPUT_TEXT_LENGTH
from tests.support.billing import PRICE_YEARLY, make_subscription


@pytest.mark.parametrize(
    ("status", "expected"),
    [
        ("active", PRO),
        ("trialing", PRO),
        ("past_due", PRO),
        ("incomplete", FREE),
        ("incomplete_expired", FREE),
        ("canceled", FREE),
        ("unpaid", FREE),
        ("paused", FREE),
    ],
)
def test_limits_follow_every_stripe_status(stripe_settings, status, expected):
    assert limits_for(make_subscription(status=status)) == expected


def test_yearly_price_is_pro(stripe_settings):
    assert limits_for(make_subscription(price_id=PRICE_YEARLY)) == PRO


def test_unknown_price_is_free_even_when_active(stripe_settings):
    assert limits_for(make_subscription(price_id="price_other_product")) == FREE


def test_no_subscription_is_free(stripe_settings):
    assert limits_for(None) == FREE


def test_pro_text_limit_is_the_schema_maximum():
    assert PRO.max_input_chars == MAX_INPUT_TEXT_LENGTH
    assert FREE.max_input_chars < PRO.max_input_chars


def _madrid(*args: int) -> datetime:
    return datetime(*args, tzinfo=MADRID)


@pytest.mark.parametrize(
    ("now", "start", "end"),
    [
        # Mid-month.
        (_madrid(2026, 10, 15, 12), _madrid(2026, 10, 1), _madrid(2026, 11, 1)),
        # Late on 31 December and early on 1 January.
        (_madrid(2026, 12, 31, 23, 59), _madrid(2026, 12, 1), _madrid(2027, 1, 1)),
        (_madrid(2027, 1, 1, 0, 0), _madrid(2027, 1, 1), _madrid(2027, 2, 1)),
        # The March (last Sunday, 29) and October (last Sunday, 25) clock changes.
        (_madrid(2026, 3, 29, 3, 30), _madrid(2026, 3, 1), _madrid(2026, 4, 1)),
        (_madrid(2026, 10, 25, 2, 30), _madrid(2026, 10, 1), _madrid(2026, 11, 1)),
    ],
)
def test_month_window_is_the_madrid_calendar_month(now, start, end):
    assert month_window(now) == (start, end)


def test_month_window_uses_madrid_not_utc_near_midnight():
    # 31 Oct 23:30 UTC is already 1 Nov 00:30 in Madrid (UTC+1 in winter).
    start, end = month_window(datetime(2026, 10, 31, 23, 30, tzinfo=UTC))

    assert start == _madrid(2026, 11, 1)
    assert end == _madrid(2026, 12, 1)
    assert start.astimezone(UTC) == datetime(2026, 10, 31, 23, 0, tzinfo=UTC)


def test_month_window_offsets_follow_daylight_saving():
    # October starts on summer time (UTC+2) and November on winter time (UTC+1).
    start, end = month_window(_madrid(2026, 10, 15))

    assert start.utcoffset() == timedelta(hours=2)
    assert end.utcoffset() == timedelta(hours=1)


def test_features_are_exactly_the_boolean_limits():
    booleans = {field.name for field in fields(PlanLimits) if field.type is bool}

    assert set(get_args(Feature)) == booleans


def test_history_floor_is_thirty_days_for_free_and_none_for_pro():
    now = datetime(2026, 10, 26, 12, tzinfo=UTC)

    assert history_floor(FREE, now) == now - timedelta(days=30)
    assert history_floor(PRO, now) is None


@pytest.mark.parametrize(
    ("limits", "used", "pending", "expected"),
    [(FREE, 4, 1, 5), (FREE, 10, 0, 0), (FREE, 9, 3, 0), (PRO, 0, 0, 300)],
)
def test_remaining_counts_pending_analyses_and_never_goes_negative(
    limits, used, pending, expected
):
    assert remaining(limits, used, pending) == expected
