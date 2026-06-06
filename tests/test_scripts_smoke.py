import json
import os
import shutil
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

    def run_powershell(self, *args):
        if sys.platform != "win32":
            self.skipTest("PowerShell smoke tests require Windows")
        powershell = shutil.which("powershell")
        if not powershell:
            self.skipTest("PowerShell smoke tests require Windows PowerShell")
        return subprocess.run(
            [
                powershell,
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                *args,
            ],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_cmd(self, command):
        if sys.platform != "win32":
            self.skipTest("cmd smoke tests require Windows")
        return subprocess.run(
            ["cmd", "/c", command],
            cwd=ROOT,
            text=True,
            encoding="utf-8",
            errors="replace",
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

    def run_batch_with_env(self, script, env_updates):
        if sys.platform != "win32":
            self.skipTest("cmd smoke tests require Windows")
        env = os.environ.copy()
        env.update(env_updates)
        return subprocess.run(
            ["cmd", "/c", script],
            cwd=ROOT,
            env=env,
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

    def test_run_prod_rejects_invalid_face_port_before_startup(self):
        result = self.run_batch_with_env(
            "run-prod.bat",
            {"FACE_PORT": "8000 & echo injected", "FACE_API_KEY": "smoke"},
        )

        self.assertNotEqual(result.returncode, 0)
        output = result.stderr + result.stdout
        self.assertIn("FACE_PORT must be an integer from 1 to 65535", output)
        self.assertNotIn("injected", output)

    def test_run_prod_rejects_out_of_range_face_port(self):
        result = self.run_batch_with_env(
            "run-prod.bat",
            {"FACE_PORT": "70000", "FACE_API_KEY": "smoke"},
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("FACE_PORT must be an integer from 1 to 65535", result.stderr + result.stdout)

    def test_windows_long_running_scripts_parse(self):
        scripts = [
            "scripts/install-task-scheduler.ps1",
            "scripts/uninstall-task-scheduler.ps1",
            "scripts/install-nssm-service.ps1",
            "scripts/uninstall-nssm-service.ps1",
        ]
        for script in scripts:
            with self.subTest(script=script):
                result = self.run_powershell(
                    "-Command",
                    f"$null = [scriptblock]::Create((Get-Content -Raw '{script}'))",
                )
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)

    def test_windows_long_running_scripts_help(self):
        scripts_and_params = [
            ("scripts/install-task-scheduler.ps1", "TaskName"),
            ("scripts/uninstall-task-scheduler.ps1", "TaskName"),
            ("scripts/install-nssm-service.ps1", "NssmPath"),
            ("scripts/uninstall-nssm-service.ps1", "NssmPath"),
        ]
        for script, param_name in scripts_and_params:
            with self.subTest(script=script):
                result = self.run_powershell("-Command", f"Get-Help .\\{script} -Parameter {param_name}")
                self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
                self.assertIn(param_name, result.stdout)

    def test_task_scheduler_install_rejects_missing_project_path(self):
        result = self.run_powershell(
            "-File",
            "scripts/install-task-scheduler.ps1",
            "-ProjectPath",
            "Z:\\missing-face-api-project",
            "-WhatIf",
        )

        self.assertNotEqual(result.returncode, 0)
        self.assertIn("ProjectPath does not exist", result.stderr + result.stdout)

    def test_nssm_install_reports_missing_nssm_without_download(self):
        result = self.run_powershell(
            "-File",
            "scripts/install-nssm-service.ps1",
            "-NssmPath",
            "Z:\\missing\\nssm.exe",
            "-WhatIf",
        )

        self.assertNotEqual(result.returncode, 0)
        output = result.stderr + result.stdout
        self.assertIn("NSSM not found", output)
        self.assertIn("will not download NSSM", output)

    def test_nssm_install_passes_expected_arguments_to_nssm(self):
        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            log_path = tmp_path / "nssm-args.log"
            nssm_path = tmp_path / "nssm.cmd"
            nssm_path.write_text(
                f'@echo off\n'
                f'echo %*>> "{log_path}"\n'
                f'exit /b 0\n',
                encoding="utf-8",
            )

            result = self.run_powershell(
                "-File",
                "scripts/install-nssm-service.ps1",
                "-ServiceName",
                "face_api_smoke_stub",
                "-NssmPath",
                str(nssm_path),
                "-Port",
                "8010",
                "-PythonPath",
                "C:\\Python310\\python.exe",
            )

            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            args = log_path.read_text(encoding="utf-8")
            self.assertIn("install face_api_smoke_stub", args)
            self.assertIn("set face_api_smoke_stub AppDirectory", args)
            self.assertIn("set face_api_smoke_stub AppStdout", args)
            self.assertIn("FACE_PORT=8010", args)
            self.assertIn("FACE_PYTHON=C:\\Python310\\python.exe", args)


if __name__ == "__main__":
    unittest.main()
