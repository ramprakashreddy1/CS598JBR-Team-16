import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
import verify


class VerifyTests(unittest.TestCase):
    def test_failed_clippy_json_command_cannot_pass_verification(self):
        with patch.object(verify, "run", side_effect=[(0, "", 0), (1, "", 0)]):
            with patch.object(verify, "lint_groups", return_value={}):
                clippy = verify.cargo_clippy(Path("."), verify.DEFAULT_TOOLCHAIN, {}, verify.DEFAULT_CLIPPY_ARGS)
        self.assertEqual(clippy["generated"]["total"], 0)
        self.assertFalse(clippy["ok"])
        passing_tests = {"ok": True, "total": 1}
        results = {
            "build": {"ok": True},
            "clippy": clippy,
            "benchmark_tests": passing_tests,
            "tests": passing_tests,
            "unsafe": {"totals": {"primary_total": 0, "forbid_unsafe_code": True, "unimplemented_or_todo": 0}},
        }
        self.assertFalse(verify.checks_pass(results))
        self.assertFalse(verify.checks_pass(results, require_passing_tests=False))

    def test_replaced_benchmark_cannot_pass_even_if_cargo_passes(self):
        with tempfile.TemporaryDirectory() as temporary:
            rust = Path(temporary) / "project_1"
            shutil.copytree(ROOT / "translations/project_1", rust, ignore=shutil.ignore_patterns("target"))
            replacement = "#[test]\nfn replacement() {}\nfn main() {}\n"
            test = rust / "src/bin/tests.rs"
            test.write_text(replacement)
            results = verify.run_all(rust, ROOT / "specs/project_1", restore_protected=False)
            self.assertEqual(results["benchmark_tests"]["tests"], {"replacement": "passed"})
            self.assertTrue(results["tests"]["ok"])
            self.assertEqual(results["protected"], [
                {"file": "src/bin/tests.rs", "status": "modified", "restored": False},
            ])
            self.assertFalse(results["success"])
            self.assertEqual(test.read_text(), replacement)


if __name__ == "__main__":
    unittest.main()
