# Connecting real businesses later

This build makes no external publishing requests, provisions no hosting and spends no money. External channels are recorded as prepared demo deliveries. Use this guide when a client is ready to connect accounts and approve a hosting arrangement.

## Social publishing

Each platform needs its own supported account connection and publishing permissions. Add a provider adapter behind the existing delivery workflow, with clear functions such as `prepare_delivery`, `publish_delivery` and `fetch_delivery_status`.

Keep provider credentials on the server, outside browser JavaScript and company exports. Record a provider's response ID and delivery outcome. A queued request should become published only when the provider confirms it. A failed request should keep a useful, visible error and be safe to retry without duplicates.

The shared post editor can remain convenient while allowing platform-specific previews, image requirements and copy limits. The current text-only preparation should not be presented as universal support for every platform feature.

## Paid advertising

Campaign preparation is separate from spending. A connected version needs explicit selection of the ad account, audience, assets, currency, budget, dates and spending limit, followed by a reviewable launch action.

Store the provider campaign ID and read actual status and results from that provider. Keep planned budget separate from actual spend. Website source codes help attribute enquiries but are not a substitute for provider reporting or a reliable guarantee of attribution.

## Bookings and notifications

The local database is currently the appointment source of truth. An email or calendar connection should send confirmations only after a reservation is committed. Use a durable queue and retries so a failed notification cannot lose the booking or create it twice.

Add explicit resources for multiple staff members or locations. If a calendar provider becomes another source of availability, define how both systems reconcile cancellations and changes.

## Hosting and access

Before taking real customer data online, add authenticated users, company membership checks, roles, HTTPS, secure sessions and a recovery process. Decide who owns the domain, hosting account, connected social accounts and backups. The current local CSRF token and company selector are not a hosted login system.

Keep public pages separate from dashboard permissions. A visitor should be able to submit an enquiry or reservation, while only authorized company users can read lead details, export data, edit content or run connected campaigns.

Select hosting only after the user approves cost and deployment. The current Python/SQLite arrangement is easy to demonstrate; its production suitability depends on traffic, concurrent writers, backups and availability requirements. A shared hosted product will likely need a managed database, a background worker for provider jobs and a deliberate migration plan.

## A realistic release sequence

1. Finish the client-specific company settings, website copy, intake fields and workflow.
2. Agree on access, retention, ownership and cost with the client.
3. Add authentication and tenant membership, migrations and automated backup/restore checks.
4. Connect one real provider and verify permission, status, failure and retry handling.
5. Review the complete workflow with the client, then deploy after approval.
6. Add further channels using the same delivery interface and verified outcomes.

The current demo is designed to make the workflow tangible before those paid services and account connections are chosen.
