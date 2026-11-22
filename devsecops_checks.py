#!/usr/bin/env python3
"""Run lightweight configuration and runtime checks for the local DevSecOps lab."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import urlopen


def check(status: bool, control_id: str, summary: str) -> dict[str, str]:
    return {
        "id": control_id,
        "status": "passed" if status else "failed",
        "summary": summary,
    }


def inspect_compose_config(config: dict, project_root: Path) -> list[dict[str, str]]:
    services = config.get("services", {})
    required_services = {"mysql", "backend", "frontend"}
    has_services = required_services.issubset(services)
    results = [
        check(
            has_services,
            "acceptance-iac",
            "La configuration Compose résolue contient les services applicatifs requis."
            if has_services
            else "La configuration Compose ne contient pas tous les services mysql/backend/frontend.",
        )
    ]

    app_services = [services[name] for name in ("mysql", "backend", "frontend") if name in services]
    safe_networking = all(
        service.get("network_mode") != "host" and not service.get("privileged", False)
        for service in app_services
    )
    loopback_only = all(
        str(port.get("host_ip", port.get("HostIp", ""))) in {"127.0.0.1", "::1"}
        for name in ("backend", "frontend")
        for port in services.get(name, {}).get("ports", [])
    )
    mysql_unpublished = not services.get("mysql", {}).get("ports")
    restarts_configured = all(
        services[name].get("restart") in {"unless-stopped", "always"}
        for name in required_services
        if name in services
    )
    results.append(
        check(
            safe_networking and loopback_only and mysql_unpublished and restarts_configured,
            "infrastructure-compliance",
            "Compose vérifié : aucun conteneur applicatif privilégié, ports backend/frontend en loopback, "
            "MySQL non publié sur l'hôte et politiques de redémarrage présentes."
            if safe_networking and loopback_only and mysql_unpublished and restarts_configured
            else "Écart de configuration : vérifier les privilèges, le réseau, l'exposition MySQL et les politiques de redémarrage.",
        )
    )

    ignore_file = project_root / ".gitignore"
    pipeline_file = project_root / "Jenkinsfile"
    gitignore = ignore_file.read_text(encoding="utf-8") if ignore_file.is_file() else ""
    pipeline = pipeline_file.read_text(encoding="utf-8") if pipeline_file.is_file() else ""
    env_ignored = any(line.strip() == ".env" for line in gitignore.splitlines())
    source_archive_excludes_env = "--exclude=.env" in pipeline
    credentials_injected = "withCredentials" in pipeline
    safe_config = env_ignored and source_archive_excludes_env
    results.append(
        check(
            safe_config,
            "configuration-safety",
            "Le fichier .env est ignoré par Git et exclu de l'archive locale Jenkins."
            if safe_config
            else "Le fichier .env n'est pas protégé à la fois par Git et par l'archive Jenkins.",
        )
    )
    managed_credentials = safe_config and credentials_injected
    results.append(
        check(
            managed_credentials,
            "secrets-management",
            "Le .env est ignoré par Git et exclu de l'archive de sources; les credentials CI passent par withCredentials. Jenkins local a accès au montage du projet et doit rester de confiance; aucun coffre cloud n'est revendiqué."
            if managed_credentials
            else "Vérifier l'exclusion de .env et l'injection des credentials Jenkins; aucun coffre cloud n'est configuré.",
        )
    )
    return results


def inspect_runtime(containers: dict[str, dict]) -> list[dict[str, str]]:
    required = {"mysql", "backend", "frontend"}
    all_present = required.issubset(containers)
    running = all_present and all(
        containers[name].get("State", {}).get("Status") == "running"
        for name in required
    )
    healthy = running and all(
        containers[name].get("State", {}).get("Health", {}).get("Status") == "healthy"
        for name in ("mysql", "backend")
    )
    results = [
        check(
            healthy,
            "infrastructure-tests",
            "MySQL et backend sont healthy; frontend et les services applicatifs sont démarrés."
            if healthy
            else "Au moins un service applicatif est absent, arrêté ou en échec de healthcheck.",
        )
    ]

    backend = containers.get("backend", {})
    backend_user = str(backend.get("Config", {}).get("User", "")).strip().lower()
    backend_unprivileged = backend_user not in {"", "0", "root", "0:0", "root:root"}
    app_containers_unprivileged = all(
        not containers.get(name, {}).get("HostConfig", {}).get("Privileged", False)
        for name in required
        if name in containers
    )
    hardened = running and backend_unprivileged and app_containers_unprivileged
    results.append(
        check(
            hardened,
            "server-hardening",
            f"Backend exécuté sous l'identité non-root « {backend_user} » et aucun service applicatif n'est privilégié."
            if hardened
            else "Le backend doit fonctionner sous un utilisateur non-root et les conteneurs applicatifs ne doivent pas être privilégiés.",
        )
    )
    return results


def fetch_json(url: str) -> tuple[int, dict]:
    try:
        with urlopen(url, timeout=10) as response:
            payload = json.loads(response.read().decode("utf-8"))
            return response.status, payload
    except (HTTPError, URLError, TimeoutError, json.JSONDecodeError) as exc:
        raise RuntimeError(f"Échec de la vérification HTTP de {url}: {exc}") from exc


def inspect_monitoring(prometheus_url: str, grafana_url: str) -> list[dict[str, str]]:
    backend_up = False
    grafana_up = False
    last_error = "les services de supervision ne sont pas encore prêts."
    for attempt in range(12):
        try:
            status, payload = fetch_json(
                f"{prometheus_url.rstrip('/')}/api/v1/targets?state=active"
            )
            targets = payload.get("data", {}).get("activeTargets", [])
            backend_up = status == 200 and any(
                target.get("health") == "up"
                and target.get("labels", {}).get("job") == "devops-backend"
                for target in targets
            )
            grafana_status, grafana = fetch_json(f"{grafana_url.rstrip('/')}/api/health")
            grafana_up = grafana_status == 200 and grafana.get("database") == "ok"
            if backend_up and grafana_up:
                break
            last_error = "la cible backend Prometheus ou la base Grafana n'est pas prête."
        except RuntimeError as exc:
            last_error = str(exc)
        if attempt < 11:
            time.sleep(5)

    monitoring_up = backend_up and grafana_up
    return [
        check(
            monitoring_up,
            "continuous-monitoring",
            "Prometheus collecte la cible backend et l'API de santé Grafana répond."
            if monitoring_up
            else f"La supervision n'est pas prête après 12 tentatives : {last_error}",
        )
    ]


def inspect_security_smoke(api_url: str) -> list[dict[str, str]]:
    checks = []
    try:
        for path in ("/api/health", "/api/products"):
            with urlopen(f"{api_url.rstrip('/')}{path}", timeout=10) as response:
                healthy = response.status == 200
                has_nosniff = response.headers.get("X-Content-Type-Options", "").lower() == "nosniff"
                checks.append((path, healthy, has_nosniff))
    except (HTTPError, URLError, TimeoutError) as exc:
        raise RuntimeError(f"Échec du security smoke test: {exc}") from exc
    passed = len(checks) == 2 and all(ok and nosniff for _, ok, nosniff in checks)
    return [
        check(
            passed,
            "security-smoke-tests",
            "Les endpoints de santé et de produits répondent en HTTP 200 avec X-Content-Type-Options: nosniff."
            if passed
            else "Un endpoint applicatif ou l'en-tête X-Content-Type-Options: nosniff est absent.",
        )
    ]


def write_report(output: Path, results: list[dict[str, str]]) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps({"checks": results}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    config_parser = subparsers.add_parser("compose-config")
    config_parser.add_argument("--project-root", type=Path, required=True)
    config_parser.add_argument("--output", type=Path, required=True)

    runtime_parser = subparsers.add_parser("runtime")
    runtime_parser.add_argument("--project-name", required=True)
    runtime_parser.add_argument("--output", type=Path, required=True)

    monitoring_parser = subparsers.add_parser("monitoring")
    monitoring_parser.add_argument("--prometheus-url", default="http://prometheus:9090")
    monitoring_parser.add_argument("--grafana-url", default="http://grafana:3000")
    monitoring_parser.add_argument("--output", type=Path, required=True)

    smoke_parser = subparsers.add_parser("security-smoke")
    smoke_parser.add_argument("--api-url", default="http://backend:8080")
    smoke_parser.add_argument("--output", type=Path, required=True)

    args = parser.parse_args()
    try:
        if args.command == "compose-config":
            config = json.load(sys.stdin)
            results = inspect_compose_config(config, args.project_root.resolve())
        elif args.command == "runtime":
            containers = {}
            for service in ("mysql", "backend", "frontend"):
                ids = subprocess.run(
                    ["docker", "compose", "--project-name", args.project_name, "ps", "-q", service],
                    check=True,
                    capture_output=True,
                    text=True,
                ).stdout.split()
                if ids:
                    inspected = subprocess.run(
                        ["docker", "inspect", *ids],
                        check=True,
                        capture_output=True,
                        text=True,
                    )
                    container = json.loads(inspected.stdout)[0]
                    containers[service] = container
            results = inspect_runtime(containers)
        elif args.command == "monitoring":
            results = inspect_monitoring(args.prometheus_url, args.grafana_url)
        else:
            results = inspect_security_smoke(args.api_url)
    except (OSError, subprocess.CalledProcessError, json.JSONDecodeError, RuntimeError) as exc:
        write_report(args.output, [check(False, "check-execution", str(exc))])
        print(str(exc), file=sys.stderr)
        return 1

    write_report(args.output, results)
    for result in results:
        print(f"{result['status']}: {result['id']} — {result['summary']}")
    return 0 if all(result["status"] == "passed" for result in results) else 1


if __name__ == "__main__":
    raise SystemExit(main())
