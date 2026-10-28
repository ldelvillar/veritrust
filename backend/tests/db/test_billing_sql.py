"""Pruebas del SQL real de ``app/db/billing.py``: clientes, Subscriptions, eventos y Usage."""

import asyncio
from datetime import UTC, datetime, timedelta

import pytest

from app.db.billing import (
    Usage,
    delete_user_billing,
    get_customer_id,
    get_user_subscription,
    insert_customer,
    is_event_processed,
    record_event,
    record_evidence_search,
    subscription_lock,
    upsert_subscription,
    usage_this_month,
    user_id_for_customer,
)
from app.db.history import delete_user_analysis
from app.schemas.analysis import AnalysisRequest
from tests.db.seed import seed_pending, seed_usage
from tests.support.billing import make_subscription

pytestmark = pytest.mark.db

USER = "user-a"
OCTOBER = (datetime(2026, 10, 1, tzinfo=UTC), datetime(2026, 11, 1, tzinfo=UTC))


async def test_customer_round_trips_both_ways(db_pool):
    assert await get_customer_id(USER) is None

    assert await insert_customer(USER, "cus_1") == "cus_1"

    assert await get_customer_id(USER) == "cus_1"
    assert await user_id_for_customer("cus_1") == USER
    assert await user_id_for_customer("cus_unknown") is None


async def test_insert_customer_keeps_the_first_one(db_pool):
    await insert_customer(USER, "cus_1")

    assert await insert_customer(USER, "cus_2") == "cus_1"
    assert await get_customer_id(USER) == "cus_1"
    assert await user_id_for_customer("cus_2") is None


async def test_upsert_subscription_replaces_every_field(db_pool):
    await upsert_subscription(make_subscription())
    updated = make_subscription(
        status="past_due",
        price_id="price_test_yearly",
        billing_interval="year",
        current_period_end=datetime(2027, 10, 26, tzinfo=UTC),
        cancel_at=datetime(2027, 10, 26, tzinfo=UTC),
    )

    await upsert_subscription(updated)

    assert await get_user_subscription(USER) == updated


async def test_user_subscription_prefers_pro_status_then_latest_period(db_pool):
    canceled_later = make_subscription(
        stripe_subscription_id="sub_old",
        status="canceled",
        current_period_end=datetime(2027, 1, 1, tzinfo=UTC),
    )
    active = make_subscription(stripe_subscription_id="sub_active")
    past_due_later = make_subscription(
        stripe_subscription_id="sub_past_due",
        status="past_due",
        current_period_end=datetime(2026, 12, 1, tzinfo=UTC),
    )
    for row in (canceled_later, active, past_due_later):
        await upsert_subscription(row)

    assert await get_user_subscription(USER) == past_due_later
    assert await get_user_subscription("user-b") is None


async def test_event_is_processed_only_once_recorded(db_pool):
    assert await is_event_processed("evt_1") is False

    await record_event("evt_1", "invoice.paid")
    await record_event("evt_1", "invoice.paid")

    assert await is_event_processed("evt_1") is True


async def test_usage_counts_this_month_and_pending_analyses(db_pool):
    start, end = OCTOBER
    await seed_usage(user_id=USER, occurred_at=start)
    await seed_usage(
        user_id=USER, occurred_at=datetime(2026, 10, 31, 23, 59, tzinfo=UTC)
    )
    # Fuera de la ventana o de otro usuario: no cuentan.
    await seed_usage(
        user_id=USER, occurred_at=datetime(2026, 9, 30, 23, 59, tzinfo=UTC)
    )
    await seed_usage(user_id=USER, occurred_at=end)
    await seed_usage(user_id="user-b", occurred_at=start)
    await seed_pending(
        user_id=USER, request=AnalysisRequest(text="La vitamina C cura el resfriado")
    )
    await seed_pending(
        user_id="user-b",
        request=AnalysisRequest(text="La vitamina C cura el resfriado"),
    )

    assert await usage_this_month(USER, start, end) == Usage(used=2, pending=1)


async def test_deleting_an_analysis_keeps_its_usage(db_pool):
    start, end = OCTOBER
    analysis_id = await seed_pending(
        user_id=USER, request=AnalysisRequest(text="La vitamina C cura el resfriado")
    )
    await seed_usage(user_id=USER, occurred_at=start, analysis_id=analysis_id)

    await delete_user_analysis(user_id=USER, analysis_id=analysis_id)

    assert await usage_this_month(USER, start, end) == Usage(used=1, pending=0)


async def test_an_evidence_search_counts_as_usage_now(db_pool):
    await record_evidence_search(USER)

    start = datetime.now(UTC) - timedelta(minutes=1)
    end = datetime.now(UTC) + timedelta(minutes=1)
    assert await usage_this_month(USER, start, end) == Usage(used=1, pending=0)
    async with db_pool.connection() as conn:
        cur = await conn.execute("SELECT kind, analysis_id FROM public.usage_events")
        assert await cur.fetchall() == [("evidence_search", None)]


async def test_deleting_a_users_billing_leaves_other_users_alone(db_pool):
    for user_id in (USER, "user-b"):
        await insert_customer(user_id, f"cus_{user_id}")
        await upsert_subscription(
            make_subscription(stripe_subscription_id=f"sub_{user_id}", user_id=user_id)
        )
        await record_evidence_search(user_id)

    await delete_user_billing(USER)

    start, end = datetime(2000, 1, 1, tzinfo=UTC), datetime(3000, 1, 1, tzinfo=UTC)
    assert await get_customer_id(USER) is None
    assert await get_user_subscription(USER) is None
    assert await usage_this_month(USER, start, end) == Usage(used=0, pending=0)
    assert await get_customer_id("user-b") == "cus_user-b"
    assert await get_user_subscription("user-b") is not None
    assert await usage_this_month("user-b", start, end) == Usage(used=1, pending=0)


async def test_subscription_lock_serializes_the_samemake_subscription(db_pool):
    order: list[str] = []
    first_holds = asyncio.Event()

    async def first():
        async with subscription_lock("sub_1"):
            first_holds.set()
            await asyncio.sleep(0.3)
            order.append("first")

    async def second():
        await first_holds.wait()
        async with subscription_lock("sub_1"):
            order.append("second")

    async def other():
        await first_holds.wait()
        async with subscription_lock("sub_2"):
            order.append("other")

    await asyncio.gather(first(), second(), other())

    assert order == ["other", "first", "second"]


async def test_queries_run_on_the_locked_connection(db_pool):
    await insert_customer(USER, "cus_1")

    async with subscription_lock("sub_1") as conn:
        assert await user_id_for_customer("cus_1", conn) == USER
        await upsert_subscription(make_subscription(), conn)

    assert await get_user_subscription(USER) == make_subscription()
