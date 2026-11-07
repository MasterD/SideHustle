"""Render owner-supplied seller disclosures for local review, without publishing."""
import html
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DETAILS = ROOT.parent / "data" / "seller-details.json"


def render():
    details = json.loads(DETAILS.read_text(encoding="utf-8-sig"))
    fields = ("legal_name", "trade_name", "business_email", "physical_business_address",
              "legal_service_address", "business_phone")
    for field in fields:
        if not isinstance(details.get(field), str) or not details[field].strip():
            raise ValueError(f"Complete {field} in the private seller-details file.")
    safe = {field: html.escape(details[field].strip(), quote=True) for field in fields}
    locator = details.get("premises_locator", {})
    locator_html = ""
    if locator:
        latitude, longitude = float(locator["latitude"]), float(locator["longitude"])
        if not (-90 <= latitude <= 90 and -180 <= longitude <= 180):
            raise ValueError("Invalid premises locator.")
        locator_html = f"<p>Premises locator supplied by the owner: {latitude:.6f}, {longitude:.6f}.</p>"
    phone = "".join(c for c in details["business_phone"] if c.isdigit() or c == "+")
    if phone.startswith("0") and len(phone) == 10:
        phone = "+27" + phone[1:]
    if not phone:
        raise ValueError("Complete a callable business telephone number.")
    rendered = []
    for name in ("seller", "paia"):
        template = (ROOT / f"{name}.template.html").read_text(encoding="utf-8")
        for field, value in safe.items():
            template = template.replace("{{" + field + "}}", value)
        template = template.replace("{{phone_link}}", html.escape(phone, quote=True))
        template = template.replace("{{premises_locator}}", locator_html)
        if "{{" in template:
            raise ValueError(f"Unfilled {name} template field.")
        (ROOT / "dist" / f"{name}.html").write_text(template, encoding="utf-8")
        rendered.append(f"dist/{name}.html")
    print(json.dumps({"rendered": rendered, "publicly_deployed": False,
                      "public_disclosure_approved": details.get("public_disclosure_approved") is True,
                      "location": "owner-supplied; not independently verified"}))


if __name__ == "__main__":
    render()
