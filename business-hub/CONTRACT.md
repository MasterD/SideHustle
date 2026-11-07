# Business Hub implementation contract

Local, dependency-free Python 3.10+ HTTP server + SQLite + vanilla browser ES modules. Listen on 127.0.0.1:8787. No external services, spend, or publishing. Fictional company: Juniper Studio (plant styling and workshops). Dashboard product: Launchpad.

## Ownership

- Backend agent owns `server.py`, `hub/` Python package, `run.ps1`, `.gitignore`, and `requirements.txt` if needed (prefer no requirements).
- Public website agent owns `static/website.html`, `static/website.js`, `static/website.css`, and `static/plant-art.svg` if useful.
- Root owns `static/index.html`, `static/app.js`, `static/styles.css`, `static/icons.js`.
- QA/docs agent owns `tests/`, `README.md`, `docs/`.

## Transport

All API responses JSON; errors `{error: "Human readable message"}` with correct 4xx. GET `/api/session` -> `{csrfToken, companies: [{id,name,slug}], defaultCompanyId}`. Dashboard requests `/api/companies/{companyId}/...`, POST/PATCH use `X-CSRF-Token`. Protect writes with same-origin checks and CSRF. Each company resource scoped server-side. Static `/` dashboard; `/site/{slug}` public website. Reject non-loopback hosts. Company IDs strings. IDs and timestamps in response. JSON dates ISO; business timezone `Africa/Johannesburg`; browser formatting in company timezone.

## Dashboard APIs

- GET `/api/companies/{id}/overview` -> `{company, metrics: {newLeads, confirmedBookings, pipelineValue, convertedValue, estimatedCommission}, leads, bookings, campaigns, activity, dailyLeads: [{date,count}]}`. Arrays up to 8 most recent. Lead metrics all-time clearly labelled by frontend.
- GET/PATCH `/api/companies/{id}/settings` -> company `{id,name,slug,tagline,description,email,phone,address,timezone,currency,accentColor,commissionRate,bookingDays,openingTime,closingTime}`. `bookingDays` ISO weekdays 1..7. Safe validated local updates; immutable slug once created.
- POST `/api/companies` body `{name,slug}` -> company. Creates default services/site draft. Session companies reread after.
- GET/POST `/api/companies/{id}/leads` -> GET `{leads}`, POST lead. Fields `{name,email,phone,message,source,status,value,commissionRate}`. Status `new|contacted|qualified|won|lost`; value in currency units, not cents. GET supports `?search=&status=` optional.
- PATCH `/api/companies/{id}/leads/{leadId}` -> lead. Update status, value, commissionRate, notes.
- GET `/api/companies/{id}/bookings` -> `{bookings}`; PATCH `.../bookings/{bookingId}` body `{status}` (`requested|confirmed|completed|cancelled`) -> booking. Booking object `{id,name,email,phone,serviceId,serviceName,startAt,endAt,status,message,leadId}`.
- GET/POST `/api/companies/{id}/services` -> GET `{services}`, POST service. Fields `{id,name,description,durationMinutes,price,active}`; PATCH `/services/{serviceId}` supports all except id.
- GET/POST `/api/companies/{id}/posts` -> `{posts}` / post. `{title,body,channels:[website,facebook,instagram,linkedin],status:draft|prepared|published,createdAt}`. POST saves draft; PATCH `/posts/{postId}` edit draft fields.
- POST `/api/companies/{id}/posts/{postId}/publish` -> `{post, deliveries}`. Publish local website if selected; social deliveries `demo_ready`. No external requests. Repeated unchanged publish no duplicate deliveries.
- GET/POST `/api/companies/{id}/campaigns` -> `{campaigns}` / campaign. `{id,name,objective:leads|bookings|awareness,offer,plannedBudget,channels,status:draft|prepared,sourceCode,createdAt}`.
- POST `/api/companies/{id}/campaigns/{campaignId}/run` -> `{campaign,post,deliveries}`. Creates ONE reusable draft/post preparation, queues demo social/ad plan, publishes local website if selected. No external requests, charge, fake clicks or leads. Repeated run idempotent. Campaign source code available for website URL `?campaign=...` attribution.
- GET `/api/companies/{id}/website` -> `{draft,published}` objects `{headline,subheadline,about,ctaLabel,announcement}`.
- PATCH same route body draft fields -> `{draft,published}`. POST `/website/publish` -> `{draft,published}`. Local website reads published version only.
- GET `/api/companies/{id}/deliveries` -> `{deliveries}` with `{id,title,channel,status,createdAt}`. Website status `published_local`; social `demo_ready`.
- GET `/api/companies/{id}/activity` -> `{activity}` with `{id,message,createdAt}`.
- GET `/api/companies/{id}/export` -> full scoped JSON downloadable export (no secrets).

## Public APIs

- GET `/api/public/{slug}` -> `{company,website,services,posts,campaign}`. `website` published only; active services; only local published posts. `campaign` optional lookup via query `?campaign=sourceCode`.
- GET `/api/public/{slug}/slots?serviceId=...&date=YYYY-MM-DD` -> `{slots:[{startAt,endAt,label}]}`; slots are future, within opening days/hours, no overlap with requested/confirmed appointments. Times include offset.
- POST `/api/public/{slug}/bookings` body `{name,email,phone,serviceId,startAt,message,consent:true,campaignCode?}` -> booking; conflict HTTP409 atomically. Creates attributed lead. Same-origin public writes without admin CSRF, rate/size limited. Mandatory consent for processing booking inquiry (no marketing opt-in).
- POST `/api/public/{slug}/enquiries` body `{name,email,phone,message,consent:true,campaignCode?}` -> `{id,message}`. Creates lead source website or campaign. Same validation, abuse limits.

## Demo data and behavior

SQLite `data/business-hub.sqlite3` created on start; synthetic demo records marked by UI persistent Local demo badge. Seed first startup only, dates relative to current date in business timezone, invalid placeholder contacts example.test. Monetary values ZAR. All stats calculated from persisted records, no fake live impressions/ROI. Fields camelCase API, snake_case Python/SQL. Basic tenant-aware structure for reuse, but not production SaaS authorization. Keep function names descriptive, comments explain rules. Python package storage/business rules/routes separated. Run `python server.py` from directory, `python -m unittest discover -s tests -v`. Tests temporary databases.
