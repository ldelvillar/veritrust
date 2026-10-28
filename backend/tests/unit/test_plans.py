"""Tablas de casos de ``app/core/plans.py``: qué Subscription da Pro y el mes de la Allowance."""

from dataclasses import fields
from datetime import UTC, datetime, timedelta
from typing import get_args

import pytest

from app.core.plans import (
    FREE,
    MADRID,
    PRO,
    Allowance,
    Feature,
    PlanLimits,
    allowance_for,
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
        # Mitad de mes
        (_madrid(2026, 10, 15, 12), _madrid(2026, 10, 1), _madrid(2026, 11, 1)),
        # 31 de diciembre a última hora y 1 de enero a primera hora
        (_madrid(2026, 12, 31, 23, 59), _madrid(2026, 12, 1), _madrid(2027, 1, 1)),
        (_madrid(2027, 1, 1, 0, 0), _madrid(2027, 1, 1), _madrid(2027, 2, 1)),
        # Cambio de hora de marzo (último domingo, 29) y de octubre (último domingo, 25)
        (_madrid(2026, 3, 29, 3, 30), _madrid(2026, 3, 1), _madrid(2026, 4, 1)),
        (_madrid(2026, 10, 25, 2, 30), _madrid(2026, 10, 1), _madrid(2026, 11, 1)),
    ],
)
def test_month_window_is_the_madrid_calendar_month(now, start, end):
    assert month_window(now) == (start, end)


def test_month_window_uses_madrid_not_utc_near_midnight():
    # 31 oct 23:30 UTC ya es 1 nov 00:30 en Madrid (UTC+1 en invierno).
    start, end = month_window(datetime(2026, 10, 31, 23, 30, tzinfo=UTC))

    assert start == _madrid(2026, 11, 1)
    assert end == _madrid(2026, 12, 1)
    assert start.astimezone(UTC) == datetime(2026, 10, 31, 23, 0, tzinfo=UTC)


def test_month_window_offsets_follow_daylight_saving():
    # Octubre empieza en horario de verano (UTC+2) y noviembre en el de invierno (UTC+1).
    start, end = month_window(_madrid(2026, 10, 15))

    assert start.utcoffset() == timedelta(hours=2)
    assert end.utcoffset() == timedelta(hours=1)


def test_features_are_exactly_the_boolean_limits():
    booleans = {field.name for field in fields(PlanLimits) if field.type is bool}

    assert set(get_args(Feature)) == booleans


def test_allowance_is_the_plans_runs_in_the_madrid_month():
    now = datetime(2026, 10, 31, 23, 30, tzinfo=UTC)

    assert allowance_for(FREE, now) == Allowance(
        runs=10, month_start=_madrid(2026, 11, 1), month_end=_madrid(2026, 12, 1)
    )
    assert allowance_for(PRO, now).runs == 300


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
