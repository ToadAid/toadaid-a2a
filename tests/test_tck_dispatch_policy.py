"""P0B-C2A manual workflow static guardrails; no TCK/dependency installation."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github/workflows/manual-a2a-tck-qualification.yml"
DOC = ROOT / "docs/agent-web/p0b-c2a-manual-tck-harness.md"
PIN = ROOT / "contracts/agent-web/a2a-tck-pin-20261030.json"


class ManualTckGateTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.yaml = WORKFLOW.read_text(encoding="utf-8")
        cls.doc = DOC.read_text(encoding="utf-8")
        cls.pin = json.loads(PIN.read_text(encoding="utf-8"))

    def test_manual_only_with_explicit_director_acknowledgement(self):
        self.assertIn("\non:\n  workflow_dispatch:", self.yaml)
        for forbidden in ("\n  push:", "\n  pull_request:", "\n  schedule:", "workflow_run:"):
            self.assertNotIn(forbidden, self.yaml)
        self.assertIn("github.ref == 'refs/heads/main'", self.yaml)
        self.assertIn("inputs.director_gate == 'RUN_PINNED_TCK_LOCAL_ONLY'", self.yaml)
        self.assertIn("permissions:\n  contents: read", self.yaml)

    def test_pinned_upstream_git_objects(self):
        for key in ("pinnedCommit", "gitTreeSha1", "runnerGitBlobSha1",
                    "dependencyLockGitBlobSha1", "projectGitBlobSha1"):
            self.assertIn(self.pin[key], self.yaml, key)
        self.assertIn("git rev-parse HEAD:uv.lock", self.yaml)
        self.assertIn("uv sync --locked --no-dev", self.yaml)

    def test_localhost_only_no_credential_persistence(self):
        self.assertIn('persist-credentials: false', self.yaml)
        self.assertIn('127\\.0\\.0\\.1', self.yaml)
        self.assertIn('python3 -u -m agent_web.local_probe', self.yaml)
        self.assertIn('mkdir -m 700', self.yaml)
        self.assertNotIn("secrets.", self.yaml)
        self.assertNotIn("0.0.0.0", self.yaml)

    def test_raw_tck_errors_are_not_silenced(self):
        self.assertIn('--transport jsonrpc --level must', self.yaml)
        self.assertIn('exit "$rc"', self.yaml)
        self.assertIn('MUST_SUITE_PROVISIONAL_PASS_DIRECTOR_REVIEW_REQUIRED', self.yaml)
        self.assertIn('if: always()', self.yaml)
        self.assertIn('actions/upload-artifact@', self.yaml)
        self.assertNotIn("continue-on-error: true", self.yaml)
        self.assertNotIn("pytest.mark.xfail", self.yaml)

    def test_no_claim_of_execution_or_deployment(self):
        for phrase in ("OFFICIAL TCK NOT RUN", "NO PUBLIC DEPLOYMENT",
                       "MUST_SUITE_FAIL_OR_EVIDENCE_HOLD",
                       "Director authorization"):
            self.assertIn(phrase, self.doc)
        for flag in ("officialTckExecuted", "officialMustConformancePassed",
                     "fullA2AConformanceClaimed", "productionAuthorized"):
            self.assertIs(self.pin[flag], False)


if __name__ == "__main__":
    unittest.main()
