# Side Hustle launch pack

Prepared 29 September 2026. **Stage: QuietBatch's R3,500 offer, public seller disclosures and R0 Cloudflare Pages hosting approved; free hosting account, officer registration and new manual review pending. Actual revenue: R0. Incremental cash spent on preparation: R0.** The confirmed contact is quietbatchreports@gmail.com. No company has been registered, offer published, customer message sent or bank/SARS connection activated.

The owner confirmed South African tax residency, no existing business or VAT registration, an R0 upfront budget, and at most three hours a week with a preference for automation. The owner is Theunis Christian Botha and now confirms no employer approval is required for work outside office hours. This supersedes the earlier manager-clearance requirement; the contract has not been independently reviewed. The business serves South Africa remotely. The owner chose EFT to an FNB personal account, whose specific terms and fees still need checking. Publication, communications, seller disclosures and payment/tax setup remain separate launch steps.

## Start here

- `business/PLAN.md`: selected business, test prices, workload, validation and cost rules.
- `business/LAUNCH-APPROVAL.md`: the exact launch proposal and information needed.
- `business/IDENTITY-AND-EMAIL.md`: the approved QuietBatch name, confirmed Gmail address and draft signature.
- `business/MANAGER-CLEARANCE.md`: the superseded earlier draft, retained as history.
- `business/FIRST-CUSTOMER.md`: the first sales post, referral message and qualification flow.
- `business/PAYMENTS-AND-LAUNCH.md`: EFT setup, seller disclosures and the free information-officer registration step.
- `website/`: the customer page, working synthetic sample and locally rendered seller details, awaiting disclosure and public hosting approval. Preview at `http://127.0.0.1:8766/` while its server runs. The review ZIP contains the owner's address, precise coordinates and telephone; keep it private until publication is approved.
- `business/INFORMATION-OFFICER.md`: the next registration step after the owner's confirmed regulator-account creation.
- `business/TAX-AND-RECORDS.md`: current SARS sources and outstanding tax decisions.
- `business/SALES-AND-DELIVERY.md`: proposed scope, customer discovery and delivery checklist.
- `business/templates/`: quote, invoice and proposed customer terms for review.
- `demo/output/report.html`: working synthetic example of the first service.

## Monitor

Run `./start-dashboard.ps1` from PowerShell in this folder, then open `http://127.0.0.1:8765/`. Keep the process running while using the monitor; Ctrl+C stops it. It runs on an existing bundled Python runtime with no dependency downloads.

The dashboard records payments, refunds, gross operating costs, income-tax payments and owner transfers separately. It shows cash surplus before income tax, a user-selected planning reserve, records per venture, unearned pipeline values, budget alerts and a preliminary VAT turnover warning. It refreshes while open. Records live in `data/sidehustle.sqlite3`, not browser storage. There is no automatic bank import or payment-provider reconciliation.

Cash surplus is a management metric, not taxable profit or fully accrued accounting profit. Customer deposits may still create delivery/refund obligations. Unpaid invoices and any other business activities must be reviewed separately. Default ventures are offer categories belonging to **one seller**, not registered companies. Use separate databases for distinct legal taxpayers.

Entries use integer cents. A unique reference prevents duplicate recording; refunds link to the original payment and cannot exceed it. Corrections preserve the original record and a reason. Evidence fields store filenames, not attachments. Keep the actual evidence files with the records. `data/launch-profile.json` separately records the owner's approvals and outstanding launch steps; back it up with the database. The dashboard reads it for launch status and omits the owner's legal identity from the report. Editing a status file is not itself evidence of external manager approval.

Exports: the CSV ledger includes active and corrected records; the JSON export contains all record tables and an audit trail. The CSV encodes amounts as cents. Neither export is a SARS return. There is no in-app restore/import. To back up the operational database, stop the server and copy `data/sidehustle.sqlite3` and the evidence folder to another owner-controlled location in South Africa. Keep multiple dated copies. To recover, stop the server, preserve the current database, and restore a known-good database copy before restarting. A JSON export is an extra portable record, not a replacement for tested database backups.

## MCP monitor

`dashboard/mcp_server.py` is a minimal read-only stdio MCP server with `business_summary` and `compliance_review`. It opens SQLite in read-only mode. It cannot add records, spend money, contact customers, register businesses, or file tax. It is implemented and smoke-tested locally; it has not been installed in an MCP client or remotely hosted. Protocol references: [MCP lifecycle](https://modelcontextprotocol.io/specification/2025-11-25/basic/lifecycle) and [tools](https://modelcontextprotocol.io/specification/2025-11-25/server/tools).

A client can launch Python with the absolute `dashboard/mcp_server.py` path as its argument. `mcp-client.example.json` records those launch details without changing any client configuration. Client-specific installation needs review in a later step. The browser also exposes a read-only reporting tool when WebMCP is supported.

## Verification

Run `python -m unittest discover -s tests -v` using the bundled Python runtime or another Python 3.10+ installation. Run `node --check dashboard/dist/app.js` for browser-script syntax. Tests use temporary databases and do not add fictional sales to the real ledger.

This is a local tool, not a hosted production accounting system. It listens only on 127.0.0.1, validates local request origins and protects writes with a session token. Do not expose its port publicly. Any future hosted dashboard needs authentication, access controls, secure storage and an approved cost model before migration.
