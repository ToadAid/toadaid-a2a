"""P0-WEB-03B1: synthetic rights intake, no real lore, consent or publication."""
import copy
import json
from pathlib import Path
import tempfile
import unittest

from agent_web.lore_rights_review import (
    HOLD, REVIEW, _read_json, assess, INVENTORY_KIND, INVENTORY_STATUS,
)
ROOT = Path(__file__).resolve().parents[1]
EXAMPLE = ROOT / "contracts/agent-web/examples/synthetic-lore-rights-request.v0.json"
SCHEMA = ROOT / "contracts/agent-web/lore-rights-review-request.v0.schema.json"


def inventory_for(packet):
    return {
        "kind": INVENTORY_KIND,
        "status": INVENTORY_STATUS,
        **packet["source"],
        "rightsReviewed": False,
        "publicExportAuthorized": False,
        "recordBodiesIncluded": False,
        "mediaPreservationClaimed": False,
        "productionDeploymentAuthorized": False,
    }


class RightsReviewTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(EXAMPLE.read_text(encoding="utf-8"))
        self.inventory = inventory_for(self.packet)

    def assert_denied(self, packet=None, receipt=None, code=None):
        result = assess(packet if packet is not None else self.packet,
                        receipt if receipt is not None else self.inventory)
        self.assertEqual(result["status"], HOLD, result)
        if code:
            self.assertIn(code, result["reasonCodes"])
        self.assertIs(result["publicationAuthorized"], False)
        self.assertIs(result["rightsLegallyDetermined"], False)
        self.assertIs(result["agentOrChatApprovalAccepted"], False)
        self.assertIs(result["deploymentAuthorized"], False)
        return result

    def test_unknown_rights_remain_held(self):
        self.assert_denied(code="RIGHTS_NOT_ADMITTED")

    def test_schema_is_explicit_draft_not_authority(self):
        schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertIs(schema["additionalProperties"], False)
        self.assertEqual(set(schema["required"]),
                         {"kind", "schemaVersion", "source", "request", "reviewEvidence"})
        self.assertIs(schema["properties"]["reviewEvidence"]["additionalProperties"], False)
        self.assertIn("NOT DEPLOYED", schema["description"])

    def test_source_integrity_mismatch_refuses(self):
        p = copy.deepcopy(self.packet)
        p["source"]["sourceDigest"] = "sha256:" + "1" * 64
        self.assert_denied(packet=p, code="SOURCE_GENERATION_MISMATCH")

    def test_mutated_blob_commit_and_record_count_each_refuse(self):
        for field, value in (("commit", "c" * 40),
                             ("sourceGitBlobSha1", "d" * 40),
                             ("recordCount", 2)):
            p = copy.deepcopy(self.packet)
            p["source"][field] = value
            with self.subTest(field=field):
                self.assert_denied(packet=p, code="SOURCE_GENERATION_MISMATCH")

    def test_untrusted_inventory_claiming_rights_cannot_pass(self):
        r = copy.deepcopy(self.inventory)
        r["rightsReviewed"] = True
        self.assert_denied(receipt=r, code="INVENTORY_AUTHORITY_INVALID")

    def test_packet_cannot_add_release_approval_field(self):
        p = copy.deepcopy(self.packet)
        p["releaseAuthorized"] = True
        self.assert_denied(packet=p, code="PACKET_SHAPE_INVALID")

    def test_restricted_or_disputed_rights_remain_held(self):
        for status in ("restricted", "disputed"):
            p = copy.deepcopy(self.packet)
            p["reviewEvidence"]["rightsStatus"] = status
            self.assert_denied(packet=p, code="RIGHTS_NOT_ADMITTED")

    def test_self_reported_license_with_missing_evidence_is_held(self):
        for status in ("permission_claimed", "public_domain_claimed"):
            p = copy.deepcopy(self.packet)
            p["reviewEvidence"]["rightsStatus"] = status
            with self.subTest(status=status):
                self.assert_denied(packet=p, code="HUMAN_EVIDENCE_INCOMPLETE")

    def test_completed_opaque_claims_only_get_human_review_not_release(self):
        p = copy.deepcopy(self.packet)
        e = p["reviewEvidence"]
        e.update({"rightsStatus": "permission_claimed",
                  "permissionEvidenceId": "proof-private-001",
                  "attributionReviewId": "attribution-private-001",
                  "privacyReviewId": "privacy-private-001",
                  "withdrawalPlanId": "withdrawal-private-001",
                  "humanReviewerAttestationId": "review-private-001"})
        result = assess(p, self.inventory)
        self.assertEqual(result["status"], REVIEW, result)
        self.assertEqual(result["reasonCodes"], [])
        for key in ("publicationAuthorized", "publicLoreExportEnabled",
                    "rightsLegallyDetermined", "rightsClearedByProgram",
                    "externalEvidenceVerified", "humanApprovalSatisfiedByPacket",
                    "mediaRehostingAuthorized"):
            self.assertIs(result[key], False, key)
        self.assertNotIn("proof-private-001", json.dumps(result))

    def test_media_binary_always_requires_separate_gate(self):
        p = copy.deepcopy(self.packet)
        p["request"]["operation"] = "evaluate_media_binary"
        p["request"]["fields"] = ["id", "img"]
        self.assert_denied(packet=p, code="MEDIA_BINARY_INDEPENDENT_GATE_REQUIRED")

    def test_media_reference_needs_independent_media_review(self):
        p = copy.deepcopy(self.packet)
        p["request"]["operation"] = "evaluate_media_reference"
        p["request"]["fields"] = ["id", "img"]
        p["reviewEvidence"].update({
            "rightsStatus": "public_domain_claimed",
            "attributionReviewId": "attribution-private-001",
            "privacyReviewId": "privacy-private-001",
            "withdrawalPlanId": "withdrawal-private-001",
            "humanReviewerAttestationId": "review-private-001",
        })
        self.assert_denied(packet=p, code="HUMAN_EVIDENCE_INCOMPLETE")

    def test_metadata_request_cannot_smuggle_lore_text(self):
        p = copy.deepcopy(self.packet)
        p["request"]["fields"] = ["id", "comment"]
        self.assert_denied(packet=p, code="REQUEST_SCOPE_CONFLICT")

    def test_lore_text_request_requires_text_field(self):
        p = copy.deepcopy(self.packet)
        p["request"]["operation"] = "evaluate_lore_text"
        self.assert_denied(packet=p, code="REQUEST_SCOPE_CONFLICT")

    def test_duplicate_record_scope_refused(self):
        p = copy.deepcopy(self.packet)
        p["request"]["recordIds"] = ["EXAMPLE_TEST_RECORD", "EXAMPLE_TEST_RECORD"]
        self.assert_denied(packet=p, code="RECORD_SCOPE_INVALID")

    def test_rejects_malformed_shapes_without_crashing(self):
        mutations = [
            (lambda x: x.update({"source": []}), "SOURCE_SHAPE_INVALID"),
            (lambda x: x.update({"reviewEvidence": []}), "REVIEW_EVIDENCE_SHAPE_INVALID"),
            (lambda x: x.update({"request": "bad"}), "REQUEST_SHAPE_INVALID"),
            (lambda x: x["request"].update({"operation": []}), "REQUEST_PURPOSE_INVALID"),
            (lambda x: x["reviewEvidence"].update({"rightsStatus": []}), "RIGHTS_STATUS_INVALID"),
            (lambda x: x["source"].update({"recordCount": True}), "SOURCE_FORMAT_INVALID"),
        ]
        for change, code in mutations:
            p = copy.deepcopy(self.packet)
            change(p)
            with self.subTest(code=code):
                self.assert_denied(packet=p, code=code)

    def test_rejects_invalid_evidence_identifiers(self):
        p = copy.deepcopy(self.packet)
        p["reviewEvidence"]["attributionReviewId"] = "https://external.example/evidence"
        self.assert_denied(packet=p, code="EVIDENCE_REFERENCE_INVALID")

    def test_local_json_input_rejects_duplicate_properties(self):
        with tempfile.TemporaryDirectory() as d:
            f = Path(d) / "invalid.json"
            f.write_text('{"kind":"a","kind":"b"}', encoding="utf-8")
            with self.assertRaises(ValueError):
                _read_json(f)

    def test_cli_sanitizes_private_packet_and_returns_hold(self):
        from agent_web.lore_rights_review import main
        from contextlib import redirect_stdout
        from io import StringIO
        with tempfile.TemporaryDirectory() as d:
            packet = Path(d) / "packet.json"
            inv = Path(d) / "inventory.json"
            packet.write_text(json.dumps(self.packet), encoding="utf-8")
            inv.write_text(json.dumps(self.inventory), encoding="utf-8")
            stream = StringIO()
            with redirect_stdout(stream):
                self.assertEqual(main(["--packet", str(packet), "--inventory", str(inv)]), 0)
            self.assertEqual(json.loads(stream.getvalue())["status"], HOLD)
            self.assertNotIn("EXAMPLE_TEST_RECORD", stream.getvalue())

    def test_no_real_lore_or_approval_flag_in_sample(self):
        raw = EXAMPLE.read_text(encoding="utf-8")
        self.assertNotIn("TOBY_T001_", raw)
        self.assertNotIn('"original":', raw)
        self.assertNotIn('"comment":', raw)
        self.assertEqual(self.packet["reviewEvidence"]["rightsStatus"], "unknown")
        self.assertEqual(self.packet["source"]["recordCount"], 1)


if __name__ == "__main__":
    unittest.main()
