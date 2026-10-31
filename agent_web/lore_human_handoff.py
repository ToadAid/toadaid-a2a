"""P0-WEB-03B2A: OFFLINE handoff check for independent HUMAN rights review.

A review docket, reviewer ID or claimed proof is untrusted. This tool cannot
authenticate a reviewer, interpret legal rights, approve publication or execute.
It emits sanitized reason codes only; real proof stays in independent custody.
"""
import argparse
import hashlib
import json
import re

from agent_web.lore_rights_review import (
    _read_json, assess as assess_packet,
    REVIEW as PACKET_REVIEW,
)

DOCKET_KIND = "toadaid-lore-human-review-handoff"
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
REF = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")
REVIEW_STATES = {"awaiting-independent-review", "declined", "withdrawn"}
OBJECTION_CODES = {"SOURCE_IDENTITY", "RIGHTS_CHAIN", "PERMISSION_SCOPE",
                   "ATTRIBUTION", "PRIVACY", "WITHDRAWAL", "CONFLICT_OF_INTEREST",
                   "MEDIA_RIGHTS", "OTHER"}
REFS = ("reviewerIdentityEvidenceRef", "reviewerIndependenceEvidenceRef",
        "rightsChainEvidenceRef", "scopePermissionEvidenceRef",
        "attributionEvidenceRef", "privacyEvidenceRef",
        "withdrawalEvidenceRef", "conflictDisclosureEvidenceRef",
        "mediaEvidenceRef")
BINDING_KEYS = {"packetSha256", "sourceDigest", "sourceGitBlobSha1"}
DOCKET_KEYS = {"kind", "schemaVersion", "binding", "review"}
REVIEW_KEYS = {"caseRef", "stage", "decisionChannel", "evidenceRefs",
               "objectionCodes"}
HOLD = "HOLD_INDEPENDENT_HUMAN_REVIEW"
HANDOFF = "STRUCTURALLY_READY_FOR_HUMAN_REVIEW_ONLY"


def _canonical(obj):
    """Digest untrusted submitted data deterministically; no signature proof."""
    return json.dumps(obj, sort_keys=True, ensure_ascii=True,
                      separators=(",", ":"), allow_nan=False).encode("ascii")


def packet_digest(packet):
    return "sha256:" + hashlib.sha256(_canonical(packet)).hexdigest()


def _exact(value, keys):
    return isinstance(value, dict) and set(value) == keys


def _opaque(value):
    return isinstance(value, str) and REF.fullmatch(value) is not None


def _out(reasons=(), state=HOLD):
    return {
        "kind": "toadaid-human-rights-handoff-assessment",
        "status": state,
        "reasonCodes": sorted(set(reasons)),
        "proofReferencesEchoed": False,
        "reviewerIdentityVerified": False,
        "reviewerIndependenceVerified": False,
        "independentLegalReviewPerformed": False,
        "sourceAuthenticityVerifiedByTool": False,
        "rightsCleared": False,
        "humanApprovalVerified": False,
        "publicationAuthorized": False,
        "publicLoreExportEnabled": False,
        "mediaRehostingAuthorized": False,
        "deploymentAuthorized": False,
    }


def assess_handoff(packet, inventory, docket):
    """Return structural handoff-readiness, never a rights grant.

    This function compares *self-submitted* local files; none is a trust anchor.
    Real human verification must occur outside this repository and agent chat.
    """
    reasons = []
    try:
        packet_result = assess_packet(packet, inventory)
        digest = packet_digest(packet)
    except (TypeError, ValueError, OverflowError, RecursionError):
        return _out(["PACKET_INVALID"])
    if packet_result["status"] != PACKET_REVIEW:
        reasons.append("INTAKE_NOT_READY")
    if not _exact(docket, DOCKET_KEYS):
        return _out(reasons + ["DOCKET_SHAPE_INVALID"])
    if docket["kind"] != DOCKET_KIND or docket["schemaVersion"] != "0.1.0":
        reasons.append("DOCKET_VERSION_INVALID")
    binding = docket["binding"]
    if not _exact(binding, BINDING_KEYS):
        reasons.append("BINDING_SHAPE_INVALID")
    else:
        if (not isinstance(binding["packetSha256"], str) or
                SHA256.fullmatch(binding["packetSha256"]) is None or
                binding["packetSha256"] != digest):
            reasons.append("PACKET_DIGEST_MISMATCH")
        source = packet.get("source") if isinstance(packet, dict) else None
        if (not isinstance(source, dict) or
                binding["sourceDigest"] != source.get("sourceDigest") or
                binding["sourceGitBlobSha1"] != source.get("sourceGitBlobSha1")):
            reasons.append("SOURCE_BINDING_MISMATCH")
    review = docket["review"]
    if not _exact(review, REVIEW_KEYS):
        return _out(reasons + ["REVIEW_SHAPE_INVALID"])
    if (not _opaque(review["caseRef"]) or
            review["decisionChannel"] != "independent-off-chat-human-process"):
        reasons.append("REVIEW_CHANNEL_OR_CASE_INVALID")
    stage = review["stage"]
    if not isinstance(stage, str) or stage not in REVIEW_STATES:
        reasons.append("UNRECOGNIZED_REVIEW_STAGE")
    elif stage != "awaiting-independent-review":
        reasons.append("REVIEW_DECLINED_OR_WITHDRAWN")
    refs = review["evidenceRefs"]
    if not _exact(refs, set(REFS)):
        reasons.append("REVIEW_REFERENCES_SHAPE_INVALID")
    else:
        if any(value is not None and not _opaque(value) for value in refs.values()):
            reasons.append("INVALID_PRIVATE_REFERENCE")
        required = REFS[:-1]
        operation = (packet.get("request", {}).get("operation")
                     if isinstance(packet, dict) and isinstance(packet.get("request"), dict)
                     else None)
        if isinstance(operation, str) and operation.startswith("evaluate_media"):
            required = REFS
        if any(not _opaque(refs[name]) for name in required):
            reasons.append("HUMAN_REVIEW_EVIDENCE_REFERENCES_MISSING")
    objections = review["objectionCodes"]
    if (not isinstance(objections, list) or len(objections) > 16 or
            any(not isinstance(code, str) or code not in OBJECTION_CODES
                for code in objections) or
            len(set(objections)) != len(objections)):
        reasons.append("OBJECTION_LIST_INVALID")
    elif objections:
        # Preserve every unresolved objection; never discard to claim readiness.
        reasons.append("OPEN_OBJECTIONS_REQUIRE_HUMAN_RESOLUTION")
    if reasons:
        return _out(reasons)
    return _out((), HANDOFF)


def main(argv=None):
    parser = argparse.ArgumentParser(description="OFFLINE human-review handoff; NEVER APPROVES")
    parser.add_argument("--packet", required=True, help="private untrusted intake")
    parser.add_argument("--inventory", required=True, help="private local source inventory")
    parser.add_argument("--docket", required=True, help="private untrusted handoff")
    args = parser.parse_args(argv)
    try:
        result = assess_handoff(_read_json(args.packet),
                                _read_json(args.inventory),
                                _read_json(args.docket))
    except (OSError, ValueError, TypeError, UnicodeError):
        result = _out(["INPUT_INVALID_OR_UNAVAILABLE"])
    print(json.dumps(result, sort_keys=True, indent=2))
    return 0  # Prints a verdict; NEVER an approval.


if __name__ == "__main__":
    raise SystemExit(main())
