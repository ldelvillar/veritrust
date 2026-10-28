"""Persistencia de facturación: clientes y Subscriptions de Stripe, eventos procesados y Usage."""

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
    """Runs done contados este mes y análisis pendientes que aún pueden consumir uno."""

    used: int
    pending: int


@asynccontextmanager
async def _connection(
    conn: psycopg.AsyncConnection | None,
) -> AsyncIterator[psycopg.AsyncConnection]:
    """Usa la conexión dada o, sin ella, una del pool."""
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
    """Ejecuta una sentencia y devuelve su primera fila, traduciendo el error de psycopg."""
    try:
        async with _connection(conn) as active, active.cursor() as cur:
            await cur.execute(query, params)
            return await cur.fetchone() if cur.description else None
    except psycopg.Error as exc:
        raise DatabaseError(_build_database_error(context)) from exc


async def get_customer_id(user_id: str) -> str | None:
    """Devuelve el cliente de Stripe del usuario, o None si nunca inició un pago."""
    row = await _fetchone(
        "SELECT stripe_customer_id FROM public.billing_customers WHERE user_id = %s",
        (user_id,),
        "No se pudo consultar el cliente de facturación.",
    )
    return row[0] if row else None


async def insert_customer(user_id: str, stripe_customer_id: str) -> str:
    """Vincula el cliente de Stripe al usuario y devuelve el que queda guardado si ya tenía uno."""
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
    """Devuelve el usuario al que pertenece un cliente de Stripe, o None si no es nuestro."""
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
    """Guarda la Subscription sustituyendo todos sus campos por los recibidos."""
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
    """Serializa la lectura en Stripe y el guardado de una Subscription; las consultas van por la conexión cedida."""
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
    """Devuelve la Subscription que decide el Plan: la Pro primero, luego la de periodo más tardío."""
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
    """Indica si un evento de Stripe ya se procesó con éxito."""
    row = await _fetchone(
        "SELECT 1 FROM public.stripe_events WHERE id = %s",
        (event_id,),
        "No se pudo consultar el evento de Stripe.",
    )
    return row is not None


async def record_event(event_id: str, event_type: str) -> None:
    """Marca un evento de Stripe como procesado; repetirlo no tiene efecto."""
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
    """Cuenta el Usage del usuario en [start, end) y sus análisis aún pendientes."""
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
    """Anota en el Usage una búsqueda de evidencia que terminó con resultado."""
    await _fetchone(
        "INSERT INTO public.usage_events (user_id, kind) "
        "VALUES (%s, 'evidence_search')",
        (user_id,),
        "No se pudo registrar el uso del plan.",
    )


async def delete_user_billing(user_id: str) -> None:
    """Borra el cliente, las Subscriptions y el Usage de un usuario que eliminó su cuenta."""
    # Una sola sentencia: los tres borrados se aplican juntos o ninguno.
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
