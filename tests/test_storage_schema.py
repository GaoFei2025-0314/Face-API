import os
import sqlite3
import tempfile
import threading
import unittest
from unittest import mock

from storage import FaceDB


class FaceDBSchemaTests(unittest.TestCase):
    def test_fresh_database_creates_faces_table_and_supports_basic_crud(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "faces.db")
            db = FaceDB(db_path=db_path)
            try:
                self.assertEqual(db.count(), 0)
                face_id = db.add("zhangsan", [0.1] * 512, {"department": "研发部"}, 1)
                self.assertTrue(face_id)
                self.assertEqual(db.count(), 1)
                rows = db.list_all()
                self.assertEqual(len(rows), 1)
                self.assertEqual(rows[0]["username"], "zhangsan")

                by_user = db.list_by_user_id(1)
                self.assertEqual(len(by_user), 1)
                self.assertEqual(by_user[0]["id"], face_id)

                cache_status = db.get_search_cache_status()
                self.assertEqual(cache_status["record_count"], 1)
                self.assertTrue(cache_status["ready"])
                self.assertEqual(cache_status["mode"], "exact")
                self.assertEqual(cache_status["target_record_count"], 50000)

                index_status = db.get_search_index_status()
                self.assertFalse(index_status["enabled"])
                self.assertEqual(index_status["mode"], "exact")
                self.assertTrue(index_status["fallback"]["enabled"])
                self.assertIn("enter_conditions", index_status)

                benchmark = db.get_search_benchmark_summary()
                self.assertEqual(benchmark["target_record_count"], 50000)
                self.assertIn("p95_ms", benchmark["metrics"])
                self.assertEqual(benchmark["index_decision"]["mode"], "exact")

                challenge_id = db.add_liveness_challenge(
                    purpose="login",
                    terminal_id="door-1",
                    action="blink",
                    expires_at=9999999999,
                    action_window_seconds=10,
                )
                self.assertTrue(challenge_id)
                self.assertEqual(db.get_liveness_challenge(challenge_id)["status"], "pending")
                self.assertTrue(db.mark_liveness_challenge_result(challenge_id, passed=True, result_reason="ok"))
                ok, reason, challenge = db.consume_liveness_challenge(
                    challenge_id=challenge_id,
                    purpose="login",
                    terminal_id="door-1",
                    now=1,
                )
                self.assertTrue(ok)
                self.assertEqual(reason, "ok")
                self.assertEqual(challenge["status"], "used")

                ok, reason, _challenge = db.consume_liveness_challenge(
                    challenge_id=challenge_id,
                    purpose="login",
                    terminal_id="door-1",
                    now=2,
                )
                self.assertFalse(ok)
                self.assertEqual(reason, "already_used")

                audit_id = db.add_login_audit(
                    success=False,
                    similarity=0.42,
                    threshold=0.6,
                    failure_reason="FACE_TOO_DARK",
                    terminal_id="door-1",
                    quality_metrics={"brightness": 12.5, "det_score": 0.91},
                )
                self.assertTrue(audit_id)
                audits = db.list_login_audits(limit=1, terminal_id="door-1")
                self.assertEqual(audits[0]["quality_metrics"]["brightness"], 12.5)
                self.assertEqual(audits[0]["failure_reason"], "FACE_TOO_DARK")

                backup_path = os.path.join(temp_dir, "backup.db")
                copied = db.backup_to(backup_path)
                self.assertEqual(copied, backup_path)
                backup_db = FaceDB(db_path=backup_path)
                try:
                    self.assertEqual(backup_db.count(), 1)
                    self.assertEqual(backup_db.list_all()[0]["username"], "zhangsan")
                finally:
                    backup_db.close()

                removed = db.remove_by_user_id(1)
                self.assertEqual(removed, 1)
                self.assertEqual(db.count(), 0)
            finally:
                db.close()

    def test_search_cache_summary_does_not_load_embedding_matrix(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "faces.db")
            db = FaceDB(db_path=db_path)
            try:
                db.add("zhangsan", [0.1] * 512, {"department": "研发部"}, 1)
                self.assertIsNone(db._search_cache)

                summary = db.get_search_cache_summary()

                self.assertEqual(summary["record_count"], 1)
                self.assertTrue(summary["dirty"])
                self.assertIsNone(db._search_cache)
            finally:
                db.close()

    def test_close_all_connections_closes_thread_local_connections(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "faces.db")
            db = FaceDB(db_path=db_path)
            connections = []
            try:
                connections.append(db._conn())

                def open_thread_connection():
                    connections.append(db._conn())

                worker = threading.Thread(target=open_thread_connection)
                worker.start()
                worker.join()

                self.assertGreaterEqual(len(connections), 2)

                db.close_all_connections()

                for conn in connections:
                    with self.assertRaises(sqlite3.ProgrammingError):
                        conn.execute("SELECT 1")
            finally:
                for conn in connections:
                    try:
                        conn.close()
                    except sqlite3.ProgrammingError:
                        pass
                db.close()

    def test_checkpoint_failure_is_logged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "faces.db")
            db = FaceDB(db_path=db_path)
            try:
                db._checkpoint_threshold = 1
                failing_conn = mock.Mock()
                failing_conn.execute.side_effect = RuntimeError("checkpoint failed")
                with mock.patch.object(db, "_conn", return_value=failing_conn):
                    with self.assertLogs("storage", level="ERROR") as logs:
                        db._maybe_checkpoint()

                self.assertIn("WAL checkpoint failed", "\n".join(logs.output))
            finally:
                db.close()

    def test_close_all_connection_failures_are_logged(self):
        with tempfile.TemporaryDirectory() as temp_dir:
            db_path = os.path.join(temp_dir, "faces.db")
            db = FaceDB(db_path=db_path)
            failing_conn = mock.Mock()
            failing_conn.execute.side_effect = RuntimeError("checkpoint close failed")
            failing_conn.close.side_effect = RuntimeError("close failed")
            try:
                with db._connections_lock:
                    db._connections.add(failing_conn)

                with self.assertLogs("storage", level="ERROR") as logs:
                    db.close_all_connections()

                output = "\n".join(logs.output)
                self.assertIn("WAL checkpoint failed while closing connection", output)
                self.assertIn("SQLite connection close failed", output)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
