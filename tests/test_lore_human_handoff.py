"""P0-WEB-03B2A offline human handoff: synthetic checks only; NO rights approval."""
import copy
from contextlib import redirect_stdout
from io import StringIO
import json
from pathlib import Path
import tempfile
import unittest

from agent_web.lore_human_handoff import (
    assess_handoff, packet_digest, HOLD, HANDOFF, REFS, _out, main,
)
from agent_web.lore_rights_review import assess as assess_packet, REVIEW as B1_REVIEW

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / "contracts/agent-web/examples/synthetic-lore-rights-request.v0.json"
DOCKET = ROOT / "contracts/agent-web/examples/synthetic-human-review-handoff.v0.json"
SCHEMA = ROOT / "contracts/agent-web/lore-human-review-handoff.v0.schema.json"


def inventory_for(packet):
    return {
        "kind": "toadaid-local-lore-inventory",
        "status": "LOCAL_OBJECT_ONLY_RIGHTS_HOLD_NOT_PUBLISHED",
        **packet["source"],
        "rightsReviewed": False,
        "publicExportAuthorized": False,
        "recordBodiesIncluded": False,
        "mediaPreservationClaimed": False,
        "productionDeploymentAuthorized": False,
    }


class HumanHandoffTests(unittest.TestCase):
    def setUp(self):
        self.packet = json.loads(PACKET.read_text(encoding="utf-8"))
        self.inventory = inventory_for(self.packet)
        self.docket = json.loads(DOCKET.read_text(encoding="utf-8"))

    def complete(self):
        """Construct a *self-claimed*, not authenticated, review-ready packet."""
        p = self.packet
        e = p["reviewEvidence"]
        e["rightsStatus"] = "permission_claimed"
        e["permissionEvidenceId"] = "claimed-permission-private"
        e["attributionReviewId"] = "claimed-attribution-private"
        e["privacyReviewId"] = "claimed-privacy-private"
        e["withdrawalPlanId"] = "claimed-withdrawal-private"
        e["humanReviewerAttestationId"] = "claimed-attestation-private"
        self.assertEqual(assess_packet(p, self.inventory)["status"], B1_REVIEW)
        d = self.docket
        d["binding"] = {
            "packetSha256": packet_digest(p),
            "sourceDigest": p["source"]["sourceDigest"],
            "sourceGitBlobSha1": p["source"]["sourceGitBlobSha1"],
        }
        d["review"]["objectionCodes"] = []
        d["review"]["evidenceRefs"] = {key: "private-"+key.lower().replace("_", "-")
                                         for key in REFS}
        return p, d

    def assert_hold(self, reason, packet=None, inventory=None, docket=None):
        r = assess_handoff(packet if packet is not None else self.packet,
                           inventory if inventory is not None else self.inventory,
                           docket if docket is not None else self.docket)
        self.assertEqual(r["status"], HOLD, r)
        self.assertIn(reason, r["reasonCodes"])
        self.assertIs(r["publicationAuthorized"], False)
        self.assertIs(r["deploymentAuthorized"], False)
        return r

    def test_untrusted_fictional_example_is_held(self):
        self.assert_hold("INTAKE_NOT_READY")

    def test_completed_self_claims_are_handoff_only_and_never_grants(self):
        p, d = self.complete()
        r = assess_handoff(p, self.inventory, d)
        self.assertEqual(r["status"], HANDOFF, r)
        self.assertEqual(r["reasonCodes"], [])
        for key in ("reviewerIdentityVerified", "reviewerIndependenceVerified",
                    "independentLegalReviewPerformed", "sourceAuthenticityVerifiedByTool",
                    "rightsCleared", "humanApprovalVerified", "publicationAuthorized",
                    "publicLoreExportEnabled", "mediaRehostingAuthorized",
                    "deploymentAuthorized"):
            self.assertIs(r[key], False, key)
        for private in ("claimed-permission-private", "private-revieweridentityevidenceref",
                        "EXAMPLE_TEST_RECORD"):
            self.assertNotIn(private, json.dumps(r))

    def test_binding_packet_change_refuses(self):
        p, d = self.complete()
        p["request"]["purpose"] += " changed later"
        self.assert_hold("PACKET_DIGEST_MISMATCH", packet=p, docket=d)

    def test_source_digest_mismatch_refuses(self):
        p, d = self.complete()
        d["binding"]["sourceDigest"] = "sha256:" + "f"*64
        self.assert_hold("SOURCE_BINDING_MISMATCH", packet=p, docket=d)

    def test_source_blob_mismatch_refuses(self):
        p, d = self.complete()
        d["binding"]["sourceGitBlobSha1"] = "f" * 40
        self.assert_hold("SOURCE_BINDING_MISMATCH", packet=p, docket=d)

    def test_missing_identity_and_independence_refs_refuse(self):
        for key in ("reviewerIdentityEvidenceRef", "reviewerIndependenceEvidenceRef",
                    "rightsChainEvidenceRef", "scopePermissionEvidenceRef",
                    "attributionEvidenceRef", "privacyEvidenceRef",
                    "withdrawalEvidenceRef", "conflictDisclosureEvidenceRef"):
            p, d = self.complete()
            d["review"]["evidenceRefs"][key] = None
            with self.subTest(field=key):
                self.assert_hold("HUMAN_REVIEW_EVIDENCE_REFERENCES_MISSING",
                                 packet=p, docket=d)

    def test_media_needs_separate_reference(self):
        p, d = self.complete()
        p["request"]["operation"] = "evaluate_media_reference"
        p["request"]["fields"] = ["id", "img"]
        p["reviewEvidence"]["mediaReviewId"] = "claimed-media-private"
        d["binding"]["packetSha256"] = packet_digest(p)
        d["review"]["evidenceRefs"]["mediaEvidenceRef"] = None
        self.assert_hold("HUMAN_REVIEW_EVIDENCE_REFERENCES_MISSING", packet=p, docket=d)

    def test_media_binary_is_never_review_ready_under_b1(self):
        p, d = self.complete()
        p["request"]["operation"] = "evaluate_media_binary"
        p["request"]["fields"] = ["id", "img"]
        p["reviewEvidence"]["mediaReviewId"] = "claimed-media-private"
        d["binding"]["packetSha256"] = packet_digest(p)
        self.assert_hold("INTAKE_NOT_READY", packet=p, docket=d)

    def test_any_objection_requires_human_resolution(self):
        p, d = self.complete()
        for objection in ("RIGHTS_CHAIN", "ATTRIBUTION", "PRIVACY",
                          "CONFLICT_OF_INTEREST", "MEDIA_RIGHTS", "OTHER"):
            d["review"]["objectionCodes"] = [objection]
            with self.subTest(objection=objection):
                self.assert_hold("OPEN_OBJECTIONS_REQUIRE_HUMAN_RESOLUTION",
                                 packet=p, docket=d)

    def test_declined_and_withdrawn_are_terminal_hold(self):
        p, d = self.complete()
        for stage in ("declined", "withdrawn"):
            d["review"]["stage"] = stage
            with self.subTest(stage=stage):
                self.assert_hold("REVIEW_DECLINED_OR_WITHDRAWN", packet=p, docket=d)

    def test_approval_stage_rejected_as_undefined(self):
        p, d = self.complete()
        for stage in ("approved", "published", "rights-cleared", True):
            d["review"]["stage"] = stage
            with self.subTest(stage=stage):
                self.assert_hold("UNRECOGNIZED_REVIEW_STAGE", packet=p, docket=d)

    def test_agent_chat_cannot_be_decision_channel(self):
        p, d = self.complete()
        d["review"]["decisionChannel"] = "agent-chat"
        self.assert_hold("REVIEW_CHANNEL_OR_CASE_INVALID", packet=p, docket=d)

    def test_publication_flag_smuggling_denied(self):
        p, d = self.complete()
        d["publicationAuthorized"] = True
        self.assert_hold("DOCKET_SHAPE_INVALID", packet=p, docket=d)

    def test_invalid_evidence_url_rejected(self):
        p, d = self.complete()
        d["review"]["evidenceRefs"]["reviewerIdentityEvidenceRef"] = "https://private.invalid/evidence"
        self.assert_hold("INVALID_PRIVATE_REFERENCE", packet=p, docket=d)

    def test_duplicate_unknown_objections_refused(self):
        p, d = self.complete()
        for codes in (["RIGHTS_CHAIN", "RIGHTS_CHAIN"], ["AUTOMATIC_CLEARANCE"], "RIGHTS_CHAIN"):
            d["review"]["objectionCodes"] = codes
            with self.subTest(codes=codes):
                self.assert_hold("OBJECTION_LIST_INVALID", packet=p, docket=d)

    def test_wrong_docket_structure_refused_without_crashing(self):
        p, d = self.complete()
        for item, error in (([], "DOCKET_SHAPE_INVALID"),
                            ({"kind": "anything"}, "DOCKET_SHAPE_INVALID"),
                            ({**d, "binding": []}, "BINDING_SHAPE_INVALID"),
                            ({**d, "review": None}, "REVIEW_SHAPE_INVALID")):
            with self.subTest(error=error):
                self.assert_hold(error, packet=p, docket=item)

    def test_bad_packet_refuses_cleanly(self):
        p, d = self.complete()
        self.assert_hold("PACKET_INVALID", packet={"x": float("nan")}, docket=d)

    def test_schema_explicitly_forbids_approval(self):
        s = json.loads(SCHEMA.read_text(encoding="utf-8"))
        self.assertEqual(s["$schema"], "https://json-schema.org/draft/2020-12/schema")
        self.assertFalse(s["additionalProperties"])
        self.assertFalse(s["properties"]["review"]["additionalProperties"])
        self.assertEqual(set(s["properties"]["review"]["properties"]["stage"]["enum"]),
                         {"awaiting-independent-review", "declined", "withdrawn"})
        self.assertIn("NOT DEPLOYED", s["description"])

    def test_cli_prints_no_private_reference(self):
        p, d = self.complete()
        with tempfile.TemporaryDirectory() as root:
            root = Path(root)
            for name, obj in (("packet", p), ("docket", d), ("inventory", self.inventory)):
                (root / (name+".json")).write_text(json.dumps(obj), encoding="utf-8")
            stdout = StringIO()
            with redirect_stdout(stdout):
                self.assertEqual(main(["--packet", str(root/"packet.json"),
                                       "--inventory", str(root/"inventory.json"),
                                       "--docket", str(root/"docket.json")]), 0)
            res = json.loads(stdout.getvalue())
            self.assertEqual(res["status"], HANDOFF)
            self.assertNotIn("private-", stdout.getvalue())
            self.assertNotIn("EXAMPLE_TEST_RECORD", stdout.getvalue())

    def test_no_publication_capability_in_module_or_example(self):
        example = json.loads(DOCKET.read_text(encoding="utf-8"))
        self.assertEqual(example["review"]["stage"], "awaiting-independent-review")
        self.assertTrue(example["review"]["objectionCodes"])
        self.assertIsNone(example["review"]["evidenceRefs"]["scopePermissionEvidenceRef"])
        self.assertTrue(all(_out()[key] is False for key in
                            ("rightsCleared", "humanApprovalVerified",
                             "publicationAuthorized", "deploymentAuthorized")))


if __name__ == "__main__":
    unittest.main()
