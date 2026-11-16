import argparse
import json
import os
from socketserver import ThreadingMixIn
from wsgiref.simple_server import WSGIServer, make_server

from .api import make_app
from .core import ChangeRequests


class ThreadedServer(ThreadingMixIn, WSGIServer):
    daemon_threads = True


def load_credentials():
    try:
        accounts = json.loads(os.environ["CHANGEFLOW_IDENTITIES"])
        if not isinstance(accounts, dict) or not accounts:
            raise ValueError
        credentials = {}
        for token, account in accounts.items():
            actor, roles = account["id"], account["roles"]
            if not token or not token.isascii() or any(c.isspace() for c in token):
                raise ValueError
            if not isinstance(actor, str) or not actor.strip() or not isinstance(roles, list):
                raise ValueError
            if any(role not in ("Requester", "Reviewer") for role in roles):
                raise ValueError
            credentials[token] = (actor, frozenset(roles))
        if len({actor for actor, _ in credentials.values()}) != len(credentials):
            raise ValueError
        return credentials
    except (KeyError, ValueError, TypeError):
        raise SystemExit("Configure valid CHANGEFLOW_IDENTITIES before starting the server.") from None


def main():
    parser = argparse.ArgumentParser(description="Run the local ChangeFlow HTTP API")
    parser.add_argument("--db", default="changeflow.sqlite3")
    parser.add_argument("--port", type=int, default=8000)
    args = parser.parse_args()
    credentials = load_credentials()
    app = make_app(ChangeRequests(args.db), credentials)
    with make_server("127.0.0.1", args.port, app, server_class=ThreadedServer) as server:
        print(f"ChangeFlow listening at http://127.0.0.1:{server.server_port}", flush=True)
        server.serve_forever()


if __name__ == "__main__":
    main()
