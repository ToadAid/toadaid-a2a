"""P0B-C2A unit tests: only synthetic JUnit, never the official TCK."""
import tempfile
import unittest
from pathlib import Path

from tools.tck_qualification_receipt import HOLD, PROVISIONAL, REQUIRED, summarize


def reports(path, junit):
    for name in REQUIRED:
        (path / name).write_text(junit if name == "junitreport.xml" else "synthetic placeholder\n")


class ReceiptTests(unittest.TestCase):
    def test_absent_reports_cannot_pass(self):
        with tempfile.TemporaryDirectory() as d:
            r = summarize(d, 0)
            self.assertEqual(r["verdict"], HOLD)
            self.assertFalse(r["requiredReportFilesPresent"])

    def test_nonzero_exit_always_holds(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"/></testsuite>')
            r = summarize(d, 1)
            self.assertEqual(r["verdict"], HOLD)
            self.assertEqual(r["commandReturnCode"], 1)

    def test_failed_case_holds_despite_zero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"><failure/></testcase></testsuite>')
            r = summarize(d, 0)
            self.assertEqual(r["verdict"], HOLD)
            self.assertEqual(r["failures"], 1)

    def test_error_case_holds_despite_zero_exit(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"><error/></testcase></testsuite>')
            self.assertEqual(summarize(d, 0)["verdict"], HOLD)

    def test_skipped_only_holds(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"><skipped/></testcase></testsuite>')
            self.assertEqual(summarize(d, 0)["verdict"], HOLD)

    def test_empty_suite_holds(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite tests="0"/>')
            self.assertEqual(summarize(d, 0)["verdict"], HOLD)

    def test_malformed_junit_holds(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), 'not-xml')
            r = summarize(d, 0)
            self.assertEqual(r["verdict"], HOLD)
            self.assertTrue(r["reportParseError"])

    def test_missing_html_report_holds(self):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d)
            reports(path, '<testsuite><testcase name="a"/></testsuite>')
            (path / "compatibility.html").unlink()
            self.assertEqual(summarize(d, 0)["verdict"], HOLD)

    def test_synthetic_success_is_provisional_not_certification(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"/><testcase name="b"><skipped/></testcase></testsuite>')
            r = summarize(d, 0)
            self.assertEqual(r["verdict"], PROVISIONAL)
            self.assertEqual((r["tests"], r["skipped"]), (2, 1))
            self.assertFalse(r["fullA2AConformanceCertified"])
            self.assertFalse(r["deploymentAuthorized"])

    def test_type_bypass_does_not_pass(self):
        with tempfile.TemporaryDirectory() as d:
            reports(Path(d), '<testsuite><testcase name="a"/></testsuite>')
            self.assertEqual(summarize(d, False)["verdict"], HOLD)


if __name__ == "__main__":
    unittest.main()
