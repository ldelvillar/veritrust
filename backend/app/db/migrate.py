"""Apply the pending SQL migrations of ``db/migrations`` in order."""

from __future__ import annotations

import hashlib
import logging
from dataclasses import dataclass
from pathlib import Path

import psycopg

from app.core.config import get_settings
from app.core.logging import configure_logging

logger = logging.getLogger(__name__)

MIGRATIONS_DIR = Path(__file__).resolve().parents[2] / "db" / "migrations"

# Advisory lock key that serialises concurrent migrator runs.
_LOCK_KEY = 7_416_235_901


class MigrationError(RuntimeError):
    """An applied migration does not match the files in the directory."""


@dataclass(frozen=True)
class Migration:
    """A migration file with its version (name without extension), SQL and checksum."""

    version: str
    sql: str
    checksum: str


def load_migrations(directory: Path = MIGRATIONS_DIR) -> list[Migration]:
    """Read the directory's ``*.sql`` files in name order."""
    migrations = []
    for path in sorted(directory.glob("*.sql")):
        sql = path.read_text(encoding="utf-8")
        checksum = hashlib.sha256(sql.encode("utf-8")).hexdigest()
        migrations.append(Migration(path.stem, sql, checksum))
    return migrations


def apply_migrations(conninfo: str, directory: Path = MIGRATIONS_DIR) -> list[str]:
    """Apply each pending migration in its own transaction and return their versions."""
    migrations = load_migrations(directory)
    with psycopg.connect(conninfo, autocommit=True) as conn:
        # Session lock, released only when the connection closes.
        conn.execute("SELECT pg_advisory_lock(%s)", (_LOCK_KEY,))
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS public.schema_migrations (
                version    TEXT PRIMARY KEY,
                checksum   TEXT NOT NULL,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
            )
            """
        )
        rows = conn.execute(
            "SELECT version, checksum FROM public.schema_migrations"
        ).fetchall()
        applied = {version: checksum for version, checksum in rows}

        by_version = {migration.version: migration for migration in migrations}
        for version, checksum in sorted(applied.items()):
            migration = by_version.get(version)
            if migration is None:
                raise MigrationError(f"La migración aplicada {version} ya no existe.")
            if migration.checksum != checksum:
                raise MigrationError(
                    f"La migración aplicada {version} ha cambiado; crea una nueva."
                )

        newly_applied = []
        for migration in migrations:
            if migration.version in applied:
                continue
            with conn.transaction():
                conn.execute(migration.sql)
                conn.execute(
                    "INSERT INTO public.schema_migrations (version, checksum) "
                    "VALUES (%s, %s)",
                    (migration.version, migration.checksum),
                )
            logger.info("Migración aplicada: %s", migration.version)
            newly_applied.append(migration.version)
    return newly_applied


def main() -> None:
    """Apply the pending migrations against DATABASE_URL."""
    configure_logging()
    database_url = get_settings().database_url.strip()
    if not database_url:
        raise SystemExit("No se encontro la variable de entorno DATABASE_URL.")
    newly_applied = apply_migrations(database_url)
    logger.info("Esquema al día; migraciones nuevas: %d", len(newly_applied))


if __name__ == "__main__":
    main()
