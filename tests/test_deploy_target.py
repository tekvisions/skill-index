import contextlib
import importlib.util
import io
import json
import os
import unittest
from pathlib import Path
from unittest.mock import patch


class DeployTargetTests(unittest.TestCase):
    def load(self, env=None):
        spec = importlib.util.spec_from_file_location("skill_deploy", Path(__file__).parents[1] / "deploy.py")
        mod = importlib.util.module_from_spec(spec)
        with patch.dict(os.environ, env or {}, clear=True):
            spec.loader.exec_module(mod)
        return mod

    def test_default_and_workflow_target_skill_index(self):
        m = self.load()
        self.assertEqual(m.PROJECT, "skill-index")
        self.assertIn("VERCEL_PROJECT: skill-index", (Path(__file__).parents[1] / ".github/workflows/update.yml").read_text())

    def test_wrong_project_rejected_even_with_framework_override(self):
        m = self.load({"VERCEL_PROJECT": "stacktracker"})
        m.req = lambda *a, **k: (200, json.dumps({"id": "prj_PdZiPoMmdnhnDBKBHJ6bUrQnkG1P"}).encode())
        with patch.dict(os.environ, {"ALLOW_OVERWRITE": "1"}), contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as e:
            m._preflight_overwrite_guard()
        self.assertEqual(e.exception.code, 2)

    def test_missing_project_fails_closed(self):
        m = self.load()
        m.req = lambda *a, **k: (404, b"{}")
        with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            m._preflight_overwrite_guard()

    def test_correct_static_project_passes(self):
        m = self.load()
        m.req = lambda *a, **k: (200, json.dumps({"id": m.EXPECTED_PROJECT_ID, "framework": None, "targets": {"production": {"meta": {}}}}).encode())
        m._preflight_overwrite_guard()


if __name__ == "__main__":
    unittest.main()
