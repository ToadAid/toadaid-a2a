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
        self.assertIn("test \"$GITHUB_REF\" != 'refs/heads/main'", self.yaml)
        self.assertIn('DIRECTOR_GATE: ${{ inputs.director_gate }}', self.yaml)
        self.assertIn('test "${DIRECTOR_GATE-}" != \'RUN_PINNED_TCK_LOCAL_ONLY\'', self.yaml)
        self.assertIn("permissions:\n  contents: read", self.yaml)

    def _gate_shell(self):
        """Extract only the pre-checkout gate step, not the TCK workflow."""
        begin = "      - name: Validate Director authorization before all other work\n"
        end = "      - name: Checkout protected main without persisted credentials"
        block = self.yaml.split(begin, 1)[1].split(end, 1)[0]
        self.assertIn("        run: |", block)
        return "\n".join(line.removeprefix("          ") for line in
                         block.split("        run: |\n", 1)[1].splitlines()) + "\n"

    def _run_gate(self, approval, ref):
        import os
        import subprocess
        env = dict(os.environ)
        env["DIRECTOR_GATE"] = approval
        env["GITHUB_REF"] = ref
        return subprocess.run(["bash", "-c", self._gate_shell()], env=env,
                              text=True, capture_output=True, timeout=3)

    def test_gate_checked_before_checkout(self):
        gate = self.yaml.index("Validate Director authorization before all other work")
        checkout = self.yaml.index("Checkout protected main without persisted credentials")
        upstream = self.yaml.index("Fetch and independently verify immutable upstream TCK")
        self.assertLess(gate, checkout)
        self.assertLess(checkout, upstream)
        self.assertNotIn("    if: ${{ github.ref ==", self.yaml)
        self.assertIn("always() && steps.director-gate.outcome == 'success'", self.yaml)

    def test_correct_authorization_allows_only_preflight(self):
        run = self._run_gate("RUN_PINNED_TCK_LOCAL_ONLY", "refs/heads/main")
        self.assertEqual(run.returncode, 0, run.stderr + run.stdout)
        self.assertIn("validated on main", run.stdout)

    def test_wrong_authorizations_fail_visibly(self):
        for approval in ("", "RUN_PINNED_TCK_LOCAL_ONLY ",
                         "RUN_PINNED_TCK_LOCAL_ONLy",
                         "RUN_PINNED_TCK_LOCAL_ONLY\n"):
            with self.subTest(approval=repr(approval)):
                run = self._run_gate(approval, "refs/heads/main")
                self.assertNotEqual(run.returncode, 0)
                self.assertIn("No TCK executed", run.stdout)
                if approval:
                    self.assertNotIn(approval, run.stdout)

    def test_correct_authorization_on_wrong_ref_fails(self):
        run = self._run_gate("RUN_PINNED_TCK_LOCAL_ONLY",
                             "refs/heads/cut-unauthorized")
        self.assertNotEqual(run.returncode, 0)
        self.assertIn("Select protected main", run.stdout)

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
