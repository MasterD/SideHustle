"""Local management records. Integer cents; no tax filing or payment automation."""
import calendar
import json
import re
import sqlite3
import uuid
from contextlib import closing
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "data" / "sidehustle.sqlite3"
VAT_THRESHOLD_CENTS = 230_000_000  # SARS administrative threshold, checked 2026-09-29.
KINDS = {"sale", "refund", "expense", "income_tax", "owner_deposit", "owner_draw"}
SEEDS = [
    ("reporting", "Reporting pilot", "Fixed-price reporting automation", 350_000, "First offer to validate"),
    ("mcp", "MCP Integrations", "Customer-owned, read-only integrations", 950_000, "After a successful reporting pilot"),
    ("templates", "Digital Templates", "Reusable reporting kits", 29_900, "After repeated customer demand"),
]


def today():
    return datetime.now(timezone(timedelta(hours=2))).date()


def iso_date(value):
    if not isinstance(value, str) or not re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
        raise ValueError("Use a date in YYYY-MM-DD format.")
    return date.fromisoformat(value)


def cents(value):
    if isinstance(value, bool):
        raise ValueError("Enter a monetary amount.")
    try:
        amount = Decimal(str(value))
        if not amount.is_finite() or amount < 0 or amount > Decimal("100000000"):
            raise ValueError("Amount must be between R0 and R100,000,000.")
        rounded = amount.quantize(Decimal("0.01"))
        if rounded != amount:
            raise ValueError("Amounts may have at most two decimal places.")
        return int(rounded * 100)
    except InvalidOperation as exc:
        raise ValueError("Enter a valid monetary amount.") from exc


def text_field(value, label, maximum=500, required=False):
    if not isinstance(value, str):
        raise ValueError(f"{label} must be text.")
    value = value.strip()
    if len(value) > maximum or (required and not value):
        raise ValueError(f"{label} must contain {'1' if required else '0'}–{maximum} characters.")
    return value


def tax_year_start(on_date):
    return date(on_date.year if on_date.month >= 3 else on_date.year - 1, 3, 1)


def previous_year(on_date):
    return on_date.replace(year=on_date.year - 1,
                           day=min(on_date.day, calendar.monthrange(on_date.year - 1, on_date.month)[1]))


class Store:
    def __init__(self, path=DEFAULT_DB, readonly=False):
        self.path = Path(path)
        self.readonly = readonly
        if readonly:
            if not self.path.is_file():
                raise ValueError("Start the dashboard once to create the records database.")
        else:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.initialize()

    def connect(self):
        db = sqlite3.connect(self.path.resolve().as_uri() + "?mode=ro", uri=True) if self.readonly else sqlite3.connect(self.path)
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        db.execute("PRAGMA busy_timeout=5000")
        return db

    def initialize(self):
        with closing(self.connect()) as db, db:
            db.executescript("""
                CREATE TABLE IF NOT EXISTS ventures (
                    id TEXT PRIMARY KEY, name TEXT NOT NULL, offer TEXT NOT NULL,
                    price_cents INTEGER NOT NULL, status TEXT NOT NULL DEFAULT 'Draft', note TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
                CREATE TABLE IF NOT EXISTS ledger (
                    id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id),
                    date TEXT NOT NULL, kind TEXT NOT NULL,
                    amount_cents INTEGER NOT NULL CHECK(amount_cents > 0),
                    vat_cents INTEGER NOT NULL DEFAULT 0 CHECK(vat_cents >= 0 AND vat_cents <= amount_cents),
                    reference TEXT NOT NULL UNIQUE, description TEXT NOT NULL,
                    evidence TEXT NOT NULL, related_id TEXT REFERENCES ledger(id),
                    recorded_at TEXT NOT NULL, void_reason TEXT, voided_at TEXT
                );
                CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger(date);
                CREATE INDEX IF NOT EXISTS idx_ledger_venture_date ON ledger(venture_id, date);
                CREATE TABLE IF NOT EXISTS opportunities (
                    id TEXT PRIMARY KEY, venture_id TEXT NOT NULL REFERENCES ventures(id),
                    customer TEXT NOT NULL, value_cents INTEGER NOT NULL,
                    stage TEXT NOT NULL, consent_note TEXT NOT NULL, next_action TEXT NOT NULL,
                    recorded_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS audit (
                    id INTEGER PRIMARY KEY, date TEXT NOT NULL, action TEXT NOT NULL, detail TEXT NOT NULL
                );
            """)
            db.executemany("INSERT OR IGNORE INTO ventures(id,name,offer,price_cents,note) VALUES(?,?,?,?,?)", SEEDS)
            db.execute("UPDATE ventures SET name='Reporting pilot' WHERE id='reporting' AND name='Reporting Studio'")
            for key, value in {"vat_status": "not_registered", "reserve_percent": None, "monthly_budget_cents": 0}.items():
                db.execute("INSERT OR IGNORE INTO settings VALUES(?,?)", (key, json.dumps(value)))
            db.execute("PRAGMA optimize")

    def settings(self):
        with closing(self.connect()) as db:
            return {r["key"]: json.loads(r["value"]) for r in db.execute("SELECT * FROM settings")}

    def launch_status(self):
        """Private owner-confirmed state. The public report omits the owner's identity."""
        fallback = {"offer_approved": False, "working_name": "Reporting Studio", "name_status": "proposed",
                    "manager_clearance": "pending", "email_status": "not_created", "candidate_email": "",
                    "email_availability": "unverified", "actual_email": None,
                    "publication_approved": False, "outreach_approved": False,
                    "public_deployment_status": "not_deployed", "public_website_url": None,
                    "hosting_account_status": "not_confirmed", "information_officer_registration_status": "not_confirmed",
                    "paia_manual_approval_status": "review_pending"}
        # Independent temporary / future taxpayer databases must not inherit this owner's approval.
        if self.path.resolve() != DEFAULT_DB.resolve():
            return fallback
        try:
            profile = json.loads((ROOT / "data" / "launch-profile.json").read_text(encoding="utf-8"))
            if not isinstance(profile, dict):
                return fallback
            return {key: profile.get(key, value) for key, value in fallback.items()}
        except (OSError, ValueError):
            return fallback

    def update_settings(self, payload):
        allowed = {"vat_status", "reserve_percent", "monthly_budget"}
        if not isinstance(payload, dict) or set(payload) - allowed:
            raise ValueError("Unknown setting.")
        changes = {}
        if "vat_status" in payload:
            if payload["vat_status"] not in {"unknown", "not_registered", "registered"}:
                raise ValueError("Select a valid VAT status.")
            changes["vat_status"] = payload["vat_status"]
        if "reserve_percent" in payload:
            value = payload["reserve_percent"]
            if value is not None:
                try:
                    value = Decimal(str(value))
                    if not value.is_finite() or value < 0 or value > 100:
                        raise ValueError()
                    value = float(value)
                except (InvalidOperation, ValueError):
                    raise ValueError("Reserve percentage must be 0–100 or left blank.")
            changes["reserve_percent"] = value
        if "monthly_budget" in payload:
            changes["monthly_budget_cents"] = cents(payload["monthly_budget"])
        with closing(self.connect()) as db, db:
            for key, value in changes.items():
                db.execute("UPDATE settings SET value=? WHERE key=?", (json.dumps(value), key))
            self._audit(db, "settings_updated", changes)
        return self.settings()

    def _audit(self, db, action, detail):
        db.execute("INSERT INTO audit(date,action,detail) VALUES(?,?,?)",
                   (datetime.now(timezone.utc).isoformat(), action, json.dumps(detail)))

    def _venture_exists(self, db, venture_id):
        if not db.execute("SELECT 1 FROM ventures WHERE id=?", (venture_id,)).fetchone():
            raise ValueError("Choose an existing venture.")

    def add_entry(self, payload):
        if not isinstance(payload, dict):
            raise ValueError("Entry must be an object.")
        allowed = {"venture_id", "date", "kind", "amount", "vat", "reference", "description", "evidence", "related_id"}
        if set(payload) - allowed:
            raise ValueError("Unknown entry field.")
        when = iso_date(payload.get("date"))
        if when > today():
            raise ValueError("Only record money already received or paid. Keep future deals in the pipeline.")
        kind = payload.get("kind")
        if kind not in KINDS:
            raise ValueError("Select a valid entry type.")
        amount = cents(payload.get("amount"))
        vat = cents(payload.get("vat", "0"))
        if not amount or vat > amount:
            raise ValueError("Amount must be positive and VAT cannot exceed it.")
        if vat and kind not in {"sale", "refund"}:
            raise ValueError("VAT field is for sales and refunds. Enter expenses gross; input VAT needs separate review.")
        if vat and self.settings()["vat_status"] != "registered":
            raise ValueError("Confirm registered VAT status before recording VAT collected.")
        reference = text_field(payload.get("reference", ""), "Unique bank / invoice reference", 120, True)
        description = text_field(payload.get("description", ""), "Description", 500, True)
        evidence = text_field(payload.get("evidence", ""), "Evidence filename", 500)
        related = payload.get("related_id") or None
        if related is not None and not isinstance(related, str):
            raise ValueError("Related sale ID must be text.")
        entry_id = str(uuid.uuid4())
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            self._venture_exists(db, payload.get("venture_id"))
            if kind == "refund":
                original = db.execute("SELECT * FROM ledger WHERE id=? AND kind='sale' AND void_reason IS NULL", (related,)).fetchone()
                if not original or original["venture_id"] != payload.get("venture_id"):
                    raise ValueError("Link a refund to an active sale from the same venture.")
                if when.isoformat() < original["date"]:
                    raise ValueError("A refund cannot precede the original payment.")
                refunded = db.execute("SELECT COALESCE(SUM(amount_cents),0), COALESCE(SUM(vat_cents),0) FROM ledger WHERE related_id=? AND void_reason IS NULL", (related,)).fetchone()
                if amount + refunded[0] > original["amount_cents"] or vat + refunded[1] > original["vat_cents"]:
                    raise ValueError("Refunds cannot exceed the original sale or VAT collected.")
                expected_vat = (original["vat_cents"] - refunded[1] if amount + refunded[0] == original["amount_cents"]
                                else int((Decimal(amount) * original["vat_cents"] / original["amount_cents"]).quantize(Decimal("1"))))
                if vat != expected_vat:
                    raise ValueError(f"This refund must include R{expected_vat / 100:.2f} VAT to match the original payment.")
            elif related:
                raise ValueError("Only a refund needs a related sale ID.")
            try:
                db.execute("INSERT INTO ledger(id,venture_id,date,kind,amount_cents,vat_cents,reference,description,evidence,related_id,recorded_at) VALUES(?,?,?,?,?,?,?,?,?,?,?)",
                           (entry_id, payload["venture_id"], when.isoformat(), kind, amount, vat, reference, description, evidence, related, datetime.now(timezone.utc).isoformat()))
            except sqlite3.IntegrityError as exc:
                raise ValueError("That reference is already recorded. Use a unique reference to prevent duplicate receipts.") from exc
            self._audit(db, "entry_added", {"id": entry_id, "reference": reference})
        return {"id": entry_id}

    def void_entry(self, entry_id, reason):
        reason = text_field(reason, "Correction reason", 500, True)
        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT * FROM ledger WHERE id=? AND void_reason IS NULL", (entry_id,)).fetchone()
            if not row:
                raise ValueError("Active entry not found.")
            if db.execute("SELECT 1 FROM ledger WHERE related_id=? AND void_reason IS NULL", (entry_id,)).fetchone():
                raise ValueError("Correct the linked refunds before correcting the original payment.")
            db.execute("UPDATE ledger SET void_reason=?, voided_at=? WHERE id=?",
                       (reason, datetime.now(timezone.utc).isoformat(), entry_id))
            self._audit(db, "entry_voided", {"id": entry_id, "reason": reason})
        return {"id": entry_id, "corrected": True}

    def add_opportunity(self, payload):
        if not isinstance(payload, dict) or set(payload) - {"venture_id", "customer", "value", "stage", "consent_note", "next_action"}:
            raise ValueError("Unknown pipeline field.")
        stage = payload.get("stage")
        if stage not in {"Discovery", "Quoted", "Agreed", "Closed"}:
            raise ValueError("Select a valid pipeline stage.")
        record = (str(uuid.uuid4()), payload.get("venture_id"), text_field(payload.get("customer", ""), "Customer alias", 120, True),
                  cents(payload.get("value")), stage, text_field(payload.get("consent_note", ""), "Contact permission", 500, True),
                  text_field(payload.get("next_action", ""), "Next action", 500, True), datetime.now(timezone.utc).isoformat())
        with closing(self.connect()) as db, db:
            self._venture_exists(db, record[1])
            db.execute("INSERT INTO opportunities VALUES(?,?,?,?,?,?,?,?)", record)
            self._audit(db, "opportunity_added", {"id": record[0]})
        return {"id": record[0]}

    def close_opportunity(self, entry_id):
        with closing(self.connect()) as db, db:
            result = db.execute("UPDATE opportunities SET stage='Closed' WHERE id=?", (entry_id,))
            if result.rowcount != 1:
                raise ValueError("Opportunity not found.")
            self._audit(db, "opportunity_closed", {"id": entry_id})
        return {"id": entry_id}

    def entries(self):
        with closing(self.connect()) as db:
            return [dict(r) for r in db.execute("SELECT ledger.*,ventures.name AS venture_name FROM ledger JOIN ventures ON ventures.id=ledger.venture_id ORDER BY date DESC,recorded_at DESC")]

    @staticmethod
    def totals(rows):
        totals = {"receipts_cents": 0, "refunds_cents": 0, "expenses_cents": 0, "vat_collected_cents": 0,
                  "income_tax_paid_cents": 0, "owner_deposits_cents": 0, "owner_draws_cents": 0}
        mapping = {"sale": "receipts_cents", "refund": "refunds_cents", "expense": "expenses_cents",
                   "income_tax": "income_tax_paid_cents", "owner_deposit": "owner_deposits_cents", "owner_draw": "owner_draws_cents"}
        for row in rows:
            if row["void_reason"]:
                continue
            totals[mapping[row["kind"]]] += row["amount_cents"]
            if row["kind"] in {"sale", "refund"}:
                totals["vat_collected_cents"] += row["vat_cents"] * (1 if row["kind"] == "sale" else -1)
        totals["net_receipts_cents"] = totals["receipts_cents"] - totals["refunds_cents"] - totals["vat_collected_cents"]
        totals["cash_surplus_cents"] = totals["net_receipts_cents"] - totals["expenses_cents"]
        totals["cash_movement_cents"] = (totals["receipts_cents"] - totals["refunds_cents"] - totals["expenses_cents"]
                                         - totals["income_tax_paid_cents"] + totals["owner_deposits_cents"] - totals["owner_draws_cents"])
        return totals

    def snapshot(self, scope="taxyear", venture_id="all", as_of=None):
        on_date = iso_date(as_of) if as_of is not None else today()
        if scope not in {"month", "taxyear", "all"}:
            raise ValueError("Choose month, taxyear or all.")
        start = on_date.replace(day=1) if scope == "month" else tax_year_start(on_date) if scope == "taxyear" else date.min
        with closing(self.connect()) as db:
            ventures = [dict(r) for r in db.execute("SELECT * FROM ventures ORDER BY rowid")]
            if venture_id != "all":
                self._venture_exists(db, venture_id)
            opportunities = [dict(r) for r in db.execute("SELECT * FROM opportunities ORDER BY recorded_at DESC")]
        all_rows = self.entries()
        selected = [r for r in all_rows if start.isoformat() <= r["date"] <= on_date.isoformat() and (venture_id == "all" or r["venture_id"] == venture_id)]
        settings = self.settings()
        launch = self.launch_status()
        totals = self.totals(selected)
        reserve = settings["reserve_percent"]
        totals["reserve_target_cents"] = None if reserve is None else int((Decimal(max(0, totals["cash_surplus_cents"])) * Decimal(str(reserve)) / 100).quantize(Decimal("1")))
        rolling_start = previous_year(on_date) + timedelta(days=1)
        rolling = self.totals([r for r in all_rows if rolling_start.isoformat() <= r["date"] <= on_date.isoformat()])
        month_expenses = self.totals([r for r in all_rows if on_date.replace(day=1).isoformat() <= r["date"] <= on_date.isoformat()])["expenses_cents"]
        alerts = [{"level": "info", "text": "Cash records need bank reconciliation and invoice review. Unpaid invoices, foreign sales, refundable deposits and other income are outside these totals."}]
        if not launch["offer_approved"]:
            alerts.insert(0, {"level": "action", "text": "The business direction and offer need owner approval."})
        if launch["manager_clearance"] not in {"cleared", "not_required"}:
            alerts.insert(0, {"level": "action", "text": "Manager clearance is pending. Keep public marketing, customer commitments and payments on hold."})
        if launch["name_status"] != "approved":
            alerts.append({"level": "action", "text": "The working business name is proposed. Confirm the name before publishing."})
        if launch["email_status"] != "created":
            alerts.append({"level": "action", "text": "The free email signup is prepared. No mailbox or available address is confirmed yet."})
        if not launch["publication_approved"] and not launch["outreach_approved"]:
            alerts.append({"level": "action", "text": "Launch materials are ready for review. Approve the final page and customer messages before publication or sending."})
        if launch["publication_approved"] and launch["public_deployment_status"] != "published":
            setup = []
            if launch["hosting_account_status"] != "ready_owner_confirmed":
                setup.append("free hosting account")
            if launch["information_officer_registration_status"] not in {"registered_owner_confirmed", "registered_verified"}:
                setup.append("Information Officer registration")
            if launch["paia_manual_approval_status"] != "approved":
                setup.append("PAIA manual review")
            message = "Publication approved. Remaining setup: " + ", ".join(setup) + "." if setup else "Approved website is ready for deployment."
            alerts.append({"level": "action", "text": message})
        if settings["vat_status"] == "unknown":
            alerts.append({"level": "action", "text": "VAT status is unconfirmed. Do not issue customer invoices until the seller's status is checked."})
        if reserve is None:
            alerts.append({"level": "action", "text": "Income-tax reserve is unset. Choose a planning percentage after reviewing salary, PAYE and other income."})
        if month_expenses > settings["monthly_budget_cents"]:
            alerts.append({"level": "action", "text": "Recorded operating expenses exceed the monthly budget. Recording a cost does not authorise spending."})
        missing = sum(not r["evidence"] for r in all_rows if not r["void_reason"])
        if missing:
            alerts.append({"level": "action", "text": f"{missing} active record(s) need an evidence filename. Keep original invoices and bank proof locally."})
        if rolling["receipts_cents"] >= VAT_THRESHOLD_CENTS * 0.8:
            alerts.append({"level": "action", "text": "Recorded receipts are approaching the VAT threshold. Review all taxable supplies, written contracts and other business turnover now."})
        for venture in ventures:
            if venture["id"] == "reporting" and launch["offer_approved"]:
                venture["status"] = "Offer approved"
                pending = []
                if launch["manager_clearance"] not in {"cleared", "not_required"}:
                    pending.append("Manager clearance")
                if launch["name_status"] != "approved":
                    pending.append("Business name approval")
                if launch["email_status"] != "created":
                    pending.append("Email setup")
                if pending:
                    venture["note"] = ", ".join(pending) + " pending"
                elif launch["public_deployment_status"] == "published":
                    venture["note"] = "Website live; first customer discovery"
                else:
                    venture["note"] = "Publication setup next" if launch["publication_approved"] else "Launch review next"
            venture.update(self.totals([r for r in selected if r["venture_id"] == venture["id"]]))
        return {"as_of": on_date.isoformat(), "scope": scope, "start": None if scope == "all" else start.isoformat(),
                "tax_year_end": tax_year_start(on_date).year + 1, "currency": "ZAR", "units": "integer cents",
                "totals": totals, "ventures": ventures, "entries": selected,
                "opportunities": [r for r in opportunities if venture_id == "all" or r["venture_id"] == venture_id],
                "settings": settings, "launch": launch, "alerts": alerts,
                "vat_monitor": {"recorded_receipts_ex_vat_cents": rolling["receipts_cents"] - rolling["vat_collected_cents"],
                                "threshold_cents": VAT_THRESHOLD_CENTS, "start": rolling_start.isoformat(),
                                "source_checked": "2026-09-29", "complete_taxable_supplies": False},
                "note": "Management cash report only. All ventures assumed to belong to one seller. No bank connection, tax assessment, registration or filing."}

    def export(self):
        with closing(self.connect()) as db:
            return {"schema_version": 1, "exported_at": datetime.now(timezone.utc).isoformat(),
                    "tables": {table: [dict(r) for r in db.execute(f"SELECT * FROM {table}")]
                               for table in ("ventures", "settings", "ledger", "opportunities", "audit")}}
