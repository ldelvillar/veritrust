"""Tests of the real SQL of ``app/db/deleted_users.py``: the record of deleted accounts and its lock."""

import asyncio

import pytest

from app.db.deleted_users import UserDeleted, lock_live_user, mark_deleted
from app.db.history import delete_all_user_analyses
from app.schemas.analysis import AnalysisRequest
from tests.db.seed import seed_pending

pytestmark = pytest.mark.db

USER = "user-a"


async def _deleted_at(pool, user_id: str):
    async with pool.connection() as conn:
        cur = await conn.execute(
            "SELECT deleted_at FROM public.deleted_users WHERE user_id = %s",
            (user_id,),
        )
        rows = await cur.fetchall()
    return [row[0] for row in rows]


async def test_marking_a_deletion_twice_keeps_the_first_date(db_pool):
    await mark_deleted(USER)
    first = await _deleted_at(db_pool, USER)

    await mark_deleted(USER)

    assert len(first) == 1
    assert await _deleted_at(db_pool, USER) == first


async def test_only_the_deleted_account_is_refused(db_pool):
    await mark_deleted(USER)

    async with db_pool.connection() as conn, conn.transaction():
        with pytest.raises(UserDeleted):
            await lock_live_user(conn, USER)
    async with db_pool.connection() as conn, conn.transaction():
        await lock_live_user(conn, "user-b")


async def test_a_deletion_waits_for_a_write_in_flight_so_the_erasure_sees_it(
    db_pool,
):
    request = AnalysisRequest(text="La lejía cura la COVID")
    async with db_pool.connection() as conn, conn.transaction():
        await lock_live_user(conn, USER)
        marking = asyncio.create_task(mark_deleted(USER))
        await asyncio.sleep(0.3)
        assert not marking.done()
        await conn.execute(
            "INSERT INTO public.analysis_history "
            "(user_id, source_type, origin, input_text, max_input_chars, status) "
            "VALUES (%s, 'text', 'web', 'texto', 10000, 'pending')",
            (USER,),
        )

    await marking
    deleted = await delete_all_user_analyses(user_id=USER)

    assert deleted.count == 1
    with pytest.raises(UserDeleted):
        await seed_pending(user_id=USER, request=request)
