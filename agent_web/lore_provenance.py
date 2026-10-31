"""P0-WEB-03A: offline canonical lore source inventory, NOT a publishing/export tool.

Reads one exact local Git object from the immutable Lore Reader source identity.
Never fetches, copies lore text/images, grants rights or contacts the network.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess

SOURCE_REPO = "ToadAid/toadaid.github.io"
SOURCE_PATH = "lore/data.json"
ACCEPTED_ORIGINS = frozenset({
    "https://github.com/ToadAid/toadaid.github.io.git",
    "https://github.com/ToadAid/toadaid.github.io",
    "git@github.com:ToadAid/toadaid.github.io.git",
})
MAX_SOURCE_BYTES = 2 * 1024 * 1024
COMMIT_RE = re.compile(r"[0-9a-f]{40}\Z")


class InventoryRefusal(ValueError):
    """A source cannot be admitted as a bounded candidate inventory."""


def _git(checkout, *args):
    environment = os.environ.copy()
    environment.update({"GIT_TERMINAL_PROMPT": "0",
                        "GIT_CONFIG_NOSYSTEM": "1",
                        "GIT_CONFIG_GLOBAL": os.devnull,
                        "GIT_NO_REPLACE_OBJECTS": "1"})
    try:
        run = subprocess.run(["git", "-C", str(checkout), *args], check=False,
                             capture_output=True, timeout=7, env=environment)
    except (OSError, subprocess.TimeoutExpired) as exc:
        raise InventoryRefusal("local read-only Git command unavailable") from exc
    if run.returncode:
        raise InventoryRefusal("local Git source or object unavailable")
    return run.stdout


def _distinct_object_pairs(pairs):
    value = {}
    for key, member in pairs:
        if key in value:
            raise InventoryRefusal("duplicate JSON member in source")
        value[key] = member
    return value


def _validate(raw):
    if not isinstance(raw, bytes) or not 0 < len(raw) <= MAX_SOURCE_BYTES:
        raise InventoryRefusal("canonical source exceeds byte bound")
    try:
        records = json.loads(raw.decode("utf-8"), object_pairs_hook=_distinct_object_pairs,
                             parse_constant=lambda _: (_ for _ in ()).throw(
                                 InventoryRefusal("invalid JSON numeric constant")))
    except InventoryRefusal:
        raise
    except (UnicodeError, ValueError, RecursionError) as exc:
        raise InventoryRefusal("invalid canonical JSON data") from exc
    if not isinstance(records, list) or not records:
        raise InventoryRefusal("expected nonempty canonical record array")
    observed = set()
    legacy_media_count = 0
    for record in records:
        if not isinstance(record, dict):
            raise InventoryRefusal("non-object lore record")
        for field in ("id", "date", "title", "comment"):
            value = record.get(field)
            if not isinstance(value, str) or not value.strip():
                raise InventoryRefusal("missing required canonical record field")
        if record["id"] in observed:
            raise InventoryRefusal("duplicate canonical lore ID")
        observed.add(record["id"])
        for field in ("original", "url", "img", "tags"):
            if field in record and not isinstance(record[field], str):
                raise InventoryRefusal("invalid optional canonical field")
        if record.get("img"):
            legacy_media_count += 1
    return len(observed), legacy_media_count


def inventory(local_canonical_checkout, reviewed_commit):
    """Inventory a reviewed local Git object; never copy or publish record bodies."""
    if not isinstance(reviewed_commit, str) or not COMMIT_RE.fullmatch(reviewed_commit):
        raise InventoryRefusal("exact lowercase reviewed commit required")
    root = Path(local_canonical_checkout).resolve(strict=True)
    if not root.is_dir():
        raise InventoryRefusal("local checkout must be a directory")
    origin = _git(root, "remote", "get-url", "origin").decode("utf-8", errors="replace").strip()
    if origin not in ACCEPTED_ORIGINS:
        raise InventoryRefusal("local checkout origin is not canonical Lore repository")
    actual = _git(root, "rev-parse", "--verify", reviewed_commit + "^{commit}").decode("ascii").strip()
    if actual != reviewed_commit:
        raise InventoryRefusal("reviewed commit did not resolve exactly")
    expression = reviewed_commit + ":" + SOURCE_PATH
    object_type = _git(root, "cat-file", "-t", expression).decode("ascii").strip()
    if object_type != "blob":
        raise InventoryRefusal("canonical object is not a blob")
    size = _git(root, "cat-file", "-s", expression).decode("ascii").strip()
    if not size.isdecimal() or not 0 < int(size) <= MAX_SOURCE_BYTES:
        raise InventoryRefusal("canonical source exceeds byte bound")
    raw = _git(root, "cat-file", "blob", expression)
    if len(raw) != int(size):
        raise InventoryRefusal("Git object byte length mismatch")
    count, legacy_media = _validate(raw)
    blob = _git(root, "rev-parse", expression).decode("ascii").strip()
    if not COMMIT_RE.fullmatch(blob):
        raise InventoryRefusal("invalid Git blob identity")
    return {
        "kind": "toadaid-local-lore-inventory",
        "status": "LOCAL_OBJECT_ONLY_RIGHTS_HOLD_NOT_PUBLISHED",
        "repository": SOURCE_REPO,
        "path": SOURCE_PATH,
        "commit": reviewed_commit,
        "sourceGitBlobSha1": blob,
        "sourceDigest": "sha256:" + hashlib.sha256(raw).hexdigest(),
        "recordCount": count,
        "uniqueCanonicalIds": count,
        "legacyImageReferences": legacy_media,
        "originalAndCommentPreservedSeparately": True,
        "archiveDateIsNotPublicationDate": True,
        "originStringIsNotIndependentAuthenticityProof": True,
        "rightsStatus": "unknown",
        "rightsReviewed": False,
        "publicExportAuthorized": False,
        "recordBodiesIncluded": False,
        "mediaPreservationClaimed": False,
        "productionDeploymentAuthorized": False,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description="Read-only local Git lore inventory; NOT an exporter")
    parser.add_argument("--canonical-repo", required=True,
                        help="existing local checkout of the fixed canonical repository")
    parser.add_argument("--commit", required=True, help="40-character reviewed commit SHA")
    args = parser.parse_args(argv)
    try:
        result = inventory(args.canonical_repo, args.commit)
    except (InventoryRefusal, OSError, ValueError) as exc:
        print("LORE_INVENTORY_REFUSED: " + str(exc))
        return 1
    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
