# Turning the demo into a client version

Juniper Studio is an example configuration. The reusable product is the dashboard, company records, public website, lead workflow, booking rules, content preparation and campaign attribution.

Keep this base as the common version. Fork the conversation for each client when you are ready to supply its details, and make industry changes in a separate Git branch or copied project directory. Both versions can then inherit fixes from a clear common starting point.

## Changes that need no code

Use company settings for the name, contact details, currency, timezone, opening days and hours, accent colour and default commission rate. Use Services for appointment names, durations and prices. Use Website for headline, explanation, call to action and announcement. Drafts can be reviewed before they are published locally.

Creating another company demonstrates separate records and a separate public URL. It is a convenient way to show another client the system while keeping Juniper Studio as an example.

## Colours and visual maintenance

This project has its own navy, royal blue and coral palette. Keep design work within `business-hub/` and follow [the design-origin policy](DESIGN_ORIGIN.md). Use additional client artwork or reference material only when the human user supplies or authorizes it for this project.

| Colour | Value | Intended use |
| --- | --- | --- |
| Navy | `#15223b` | Main text and dark navigation surfaces. |
| Royal blue | `#315fe7` | Primary actions and the default business accent. |
| Coral | `#ff8169` | Selected highlights and decorative accents. |
| Paper | `#f3f6fc` | Main page background. |
| Slate | `#52627c` | Supporting text and labels. |
| Border | `#dbe3ef` | Dividers, outlines and table boundaries. |

Use **Settings & services → Brand accent** for a company's editable accent. Existing databases retain their saved company settings; changing the source default does not automatically change a saved business accent.

For broader visual changes, start with the CSS custom properties at the top of `static/styles.css` and `static/website.css`. Then review the relevant component rules and this project's `static/plant-art.svg` fills and strokes. Keep the dashboard and public site readable at narrow and wide screen sizes, with visible keyboard focus and sufficient text contrast. Open both pages after a colour change to check the result.

## Changes that probably need code

Industry-specific intake fields, staff calendars, vehicles or policies should be explicit additions to the data model. Avoid hiding structured information in a free-text note if you need to search, validate or report on it later.

If a new field is required, follow it through all layers: database storage, server validation, API response, dashboard display, public form when relevant, export and tests. For an existing database, add an intentional schema migration rather than relying on the original database creation statement to run again.

## Diesel mechanic discussion

The next version can start from the existing enquiry and service appointment workflow. Useful details to collect from your friend include:

- Business name, service area, contact channels and brand assets.
- Workshop appointments versus call-outs, availability, staff capacity and travel time.
- Vehicle or equipment details required before quoting.
- Whether advertised prices are fixed prices, starting prices or quote-only.
- How requests become confirmed jobs and who changes their status.

The present booking engine handles one shared schedule per company. Multiple mechanics, bays or mobile teams need resource-specific availability before you represent them as bookable capacity.

## Insurance referral discussion

The generic lead pipeline and commission estimate provide a starting point. Before implementing an incentive workflow, agree on the following with the client:

- Which information is needed for an initial enquiry and which should be collected by an authorized provider later.
- The definition of a converted lead and who confirms it.
- The agreed referral amount or rate, reconciliation process and payment evidence.
- The information that can be shown on the website and who approves it.
- Consent wording, access requirements and the retention rules the client needs.

Do not relabel the demo's estimated commission as paid commission. A real version should separate referral, confirmed conversion, expected incentive and payment received, with dates and an audit trail.

## Keep the common product understandable

Share stable capabilities such as website drafts, company scope, service availability and content preparation. Add small, explicit client extensions for industry-specific requirements. Avoid scattering checks for a particular company name throughout the server or JavaScript.

As a practical selling point, describe the current product as a single place to prepare marketing, collect enquiries and manage bookings. Real multi-channel publishing and paid campaign execution become connected services with their own authorization and results, as described in [the integration plan](INTEGRATIONS.md).
