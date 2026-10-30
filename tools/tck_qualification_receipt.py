"""Classify pinned A2A TCK artifacts without ever converting failures into a pass.

This helper does NOT execute TCK, validate its provenance, or certify A2A
conformance. The manual workflow verifies upstream source identity separately.
"""
import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET

REQUIRED = ("compatibility.json", "compatibility.html", "tck_report.html", "junitreport.xml")
PROVISIONAL = "MUST_SUITE_PROVISIONAL_PASS_DIRECTOR_REVIEW_REQUIRED"
HOLD = "MUST_SUITE_FAIL_OR_EVIDENCE_HOLD"


def summarize(reports_dir, command_returncode):
    """Return a narrow, audit-friendly assessment. No implicit skipped-test success."""
    root = Path(reports_dir)
    missing = sorted(name for name in REQUIRED if not (root / name).is_file())
    result = {
        "qualificationScope": "pinned-official-A2A-TCK-JSONRPC-MUST-only",
        "commandReturnCode": command_returncode,
        "requiredReportFilesPresent": not missing,
        "missingReports": missing,
        "tests": 0,
        "failures": 0,
        "errors": 0,
        "skipped": 0,
        "reportParseError": False,
        "verdict": HOLD,
        "fullA2AConformanceCertified": False,
        "deploymentAuthorized": False,
    }
    junit = root / "junitreport.xml"
    if junit.is_file():
        try:
            tree = ET.parse(junit)
            cases = tree.findall(".//testcase")
            result["tests"] = len(cases)
            result["failures"] = sum(bool(c.findall("failure")) for c in cases)
            result["errors"] = sum(bool(c.findall("error")) for c in cases)
            result["skipped"] = sum(bool(c.findall("skipped")) for c in cases)
        except (ET.ParseError, OSError, ValueError):
            result["reportParseError"] = True
    if (type(command_returncode) is int and command_returncode == 0 and not missing
            and not result["reportParseError"]
            and result["tests"] > 0 and result["tests"] > result["skipped"]
            and result["failures"] == 0 and result["errors"] == 0):
        result["verdict"] = PROVISIONAL
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description="TCK evidence classification; never a conformance certificate")
    parser.add_argument("--reports", type=Path, required=True)
    parser.add_argument("--return-code", type=int, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    result = summarize(args.reports, args.return_code)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(result, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    print(result["verdict"])
    return 0  # Report creation status only; manual workflow enforces verdict separately.


if __name__ == "__main__":
    raise SystemExit(main())
