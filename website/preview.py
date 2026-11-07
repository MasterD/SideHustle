"""Preview only the public static files, on loopback. No owner ledger or API."""
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

PUBLIC = Path(__file__).resolve().parent / "dist"

class Preview(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(PUBLIC), **kwargs)

    def do_GET(self):
        if self.headers.get("Host") not in {"127.0.0.1:8766", "localhost:8766"}:
            return self.send_error(403)
        super().do_GET()

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self' data:; connect-src 'none'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'none'")
        super().end_headers()

    def log_message(self, *args):
        pass

if __name__ == "__main__":
    with ThreadingHTTPServer(("127.0.0.1", 8766), Preview) as server:
        print("Customer page preview: http://127.0.0.1:8766/", flush=True)
        try:
            server.serve_forever()
        except KeyboardInterrupt:
            pass
