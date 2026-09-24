---
status: accepted
---

# The Analysis lifecycle is the only writer of status and stage, tested against real Postgres

An Analysis's `status` and `stage` used to be written from the web routes, the MCP server, the enqueue helper and the worker, each with its own guards (some writes had none). Now every transition — submit, Retry, Reanalyze, stage progress, complete, fail and reaping an Orphaned analysis — goes through the Analysis lifecycle module, as a single guarded update that names the status it moves from; an architecture test keeps other code in `app/` from writing those columns. Features that only *depend* on status (sharing, feedback) read it but must never set it; a new transition belongs in the lifecycle module.

## Considered Options

- **A store port with an in-memory adapter** (so the lifecycle suite runs without Docker): rejected. The port would mirror the SQL statements one-to-one, and the in-memory adapter would re-implement every status guard and drift from the real ones. The suite runs against real Postgres (`tests/db`); the few error-code cases that need a specific statement to fail use a fault-injecting pool inside the module's own tests.
- **An attempt counter on each Run** (to stop a write from an earlier Run landing on a later one): rejected for now. Runs cannot overlap: the reaper only fails rows with no live job, and Retry/Reanalyze refuse while the previous job is still live. Revisit if anything starts running an Analysis outside the queue.
