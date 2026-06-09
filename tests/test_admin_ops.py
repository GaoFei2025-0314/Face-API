import tempfile
import unittest
from pathlib import Path

from fastapi import HTTPException

from admin_ops import ensure_backup_subdir, require_confirm


class AdminOpsTest(unittest.TestCase):
    def test_require_confirm_rejects_false(self):
        with self.assertRaises(HTTPException) as ctx:
            require_confirm(False)

        self.assertEqual(ctx.exception.status_code, 400)
        self.assertEqual(ctx.exception.detail["code"], "MAINTENANCE_CONFIRM_REQUIRED")

    def test_require_confirm_accepts_true(self):
        self.assertIsNone(require_confirm(True))

    def test_ensure_backup_subdir_rejects_outside_path(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            project_root.mkdir()
            outside = Path(tmp) / "outside"
            outside.mkdir()

            with self.assertRaises(HTTPException) as ctx:
                ensure_backup_subdir(outside, project_root=project_root)

        self.assertEqual(ctx.exception.detail["code"], "BACKUP_PATH_INVALID")

    def test_ensure_backup_subdir_accepts_project_backup_child(self):
        with tempfile.TemporaryDirectory() as tmp:
            project_root = Path(tmp) / "project"
            backup_dir = project_root / "backups" / "20260609-120000"
            backup_dir.mkdir(parents=True)

            resolved = ensure_backup_subdir(backup_dir, project_root=project_root)

        self.assertEqual(resolved.name, "20260609-120000")


if __name__ == "__main__":
    unittest.main()
