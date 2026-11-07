"""Run Launchpad locally. Python's standard library is the only dependency."""

import argparse
from http.server import ThreadingHTTPServer
from pathlib import Path
import secrets

from hub.application import create_application
from hub.routes import PublicWriteLimiter, RequestHandler


ROOT = Path(__file__).resolve().parent
DEFAULT_DATABASE = ROOT / "data" / "business-hub.sqlite3"


def make_server(host="127.0.0.1", port=8787, database_path=None, seed=True):
    """Use port=0 and a temporary database to run independent integration tests."""
    if host != "127.0.0.1":
        raise ValueError("This local demo must listen on 127.0.0.1.")
    application = create_application(database_path or DEFAULT_DATABASE, seed=seed)
    server = ThreadingHTTPServer((host, port), RequestHandler)
    server.daemon_threads = True
    server.application = application
    server.app = application
    server.csrf_token = secrets.token_urlsafe(32)
    server.public_write_limiter = PublicWriteLimiter()
    server.static_root = (ROOT / "static").resolve()
    return server


# Both names make the entry point easy to discover in examples and tests.
create_server = make_server


def main():
    parser = argparse.ArgumentParser(description="Local Launchpad business dashboard. No hosting or external services.")
    parser.add_argument("--port", type=int, default=8787, help="Local HTTP port (default: 8787)")
    parser.add_argument("--database", type=Path, default=DEFAULT_DATABASE, help="SQLite database file")
    parser.add_argument("--no-seed", action="store_true", help="Start with an empty database instead of demo data")
    arguments = parser.parse_args()
    server = make_server(port=arguments.port, database_path=arguments.database, seed=not arguments.no_seed)
    print(f"Launchpad is running at http://127.0.0.1:{server.server_port}")
    print(f"Local data: {Path(arguments.database).resolve()}")
    print("Fictional local demo. Social publishing and paid ads are prepared only; no money is spent.")
    print("Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping Launchpad.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
