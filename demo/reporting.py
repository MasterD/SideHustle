"""Offline reporting pilot. Explicit fixed schemas; synthetic demo, not business revenue."""
import argparse
import csv
import html
import json
from collections import defaultdict
from datetime import date
from decimal import Decimal, InvalidOperation
from pathlib import Path


def parse_amount(raw, filename, line, column):
    try:
        value = Decimal(raw)
        if not value.is_finite() or value < 0 or value.quantize(Decimal("0.01")) != value:
            raise ValueError()
        return int(value * 100)
    except (InvalidOperation, ValueError):
        raise ValueError(f"{filename}, row {line}: {column} must be a non-negative amount with up to two decimals.")


def read_rows(path, columns):
    with Path(path).open(encoding="utf-8-sig", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != columns:
            raise ValueError(f"{path}: expected columns {', '.join(columns)} in that order.")
        rows = []
        seen = set()
        for line, row in enumerate(reader, 2):
            if None in row or any(value is None or value.strip() == "" for value in row.values()):
                raise ValueError(f"{path}, row {line}: missing or extra values.")
            key = row[columns[0]].strip()
            if key in seen:
                raise ValueError(f"{path}, row {line}: duplicate ID {key}.")
            seen.add(key)
            rows.append((line, {key: value.strip() for key, value in row.items()}))
        return rows


def build_report(sales_path, invoices_path, start, end, as_of):
    start, end, as_of = map(date.fromisoformat, (start, end, as_of))
    if start > end:
        raise ValueError("Start must be on or before end.")
    sales = []
    for line, row in read_rows(sales_path, ["transaction_id", "date", "client", "amount_ex_vat"]):
        when = date.fromisoformat(row["date"])
        amount = parse_amount(row["amount_ex_vat"], sales_path, line, "amount_ex_vat")
        if start <= when <= end:
            sales.append({"date": when.isoformat(), "client": row["client"], "amount_cents": amount})
    overdue = []
    outstanding_total = 0
    for line, row in read_rows(invoices_path, ["invoice_id", "client", "issued_date", "due_date", "amount_ex_vat", "paid_ex_vat"]):
        issued, due = date.fromisoformat(row["issued_date"]), date.fromisoformat(row["due_date"])
        amount = parse_amount(row["amount_ex_vat"], invoices_path, line, "amount_ex_vat")
        paid = parse_amount(row["paid_ex_vat"], invoices_path, line, "paid_ex_vat")
        if paid > amount or due < issued:
            raise ValueError(f"{invoices_path}, row {line}: payment exceeds invoice or due date precedes issue date.")
        if issued <= as_of:
            outstanding = amount - paid
            outstanding_total += outstanding
            if outstanding and due < as_of:
                overdue.append({"invoice_id": row["invoice_id"], "client": row["client"], "due_date": due.isoformat(), "outstanding_cents": outstanding})
    by_client = defaultdict(int)
    for item in sales:
        by_client[item["client"]] += item["amount_cents"]
    return {"label": "SYNTHETIC DEMONSTRATION — not actual business revenue", "period": {"start": start.isoformat(), "end": end.isoformat(), "as_of": as_of.isoformat()},
            "currency": "ZAR", "sales_ex_vat_cents": sum(item["amount_cents"] for item in sales), "transaction_count": len(sales),
            "outstanding_ex_vat_cents": outstanding_total, "overdue_ex_vat_cents": sum(item["outstanding_cents"] for item in overdue),
            "by_client_cents": dict(sorted(by_client.items())), "overdue_invoices": overdue}


def render_html(report):
    def rand(value):
        return f"R{value / 100:,.2f}"
    rows = "".join(f"<tr><td>{html.escape(client)}</td><td>{rand(amount)}</td></tr>" for client, amount in report["by_client_cents"].items())
    return f"""<!doctype html><html lang="en-ZA"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Reporting pilot — synthetic example</title>
<style>body{{font:16px/1.5 'Segoe UI',sans-serif;margin:45px auto;padding:0 25px;max-width:900px;color:#182a43;background:#f1f5fa}}article{{background:white;padding:25px;border-radius:14px;margin:20px 0}}.demo{{border-left:4px solid #174cd3;padding:12px;background:#eaf0ff}}h1{{letter-spacing:-.03em}}.metrics{{display:grid;grid-template-columns:repeat(auto-fit,minmax(200px,1fr));gap:20px}}strong{{font-size:1.6rem;display:block}}table{{border-collapse:collapse;width:100%}}td,th{{padding:13px;border-bottom:1px solid #dbe3ec;text-align:left}}th{{font-size:.875rem}}p{{color:#58687b}}</style>
<p class="demo">{html.escape(report['label'])}</p><h1>Your weekly report, ready to review.</h1><p>{report['period']['start']} to {report['period']['end']} · overdue balances as at {report['period']['as_of']}</p>
<div class="metrics"><article>Sales excluding VAT<strong>{rand(report['sales_ex_vat_cents'])}</strong></article><article>Transactions<strong>{report['transaction_count']}</strong></article><article>Overdue excluding VAT<strong>{rand(report['overdue_ex_vat_cents'])}</strong></article></div>
<article><h2>Sales by client</h2><table><thead><tr><th>Client alias</th><th>Sales excluding VAT</th></tr></thead><tbody>{rows}</tbody></table></article><p>Offline report. Source exports determine accuracy. This demonstration does not update the owner's business ledger.</p></html>"""


if __name__ == "__main__":
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser()
    parser.add_argument("--sales", type=Path, default=base / "sample-sales.csv")
    parser.add_argument("--invoices", type=Path, default=base / "sample-invoices.csv")
    parser.add_argument("--start", default="2026-09-21")
    parser.add_argument("--end", default="2026-09-27")
    parser.add_argument("--as-of", default="2026-09-28")
    parser.add_argument("--output", type=Path, default=base / "output")
    args = parser.parse_args()
    try:
        report = build_report(args.sales, args.invoices, args.start, args.end, args.as_of)
        args.output.mkdir(parents=True, exist_ok=True)
        (args.output / "report.json").write_text(json.dumps(report, indent=2), encoding="utf-8")
        (args.output / "report.html").write_text(render_html(report), encoding="utf-8")
        print(f"Synthetic report: {args.output.resolve() / 'report.html'}")
        print(f"Sales ex VAT: R{report['sales_ex_vat_cents'] / 100:,.2f}; overdue ex VAT: R{report['overdue_ex_vat_cents'] / 100:,.2f}")
    except (ValueError, OSError) as exc:
        parser.exit(1, str(exc) + "\n")

