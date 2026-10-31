"""P0-WEB-03A: synthetic local Git object inventory tests; no network or real lore."""
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

from agent_web.lore_provenance import (
    ACCEPTED_ORIGINS, InventoryRefusal, _validate, inventory,
    SOURCE_PATH, SOURCE_REPO,
)

CANONICAL_ORIGIN = "https://github.com/ToadAid/toadaid.github.io.git"


def record(record_id="TOBY_TEST_Synthetic"):
    return {"id": record_id, "date": "2026-01-01", "title": "Fictional",
            "original": "SYNTHETIC_SECRET_DO_NOT_PUBLISH",
            "comment": "A purely fictional archive test.", "url": "",
            "img": "https://example.invalid/no-real-image", "tags": "test"}


class LocalGitSourceTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.root = Path(self.tmp.name)
        self.git("init", "-q")
        self.git("remote", "add", "origin", CANONICAL_ORIGIN)
        (self.root / "lore").mkdir()
        self.commit = self.write_commit([record()])

    def tearDown(self):
        self.tmp.cleanup()

    def git(self, *argv):
        proc = subprocess.run(["git", "-C", str(self.root), *argv],
                              text=True, capture_output=True, timeout=5)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        return proc.stdout.strip()

    def write_commit(self, records):
        path = self.root / SOURCE_PATH
        path.write_text(json.dumps(records, ensure_ascii=False), encoding="utf-8")
        self.git("add", SOURCE_PATH)
        self.git("-c", "user.name=ToadAid Test",
                 "-c", "user.email=test@example.invalid",
                 "-c", "commit.gpgsign=false", "commit", "-qm", "synthetic lore snapshot")
        return self.git("rev-parse", "HEAD")

    def test_reads_exact_committed_object_and_never_returns_lore_bodies(self):
        recordset = inventory(self.root, self.commit)
        self.assertEqual(recordset["repository"], SOURCE_REPO)
        self.assertEqual(recordset["path"], SOURCE_PATH)
        self.assertEqual(recordset["commit"], self.commit)
        self.assertEqual(recordset["recordCount"], 1)
        self.assertEqual(recordset["uniqueCanonicalIds"], 1)
        self.assertEqual(recordset["legacyImageReferences"], 1)
        self.assertTrue(recordset["originalAndCommentPreservedSeparately"])
        self.assertTrue(recordset["archiveDateIsNotPublicationDate"])
        self.assertTrue(recordset["originStringIsNotIndependentAuthenticityProof"])
        self.assertEqual(recordset["rightsStatus"], "unknown")
        for key in ("rightsReviewed", "publicExportAuthorized", "recordBodiesIncluded",
                    "mediaPreservationClaimed", "productionDeploymentAuthorized"):
            self.assertIs(recordset[key], False)
        self.assertNotIn("SYNTHETIC_SECRET_DO_NOT_PUBLISH", json.dumps(recordset))
        self.assertTrue(recordset["sourceDigest"].startswith("sha256:"))
        self.assertEqual(recordset["sourceGitBlobSha1"], self.git("rev-parse",
                                                               self.commit + ":" + SOURCE_PATH))

    def test_working_tree_mutation_cannot_change_pinned_inventory(self):
        baseline = inventory(self.root, self.commit)
        (self.root / SOURCE_PATH).write_text("secret or invalid working-tree bytes")
        self.assertEqual(inventory(self.root, self.commit), baseline)

    def test_reviewed_commit_must_exist_and_be_exact(self):
        with self.assertRaises(InventoryRefusal):
            inventory(self.root, "main")
        with self.assertRaises(InventoryRefusal):
            inventory(self.root, "f" * 40)

    def test_canonical_origin_is_not_caller_override(self):
        self.git("remote", "set-url", "origin", "https://github.com/other/forged.git")
        with self.assertRaisesRegex(InventoryRefusal, "origin"):
            inventory(self.root, self.commit)

    def test_bad_required_fields_fail(self):
        for field in ("id", "date", "title", "comment"):
            item = record()
            item[field] = " "
            with self.subTest(field=field), self.assertRaises(InventoryRefusal):
                _validate(json.dumps([item]).encode())

    def test_duplicate_ids_fail_without_silent_repair(self):
        with self.assertRaisesRegex(InventoryRefusal, "duplicate"):
            _validate(json.dumps([record(), record()]).encode())

    def test_bad_optional_field_type_fails(self):
        item = record()
        item["img"] = ["not valid"]
        with self.assertRaisesRegex(InventoryRefusal, "optional"):
            _validate(json.dumps([item]).encode())

    def test_unknown_optional_fields_do_not_create_authority(self):
        item = record()
        item["publishedAt"] = "fiction"
        item["rightsStatus"] = "cleared"
        self.assertEqual(_validate(json.dumps([item]).encode()), (1, 1))
        self.assertFalse(inventory(self.root, self.commit)["publicExportAuthorized"])

    def test_malformed_and_duplicate_json_fields_refused(self):
        for raw in (b"not json", b"[]", b'{"id":"x","id":"y"}',
                    b'[{"id":"x","id":"y"}]', b'[NaN]'):
            with self.subTest(raw=raw), self.assertRaises(InventoryRefusal):
                _validate(raw)

    def test_oversized_input_refused(self):
        with self.assertRaisesRegex(InventoryRefusal, "bound"):
            _validate(b" " * (2 * 1024 * 1024 + 1))

    def test_no_independent_media_preservation_claim(self):
        with_image = inventory(self.root, self.commit)
        self.assertEqual(with_image["legacyImageReferences"], 1)
        self.assertFalse(with_image["mediaPreservationClaimed"])

    def test_origin_is_only_declared_identity_not_cryptographic_identity(self):
        self.assertIn(CANONICAL_ORIGIN, ACCEPTED_ORIGINS)
        self.assertTrue(inventory(self.root, self.commit)["originStringIsNotIndependentAuthenticityProof"])



class SourceObservationContractTests(unittest.TestCase):
    def test_architecture_evidence_does_not_claim_publication_rights(self):
        root = Path(__file__).resolve().parents[1]
        item = json.loads((root / "contracts/agent-web/lore-source-inventory.v0.json").read_text())
        self.assertEqual(item["fixedCanonicalRepository"], SOURCE_REPO)
        self.assertEqual(item["fixedCanonicalPath"], SOURCE_PATH)
        self.assertEqual(item["generationSpecificObservation"]["observedRecordCount"], 132)
        self.assertEqual(item["generationSpecificObservation"]["sourceGitBlobSha1"],
                         "b81d32c951d754780ac310e38b81a17f21292fe1")
        self.assertIs(item["generationSpecificObservation"]["thisObservationIsPermanentPin"], False)
        self.assertIs(item["generationSpecificObservation"]["sha256SourceDigestVerifiedHere"], False)
        for key in ("rightsReviewed", "publicTextExportAuthorized", "publicMediaExportAuthorized",
                    "commercialReuseAuthorized", "ownerRightsOrAuthorshipAsserted",
                    "productionDeploymentAuthorized"):
            self.assertIs(item["authority"][key], False, key)
        self.assertEqual(item["authority"]["rightsStatus"], "unknown")
        self.assertIs(item["provenanceBoundaries"]["legacyImageReferenceProvesPreservation"], False)

    def test_documentation_preserves_reader_provenance_and_tck_hold(self):
        root = Path(__file__).resolve().parents[1]
        doc = (root / "docs/agent-web/p0-web-03a-lore-source-inventory.md").read_text()
        for phrase in ("132 records", "original", "comment", "rights", "P0-WEB-03B",
                       "Official A2A TCK remains UNRUN", "NOT DEPLOYED"):
            self.assertIn(phrase, doc)



if __name__ == "__main__":
    unittest.main()
