from contextlib import closing
import sqlite3


class Problem(Exception):
    def __init__(self, status, message):
        self.status = status
        self.message = message
        super().__init__(message)


class ChangeRequests:
    def __init__(self, path):
        self.path = path
        with closing(self.connect()) as db, db:
            db.execute("""
                CREATE TABLE IF NOT EXISTS change_requests (
                    id INTEGER PRIMARY KEY,
                    requesterId TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT NOT NULL,
                    reason TEXT NOT NULL,
                    status TEXT NOT NULL CHECK (status IN
                        ('Draft','PendingReview','ChangesRequested','Approved')),
                    version INTEGER NOT NULL CHECK (version >= 1)
                )
            """)

    def connect(self):
        db = sqlite3.connect(self.path, timeout=5)
        db.row_factory = sqlite3.Row
        return db

    @staticmethod
    def require(condition):
        if not condition:
            raise Problem(403, "Forbidden")

    @staticmethod
    def read(db, request_id):
        row = db.execute("SELECT * FROM change_requests WHERE id = ?", (request_id,)).fetchone()
        if row is None:
            raise Problem(404, "Change request not found")
        return dict(row)

    @staticmethod
    def content(payload):
        values = []
        for key, limit in (("title", 200), ("description", 4000), ("reason", 4000)):
            value = payload.get(key)
            if not isinstance(value, str) or not 1 <= len(value.strip()) <= limit:
                raise Problem(400, f"Invalid {key}")
            values.append(value.strip())
        return values

    def create(self, actor, roles, payload):
        self.require("Requester" in roles)
        if set(payload) != {"title", "description", "reason"}:
            raise Problem(400, "Expected title, description and reason")
        with closing(self.connect()) as db, db:
            cursor = db.execute("""
                INSERT INTO change_requests (requesterId, title, description, reason, status, version)
                VALUES (?, ?, ?, ?, 'Draft', 1)
            """, (actor, *self.content(payload)))
            return self.read(db, cursor.lastrowid)

    def get(self, request_id, actor, roles):
        with closing(self.connect()) as db:
            row = self.read(db, request_id)
            owns_request = actor == row["requesterId"] and "Requester" in roles
            visible_for_review = "Reviewer" in roles and row["status"] != "Draft"
            self.require(owns_request or visible_for_review)
            return row

    def mutate(self, request_id, actor, roles, operation, payload):
        expected_fields = {"version"}
        if operation == "edit":
            expected_fields.update(("title", "description", "reason"))
        version = payload.get("version")
        if set(payload) != expected_fields or type(version) is not int or version < 1:
            raise Problem(400, "Invalid mutation payload or version")

        with closing(self.connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = self.read(db, request_id)
            owner = actor == row["requesterId"]
            if operation in ("edit", "submit"):
                self.require(owner and "Requester" in roles)
                allowed = ("Draft", "ChangesRequested")
            else:
                self.require("Reviewer" in roles and (operation != "approve" or not owner))
                allowed = ("PendingReview",)

            if row["version"] != version:
                raise Problem(409, "Stale version. Read the current request before retrying.")
            if row["status"] not in allowed:
                raise Problem(409, "Operation is invalid for the current status")

            if operation == "edit":
                db.execute("""
                    UPDATE change_requests
                    SET title = ?, description = ?, reason = ?, version = version + 1 WHERE id = ?
                """, (*self.content(payload), request_id))
            else:
                next_status = {
                    "submit": "PendingReview",
                    "approve": "Approved",
                    "request-changes": "ChangesRequested",
                }[operation]
                db.execute("""
                    UPDATE change_requests SET status = ?, version = version + 1 WHERE id = ?
                """, (next_status, request_id))
            return self.read(db, request_id)
