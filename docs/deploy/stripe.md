# Billing (Stripe)

Pro is sold through Stripe Billing in EUR, IVA included (ADR-0005). The backend only creates Checkout and Customer Portal sessions and receives Stripe's webhook; everything else is set up by hand in the Stripe Dashboard, following this runbook.

## Test mode, live mode and sandboxes

Activate the account first (step 1), then do steps 2 to 6 in its **test mode** for local development (see [Local development](#local-development)), and steps 3 to 7 in **live mode** for production. Step 7's endpoint is the production URL, so it exists only in live mode; locally, the Stripe CLI forwards test events instead.

Use the activated account's test mode, not a separate sandbox: test mode shares the live account's business and public details (the terms URL Checkout needs), while a sandbox is an isolated account without them.

Test-mode and live-mode keys are never mixed: test keys go in local `.env` files, live keys only in the server's `backend/.env` (see [env.md](env.md)).

## API key

`STRIPE_SECRET_KEY` is a **fine-grained key** (**Developers → API keys → Create fine-grained key**), never the account's full-access secret key, so a leaked key can't touch refunds, payouts or anything else. Create one per mode, named for example `veritrust-backend`, with only the permissions the backend uses (`backend/app/core/billing.py`) and everything else set to **None**:

| Resource | Permission | Used for |
| --- | --- | --- |
| Customers | Write | creating the Stripe customer on the first checkout |
| Checkout Sessions | Write | creating a session, and listing and expiring the customer's other open ones |
| Customer portal | Write | opening portal sessions |
| Subscriptions | Write | re-reading the Subscription on every webhook, and cancelling it when the user deletes their account (see [Account deletion](#account-deletion)) |

The webhook signature is checked locally with `STRIPE_WEBHOOK_SECRET`, and prices and tax need no permission, since the backend only passes the price IDs and turns automatic tax on. A missing permission makes the call fail with 503 `BILLING_UNAVAILABLE` and logs `PermissionError`, so check the test-mode key through the local flow before creating the live one.

## Dashboard setup

1. **Account activation**: a Stripe account in Spain with EUR as the default currency, activated with **Activate products** (on the empty **Settings → Business → Business details** tab) as the business type that invoices (**Vendedor** for an autónomo, **Empresa** for a company). The business type and legal identity are hard to change once verified. In the activation's **Public details** step, set the terms of service URL to `https://$APP_DOMAIN/terminos-y-condiciones` and the privacy policy URL to `https://$APP_DOMAIN/politica-de-privacidad`. Checkout asks the customer to accept the terms and refuses to open without that URL, so until activation checkout fails with 503 `BILLING_UNAVAILABLE`. Stripe reviews the website you give it, so keep it up with the product, prices, terms and contact details visible.
2. **Stripe Tax** (**Tax → Settings**): add the Spain registration, set the origin address, and set the product tax code to the SaaS code that matches the audience (check Stripe's list; the personal-use SaaS code is the likely default). Add OSS later, once cross-border EU B2C sales get close to 10,000€/year.
3. **Product**: "VeriTrust Pro" with two prices, 29.00 EUR monthly and 290.00 EUR yearly, both with tax behaviour **inclusive**. Copy the price IDs (`price_…`) into `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY`. A Subscription on any other price never makes a user Pro, so never replace a price ID while Subscriptions still use it: move them to the new price first, or existing subscribers drop to Free.
4. **Customer Portal** (**Settings → Billing → Customer portal**): the backend opens portal sessions through the API with the **Default** configuration, so leave **Enable next generation portal experience** (a preview) off. Click **Activate test link** (**Activate link** in live mode): step 5 sends already-subscribed customers to that no-code login link, and its option stays greyed out until the link is active. Below the preview, set:
   - **Invoices**: show invoice history.
   - **Customer information**: allow updating the billing address, email and tax ID, so invoices stay correct.
   - **Payment methods**: allow updating them.
   - **Cancellations**: allow cancelling **at the end of the billing period**, not immediately; collecting a cancellation reason is optional.
   - **Subscriptions**: allow switching plans and add the **VeriTrust Pro** product with both prices (step 3 must be done first); turn quantity changes off and keep the default proration.
   - **Business information**: set the **Portal header** to "Gestiona tu suscripción, pagos y facturas de VeriTrust Pro" (60 characters at most). Leave **Redirect link** empty, since the backend sends `/app/cuenta` as the return URL on every session, and skip the custom domain (a paid add-on). The legal policy links come from step 1's public details.

   Then **Save changes** (greyed out until something changes).
5. **One subscription per customer** (**Settings → Payments → Checkout and Payment Links → Subscriptions**): turn on **Limit customers to 1 subscription** and choose **customer portal** as the place to manage it (the option is enabled only once step 4 has activated the portal link), so a customer who already pays is sent to the portal instead of a second Checkout. The backend also expires a customer's other open Checkout sessions when it opens a new one.
6. **Billing settings** (**Settings → Billing → Subscriptions and emails**):
   - Under **Manage failed payments → Card payments → Manage**, keep **Smart Retries** on. The default, up to 8 retries within 2 weeks, is the grace period in which a `past_due` user keeps Pro.
   - The **Subscription status** section (shown by **View all settings**, editable only in live mode) must say **When the first payment attempt for a renewal fails: leave the subscription overdue** (`past_due`, still Pro) and **If all retries for a payment fail: cancel the subscription** (which ends `past_due`). Both are the defaults. **Invoice status** doesn't affect the backend.
   - For renewals that need the customer's confirmation (3D Secure), turn on **Customer emails: Send a Stripe-hosted link for customers to confirm their payments when required**. Under its **Subscription status**, set **If a recurring payment is incomplete for 15 days: cancel the subscription**. The default, "leave the subscription overdue", keeps it `past_due`, which counts as Pro, so a customer who never confirms would keep Pro forever. Its **Invoice status** can stay "leave the invoice as-is".
   - Leave **Local payment methods** at their defaults, since Checkout only takes cards.
   - Further down, turn on the customer emails for successful payments, failed payments, upcoming renewals and expiring cards. Stripe sends them in the customer's language, and Checkout runs in Spanish.

   Test mode hides settings shared with live mode (**View all settings** shows them); set those in live mode.
7. **Webhook**, live mode only (**Developers → Workbench → Webhooks → Add destination**): events from **Your account**, API version `2026-09-30.endive` (the version pinned as `STRIPE_API_VERSION` in `backend/app/core/billing.py`), destination type **Webhook endpoint**, URL `https://$API_DOMAIN/billing/webhook`, and these events:
   - `checkout.session.completed`
   - `customer.subscription.created`, `customer.subscription.updated`, `customer.subscription.deleted`
   - `invoice.paid`, `invoice.payment_failed`

   Open the new destination and **Reveal** its **Signing secret**. Copy that `whsec_…` (not the one `stripe listen` prints, which only works locally) into `STRIPE_WEBHOOK_SECRET`. Each endpoint has its own secret, so recreating the destination or rolling its secret means updating `.env` again; otherwise every webhook answers 400 `INVALID_WEBHOOK`. Copy and the live fine-grained key (see [API key](#api-key)) into `STRIPE_SECRET_KEY`.

## Local development

Test mode only (**Workbench → Webhooks → Test with a local listener** shows the same steps):

1. Install the [Stripe CLI](https://docs.stripe.com/stripe-cli) (1.51 or later) and run `stripe login`, approving it in the browser for the activated VeriTrust account in **test mode**, not a sandbox.
2. Fill these values in `backend/.env`; the web process refuses to start until all are set:
   - `STRIPE_SECRET_KEY`: the test-mode fine-grained key (see [API key](#api-key)), never a live one.
   - `STRIPE_WEBHOOK_SECRET`: the `whsec_…` printed by `stripe listen --print-secret`, which doesn't need the backend running and stays the same on this machine.
   - `STRIPE_PRICE_PRO_MONTHLY` and `STRIPE_PRICE_PRO_YEARLY`: the test-mode price IDs from step 3.
   - `CLERK_WEBHOOK_SECRET`: a placeholder is enough locally (see [Account deletion](#account-deletion)).

   Also check that `APP_BASE_URL` is `http://localhost:3000`: Checkout and the portal send the customer back there, so a production value lands them on the live site.
3. Start the stack with `docker compose up -d --build`; the backend needs Postgres, Redis and the migrations, and compose publishes it on port 8000. After changing `backend/.env`, run `docker compose up -d` again so the backend is recreated with the new values.
4. In a second terminal, keep `stripe listen --all-snapshot --forward-to localhost:8000/billing/webhook` running. It forwards test-mode events as snapshot events, the format the webhook verifies, and the webhook ignores the types it doesn't handle. Events that arrive while the backend is down fail, and Stripe doesn't redeliver them to the CLI; `docker compose logs -f backend` shows how each one was handled.
5. Test a subscription by going through Checkout with the card `4242 4242 4242 4242`. Until the app's plan card exists (PR 3 of [the billing plan](../plans/billing-free-pro.md)), open Checkout by calling `POST /billing/checkout` with `{"interval": "month"}` and a signed-in user's token, then open the `url` it returns. `stripe trigger` creates customers that belong to no VeriTrust user, so the webhook logs and skips their subscriptions.

## Account deletion

Users delete their account through Clerk, so Clerk tells the backend with a webhook: on `user.deleted`, the backend cancels the user's Stripe Subscription at once, with no proration or refund, deletes their rows in `billing_customers`, `subscriptions` and `usage_events`, then deletes all their analyses (feedback included) and aborts their pending Runs, like `DELETE /history`. The Stripe customer and its invoices stay in Stripe, since tax law requires keeping invoices. Without the webhook, a deleted user keeps being charged and their analyses stay in the database, which the privacy policy promises they don't.

1. Give the fine-grained key of each mode **Subscriptions: Write** (see [API key](#api-key)); with only Read, cancelling fails and the webhook answers 503, so Clerk retries it.
2. In the Clerk Dashboard of the **Production** instance, open **Configure → Webhooks → Add Endpoint**: URL `https://$API_DOMAIN/webhooks/clerk`, subscribed to the `user.deleted` event only.
3. Open the new endpoint and copy its **Signing Secret** (`whsec_…`) into `CLERK_WEBHOOK_SECRET` in the server's `backend/.env` (see [env.md](env.md)). A wrong secret makes every delivery answer 400 `INVALID_WEBHOOK`; the endpoint's **Logs** tab in Clerk lists failed deliveries and can resend them.

Locally, the Clerk development instance can't reach `localhost`, so account deletion doesn't cancel or delete anything unless you expose the backend through a tunnel and add a development endpoint the same way. `CLERK_WEBHOOK_SECRET` must still be set for the web process to start: copy the secret of a development endpoint, or use any `whsec_` value with valid base64 after the prefix, such as `whsec_ZGV2ZWxvcG1lbnQ=`.

## Operations

The four `STRIPE_*` variables and `CLERK_WEBHOOK_SECRET` are required by the web process: without them the backend refuses to start and `/healthz` answers 503. The worker doesn't need them.

The webhook answers 400 to a request with a bad signature, and 5xx when handling fails, so Stripe retries it (**Developers → Workbench → Webhooks → the endpoint** lists failed deliveries and can resend them). The backend logs each event's id and type, never its payload.

To check a user's Plan by hand:

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml exec postgres \
  psql -U veritrust -d veritrust -c \
  "SELECT status, price_id, current_period_end, cancel_at FROM subscriptions WHERE user_id = 'user_…'"
```
