import json
import tempfile
import unittest
from argparse import Namespace
from pathlib import Path
from urllib.parse import urljoin

from devsecops_report import (
    CONTROLS,
    generate,
    initialize,
    public_build_url,
    record,
    record_check_report,
)


class DevSecOpsReportTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / "THREAT-MODEL.md").write_text("STRIDE review", encoding="utf-8")
        self.reports = self.root / "reports"
        self.results = self.reports / "devsecops-results.json"
        self.report = self.reports / "devsecops-report.html"

    def tearDown(self):
        self.temporary_directory.cleanup()

    def assert_report_link_resolves(self, document, artifact):
        filename = Path(artifact).name
        self.assertIn(f'href="{filename}"', document)
        self.assertTrue((self.reports / filename).is_file())

    def test_report_includes_status_and_safe_artifact_links(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "maven-tests.xml").write_text(
            '<testsuite tests="1" failures="0" errors="0" skipped="0"/>',
            encoding="utf-8",
        )
        record(Namespace(
            id="maven-tests",
            status="passed",
            summary="<script>alert('x')</script>",
            command="mvn test",
            artifact=["reports/maven-tests.xml"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("Réussi", document)
        self.assertIn("&lt;script&gt;", document)
        self.assertNotIn("<script>alert", document)
        self.assertNotIn("THREAT-MODEL.md", document)
        self.assert_report_link_resolves(document, "reports/maven-tests.xml")
        self.assertIn("Plan d'action", document)
        self.assertIn("Findings — SonarQube, Trivy SCA/IaC/images et OWASP ZAP", document)
        self.assertIn('<link rel="stylesheet" href="devsecops-report.css">', document)
        self.assertNotIn("<style>", document)
        self.assertNotIn("<script>", document)
        self.assertNotIn("style=", document)
        stylesheet = self.report.with_suffix(".css").read_text(encoding="utf-8")
        self.assertIn(".dashboard-layout", stylesheet)
        self.assertIn("min-width:820px", stylesheet)
        self.assertIn("width:19%", stylesheet)
        self.assertIn(".report-link", stylesheet)
        self.assertIn("text-decoration:underline", stylesheet)
        self.assertIn("min-height:38px", stylesheet)
        self.assertIn(".width-100", stylesheet)

    def test_unknown_status_is_rejected(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        with self.assertRaises(SystemExit):
            record(Namespace(
                id="maven-tests",
                status="invalid",
                summary="invalid",
                command="",
                artifact=[],
                output="",
                results=self.results,
            ))

    def test_dashboard_contains_only_configured_controls(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        data = json.loads(self.results.read_text(encoding="utf-8"))
        data["results"].extend([
            {
                "id": "ide-plugins",
                "phase": "Pré-commit",
                "tool": "Plugins IDE",
                "status": "not_run",
                "summary": "Non exécuté",
            },
            {
                "id": "cloud-configuration",
                "phase": "Acceptation",
                "tool": "Gestion de configuration cloud",
                "status": "not_run",
                "summary": "Non exécuté",
            },
        ])
        self.results.write_text(json.dumps(data), encoding="utf-8")
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertNotIn("Plugins IDE", document)
        self.assertNotIn("Gestion de configuration cloud", document)
        self.assertNotIn("Analyse propre à l&#x27;éditeur", document)
        self.assertNotIn("environnement cloud non configuré", document)
        self.assertIn("contrôles configurés dans le laboratoire", document)
        filtered_data = json.loads(self.results.read_text(encoding="utf-8"))
        included_ids = {item["id"] for item in filtered_data["results"]}
        self.assertNotIn("ide-plugins", included_ids)
        self.assertNotIn("cloud-configuration", included_ids)
        self.assertEqual(len(included_ids), len(CONTROLS))

    def test_dashboard_shows_tool_objective_and_report_metrics(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="maven-tests",
            status="passed",
            summary="Les tests automatisés Maven sont terminés.",
            command="mvn -B test jacoco:report",
            artifact=["reports/maven-tests.xml"],
            output="",
            results=self.results,
        ))
        (self.reports / "maven-tests.xml").write_text(
            '<testsuite name="BackendTest" tests="5" failures="0" errors="0" skipped="1"/>',
            encoding="utf-8",
        )
        (self.reports / "trivy-backend.json").write_text(
            '{"ArtifactName":"backend","Results":[{"Vulnerabilities":['
            '{"Severity":"HIGH","VulnerabilityID":"CVE-TEST-2"},'
            '{"Severity":"MEDIUM","VulnerabilityID":"CVE-TEST-3"}]}]}',
            encoding="utf-8",
        )
        record(Namespace(
            id="trivy",
            status="passed",
            summary="Le scan s’est terminé; un finding HIGH bloque la règle de sécurité.",
            command="trivy image backend",
            artifact=["reports/trivy-backend.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("Objectif :", document)
        self.assertIn("5 test(s), 0 échec(s), 0 erreur(s), 1 ignoré(s).", document)
        self.assertIn("trivy-backend.json : HIGH : 1, MEDIUM : 1.", document)
        self.assertIn("Le scan s’est terminé; un finding HIGH bloque la règle de sécurité.", document)
        results = json.loads(self.results.read_text(encoding="utf-8"))["results"]
        trivy_result = next(item for item in results if item["id"] == "trivy")
        self.assertEqual(trivy_result["status"], "passed")
        self.assert_report_link_resolves(document, "reports/maven-tests.xml")
        self.assert_report_link_resolves(document, "reports/trivy-backend.json")
        self.assertIn('class="report-link"', document)
        self.assertNotIn('target="_blank"', document)
        self.assertIn(">trivy-backend.json</a>", document)

    def test_unexecuted_stage_explains_where_to_find_its_blocker(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("Aucun résultat n&#x27;a été enregistré pour ce stage", document)
        self.assertIn("Consultez la première étape en échec dans Jenkins", document)

    def test_passed_control_without_a_valid_artifact_is_blocked(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="trivy",
            status="passed",
            summary="Image scan completed.",
            command="trivy image",
            artifact=["reports/trivy-backend.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        results = json.loads(self.results.read_text(encoding="utf-8"))["results"]
        trivy = next(item for item in results if item["id"] == "trivy")
        self.assertEqual(trivy["status"], "blocked")
        self.assertIn("Rapport attendu absent", document)

    def test_local_regeneration_does_not_reuse_a_historic_jenkins_build(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "trivy-backend.json").write_text(
            '{"Results":[]}', encoding="utf-8"
        )
        record(Namespace(
            id="trivy",
            status="passed",
            summary="Historical scan completed.",
            command="trivy image",
            artifact=["reports/trivy-backend.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(
            results=self.results,
            output=self.report,
            build_number="47",
            build_result="SUCCESS",
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        data = json.loads(self.results.read_text(encoding="utf-8"))
        trivy = next(item for item in data["results"] if item["id"] == "trivy")
        self.assertEqual(trivy["status"], "not_run")
        self.assertEqual(trivy["artifact"], "")
        self.assertNotIn("SUCCESS", document)
        self.assertIn("résultat Jenkins #47 est historique", document)
        self.assertIn("Aucune nouvelle analyse exécutée", document)

    def test_trivy_failure_displays_diagnostic_and_redacts_secrets(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "trivy-scan.log").write_text(
            "2026-10-04T12:00:00Z FATAL Fatal error failed to download DB token=private-value\n",
            encoding="utf-8",
        )
        record(Namespace(
            id="trivy",
            status="failed",
            summary="Le scan image a échoué.",
            command="trivy image backend",
            artifact=["reports/trivy-scan.log"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("FATAL Fatal error failed to download DB", document)
        self.assertIn("token=[redacted]", document)
        self.assertNotIn("private-value", document)
        self.assertIn("trivy-scan.log", document)

    def test_dashboard_ignores_stale_fixture_reports(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "trivy-fixture-sca.json").write_text(
            '{"Results":[{"Target":"retired-fixture","Vulnerabilities":['
            '{"VulnerabilityID":"OLD-FIXTURE-FINDING","Severity":"HIGH"}]}]}',
            encoding="utf-8",
        )
        (self.reports / "trivy-fixture-iac.json").write_text(
            '{"Results":[{"Target":"retired-fixture","Misconfigurations":['
            '{"ID":"OLD-FIXTURE-IAC","Severity":"MEDIUM"}]}]}',
            encoding="utf-8",
        )
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertNotIn("OLD-FIXTURE-FINDING", document)
        self.assertNotIn("OLD-FIXTURE-IAC", document)
        self.assertNotIn("trivy-fixture", document)
        self.assertNotIn("security-fixture", document)

    def test_check_report_records_each_control_and_artifact(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        checks_path = self.reports / "runtime-checks.json"
        checks_path.write_text(
            json.dumps({
                "checks": [
                    {"id": "infrastructure-tests", "status": "passed", "summary": "All services healthy."},
                    {"id": "server-hardening", "status": "failed", "summary": "Backend is running as root."},
                ]
            }),
            encoding="utf-8",
        )

        record_check_report(Namespace(
            report=checks_path,
            id=["infrastructure-tests", "server-hardening"],
            command="docker compose inspect",
            results=self.results,
        ))

        results = json.loads(self.results.read_text(encoding="utf-8"))["results"]
        by_id = {item["id"]: item for item in results}
        self.assertEqual(by_id["infrastructure-tests"]["status"], "passed")
        self.assertEqual(by_id["server-hardening"]["status"], "failed")
        self.assertEqual(by_id["server-hardening"]["artifact"], "reports/runtime-checks.json")

    def test_trivy_findings_are_listed_for_triage(self):
        self.reports.mkdir()
        (self.reports / "trivy-backend.json").write_text(
            '{"ArtifactName":"backend","Results":[{"Vulnerabilities":['
            '{"Severity":"HIGH","VulnerabilityID":"CVE-TEST-1","PkgName":"jackson-core",'
            '"InstalledVersion":"2.21.6","FixedVersion":"2.21.7"}]}]}',
            encoding="utf-8",
        )
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="trivy",
            status="passed",
            summary="Image scan completed.",
            command="trivy image",
            artifact=["reports/trivy-backend.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("CVE-TEST-1", document)
        self.assertIn("2.21.7", document)
        self.assertIn("trivy-backend.json", document)

    def test_trivy_sca_and_iac_findings_are_listed(self):
        self.reports.mkdir()
        (self.reports / "trivy-sca.json").write_text(
            '{"ArtifactName":"backend","Results":[{"Target":"pom.xml","Vulnerabilities":['
            '{"Severity":"HIGH","VulnerabilityID":"CVE-SCA-1","PkgName":"example-lib",'
            '"InstalledVersion":"1.0","FixedVersion":"1.1"}]}]}',
            encoding="utf-8",
        )
        (self.reports / "trivy-iac.json").write_text(
            '{"Results":[{"Target":"docker-compose.yml","Misconfigurations":['
            '{"ID":"AVD-IAC-1","Severity":"HIGH","Title":"Container configuration issue",'
            '"Message":"A hardened setting is missing.",'
            '"CauseMetadata":{"StartLine":12}}]}]}',
            encoding="utf-8",
        )
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="sca",
            status="passed",
            summary="SCA completed.",
            command="trivy image",
            artifact=["reports/trivy-sca.json"],
            output="",
            results=self.results,
        ))
        record(Namespace(
            id="iac-analysis",
            status="passed",
            summary="IaC completed.",
            command="trivy config",
            artifact=["reports/trivy-iac.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("CVE-SCA-1", document)
        self.assertIn("Trivy SCA", document)
        self.assertIn("AVD-IAC-1", document)
        self.assertIn("Trivy IaC", document)

    def test_sonarqube_issues_and_hotspots_are_listed_as_scan_findings(self):
        self.reports.mkdir()
        (self.reports / "sonarqube-issues.json").write_text(
            '{"issues":[{"key":"issue-1","rule":"java:S2077","severity":"MAJOR",'
            '"component":"devops-catalog:src/main/java/com/example/devops/ProductRepository.java",'
            '"line":12,"message":"Review this dynamically formatted SQL query."},'
            '{"key":"test-only-issue","rule":"java:S3649","severity":"CRITICAL",'
            '"component":"devops-catalog:src/test/java/ProductRepositoryTest.java",'
            '"line":15,"message":"Test-only Sonar finding."}]}',
            encoding="utf-8",
        )
        (self.reports / "sonarqube-hotspots.json").write_text(
            '{"hotspots":[{"key":"hotspot-1","vulnerabilityProbability":"HIGH",'
            '"component":"devops-catalog:src/main/java/com/example/devops/ProductRepository.java",'
            '"line":12,"message":"Make sure using this SQL query is safe here.",'
            '"status":"TO_REVIEW"}]}',
            encoding="utf-8",
        )
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="sonarqube",
            status="passed",
            summary="SonarQube completed.",
            command="sonar",
            artifact=["reports/sonarqube-issues.json", "reports/sonarqube-hotspots.json"],
            output="",
            results=self.results,
        ))
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("issue-1", document)
        self.assertIn("SonarQube SAST", document)
        self.assertIn("SonarQube hotspot", document)
        self.assertIn("hotspot-1", document)
        self.assertIn("1 issue(s) SonarQube retournée(s).", document)
        self.assertNotIn("test-only-issue", document)
        self.assertNotIn("Test-only Sonar finding", document)
        self.assert_report_link_resolves(document, "reports/sonarqube-issues.json")
        self.assert_report_link_resolves(document, "reports/sonarqube-hotspots.json")

    def test_global_dashboard_includes_nonblocking_zap_findings_and_all_phases(self):
        self.reports.mkdir()
        (self.reports / "zap-report.json").write_text(
            '{"site":[{"alerts":['
            '{"pluginid":"10021","alert":"X-Content-Type-Options Header Missing",'
            '"riskcode":"1","solution":"<p>Set nosniff.</p>",'
            '"instances":[{"uri":"http://backend:8080/api/products"}]},'
            '{"pluginid":"10049","alert":"Storable and Cacheable Content",'
            '"riskcode":"0","solution":"<p>Review cache headers.</p>",'
            '"instances":[{"uri":"http://backend:8080/api/products"}]}]}]}',
            encoding="utf-8",
        )
        initialize(Namespace(project_root=self.root, results=self.results))
        record(Namespace(
            id="zap",
            status="passed",
            summary="ZAP completed with non-blocking warnings.",
            command="zap-baseline.py -I",
            artifact=["reports/zap-report.html", "reports/zap-report.json"],
            output="",
            results=self.results,
        ))
        (self.reports / "zap-report.html").write_text("<html/>", encoding="utf-8")
        generate(Namespace(results=self.results, output=self.report))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("Vue globale des cinq phases DevSecOps", document)
        self.assertIn("phase-overview", document)
        self.assertIn("Production", document)
        self.assertIn("Opérations", document)
        self.assertIn("ZAP-10021", document)
        self.assertIn("ZAP-10049", document)
        self.assertIn("data-severity=\"INFO\"", document)
        self.assertIn("ne bloquent pas le pipeline", document)
        self.assertIn("menu-links", document)
        self.assertIn("Set nosniff.", document)
        self.assertIn("Recommandations extraites des constats présents", document)
        self.assert_report_link_resolves(document, "reports/zap-report.html")
        self.assert_report_link_resolves(document, "reports/zap-report.json")
        self.assertIn(">zap-report.html</a>", document)
        self.assertIn(">zap-report.json</a>", document)
        self.assertNotIn("report-views/", document)
        self.assertNotIn("SIM-DEMO-", document)
        self.assertNotIn("Mode simulation", document)
        self.assertNotIn("Score indicatif", document)
        self.assertNotIn("simulation", document.lower())
        self.assertNotIn("SIM-DEMO-", self.results.read_text(encoding="utf-8"))

    def test_jenkins_build_metadata_is_shown_and_persisted(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        generate(Namespace(
            results=self.results,
            output=self.report,
            build_number="42",
            build_url="http://jenkins/job/devops-catalog/42/",
            build_result="SUCCESS",
        ))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn("Ouvrir le build Jenkins #42", document)
        self.assertIn('<a href="../">Ouvrir le build Jenkins #42</a>', document)
        self.assertIn("SUCCESS", document)
        self.assertEqual(
            json.loads(self.results.read_text(encoding="utf-8"))["pipeline"]["build_number"],
            "42",
        )

    def test_jenkins_report_links_resolve_to_current_build_artifacts(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "zap-report.json").write_text(
            '{"site":[{"alerts":[{"pluginid":"10021","alert":"Header issue","riskcode":"1"}]}]}',
            encoding="utf-8",
        )
        (self.reports / "zap-report.html").write_text("<html/>", encoding="utf-8")
        record(Namespace(
            id="zap",
            status="passed",
            summary="ZAP scan completed.",
            command="zap-baseline.py",
            artifact=["reports/zap-report.html", "reports/zap-report.json"],
            output="",
            results=self.results,
        ))
        build_url = "http://jenkins-internal:8080/jenkins/job/devops-catalog/52/"
        generate(Namespace(
            results=self.results,
            output=self.report,
            build_number="52",
            build_url=build_url,
            build_result="SUCCESS",
        ))

        document = self.report.read_text(encoding="utf-8")
        self.assertIn(
            'href="../artifact/reports/zap-report.html"',
            document,
        )
        self.assertIn(
            'href="../artifact/reports/zap-report.json"',
            document,
        )
        dashboard_url = "https://ci.example/jenkins/job/devops-catalog/52/Dashboard_20DevSecOps/devsecops-report.html"
        self.assertEqual(
            urljoin(dashboard_url, "../artifact/reports/zap-report.html"),
            "https://ci.example/jenkins/job/devops-catalog/52/artifact/reports/zap-report.html",
        )
        self.assertNotIn("jenkins-internal:8080", document)
        self.assertNotIn('target="_blank"', document)
        self.assertNotIn("report-views/", document)

    def test_jenkins_artifact_urls_preserve_nested_job_and_path(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        (self.reports / "scan output.json").write_text('{"Results":[]}', encoding="utf-8")
        record(Namespace(
            id="trivy",
            status="passed",
            summary="Trivy scan completed.",
            command="trivy image",
            artifact=["reports/scan output.json"],
            output="",
            results=self.results,
        ))
        build_url = "https://jenkins.example/jenkins/job/security/job/catalog/52/"
        generate(Namespace(
            results=self.results,
            output=self.report,
            build_number="52",
            build_url=build_url,
            build_result="SUCCESS",
        ))
        document = self.report.read_text(encoding="utf-8")
        self.assertIn(
            'href="../artifact/reports/scan%20output.json"',
            document,
        )

    def test_executed_tools_with_text_reports_show_build_artifact_links(self):
        initialize(Namespace(project_root=self.root, results=self.results))
        artifacts = {
            "gitleaks": ("reports/gitleaks-summary.txt", "passed"),
            "smoke-tests": ("reports/smoke-tests.log", "passed"),
            "fault-injection": ("reports/fault-injection.log", "failed"),
        }
        for control_id, (artifact, status) in artifacts.items():
            (self.root / artifact).write_text(f"Result for {control_id}\n", encoding="utf-8")
            record(Namespace(
                id=control_id,
                status=status,
                summary=f"{control_id} completed.",
                command=control_id,
                artifact=[artifact],
                output="",
                results=self.results,
            ))
        build_url = "http://jenkins-internal:8080/job/devops-catalog/53/"
        generate(Namespace(
            results=self.results,
            output=self.report,
            build_number="53",
            build_url=build_url,
            build_result="FAILURE",
        ))
        document = self.report.read_text(encoding="utf-8")
        for artifact, _ in artifacts.values():
            expected = f'href="../artifact/{artifact}"'
            self.assertIn(expected, document)

    def test_public_build_url_uses_browser_reachable_jenkins_base(self):
        self.assertEqual(
            public_build_url(
                "http://localhost:8080/job/devops-catalog/42/",
                "http://localhost:8083/",
                "http://localhost:8080/",
            ),
            "http://localhost:8083/job/devops-catalog/42/",
        )
        self.assertEqual(
            public_build_url(
                "http://jenkins:8080/job/devops-catalog/42/",
                "http://localhost:8083/",
                "http://jenkins:8080/",
            ),
            "http://localhost:8083/job/devops-catalog/42/",
        )
        self.assertEqual(
            public_build_url(
                "http://jenkins:8080/jenkins/job/folder/job/catalog/42/",
                "https://ci.example/jenkins/",
                "http://jenkins:8080/jenkins/",
            ),
            "https://ci.example/jenkins/job/folder/job/catalog/42/",
        )


if __name__ == "__main__":
    unittest.main()
