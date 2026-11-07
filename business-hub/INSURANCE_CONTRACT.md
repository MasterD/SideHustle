# Quote Lab proof of concept

User wants a small local motor-insurance intake/estimate demo to show an insurance friend. Confirmed user vehicle: **2026 Volkswagen Polo GTI, approximately R620,000, white, sunroof, no modifications**. User confirmed **the sunroof is already included in R620,000**; its separate cost is unknown and unnecessary for incremental value. Default sunroof extra `{name:"Factory sunroof",category:"factory",value:null,includedInVehicleValue:true}`. Do not invent user driver/claims/location/use/cover details. R2,000 is an illustrative baseline inspired by the user's example, not a live Hippo quote. No money, hosting, provider connection, real policy sales, identity numbers or personal contact data. Preserve own navy/blue/coral palette and restriction against using other projects' code/assets/designs. Reuse only this Business Hub foundation.

## Ownership

- Root: static/insurance.html, static/insurance.js, dashboard link, WORK_STATE and preview/checkpoints.
- Insurance backend agent: hub/insurance.py, hub/insurance_rules.json, hub/routes.py integration for routes and static page.
- Design agent: static/insurance.css, static/insurance-car.svg (new generic hatchback, no vendor logos), based on root HTML and selectors below.
- QA/docs agent: tests/test_insurance.py, docs/INSURANCE_POC.md, README mention. May coordinate direct with backend.

## HTTP

GET `/insurance` serves static/insurance.html. GET `/api/insurance/config` returns the full demo rule config (no secrets). POST `/api/insurance/estimate` normalizes/validates inputs and returns calculated report, with existing same-origin/host/body limits and session X-CSRF-Token. Frontend gets token from `/api/session`; calculations don't write to SQLite. Existing APIs and business data stay separate from quote lab. Import `get_config`, `estimate` from hub.insurance in transport, handling these before Application.dispatch. Errors ApiError 400; unknown routes 404.

## Payload (flat JSON)

Required: `make` string, `model` string, `year` integer 1900..current+1, `vehicleValue` positive number <=10000000. Optional string `variant` max120; `colour` max60 (blank unanswered); `locationDescription` max160 (general area only; blank unanswered). `paintFinish`: standard|metallic|custom|unknown. `valuationBasis`: retail|market|agreed|unknown.

Nullable numeric fields: `driverAge` 18..100, `licenceYears` 0..80 (cannot exceed age when both present), `claimsLast3Years` int0..20, `annualKm` int0..200000, `excess` 0..100000. Missing or null remains unknown, never quietly assumes a disclosed answer.

Enums: `usage` private|business|delivery|unknown; `overnightParking` garage|secured|driveway|street|unknown; `tracker` active|none|unknown; `finance` financed|owned|unknown; `coverType` comprehensive|third_party_fire_theft|third_party|unknown; `carHire` yes|no|unknown; `creditShortfall` yes|no|unknown; `modifications` none|cosmetic|performance|unknown. Missing enums default unknown.

`extrasConfirmed`: bool or null. `extras`: list(max20) of `{name:string(max120), category:factory|aftermarket|paint|performance, value:number|null (0..1000000), includedInVehicleValue:bool|null}`. Known included values are not added again. Unknown cost/inclusion creates review flag and unpriced entry; don't invent costs. Duplicate normalized name rejected to prevent double counting. Category factory alone never means included; explicit flag governs. Performance category must trigger review even if modifications selection says none. Specialty paint/custom modifications require review. Colour has no pricing factor. No make/model/year/location lookup or insurer database.

## Engine (plain named functions, JSON assumptions)

Config metadata: `modelVersion:demo-motor-v1`, `label`, `currency:ZAR`, `calibrated:false`, `notice`. `referenceVehicleValue:620000`, `referenceMonthlyPremium:2000` and explanation that rates are fabricated for interaction/demo, not extracted from insurer sources. Tier boundaries live in `selected_factors()` in Python and matching frontend rule labels; no unused reference-excess setting is exposed.

1. Basic reference = 2000 × vehicleValue / 620000. This demonstrates a simple value-linked placeholder baseline, not an insurer tariff. User's confirmed R620k profile has R2k illustrative baseline.
2. Sum only priced, explicitly not-included extras. Detailed value-linked amount = basic × (vehicleValue+extrasAdded)/vehicleValue.
3. Apply selected demo factors in order: age(<25 1.25, otherwise1); licence(<3 1.15 else1); claims(0=1,1=1.15,2+=1.30); annualKm(<=10000 .95,<=20000 1,>20000 1.10); usage(private1,business1.12,delivery1.25); parking(garage1,secured1,driveway1.08,street1.18); tracker(active1,none1.08); cover(comprehensive1,third_party_fire_theft.72,third_party.48); excess(<2500 1.15,<=5000 1,>5000 .92).
4. Add demo monthly optional carHire R90, creditShortfall R45. Shortfall is priced only if financed; owned+yes => no addition and review inconsistency. Unknown finance+yes => unpriced pending review. Unknown factors neutral for arithmetic but explicitly listed in assumptions/missing, not presented as zero risk.
5. Performance risk, custom paint, location-based risk, insurer eligibility/limits/exclusions and exact variant/valuation verification remain unpriced broker/insurer checks. Never accepts/declines insurance or promises coverage.
6. Demo scenario band = ±(10 + 25×missing/total + min(15,5×unpricedReviewCount)) percent, capped50. Explain as arbitrary demonstration sensitivity band, not statistically calibrated prediction/confidence interval.
7. Round final monetary results to cents (Decimal preferred); line item before/after/delta sum must reconcile to final. No physical/risk surcharge for standard colour.

## Report schema

`{meta:{modelVersion,label,currency,calibrated:false,notice}, profile:normalizedPayload, benchmarkMonthly, illustrativeMonthly, differenceMonthly, differencePercent, range:{low,high,marginPercent,basis}, declaredVehicleValue, extrasAddedValue, insuredValueForDemo, extrasSummary:[{name,value,includedInVehicleValue,addedValue,status:included|added|unpriced}], breakdown:[{key,label,explanation,factor:number|null,before,after,amount,kind:base|value|factor|optional}], completeness:{answered,total,percent,missing:[{key,label}],description}, reviewItems:[{code,title,detail,severity:review|unknown}], assumptions:[string]}`

Completeness counts fixed documented 22 fields: variant,colour,paintFinish,valuationBasis,locationDescription,driverAge,licenceYears,claimsLast3Years,annualKm,usage,overnightParking,tracker,finance,coverType,excess,carHire,creditShortfall,modifications,extrasConfirmed,extras-costs,extras-inclusion,extras-inventory. Extras-costs/inclusion are answered for empty inventory ONLY if extrasConfirmed=true; extras-inventory answered if true. An extra already included in vehicle value has zero incremental value, so an unknown separate cost must NOT be treated as an unpriced surcharge; it is accounted for by current vehicle value. Unknown cost matters when extra is NOT included, or inclusion is unknown. extrasConfirmed counts non-null(bool) as answer but false generates review. Completeness describes input coverage, never likelihood/accuracy.

Review needs separate flags for missing fields, extras unknowns, performance/custompaint, valuation verification and insurer rules (including location, declared colour). Include generic provider verification on every report even when all inputs answered. UnpricedReviewCount must be deterministic count of unresolved pricing drivers; generic verification needn't inflate count when full disclosure.

## Frontend behavior

One responsive app with header (Quote Lab / Local proof of concept / dashboard link), hero with generic native SVG, three preset buttons (Basic intake / Your Polo GTI / What-if scenario). Default Your Polo GTI uses confirmed vehicle data only, sunroof included=true/cost=null and unknown driver/use/cover answers. What-if scenario adds clearly fictional driver/use/cover details and extras to demonstrate effects; never implies these are user's facts. 4-step intake (Vehicle, Extras, Driver & use, Cover) left and sticky result right. Manual Calculate demo estimate button and debounced updates after valid inputs; baseline and detailed amount, range, completeness, audit line items, missing/pricing review indicators. Tabs or stepper for mobile; step buttons accessible. R2k and all rates clearly illustrative, not verified user premium/competitor quotes. No ID/name/contact/exact-address collection. Editable extras row with include-in-value control. Show last report as out of date on edits until successful recalculation; abort/sequence to ignore stale requests. Config/rule assumptions dialog or expanded view. Download structured JSON and print assessment, no extra dependencies. Use safe DOM text/escaping; errors inline; accessible labels. Draft not saved without download; no browser storage by default.

Root HTML CSS hooks: `.quote-shell`, `.quote-header`, `.quote-brand`, `.demo-label`, `.quote-hero`, `.hero-copy`, `.hero-art`, `.eyebrow`, `.preset-row`, `.preset-button`, `.workspace-grid`, `.intake-panel`, `.step-navigation`, `.step-button`, `.step-section`, `.section-heading`, `.field-grid`, `.field`, `.field-note`, `.wide-field`, `.extras-list`, `.extra-row`, `.extra-name`, `.extra-value`, `.extra-included`, `.extra-remove`, `.form-actions`, `.button`, `.button-primary`, `.button-secondary`, `.result-panel`, `.result-heading`, `.result-empty`, `.comparison-grid`, `.comparison-card`, `.detailed-card`, `.estimate-number`, `.range-line`, `.completeness-track`, `.readiness-note`, `.breakdown-list`, `.breakdown-row`, `.review-list`, `.review-item`, `.review-count`, `.status-chip`, `.model-note`, `.report-actions`, `.error-message`, `.quote-footer`, `.rules-dialog`. Common `[hidden]` must hide. Print CSS show all intake sections + report, hide actions/navigation/dialog. Use semantic inputs standard platform controls.

## Sources for field selection (not numerical rates)

https://www.outsurance.co.za/car-insurance/non-standard-accessories/ : standard fitted items included in vehicle value vs non-standard cover.
https://www.miway.co.za/blog/do-car-modifications-affect-your-car-insurance : modification types, value/repair and policy impact; insurer dependent.
No unsupported claim that Hippo always asks only basic questions or any competitor's price is incorrect. Proving real improved accuracy requires insurer-approved rates/valuation plus matched final quotes, held-out error measurement, and provider availability/acceptance checks.
