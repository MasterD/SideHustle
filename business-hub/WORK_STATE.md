# Continue from here

Last updated: 14 October 2026. Project: reusable local Business Hub, dashboard named Launchpad, demo company Juniper Studio (plant styling / workshops). No spending, no hosting, no real account connections, no purchases.

## Current milestone: insurance intake proof of concept complete and verified

On 14 October 2026 the user asked for a small car-insurance quoting proof of concept to show an insurance friend. The intended benefit is more complete intake and clearer estimate assumptions before a real insurer quote. The user hit a usage limit, added tokens, and explicitly asked to continue and keep creating restore points. No purchase by the agent is authorized or needed.

Confirmed example vehicle: **2026 Volkswagen Polo GTI, approximately R620,000, white, factory sunroof, no modifications. The sunroof is already included in R620,000.** Do not add its value twice. Separate sunroof price, driver, claims, location, usage, cover and excess are unknown. Do not invent these as user facts.

Plan: add local `/insurance` Quote Lab page and stateless demo calculation APIs. Rich intake includes extras/included value, paint/colour, modifications, driver/use/security and cover; input completeness and explicit broker checks; downloadable/printable report; three scenarios (basic intake, known user GTI, fictional what-if). Numerical rates and ranges are labelled illustrative and uncalibrated. Do not claim a more accurate real premium without insurer-approved tariffs and matched validation data. Do not copy any competitor UI/code/assets, collect ID/contact/exact address data, or connect to providers/paid services.

The current API/ownership/model design is in `INSURANCE_CONTRACT.md`. Reference baseline is a fictional R2,000/month for R620,000; standard colour has no invented surcharge. Known included extras add zero incremental value. Unknown details remain unanswered and increase missing/review indicators. Insurer sources inform field selection only, never numerical rates.

Completed: current scope/API/model contract; confirmed vehicle facts; insurer field research; stateless Decimal engine and local routes; rich intake frontend, original car artwork/styles; rule viewer, download and print support; dashboard navigation link; maintenance documentation and 24 new insurance tests. The full 48-test suite passed cleanly, including the existing throttle check. Following a small maintenance fix, all 18 engine tests and a reference-override regression passed; JavaScript syntax checks passed. Baseline audit text and page notice derive configured reference amounts. The unused reference-excess setting was removed; tier boundaries remain explicit in Python and frontend labels. No insurer integration, quote persistence or business database schema changes.

Browser verification: Basic intake leaves all 22 coverage checks unanswered; Your Polo GTI answers 5/22 and keeps 17 details unknown. Included sunroof adds R0; known vehicle and demo insured value both remain R620,000. The fictional what-if answers 22/22 and produces an illustrative R4,432.98/month using shipped arbitrary rules; provider review is still required. Changing the fictional wheels to included removes their R25,000 addition; unknown inclusion labels the item unpriced. Invalid vehicle-value edits disable report export until corrected. Rule dialog and JSON download work; the downloaded known profile contains calibrated=false, scenario=known, hypothetical=false and sunroof addedValue=0. Desktop and all four phone steps were checked at a 390px viewport with no horizontal overflow or console warnings/errors. Print action/styles are implemented; no physical printer or saved PDF was tested. Preview images are in docs/insurance-preview.jpg, docs/insurance-full-preview.jpg and docs/insurance-mobile-preview.jpg.

No required local proof-of-concept work remains. Next client work: show the richer intake/report to the insurance friend and identify an actual provider's approved fields, valuation/rating data and matched final quotes before claiming premium accuracy. Do not invent driver details or pricing rules as real facts. To launch use `.\run.ps1`, then `/insurance`. Owned preview server is stopped at handoff; launch it before using the local URL.

Restore points: `06-insurance-scope` records the start, `07-insurance-assembled` captures the implementation before browser QA, and `08-insurance-verified` is the final verified milestone with source, docs, screenshots and consistent demo database. Base restore point `05` remains recoverable.

## Previous milestone: independent visual redesign complete and verified

The user requested a different visual identity because the green/lime colors resemble another project and explicitly prohibited using anything from that project. Work was paused and restore point `04-paused-visual-redesign` saved. On 14 October 2026 the user explicitly said **"Ok you can continue from where you left off."** Implementation has resumed.

The chosen independent direction is navy `#15223b`, royal blue `#315fe7`, coral `#ff8169`, cool paper `#f3f6fc`, slate text `#52627c`, and borders `#dbe3ef`. Work must stay within `business-hub`; do not read, copy, import, or use other projects' code, assets, templates, or designs. This is a development constraint, not a legal clearance assessment.

### Current redesign state

- `docs/DESIGN_ORIGIN.md` and the palette guidance in `docs/CUSTOMIZATION.md` were added. An audit of this project's imports/resource paths found no sibling-project dependencies.
- Public website styling, HTML theme/logo, inline service SVGs and hero SVG now use the new palette and newly authored local artwork. Website accent applies validated `company.accentColor` to primary buttons.
- Dashboard has the new palette, a geometric arrow mark, and a new campaign-card illustration. Green/lime CSS variables and old orbit/star illustration were removed. CSS declarations are expanded for manual maintenance.
- New-company accent defaults to `#315fe7`. Only Juniper's saved accent equal to the unchanged original demo default was updated; custom accents, other company settings, and operational records were preserved.
- JavaScript syntax, hero SVG XML, and the three inline service SVG XML checks pass. All 24 existing automated tests passed after the update, using temporary databases.
- Final source audit found no former green/lime styling and no sibling-project or remote asset dependencies. Contrast checks pass for blue/white (5.36:1), navy/coral (6.49:1), and slate/paper (5.71:1).
- Browser verified the dashboard, website editor, public website, and booking availability dialog on desktop and phone widths. No horizontal overflow at 390px viewport / 375px content. Compact screens hide the decorative campaign card so the copy has room.
- No browser warning/error logs were observed. Preview screenshots in `docs/dashboard-preview.jpg` and `docs/website-preview.jpg` now show the new design.
- Preview verification is complete; the owned preview server is stopped during final teardown. Start the local app with `.\run.ps1`. No publishing, hosting, paid services or purchases.

### Continuation reference

No required work remains for the base or this redesign. The base is ready for the user's separate mechanic and insurance conversations, where they will provide business-specific requirements. Preserve the no-other-project-material restriction and the no-spending/no-hosting constraint on future changes.

Restore point `05-independent-visual-design` captures the completed design, source, tests, documentation, previews, and a consistent SQLite backup. It supersedes the incomplete visual state in archive `04`.

Restore point `04-paused-visual-redesign` captures this exact partial state, source, documents, and a consistent database backup. Earlier archives retain the previous completed design for recovery; restoring one would also restore its old palette.

## User intent

Build an all-in-one base for a public website, bookings, lead management, campaigns, and multi-channel content. Later fork this chat for a diesel mechanic and an insurance business. Keep code human-readable. Save restore points so work can continue after account token limits.

## Agreed implementation

- Isolated in `business-hub/`; the existing SideHustle project is separate.
- Python standard library HTTP server + SQLite, vanilla HTML/CSS/JavaScript. No build or dependency install.
- Local URL `http://127.0.0.1:8787/`; public demo `/site/juniper-studio`.
- Persist operational data on disk. APIs scope records by company. Local demo only; real SaaS authentication/authorization is future work.
- Website publishing is real locally. Social delivery and advertising are labelled demo preparation, with no external posts or spend.
- Scope/route details in `CONTRACT.md`.

## Previously completed base, before the requested redesign

- Backend, public website, dashboard, launcher, documentation and restore tooling implemented.
- All 24 automated tests pass, including company scope, booking conflicts, published post drafts, and restore-point recovery.
- Browser verified settings save, website draft isolation and publication, customer booking to dashboard, confirmation, campaign preparation and source-attributed enquiry.
- Published post snapshots preserve current live content while editing drafts. Existing databases migrate on startup.
- Workspace switching removes old controls before activating a different company's ID. Chart uses last 7 days.
- Restore helper verified to recover committed SQLite WAL data on Windows; connections explicitly closed.
- Browser also verified content composition/publication, lead conversion with values/rates, a new company with an empty pipeline, and switching back to the first company.
- Desktop and phone layouts verified: dashboard, website editor, public website, and booking dialog. Phone widths 390px (375px content with scrollbar), no horizontal overflow. No browser console errors observed.
- PowerShell launcher confirmed to choose the bundled Python runtime and serve HTTP successfully.
- Clean seeded demo data is in the project database. Browser workflow tests used a separate temporary database, not the starter database.
- Preview screenshots are in `docs/dashboard-preview.jpg` and `docs/website-preview.jpg`.

## Base handoff reference

No required base implementation remains. Read `README.md` for operation, `docs/ARCHITECTURE.md` for maintenance, `docs/CUSTOMIZATION.md` for client forks, and `docs/INTEGRATIONS.md` for future real services.

For a future continuation, inspect the current files first and preserve saved data. Ask for the business-specific details in the mechanic / insurance fork, then customize a copied project and its own database. Real social/ad adapters, production sign-in, hosting, payments, and scheduling workers are deliberately future integration work; no real provider account is connected and this local server must not be exposed publicly.

## Restore points

Run `.\save-restore-point.ps1 -Label descriptive-name` from this folder (it finds the available Python runtime), or `python tools/checkpoint.py --label descriptive-name` with an installed Python. Snapshots are ZIP files in `.restore-points/`, with a separate consistent SQLite backup included when a database exists. They include this work-state note. Archives are local; nothing is uploaded.

Saved milestones: `01-scope-and-foundation`, `02-working-app-before-browser-qa`, `03-verified-local-demo`, `04-paused-visual-redesign`, `05-independent-visual-design`, `06-insurance-scope`, `07-insurance-assembled`, and latest `08-insurance-verified`. The latest archive includes all source, documentation, tests, preview images, and the consistent demo database. Recovery behavior was tested with a database still using WAL. Archives 01–04 contain earlier/incomplete visual designs; use 05 for the finished navy/blue/coral base or 08 for the base plus insurance proof of concept.

To resume, first read this file and the README in the existing project. If the checkout needs recovery, extract the latest ZIP to a **new empty folder**, read its `RESTORE_NOTE.txt`, and run it there. Keep the current folder and all snapshots until you have verified the recovered copy. Do not overwrite an active database. No snapshot purchase or subscription action is involved.
