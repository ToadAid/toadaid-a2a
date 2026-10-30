"""Offline A2A v1.0 Agent Card safety/profile inspector, not protocol certification.

No network I/O, HTTP serving, authentication, endpoint probe or authority.
"""
import ipaddress
import json
import sys
from pathlib import Path
from urllib.parse import urlsplit

MAX_CARD_BYTES = 65536
MAX_INTERFACES = 8
MAX_SKILLS = 32
BINDINGS = frozenset(("JSONRPC", "GRPC", "HTTP+JSON"))
LEGACY = frozenset(("url", "preferredTransport", "additionalInterfaces",
                    "protocolVersion", "supportsAuthenticatedExtendedCard", "security"))
SENSITIVE = frozenset(("privatekey", "secret", "password", "apikey", "accesstoken",
                       "refreshtoken", "bearertoken", "clientsecret", "mnemonic"))


class CardError(ValueError):
    pass


def _object_no_duplicates(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise CardError("duplicate JSON field")
        result[key] = value
    return result


def parse_bytes(raw):
    if not isinstance(raw, bytes) or len(raw) > MAX_CARD_BYTES:
        raise CardError("card missing or larger than 65536 bytes")
    try:
        card = json.loads(raw.decode("utf-8"), object_pairs_hook=_object_no_duplicates,
                          parse_constant=lambda _: (_ for _ in ()).throw(CardError("non-finite number")))
    except (UnicodeError, json.JSONDecodeError) as exc:
        raise CardError("invalid UTF-8 or JSON") from exc
    if not isinstance(card, dict):
        raise CardError("card must be an object")
    return card


def _text(value, limit=256):
    return isinstance(value, str) and 0 < len(value.strip()) <= limit


def _str_list(values, max_items=32):
    return (isinstance(values, list) and 0 < len(values) <= max_items
            and all(_text(v, 120) for v in values) and len(set(values)) == len(values))


def _public_https(url):
    if not _text(url, 2048):
        return False
    try:
        parsed = urlsplit(url)
        host = parsed.hostname
        if (parsed.scheme != "https" or not host or parsed.username is not None
                or parsed.password is not None or parsed.fragment or parsed.query
                or parsed.port not in (None, 443) or any(c.isspace() for c in url)):
            return False
        if host == "localhost" or host.endswith((".localhost", ".local", ".internal")):
            return False
        if "." not in host or not parsed.netloc:
            return False
        try:
            ipaddress.ip_address(host)
            return False
        except ValueError:
            pass
        return True
    except ValueError:
        return False


def _sensitive_fields(value):
    """Conservative refusal of embedded credentials; no secret value is logged."""
    if isinstance(value, dict):
        for key, item in value.items():
            if key.lower().replace("_", "").replace("-", "") in SENSITIVE:
                return True
            if _sensitive_fields(item):
                return True
    elif isinstance(value, list):
        return any(_sensitive_fields(item) for item in value)
    return False


def inspect_card(card):
    """Return profile errors; never assert remote endpoint reachability or A2A compliance."""
    errors = []
    if not isinstance(card, dict):
        return ["card must be an object"]
    if LEGACY.intersection(card):
        errors.append("legacy top-level A2A fields not accepted by this v1.0 profile")
    if _sensitive_fields(card):
        errors.append("possible embedded credential field")
    for field in ("name", "description", "version"):
        if not _text(card.get(field), 1024 if field == "description" else 120):
            errors.append("invalid " + field)
    if not _str_list(card.get("defaultInputModes"), 16):
        errors.append("invalid defaultInputModes")
    if not _str_list(card.get("defaultOutputModes"), 16):
        errors.append("invalid defaultOutputModes")
    capabilities = card.get("capabilities")
    if not isinstance(capabilities, dict):
        errors.append("invalid capabilities")
    else:
        for field in ("streaming", "pushNotifications", "extendedAgentCard"):
            if field in capabilities and type(capabilities[field]) is not bool:
                errors.append("invalid capability flag " + field)
    interfaces = card.get("supportedInterfaces")
    if not isinstance(interfaces, list) or not 1 <= len(interfaces) <= MAX_INTERFACES:
        errors.append("supportedInterfaces must contain 1..8 entries")
    else:
        seen = set()
        for i, item in enumerate(interfaces):
            if not isinstance(item, dict):
                errors.append(f"interface {i}: expected object")
                continue
            if not _public_https(item.get("url")):
                errors.append(f"interface {i}: unsafe or invalid public HTTPS URL")
            if item.get("protocolBinding") not in BINDINGS:
                errors.append(f"interface {i}: unsupported binding for this profile")
            if item.get("protocolVersion") != "1.0":
                errors.append(f"interface {i}: protocolVersion must equal 1.0")
            signature = (item.get("url"), item.get("protocolBinding"))
            if not all(isinstance(v, str) for v in signature):
                continue
            if signature in seen:
                errors.append(f"interface {i}: duplicate")
            seen.add(signature)
    skills = card.get("skills")
    if not isinstance(skills, list) or not 1 <= len(skills) <= MAX_SKILLS:
        errors.append("skills must contain 1..32 entries")
    else:
        ids = set()
        for i, item in enumerate(skills):
            if not isinstance(item, dict):
                errors.append(f"skill {i}: expected object")
                continue
            if not all(_text(item.get(k), 512 if k == "description" else 120)
                       for k in ("id", "name", "description")):
                errors.append(f"skill {i}: invalid identifying fields")
            if not _str_list(item.get("tags"), 32):
                errors.append(f"skill {i}: invalid tags")
            identity = item.get("id")
            if isinstance(identity, str):
                if identity in ids:
                    errors.append(f"skill {i}: duplicate id")
                ids.add(identity)
    schemes = card.get("securitySchemes", {})
    requirements = card.get("securityRequirements", [])
    if not isinstance(schemes, dict) or not isinstance(requirements, list):
        errors.append("invalid security metadata")
    else:
        if len(requirements) > 16:
            errors.append("too many security requirements")
        for i, req in enumerate(requirements):
            if not isinstance(req, dict) or not all(
                    isinstance(k, str) and k in schemes and isinstance(v, list)
                    and all(isinstance(x, str) for x in v)
                    for k, v in req.items()):
                errors.append(f"securityRequirements {i}: invalid scheme reference")
    return errors


def main(argv=None):
    args = sys.argv[1:] if argv is None else argv
    if len(args) != 1 or args[0].startswith("-"):
        print("usage: python3 -m agent_web.card_inspector LOCAL_CARD.json", file=sys.stderr)
        return 2
    try:
        with Path(args[0]).open("rb") as stream:
            raw = stream.read(MAX_CARD_BYTES + 1)
        problems = inspect_card(parse_bytes(raw))
    except (CardError, OSError) as exc:
        problems = [str(exc) if isinstance(exc, CardError) else "cannot read local file"]
    if problems:
        for item in problems:
            print("REJECTED: " + item, file=sys.stderr)
        return 1
    print("PROFILE_SHAPE_OK_UNVERIFIED: offline only; interfaces, skills, authority and publication NOT verified")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
