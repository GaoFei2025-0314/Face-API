from contextlib import contextmanager
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

from .errors import raise_business_error


def utc_now():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")


class BusinessDB:
    def __init__(self, db_path="business-demo.db"):
        self.db_path = str(db_path)
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)
        self._init_schema()
        self._seed_users()

    @contextmanager
    def _conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _init_schema(self):
        with self._conn() as conn:
            conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS business_users (
                    user_id TEXT PRIMARY KEY,
                    username TEXT NOT NULL,
                    display_name TEXT,
                    department TEXT,
                    status TEXT NOT NULL DEFAULT 'active',
                    created_at TEXT NOT NULL
                );

                CREATE TABLE IF NOT EXISTS face_bindings (
                    id TEXT PRIMARY KEY,
                    user_id TEXT NOT NULL,
                    face_id TEXT NOT NULL,
                    bind_status TEXT NOT NULL,
                    bound_at TEXT NOT NULL,
                    removed_at TEXT,
                    source TEXT NOT NULL,
                    metadata_json TEXT NOT NULL DEFAULT '{}'
                );

                CREATE TABLE IF NOT EXISTS business_login_audits (
                    id TEXT PRIMARY KEY,
                    terminal_event_id TEXT,
                    user_id TEXT,
                    terminal_id TEXT,
                    source TEXT NOT NULL,
                    success INTEGER NOT NULL,
                    failure_reason TEXT,
                    face_similarity REAL,
                    face_liveness_status TEXT,
                    face_liveness_reason TEXT,
                    anti_spoof_risk TEXT,
                    issued_token_id TEXT,
                    state TEXT,
                    created_at TEXT NOT NULL
                );

                """
            )
            existing_columns = {
                row["name"] for row in conn.execute("PRAGMA table_info(business_login_audits)").fetchall()
            }
            if "terminal_event_id" not in existing_columns:
                conn.execute("ALTER TABLE business_login_audits ADD COLUMN terminal_event_id TEXT")
            if "anti_spoof_risk" not in existing_columns:
                conn.execute("ALTER TABLE business_login_audits ADD COLUMN anti_spoof_risk TEXT")
            self._dedupe_for_unique_indexes(conn)
            conn.executescript(
                """
                CREATE UNIQUE INDEX IF NOT EXISTS idx_face_bindings_one_active_user
                ON face_bindings(user_id)
                WHERE bind_status = 'active';

                CREATE UNIQUE INDEX IF NOT EXISTS idx_business_login_audits_terminal_event
                ON business_login_audits(terminal_event_id)
                WHERE terminal_event_id IS NOT NULL;
                """
            )

    def _dedupe_for_unique_indexes(self, conn):
        now = utc_now()
        conn.execute(
            """
            UPDATE face_bindings
            SET bind_status = 'removed',
                removed_at = COALESCE(removed_at, ?)
            WHERE bind_status = 'active'
              AND id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY user_id
                               ORDER BY bound_at DESC, id DESC
                           ) AS rn
                    FROM face_bindings
                    WHERE bind_status = 'active'
                )
                WHERE rn > 1
              )
            """,
            (now,),
        )
        conn.execute(
            """
            UPDATE business_login_audits
            SET terminal_event_id = NULL
            WHERE terminal_event_id IS NOT NULL
              AND id IN (
                SELECT id FROM (
                    SELECT id,
                           ROW_NUMBER() OVER (
                               PARTITION BY terminal_event_id
                               ORDER BY created_at DESC, id DESC
                           ) AS rn
                    FROM business_login_audits
                    WHERE terminal_event_id IS NOT NULL
                )
                WHERE rn > 1
              )
            """
        )

    def _seed_users(self):
        seeds = [
            ("100001", "GAOFEI", "GAOFEI", "IT"),
            ("100002", "DEMO_ADMIN", "Demo Admin", "Ops"),
            ("100003", "VISITOR_01", "Visitor 01", "Guest"),
        ]
        with self._conn() as conn:
            for user_id, username, display_name, department in seeds:
                conn.execute(
                    """
                    INSERT OR IGNORE INTO business_users
                    (user_id, username, display_name, department, status, created_at)
                    VALUES (?, ?, ?, ?, 'active', ?)
                    """,
                    (user_id, username, display_name, department, utc_now()),
                )

    def _row_to_user(self, row):
        binding = self.get_active_binding(row["user_id"])
        return {
            "user_id": row["user_id"],
            "username": row["username"],
            "display_name": row["display_name"],
            "department": row["department"],
            "status": row["status"],
            "created_at": row["created_at"],
            "face_bound": binding is not None,
            "face_id": binding["face_id"] if binding else None,
        }

    def list_users(self, status=None):
        with self._conn() as conn:
            if status:
                rows = conn.execute(
                    "SELECT * FROM business_users WHERE status = ? ORDER BY user_id",
                    (status,),
                ).fetchall()
            else:
                rows = conn.execute("SELECT * FROM business_users ORDER BY user_id").fetchall()
        return [self._row_to_user(row) for row in rows]

    def get_user(self, user_id):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM business_users WHERE user_id = ?", (str(user_id),)).fetchone()
        return self._row_to_user(row) if row else None

    def require_user(self, user_id):
        user = self.get_user(user_id)
        if not user:
            raise_business_error("BUSINESS_USER_NOT_FOUND")
        return user

    def require_active_user(self, user_id):
        user = self.require_user(user_id)
        if user["status"] != "active":
            raise_business_error("USER_DISABLED")
        return user

    def add_user(self, user_id, username, display_name=None, department=None):
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO business_users
                (user_id, username, display_name, department, status, created_at)
                VALUES (?, ?, ?, ?, 'active', ?)
                """,
                (str(user_id), username, display_name, department, utc_now()),
            )
        return self.get_user(user_id)

    def update_user_status(self, user_id, status):
        with self._conn() as conn:
            conn.execute("UPDATE business_users SET status = ? WHERE user_id = ?", (status, str(user_id)))

    def get_active_binding(self, user_id):
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM face_bindings
                WHERE user_id = ? AND bind_status = 'active'
                ORDER BY bound_at DESC
                LIMIT 1
                """,
                (str(user_id),),
            ).fetchone()
        return dict(row) if row else None

    def create_binding(self, user_id, face_id, source, metadata=None):
        if self.get_active_binding(user_id):
            raise_business_error("FACE_ALREADY_BOUND")
        binding_id = str(uuid.uuid4())
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO face_bindings
                (id, user_id, face_id, bind_status, bound_at, source, metadata_json)
                VALUES (?, ?, ?, 'active', ?, ?, ?)
                """,
                (
                    binding_id,
                    str(user_id),
                    face_id,
                    utc_now(),
                    source,
                    json.dumps(metadata or {}, ensure_ascii=False),
                ),
            )
        return self.get_active_binding(user_id)

    def _create_binding_in_conn(self, conn, user_id, face_id, source, metadata=None):
        existing = conn.execute(
            """
            SELECT id FROM face_bindings
            WHERE user_id = ? AND bind_status = 'active'
            LIMIT 1
            """,
            (str(user_id),),
        ).fetchone()
        if existing:
            raise_business_error("FACE_ALREADY_BOUND")
        binding_id = str(uuid.uuid4())
        conn.execute(
            """
            INSERT INTO face_bindings
            (id, user_id, face_id, bind_status, bound_at, source, metadata_json)
            VALUES (?, ?, ?, 'active', ?, ?, ?)
            """,
            (
                binding_id,
                str(user_id),
                face_id,
                utc_now(),
                source,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )
        row = conn.execute("SELECT * FROM face_bindings WHERE id = ?", (binding_id,)).fetchone()
        return dict(row) if row else None

    def remove_binding(self, user_id):
        binding = self.get_active_binding(user_id)
        if not binding:
            raise_business_error("FACE_NOT_BOUND")
        with self._conn() as conn:
            conn.execute(
                """
                UPDATE face_bindings
                SET bind_status = 'removed', removed_at = ?
                WHERE id = ?
                """,
                (utc_now(), binding["id"]),
            )
        return binding

    def mark_binding_pending_cleanup(self, binding_id, reason=None):
        with self._conn() as conn:
            row = conn.execute("SELECT * FROM face_bindings WHERE id = ?", (binding_id,)).fetchone()
            if not row:
                return None
            metadata = json.loads(row["metadata_json"] or "{}")
            if reason:
                metadata["cleanup_error"] = reason
            conn.execute(
                """
                UPDATE face_bindings
                SET bind_status = 'pending_cleanup',
                    removed_at = COALESCE(removed_at, ?),
                    metadata_json = ?
                WHERE id = ?
                """,
                (utc_now(), json.dumps(metadata, ensure_ascii=False), binding_id),
            )
            updated = conn.execute("SELECT * FROM face_bindings WHERE id = ?", (binding_id,)).fetchone()
        return dict(updated) if updated else None

    def replace_binding(self, user_id, new_face_id, source, metadata=None):
        with self._conn() as conn:
            old_row = conn.execute(
                """
                SELECT * FROM face_bindings
                WHERE user_id = ? AND bind_status = 'active'
                ORDER BY bound_at DESC
                LIMIT 1
                """,
                (str(user_id),),
            ).fetchone()
            old = dict(old_row) if old_row else None
            if old:
                conn.execute(
                    """
                    UPDATE face_bindings
                    SET bind_status = 'removed', removed_at = ?
                    WHERE id = ?
                    """,
                    (utc_now(), old["id"]),
                )
            new_binding = self._create_binding_in_conn(
                conn=conn,
                user_id=user_id,
                face_id=new_face_id,
                source=source,
                metadata=metadata,
            )
        return old, new_binding

    def add_audit(
        self,
        *,
        terminal_event_id=None,
        user_id=None,
        terminal_id=None,
        source,
        success,
        failure_reason=None,
        face_similarity=None,
        face_liveness_status=None,
        face_liveness_reason=None,
        anti_spoof_risk=None,
        issued_token_id=None,
        state=None,
    ):
        audit_id = str(uuid.uuid4())
        anti_spoof_risk_text = json.dumps(anti_spoof_risk, ensure_ascii=False) if anti_spoof_risk is not None else None
        with self._conn() as conn:
            conn.execute(
                """
                INSERT INTO business_login_audits
                (id, terminal_event_id, user_id, terminal_id, source, success, failure_reason, face_similarity,
                 face_liveness_status, face_liveness_reason, anti_spoof_risk, issued_token_id, state, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    audit_id,
                    terminal_event_id,
                    str(user_id) if user_id is not None else None,
                    terminal_id,
                    source,
                    1 if success else 0,
                    failure_reason,
                    face_similarity,
                    face_liveness_status,
                    face_liveness_reason,
                    anti_spoof_risk_text,
                    issued_token_id,
                    state,
                    utc_now(),
                ),
            )
        return audit_id

    def get_audit_by_terminal_event_id(self, terminal_event_id):
        if not terminal_event_id:
            return None
        with self._conn() as conn:
            row = conn.execute(
                """
                SELECT * FROM business_login_audits
                WHERE terminal_event_id = ?
                ORDER BY created_at DESC, id DESC
                LIMIT 1
                """,
                (terminal_event_id,),
            ).fetchone()
        if not row:
            return None
        result = dict(row)
        result["success"] = bool(row["success"])
        result["anti_spoof_risk"] = json.loads(row["anti_spoof_risk"]) if row["anti_spoof_risk"] else None
        return result

    def list_audits(self, limit=20, terminal_id=None, success=None):
        limit = max(1, min(int(limit or 20), 100))
        query = "SELECT * FROM business_login_audits WHERE 1=1"
        params = []
        if terminal_id:
            query += " AND terminal_id = ?"
            params.append(terminal_id)
        if success is not None:
            query += " AND success = ?"
            params.append(1 if success else 0)
        query += " ORDER BY created_at DESC, id DESC LIMIT ?"
        params.append(limit)
        with self._conn() as conn:
            rows = conn.execute(query, params).fetchall()
        return [
            {
                **dict(row),
                "success": bool(row["success"]),
                "anti_spoof_risk": json.loads(row["anti_spoof_risk"]) if row["anti_spoof_risk"] else None,
            }
            for row in rows
        ]
