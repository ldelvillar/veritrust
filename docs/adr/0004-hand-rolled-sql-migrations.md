---
status: accepted
---

# Schema changes are ordered SQL files applied by a small in-repo runner, not a migration framework

The schema used to live in one `init.sql` that Postgres ran only on an empty volume, and the DB tests applied it to a fresh database. Once deploys became automatic (CI green on `main` → `deploy.yml`), merging a schema change would ship code that queried columns the live database never got. Now the schema is the ordered files in `backend/db/migrations/` (the old `init.sql` is `0001_baseline.sql`), applied by `app/db/migrate.py`. The runner holds a Postgres advisory lock, applies each pending file in its own transaction, records it in `schema_migrations` with a checksum, and refuses to run if an applied file was edited or deleted. Compose runs it as a one-shot `migrate` service that the API and worker wait on (`service_completed_successfully`), and `tests/db` builds its database through the same function, so CI exercises the exact code prod runs. Migrations only roll forward; the deploy takes a `pg_dump` before `up` instead of relying on down scripts.

## Considered Options

- **Alembic**: rejected. Its main feature, autogenerating migrations from model diffs, needs SQLAlchemy models, and the app uses raw psycopg3 with no ORM. It would add SQLAlchemy only to wrap `op.execute("ALTER TABLE …")`.
- **An external SQL-file tool (dbmate, Flyway, sqitch)**: rejected for now. The SQL files would be the same, but prod and tests would apply them through different code (a binary in the image and in CI, versus Python in the test fixture), and the tool would read the DSN outside `Settings`. Every schema change so far (new columns, wider CHECKs, indexes, one rename) runs inside a transaction, so the extra safety these tools offer is already covered by Postgres. Revisit if several people write migrations on parallel branches (numbering conflicts), or if changes need zero-downtime expand/contract tooling; the `.sql` files carry over unchanged.
- **Running migrations in the API/worker startup**: rejected. Both processes start from the same image at once, and the worker's orphan reaper queries the table every minute; a separate step that both depend on keeps them from ever running against a half-migrated schema.
