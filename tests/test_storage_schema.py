import os
import tempfile
import unittest

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

                removed = db.remove_by_user_id(1)
                self.assertEqual(removed, 1)
                self.assertEqual(db.count(), 0)
            finally:
                db.close()


if __name__ == "__main__":
    unittest.main()
