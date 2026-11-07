"""Check the demo's arithmetic, disclosure rules and stateless HTTP boundary.

These checks establish predictable proof-of-concept behaviour. They do not
establish that the fabricated model predicts an insurer's final premium.
"""

from copy import deepcopy
from datetime import date
from decimal import Decimal
import http.client
import json
from pathlib import Path
import sqlite3
import tempfile
import threading
import unittest

from hub.insurance import estimate, get_config
from hub.validation import ApiError
from server import make_server


def confirmed_polo():
    """Only the vehicle facts supplied by the user; driver answers stay unknown."""
    return {
        "make": "Volkswagen",
        "model": "Polo GTI",
        "year": 2026,
        "vehicleValue": 620000,
        "colour": "White",
        "modifications": "none",
        "extrasConfirmed": True,
        "extras": [{
            "name": "Factory sunroof",
            "category": "factory",
            "value": None,
            "includedInVehicleValue": True,
        }],
    }


def complete_sample(**overrides):
    """Invented neutral answers for tests, never represented as the user's facts."""
    payload = confirmed_polo()
    payload.update({
        "variant": "Sample GTI variant",
        "paintFinish": "standard",
        "valuationBasis": "retail",
        "locationDescription": "Fictional suburb for demonstration",
        "driverAge": 35,
        "licenceYears": 15,
        "claimsLast3Years": 0,
        "annualKm": 15000,
        "usage": "private",
        "overnightParking": "garage",
        "tracker": "active",
        "finance": "financed",
        "coverType": "comprehensive",
        "excess": 5000,
        "carHire": "no",
        "creditShortfall": "no",
    })
    payload.update(overrides)
    return payload


def money(value):
    """Use decimal cents for assertions rather than binary floating point sums."""
    return Decimal(str(value)).quantize(Decimal("0.01"))


class InsuranceEstimateTests(unittest.TestCase):
    def test_config_and_every_report_identify_the_uncalibrated_demo(self):
        config = get_config()
        self.assertEqual(config["modelVersion"], "demo-motor-v1")
        self.assertEqual(config["currency"], "ZAR")
        self.assertIs(config["calibrated"], False)
        self.assertTrue(config["notice"])
        report = estimate(confirmed_polo())
        self.assertIs(report["meta"]["calibrated"], False)
        self.assertEqual(report["meta"]["modelVersion"], config["modelVersion"])
        self.assertTrue(report["assumptions"])
        self.assertTrue(report["range"]["basis"])

    def test_unanswered_driver_fields_remain_unknown(self):
        report = estimate(confirmed_polo())
        self.assertIsNone(report["profile"]["driverAge"])
        self.assertIsNone(report["profile"]["claimsLast3Years"])
        self.assertEqual(report["profile"]["usage"], "unknown")
        self.assertEqual(report["profile"]["coverType"], "unknown")
        missing = {item["key"] for item in report["completeness"]["missing"]}
        self.assertIn("driverAge", missing)
        self.assertIn("claimsLast3Years", missing)
        self.assertIn("usage", missing)
        self.assertEqual(report["completeness"]["total"], 22)
        self.assertLess(report["completeness"]["percent"], 100)
        self.assertEqual(report["benchmarkMonthly"], 2000)
        self.assertEqual(report["illustrativeMonthly"], 2000)

    def test_included_sunroof_is_not_charged_again_even_without_separate_cost(self):
        included_unknown = estimate(complete_sample())
        payload = complete_sample()
        payload["extras"][0]["value"] = 25000
        included_known = estimate(payload)
        for report in [included_unknown, included_known]:
            self.assertEqual(report["extrasAddedValue"], 0)
            self.assertEqual(report["insuredValueForDemo"], 620000)
            self.assertEqual(report["illustrativeMonthly"], 2000)
            self.assertEqual(report["extrasSummary"][0]["status"], "included")
            self.assertEqual(report["extrasSummary"][0]["addedValue"], 0)
            self.assertEqual(report["completeness"]["percent"], 100)
        self.assertEqual(included_unknown["range"], included_known["range"])

    def test_explicitly_nonincluded_extra_increases_value_once(self):
        report = estimate(complete_sample(extras=[{
            "name": "Sample roof rack", "category": "aftermarket",
            "value": 31000, "includedInVehicleValue": False,
        }]))
        self.assertEqual(report["declaredVehicleValue"], 620000)
        self.assertEqual(report["extrasAddedValue"], 31000)
        self.assertEqual(report["insuredValueForDemo"], 651000)
        self.assertEqual(report["benchmarkMonthly"], 2000)
        self.assertEqual(report["illustrativeMonthly"], 2100)
        self.assertEqual(report["extrasSummary"][0]["status"], "added")

    def test_unknown_extra_price_or_inclusion_is_not_invented(self):
        examples = [(None, False, "extras-costs"), (25000, None, "extras-inclusion")]
        for value, inclusion, missing_key in examples:
            with self.subTest(value=value, inclusion=inclusion):
                report = estimate(complete_sample(extras=[{
                    "name": "Sample accessory", "category": "factory",
                    "value": value, "includedInVehicleValue": inclusion,
                }]))
                self.assertEqual(report["extrasAddedValue"], 0)
                self.assertEqual(report["illustrativeMonthly"], 2000)
                self.assertEqual(report["extrasSummary"][0]["status"], "unpriced")
                self.assertIn(missing_key, {item["key"] for item in report["completeness"]["missing"]})
                self.assertGreater(len(report["reviewItems"]), 1)

    def test_empty_inventory_is_complete_only_after_confirmation(self):
        unconfirmed = estimate(complete_sample(extras=[], extrasConfirmed=None))
        confirmed = estimate(complete_sample(extras=[], extrasConfirmed=True))
        missing = {item["key"] for item in unconfirmed["completeness"]["missing"]}
        self.assertTrue({"extras-costs", "extras-inclusion", "extras-inventory"} <= missing)
        self.assertEqual(confirmed["completeness"]["percent"], 100)
        denied = estimate(complete_sample(extras=[], extrasConfirmed=False))
        self.assertNotIn("extrasConfirmed", {item["key"] for item in denied["completeness"]["missing"]})
        self.assertIn("extras-inventory", {item["key"] for item in denied["completeness"]["missing"]})
        self.assertTrue(denied["reviewItems"])

    def test_duplicate_extras_are_rejected_after_name_normalization(self):
        first = confirmed_polo()["extras"][0]
        duplicate = {**first, "name": " FACTORY   SUNROOF "}
        with self.assertRaises(ApiError) as caught:
            estimate(complete_sample(extras=[first, duplicate]))
        self.assertEqual(caught.exception.status, 400)

    def test_colour_has_no_invented_pricing_factor(self):
        white = estimate(complete_sample(colour="White"))
        red = estimate(complete_sample(colour="Red"))
        self.assertEqual(white["illustrativeMonthly"], red["illustrativeMonthly"])
        self.assertEqual(white["breakdown"], red["breakdown"])
        self.assertEqual(white["range"], red["range"])

    def test_performance_extra_triggers_review_even_when_modifications_say_none(self):
        plain = estimate(complete_sample())
        performance = estimate(complete_sample(extras=[{
            "name": "Sample tuning", "category": "performance",
            "value": 15000, "includedInVehicleValue": True,
        }]))
        self.assertEqual(performance["profile"]["modifications"], "none")
        self.assertEqual(performance["illustrativeMonthly"], plain["illustrativeMonthly"])
        self.assertGreater(len(performance["reviewItems"]), len(plain["reviewItems"]))
        self.assertGreater(performance["range"]["marginPercent"], plain["range"]["marginPercent"])
        self.assertIn("performance", json.dumps(performance["reviewItems"]).lower())

    def test_custom_paint_requires_review_without_an_unapproved_tariff(self):
        plain = estimate(complete_sample())
        custom = estimate(complete_sample(paintFinish="custom"))
        self.assertEqual(custom["illustrativeMonthly"], plain["illustrativeMonthly"])
        self.assertGreater(len(custom["reviewItems"]), len(plain["reviewItems"]))
        self.assertGreater(custom["range"]["marginPercent"], plain["range"]["marginPercent"])

    def test_complete_intake_still_requires_provider_verification(self):
        report = estimate(complete_sample())
        self.assertEqual(report["completeness"]["answered"], 22)
        self.assertEqual(report["completeness"]["missing"], [])
        self.assertTrue(report["reviewItems"])
        self.assertIn("insurer", json.dumps(report["reviewItems"]).lower())
        self.assertIs(report["meta"]["calibrated"], False)
        self.assertGreater(report["range"]["marginPercent"], 0)
        self.assertLess(report["range"]["low"], report["illustrativeMonthly"])
        self.assertGreater(report["range"]["high"], report["illustrativeMonthly"])
        self.assertGreater(estimate(confirmed_polo())["range"]["marginPercent"], report["range"]["marginPercent"])

    def test_selected_demo_factors_change_only_their_explained_arithmetic(self):
        examples = [
            ({"driverAge": 24}, 2500),
            ({"licenceYears": 2}, 2300),
            ({"claimsLast3Years": 1}, 2300),
            ({"claimsLast3Years": 2}, 2600),
            ({"annualKm": 10000}, 1900),
            ({"annualKm": 20001}, 2200),
            ({"usage": "business"}, 2240),
            ({"usage": "delivery"}, 2500),
            ({"overnightParking": "street"}, 2360),
            ({"tracker": "none"}, 2160),
            ({"coverType": "third_party"}, 960),
            ({"excess": 1000}, 2300),
            ({"excess": 10000}, 1840),
            ({"carHire": "yes"}, 2090),
            ({"creditShortfall": "yes"}, 2045),
        ]
        for changes, expected in examples:
            with self.subTest(changes=changes):
                report = estimate(complete_sample(**changes))
                self.assertEqual(money(report["illustrativeMonthly"]), money(expected))

    def test_owned_shortfall_is_flagged_and_cannot_add_a_charge(self):
        report = estimate(complete_sample(finance="owned", creditShortfall="yes"))
        without_shortfall = estimate(complete_sample(finance="owned"))
        self.assertEqual(report["illustrativeMonthly"], without_shortfall["illustrativeMonthly"])
        self.assertGreater(len(report["reviewItems"]), len(without_shortfall["reviewItems"]))
        self.assertIn("shortfall", json.dumps(report["reviewItems"]).lower())

    def test_shortfall_with_unknown_finance_remains_unpriced(self):
        report = estimate(complete_sample(finance="unknown", creditShortfall="yes"))
        self.assertEqual(report["illustrativeMonthly"], 2000)
        self.assertIn("finance", {item["key"] for item in report["completeness"]["missing"]})
        self.assertIn("shortfall", json.dumps(report["reviewItems"]).lower())
        self.assertGreater(len(report["reviewItems"]), len(estimate(complete_sample())["reviewItems"]))

    def test_line_item_cents_reconcile_for_a_complex_fractional_scenario(self):
        payload = complete_sample(
            vehicleValue=619999.97, driverAge=24, licenceYears=2,
            claimsLast3Years=2, annualKm=32000, usage="business",
            overnightParking="street", tracker="none", excess=1750,
            carHire="yes", creditShortfall="yes",
            extras=[{"name": "Sample rack", "category": "aftermarket", "value": 12345.67, "includedInVehicleValue": False}],
        )
        report = estimate(payload)
        previous = money(0)
        total = money(0)
        adjustments = money(0)
        for item in report["breakdown"]:
            self.assertEqual(money(item["before"]), previous)
            self.assertEqual(money(item["after"]) - money(item["before"]), money(item["amount"]))
            previous = money(item["after"])
            total += money(item["amount"])
            if item["kind"] != "base":
                adjustments += money(item["amount"])
        self.assertEqual(total, money(report["illustrativeMonthly"]))
        self.assertEqual(adjustments, money(report["differenceMonthly"]))
        self.assertEqual(money(report["illustrativeMonthly"]) - money(report["benchmarkMonthly"]), money(report["differenceMonthly"]))

    def test_invalid_numbers_enums_and_boolean_impersonations_are_rejected(self):
        examples = [
            {"vehicleValue": True}, {"vehicleValue": float("nan")},
            {"vehicleValue": float("inf")}, {"vehicleValue": "620000"},
            {"vehicleValue": 0}, {"vehicleValue": 10000001},
            {"vehicleValue": 10 ** 1000}, {"year": True},
            {"year": 1899}, {"year": date.today().year + 2}, {"year": 2026.5},
            {"driverAge": True}, {"driverAge": 17}, {"driverAge": 101},
            {"licenceYears": -1}, {"licenceYears": 81},
            {"driverAge": 25, "licenceYears": 26},
            {"claimsLast3Years": False}, {"claimsLast3Years": 1.5},
            {"claimsLast3Years": 21}, {"annualKm": 1.5},
            {"annualKm": 200001}, {"excess": -1}, {"excess": 100001},
            {"usage": "commuting"}, {"tracker": True},
            {"extrasConfirmed": "yes"}, {"paintFinish": "blue"},
            {"make": ""}, {"model": None}, {"colour": "x" * 61},
            {"extras": "sunroof"},
        ]
        for changes in examples:
            with self.subTest(changes=changes):
                with self.assertRaises(ApiError) as caught:
                    estimate(complete_sample(**changes))
                self.assertEqual(caught.exception.status, 400)

    def test_invalid_extra_shape_money_and_inclusion_are_rejected(self):
        examples = [
            {"name": "", "category": "factory", "value": 0, "includedInVehicleValue": True},
            {"name": "Roof rack", "category": "unknown", "value": 0, "includedInVehicleValue": False},
            {"name": "Roof rack", "category": "factory", "value": True, "includedInVehicleValue": True},
            {"name": "Roof rack", "category": "factory", "value": float("nan"), "includedInVehicleValue": True},
            {"name": "Roof rack", "category": "factory", "value": -1, "includedInVehicleValue": False},
            {"name": "Roof rack", "category": "factory", "value": 1000001, "includedInVehicleValue": False},
            {"name": "Roof rack", "category": "factory", "value": 1, "includedInVehicleValue": "yes"},
            "Roof rack",
        ]
        for extra in examples:
            with self.subTest(extra=extra):
                with self.assertRaises(ApiError) as caught:
                    estimate(complete_sample(extras=[extra]))
                self.assertEqual(caught.exception.status, 400)
        with self.assertRaises(ApiError):
            estimate(complete_sample(extras=[{"name": f"Extra {index}", "category": "factory", "value": 1, "includedInVehicleValue": True} for index in range(21)]))

    def test_estimate_does_not_mutate_input_and_repeats_deterministically(self):
        payload = complete_sample()
        original = deepcopy(payload)
        first = estimate(payload)
        self.assertEqual(payload, original)
        self.assertEqual(first, estimate(payload))


class InsuranceHTTPTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.database_path = Path(self.directory.name) / "insurance-http.sqlite3"
        self.server = make_server(port=0, database_path=self.database_path)
        original_handler = self.server.RequestHandlerClass

        class QuietRequestHandler(original_handler):
            def log_message(self, format, *arguments):
                pass

        self.server.RequestHandlerClass = QuietRequestHandler
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.port = self.server.server_port
        self.origin = f"http://127.0.0.1:{self.port}"
        status, session, _ = self.request("GET", "/api/session")
        self.assertEqual(status, 200, session)
        self.token = session["csrfToken"]
        self.company_id = session["defaultCompanyId"]

    def tearDown(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=5)
        self.directory.cleanup()

    def request(self, method, path, payload=None, headers=None):
        request_headers = {"Accept": "application/json"}
        body = None
        if payload is not None:
            body = json.dumps(payload).encode("utf-8")
            request_headers["Content-Type"] = "application/json"
        if headers:
            request_headers.update(headers)
        connection = http.client.HTTPConnection("127.0.0.1", self.port, timeout=10)
        try:
            connection.request(method, path, body, request_headers)
            response = connection.getresponse()
            raw = response.read()
            try:
                result = json.loads(raw) if raw else None
            except (json.JSONDecodeError, UnicodeDecodeError):
                result = raw.decode("utf-8", errors="replace")
            return response.status, result, dict(response.getheaders())
        finally:
            connection.close()

    def write(self, payload, headers=None, path="/api/insurance/estimate"):
        request_headers = {"Origin": self.origin, "X-CSRF-Token": self.token}
        request_headers.update(headers or {})
        return self.request("POST", path, payload, request_headers)

    def database_snapshot(self):
        connection = sqlite3.connect(self.database_path)
        try:
            return "\n".join(connection.iterdump())
        finally:
            # SQLite's context manager handles transactions, not closing the
            # file. Explicit close also lets Windows remove the temporary DB.
            connection.close()

    def test_config_and_estimate_are_stateless_and_leave_base_apis_unchanged(self):
        status, initial_export, _ = self.request("GET", f"/api/companies/{self.company_id}/export")
        self.assertEqual(status, 200, initial_export)
        before = self.database_snapshot()
        status, config, _ = self.request("GET", "/api/insurance/config")
        self.assertEqual(status, 200, config)
        self.assertIs(config["calibrated"], False)
        for payload in [confirmed_polo(), complete_sample(usage="delivery"), complete_sample()]:
            status, report, headers = self.write(payload)
            self.assertEqual(status, 200, report)
            self.assertIs(report["meta"]["calibrated"], False)
            self.assertEqual(headers.get("Cache-Control"), "no-store")
        self.assertEqual(self.database_snapshot(), before)
        status, final_export, _ = self.request("GET", f"/api/companies/{self.company_id}/export")
        self.assertEqual(status, 200, final_export)
        # A fresh export has a fresh timestamp even when saved data is identical.
        initial_export.pop("exportedAt")
        final_export.pop("exportedAt")
        self.assertEqual(final_export, initial_export)

    def test_estimate_requires_token_and_same_origin(self):
        before = self.database_snapshot()
        for headers in [
            {"X-CSRF-Token": ""},
            {"X-CSRF-Token": "invalid"},
            {"Origin": "https://unrelated.example"},
            {"Sec-Fetch-Site": "cross-site"},
        ]:
            with self.subTest(headers=headers):
                status, error, _ = self.write(confirmed_polo(), headers)
                self.assertEqual(status, 403, error)
        self.assertEqual(self.database_snapshot(), before)

    def test_insurance_routes_reject_foreign_hosts(self):
        status, error, _ = self.request("GET", "/api/insurance/config", headers={"Host": "unrelated.example"})
        self.assertEqual(status, 403, error)
        status, error, _ = self.write(confirmed_polo(), {"Host": "unrelated.example"})
        self.assertEqual(status, 403, error)

    def test_invalid_estimate_and_oversized_body_return_client_errors(self):
        status, error, _ = self.write(complete_sample(vehicleValue=float("nan")))
        self.assertEqual(status, 400, error)
        status, error, _ = self.request(
            "POST", "/api/insurance/estimate", headers={
                "Origin": self.origin, "X-CSRF-Token": self.token,
                "Content-Type": "application/json", "Content-Length": "1000000",
            },
        )
        self.assertEqual(status, 413, error)

    def test_unknown_insurance_routes_do_not_fall_through_to_business_writes(self):
        before = self.database_snapshot()
        status, error, _ = self.request("GET", "/api/insurance/not-a-route")
        self.assertEqual(status, 404, error)
        status, error, _ = self.write(confirmed_polo(), path="/api/insurance/not-a-route")
        self.assertEqual(status, 404, error)
        self.assertEqual(self.database_snapshot(), before)

    def test_quote_lab_page_is_served_with_local_security_headers(self):
        status, html, headers = self.request("GET", "/insurance")
        self.assertEqual(status, 200, html)
        self.assertIn("Quote Lab", html)
        self.assertIn("text/html", headers.get("Content-Type", ""))
        self.assertIn("frame-ancestors 'none'", headers.get("Content-Security-Policy", ""))
        status, dashboard, _ = self.request("GET", "/")
        self.assertEqual(status, 200, dashboard)
        self.assertIn("Launchpad", dashboard)


if __name__ == "__main__":
    unittest.main()
