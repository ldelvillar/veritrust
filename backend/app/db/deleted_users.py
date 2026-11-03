"""Record of accounts deleted in Clerk, which refuses the writes that would land for them afterwards."""

from __future__ import annotations

import psycopg

from app.db.pool import DatabaseError, _build_database_error, get_pool

# Longer than the backup cycle of about a month, so a restore of any kept dump still finds the deletions made after it.
RETENTION_DAYS = 35

# Serialises a user's openings, Usage writes and deletion until their transaction ends.
_LOCK_USER = "SELECT pg_advisory_xact_lock(hashtext('allowance:' || %s))"
_IS_DELETED = "SELECT 1 FROM public.deleted_users WHERE user_id = %s"


class UserDeleted(Exception):
    """The user deleted their account, and nothing was written."""


async def lock_live_user(conn: psycopg.AsyncConnection, user_id: str) -> None:
    """Lock the user's writes for the transaction and raise UserDeleted if their account is gone."""
    async with conn.cursor() as cur:
        await cur.execute(_LOCK_USER, (user_id,))
        # Read after the lock, so a deletion that committed while this waited is seen.
        await cur.execute(_IS_DELETED, (user_id,))
        if await cur.fetchone() is not None:
            raise UserDeleted(user_id)


async def is_deleted(user_id: str) -> bool:
    """Tell whether the account is recorded as deleted, without locking, for a check before a call outside the database."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            cur = await conn.execute(_IS_DELETED, (user_id,))
            return await cur.fetchone() is not None
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo consultar la baja del usuario.")
        ) from exc


async def mark_deleted(user_id: str) -> None:
    """Record the account's deletion once, after any write of the user already in flight commits."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn, conn.transaction():
            async with conn.cursor() as cur:
                await cur.execute(_LOCK_USER, (user_id,))
                await cur.execute(
                    "INSERT INTO public.deleted_users (user_id) VALUES (%s) "
                    "ON CONFLICT (user_id) DO NOTHING",
                    (user_id,),
                )
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudo registrar la baja del usuario.")
        ) from exc


async def prune_expired() -> int:
    """Forget the deletions older than the retention, which no kept backup predates, and return how many."""
    pool = await get_pool()
    try:
        async with pool.connection() as conn:
            async with conn.cursor() as cur:
                await cur.execute(
                    "DELETE FROM public.deleted_users "
                    "WHERE deleted_at < NOW() - make_interval(days => %s)",
                    (RETENTION_DAYS,),
                )
                return cur.rowcount
    except psycopg.Error as exc:
        raise DatabaseError(
            _build_database_error("No se pudieron purgar las bajas de usuarios.")
        ) from exc
