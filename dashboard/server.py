"""Loopback-only dashboard; Python standard library, no subscriptions or remote requests."""
import argparse
import csv
import io
import json
import secrets
import sqlite3
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse
from model import DEFAULT_DB, Store

STATIC = Path(__file__).resolve().parent / "dist"


def make_server(store, port=8765):
    token = secrets.token_urlsafe(32)

    class Handler(BaseHTTPRequestHandler):
        def _valid_host(self):
            return self.headers.get("Host") in {f"127.0.0.1:{self.server.server_port}", f"localhost:{self.server.server_port}"}

        def _send(self, body, status=200, content_type="application/json; charset=utf-8", filename=None):
            if not isinstance(body, bytes):
                body = json.dumps(body, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", content_type)
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.send_header("Content-Length", str(len(body)))
            if filename:
                self.send_header("Content-Disposition", f'attachment; filename="{filename}"')
            self.end_headers()
            self.wfile.write(body)

        def do_GET(self):
            if not self._valid_host():
                return self._send({"error": "Invalid local host."}, 403)
            parsed = urlparse(self.path)
            params = parse_qs(parsed.query)
            try:
                if parsed.path == "/api/bootstrap":
                    return self._send({"token": token})
                if parsed.path == "/api/snapshot":
                    return self._send(store.snapshot(params.get("scope", ["taxyear"])[0], params.get("venture", ["all"])[0]))
                if parsed.path == "/api/export.json":
                    return self._send(json.dumps(store.export(), ensure_ascii=False, indent=2).encode(), filename="sidehustle-backup.json")
                if parsed.path == "/api/ledger.csv":
                    stream = io.StringIO(newline="")
                    fields = ["id", "venture_id", "date", "kind", "amount_cents", "vat_cents", "reference", "description", "evidence", "related_id", "recorded_at", "void_reason", "voided_at"]
                    writer = csv.DictWriter(stream, fieldnames=fields, extrasaction="ignore")
                    writer.writeheader()
                    for row in store.entries():
                        # Keep exported free text from being interpreted as spreadsheet formulas.
                        writer.writerow({key: "'" + value if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@")) else value for key, value in row.items()})
                    return self._send(("\ufeff" + stream.getvalue()).encode("utf-8"), content_type="text/csv; charset=utf-8", filename="sidehustle-ledger.csv")
                files = {"/": ("index.html", "text/html"), "/index.html": ("index.html", "text/html"),
                         "/app.js": ("app.js", "text/javascript"), "/styles.css": ("styles.css", "text/css"),
                         "/offer": ("offer.html", "text/html"), "/favicon.svg": ("favicon.svg", "image/svg+xml")}
                if parsed.path in files:
                    name, mime = files[parsed.path]
                    return self._send((STATIC / name).read_bytes(), content_type=mime + "; charset=utf-8")
                self._send({"error": "Not found."}, 404)
            except ValueError as exc:
                self._send({"error": str(exc)}, 400)
            except (OSError, sqlite3.Error):
                self._send({"error": "Records are unavailable. Check the local data folder and try again."}, 503)

        def do_POST(self):
            origin = self.headers.get("Origin")
            allowed_origins = {f"http://127.0.0.1:{self.server.server_port}", f"http://localhost:{self.server.server_port}"}
            if not self._valid_host() or origin not in allowed_origins or not secrets.compare_digest(self.headers.get("X-Session-Token", ""), token):
                return self._send({"error": "Local session verification failed. Refresh the dashboard."}, 403)
            try:
                length = int(self.headers.get("Content-Length", "0"))
                if length <= 0 or length > 32_768 or self.headers.get_content_type() != "application/json":
                    return self._send({"error": "Send a small JSON request."}, 400)
                payload = json.loads(self.rfile.read(length))
                path = urlparse(self.path).path
                if path == "/api/entry":
                    result = store.add_entry(payload)
                elif path == "/api/void":
                    result = store.void_entry(payload.get("id"), payload.get("reason", ""))
                elif path == "/api/settings":
                    result = store.update_settings(payload)
                elif path == "/api/opportunity":
                    result = store.add_opportunity(payload)
                elif path == "/api/close-opportunity":
                    result = store.close_opportunity(payload.get("id"))
                else:
                    return self._send({"error": "Not found."}, 404)
                self._send(result, 201)
            except (ValueError, TypeError, AttributeError) as exc:
                self._send({"error": str(exc)}, 400)
            except sqlite3.Error:
                self._send({"error": "Could not save. Your input is preserved; retry after checking the data folder."}, 503)

        def log_message(self, format, *args):
            pass

    return ThreadingHTTPServer(("127.0.0.1", port), Handler)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    args = parser.parse_args()
    with make_server(Store(args.db), args.port) as server:
        print(f"Local dashboard: http://127.0.0.1:{server.server_port}", flush=True)
        print(f"Records: {args.db.resolve()}", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass

