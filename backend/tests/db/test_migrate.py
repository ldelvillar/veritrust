"""Pruebas de ``app/db/migrate.py`` contra un PostgreSQL real, en una base vacía por prueba."""

import uuid
from concurrent.futures import ThreadPoolExecutor

import psycopg
import pytest
from psycopg.conninfo import make_conninfo

from app.core.config import get_settings
from app.db.migrate import MigrationError, apply_migrations, load_migrations, main

pytestmark = pytest.mark.db


@pytest.fixture
def empty_dsn(postgres_dsn):
    """Crea una base de datos vacía para la prueba y la borra al terminar."""
    name = f"migrate_{uuid.uuid4().hex}"
    with psycopg.connect(postgres_dsn, autocommit=True) as admin:
        admin.execute(f'CREATE DATABASE "{name}"')
    try:
        yield make_conninfo(postgres_dsn, dbname=name)
    finally:
        with psycopg.connect(postgres_dsn, autocommit=True) as admin:
            admin.execute(f'DROP DATABASE "{name}" WITH (FORCE)')


def _write(directory, name, sql):
    (directory / name).write_text(sql, encoding="utf-8")


def _tables(dsn):
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT tablename FROM pg_tables WHERE schemaname = 'public'"
        ).fetchall()
    return {row[0] for row in rows}


def _recorded(dsn):
    with psycopg.connect(dsn) as conn:
        rows = conn.execute(
            "SELECT version FROM public.schema_migrations ORDER BY version"
        ).fetchall()
    return [row[0] for row in rows]


def test_applies_pending_migrations_in_name_order_and_records_them(empty_dsn, tmp_path):
    _write(tmp_path, "0002_child.sql", "CREATE TABLE child (p INT REFERENCES parent);")
    _write(tmp_path, "0001_parent.sql", "CREATE TABLE parent (id INT PRIMARY KEY);")

    assert apply_migrations(empty_dsn, tmp_path) == ["0001_parent", "0002_child"]
    assert _recorded(empty_dsn) == ["0001_parent", "0002_child"]
    assert {"parent", "child"} <= _tables(empty_dsn)


def test_second_run_applies_only_new_files(empty_dsn, tmp_path):
    _write(tmp_path, "0001_a.sql", "CREATE TABLE a (id INT);")
    apply_migrations(empty_dsn, tmp_path)

    assert apply_migrations(empty_dsn, tmp_path) == []

    _write(tmp_path, "0002_b.sql", "CREATE TABLE b (id INT);")
    assert apply_migrations(empty_dsn, tmp_path) == ["0002_b"]


def test_failing_migration_rolls_back_entirely_and_stops_the_run(empty_dsn, tmp_path):
    _write(tmp_path, "0001_ok.sql", "CREATE TABLE ok (id INT);")
    _write(
        tmp_path,
        "0002_broken.sql",
        "CREATE TABLE half (id INT); SELECT * FROM no_such_table;",
    )
    _write(tmp_path, "0003_later.sql", "CREATE TABLE later (id INT);")

    with pytest.raises(psycopg.errors.UndefinedTable):
        apply_migrations(empty_dsn, tmp_path)

    assert _recorded(empty_dsn) == ["0001_ok"]
    assert "half" not in _tables(empty_dsn)
    assert "later" not in _tables(empty_dsn)


def test_refuses_when_an_applied_migration_was_edited(empty_dsn, tmp_path):
    _write(tmp_path, "0001_a.sql", "CREATE TABLE a (id INT);")
    apply_migrations(empty_dsn, tmp_path)
    _write(tmp_path, "0001_a.sql", "CREATE TABLE a (id BIGINT);")
    _write(tmp_path, "0002_b.sql", "CREATE TABLE b (id INT);")

    with pytest.raises(MigrationError, match="0001_a ha cambiado"):
        apply_migrations(empty_dsn, tmp_path)
    assert _recorded(empty_dsn) == ["0001_a"]


def test_refuses_when_an_applied_migration_was_deleted(empty_dsn, tmp_path):
    _write(tmp_path, "0001_a.sql", "CREATE TABLE a (id INT);")
    apply_migrations(empty_dsn, tmp_path)
    (tmp_path / "0001_a.sql").unlink()

    with pytest.raises(MigrationError, match="0001_a ya no existe"):
        apply_migrations(empty_dsn, tmp_path)


def test_concurrent_runs_apply_each_migration_once(empty_dsn, tmp_path):
    # Sin IF NOT EXISTS: una segunda aplicación fallaría por tabla duplicada.
    _write(
        tmp_path, "0001_slow.sql", "SELECT pg_sleep(0.5); CREATE TABLE once (id INT);"
    )

    with ThreadPoolExecutor(max_workers=2) as pool:
        runs = [pool.submit(apply_migrations, empty_dsn, tmp_path) for _ in range(2)]
        results = sorted(run.result() for run in runs)

    assert results == [[], ["0001_slow"]]
    assert _recorded(empty_dsn) == ["0001_slow"]


def test_real_migrations_build_the_schema_the_app_queries(empty_dsn):
    applied = apply_migrations(empty_dsn)

    assert applied == [migration.version for migration in load_migrations()]
    assert {"analysis_history", "analysis_feedback"} <= _tables(empty_dsn)


# Restricciones de verdict previas a 'mixed': (tabla, nombre, condición).
_PRE_MIXED_CHECKS = [
    (
        "analysis_history",
        "analysis_history_verdict_check",
        "verdict IS NULL OR verdict IN ('real', 'fake', 'uncertain')",
    ),
    (
        "analysis_feedback",
        "analysis_feedback_suggested_verdict_check",
        "suggested_verdict IS NULL OR suggested_verdict IN ('real', 'fake', 'uncertain')",
    ),
    (
        "analysis_feedback",
        "analysis_feedback_verdict_snapshot_check",
        "verdict_snapshot IN ('real', 'fake', 'uncertain')",
    ),
]


def test_migrations_let_a_pre_mixed_database_store_mixed_verdicts(empty_dsn, tmp_path):
    baseline = load_migrations()[0]
    _write(tmp_path, f"{baseline.version}.sql", baseline.sql)
    apply_migrations(empty_dsn, tmp_path)
    # El baseline no toca tablas existentes, así que una base antigua conserva estas restricciones.
    with psycopg.connect(empty_dsn) as conn:
        for table, name, condition in _PRE_MIXED_CHECKS:
            conn.execute(
                f"ALTER TABLE {table} DROP CONSTRAINT {name}, "
                f"ADD CONSTRAINT {name} CHECK ({condition})"
            )

    assert apply_migrations(empty_dsn) == [m.version for m in load_migrations()[1:]]

    with psycopg.connect(empty_dsn) as conn:
        analysis_id = conn.execute(
            "INSERT INTO analysis_history (user_id, source_type, verdict, max_input_chars) "
            "VALUES ('u', 'text', 'mixed', 10000) RETURNING id"
        ).fetchone()[0]
        conn.execute(
            "INSERT INTO analysis_feedback "
            "(analysis_id, user_id, is_correct, suggested_verdict, verdict_snapshot) "
            "VALUES (%s, 'u', false, 'mixed', 'mixed')",
            (analysis_id,),
        )


def test_billing_enforcement_gives_older_analyses_the_schema_maximum(
    empty_dsn, tmp_path
):
    before = [m for m in load_migrations() if m.version < "0004"]
    for migration in before:
        _write(tmp_path, f"{migration.version}.sql", migration.sql)
    apply_migrations(empty_dsn, tmp_path)
    with psycopg.connect(empty_dsn) as conn:
        conn.execute(
            "INSERT INTO analysis_history (user_id, source_type) VALUES ('u', 'text')"
        )

    apply_migrations(empty_dsn)

    with psycopg.connect(empty_dsn) as conn:
        assert conn.execute(
            "SELECT max_input_chars FROM analysis_history"
        ).fetchall() == [(10000,)]
        with pytest.raises(psycopg.errors.NotNullViolation):
            conn.execute(
                "INSERT INTO analysis_history (user_id, source_type) VALUES ('u', 'text')"
            )


@pytest.fixture
def database_url(monkeypatch):
    """Fija DATABASE_URL para ``main`` y descarta la configuración cacheada."""

    def configure(value):
        monkeypatch.setenv("DATABASE_URL", value)
        get_settings.cache_clear()

    yield configure
    get_settings.cache_clear()


def test_main_migrates_the_configured_database(empty_dsn, database_url):
    database_url(empty_dsn)

    main()

    assert _recorded(empty_dsn) == [m.version for m in load_migrations()]


def test_main_exits_without_database_url(database_url):
    database_url("")

    with pytest.raises(SystemExit, match="DATABASE_URL"):
        main()
