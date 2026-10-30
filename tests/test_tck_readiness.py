"""P0B-C1 upstream independent TCK pin assertions; no network access."""
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
TCK = ROOT / "contracts/agent-web/a2a-tck-pin-20261030.json"
DOC = ROOT / "docs/agent-web/p0b-c1-interop-tck-readiness.md"


class TCKPinTests(unittest.TestCase):
    def test_official_tck_source_pin_and_no_false_certification(self):
        item = json.loads(TCK.read_text(encoding="utf-8"))
        self.assertEqual(item["upstream"], "a2aproject/a2a-tck")
        self.assertEqual(item["pinnedCommit"], "d4d6fae7887f88ef607fb461c13e3b0e1802f19b")
        self.assertEqual(item["gitTreeSha1"], "8469eb8aa083c027aa00a3107972b1787dc6671a")
        self.assertEqual(item["runnerGitBlobSha1"], "06f70520f89c2bb60e1f752694781141568ad08b")
        self.assertEqual(item["dependencyLockGitBlobSha1"], "9c17390a1441fb70d798baa8f4e71bc24fe95cdb")
        self.assertEqual(item["projectGitBlobSha1"], "3bb6059dbd68d3ce9e2dd01776077adebc7c5577")
        for key in ("officialTckExecuted", "officialMustConformancePassed",
                    "externalSdkInteroperabilityRun", "fullA2AConformanceClaimed",
                    "productionAuthorized"):
            self.assertIs(item[key], False, key)
        text = DOC.read_text(encoding="utf-8")
        for phrase in ("TCK NOT RUN", "P0B is still incomplete", "FAIL/HOLD",
                       "No speech grants"):
            self.assertIn(phrase, text)


if __name__ == "__main__":
    unittest.main()
