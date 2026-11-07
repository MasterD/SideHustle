"""Create an allowlisted static review archive; never include owner records."""
import argparse
import hashlib
import json
import zipfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PUBLIC = ROOT / "dist"
FILES = (
    "index.html", "styles.css", "sample.html", "sample.js", "privacy.html", "seller.html", "paia.html",
    "404.html", "_headers", "robots.txt", "sample-sales.csv",
    "sample-invoices.csv", "sample-report.json",
)

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--publication-ready", action="store_true",
                        help="Require owner approval of these exact files before preparing an upload archive.")
    args = parser.parse_args()
    for name in FILES:
        path = PUBLIC / name
        if not path.is_file() or path.is_symlink():
            raise SystemExit(f"Missing or unsupported public file: {name}")
    digest = hashlib.sha256()
    for name in FILES:
        content = (PUBLIC / name).read_bytes()
        digest.update(name.encode("utf-8") + b"\0" + str(len(content)).encode() + b"\0" + content)
    content_sha256 = digest.hexdigest()
    details = json.loads((ROOT.parent / "data" / "seller-details.json").read_text(encoding="utf-8-sig"))
    profile = json.loads((ROOT.parent / "data" / "launch-profile.json").read_text(encoding="utf-8-sig"))
    consent = details.get("public_disclosure_approved") is True
    publication = profile.get("publication_approved") is True
    exact_content = profile.get("approved_site_content_sha256") == content_sha256
    if args.publication_ready and not (consent and publication and exact_content):
        raise SystemExit("Publication archive refused: approve public disclosures and these exact website files first.")
    archive = ROOT / ("quietbatch-site-publish.zip" if args.publication_ready else "quietbatch-site-preview.zip")
    with zipfile.ZipFile(archive, "w", zipfile.ZIP_DEFLATED) as bundle:
        for name in FILES:
            bundle.write(PUBLIC / name, name)
    with zipfile.ZipFile(archive) as bundle:
        if tuple(bundle.namelist()) != FILES or bundle.testzip() is not None:
            raise SystemExit("Archive verification failed.")
    manifest = {"archive": archive.name, "sha256": hashlib.sha256(archive.read_bytes()).hexdigest(),
                "content_sha256": content_sha256,
                "files": list(FILES), "publicly_deployed": False,
                "contains_owner_contact_and_location": True,
                "public_disclosure_approved": consent,
                "publication_approved": publication,
                "exact_content_approved": exact_content,
                "publication_archive": args.publication_ready,
                "note": "Local review archive contains the owner's address, coordinates and telephone. Do not upload without explicit disclosure and publication approval; confirm privacy setup before launch."}
    (ROOT / "archive-review.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archive": str(archive), "files": len(FILES), "bytes": archive.stat().st_size,
                      "sha256": manifest["sha256"], "content_sha256": content_sha256, "published": False}))
