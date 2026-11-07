# QuietBatch customer page — approved hosting; account/registration setup pending

This folder contains marketing copy and fictional sample data. The owner explicitly approved public display of the legal name, email, address, precise coordinates and telephone shown on the seller preview, and confirmed its use for legal service. The owner approved Cloudflare Pages Free publication at R0 after information-officer setup. The newly completed PAIA manual is awaiting its separate review. The owner dashboard and records remain in the parent project and must never be included in a hosting upload.

The complete page introduces the R3,500 pilot, lets a visitor explore a synthetic report and opens an enquiry draft in their own email app. It has no payment collection, production-data uploads, backend, analytics, sign-in, tax records or MCP server.

Local preview: run `./start-preview.ps1` from the project root or run `preview.py` with the existing bundled Python, then open `http://127.0.0.1:8766/`. The deployment files are exactly the allowlisted files in `dist/`; `preview.py` is not a hosted service.

Approved R0 hosting: Cloudflare Pages Free, static Direct Upload, using its included pages.dev address. Official documentation confirms static asset requests are free and unlimited; avoid paid Workers, functions, custom-domain purchases and paid add-ons. The account form is prepared with the business email, awaiting the owner's password, verification and terms steps. No account or project is confirmed yet. [Static pricing](https://developers.cloudflare.com/pages/functions/pricing/), [Direct Upload](https://developers.cloudflare.com/pages/get-started/direct-upload/), [Free limits](https://developers.cloudflare.com/pages/platform/limits/).

The earlier native Sites route has not been used for registration because its pricing was not verified against the R0 requirement. Local preparation follows the Sites static workflow. The user's approval request takes precedence over default publication.

Before publication: complete the owner-controlled free hosting account and separate information-officer registration/privacy setup; review the new PAIA manual. Seller disclosures and hosting are already approved, so do not ask for those again unless they change. ECTA seller disclosures are included on seller.html; enquiry-only wording is not treated as an exemption. The coordinates are an owner-supplied locator, not independent documentary proof of an address. Before any order: confirm customer-specific terms, bank-account permissions/fees and provisional-tax duties. The page has no online order acceptance.

`render-seller.py` renders the contact page locally from the private data/seller-details.json. It does not approve disclosure or publish anything. If those details change, rerender and repeat content review. `package.py` makes the review archive and fingerprints its exact contents; `--publication-ready` refuses an upload archive until both disclosure and publication approval are recorded for that fingerprint.

A deployment archive must contain only the allowlisted `dist/` files at its root. Verify a successful public URL and HTTPS before recording publication as complete; never invent or assume pages.dev availability. No archive includes data/, ledger, private profile, payment details, or employer information.
