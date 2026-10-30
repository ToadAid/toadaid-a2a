"""P0A static architecture-contract tests; not runtime security verification."""
import copy
import json
import unittest
from pathlib import Path
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[1]
CONTRACT = ROOT / "contracts/agent-web/topology.v0.json"
FOUNDATION = ROOT / "docs/agent-web/foundation-v0.md"
CANON = ROOT / "docs/architecture/canonical-a2a-architecture-master-note-v0.md"
GATES = ROOT / "docs/agent-web/acceptance-gates-v0.md"

EXPECTED_ORIGINS = {
    "portal": "https://portal.toadaid.org",
    "agent": "https://agent.toadaid.org",
    "mcp": "https://mcp.toadaid.org",
}
INVARIANTS = (
    "THE_MODEL_IS_NOT_THE_AUTHORITY",
    "A2A_CHAT_HAS_ZERO_EXECUTION_AUTHORITY",
    "IDENTITY_DOES_NOT_IMPLY_CAPABILITY",
    "CAPABILITY_DOES_NOT_IMPLY_AUTHORITY",
    "JOURNAL_BEFORE_DELIVERY",
    "REVOCATION_OVERRIDES_PRIOR_APPROVAL",
    "REFUSAL_IS_ALWAYS_AVAILABLE",
)


def validate(topology):
    """Return contract violations. This is not an endpoint or A2A schema validator."""
    errors = []
    if topology.get("kind") != "toadaid-agent-web-topology" or topology.get("wireProtocol") is not False:
        errors.append("architecture-only contract identity")
    if topology.get("status") != "planned-not-deployed":
        errors.append("non-live status")
    surfaces = topology.get("surfaces", {})
    if set(surfaces) != set(EXPECTED_ORIGINS):
        errors.append("surface set")
    for key, origin in EXPECTED_ORIGINS.items():
        surface = surfaces.get(key, {})
        if surface.get("origin") != origin or urlparse(origin).scheme != "https":
            errors.append(f"{key} origin")
    if surfaces.get("portal", {}).get("audience") != "human":
        errors.append("portal audience")
    if surfaces.get("agent", {}).get("audience") != "machine":
        errors.append("agent audience")
    if surfaces.get("agent", {}).get("proposedWellKnownAgentCard") != "/.well-known/agent-card.json":
        errors.append("A2A discovery path")
    if surfaces.get("mcp", {}).get("audience") != "authorized-tool-client":
        errors.append("mcp audience")
    obs = topology.get("observatory", {})
    if obs.get("proposedPath") != "/agents" or obs.get("visibilityClasses") != ["public", "community", "operator"]:
        errors.append("observatory projection")
    if obs.get("privateByDefault") is not True or obs.get("rawPrivateJournalsPublished") is not False:
        errors.append("observatory confidentiality")
    policy = topology.get("authority", {})
    required = {
        "chatGrantsExecution": False,
        "identityGrantsCapability": False,
        "registrationGrantsToolAuthority": False,
        "executionNeedsSeparateCurrentGrant": True,
        "walletRequiredForPublicLore": False,
    }
    for key, value in required.items():
        if policy.get(key) is not value:
            errors.append(f"authority: {key}")
    for key in ("publicExposureAuthorized", "hostMutationAuthorized", "agentRegistrationActive"):
        if topology.get("release", {}).get(key) is not False:
            errors.append(f"release: {key}")
    return errors


class FoundationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.record = json.loads(CONTRACT.read_text(encoding="utf-8"))

    def test_contract_valid(self):
        self.assertEqual(validate(self.record), [])

    def test_canonical_invariants_preserved(self):
        base = CANON.read_text(encoding="utf-8")
        foundation = FOUNDATION.read_text(encoding="utf-8")
        for invariant in INVARIANTS:
            with self.subTest(invariant=invariant):
                self.assertIn(invariant, base)
                self.assertIn(invariant, foundation)

    def test_non_live_truthfulness(self):
        self.assertIn("NOT DEPLOYED", FOUNDATION.read_text(encoding="utf-8"))
        self.assertIn("NOT DEPLOYED", GATES.read_text(encoding="utf-8"))

    def test_negative_control_chat_authority(self):
        changed = copy.deepcopy(self.record)
        changed["authority"]["chatGrantsExecution"] = True
        self.assertIn("authority: chatGrantsExecution", validate(changed))

    def test_negative_control_publication(self):
        changed = copy.deepcopy(self.record)
        changed["observatory"]["rawPrivateJournalsPublished"] = True
        self.assertIn("observatory confidentiality", validate(changed))

    def test_negative_control_fake_live(self):
        changed = copy.deepcopy(self.record)
        changed["status"] = "deployed"
        self.assertIn("non-live status", validate(changed))

    def test_negative_control_wrong_origin(self):
        changed = copy.deepcopy(self.record)
        changed["surfaces"]["agent"]["origin"] = "http://localhost:8888"
        self.assertIn("agent origin", validate(changed))

    def test_negative_control_unauthorized_exposure(self):
        changed = copy.deepcopy(self.record)
        changed["release"]["publicExposureAuthorized"] = True
        self.assertIn("release: publicExposureAuthorized", validate(changed))

    def test_gates_separate_authority(self):
        text = GATES.read_text(encoding="utf-8")
        for label in ("P0A", "P0B", "P0C", "P0D", "P0E", "STOP"):
            self.assertIn(label, text)


if __name__ == "__main__":
    unittest.main()
