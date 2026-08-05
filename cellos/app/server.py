"""
The server. Python standard library only -- no framework, no build step.

Serves the single page out of web/ and dispatches everything under /api/ to
whichever domain registered that route. It knows nothing about cells.
"""

import json
import mimetypes
import os
import posixpath
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from ..domains.member import service as member
from ..kernel import db, routing
from ..kernel.errors import DomainError, NotAllowed

ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
WEB_ROOT = os.path.join(ROOT, "web")
MAX_BODY = 1 << 20  # far more than any request here needs


def dispatch(method, path, body, token):
    """Route, authenticate, hand to the domain. The whole of the API layer."""
    handler, params, public = routing.match(method, path)
    actor = member.user_for_token(token)
    if not public and actor is None:
        raise NotAllowed("Sign in first.")
    return handler(actor, body, **params)


class Handler(BaseHTTPRequestHandler):
    server_version = "CellOS/2.0"
    protocol_version = "HTTP/1.1"

    def do_GET(self):
        self._handle("GET")

    def do_POST(self):
        self._handle("POST")

    def do_PATCH(self):
        self._handle("PATCH")

    def do_PUT(self):
        self._handle("PUT")

    def do_DELETE(self):
        self._handle("DELETE")

    # ----------------------------------------------------------------

    def _handle(self, method):
        path = self.path.split("?", 1)[0]
        try:
            if path.startswith("/api/"):
                self._api(method, path)
            elif method == "GET":
                self._static(path)
            else:
                self._json(405, {"error": "Not something you can do here."})
        except BrokenPipeError:
            pass
        finally:
            # One SQLite connection per request thread, released with it.
            db.close()

    def _api(self, method, path):
        try:
            body = self._body()
        except ValueError:
            self._json(400, {"error": "That request was not valid JSON."})
            return

        token = None
        header = self.headers.get("Authorization", "")
        if header.startswith("Bearer "):
            token = header[7:].strip()

        try:
            result = dispatch(method, path, body, token)
        except DomainError as e:
            self._json(e.status, {"error": str(e)})
        except Exception as e:  # a bug, not a refusal
            self.log_error("unhandled: %s: %s", type(e).__name__, e)
            self._json(500, {"error": "Something broke on the server."})
        else:
            self._json(200, result)

    def _body(self):
        length = int(self.headers.get("Content-Length") or 0)
        if not length:
            return {}
        if length > MAX_BODY:
            raise ValueError("too large")
        parsed = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(parsed, dict):
            raise ValueError("expected an object")
        return parsed

    def _static(self, path):
        if path == "/":
            path = "/index.html"
        clean = posixpath.normpath(posixpath.join("/", path)).lstrip("/")
        target = os.path.realpath(os.path.join(WEB_ROOT, clean))
        if not target.startswith(os.path.realpath(WEB_ROOT) + os.sep) \
                or not os.path.isfile(target):
            self._json(404, {"error": "Not found."})
            return

        ctype = mimetypes.guess_type(target)[0] or "application/octet-stream"
        if target.endswith(".js"):
            ctype = "text/javascript"  # ES modules must not be sniffed
        with open(target, "rb") as fh:
            payload = fh.read()
        self.send_response(200)
        self.send_header("Content-Type", ctype)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        self.wfile.write(payload)

    def _json(self, status, obj):
        payload = json.dumps(obj, default=str).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(payload)))
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, fmt, *args):
        if os.environ.get("CELLOS_QUIET"):
            return
        super().log_message(fmt, *args)


def serve(host="127.0.0.1", port=8420):
    httpd = ThreadingHTTPServer((host, port), Handler)
    httpd.daemon_threads = True
    return httpd
