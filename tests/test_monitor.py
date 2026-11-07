import io
import json
import sqlite3
import sys
import tempfile
import threading
import unittest
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from datetime import date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "dashboard"))
sys.path.insert(0, str(ROOT / "demo"))
from model import Store, cents, previous_year, tax_year_start
from server import make_server
from mcp_server import MCP
from reporting import build_report, render_html


class MonitorTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.store = Store(Path(self.temp.name) / "records.sqlite3")

    def tearDown(self):
        self.temp.cleanup()

    def entry(self, kind="sale", amount="100.00", reference="A", venture="reporting", when="2026-09-01", **extra):
        return self.store.add_entry({"venture_id": venture, "date": when, "kind": kind, "amount": amount,
                                     "reference": reference, "description": "Test record", "evidence": "test-proof.pdf", **extra})["id"]

    def test_cash_categories_reserve_and_reconciliation(self):
        payment = self.entry(amount="1000.00")
        self.entry("refund", "100.00", "REF", related_id=payment)
        self.entry("expense", "50.00", "FEE")
        self.entry("owner_deposit", "200.00", "CAP")
        self.entry("owner_draw", "100.00", "DRAW")
        self.entry("income_tax", "75.00", "TAX")
        self.store.update_settings({"reserve_percent": 30})
        t = self.store.snapshot(as_of="2026-09-29")["totals"]
        self.assertEqual(t["cash_surplus_cents"], 85_000)
        self.assertEqual(t["reserve_target_cents"], 25_500)
        self.assertEqual(t["cash_movement_cents"], 87_500)
        self.assertEqual(t["income_tax_paid_cents"], 7500)

    def test_money_precision_and_invalid_values(self):
        self.assertEqual(cents("0.29"), 29)
        for invalid in ["0.001", "NaN", "Infinity", "-1", True, None, "100000001"]:
            with self.subTest(value=invalid), self.assertRaises(ValueError):
                cents(invalid)

    def test_duplicate_future_and_over_refund_rejected(self):
        payment = self.entry()
        with self.assertRaises(ValueError):
            self.entry(reference="A")
        with self.assertRaises(ValueError):
            self.entry(reference="FUTURE", when="2099-01-01")
        self.entry("refund", "70.00", "REF1", related_id=payment)
        with self.assertRaises(ValueError):
            self.entry("refund", "40.00", "REF2", related_id=payment)
        with self.assertRaises(ValueError):
            self.entry("refund", "5.00", "REF3", venture="mcp", related_id=payment)
        with self.assertRaises(ValueError):
            self.entry("refund", "5.00", "REF4", when="2026-08-31", related_id=payment)

    def test_concurrent_refunds_do_not_overdraw_original(self):
        payment = self.entry()
        def refund(reference):
            try:
                self.entry("refund", "70.00", reference, related_id=payment)
                return True
            except ValueError:
                return False
        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(refund, ["R1", "R2"]))
        self.assertEqual(sum(outcomes), 1)
        self.assertEqual(self.store.snapshot(as_of="2026-09-29")["totals"]["refunds_cents"], 7000)

    def test_vat_not_revenue_and_proportional_refund(self):
        with self.assertRaises(ValueError):
            self.entry(amount="115.00", vat="15.00")
        self.store.update_settings({"vat_status": "registered"})
        payment = self.entry(amount="115.00", vat="15.00")
        with self.assertRaises(ValueError):
            self.entry("refund", "57.50", "BADREF", related_id=payment, vat="0")
        self.entry("refund", "57.50", "REF", related_id=payment, vat="7.50")
        t = self.store.snapshot(as_of="2026-09-29")["totals"]
        self.assertEqual(t["net_receipts_cents"], 5000)
        self.assertEqual(t["vat_collected_cents"], 750)

    def test_corrections_retain_audit_and_protect_linked_refunds(self):
        payment = self.entry()
        refund = self.entry("refund", "10.00", "REF", related_id=payment)
        with self.assertRaises(ValueError):
            self.store.void_entry(payment, "Wrong entry")
        self.store.void_entry(refund, "Incorrect refund")
        self.store.void_entry(payment, "Incorrect test payment")
        self.assertEqual(self.store.snapshot(as_of="2026-09-29")["totals"]["receipts_cents"], 0)
        self.assertEqual(len(self.store.export()["tables"]["ledger"]), 2)
        self.assertEqual(len(self.store.export()["tables"]["audit"]), 4)

    def test_tax_year_and_rolling_window_aggregate_ventures(self):
        self.assertEqual(tax_year_start(date(2027, 2, 28)), date(2026, 3, 1))
        self.assertEqual(tax_year_start(date(2027, 3, 1)), date(2027, 3, 1))
        self.assertEqual(previous_year(date(2024, 2, 29)), date(2023, 2, 28))
        self.entry(reference="EXCLUDED", amount="500.00", when="2025-09-29")
        self.entry(reference="INCLUDED", amount="1200000.00", when="2025-09-30")
        self.entry(reference="OTHER", amount="900000.00", when="2026-09-01", venture="mcp")
        self.entry(reference="OTHER-TAXYEAR", amount="50.00", when="2026-02-28")
        report = self.store.snapshot(venture_id="reporting", as_of="2026-09-29")
        self.assertEqual(report["totals"]["receipts_cents"], 0)
        self.assertEqual(report["vat_monitor"]["recorded_receipts_ex_vat_cents"], 210_005_000)
        self.assertTrue(any("approaching" in a["text"] for a in report["alerts"]))

    def test_pipeline_not_revenue_and_budget_alert(self):
        self.store.add_opportunity({"venture_id": "reporting", "customer": "Client alias", "value": "3500.00", "stage": "Quoted", "consent_note": "Requested quote", "next_action": "Review sample"})
        self.entry("expense", "5.00", "COST")
        report = self.store.snapshot(as_of="2026-09-29")
        self.assertEqual(report["totals"]["receipts_cents"], 0)
        self.assertEqual(report["totals"]["cash_surplus_cents"], -500)
        self.assertTrue(any("budget" in a["text"] for a in report["alerts"]))
        self.store.update_settings({"reserve_percent": 30})
        self.assertEqual(self.store.snapshot(as_of="2026-09-29")["totals"]["reserve_target_cents"], 0)

    def test_mcp_initialization_validation_and_read_only_database(self):
        mcp = MCP(Store(self.store.path, readonly=True))
        def call(method, params=None):
            return mcp.handle({"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}})
        self.assertIn("error", call("tools/list"))
        self.assertEqual(call("initialize", {"protocolVersion": "2025-11-25"})["result"]["protocolVersion"], "2025-11-25")
        mcp.handle({"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(len(call("tools/list")["result"]["tools"]), 2)
        result = call("tools/call", {"name": "business_summary", "arguments": {}})["result"]
        self.assertFalse(result["isError"])
        self.assertEqual(json.loads(result["content"][0]["text"])["totals"]["receipts_cents"], 0)
        self.assertIn("error", call("tools/call", {"name": "business_summary", "arguments": {"send_money": True}}))
        with closing(mcp.store.connect()) as db, self.assertRaises(sqlite3.OperationalError):
            db.execute("DELETE FROM ledger")

    def test_http_origin_token_host_and_actual_write(self):
        with make_server(self.store, port=0) as server:
            thread = threading.Thread(target=server.serve_forever, daemon=True)
            thread.start()
            base = f"http://127.0.0.1:{server.server_port}"
            try:
                with urllib.request.urlopen(base + "/api/bootstrap") as response:
                    token = json.load(response)["token"]
                data = {"venture_id": "reporting", "date": "2026-09-01", "kind": "sale", "amount": "35.00", "reference": "HTTP", "description": "HTTP test", "evidence": "proof.pdf"}
                for headers in [{}, {"Origin": "https://evil.example", "X-Session-Token": token}]:
                    request = urllib.request.Request(base + "/api/entry", json.dumps(data).encode(), {"Content-Type": "application/json", **headers})
                    with self.assertRaises(urllib.error.HTTPError) as error:
                        urllib.request.urlopen(request)
                    self.assertEqual(error.exception.code, 403)
                headers = {"Content-Type": "application/json", "Origin": base, "X-Session-Token": token}
                with urllib.request.urlopen(urllib.request.Request(base + "/api/entry", json.dumps(data).encode(), headers)) as response:
                    self.assertEqual(response.status, 201)
                self.assertEqual(self.store.snapshot(as_of="2026-09-29")["totals"]["receipts_cents"], 3500)
                with self.assertRaises(urllib.error.HTTPError) as error:
                    urllib.request.urlopen(urllib.request.Request(base + "/api/snapshot", headers={"Host": "evil.example"}))
                self.assertEqual(error.exception.code, 403)
            finally:
                server.shutdown()
                thread.join()


class ReportingDemoTests(unittest.TestCase):
    def test_dates_totals_partial_payment_and_due_date(self):
        report = build_report(ROOT / "demo/sample-sales.csv", ROOT / "demo/sample-invoices.csv", "2026-09-21", "2026-09-27", "2026-09-28")
        self.assertEqual(report["sales_ex_vat_cents"], 1_230_000)
        self.assertEqual(report["transaction_count"], 4)
        self.assertEqual(report["overdue_ex_vat_cents"], 400_000)
        self.assertEqual(report["outstanding_ex_vat_cents"], 650_000)
        self.assertIn("SYNTHETIC", render_html(report))
        report = build_report(ROOT / "demo/sample-sales.csv", ROOT / "demo/sample-invoices.csv", "2026-09-21", "2026-09-27", "2026-09-20")
        self.assertEqual(report["overdue_ex_vat_cents"], 200_000)  # Due today is not overdue.

    def test_duplicate_ids_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            sample = Path(directory) / "bad.csv"
            sample.write_text("transaction_id,date,client,amount_ex_vat\nA,2026-09-21,Client,10.00\nA,2026-09-22,Client,20.00\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate ID"):
                build_report(sample, ROOT / "demo/sample-invoices.csv", "2026-09-21", "2026-09-27", "2026-09-28")


if __name__ == "__main__":
    unittest.main()
