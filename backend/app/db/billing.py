"""Billing persistence: Stripe customers and Subscriptions, processed events and Usage."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, LiteralString

import psycopg

from app.core.plans import PRO_STATUSES, SubscriptionRow
from app.db.pool import DatabaseError, _build_database_error, get_pool


@dataclass(frozen=True)
class Usage:
    """Done Runs counted this month and pending analyses that can still consume one."""

    used: int
    pending: int


@asynccontextmanager
async def _connection(
    conn: psycopg.AsyncConnection | None,
) -> AsyncIterator[psycopg.AsyncConnection]:
    """Use the given connection or, without one, one from the pool."""
    if conn is not None:
        yield conn
        return
    pool = await get_pool()
    async with pool.connection() as pooled:
        yield pooled


async def _fetchone(
    query: LiteralString,
    params: tuple[Any, ...],
    context: str,
    conn: psycopg.AsyncConnection | None = None,
) -> tuple[Any, ...] | None:
    """Run a statement and return its first row, translating the psycopg error."""
    try:
        async with _connection(conn) as active, active.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchone() if cur.description else None
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc


async def get_customer_id(user_id: str) -> str | None:
    """Return the user's Stripe customer, or None if they never started a payment."""
    row = await _fetchone(
        "SELECT stripe_customer_id FROM public.billing_customers WHERE user_id = %s",
        (user_id,),
        "No se pudo consultar el cliente de facturación.",
    )
    return row[0] if row else None


async def insert_customer(user_id: str, stripe_customer_id: str) -> str:
    """Link the Stripe customer to the user and return the stored one if they already had one."""
    row = await _fetchone(
        """
        INSERT INTO public.billing_customers (user_id, stripe_customer_id)
        VALUES (%s, %s)
        ON CONFLICT (user_id) DO UPDATE SET user_id = EXCLUDED.user_id
        RETURNING stripe_customer_id
        """,
        (user_id, stripe_customer_id),
        "No se pudo guardar el cliente de facturación.",
    )
    assert row is not None
    return row[0]


async def user_id_for_customer(
    stripe_customer_id: str, conn: psycopg.AsyncConnection | None = None
) -> str | None:
    """Return the user a Stripe customer belongs to, or None if it is not ours."""
    row = await _fetchone(
        "SELECT user_id FROM public.billing_customers WHERE stripe_customer_id = %s",
        (stripe_customer_id,),
        "No se pudo consultar el cliente de facturación.",
        conn,
    )
    return row[0] if row else None


async def upsert_subscription(
    row: SubscriptionRow, conn: psycopg.AsyncConnection | None = None
) -> None:
    """Store the Subscription, replacing all its fields with the received ones."""
    await _fetchone(
        """
        INSERT INTO public.subscriptions
            (stripe_subscription_id, user_id, status, price_id, billing_interval,
             current_period_end, cancel_at)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (stripe_subscription_id) DO UPDATE SET
            user_id = EXCLUDED.user_id,
            status = EXCLUDED.status,
            price_id = EXCLUDED.price_id,
            billing_interval = EXCLUDED.billing_interval,
            current_period_end = EXCLUDED.current_period_end,
            cancel_at = EXCLUDED.cancel_at,
            updated_at = NOW()
        """,
        (
            row.stripe_subscription_id,
            row.user_id,
            row.status,
            row.price_id,
            row.billing_interval,
            row.current_period_end,
            row.cancel_at,
        ),
        "No se pudo guardar la suscripción.",
        conn,
    )


@asynccontextmanager
async def subscription_lock(
    stripe_subscription_id: str,
) -> AsyncIterator[psycopg.AsyncConnection]:
    """Serialise the Stripe read and the store of a Subscription, with queries going through the yielded connection."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn, conn.transaction():
            await conn.execute(
                "SELECT pg_advisory_xact_lock(hashtext('subscription:' || %s))",
                (stripe_subscription_id,),
            )
            yield conn
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo bloquear la suscripción.")
        ) from exc


async def get_user_subscription(user_id: str) -> SubscriptionRow | None:
    """Return the Subscription that decides the Plan, Pro first and then the latest period."""
    row = await _fetchone(
        """
        SELECT stripe_subscription_id, user_id, status, price_id, billing_interval,
               current_period_end, cancel_at
        FROM public.subscriptions
        WHERE user_id = %s
        ORDER BY status = ANY(%s) DESC, current_period_end DESC
        LIMIT 1
        """,
        (user_id, list(PRO_STATUSES)),
        "No se pudo consultar la suscripción.",
    )
    return SubscriptionRow(*row) if row else None


async def is_event_processed(event_id: str) -> bool:
    """Tell whether a Stripe event was already processed successfully."""
    row = await _fetchone(
        "SELECT 1 FROM public.stripe_events WHERE id = %s",
        (event_id,),
        "No se pudo consultar el evento de Stripe.",
    )
    return row is not None


async def record_event(event_id: str, event_type: str) -> None:
    """Mark a Stripe event as processed, where repeating it has no effect."""
    await _fetchone(
        """
        INSERT INTO public.stripe_events (id, type) VALUES (%s, %s)
        ON CONFLICT (id) DO NOTHING
        """,
        (event_id, event_type),
        "No se pudo registrar el evento de Stripe.",
    )


async def usage_this_month(
    user_id: str,
    start: datetime,
    end: datetime,
    conn: psycopg.AsyncConnection | None = None,
) -> Usage:
    """Count the user's Usage in [start, end) and their still pending analyses."""
    row = await _fetchone(
        """
        SELECT
            (SELECT count(*) FROM public.usage_events
             WHERE user_id = %s AND occurred_at >= %s AND occurred_at < %s),
            (SELECT count(*) FROM public.analysis_history
             WHERE user_id = %s AND status = 'pending')
        """,
        (user_id, start, end, user_id),
        "No se pudo consultar el uso del plan.",
        conn,
    )
    assert row is not None
    return Usage(used=row[0], pending=row[1])


async def record_evidence_search(user_id: str) -> None:
    """Record in the Usage an Evidence search that ended with a result."""
    await _fetchone(
        "INSERT INTO public.usage_events (user_id, kind) "
        "VALUES (%s, 'evidence_search')",
        (user_id,),
        "No se pudo registrar el uso del plan.",
    )


async def delete_user_billing(user_id: str) -> None:
    """Erase the customer, Subscriptions and Usage of a user who deleted their account."""
    # A single statement, so the three deletions apply together or not at all.
    await _fetchone(
        """
        WITH deleted_customers AS (
            DELETE FROM public.billing_customers WHERE user_id = %s
        ), deleted_subscriptions AS (
            DELETE FROM public.subscriptions WHERE user_id = %s
        )
        DELETE FROM public.usage_events WHERE user_id = %s
        """,
        (user_id, user_id, user_id),
        "No se pudo borrar la facturación del usuario.",
    )
