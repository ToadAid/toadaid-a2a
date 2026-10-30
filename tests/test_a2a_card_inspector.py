"""No-network structural discovery tests, including hostile negative controls."""
import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from agent_web.card_inspector import CardError, inspect_card, parse_bytes, MAX_CARD_BYTES

CARD = {
    "name": "Synthetic Example (not deployed)",
    "description": "A structural testing example, not a live agent.",
    "version": "0.0.0-test",
    "supportedInterfaces": [{
        "url": "https://example.org/a2a",
        "protocolBinding": "JSONRPC",
        "protocolVersion": "1.0",
    }],
    "capabilities": {
        "streaming": False,
        "pushNotifications": False,
        "extendedAgentCard": False,
    },
    "defaultInputModes": ["text/plain"],
    "defaultOutputModes": ["text/plain"],
    "skills": [{
        "id": "offline-shape-example",
        "name": "Shape example",
        "description": "Never send a request; this is not deployed.",
        "tags": ["synthetic", "offline"],
    }],
}


class InspectTests(unittest.TestCase):
    def setUp(self):
        self.card = copy.deepcopy(CARD)

    def reject(self, needle=None):
        errors = inspect_card(self.card)
        self.assertTrue(errors, "unsafe card incorrectly accepted")
        if needle:
            self.assertTrue(any(needle in item for item in errors), errors)

    def test_synthetic_structure_passes_but_is_not_reachable_proof(self):
        self.assertEqual(inspect_card(self.card), [])

    def test_json_duplicate_keys_refused(self):
        with self.assertRaisesRegex(CardError, "duplicate"):
            parse_bytes(b'{"name":"x","name":"y"}')

    def test_nested_duplicate_keys_refused(self):
        with self.assertRaises(CardError):
            parse_bytes(b'{"a":{"b":1,"b":2}}')

    def test_non_object_refused(self):
        with self.assertRaises(CardError):
            parse_bytes(b'[]')

    def test_non_utf8_refused(self):
        with self.assertRaises(CardError):
            parse_bytes(b'\\xff'.decode("unicode_escape").encode("latin1"))

    def test_oversized_refused(self):
        with self.assertRaises(CardError):
            parse_bytes(b" " * (MAX_CARD_BYTES + 1))

    def test_nonfinite_refused(self):
        with self.assertRaises(CardError):
            parse_bytes(b'{"n":NaN}')

    def test_legacy_v03_top_level_refused(self):
        self.card["url"] = "https://example.org"
        self.reject("legacy")

    def test_wrong_protocol_version(self):
        self.card["supportedInterfaces"][0]["protocolVersion"] = "0.3"
        self.reject("protocolVersion")

    def test_unknown_transport_refused(self):
        self.card["supportedInterfaces"][0]["protocolBinding"] = "MADEUP"
        self.reject("binding")

    def test_http_url_refused(self):
        self.card["supportedInterfaces"][0]["url"] = "http://example.org/a2a"
        self.reject("HTTPS")

    def test_loopback_refused_for_public_profile(self):
        self.card["supportedInterfaces"][0]["url"] = "https://127.0.0.1/a2a"
        self.reject("HTTPS")

    def test_localhost_refused(self):
        self.card["supportedInterfaces"][0]["url"] = "https://localhost/a2a"
        self.reject("HTTPS")

    def test_userinfo_refused(self):
        self.card["supportedInterfaces"][0]["url"] = "https://user:pass@example.org/a2a"
        self.reject("HTTPS")

    def test_fragment_refused(self):
        self.card["supportedInterfaces"][0]["url"] = "https://example.org/a2a#secret"
        self.reject("HTTPS")

    def test_query_refused(self):
        self.card["supportedInterfaces"][0]["url"] = "https://example.org/a2a?token=stuff"
        self.reject("HTTPS")

    def test_empty_skills_refused(self):
        self.card["skills"] = []
        self.reject("skills")

    def test_skill_missing_tags_refused(self):
        del self.card["skills"][0]["tags"]
        self.reject("tags")

    def test_duplicate_skill_id_refused(self):
        self.card["skills"].append(copy.deepcopy(self.card["skills"][0]))
        self.reject("duplicate id")

    def test_duplicate_interface_refused(self):
        self.card["supportedInterfaces"].append(copy.deepcopy(self.card["supportedInterfaces"][0]))
        self.reject("duplicate")

    def test_private_key_refused_without_echo(self):
        self.card["privateKey"] = "do-not-print-this"
        self.reject("credential")
        self.assertNotIn("do-not-print-this", "\\n".join(inspect_card(self.card)))

    def test_invalid_security_reference(self):
        self.card["securityRequirements"] = [{"unknownScheme": []}]
        self.reject("scheme reference")

    def test_non_boolean_capability_refused(self):
        self.card["capabilities"]["streaming"] = "false"
        self.reject("flag")

    def test_missing_required_modes(self):
        del self.card["defaultOutputModes"]
        self.reject("defaultOutputModes")

    def test_cli_shape_only_and_no_network(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "card.json"
            p.write_text(json.dumps(self.card), encoding="utf-8")
            x = subprocess.run([sys.executable, "-m", "agent_web.card_inspector", str(p)],
                               capture_output=True, text=True, timeout=5)
            self.assertEqual(x.returncode, 0, x.stderr)
            self.assertIn("PROFILE_SHAPE_OK_UNVERIFIED", x.stdout)
            self.assertIn("NOT verified", x.stdout)

    def test_cli_rejects_bad_secret_without_echo(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "card.json"
            self.card["privateKey"] = "SHOULD_NOT_PRINT_SECRET"
            p.write_text(json.dumps(self.card), encoding="utf-8")
            x = subprocess.run([sys.executable, "-m", "agent_web.card_inspector", str(p)],
                               capture_output=True, text=True, timeout=5)
            self.assertEqual(x.returncode, 1)
            self.assertNotIn("SHOULD_NOT_PRINT_SECRET", x.stdout + x.stderr)


if __name__ == "__main__":
    unittest.main()
