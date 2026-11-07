"""Stateless, deliberately uncalibrated motor-insurance demonstration.

No database, provider connection or real rating data is used here. The separate
JSON file makes the invented assumptions visible to someone maintaining the
demo. Disclosure completeness describes answers supplied, not quote accuracy.
"""

from datetime import datetime
from decimal import Decimal, ROUND_HALF_UP
import json
from pathlib import Path
import unicodedata

from .validation import ApiError, business_timezone


RULES_PATH = Path(__file__).with_name("insurance_rules.json")
CENT = Decimal("0.01")

ENUM_CHOICES = {
    "paintFinish": ("standard", "metallic", "custom", "unknown"),
    "valuationBasis": ("retail", "market", "agreed", "unknown"),
    "usage": ("private", "business", "delivery", "unknown"),
    "overnightParking": ("garage", "secured", "driveway", "street", "unknown"),
    "tracker": ("active", "none", "unknown"),
    "finance": ("financed", "owned", "unknown"),
    "coverType": ("comprehensive", "third_party_fire_theft", "third_party", "unknown"),
    "carHire": ("yes", "no", "unknown"),
    "creditShortfall": ("yes", "no", "unknown"),
    "modifications": ("none", "cosmetic", "performance", "unknown"),
}
TEXT_LIMITS = {
    "make": 120, "model": 120, "variant": 120,
    "colour": 60, "locationDescription": 160,
}
NUMBER_FIELDS = {
    "driverAge": (18, 100, False),
    "licenceYears": (0, 80, False),
    "claimsLast3Years": (0, 20, True),
    "annualKm": (0, 200000, True),
    "excess": (0, 100000, False),
}
EXTRA_FIELDS = {"name", "category", "value", "includedInVehicleValue"}
EXTRA_CATEGORIES = ("factory", "aftermarket", "paint", "performance")
PROFILE_FIELDS = (set(TEXT_LIMITS) | set(ENUM_CHOICES) | set(NUMBER_FIELDS)
                  | {"year", "vehicleValue", "extrasConfirmed", "extras"})


def get_config():
    """Return a fresh copy of the public rules. There are no secrets in it."""
    return json.loads(RULES_PATH.read_text(encoding="utf-8"))


def decimal_number(value):
    """Convert through text so binary floating-point does not enter the maths."""
    return Decimal(str(value))


def money(value):
    return value.quantize(CENT, rounding=ROUND_HALF_UP)


def json_money(value):
    return float(money(value))


def format_rand(value):
    """Format configured reference amounts for the human-readable audit trail."""
    amount = money(decimal_number(value))
    if amount == amount.to_integral_value():
        return f"R{amount:,.0f}"
    return f"R{amount:,.2f}"


def read_text(data, key, maximum, required=False):
    value = data.get(key, "")
    if not isinstance(value, str):
        raise ApiError(400, f"{key} must be text.")
    value = " ".join(value.split())
    if required and not value:
        raise ApiError(400, f"Please provide {key}.")
    if len(value) > maximum:
        raise ApiError(400, f"{key} must be no longer than {maximum} characters.")
    return value


def read_number(data, key, minimum, maximum, integer=False, required=False,
                positive=False):
    value = data.get(key)
    if value is None and not required:
        return None
    # In Python, True is an int. Explicitly exclude it from numeric answers.
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ApiError(400, f"{key} must be a number{' or null' if not required else ''}.")
    numeric = decimal_number(value)
    if not numeric.is_finite() or numeric < minimum or numeric > maximum:
        raise ApiError(400, f"{key} must be between {minimum} and {maximum}.")
    if positive and numeric <= 0:
        raise ApiError(400, f"{key} must be greater than zero.")
    if integer and (not isinstance(value, int)):
        raise ApiError(400, f"{key} must be a whole-number integer.")
    return value


def read_choice(data, key, choices, default="unknown"):
    value = data.get(key, default)
    if not isinstance(value, str) or value not in choices:
        raise ApiError(400, f"{key} must be one of: {', '.join(choices)}.")
    return value


def read_nullable_boolean(data, key):
    value = data.get(key)
    if value is not None and not isinstance(value, bool):
        raise ApiError(400, f"{key} must be true, false or null.")
    return value


def reject_unexpected_fields(data, allowed, label):
    unexpected = set(data) - allowed
    if unexpected:
        raise ApiError(400, f"{label} contains unsupported fields. Only quote-intake fields are accepted.")


def normalize_extras(data):
    extras = data.get("extras", [])
    if not isinstance(extras, list) or len(extras) > 20:
        raise ApiError(400, "extras must be a list of no more than 20 items.")
    normalized = []
    names = set()
    for index, extra in enumerate(extras):
        if not isinstance(extra, dict):
            raise ApiError(400, f"Extra {index + 1} must be an object with named fields.")
        reject_unexpected_fields(extra, EXTRA_FIELDS, f"Extra {index + 1}")
        name = read_text(extra, "name", 120, required=True)
        duplicate_key = unicodedata.normalize("NFKC", name).casefold()
        if duplicate_key in names:
            raise ApiError(400, "An extra is listed more than once. Use one entry for each extra.")
        names.add(duplicate_key)
        normalized.append({
            "name": name,
            "category": read_choice(extra, "category", EXTRA_CATEGORIES, default=None),
            "value": read_number(extra, "value", 0, 1000000),
            "includedInVehicleValue": read_nullable_boolean(extra, "includedInVehicleValue"),
        })
    return normalized


def normalize_profile(data):
    """Validate inputs without substituting invented answers for missing ones."""
    if not isinstance(data, dict):
        raise ApiError(400, "Send a JSON object with named quote-intake fields.")
    reject_unexpected_fields(data, PROFILE_FIELDS, "The intake")
    profile = {
        key: read_text(data, key, limit, required=key in ("make", "model"))
        for key, limit in TEXT_LIMITS.items()
    }
    current_year = datetime.now(business_timezone("Africa/Johannesburg")).year
    profile["year"] = read_number(data, "year", 1900, current_year + 1,
                                  integer=True, required=True)
    profile["vehicleValue"] = read_number(data, "vehicleValue", 0, 10000000,
                                          required=True, positive=True)
    for key, choices in ENUM_CHOICES.items():
        profile[key] = read_choice(data, key, choices)
    for key, (minimum, maximum, integer) in NUMBER_FIELDS.items():
        profile[key] = read_number(data, key, minimum, maximum, integer=integer)
    if (profile["driverAge"] is not None and profile["licenceYears"] is not None
            and profile["licenceYears"] > profile["driverAge"]):
        raise ApiError(400, "licenceYears cannot exceed driverAge.")
    profile["extrasConfirmed"] = read_nullable_boolean(data, "extrasConfirmed")
    profile["extras"] = normalize_extras(data)
    return profile


def summarize_extras(profile):
    """Only add an extra when its cost and exclusion from the value are known."""
    summary = []
    added_value = Decimal("0")
    for extra in profile["extras"]:
        included = extra["includedInVehicleValue"]
        value = extra["value"]
        added = Decimal("0")
        if included is True:
            # A sunroof already inside R620,000 stays inside R620,000, even
            # when its separate cost is unknown. Never invent a surcharge.
            status = "included"
        elif included is False and value is not None:
            status = "added"
            added = decimal_number(value)
            added_value += added
        else:
            status = "unpriced"
        summary.append({
            "name": extra["name"], "value": value,
            "includedInVehicleValue": included,
            "addedValue": json_money(added), "status": status,
        })
    return summary, added_value


def calculate_completeness(profile, config):
    """Count the same documented 22 questions for every intake."""
    answered = {}
    for field in config["completenessFields"]:
        key = field["key"]
        value = profile.get(key)
        answered[key] = value is not None and value != "" and value != "unknown"
    extras = profile["extras"]
    if extras:
        # Separate cost is unnecessary when inclusion is confirmed. A known
        # cost alone cannot resolve whether it is already in the vehicle value.
        answered["extras-costs"] = all(
            item["includedInVehicleValue"] is True or item["value"] is not None
            for item in extras
        )
        answered["extras-inclusion"] = all(
            item["includedInVehicleValue"] is not None for item in extras
        )
    else:
        answered["extras-costs"] = profile["extrasConfirmed"] is True
        answered["extras-inclusion"] = profile["extrasConfirmed"] is True
    answered["extras-inventory"] = profile["extrasConfirmed"] is True
    missing = [dict(field) for field in config["completenessFields"]
               if not answered[field["key"]]]
    total = len(config["completenessFields"])
    count = total - len(missing)
    return {
        "answered": count, "total": total,
        "percent": round(count * 100 / total, 1), "missing": missing,
        "description": "Input coverage only. More answers reveal issues for review; this percentage does not measure accuracy or the likelihood of an insurer quote.",
    }


def selected_factors(profile, config):
    """Yield disclosed demo factors in the documented order; unknowns stay out."""
    rates = config["factors"]
    age = profile["driverAge"]
    if age is not None:
        tier = "under25" if age < 25 else "25AndOver"
        yield ("driverAge", "Driver age", rates["driverAge"][tier],
               "Invented demo age factor; not an insurer age tariff.")
    years = profile["licenceYears"]
    if years is not None:
        tier = "under3" if years < 3 else "3AndOver"
        yield ("licenceYears", "Years licensed", rates["licenceYears"][tier],
               "Invented demo factor for disclosed years licensed.")
    claims = profile["claimsLast3Years"]
    if claims is not None:
        tier = str(claims) if claims < 2 else "2AndOver"
        yield ("claimsLast3Years", "Claims history", rates["claimsLast3Years"][tier],
               "Invented demo factor for claims disclosed in the last three years.")
    kilometres = profile["annualKm"]
    if kilometres is not None:
        if kilometres <= 10000:
            tier = "upTo10000"
        elif kilometres <= 20000:
            tier = "upTo20000"
        else:
            tier = "over20000"
        yield ("annualKm", "Annual kilometres", rates["annualKm"][tier],
               "Invented demo factor for disclosed annual travel.")
    labels = {
        "usage": "Vehicle use", "overnightParking": "Overnight parking",
        "tracker": "Tracker status", "coverType": "Cover type",
    }
    for key, label in labels.items():
        if profile[key] != "unknown":
            yield (key, label, rates[key][profile[key]],
                   f"Invented demo factor for {label.lower()}; actual provider rules may differ.")
    excess = profile["excess"]
    if excess is not None:
        if excess < 2500:
            tier = "under2500"
        elif excess <= 5000:
            tier = "upTo5000"
        else:
            tier = "over5000"
        yield ("excess", "Chosen excess", rates["excess"][tier],
               "Invented demo excess factor. Actual excess definitions and conditions require provider verification.")


class EstimateBreakdown:
    """Keep exact running maths while showing cents that reconcile row by row."""

    def __init__(self):
        self.current = Decimal("0")
        self.items = []

    def add(self, key, label, explanation, after, kind, factor=None):
        before_display = money(self.current)
        after_display = money(after)
        self.items.append({
            "key": key, "label": label, "explanation": explanation,
            "factor": factor, "before": float(before_display),
            "after": float(after_display),
            "amount": float(after_display - before_display), "kind": kind,
        })
        self.current = after


def build_review_items(profile, summary, completeness):
    """Separate unanswered inputs from disclosed, unpriced provider checks.

    The scenario count tracks specific unresolved extra/special-risk/shortfall
    drivers. Generic provider verification does not widen the band by itself.
    Missing inputs already widen it through the separate completeness term.
    """
    items = []
    unpriced_count = 0

    def review(code, title, detail, severity="review"):
        items.append({"code": code, "title": title, "detail": detail, "severity": severity})

    if completeness["missing"]:
        labels = ", ".join(item["label"] for item in completeness["missing"])
        review("missing_fields", "Unanswered intake questions", labels + ". Unknown rating inputs are neutral only for demo arithmetic, not evidence of low risk.", "unknown")
    if profile["extrasConfirmed"] is not True:
        review("extras_inventory", "Extras inventory needs confirmation", "Confirm that all factory options, accessories and modifications have been declared. This demo cannot discover missing extras.", "unknown")
    for index, (extra, result) in enumerate(zip(profile["extras"], summary), start=1):
        if result["status"] != "unpriced":
            continue
        unpriced_count += 1
        if extra["includedInVehicleValue"] is None:
            review(f"extra_inclusion_{index}", f"Confirm inclusion: {extra['name']}", "Its inclusion in the declared vehicle value is unknown. No incremental value has been assumed or added.", "unknown")
        if extra["value"] is None:
            review(f"extra_cost_{index}", f"Confirm incremental cost: {extra['name']}", "Its cost is unknown and inclusion in the declared value is not confirmed. No cost or surcharge has been invented.", "unknown")
    performance = (profile["modifications"] == "performance"
                   or any(item["category"] == "performance" for item in profile["extras"]))
    if performance:
        unpriced_count += 1
        review("performance_modifications", "Performance items need provider review", "Performance items are disclosed. Their value, repair implications, policy conditions and acceptability remain unpriced; no coverage is promised.")
        if profile["modifications"] == "none":
            review("modification_inconsistency", "Modification declaration conflicts with an extra", "A performance extra is listed while modifications are declared as none. Resolve this before seeking an insurer quote.")
    elif profile["modifications"] == "cosmetic":
        unpriced_count += 1
        review("cosmetic_modifications", "Cosmetic modifications need provider review", "Any effect on repair costs, valuation and policy conditions remains unpriced in this demo.")
    specialty_paint = (profile["paintFinish"] == "custom"
                      or any(item["category"] == "paint" for item in profile["extras"]))
    if specialty_paint:
        unpriced_count += 1
        review("custom_paint", "Specialty paint needs provider review", "Custom paint or a paint extra is disclosed. Repair/replacement cost and policy treatment remain unpriced. Standard colour does not receive a demo surcharge.")
    if profile["creditShortfall"] == "yes":
        if profile["finance"] == "unknown":
            unpriced_count += 1
            review("shortfall_finance_unknown", "Shortfall option awaits finance details", "Finance status is unknown. The shortfall option has not been priced; a provider must confirm the finance and coverage conditions.", "unknown")
        elif profile["finance"] == "owned":
            review("shortfall_not_financed", "Shortfall option conflicts with finance status", "The vehicle is declared owned without finance, so the demo adds no shortfall amount. Confirm the intended option with a provider.")
    review("valuation_verification", "Verify vehicle and valuation", "Make, model, year, exact variant and declared value require independent provider verification. The demo uses no vehicle valuation database or model lookup.")
    review("location_colour_verification", "Check location and declared paint details", "Insurer-specific location risk, declared colour and paint treatment have not been priced. No standard-colour numerical factor or postcode lookup is used.")
    review("insurer_rules", "Provider rules and quote still required", "Eligibility, cover limits, exclusions, excess conditions and provider acceptance have not been checked. This assessment does not bind cover, accept or decline an application, or guarantee a final premium.")
    return items, unpriced_count


def calculate_scenario_range(amount, completeness, unpriced_count, config):
    rule = config["scenarioBand"]
    missing_fraction = Decimal(len(completeness["missing"])) / Decimal(completeness["total"])
    extra_margin = min(decimal_number(rule["maximumUnpricedPercent"]),
                       decimal_number(rule["perUnpricedDriverPercent"]) * unpriced_count)
    margin = min(decimal_number(rule["maximumMarginPercent"]),
                 decimal_number(rule["basePercent"])
                 + decimal_number(rule["missingFieldWeightPercent"]) * missing_fraction
                 + extra_margin)
    return {
        "low": json_money(amount * (1 - margin / 100)),
        "high": json_money(amount * (1 + margin / 100)),
        "marginPercent": float(margin.quantize(CENT, rounding=ROUND_HALF_UP)),
        "basis": rule["explanation"] + f" This intake has {len(completeness['missing'])} unanswered fields and {unpriced_count} specific unresolved pricing drivers. Generic provider checks are not added to that driver count.",
    }


def build_assumptions(profile, config):
    factor_keys = tuple(config["factors"])
    unknown_factor_keys = [key for key in factor_keys
                           if profile[key] is None or profile[key] == "unknown"]
    labels = {field["key"]: field["label"] for field in config["completenessFields"]}
    assumptions = [
        config["referenceExplanation"],
        "All rating factors and optional-cover amounts are fabricated demonstration assumptions. No insurer rates, underwriting model or provider availability checks are connected.",
        "The basic reference uses declared vehicle value only. The detailed illustration adds only priced extras explicitly outside that value, then selected demo factors and optional amounts.",
        "Confirmed included extras have zero incremental value even when their separate cost is unknown. Factory category alone does not establish inclusion; the explicit declaration does.",
        "Vehicle make, model, year, exact variant and location have no lookup-based pricing. Standard colour has no numerical surcharge in this model; provider treatment of paint and location needs verification.",
        "The scenario band is an arbitrary sensitivity demonstration, not a statistically calibrated prediction or confidence interval. Input coverage is not a measure of accuracy.",
        "A provider must verify disclosures, valuation, eligibility and coverage conditions before giving a real quote. This demo cannot promise coverage or a final premium.",
    ]
    if unknown_factor_keys:
        assumptions.append("Unanswered rating inputs are neutral solely for arithmetic: "
                           + ", ".join(labels[key] for key in unknown_factor_keys)
                           + ". They remain unknown, not zero-risk answers.")
    if profile["carHire"] == "unknown" or profile["creditShortfall"] == "unknown":
        assumptions.append("Unanswered optional-cover selections add no amount in the demo and remain unanswered; no choice has been inferred.")
    return assumptions


def estimate(data):
    """Return one reproducible report; never persist input or create a lead."""
    config = get_config()
    profile = normalize_profile(data)
    summary, extras_added = summarize_extras(profile)
    vehicle_value = decimal_number(profile["vehicleValue"])
    insured_value = vehicle_value + extras_added
    reference_value = decimal_number(config["referenceVehicleValue"])
    reference_monthly = decimal_number(config["referenceMonthlyPremium"])
    basic_amount = reference_monthly * vehicle_value / reference_value
    value_linked_amount = reference_monthly * insured_value / reference_value
    breakdown = EstimateBreakdown()
    breakdown.add("basic_reference", "Basic illustrative reference",
                  f"Invented {format_rand(config['referenceMonthlyPremium'])} reference at {format_rand(config['referenceVehicleValue'])}, scaled only by the declared vehicle value. This is not a live provider or competitor quote.",
                  basic_amount, "base")
    breakdown.add("extras_value", "Extras outside declared value",
                  "Only explicitly excluded extras with a known cost add value. Already included items and unresolved extras add zero incremental value.",
                  value_linked_amount, "value")
    for key, label, factor, explanation in selected_factors(profile, config):
        breakdown.add(key, label, explanation,
                      breakdown.current * decimal_number(factor), "factor", factor)
    if profile["carHire"] == "yes":
        breakdown.add("carHire", "Car hire option", "Invented flat demo amount; actual benefit limits and terms need provider verification.",
                      breakdown.current + decimal_number(config["optionalMonthly"]["carHire"]), "optional")
    if profile["creditShortfall"] == "yes" and profile["finance"] == "financed":
        breakdown.add("creditShortfall", "Credit shortfall option", "Invented flat demo amount for declared financed vehicles. Actual finance and coverage conditions need provider verification.",
                      breakdown.current + decimal_number(config["optionalMonthly"]["creditShortfall"]), "optional")
    completeness = calculate_completeness(profile, config)
    review_items, unpriced_count = build_review_items(profile, summary, completeness)
    benchmark = money(basic_amount)
    detailed = money(breakdown.current)
    difference = detailed - benchmark
    # A permitted positive sub-cent value may display a zero benchmark. A
    # percentage relative to displayed zero would be misleading or infinite.
    difference_percent = (float(money(difference * 100 / benchmark))
                          if benchmark else None)
    assumptions = build_assumptions(profile, config)
    if benchmark == 0:
        assumptions.append("The benchmark rounds below one cent; percentage change is undefined and is returned as null.")
    return {
        "meta": {key: config[key] for key in ("modelVersion", "label", "currency", "calibrated", "notice")},
        "profile": profile,
        "benchmarkMonthly": float(benchmark),
        "illustrativeMonthly": float(detailed),
        "differenceMonthly": float(difference),
        "differencePercent": difference_percent,
        "range": calculate_scenario_range(detailed, completeness, unpriced_count, config),
        "declaredVehicleValue": json_money(vehicle_value),
        "extrasAddedValue": json_money(extras_added),
        "insuredValueForDemo": json_money(insured_value),
        "extrasSummary": summary,
        "breakdown": breakdown.items,
        "completeness": completeness,
        "reviewItems": review_items,
        "assumptions": assumptions,
    }
