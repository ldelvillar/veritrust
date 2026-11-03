"""Record of accounts deleted in Clerk, which refuses the writes that would land for them afterwards."""

from __future__ import annotations

import psycopg

from app.db.pool import DatabaseError, _build_database_error, get_pool

# Serialises a user's openings, Usage writes and deletion until their transaction ends.
_LOCK_USER = "SELECT pg_advisory_xact_lock(hashtext('allowance:' || %s))"


class UserDeleted(Exception):
    """The user deleted their account, and nothing was written."""


async def lock_live_user(conn: psycopg.AsyncConnection, user_id: str) -> None:
    """Lock the user's writes for the transaction and raise UserDeleted if their account is gone."""
    async with conn.cursor() as cur:
        await cur.execute(_LOCK_USER, (user_id,))
        # Read after the lock, so a deletion that committed while this waited is seen.
        await cur.execute(
            "SELECT 1 FROM public.deleted_users WHERE user_id = %s", (user_id,)
        )
        if await cur.fetchone() is not None:
            raise UserDeleted(user_id)


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
