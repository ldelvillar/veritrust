---
status: accepted
---

# Plans are billed through Stripe and decided from our own Postgres tables

Pro is sold in EUR with Spanish IVA included, and its card payments need 3DS, so we bill through Stripe Billing with Stripe Tax: hosted Checkout to subscribe, the Customer Portal to cancel, switch interval, change card and download invoices. A user's Plan is decided on each gated request from our own `subscriptions` table, looked up by Clerk `user_id`. That way it is the same for web sessions, MCP OAuth tokens and API keys, and a change takes effect on the next request. Only the Stripe webhook writes that table. It never trusts the event's embedded object or the order events arrive in: it re-fetches the Subscription from Stripe and replaces the row. An event is recorded as processed only after it has been handled, so a failure answers 5xx and Stripe retries it.

Usage is an append-only ledger (`usage_events`), not a count of Analyses. A Run's unit is written in the same transaction that marks the Analysis done, so failed Runs consume nothing. The first done Run of an Analysis counts as `analysis`, each later one as `reanalysis`, and a Retry adds nothing of its own. Its foreign key is `ON DELETE SET NULL`, so deleting Analyses never refunds units. The Allowance check (done Runs this month plus pending Analyses, under a per-user advisory lock) runs inside `analysis_transitions`, in the same transaction as the row it opens. ADR-0001 still holds: the lifecycle module stays the only writer of `status`, and of the Usage of Runs. An evidence search leaves no Analysis, so the worker records its unit when the search succeeds. A Run that completes after midnight on the 1st counts in the new month.

## Considered Options

- **Clerk Billing**: rejected. It only charges in USD, collects no VAT and has no 3DS, so it cannot sell to Spanish consumers.
- **The Plan in Clerk user metadata**: rejected. It would sync a second copy of what Stripe already tells us, take effect only once a new session token is issued, and API keys carry no session claims.
- **Counting Usage from `analysis_history`**: rejected. Deleting an Analysis or Reanalyzing it would change past Usage, and evidence searches leave no Analysis row.
