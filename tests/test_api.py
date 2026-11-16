from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
import http.client
import json
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory
from threading import Barrier, Thread
import unittest
from wsgiref.simple_server import WSGIRequestHandler, make_server

from changeflow.__main__ import ThreadedServer
from changeflow.api import make_app
from changeflow.core import ChangeRequests


class QuietHandler(WSGIRequestHandler):
    def log_message(self, *args):
        pass


class ChangeFlowTests(unittest.TestCase):
    CONTENT = {"title": "Show branch title", "description": "Add accountTitle", "reason": "Help branch staff"}

    def setUp(self):
        temp = TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / "test.sqlite3"
        users = {
            "owner": ("sara", {"Requester", "Reviewer"}),
            "reviewer": ("reza", {"Reviewer"}),
            "other": ("mina", {"Requester"}),
        }
        app = make_app(ChangeRequests(self.path), users)
        server = make_server("127.0.0.1", 0, app, server_class=ThreadedServer, handler_class=QuietHandler)
        self.port = server.server_port
        self.addCleanup(server.server_close)
        thread = Thread(target=server.serve_forever, kwargs={"poll_interval": 0.01}, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 5)
        self.addCleanup(server.shutdown)

    def http(self, method, path, token, data=None):
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        body = None
        if data is not None:
            body = json.dumps(data)
            headers["Content-Type"] = "application/json"
        with closing(http.client.HTTPConnection("127.0.0.1", self.port, timeout=8)) as client:
            client.request(method, path, body=body, headers=headers)
            response = client.getresponse()
            return response.status, json.loads(response.read())

    def create(self):
        status, row = self.http("POST", "/requests", "owner", self.CONTENT)
        self.assertEqual(status, 201)
        return row

    def stored(self, request_id):
        with closing(sqlite3.connect(self.path)) as db:
            db.row_factory = sqlite3.Row
            row = db.execute("SELECT * FROM change_requests WHERE id = ?", (request_id,)).fetchone()
            self.assertIsNotNone(row)
            return dict(row)

    def pending(self):
        row = self.create()
        status, pending = self.http("POST", f"/requests/{row['id']}/submit", "owner", {"version": 1})
        self.assertEqual(status, 200)
        return pending

    def test_create_draft(self):
        row = self.create()
        self.assertEqual(row, dict(self.CONTENT, id=row["id"], requesterId="sara", status="Draft", version=1))
        self.assertEqual(row, self.stored(row["id"]))

    def test_submit_draft(self):
        row = self.pending()
        self.assertEqual((row["status"], row["version"]), ("PendingReview", 2))
        self.assertEqual(row, self.stored(row["id"]))

    def test_self_approval_rejected_for_user_with_both_roles(self):
        row = self.pending()
        status, _ = self.http("POST", f"/requests/{row['id']}/approve", "owner", {"version": 2})
        self.assertEqual(status, 403)
        self.assertEqual(row, self.stored(row["id"]))

    def test_independent_reviewer_can_approve(self):
        row = self.pending()
        status, approved = self.http("POST", f"/requests/{row['id']}/approve", "reviewer", {"version": 2})
        self.assertEqual(status, 200)
        self.assertEqual(approved, dict(row, status="Approved", version=3))
        self.assertEqual(approved, self.stored(row["id"]))

    def test_approved_cannot_be_edited_even_with_current_version(self):
        row = self.pending()
        route = f"/requests/{row['id']}"
        status, approved = self.http("POST", route + "/approve", "reviewer", {"version": 2})
        self.assertEqual(status, 200)
        status, _ = self.http("PUT", route, "owner", dict(self.CONTENT, title="New title", version=3))
        self.assertEqual(status, 409)
        self.assertEqual(approved, self.stored(row["id"]))

    def test_stale_edit_does_not_overwrite(self):
        row = self.create()
        route = f"/requests/{row['id']}"
        status, newest = self.http("PUT", route, "owner", dict(self.CONTENT, title="First edit", version=1))
        self.assertEqual(status, 200)
        status, _ = self.http("PUT", route, "owner", dict(self.CONTENT, title="Stale edit", version=1))
        self.assertEqual(status, 409)
        self.assertEqual(newest, self.stored(row["id"]))

    def test_return_edit_resubmit_and_reject_old_review(self):
        row = self.pending()
        route = f"/requests/{row['id']}"
        status, returned = self.http("POST", route + "/request-changes", "reviewer", {"version": 2})
        self.assertEqual((status, returned["status"], returned["version"]), (200, "ChangesRequested", 3))
        status, edited = self.http("PUT", route, "owner", dict(self.CONTENT, title="Revised", version=3))
        self.assertEqual((status, edited["version"]), (200, 4))
        status, resubmitted = self.http("POST", route + "/submit", "owner", {"version": 4})
        self.assertEqual((status, resubmitted["status"], resubmitted["version"]), (200, "PendingReview", 5))
        status, _ = self.http("POST", route + "/approve", "reviewer", {"version": 2})
        self.assertEqual(status, 409)
        self.assertEqual(resubmitted, self.stored(row["id"]))

    def test_auth_ownership_and_read_visibility(self):
        row = self.create()
        route = f"/requests/{row['id']}"
        self.assertEqual(self.http("GET", route, "owner"), (200, row))
        self.assertEqual(self.http("GET", route, None)[0], 401)
        self.assertEqual(self.http("GET", route, "reviewer")[0], 403)
        self.assertEqual(self.http("GET", route, "other")[0], 403)
        self.assertEqual(self.http("POST", route + "/submit", "other", {"version": 1})[0], 403)
        self.assertEqual(self.http("POST", route + "/approve", "reviewer", {"version": 1})[0], 409)
        self.assertEqual(self.stored(row["id"]), row)
        status, pending = self.http("POST", route + "/submit", "owner", {"version": 1})
        self.assertEqual(status, 200)
        self.assertEqual(self.http("GET", route, "reviewer"), (200, pending))
        self.assertEqual(self.http("PUT", route, "owner", dict(self.CONTENT, version=2))[0], 409)
        self.assertEqual(self.stored(row["id"]), pending)

    def test_competing_review_actions_only_commit_one_transition(self):
        row = self.pending()
        barrier = Barrier(2, timeout=5)

        def review(action):
            barrier.wait()
            return self.http("POST", f"/requests/{row['id']}/{action}", "reviewer", {"version": 2})

        with ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(review, ("approve", "request-changes")))
        self.assertEqual(sorted(status for status, _ in outcomes), [200, 409])
        winner = outcomes[0][1] if outcomes[0][0] == 200 else outcomes[1][1]
        self.assertEqual(winner, self.stored(row["id"]))
        self.assertEqual(winner["version"], 3)
        self.assertIn(winner["status"], ("Approved", "ChangesRequested"))


if __name__ == "__main__":
    unittest.main()
