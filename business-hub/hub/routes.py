"""HTTP transport and local-browser protections for the business application."""

from collections import defaultdict, deque
from http.server import BaseHTTPRequestHandler
import json
import mimetypes
import secrets
import threading
import time
from urllib.parse import parse_qs, unquote, urlsplit

from .insurance import estimate, get_config
from .validation import ApiError


MAX_BODY_BYTES = 64 * 1024


class PublicWriteLimiter:
    """Small in-memory throttle; public forms should not fill the local database."""

    def __init__(self):
        self.requests = defaultdict(deque)
        self.lock = threading.Lock()

    def check(self, address):
        now = time.monotonic()
        with self.lock:
            times = self.requests[address]
            while times and times[0] < now - 3600:
                times.popleft()
            if len(times) >= 100 or sum(item > now - 60 for item in times) >= 20:
                raise ApiError(429, "Too many requests. Please wait a minute before trying again.")
            times.append(now)


class RequestHandler(BaseHTTPRequestHandler):
    server_version = "LaunchpadLocal/1.0"

    def setup(self):
        super().setup()
        self.connection.settimeout(10)

    def do_GET(self):
        self.handle_request("GET")

    def do_POST(self):
        self.handle_request("POST")

    def do_PATCH(self):
        self.handle_request("PATCH")

    def do_PUT(self):
        self.send_json(405, {"error": "This method is not supported."})

    def do_DELETE(self):
        self.send_json(405, {"error": "This method is not supported."})

    def do_OPTIONS(self):
        self.send_json(405, {"error": "Cross-origin access is not enabled for this local tool."})

    def do_HEAD(self):
        self.send_response(405)
        self.security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", "0")
        self.end_headers()

    def do_TRACE(self):
        self.send_json(405, {"error": "This method is not supported."})

    def valid_local_host(self):
        raw_host = self.headers.get("Host", "")
        try:
            parsed = urlsplit("http://" + raw_host)
            hostname = parsed.hostname
            port = parsed.port or 80
        except ValueError:
            raise ApiError(403, "Use the local server address shown in the terminal.")
        if hostname not in ("127.0.0.1", "localhost", "::1") or port != self.server.server_port or parsed.username or parsed.password or parsed.path or parsed.query or parsed.fragment:
            raise ApiError(403, "This demo accepts requests only on its local loopback address.")
        return raw_host.lower()

    def validate_write(self, local_host, path):
        origin = self.headers.get("Origin")
        if origin and origin.lower() != f"http://{local_host}":
            raise ApiError(403, "Requests must come from this local website.")
        if self.headers.get("Sec-Fetch-Site") in ("cross-site", "same-site"):
            raise ApiError(403, "Requests must come from this local website.")
        if path.startswith("/api/public/"):
            self.server.public_write_limiter.check(self.client_address[0])
        elif not secrets.compare_digest(self.headers.get("X-CSRF-Token", "").encode("utf-8"), self.server.csrf_token.encode("utf-8")):
            raise ApiError(403, "Your dashboard session expired. Reload the page and try again.")

    def read_json_body(self):
        if self.headers.get("Transfer-Encoding"):
            raise ApiError(400, "Chunked request bodies are not supported.")
        if self.headers.get_content_type() != "application/json":
            raise ApiError(415, "Send this request as application/json.")
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            raise ApiError(400, "Invalid request size.")
        if length < 0 or length > MAX_BODY_BYTES:
            raise ApiError(413, "This request is too large. Keep it below 64 KB.")
        try:
            value = json.loads(self.rfile.read(length).decode("utf-8"))
        except (ValueError, UnicodeDecodeError):
            raise ApiError(400, "Send a valid JSON object.")
        if not isinstance(value, dict):
            raise ApiError(400, "Send a JSON object with named fields.")
        return value

    def handle_request(self, method):
        try:
            local_host = self.valid_local_host()
            parsed = urlsplit(self.path)
            if parsed.scheme or parsed.netloc:
                raise ApiError(400, "Use a local relative request path.")
            path = unquote(parsed.path)
            if "\x00" in path or "\\" in path:
                raise ApiError(400, "Invalid request path.")
            try:
                query = parse_qs(parsed.query, max_num_fields=50)
            except ValueError:
                raise ApiError(400, "Too many query fields.")
            body = None
            if method in ("POST", "PATCH"):
                self.validate_write(local_host, path)
                body = self.read_json_body()
            if path == "/api/session" and method == "GET":
                companies = self.server.application.companies()
                self.send_json(200, {"csrfToken": self.server.csrf_token, "companies": companies,
                                     "defaultCompanyId": companies[0]["id"] if companies else None})
                return
            # Quote Lab is stateless and does not create business records.
            # The existing local-origin, CSRF and body checks above apply.
            if path == "/api/insurance/config" and method == "GET":
                self.send_json(200, get_config())
                return
            if path == "/api/insurance/estimate" and method == "POST":
                self.send_json(200, estimate(body))
                return
            if path.startswith("/api/"):
                result = self.server.application.dispatch(method, path, query, body)
                status = 201 if method == "POST" and not path.endswith(("/publish", "/run")) else 200
                extra_headers = {}
                if path.endswith("/export"):
                    slug = result["company"]["slug"]
                    extra_headers["Content-Disposition"] = f'attachment; filename="{slug}-export.json"'
                self.send_json(status, result, extra_headers)
                return
            if method != "GET":
                raise ApiError(405, "This method is not supported for that page.")
            self.serve_static(path)
        except ApiError as error:
            headers = {"Retry-After": "60"} if error.status == 429 else None
            self.send_json(error.status, {"error": error.message}, headers)
        except (BrokenPipeError, ConnectionResetError):
            pass
        except Exception as error:
            # Keep private SQL/details out of the browser, but make maintenance
            # failures visible in the terminal running the local server.
            self.log_error("Request failed: %s", error)
            self.send_json(500, {"error": "Something went wrong locally. Check the server terminal and try again."})

    def security_headers(self):
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "same-origin")
        self.send_header("Cache-Control", "no-store")
        self.send_header("Content-Security-Policy", "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; connect-src 'self'; base-uri 'none'; form-action 'self'; frame-ancestors 'none'")

    def send_json(self, status, payload, extra_headers=None):
        content = json.dumps(payload, ensure_ascii=False, allow_nan=False).encode("utf-8")
        self.send_response(status)
        self.security_headers()
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(content)))
        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)
        self.end_headers()
        self.wfile.write(content)

    def serve_static(self, path):
        static_root = self.server.static_root
        if path == "/":
            file_path = static_root / "index.html"
        elif path == "/insurance":
            file_path = static_root / "insurance.html"
        elif path.startswith("/site/"):
            slug = path.removeprefix("/site/").rstrip("/")
            with self.server.application.database.connection() as connection:
                self.server.application.company_by_slug(connection, slug)
            file_path = static_root / "website.html"
        elif path.startswith("/static/"):
            file_path = (static_root / path.removeprefix("/static/")).resolve()
            if not file_path.is_relative_to(static_root):
                raise ApiError(404, "File was not found.")
        elif path == "/favicon.ico":
            self.send_response(204)
            self.security_headers()
            self.end_headers()
            return
        else:
            raise ApiError(404, "Page was not found.")
        if not file_path.is_file():
            raise ApiError(404, "File was not found.")
        content = file_path.read_bytes()
        content_type = mimetypes.guess_type(str(file_path))[0] or "application/octet-stream"
        if file_path.suffix == ".js":
            content_type = "text/javascript"
        if content_type.startswith("text/") or file_path.suffix == ".svg":
            content_type += "; charset=utf-8"
        self.send_response(200)
        self.security_headers()
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.end_headers()
        self.wfile.write(content)
