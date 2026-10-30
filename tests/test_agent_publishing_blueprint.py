"""P0-WEB-01 architecture-only publishing plan invariants; no network or endpoints.

These tests protect planning metadata. They do NOT test a deployed service,
A2A conformance, data rights, real-world provenance, or enforcement.
"""
import copy
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
PLAN = ROOT / "contracts/agent-web/publishing-plan.v0.json"
EXAMPLE = ROOT / "contracts/agent-web/examples/synthetic-lore-resource.v0.json"
BLUEPRINT = ROOT / "docs/agent-web/p0-web-01-agent-native-publishing-blueprint.md"
GATES = ROOT / "docs/agent-web/p0-web-01-acceptance-gates.md"

EXPECTED_DOMAINS = {
    "humanPortal": "https://portal.toadaid.org",
    "agentNative": "https://agent.toadaid.org",
    "governedTools": "https://mcp.toadaid.org",
}
EXPECTED_DISCOVERY = {
    "a2a-agent-card": ("/.well-known/agent-card.json", "standard-a2a-discovery"),
    "llms-index": ("/llms.txt", "optional-convention"),
    "siteai-policy": ("/siteai.json", "experimental-draft"),
}
MIME = {
    "browser": ("text/html", "text/html; charset=utf-8"),
    "reader": ("text/markdown", "text/markdown; charset=utf-8"),
    "structured": ("application/json", "application/json; charset=utf-8"),
}
RELEASE_FALSE = (
    "agentCardPublished", "llmsIndexPublished", "siteaiPolicyPublished",
    "markdownServingEnabled", "loreRecordsPublished", "actionsEnabled",
    "officialTckExecuted", "productionDeploymentAuthorized",
)
ACTION_FALSE = (
    "requestIsGrant", "agentCardGrantsExecution", "discoveryFileGrantsExecution",
    "chatGrantsExecution", "signedIdentityGrantsExecution", "approvalViaChatAllowed",
)


def validate(plan):
    """Return architecture-policy violations, not a published wire-schema verdict."""
    errors = []
    if not isinstance(plan, dict):
        return ["plan object missing"]
    if (plan.get("kind") != "toadaid-agent-native-publishing-plan"
            or plan.get("planVersion") != "0.1.0"
            or plan.get("status") != "architecture-only-not-deployed"
            or plan.get("wireProtocol") is not False
            or plan.get("serviceActive") is not False):
        errors.append("plan must be architecture-only and not live")
    if plan.get("domains") != EXPECTED_DOMAINS:
        errors.append("domain boundaries changed")
    discovery = plan.get("discovery")
    if not isinstance(discovery, list) or len(discovery) != len(EXPECTED_DISCOVERY):
        errors.append("discovery shape")
    else:
        seen = set()
        for item in discovery:
            if not isinstance(item, dict) or item.get("kind") not in EXPECTED_DISCOVERY:
                errors.append("unrecognized discovery item")
                continue
            kind = item["kind"]
            if kind in seen:
                errors.append("duplicate discovery item")
            seen.add(kind)
            if (item.get("candidatePath"), item.get("classification")) != EXPECTED_DISCOVERY[kind]:
                errors.append("discovery classification/path")
            if item.get("publishAuthorized") is not False or item.get("confersAuthorization") is not False:
                errors.append("discovery publication/authority violation")
            if kind == "a2a-agent-card" and item.get("requiresQualifiedLiveEndpoint") is not True:
                errors.append("A2A card needs an actual qualified endpoint")
        if seen != set(EXPECTED_DISCOVERY):
            errors.append("missing discovery kind")
    reps = plan.get("representations", {})
    if reps.get("status") != "planned-only":
        errors.append("representation incorrectly active")
    if reps.get("canonicalSourceRequired") is not True or reps.get("sameFactsAcrossRepresentations") is not True:
        errors.append("representation parity")
    negotiation = reps.get("contentNegotiation", {})
    if not isinstance(negotiation, dict):
        errors.append("missing negotiation")
    else:
        for kind, (accept, response) in MIME.items():
            item = negotiation.get(kind, {})
            if item != {"accept": accept, "responseContentType": response}:
                errors.append("representation MIME mismatch")
        if (negotiation.get("varyHeader") != "Accept"
                or negotiation.get("cacheMustPartitionByRepresentation") is not True
                or negotiation.get("privateCacheMustPartitionByAuthorization") is not True
                or negotiation.get("noUserAgentSniffing") is not True):
            errors.append("cache or negotiation safety")
    content = plan.get("content", {})
    if content.get("publicationDefault") != "withhold-until-approved":
        errors.append("content default publication")
    if set(content.get("classificationValues", [])) != {
        "original_lore", "onchain_metadata", "community_creation",
        "imagined_visual", "editorial_summary",
    }:
        errors.append("missing provenance distinctions")
    if set(content.get("verificationValues", [])) != {"verified", "unverified"}:
        errors.append("verification taxonomy missing")
    for key in ("publicProvenanceRequired", "rightsReviewRequired"):
        if content.get(key) is not True:
            errors.append("content verification/rights requirement")
    for key in ("privateJournalExportAllowed", "privatePromptExportAllowed"):
        if content.get(key) is not False:
            errors.append("private content exposure")
    if content.get("syntheticExample") != "contracts/agent-web/examples/synthetic-lore-resource.v0.json":
        errors.append("synthetic example reference changed")
    actions = plan.get("actions", {})
    if actions.get("status") != "not-implemented" or actions.get("defaultPolicy") != "deny":
        errors.append("actions accidentally enabled")
    for key in ACTION_FALSE:
        if actions.get(key) is not False:
            errors.append("action grant boundary " + key)
    for key in ("executionRequiresCurrentExactGrant", "tenantDerivedFromTrustedServer", "serverEnforcementRequired"):
        if actions.get(key) is not True:
            errors.append("action enforcement boundary " + key)
    release = plan.get("release", {})
    for key in RELEASE_FALSE:
        if release.get(key) is not False:
            errors.append("release flag must stay false " + key)
    return errors


class PublishingBlueprintTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.plan = json.loads(PLAN.read_text(encoding="utf-8"))
        cls.example = json.loads(EXAMPLE.read_text(encoding="utf-8"))

    def test_plan_matches_non_live_contract(self):
        self.assertEqual(validate(self.plan), [])

    def test_synthetic_example_contains_no_real_deed_or_verified_claim(self):
        rec = self.example
        self.assertEqual(rec["kind"], "toadaid-synthetic-lore-resource-example")
        self.assertEqual(rec["status"], "SYNTHETIC-NONCANONICAL-NOT-PUBLISHED")
        self.assertTrue(rec["recordId"].startswith("example:"))
        for key in ("realDeed", "canonicalLore", "publicPublicationAuthorized",
                    "privateDataIncluded", "indexingAllowed"):
            self.assertIs(rec[key], False)
        self.assertEqual(rec["representationContract"], "toadaid-agent-native-publishing-plan/0.1.0")
        self.assertEqual(len(rec["provenance"]), 1)
        item = rec["provenance"][0]
        self.assertEqual(item["classification"], "imagined_visual")
        self.assertEqual(item["verification"], "unverified")
        for key in ("creatorIdentityVerified", "chainOwnershipVerified", "rightsVerified"):
            self.assertIs(item[key], False)
        self.assertIsNone(item["sourceUrl"])

    def mutate(self, fn, expected):
        changed = copy.deepcopy(self.plan)
        fn(changed)
        messages = validate(changed)
        self.assertTrue(any(expected in err for err in messages), messages)

    def test_negative_card_published(self):
        self.mutate(lambda x: x["release"].__setitem__("agentCardPublished", True), "release flag")

    def test_negative_fake_policy_grant(self):
        self.mutate(lambda x: x["discovery"][2].__setitem__("confersAuthorization", True), "discovery publication")

    def test_negative_card_without_qualified_service(self):
        self.mutate(lambda x: x["discovery"][0].__setitem__("requiresQualifiedLiveEndpoint", False), "qualified endpoint")

    def test_negative_server_claimed_live(self):
        self.mutate(lambda x: x.__setitem__("serviceActive", True), "architecture-only")

    def test_negative_cross_format_factual_divergence(self):
        self.mutate(lambda x: x["representations"].__setitem__("sameFactsAcrossRepresentations", False), "parity")

    def test_negative_unsafe_cache_variance(self):
        self.mutate(lambda x: x["representations"]["contentNegotiation"].__setitem__("varyHeader", ""), "cache")

    def test_negative_unauthorized_lore_publication(self):
        self.mutate(lambda x: x["release"].__setitem__("loreRecordsPublished", True), "release flag")

    def test_negative_unreviewed_rights(self):
        self.mutate(lambda x: x["content"].__setitem__("rightsReviewRequired", False), "rights")

    def test_negative_raw_private_journals(self):
        self.mutate(lambda x: x["content"].__setitem__("privateJournalExportAllowed", True), "private content")

    def test_negative_client_supplied_tenant_grants_auth(self):
        self.mutate(lambda x: x["actions"].__setitem__("tenantDerivedFromTrustedServer", False), "enforcement")

    def test_negative_chat_permission(self):
        self.mutate(lambda x: x["actions"].__setitem__("chatGrantsExecution", True), "grant")

    def test_negative_default_allow(self):
        self.mutate(lambda x: x["actions"].__setitem__("defaultPolicy", "allow"), "actions accidentally enabled")

    def test_negative_duplicate_discovery(self):
        self.mutate(lambda x: x["discovery"].__setitem__(1, copy.deepcopy(x["discovery"][0])), "duplicate")

    def test_documented_exclusions_and_gates(self):
        text = BLUEPRINT.read_text(encoding="utf-8")
        gate = GATES.read_text(encoding="utf-8")
        for phrase in ("NOT DEPLOYED", "A2A Agent Card", "Vary: Accept",
                       "JOURNAL", "original_lore", "imagined_visual",
                       "siteai.json", "llms.txt", "P0B-C2", "P0C", "P0E"):
            if phrase == "JOURNAL":
                self.assertIn("Journal-before-delivery", text)
            else:
                self.assertIn(phrase, text)
        self.assertIn("NO SERVICE OR GRANT AUTHORIZED", gate)
        self.assertIn("ONE CUT", gate)


if __name__ == "__main__":
    unittest.main()
