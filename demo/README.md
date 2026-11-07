# Reporting pilot demonstration

All input records are synthetic. The output is never imported into the business monitor.

Run `reporting.py` with Python 3.10+; it uses only the standard library. The default example reports sales of R12,300 excluding VAT, four transactions and R4,000 overdue excluding VAT. The R1,100 transaction on 28 September is outside the selected sales period. Outstanding balances include R2,500 not yet due, for R6,500 total outstanding.

Each customer pilot needs its own approved schema, accounting definitions and acceptance test. This sample assumes positive sales only, one currency, amounts excluding VAT, invoice balances as at the reporting date, and no credit notes. Paid balances must reflect that date; this is not a historical balance reconstruction. Refunds, credit notes, mixed currencies or historical snapshots need an agreed extension before accepting work.

The script rejects unexpected headers, duplicate IDs, malformed rows, negative/invalid monetary values, overpayments and due dates preceding invoice dates. It writes an HTML report and a JSON report to `demo/output/` by default.

The delivered customer version should remove the synthetic demonstration label only after it uses approved customer data and has passed acceptance. Do not use live customer exports in this repository; keep them in a customer-controlled location.
