import json
import re
import secrets
import sqlite3

from .core import Problem


ITEM = re.compile(r"/requests/([1-9][0-9]{0,18})(?:/(submit|approve|request-changes))?")


def make_app(requests, credentials):
    def authenticate(environ):
        scheme, _, token = environ.get("HTTP_AUTHORIZATION", "").partition(" ")
        if scheme.lower() == "bearer" and token.isascii():
            for configured_token, identity in credentials.items():
                if secrets.compare_digest(configured_token, token):
                    return identity
        raise Problem(401, "Bearer token required")

    def payload(environ):
        if environ.get("CONTENT_TYPE", "").split(";")[0].strip().lower() != "application/json":
            raise Problem(415, "Expected application/json")
        try:
            length = int(environ.get("CONTENT_LENGTH") or 0)
            if not 0 < length <= 65536:
                raise ValueError
            data = json.loads(environ["wsgi.input"].read(length).decode("utf-8"))
            if not isinstance(data, dict):
                raise ValueError
            # Ensure all strings can be stored as valid Unicode.
            json.dumps(data, ensure_ascii=False).encode("utf-8")
        except (ValueError, RecursionError):
            raise Problem(400, "Invalid JSON object or body size") from None
        return data

    def dispatch(environ):
        actor, roles = authenticate(environ)
        method = environ["REQUEST_METHOD"]
        path = environ["PATH_INFO"]
        if method == "POST" and path == "/requests":
            result = requests.create(actor, roles, payload(environ))
            return 201, result, [("Location", f"/requests/{result['id']}")]

        match = ITEM.fullmatch(path)
        if match:
            request_id, action = int(match[1]), match[2]
            if request_id >= 2**63:
                raise Problem(404, "Change request not found")
            if method == "GET" and action is None:
                return 200, requests.get(request_id, actor, roles), []
            if (method == "PUT" and action is None) or (method == "POST" and action):
                result = requests.mutate(request_id, actor, roles, action or "edit", payload(environ))
                return 200, result, []
        raise Problem(404, "Route not found")

    def app(environ, start_response):
        from http import HTTPStatus

        try:
            status, body, headers = dispatch(environ)
        except Problem as error:
            status, body, headers = error.status, {"error": error.message}, []
            if status == 401:
                headers.append(("WWW-Authenticate", "Bearer"))
        except sqlite3.OperationalError as error:
            if getattr(error, "sqlite_errorcode", None) != sqlite3.SQLITE_BUSY:
                raise
            status, body, headers = 503, {"error": "Database busy"}, [("Retry-After", "1")]
        encoded = json.dumps(body, ensure_ascii=False).encode("utf-8")
        headers.extend([("Content-Type", "application/json; charset=utf-8"),
                        ("Content-Length", str(len(encoded))), ("Cache-Control", "no-store")])
        start_response(f"{status} {HTTPStatus(status).phrase}", headers)
        return [encoded]

    return app
