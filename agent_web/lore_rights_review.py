"""P0-WEB-03B1: offline rights-review packet classifier, NEVER a publisher.

A submitted packet is untrusted *evidence for human review*, not consent, an
authorization grant, verified authorship, source authenticity or a license.
Nothing in this module can turn rights/public publication flags on.
"""
import argparse
import json
from pathlib import Path
import re

REPO = "ToadAid/toadaid.github.io"
SOURCE_PATH = "lore/data.json"
PACKET_KIND = "toadaid-lore-rights-review-request"
INVENTORY_KIND = "toadaid-local-lore-inventory"
INVENTORY_STATUS = "LOCAL_OBJECT_ONLY_RIGHTS_HOLD_NOT_PUBLISHED"
SOURCE_KEYS = {"repository", "path", "commit", "sourceGitBlobSha1", "sourceDigest", "recordCount"}
PACKET_KEYS = {"kind", "schemaVersion", "source", "request", "reviewEvidence"}
REQUEST_KEYS = {"operation", "audience", "recordIds", "fields", "purpose"}
REVIEW_KEYS = {"rightsStatus", "permissionEvidenceId", "attributionReviewId",
               "privacyReviewId", "withdrawalPlanId", "humanReviewerAttestationId",
               "mediaReviewId"}
FIELDS = {"id", "date", "title", "original", "comment", "url", "img", "tags"}
OPERATIONS = {"evaluate_metadata", "evaluate_lore_text", "evaluate_media_reference",
              "evaluate_media_binary"}
RIGHTS = {"unknown", "restricted", "disputed", "permission_claimed",
          "public_domain_claimed"}
HEX40 = re.compile(r"[0-9a-f]{40}\Z")
SHA256 = re.compile(r"sha256:[0-9a-f]{64}\Z")
OPAQUE = re.compile(r"[a-z][a-z0-9-]{2,63}\Z")
IDENTITY = re.compile(r"[A-Za-z0-9_:-]{3,128}\Z")
HOLD = "HOLD_NO_PUBLICATION"
REVIEW = "READY_FOR_INDEPENDENT_HUMAN_REVIEW_ONLY"


def _exact_keys(obj, keys):
    return isinstance(obj, dict) and set(obj) == keys


def _opaque(value):
    return isinstance(value, str) and OPAQUE.fullmatch(value) is not None


def assess(packet, inventory):
    """Only returns sanitized reason codes; never echoes rights evidence or lore.

    Valid, apparently complete claims may qualify for independent *review*
    but never for publication. Neither input is independently authenticated.
    """
    reasons = []
    if not _exact_keys(packet, PACKET_KEYS):
        reasons.append("PACKET_SHAPE_INVALID")
    elif packet["kind"] != PACKET_KIND or packet["schemaVersion"] != "0.1.0":
        reasons.append("PACKET_VERSION_INVALID")
    if not isinstance(inventory, dict) or inventory.get("kind") != INVENTORY_KIND or (
            inventory.get("status") != INVENTORY_STATUS):
        reasons.append("INVENTORY_STATUS_UNTRUSTED")
    else:
        for flag in ("rightsReviewed", "publicExportAuthorized",
                     "recordBodiesIncluded", "mediaPreservationClaimed",
                     "productionDeploymentAuthorized"):
            if inventory.get(flag) is not False:
                reasons.append("INVENTORY_AUTHORITY_INVALID")
                break
    if reasons and "PACKET_SHAPE_INVALID" in reasons:
        return _result(reasons)

    source = packet.get("source")
    req = packet.get("request")
    evidence = packet.get("reviewEvidence")
    if not _exact_keys(source, SOURCE_KEYS):
        reasons.append("SOURCE_SHAPE_INVALID")
    else:
        if (source["repository"] != REPO or source["path"] != SOURCE_PATH
                or not isinstance(source["commit"], str)
                or not HEX40.fullmatch(source["commit"])
                or not isinstance(source["sourceGitBlobSha1"], str)
                or not HEX40.fullmatch(source["sourceGitBlobSha1"])
                or not isinstance(source["sourceDigest"], str)
                or not SHA256.fullmatch(source["sourceDigest"])
                or type(source["recordCount"]) is not int
                or not 0 < source["recordCount"] <= 200000):
            reasons.append("SOURCE_FORMAT_INVALID")
        if isinstance(inventory, dict):
            binding = {
                "repository": inventory.get("repository"),
                "path": inventory.get("path"),
                "commit": inventory.get("commit"),
                "sourceGitBlobSha1": inventory.get("sourceGitBlobSha1"),
                "sourceDigest": inventory.get("sourceDigest"),
                "recordCount": inventory.get("recordCount"),
            }
            if any(source.get(k) != v for k, v in binding.items()):
                reasons.append("SOURCE_GENERATION_MISMATCH")
    if not _exact_keys(req, REQUEST_KEYS):
        reasons.append("REQUEST_SHAPE_INVALID")
    else:
        op = req["operation"]
        fields = req["fields"]
        ids = req["recordIds"]
        if not isinstance(op, str) or op not in OPERATIONS or req["audience"] != "public-agent-native-web" or (
                not isinstance(req["purpose"], str) or
                not 1 <= len(req["purpose"]) <= 180 or not req["purpose"].strip()):
            reasons.append("REQUEST_PURPOSE_INVALID")
        if (not isinstance(fields, list) or not fields
                or len(fields) > len(FIELDS)
                or any(not isinstance(x, str) or x not in FIELDS for x in fields)
                or len(set(fields)) != len(fields)):
            reasons.append("REQUEST_FIELDS_INVALID")
        elif (op == "evaluate_metadata" and
              bool({"original", "comment", "img"}.intersection(fields))):
            reasons.append("REQUEST_SCOPE_CONFLICT")
        elif op == "evaluate_lore_text" and not ({"original", "comment"} & set(fields)):
            reasons.append("REQUEST_SCOPE_CONFLICT")
        elif isinstance(op, str) and op in {"evaluate_media_reference", "evaluate_media_binary"} and "img" not in fields:
            reasons.append("REQUEST_SCOPE_CONFLICT")
        if (not isinstance(ids, list) or not 1 <= len(ids) <= 25 or
                any(not isinstance(x, str) or not IDENTITY.fullmatch(x) for x in ids)
                or len(set(ids)) != len(ids)):
            reasons.append("RECORD_SCOPE_INVALID")
        if op == "evaluate_media_binary":
            reasons.append("MEDIA_BINARY_INDEPENDENT_GATE_REQUIRED")
    if not _exact_keys(evidence, REVIEW_KEYS):
        reasons.append("REVIEW_EVIDENCE_SHAPE_INVALID")
    else:
        status = evidence["rightsStatus"]
        if not isinstance(status, str) or status not in RIGHTS:
            reasons.append("RIGHTS_STATUS_INVALID")
        elif status in {"unknown", "restricted", "disputed"}:
            reasons.append("RIGHTS_NOT_ADMITTED")
        for field in REVIEW_KEYS - {"rightsStatus"}:
            if evidence[field] is not None and not _opaque(evidence[field]):
                reasons.append("EVIDENCE_REFERENCE_INVALID")
                break
        needed = ["attributionReviewId", "privacyReviewId", "withdrawalPlanId",
                  "humanReviewerAttestationId"]
        if status == "permission_claimed":
            needed.append("permissionEvidenceId")
        if req and isinstance(req, dict) and isinstance(req.get("operation"), str) and req.get("operation", "").startswith("evaluate_media"):
            needed.append("mediaReviewId")
        if isinstance(status, str) and status in {"permission_claimed", "public_domain_claimed"} and any(
                not _opaque(evidence.get(k)) for k in needed):
            reasons.append("HUMAN_EVIDENCE_INCOMPLETE")
    if not reasons:
        return _result([], REVIEW)
    return _result(sorted(set(reasons)))


def _result(reasons, state=HOLD):
    return {
        "kind": "toadaid-rights-packet-assessment",
        "status": state,
        "reasonCodes": sorted(set(reasons)),
        "packetFieldsEchoed": False,
        "externalEvidenceVerified": False,
        "rightsLegallyDetermined": False,
        "rightsClearedByProgram": False,
        "publicationAuthorized": False,
        "publicLoreExportEnabled": False,
        "mediaRehostingAuthorized": False,
        "humanApprovalSatisfiedByPacket": False,
        "agentOrChatApprovalAccepted": False,
        "deploymentAuthorized": False,
    }


def _reject_duplicates(pairs):
    obj = {}
    for k, v in pairs:
        if k in obj:
            raise ValueError("duplicate key")
        obj[k] = v
    return obj


def _read_json(path, maximum=32768):
    # Explicit local operator-supplied files only; no fetch/network or writes.
    with Path(path).open("rb") as f:
        data = f.read(maximum + 1)
    if len(data) > maximum:
        raise ValueError("input size bound")
    return json.loads(data.decode("utf-8"), object_pairs_hook=_reject_duplicates,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError("non-finite")))


def main(argv=None):
    parser = argparse.ArgumentParser(description="OFFLINE RIGHTS PACKET REVIEW; NEVER A PUBLICATION GRANT")
    parser.add_argument("--packet", required=True, help="private local review request JSON")
    parser.add_argument("--inventory", required=True, help="local source metadata inventory JSON")
    args = parser.parse_args(argv)
    try:
        result = assess(_read_json(args.packet), _read_json(args.inventory))
    except (OSError, ValueError, TypeError, UnicodeError):
        result = _result(["INPUT_INVALID_OR_UNAVAILABLE"])
    print(json.dumps(result, sort_keys=True, indent=2))
    # Exit 0 means assessment printed, NOT permission; status is always non-admission.
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
