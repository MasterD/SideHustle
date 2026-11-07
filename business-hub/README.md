# Launchpad — a local business workspace

Launchpad is a working foundation for a business website, enquiries, bookings, social content and campaign preparation. The fictional starter business is **Juniper Studio**, a plant styling and workshop company. It gives you something to demonstrate without tying the product to a mechanic or insurance business.

The dashboard and public website run on your own computer. Python and SQLite provide the server and storage; ordinary HTML, CSS and JavaScript provide the interface. There are no package subscriptions, hosting fees, API keys or paid services in this version.

## Start it

Open PowerShell in this folder and use the launcher:

```powershell
.\run.ps1
```

The launcher finds an installed Python or the bundled Codex Python runtime when available. If you already have Python 3.10 or newer installed, you can start it directly:

```powershell
python server.py --port 8787
```

Open these addresses in a browser:

- Dashboard: <http://127.0.0.1:8787/>
- Juniper Studio website: <http://127.0.0.1:8787/site/juniper-studio>
- Quote Lab motor-insurance proof of concept: <http://127.0.0.1:8787/insurance>

Leave the terminal open while you use the app. Press `Ctrl+C` there to stop it. The server listens on the loopback address, so it is accessible from your computer rather than being an internet hosting service.

## Quote Lab insurance demo

Quote Lab adds a local vehicle, extras, driver/use and cover intake with an explained calculation, missing-answer checks, JSON download and printable report. **Your Polo GTI** uses your confirmed 2026 model, approximately R620,000 value, white colour, included factory sunroof and no modifications; unanswered driver details remain unknown. **What-if scenario** uses fictional choices.

The R2,000 reference and all numerical factors are fabricated demonstration assumptions. This is an uncalibrated proof of concept, not a live insurer quote or proof of more accurate premiums. Included extras are not charged twice; unpriced items and provider checks remain visible. Calculations do not create leads or write to the database. Read [the insurance demo and maintenance guide](docs/INSURANCE_POC.md) for a walkthrough and the evidence needed before claiming real accuracy.

Preview screenshots: [desktop intake and comparison](docs/insurance-preview.jpg), [complete page](docs/insurance-full-preview.jpg), and [phone intake](docs/insurance-mobile-preview.jpg).

## What you can demonstrate

| Area | What works now |
| --- | --- |
| Overview | Metrics calculated from saved leads and bookings, recent activity and campaign preparation. |
| Leads | Search and manage enquiries; record qualification, outcomes, values and an estimated commission rate. |
| Bookings | Visitors choose available times; overlapping reservations are rejected; the dashboard manages appointment status. |
| Services | Set the services, prices and appointment durations offered by the business. |
| Content | Write one post for selected channels, publish it to the local website and prepare deliveries for social channels. |
| Campaigns | Prepare a reusable campaign, its content and a source code for attributing website enquiries or bookings. |
| Website | Edit a draft, publish it, and see the published version on the public website. |
| Company settings | Change contact details, business hours, currency and other company details. |
| Separate companies | Create another company with its own data and website, then switch between companies. |
| Export | Download the current company's saved records as JSON. |

### A useful first demo

1. Open the dashboard and review the seeded Juniper Studio example records. The **Local demo** label means this is a local demonstration with synthetic starter data.
2. Open the public website in another tab. Submit an enquiry or request an appointment; return to the dashboard to see the saved lead and booking.
3. Edit the website draft. Refresh the public website before publishing, then publish the draft and refresh again to demonstrate the difference.
4. Write a post and select the website plus a social channel. Use **Prepare & publish**. The website changes immediately; the social delivery says **Demo draft ready** (`demo_ready` in the API).
5. Create a campaign and run its preparation. Use the website link with `?campaign=SOURCE_CODE`, submit an enquiry and inspect its attribution in Leads.
6. Mark a lead won and set its value and commission rate to show how conversion tracking changes the overview.

## What a “run campaign” button means here

The button prepares the campaign, creates its associated content, publishes to the local website when selected and records demo deliveries for the selected social channels. Repeating the action reuses the prepared campaign instead of creating duplicate content.

It does **not** buy advertising or publish to external social accounts. Facebook, Instagram and LinkedIn deliveries are locally prepared records, not proof of delivery. The planned budget is a planning field; it is not a charge. There are no invented impressions, clicks or advertising results.

A won lead's conversion value is an amount you entered. Estimated commission is calculated from that value and its saved commission rate. Neither figure establishes an insurance sale, a contractual entitlement, an invoice or a payment received.

Editing a published post saves a draft while the website keeps its previously published copy. Use **Prepare & publish** again to replace it. If you remove the website from the selected channels and publish again, that post is removed from the website.

## Your data and backups

The app creates `data/business-hub.sqlite3` on first start and seeds its fictional example data only when the database is new. Changes survive server and browser restarts. Keep that file private: it contains the contact details and enquiries you enter.

The dashboard's export provides a readable JSON copy of one company's records. For a complete backup, use the restore-point helper described below: it captures a consistent SQLite copy even while the server is running. For a manual offline backup, stop the server and copy the **whole `data/` folder**, including any accompanying journal files. Keep a separate copy of the current data before restoring an older backup.

Do not commit the database or customer exports to a source repository. The provided `.gitignore` excludes the local database directory.

### Restore points and resuming work

[WORK_STATE.md](WORK_STATE.md) records the implementation state, validation and next steps so another conversation can resume after a context or token limit. Share that file with the next conversation before making further changes.

Create a named restore point from this folder:

```powershell
.\save-restore-point.ps1 -Label custom
```

The shortcut finds an available Python runtime. With an installed Python you can also run `python tools/checkpoint.py --label custom`. Restore points are timestamped ZIP files under `.restore-points/` and include the source plus a consistent database backup when a database exists. To restore, extract an archive into a **new folder**, inspect its state and start it there. Keep your current folder until you have confirmed the restored copy is the one you want.

## How the code is arranged

```text
business-hub/
  server.py             Server startup and command-line options
  run.ps1               PowerShell start shortcut
  save-restore-point.ps1 PowerShell restore-point shortcut
  hub/
    storage.py          Database schema and transaction handling
    validation.py       Reusable input validation
    application.py      Company-scoped business rules and API dispatch
    routes.py           HTTP requests, local security and static files
    insurance.py        Stateless motor-intake validation and demo arithmetic
    insurance_rules.json Readable, versioned demo assumptions
  static/
    index.html          Dashboard page
    app.js              Dashboard behaviour and API calls
    styles.css          Dashboard appearance
    website.html        Public website page
    website.js          Public enquiry and booking behaviour
    website.css         Public website appearance
    insurance.html      Quote Lab intake and report page
    insurance.js        Quote Lab presets, calculation and export
    insurance.css       Quote Lab responsive and print presentation
  tools/checkpoint.py   Source and database restore-point helper
  WORK_STATE.md         Handoff note for continuing the work
  tests/                Standard-library integration tests
  docs/                 Maintenance and extension notes
  data/                 Local SQLite database, created on first run
```

Start with [the architecture guide](docs/ARCHITECTURE.md) to understand a request from browser to database. Use [the customization guide](docs/CUSTOMIZATION.md) when creating the mechanic and insurance versions. [The integration plan](docs/INTEGRATIONS.md) explains what must be added before connecting real social accounts, advertising or hosting.

Run the checks from this folder:

```powershell
python -m unittest discover -s tests -v
```

The tests use temporary databases, so they do not change your demo records.

## The current boundary

Each company's records are scoped separately in server queries, which makes the structure reusable. This version does not provide user accounts, roles or production access control. Someone who can use this local dashboard can switch between its companies. Company separation is a foundation for future development, not a complete hosted SaaS security system.

The server checks request hosts, request origins, write tokens and input, limits public submissions, and reserves bookings atomically. Those measures support a local demo. Before using the product on the internet with real clients, implement authenticated company membership, HTTPS, operational backups and the real provider integrations described in the integration plan.
