"""P0B-B source-pin invariants; no external fetch or implied conformance."""
import json
from pathlib import Path
import unittest

PIN = Path(__file__).resolve().parents[1] / "contracts/agent-web/a2a-upstream-v1.0.1.json"


class PinTests(unittest.TestCase):
    def test_version_pin_is_explicit_and_non_live(self):
        data = json.loads(PIN.read_text(encoding="utf-8"))
        self.assertEqual(data["upstream"], "a2aproject/A2A")
        self.assertEqual(data["releaseTag"], "v1.0.1")
        self.assertEqual(data["protocolMajorMinor"], "1.0")
        self.assertEqual(data["releaseCommit"], "3303592588e388e62e0f69f701af531d2f4e3991")
        self.assertEqual(data["normativeProtoGitBlobSha1"], "400cdbad934654e27d7abbae1e145923eb40ac52")
        self.assertEqual(data["specDocumentationGitBlobSha1"], "382185a53b312cd6a60f5ac536ec5a356437ce77")
        self.assertIs(data["externalConformanceTestPassed"], False)
        self.assertIs(data["publicDeploymentAuthorized"], False)


if __name__ == "__main__":
    unittest.main()
