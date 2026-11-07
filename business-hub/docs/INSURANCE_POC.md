# Quote Lab: motor-insurance intake proof of concept

Quote Lab demonstrates how a more complete intake can expose unanswered questions, avoid counting extras twice and explain the assumptions behind an estimate. It is a local addition to Launchpad. It does not connect to insurers, issue policies, establish cover or prove improved premium accuracy.

Start Launchpad with `..\run.ps1` from this directory, or `.\run.ps1` from the project directory, then open **http://127.0.0.1:8787/insurance**. Use the normal launcher from the project directory as described in [the README](../README.md).

## What to show your insurance friend

1. Open **Your Polo GTI**. The vehicle facts come from the user: a **2026 Volkswagen Polo GTI**, approximately **R620,000**, **white**, with a **factory sunroof and no modifications**. The user confirmed that the sunroof is already included in that R620,000. Its separate cost is unknown and does not need to be added again.
2. Point out the unanswered driver, use, parking, finance and cover details. They remain unknown; the form does not pretend that the user is a particular age or has a particular claims history. The illustrative amount can remain R2,000 while the report still shows missing inputs and provider checks.
3. Compare **Basic intake** with **What-if scenario**. The latter uses explicitly fictional driver and cover choices to demonstrate how disclosed information could affect an estimate. It is not the user's risk profile.
4. Add a sample accessory with a known value and choose **Not included** in the declared vehicle value. Recalculate and inspect the extra's value and the calculation line items. Change it to **Included** to demonstrate why it should not be counted twice.
5. Leave the value or inclusion of a nonincluded extra unanswered. The report marks it for review rather than inventing a cost. Try a performance extra or custom paint to see an insurer review flag.
6. Inspect the remaining questions, model assumptions and line items. Download the structured JSON report or print it for a discussion. Downloads are saved by the browser; calculations do not create a saved lead or policy.

The R2,000 reference is a fabricated demonstration amount inspired by the user's example. It is not a live Hippo quote, a verified premium for this Polo, or a claim that a competitor quoted incorrectly. The demo makes no claim about which questions Hippo currently asks.

## What the numbers mean

The server reads the readable assumptions in [hub/insurance_rules.json](../hub/insurance_rules.json). The model is marked `calibrated: false` and identified by a version in both its configuration and every report.

The basic reference is `R2,000 × declared vehicle value ÷ R620,000`. Priced extras are added only when their inclusion flag is explicitly false. Selected answers then apply the fabricated factors listed below in order; optional demo amounts are added afterwards. All amounts and displayed changes are rounded to cents so the audit line items reconcile to the final illustrative result.

| Disclosed detail | Fabricated demo rule |
| --- | --- |
| Driver age | Under 25: ×1.25; otherwise ×1.00. |
| Years licensed | Under 3 years: ×1.15; otherwise ×1.00. |
| Claims in the last 3 years | None: ×1.00; one: ×1.15; two or more: ×1.30. |
| Annual distance | Up to 10,000 km: ×0.95; up to 20,000 km: ×1.00; higher: ×1.10. |
| Use | Private: ×1.00; business: ×1.12; delivery: ×1.25. |
| Overnight parking | Garage or secured: ×1.00; driveway: ×1.08; street: ×1.18. |
| Tracker | Active: ×1.00; none: ×1.08. |
| Cover type | Comprehensive: ×1.00; third-party, fire and theft: ×0.72; third-party: ×0.48. |
| Excess | Below R2,500: ×1.15; up to R5,000: ×1.00; higher: ×0.92. |
| Car hire | If selected: add R90 per month. |
| Credit shortfall | If selected and the car is financed: add R45 per month. |

These rules are arbitrary teaching examples, not insurer rates or recommendations about selecting cover or excess. Credit shortfall selected for an owned vehicle is flagged as inconsistent and adds nothing. If finance is unknown, selected shortfall remains unpriced pending review.

Unknown factors are neutral only for demonstration arithmetic. That does not mean their risk is zero. They remain listed in missing answers and assumptions. The engine does not look up the risk of the make, model, year, exact variant or location. Colour is captured for provider verification and has no invented surcharge. Performance risk and specialty paint remain unpriced checks; a known, nonincluded item's value can still be included in the demonstration value calculation.

The displayed scenario band uses this arbitrary formula:

```text
margin percent = min(50, 10 + 25 × missing fields ÷ total fields
                         + min(15, 5 × unresolved pricing drivers))
low / high = illustrative amount × (1 - / + margin percent ÷ 100)
```

It is a demonstration sensitivity band, not a calibrated prediction interval, statistical confidence level or promise that a final premium falls within it. Filling out the form can narrow this arbitrary band; it does not make the fabricated rates accurate.

## Completeness and review

Completeness counts **22 input-coverage fields**: exact variant, colour, paint finish, valuation basis, general location, driver age, years licensed, claims, annual distance, use, overnight parking, tracker, finance, cover type, excess, car hire, credit shortfall, modifications, confirmation of extras, extras costs, extras inclusion and confirmation of the extras inventory.

An empty extras list answers the inventory, costs and inclusion questions only when the user confirms it is complete. For an item already included in the declared value, an unknown separate cost is acceptable: its incremental value is zero. Unknown cost matters when an item is not included or when inclusion is unknown. A false extras confirmation is a disclosed answer but leaves the inventory unresolved.

Completeness describes what was answered, not the chance that an amount is correct. Even at 100%, the report retains provider verification of the valuation, variant, declared colour, location, eligibility, terms, limits and exclusions. No combination of form answers accepts or declines insurance.

## How the code works

| File | Responsibility |
| --- | --- |
| [hub/insurance.py](../hub/insurance.py) | Validate and normalize intake; handle extras; calculate the illustrative amount; assemble disclosures and review items. The main entry points are `get_config()` and `estimate(payload)`. |
| [hub/insurance_rules.json](../hub/insurance_rules.json) | Demo metadata, named factors, optional amounts, scenario-band assumptions and completeness labels. |
| [hub/routes.py](../hub/routes.py) | Serve the local page and insurance API within the existing local request protections. |
| [static/insurance.html](../static/insurance.html) | The four intake sections, labels and report layout. |
| [static/insurance.js](../static/insurance.js) | Presets, input collection, recalculation, report rendering, JSON download and print action. |
| [static/insurance.css](../static/insurance.css) | Responsive and print presentation using this project's own palette. |
| [tests/test_insurance.py](../tests/test_insurance.py) | Arithmetic, extras, unknowns, validation, review and HTTP boundary checks. |

`GET /insurance` serves the page. `GET /api/insurance/config` returns public demo assumptions. `POST /api/insurance/estimate` accepts the flat JSON intake and returns a report. The frontend first gets its write token from `GET /api/session`. Insurance requests use the same loopback host, origin, token and body-size protections as the dashboard.

The calculation is stateless. It does not write to SQLite or change the selected company. The intake is not stored in browser storage by default. A JSON download includes its normalized profile, model version, amounts, extra inventory, audit line items, completeness, review items and assumptions. Treat downloaded information according to the data you chose to enter.

The form does not need a name, phone number, email, identity number, registration number or exact home address for this local demonstration. Use sample details when showing it. No external provider, advert, paid tool or hosting service is called.

## Small maintenance changes

Create a restore point before changing the model with `.\save-restore-point.ps1 -Label before-insurance-rule-change` from the project directory. Edit the JSON rules for reference amounts, factor multipliers, optional additions and scenario-band weights. The baseline notice and audit explanation read the configured reference amounts. Use the Python engine for validation or new calculation logic, and HTML/JavaScript for new intake fields. Keep names explicit so a maintenance reader can follow each adjustment.

Tier boundaries (such as age 25, 10,000/20,000 km and R2,500/R5,000 excess) live in `selected_factors()` in `hub/insurance.py`; their readable labels live in `renderRules()` in `static/insurance.js`. Change both when moving a boundary. Validation limits live in `normalize_profile()` and the HTML input attributes. The rule table and reference numbers above describe the current shipped defaults; update this guide when those defaults change.

When changing a rule, update `modelVersion` so downloaded reports identify which assumptions produced them. Keep previous versions and examples in a restore point. Keep `calibrated` false unless the model has actually been validated and approved for its intended use. Changing the label alone cannot turn this model into an insurer quote.

Restart the local server after editing Python or JSON, then refresh the browser. Run the standard-library checks from the project directory:

```powershell
python -m unittest discover -s tests -v
```

Tests run against temporary databases and do not touch the demo's saved business records. They check observable behaviour and arithmetic, including the included sunroof, unpriced extras, invalid inputs, shortfall conditions, remaining provider review and stateless local routes. Passing them proves software behaviour; it does not validate the premium model.

## What is needed to demonstrate real accuracy

Agree with your friend and an insurer on the target product, approved intake, rating and valuation data, terms, eligibility and referral workflow before describing a result as an insurer quote. A more complete questionnaire is a useful starting point, but real accuracy requires evidence.

Collect matched, permitted cases where the proposed system's initial estimate and the insurer's final quote use the same vehicle, driver, declared extras, cover, excess and quote date. Record changes in disclosures and provider availability so mismatched cases do not silently distort the comparison. Keep separate data for calibration and evaluation.

Agree in advance on an acceptable error measure, such as mean absolute Rand error and percentage error, and report sample size and results on held-out cases. Compare against an agreed baseline using the same cases; examine both underestimates and overestimates. Test whether any proposed ranges cover actual final prices at the promised rate. Provider checks for availability, eligibility and approval remain necessary even with good numerical results.

This demo has none of that evidence yet. The next concrete step is to show the intake and report to your friend and identify which fields and rates an actual provider can approve and supply.

## Sources for the intake design

The insurer pages below support collecting and checking accessory and modification details. They do not supply the numerical demonstration rules, confirm this user's valuation, or establish cover under any policy.

- [OUTsurance: non-standard vehicle accessories](https://www.outsurance.co.za/car-insurance/non-standard-accessories/) describes distinguishing standard vehicle items from additional accessories that need to be specified. This informs the inventory and inclusion questions, without assuming every factory option is already included in a declared value.
- [MiWay: do car modifications affect your car insurance?](https://www.miway.co.za/blog/do-car-modifications-affect-your-car-insurance) discusses cosmetic and performance changes, disclosure, and effects that depend on the upgrade and insurer's terms. This informs the modification categories and provider review flags.

Sources checked on **14 October 2026**. The sunroof's inclusion in R620,000 comes from the user's explicit confirmation, not an inference from either source. The artwork and presentation are authored within this project and follow [the design-origin policy](DESIGN_ORIGIN.md).
