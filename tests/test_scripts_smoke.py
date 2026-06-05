import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class ScriptSmokeTests(unittest.TestCase):
    def run_script(self, *args):
        return subprocess.run(
            [sys.executable, *args],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def test_benchmark_scale_uses_temporary_db_for_synthetic_data(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "benchmark.json"
            result = self.run_script(
                "scripts/benchmark-scale.py",
                "--seed-synthetic",
                "--target-count",
                "2",
                "--sample-count",
                "1",
                "--output",
                str(output),
            )

            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(output.read_text(encoding="utf-8"))
            self.assertTrue(report["runtime"]["temporary_db"])
            self.assertEqual(report["record_count"], 2)

    def test_bulk_manifest_reports_bad_jsonl_without_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            manifest = Path(tmp) / "bad.jsonl"
            manifest.write_text("{bad json\n", encoding="utf-8")

            result = self.run_script("scripts/bulk-manifest.py", "validate-import", str(manifest))

            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn("Traceback", result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertFalse(report["ok"])
            self.assertIn("invalid_json", ",".join(report["failed"][0]["reasons"]))

    def test_bulk_manifest_reports_missing_manifest_without_traceback(self):
        result = self.run_script("scripts/bulk-manifest.py", "validate-import", "missing-manifest.jsonl")

        self.assertNotEqual(result.returncode, 0)
        self.assertNotIn("Traceback", result.stderr + result.stdout)
        report = json.loads(result.stdout)
        self.assertFalse(report["ok"])
        self.assertEqual(report["failed"][0]["reasons"], ["manifest_not_found"])


if __name__ == "__main__":
    unittest.main()
