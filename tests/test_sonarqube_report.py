import io
import json
import unittest
from unittest.mock import patch
from urllib.parse import parse_qs, urlsplit
from urllib.request import Request

from sonarqube_report import fetch_all


class SonarQubeReportTests(unittest.TestCase):
    @patch("sonarqube_report.urlopen")
    def test_fetch_all_collects_pages_and_uses_authorization_header(self, urlopen):
        pages = [
            {"paging": {"total": 2}, "issues": [{"key": "issue-1"}]},
            {"paging": {"total": 2}, "issues": [{"key": "issue-2"}]},
        ]
        urlopen.side_effect = [io.BytesIO(json.dumps(page).encode()) for page in pages]

        report = fetch_all(
            "http://sonarqube:9000",
            "issues/search",
            "issues",
            {"componentKeys": "devops-catalog", "types": "VULNERABILITY"},
            "Basic test-credential",
        )

        self.assertEqual([item["key"] for item in report["issues"]], ["issue-1", "issue-2"])
        self.assertEqual(report["paging"]["total"], 2)
        self.assertEqual(urlopen.call_count, 2)
        first_request = urlopen.call_args_list[0].args[0]
        self.assertIsInstance(first_request, Request)
        self.assertEqual(first_request.get_header("Authorization"), "Basic test-credential")
        self.assertEqual(parse_qs(urlsplit(first_request.full_url).query)["p"], ["1"])
        second_request = urlopen.call_args_list[1].args[0]
        self.assertEqual(parse_qs(urlsplit(second_request.full_url).query)["p"], ["2"])


if __name__ == "__main__":
    unittest.main()
