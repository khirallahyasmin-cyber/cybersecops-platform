import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from devsecops_checks import inspect_compose_config, inspect_monitoring, inspect_runtime


class DevSecOpsCheckTests(unittest.TestCase):
    def setUp(self):
        self.temporary_directory = tempfile.TemporaryDirectory()
        self.root = Path(self.temporary_directory.name)
        (self.root / ".gitignore").write_text(".env\n**/target/\n", encoding="utf-8")
        (self.root / "Jenkinsfile").write_text(
            "tar --exclude=.env -cf source.tar .\nwithCredentials([])\n",
            encoding="utf-8",
        )

    def tearDown(self):
        self.temporary_directory.cleanup()

    def test_compose_configuration_reports_local_safety_controls(self):
        config = {
            "services": {
                "mysql": {"restart": "unless-stopped"},
                "backend": {"restart": "unless-stopped", "ports": [{"host_ip": "127.0.0.1"}]},
                "frontend": {"restart": "unless-stopped", "ports": [{"host_ip": "127.0.0.1"}]},
            }
        }

        results = inspect_compose_config(config, self.root)

        self.assertEqual(
            {item["id"]: item["status"] for item in results},
            {
                "acceptance-iac": "passed",
                "infrastructure-compliance": "passed",
                "configuration-safety": "passed",
                "secrets-management": "passed",
            },
        )

    def test_compose_configuration_fails_on_privileged_or_host_network(self):
        config = {
            "services": {
                "mysql": {"restart": "unless-stopped"},
                "backend": {
                    "restart": "unless-stopped",
                    "privileged": True,
                    "network_mode": "host",
                    "ports": [{"host_ip": "127.0.0.1"}],
                },
                "frontend": {"restart": "unless-stopped", "ports": [{"host_ip": "127.0.0.1"}]},
            }
        }

        results = inspect_compose_config(config, self.root)
        statuses = {item["id"]: item["status"] for item in results}

        self.assertEqual(statuses["acceptance-iac"], "passed")
        self.assertEqual(statuses["infrastructure-compliance"], "failed")

    def test_compose_configuration_fails_when_demo_app_ports_are_public(self):
        config = {
            "services": {
                "mysql": {"restart": "unless-stopped"},
                "backend": {"restart": "unless-stopped", "ports": [{"host_ip": "0.0.0.0"}]},
                "frontend": {"restart": "unless-stopped", "ports": [{"host_ip": "0.0.0.0"}]},
            }
        }

        results = inspect_compose_config(config, self.root)
        statuses = {item["id"]: item["status"] for item in results}

        self.assertEqual(statuses["acceptance-iac"], "passed")
        self.assertEqual(statuses["infrastructure-compliance"], "failed")

    def test_runtime_checks_health_and_non_root_backend(self):
        def container(user="", health=None, privileged=False):
            state = {"Status": "running"}
            if health:
                state["Health"] = {"Status": health}
            return {
                "State": state,
                "Config": {"User": user},
                "HostConfig": {"Privileged": privileged},
            }

        results = inspect_runtime({
            "mysql": container(health="healthy"),
            "backend": container(user="app", health="healthy"),
            "frontend": container(),
        })

        self.assertEqual(
            {item["id"]: item["status"] for item in results},
            {"infrastructure-tests": "passed", "server-hardening": "passed"},
        )

    def test_runtime_checks_fail_when_backend_is_root_or_unhealthy(self):
        def container(user="", health=None):
            state = {"Status": "running"}
            if health:
                state["Health"] = {"Status": health}
            return {"State": state, "Config": {"User": user}, "HostConfig": {}}

        results = inspect_runtime({
            "mysql": container(health="healthy"),
            "backend": container(user="root", health="unhealthy"),
            "frontend": container(),
        })

        self.assertEqual(
            {item["id"]: item["status"] for item in results},
            {"infrastructure-tests": "failed", "server-hardening": "failed"},
        )

    def test_monitoring_check_retries_until_grafana_is_ready(self):
        targets = {
            "data": {
                "activeTargets": [
                    {"health": "up", "labels": {"job": "devops-backend"}}
                ]
            }
        }
        with (
            patch("devsecops_checks.fetch_json") as fetch_json,
            patch("devsecops_checks.time.sleep") as sleep,
        ):
            fetch_json.side_effect = [
                (200, targets),
                RuntimeError("Grafana is starting"),
                (200, targets),
                (200, {"database": "ok"}),
            ]

            results = inspect_monitoring("http://prometheus", "http://grafana")

        self.assertEqual(results[0]["id"], "continuous-monitoring")
        self.assertEqual(results[0]["status"], "passed")
        sleep.assert_called_once_with(5)


if __name__ == "__main__":
    unittest.main()
