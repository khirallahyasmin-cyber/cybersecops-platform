#!/usr/bin/env python3
"""Build a single HTML dashboard from DevSecOps check results."""

from __future__ import annotations

import argparse
import html
import json
import os
import re
import xml.etree.ElementTree as ET
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote, urlsplit


STATUS_LABELS = {
    "passed": "Réussi",
    "failed": "Échec",
    "blocked": "Bloqué",
    "skipped": "Ignoré",
    "manual": "Revue documentaire",
    "not_run": "Non exécuté",
}

PHASES = ["Pré-commit", "Commit (CI)", "Acceptation", "Production", "Opérations"]

CONTROLS = [
    ("precommit", "Pré-commit", "Hooks pre-commit", "Format, YAML, conflits, clés privées et taille des fichiers."),
    ("gitleaks", "Pré-commit", "Gitleaks", "Recherche de secrets dans les fichiers suivis."),
    ("secure-coding", "Pré-commit", "Standards de codage sécurisé", "Règles de sécurité Java vérifiées par SonarQube dans le pipeline."),
    ("commitizen", "Commit (CI)", "Commitizen", "Validation du message au format Conventional Commits."),
    ("sonarqube", "Commit (CI)", "SonarQube (SAST)", "Analyse statique; nécessite le jeton SonarQube."),
    ("sca", "Commit (CI)", "Analyse SCA des dépendances", "Trivy analyse les composants Java intégrés dans l'image backend."),
    ("maven-tests", "Commit (CI)", "Tests unitaires et sécurité Maven", "Tests automatisés du backend."),
    ("iac-analysis", "Commit (CI)", "Analyse IaC", "Trivy analyse les Dockerfiles et la configuration Docker Compose."),
    ("dependency-management", "Commit (CI)", "Gestion des dépendances", "Maven Versions Plugin signale les mises à jour disponibles."),
    ("trivy", "Commit (CI)", "Trivy (sécurité des conteneurs)", "Vulnérabilités HIGH/CRITICAL corrigibles des images."),
    ("acceptance-iac", "Acceptation", "Contrôle IaC", "Résolution et validation de la configuration Docker Compose avant déploiement."),
    ("zap", "Acceptation", "Scan de sécurité — OWASP ZAP Baseline", "Scan passif de l'API déployée; les alertes WARN restent visibles sans bloquer le pipeline."),
    ("smoke-tests", "Acceptation", "Tests d'acceptation", "Vérification de santé de l'application et de l'API."),
    ("infrastructure-tests", "Acceptation", "Tests d'infrastructure", "Vérification des conteneurs applicatifs et de leurs healthchecks."),
    ("infrastructure-compliance", "Acceptation", "Conformité infrastructure", "Contrôle ciblé des privilèges, réseaux, volumes et redémarrages Compose."),
    ("security-smoke-tests", "Production", "Security smoke tests", "Vérification HTTP post-déploiement et en-tête anti-MIME-sniffing."),
    ("configuration-safety", "Production", "Contrôles de configuration", "Vérifie la syntaxe et les protections de configuration Compose/.env."),
    ("secrets-management", "Production", "Gestion des secrets", "Vérifie l'exclusion des secrets locaux et l'injection des credentials Jenkins."),
    ("server-hardening", "Production", "Durcissement serveur", "Vérifie l'exécution non-root du backend et l'absence de conteneur privilégié."),
    ("fault-injection", "Opérations", "Injection de pannes", "Redémarrage contrôlé du backend et vérification de la reprise."),
    ("continuous-scanning", "Opérations", "Scans continus", "Trivy exécute les scans de dépendances, IaC et images à chaque build Jenkins."),
    ("continuous-monitoring", "Opérations", "Supervision continue", "Vérifie que Prometheus collecte l'API et que Grafana répond."),
]
CONTROL_DESCRIPTIONS = {
    control_id: description
    for control_id, _, _, description in CONTROLS
}

REMEDIATIONS = {
    "trivy": "Les rapports Trivy donnent le paquet et la version corrigée. Mettre à jour les dépendances ou l’image, reconstruire les conteneurs, puis relancer le scan.",
    "sonarqube": "Vérifier le credential Jenkins « sonar-token », puis relancer le build du job devops-catalog.",
    "precommit": "Ouvrir le journal des hooks, corriger les fichiers signalés, puis relancer pre-commit.",
    "gitleaks": "Ne pas afficher ni recopier une valeur secrète. Révoquer/faire tourner le secret signalé, l’exclure de l’historique si nécessaire, puis relancer Gitleaks.",
    "commitizen": "Réécrire le message selon Conventional Commits (ex. fix: corriger la validation), puis relancer le contrôle.",
    "zap": "Examiner les alertes OWASP ZAP non bloquantes et corriger les en-têtes ou comportements signalés si le contexte le justifie.",
    "sca": "Examiner le rapport Trivy SCA, mettre à jour la dépendance corrigible, puis relancer l'analyse.",
    "iac-analysis": "Examiner la configuration Docker/IaC signalée, appliquer le correctif, puis relancer Trivy Config.",
    "dependency-management": "Examiner les mises à jour listées dans le rapport Maven Versions et appliquer celles qui sont compatibles après test.",
    "acceptance-iac": "Corriger la configuration Compose si un service requis est absent ou si la configuration ne peut pas être résolue.",
    "infrastructure-tests": "Examiner les états et healthchecks Docker Compose; rétablir les services avant de poursuivre.",
    "infrastructure-compliance": "Retirer le mode host ou les privilèges superflus, ne pas publier MySQL, et conserver une politique de redémarrage.",
    "security-smoke-tests": "Rétablir les endpoints API et ajouter X-Content-Type-Options: nosniff au backend.",
    "configuration-safety": "Ajouter .env à .gitignore et l'exclure de l'archive locale Jenkins.",
    "secrets-management": "Conserver les secrets d'exécution dans Jenkins Credentials; ne pas ajouter .env à Git ou aux archives.",
    "server-hardening": "Exécuter le backend sous un utilisateur non-root et éviter les conteneurs privilégiés.",
    "fault-injection": "Examiner le healthcheck et le journal backend après redémarrage; corriger la cause avant de relancer.",
    "continuous-monitoring": "Démarrer le profil monitoring et vérifier la cible backend dans Prometheus ainsi que l'API de santé Grafana.",
}

def now() -> str:
    return datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")


def public_build_url(build_url: str, public_base_url: str, jenkins_url: str) -> str:
    if not build_url or not public_base_url:
        return build_url
    build = urlsplit(build_url)
    public = urlsplit(public_base_url)
    if (
        build.scheme not in {"http", "https"}
        or not build.netloc
        or build.username
        or build.password
        or public.scheme not in {"http", "https"}
        or not public.netloc
        or public.username
        or public.password
    ):
        return build_url

    internal = urlsplit(jenkins_url) if jenkins_url else None
    build_path = build.path.rstrip("/")
    internal_path = internal.path.rstrip("/") if internal else ""
    if internal_path and (build_path == internal_path or build_path.startswith(f"{internal_path}/")):
        build_path = build_path[len(internal_path):]

    base_path = public.path.rstrip("/")
    combined_path = f"{base_path}/{build_path.lstrip('/')}" if build_path else base_path
    return build._replace(
        scheme=public.scheme,
        netloc=public.netloc,
        path=combined_path or "/",
    ).geturl().rstrip("/") + "/"


def load_results(path: Path) -> dict:
    if not path.exists():
        return {"schema_version": 1, "generated_at": now(), "results": []}
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Impossible de lire le fichier de résultats {path}: {exc}") from exc
    if not isinstance(data, dict) or not isinstance(data.get("results"), list):
        raise SystemExit(f"Format de résultats invalide dans {path}.")
    return data


def write_results(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def redact_sensitive_text(text: str) -> str:
    text = re.sub(
        r"(?i)\b(authorization|token|password|secret|api[_-]?key|access[_-]?key)\b(\s*[:=]\s*)[^\s,;]+",
        r"\1\2[redacted]",
        text,
    )
    return re.sub(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]+", r"\1 [redacted]", text)


def initialize(args: argparse.Namespace) -> None:
    results = []
    for control_id, phase, tool, description in CONTROLS:
        results.append({
            "id": control_id,
            "phase": phase,
            "tool": tool,
            "status": "not_run",
            "summary": f"Non exécuté : {description}",
            "command": "",
            "artifact": "",
            "output": "",
            "checked_at": now(),
        })
    write_results(args.results, {"schema_version": 1, "generated_at": now(), "results": results})


def record(args: argparse.Namespace) -> None:
    if args.status not in STATUS_LABELS:
        raise SystemExit(f"Statut invalide: {args.status}")
    data = load_results(args.results)
    result = next((item for item in data["results"] if item.get("id") == args.id), None)
    if result is None:
        definition = next((item for item in CONTROLS if item[0] == args.id), None)
        if definition is None:
            raise SystemExit(f"Contrôle inconnu: {args.id}")
        _, phase, tool, _ = definition
        result = {"id": args.id, "phase": phase, "tool": tool}
        data["results"].append(result)
    artifacts = args.artifact if isinstance(args.artifact, list) else [args.artifact]
    artifacts = [value for value in artifacts if value]
    result.update({
        "status": args.status,
        "summary": args.summary,
        "command": args.command,
        "artifact": artifacts[0] if artifacts else "",
        "artifacts": artifacts,
        "output": args.output,
        "checked_at": now(),
    })
    data["generated_at"] = now()
    write_results(args.results, data)


def artifact_problem(project_root: Path, artifact: str) -> str:
    target = Path(artifact)
    if target.is_absolute() or ".." in target.parts:
        return f"Chemin de rapport non sûr : {artifact}."
    resolved = (project_root / target).resolve()
    if not resolved.is_relative_to(project_root.resolve()) or not resolved.is_file():
        return f"Rapport attendu absent : {artifact}."
    if resolved.stat().st_size == 0:
        return f"Rapport attendu vide : {artifact}."

    if resolved.suffix.lower() == ".json":
        try:
            payload = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, UnicodeDecodeError, json.JSONDecodeError):
            return f"Rapport JSON illisible : {artifact}."
        if not isinstance(payload, dict):
            return f"Format JSON invalide : {artifact}."
        expected_collection = {
            "sonarqube-issues.json": "issues",
            "sonarqube-hotspots.json": "hotspots",
            "zap-report.json": "site",
            "configuration-checks.json": "checks",
            "runtime-checks.json": "checks",
            "security-smoke-checks.json": "checks",
            "monitoring-checks.json": "checks",
        }.get(resolved.name)
        if resolved.name.startswith("trivy-"):
            expected_collection = "Results"
        if expected_collection and not isinstance(payload.get(expected_collection), list):
            return f"Rapport incomplet ({expected_collection} absent) : {artifact}."
    elif resolved.suffix.lower() == ".xml":
        try:
            root = ET.parse(resolved).getroot()
        except (ET.ParseError, OSError):
            return f"Rapport XML illisible : {artifact}."
        if root.tag not in {"testsuite", "testsuites"}:
            return f"Format de rapport de tests invalide : {artifact}."
        suites = list(root) if root.tag == "testsuites" else [root]
        if sum(int(suite.get("tests", "0")) for suite in suites) < 1:
            return f"Aucun test Maven n'est comptabilisé dans {artifact}."
    return ""


def record_check_report(args: argparse.Namespace) -> None:
    try:
        report = json.loads(args.report.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise SystemExit(f"Impossible de lire le rapport de contrôles {args.report}: {exc}") from exc
    checks = {
        item.get("id"): item
        for item in report.get("checks", [])
        if isinstance(item, dict) and item.get("id")
    }
    project_root = args.results.parent.parent.resolve()
    try:
        artifact = args.report.resolve().relative_to(project_root).as_posix()
    except ValueError:
        artifact = ""
    for control_id in args.id:
        result = checks.get(control_id)
        if result is None:
            status = "failed"
            summary = f"Le contrôle {control_id} n'a produit aucun résultat exploitable."
        else:
            status = result.get("status", "failed")
            if status not in STATUS_LABELS:
                status = "failed"
            summary = str(result.get("summary", "Contrôle terminé sans résumé."))
        record(
            argparse.Namespace(
                id=control_id,
                status=status,
                summary=summary,
                command=args.command,
                artifact=[artifact],
                output="",
                results=args.results,
            )
        )


def item_artifacts(item: dict) -> set[str]:
    values = item.get("artifacts") or [item.get("artifact", "")]
    return {Path(str(value)).name for value in values if value}


def _has_artifact(item: dict, filename: str) -> bool:
    return filename in item_artifacts(item)


def _load_json_report(path: Path, item: dict) -> dict | None:
    if not _has_artifact(item, path.name) or not path.is_file():
        return None
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def control_evidence(control_id: str, results_path: Path, item: dict) -> list[str]:
    reports = results_path.parent
    evidence: list[str] = []

    if item.get("status") == "not_run":
        evidence.append(
            "Aucun résultat n'a été enregistré pour ce stage dans ce build. "
            "Consultez la première étape en échec dans Jenkins pour identifier le blocage."
        )
        return evidence

    if control_id == "precommit":
        path = reports / "pre-commit.log"
        if _has_artifact(item, path.name) and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            passed = len(re.findall(r"\bPassed\b", text))
            failed = len(re.findall(r"\bFailed\b", text))
            evidence.append(f"{passed} hook(s) passé(s), {failed} hook(s) en échec.")
    elif control_id == "maven-tests":
        path = reports / "maven-tests.xml"
        if _has_artifact(item, path.name) and path.is_file():
            try:
                root = ET.parse(path).getroot()
                suites = list(root) if root.tag == "testsuites" else [root]
                counts = {key: sum(int(suite.get(key, "0")) for suite in suites) for key in ("tests", "failures", "errors", "skipped")}
                evidence.append(
                    f"{counts['tests']} test(s), {counts['failures']} échec(s), "
                    f"{counts['errors']} erreur(s), {counts['skipped']} ignoré(s)."
                )
            except (ET.ParseError, OSError, ValueError):
                evidence.append("Le rapport XML Maven est présent mais illisible.")
    elif control_id in {"sonarqube", "secure-coding"}:
        issues = _load_json_report(reports / "sonarqube-issues.json", item)
        hotspots = _load_json_report(reports / "sonarqube-hotspots.json", item)
        if issues is not None:
            issue_list = [
                issue for issue in issues.get("issues", [])
                if str(issue.get("component", "")).rsplit(":", 1)[-1].replace("\\", "/").startswith("src/main/")
            ]
            evidence.append(f"{len(issue_list)} issue(s) SonarQube retournée(s).")
        if hotspots is not None:
            hotspot_list = [
                hotspot for hotspot in hotspots.get("hotspots", [])
                if str(hotspot.get("component", "")).rsplit(":", 1)[-1].replace("\\", "/").startswith("src/main/")
            ]
            evidence.append(f"{len(hotspot_list)} hotspot(s) de sécurité retourné(s).")
    elif control_id in {"sca", "trivy", "continuous-scanning"}:
        scan_log = reports / "trivy-scan.log"
        if _has_artifact(item, scan_log.name) and scan_log.is_file():
            failures = [
                line.strip()
                for line in scan_log.read_text(encoding="utf-8", errors="replace").splitlines()
                if re.search(r"\b(FATAL|ERROR)\b", line, re.IGNORECASE)
            ]
            evidence.extend(
                redact_sensitive_text(line)[:400]
                for line in failures[-3:]
            )
        for report_name in ("trivy-backend.json", "trivy-frontend.json"):
            report = _load_json_report(reports / report_name, item)
            if report is None:
                evidence.append(f"{report_name} absent : le scan n'a pas produit de rapport pour cette image.")
                continue
            counts: dict[str, int] = {}
            for result in report.get("Results", []):
                for finding in result.get("Vulnerabilities") or []:
                    severity = str(finding.get("Severity", "UNKNOWN")).upper()
                    counts[severity] = counts.get(severity, 0) + 1
            summary = ", ".join(f"{severity} : {count}" for severity, count in sorted(counts.items()))
            evidence.append(
                f"{report_name} : {summary}."
                if summary
                else f"{report_name} : rapport présent, aucune vulnérabilité listée."
            )
        if control_id == "continuous-scanning":
            iac = _load_json_report(reports / "trivy-iac.json", item)
            if iac is not None:
                findings = [
                    misconfiguration
                    for result in iac.get("Results", [])
                    for misconfiguration in result.get("Misconfigurations") or []
                ]
                evidence.append(f"Trivy IaC : {len(findings)} finding(s) de configuration.")
    elif control_id == "iac-analysis":
        report = _load_json_report(reports / "trivy-iac.json", item)
        if report is not None:
            findings = [
                (result.get("Target", "cible inconnue"), misconfiguration)
                for result in report.get("Results", [])
                for misconfiguration in result.get("Misconfigurations") or []
            ]
            evidence.append(f"{len(findings)} finding(s) IaC dans {len(report.get('Results', []))} fichier(s) analysé(s).")
            evidence.extend(
                f"{misconfiguration.get('Severity', 'UNKNOWN')} · {misconfiguration.get('ID', '—')} · {target}"
                for target, misconfiguration in findings[:5]
            )
    elif control_id == "dependency-management":
        path = reports / "dependency-updates.log"
        if _has_artifact(item, path.name) and path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            updates = [line.strip() for line in text.splitlines() if re.search(r"\S\s+->\s+\S", line)]
            evidence.append(f"{len(updates)} mise(s) à jour candidate(s) listée(s); aucune n'est appliquée automatiquement.")
            evidence.extend(updates[:5])
    elif control_id == "zap":
        report = _load_json_report(reports / "zap-report.json", item)
        if report is not None:
            alerts = [alert for site in report.get("site", []) for alert in site.get("alerts", [])]
            risks = {"0": "INFO", "1": "LOW", "2": "MEDIUM", "3": "HIGH", "4": "CRITICAL"}
            counts: dict[str, int] = {}
            for alert in alerts:
                severity = risks.get(str(alert.get("riskcode", "0")), "INFO")
                counts[severity] = counts.get(severity, 0) + 1
            evidence.append(
                f"{len(alerts)} alerte(s) ZAP : "
                + (", ".join(f"{severity} {count}" for severity, count in sorted(counts.items())) or "aucune.")
            )
            evidence.extend(
                f"{alert.get('riskdesc', 'Info')} · {alert.get('alert', alert.get('name', 'Alerte ZAP'))}"
                for site in report.get("site", [])
                for alert in site.get("alerts", [])[:5]
            )
    elif control_id in {
        "acceptance-iac",
        "infrastructure-tests",
        "infrastructure-compliance",
        "security-smoke-tests",
        "configuration-safety",
        "secrets-management",
        "server-hardening",
        "continuous-monitoring",
    }:
        report_name = {
            "acceptance-iac": "configuration-checks.json",
            "infrastructure-compliance": "configuration-checks.json",
            "configuration-safety": "configuration-checks.json",
            "secrets-management": "configuration-checks.json",
            "infrastructure-tests": "runtime-checks.json",
            "server-hardening": "runtime-checks.json",
            "security-smoke-tests": "security-smoke-checks.json",
            "continuous-monitoring": "monitoring-checks.json",
        }[control_id]
        report = _load_json_report(reports / report_name, item)
        if report is not None:
            matched = [
                check for check in report.get("checks", [])
                if check.get("id") == control_id
            ]
            evidence.extend(
                str(check.get("summary", "Contrôle terminé sans détail."))
                for check in matched
            )

    return evidence


def _archived_artifact_url(build_url: str, artifact: str) -> str:
    if not build_url or not artifact:
        return ""
    parsed = urlsplit(build_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc or parsed.username or parsed.password:
        return ""
    target = Path(artifact)
    if target.is_absolute() or ".." in target.parts:
        return ""
    return f"../artifact/{quote(target.as_posix(), safe='/')}"


def safe_link(output: Path, artifact: str, build_url: str = "") -> str:
    if not artifact:
        return ""
    target = Path(artifact)
    if target.is_absolute():
        return ""
    project_root = output.parent.parent.resolve()
    resolved = (project_root / target).resolve()
    if not resolved.is_relative_to(project_root) or not resolved.is_file():
        return ""
    href = _archived_artifact_url(build_url, target.as_posix())
    if not href:
        relative_path = Path(os.path.relpath(resolved, output.parent)).as_posix()
        href = quote(relative_path, safe="/.-_")
    href = html.escape(href, quote=True)
    label = html.escape(target.name)
    return (
        f'<a class="report-link" href="{href}" '
        f'title="Ouvrir le fichier original : {label}">{label}</a>'
    )


def artifact_link(output: Path, artifact: str, build_url: str = "") -> str:
    return safe_link(output, artifact, build_url)


def artifact_links(output: Path, artifacts: list[str], build_url: str = "") -> list[str]:
    links = []
    seen = set()
    for artifact in artifacts:
        link = artifact_link(output, str(artifact), build_url)
        match = re.search(r'href="([^"]+)"', link)
        if link and match and match.group(1) not in seen:
            seen.add(match.group(1))
            links.append(link)
    return links


def load_vulnerabilities(results_path: Path, data: dict) -> list[dict]:
    findings = []
    current_artifacts = {
        filename
        for item in data.get("results", [])
        for filename in item_artifacts(item)
    }
    sonar_severity = {
        "BLOCKER": "CRITICAL",
        "CRITICAL": "CRITICAL",
        "HIGH": "HIGH",
        "MAJOR": "HIGH",
        "MEDIUM": "MEDIUM",
        "MINOR": "LOW",
        "LOW": "LOW",
        "INFO": "INFO",
    }
    sonar_issues_path = results_path.parent / "sonarqube-issues.json"
    if sonar_issues_path.name in current_artifacts and sonar_issues_path.is_file():
        try:
            report = json.loads(sonar_issues_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
        for issue in report.get("issues", []):
            component = str(issue.get("component", "")).rsplit(":", 1)[-1].replace("\\", "/")
            if not component.startswith("src/main/"):
                continue
            impacts = issue.get("impacts") or []
            security_impact = next(
                (impact for impact in impacts if impact.get("softwareQuality") == "SECURITY"),
                {},
            )
            severity = sonar_severity.get(
                str(security_impact.get("severity") or issue.get("severity", "INFO")).upper(),
                "INFO",
            )
            line = issue.get("line")
            location = f"{component}:{line}" if component and line else component
            findings.append({
                "source": "SonarQube SAST",
                "severity": severity,
                "id": str(issue.get("key") or issue.get("rule", "—")),
                "name": str(issue.get("message", "SonarQube vulnerability")),
                "detail": f"{location} · règle {issue.get('rule', '—')}" if location else f"Règle {issue.get('rule', '—')}",
                "report": f"reports/{sonar_issues_path.name}",
            })

    sonar_hotspots_path = results_path.parent / "sonarqube-hotspots.json"
    if sonar_hotspots_path.name in current_artifacts and sonar_hotspots_path.is_file():
        try:
            report = json.loads(sonar_hotspots_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
        for hotspot in report.get("hotspots", []):
            component = str(hotspot.get("component", "")).rsplit(":", 1)[-1].replace("\\", "/")
            if not component.startswith("src/main/"):
                continue
            severity = sonar_severity.get(
                str(hotspot.get("vulnerabilityProbability", "INFO")).upper(),
                "INFO",
            )
            line = hotspot.get("line")
            location = f"{component}:{line}" if component and line else component
            detail = f"{location} · hotspot {hotspot.get('status', '—')}" if location else f"Hotspot {hotspot.get('status', '—')}"
            findings.append({
                "source": "SonarQube hotspot",
                "severity": severity,
                "id": str(hotspot.get("key", "—")),
                "name": str(hotspot.get("message", "Security hotspot à examiner")),
                "detail": detail,
                "report": f"reports/{sonar_hotspots_path.name}",
            })

    for report_name in ("trivy-backend.json", "trivy-frontend.json", "trivy-sca.json"):
        report_path = results_path.parent / report_name
        if report_name not in current_artifacts or not report_path.is_file():
            continue
        try:
            report = json.loads(report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        image = str(report.get("ArtifactName", report_name))
        for result in report.get("Results", []):
            for vulnerability in result.get("Vulnerabilities") or []:
                severity = str(vulnerability.get("Severity", "UNKNOWN")).upper()
                fixed = str(vulnerability.get("FixedVersion") or "")
                if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                    continue
                findings.append({
                    "source": "Trivy SCA" if report_name == "trivy-sca.json" else "Trivy",
                    "severity": severity,
                    "id": str(vulnerability.get("VulnerabilityID", "—")),
                    "name": str(vulnerability.get("PkgName", "—")),
                    "detail": f"{vulnerability.get('InstalledVersion', '—')} → {fixed or 'Correctif non indiqué'} · {image}",
                    "report": f"reports/{report_name}",
                })
            for misconfiguration in result.get("Misconfigurations") or []:
                severity = str(misconfiguration.get("Severity", "UNKNOWN")).upper()
                if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                    continue
                location = result.get("Target", report_name)
                start_line = misconfiguration.get("CauseMetadata", {}).get("StartLine")
                if start_line:
                    location = f"{location}:{start_line}"
                findings.append({
                    "source": "Trivy IaC",
                    "severity": severity,
                    "id": str(misconfiguration.get("ID") or misconfiguration.get("AVDID", "—")),
                    "name": str(misconfiguration.get("Title") or misconfiguration.get("Message", "Configuration IaC à examiner")),
                    "detail": f"{location} · {misconfiguration.get('Message', '')}".strip(),
                    "report": f"reports/{report_name}",
                })
    iac_report_path = results_path.parent / "trivy-iac.json"
    if iac_report_path.name in current_artifacts and iac_report_path.is_file():
        try:
            report = json.loads(iac_report_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
        for result in report.get("Results", []):
            for misconfiguration in result.get("Misconfigurations") or []:
                severity = str(misconfiguration.get("Severity", "UNKNOWN")).upper()
                if severity not in {"CRITICAL", "HIGH", "MEDIUM", "LOW"}:
                    continue
                location = result.get("Target", "Infrastructure as Code")
                start_line = misconfiguration.get("CauseMetadata", {}).get("StartLine")
                if start_line:
                    location = f"{location}:{start_line}"
                findings.append({
                    "source": "Trivy IaC",
                    "severity": severity,
                    "id": str(misconfiguration.get("ID") or misconfiguration.get("AVDID", "—")),
                    "name": str(misconfiguration.get("Title") or misconfiguration.get("Message", "Configuration IaC à examiner")),
                    "detail": f"{location} · {misconfiguration.get('Message', '')}".strip(),
                    "report": f"reports/{iac_report_path.name}",
                })
    zap_report = results_path.parent / "zap-report.json"
    if zap_report.name in current_artifacts and zap_report.is_file():
        try:
            report = json.loads(zap_report.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            report = {}
        risk_levels = {"0": "INFO", "1": "LOW", "2": "MEDIUM", "3": "HIGH", "4": "CRITICAL"}
        for site in report.get("site", []):
            for alert in site.get("alerts", []):
                risk = str(alert.get("riskcode", "0"))
                severity = risk_levels.get(risk, "INFO")
                instances = alert.get("instances") or []
                endpoints = sorted({
                    urlsplit(str(instance.get("uri", ""))).path or "/"
                    for instance in instances
                    if instance.get("uri")
                })
                recommendation = re.sub(r"\s+", " ", html.unescape(
                    re.sub(r"<[^>]*>", " ", str(alert.get("solution", "")))
                )).strip()
                description = re.sub(r"\s+", " ", html.unescape(
                    re.sub(r"<[^>]*>", " ", str(alert.get("alert", alert.get("name", "ZAP finding"))))
                )).strip()
                detail = recommendation[:300] or "Consulter le rapport ZAP."
                if endpoints:
                    detail = f"{detail} Endpoints: {', '.join(endpoints[:4])}."
                findings.append({
                    "source": "OWASP ZAP",
                    "severity": severity,
                    "id": f"ZAP-{alert.get('pluginid', '—')}",
                    "name": description,
                    "detail": detail,
                    "report": "reports/zap-report.html",
                })
    order = {"CRITICAL": 0, "HIGH": 1, "MEDIUM": 2, "LOW": 3, "INFO": 4}
    return sorted(findings, key=lambda item: (order.get(item["severity"], 5), item["id"], item["source"]))


def generate(args: argparse.Namespace) -> None:
    data = load_results(args.results)
    data["generated_at"] = now()
    pipeline = data.setdefault("pipeline", {})
    build_number = str(getattr(args, "build_number", "") or "").strip()
    if not build_number and pipeline.get("build_number"):
        previous_build = pipeline["build_number"]
        for item in data["results"]:
            item.update({
                "status": "not_run",
                "summary": (
                    f"Non exécuté : le résultat Jenkins #{previous_build} est historique; "
                    "une nouvelle analyse n'a pas été lancée localement."
                ),
                "artifact": "",
                "artifacts": [],
                "output": "",
                "checked_at": "—",
            })
        pipeline.clear()
        pipeline["build_result"] = "Aucune nouvelle analyse exécutée"

    build_url = public_build_url(
        getattr(args, "build_url", ""),
        getattr(args, "public_base_url", ""),
        os.environ.get("JENKINS_URL", ""),
    )
    for key, value in (
        ("build_number", getattr(args, "build_number", "")),
        ("build_url", build_url),
        ("build_result", getattr(args, "build_result", "")),
    ):
        if value:
            pipeline[key] = value
    control_ids = {control_id for control_id, _, _, _ in CONTROLS}
    results = {
        item.get("id"): item
        for item in data["results"]
        if item.get("id") in control_ids
    }
    ordered = []
    for control_id, phase, tool, description in CONTROLS:
        item = results.get(control_id)
        if item is None:
            item = {
                "id": control_id,
                "phase": phase,
                "tool": tool,
                "status": "not_run",
                "summary": f"Non exécuté : {description}",
                "command": "",
                "artifact": "",
                "output": "",
                "checked_at": "—",
            }
            data["results"].append(item)
        elif (
            item.get("status") == "not_run"
            and item.get("summary") == "Aucun résultat enregistré pour cette exécution."
        ):
            item["summary"] = f"Non exécuté : {description}"
        item["phase"] = phase
        item["tool"] = tool
        ordered.append(item)
    data["results"] = ordered

    project_root = args.results.parent.parent.resolve()
    for item in ordered:
        if item.get("status") != "passed":
            continue
        artifact_values = item.get("artifacts") or [item.get("artifact", "")]
        artifacts = [str(value) for value in artifact_values if value]
        problem = (
            "Aucun rapport ou journal de preuve n'est associé à ce résultat."
            if not artifacts
            else next(
                (
                    error
                    for artifact in artifacts
                    if (error := artifact_problem(project_root, artifact))
                ),
                "",
            )
        )
        if problem:
            item["status"] = "blocked"
            item["summary"] = f"Résultat non vérifiable : {problem}"

    write_results(args.results, data)

    counts = {status: sum(item.get("status") == status for item in ordered) for status in STATUS_LABELS}
    phase_counts = {}
    for phase in PHASES:
        phase_items = [item for item in ordered if item.get("phase") == phase]
        completed = sum(item.get("status") in {"passed", "failed", "blocked", "manual"} for item in phase_items)
        phase_counts[phase] = (completed, len(phase_items))
    sections = []
    for phase_index, phase in enumerate(PHASES, start=1):
        rows = []
        for item in ordered:
            if item.get("phase") != phase:
                continue
            status = item.get("status", "not_run")
            if status not in STATUS_LABELS:
                status = "blocked"
            artifact_values = item.get("artifacts") or [item.get("artifact", "")]
            report_links = artifact_links(args.output, artifact_values, build_url)
            output = str(item.get("output", ""))
            output_block = (
                f'<details><summary>Afficher la sortie</summary><pre>{html.escape(output)}</pre></details>'
                if output else ""
            )
            remediation = REMEDIATIONS.get(
                str(item.get("id")),
                "Vérifier le résultat et corriger avant de considérer la phase terminée.",
            )
            control_id = str(item.get("id", ""))
            description = html.escape(CONTROL_DESCRIPTIONS.get(control_id, ""))
            evidence = control_evidence(control_id, args.results, item)
            missing_artifacts = [
                str(value)
                for value in artifact_values
                if value and not safe_link(args.output, str(value), build_url)
            ]
            evidence.extend(
                f"Rapport déclaré mais absent de cette exécution : {artifact}."
                for artifact in missing_artifacts
            )
            evidence_block = (
                '<ul class="evidence">'
                + "".join(f"<li>{html.escape(detail)}</li>" for detail in evidence)
                + "</ul>"
                if evidence else ""
            )
            artifact_cell = (
                f'<td><div class="report-links">{"".join(report_links)}</div></td>'
                if report_links else (
                    '<td><span class="muted">Aucun rapport produit.</span></td>'
                    if not artifact_values or not any(artifact_values)
                    else '<td><span class="muted">Rapport manquant.</span></td>'
                )
            )
            command = html.escape(str(item.get("command", ""))) or (
                '<span class="muted">Commande non enregistrée pour ce build.</span>'
            )
            rows.append(
                f'<tr data-phase="{html.escape(phase, quote=True)}">'
                f'<td><span class="badge {status}">{STATUS_LABELS[status]}</span></td>'
                f'<td><strong>{html.escape(str(item.get("tool", "")))}</strong>'
                f'<div class="muted">Objectif : {description}</div>'
                f'<div>{html.escape(str(item.get("summary", "")))}</div>{evidence_block}</td>'
                f'<td><code>{command}</code>{output_block}</td>'
                f'<td class="remediation">{html.escape(remediation)}</td>'
                f"{artifact_cell}"
                f'<td class="muted">{html.escape(str(item.get("checked_at", "—")))}</td>'
                "</tr>"
            )
        sections.append(f'<section id="phase-{phase_index}"><h2>{html.escape(phase)}</h2><div class="table-wrap"><table>'
                        "<thead><tr><th>État</th><th>Contrôle</th><th>Commande / détails</th>"
                        "<th>Prochaine action</th><th>Rapport</th><th>Vérifié le</th></tr></thead>"
                        f"<tbody>{''.join(rows)}</tbody></table></div></section>")

    vulnerability_rows = []
    vulnerabilities = load_vulnerabilities(args.results, data)
    severity_counts = {
        severity: sum(finding["severity"] == severity for finding in vulnerabilities)
        for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
    }
    assessed_count = sum(
        item.get("status") in {"passed", "failed", "blocked", "manual"}
        for item in ordered
    )
    coverage = round(assessed_count * 100 / len(ordered)) if ordered else 0
    for index, finding in enumerate(vulnerabilities, start=1):
        report_link = artifact_link(args.output, finding["report"], build_url)
        vulnerability_rows.append(
            f'<tr data-severity="{html.escape(finding["severity"])}" data-source="{html.escape(finding["source"])}">'
            f'<td>{html.escape(finding["source"])}</td>'
            f'<td><span class="badge {finding["severity"].lower()}">{html.escape(finding["severity"])}</span></td>'
            f'<td><code>{html.escape(finding["id"])}</code></td>'
            f'<td><strong>{html.escape(finding["name"])}</strong></td>'
            f'<td>{html.escape(finding["detail"])}</td>'
            f'<td>{report_link}</td></tr>'
        )
    finding_table = (
        '<div class="table-wrap"><table><thead><tr><th>Source</th><th>Sévérité</th><th>ID</th><th>Finding</th>'
        f'<th>Détail / localisation</th><th>Rapport</th></tr></thead><tbody>{"".join(vulnerability_rows)}'
        '</tbody></table></div>'
        if vulnerabilities else '<p class="muted">Aucun finding ou hotspot n’est associé aux rapports SonarQube, Trivy et ZAP disponibles.</p>'
    )
    severity_cards = "".join(
        f'<div class="severity-card"><span class="badge {severity.lower()}">{severity}</span>'
        f'<strong>{severity_counts[severity]}</strong></div>'
        for severity in ("CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO")
    )
    source_counts = {
        source: sum(finding["source"] == source for finding in vulnerabilities)
        for source in ("SonarQube SAST", "SonarQube hotspot", "Trivy", "Trivy SCA", "Trivy IaC", "OWASP ZAP")
    }
    source_bars = "".join(
        f'<div class="source-row"><span>{source}</span><strong>{source_counts[source]}</strong>'
        f'<span class="source-track"><span class="width-{round(source_counts[source] * 100 / max(1, len(vulnerabilities)))}"></span></span></div>'
        for source in source_counts
    )
    remediation_rows = "".join(
        f'<li><strong>{html.escape(finding["source"])} · {html.escape(finding["severity"])} · '
        f'{html.escape(finding["id"])}</strong><span>{html.escape(finding["name"])} — '
        f'{html.escape(finding["detail"])}</span></li>'
        for finding in vulnerabilities
    ) or '<li class="muted">Aucun finding Trivy ou ZAP n’a généré de recommandation pour cette exécution.</li>'
    total = len(ordered)
    generated_at = html.escape(str(data.get("generated_at", now())))
    summary_cards = "".join(
        f'<div class="card"><span class="badge {status}">{STATUS_LABELS[status]}</span>'
        f'<strong>{counts[status]}</strong></div>'
        for status in ("passed", "failed", "blocked", "skipped", "manual", "not_run")
    )
    phase_cards = "".join(
        f'<a class="phase-card phase-{index}" href="#phase-{index}">'
        f'<strong>{html.escape(phase)}</strong>'
        f'<span>{phase_counts[phase][0]} / {phase_counts[phase][1]} résultats</span>'
        f'<span class="phase-track"><span class="width-{round(phase_counts[phase][0] * 100 / phase_counts[phase][1]) if phase_counts[phase][1] else 0}"></span></span></a>'
        for index, phase in enumerate(PHASES, start=1)
    )
    pipeline = data.get("pipeline", {})
    build_number = html.escape(str(pipeline.get("build_number", "—")))
    build_result = html.escape(str(pipeline.get("build_result", "Rapport local — aucun build Jenkins associé")))
    build_url = str(pipeline.get("build_url", ""))
    build_link = (
        f'<a href="../">Ouvrir le build Jenkins #{build_number}</a>'
        if build_url.startswith(("http://", "https://")) else "Généré localement"
    )
    document = f"""<!doctype html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Suivi des contrôles DevSecOps</title>
<style>
:root {{ color-scheme: light; --ink:#172b4d; --muted:#5e6c84; --line:#dfe4ec; --bg:#f5f7fa; }}
* {{ box-sizing:border-box; }} body {{ margin:0; background:var(--bg); color:var(--ink); font:15px/1.5 system-ui,Segoe UI,Arial,sans-serif; }}
header {{ background:linear-gradient(120deg,#123c69,#087e8b); color:white; padding:34px max(24px,calc((100% - 1180px)/2)); }}
header h1 {{ margin:0 0 6px; font-size:clamp(1.6rem,3vw,2.3rem); }} header p {{ margin:0; opacity:.9; }}
main {{ max-width:1180px; margin:26px auto; padding:0 18px 44px; }}
.dashboard-layout {{ max-width:1360px; margin:0 auto; padding:18px; display:grid; grid-template-columns:210px minmax(0,1fr); gap:18px; align-items:start; }}
.side-menu {{ position:sticky; top:18px; background:#fff; border:1px solid var(--line); border-radius:12px; padding:16px; box-shadow:0 3px 12px #172b4d0b; }}
.menu-title {{ display:block; margin:0 0 12px; color:#1764b0; font-size:.78rem; font-weight:800; letter-spacing:.09em; text-transform:uppercase; }}
.menu-links {{ display:grid; gap:5px; }} .menu-links a {{ text-decoration:none; color:var(--ink); padding:9px 10px; border-radius:7px; font-size:.92rem; }}
.menu-links a:hover,.menu-links a.active {{ color:#075985; background:#eaf4ff; font-weight:700; }}
.dashboard-layout main {{ max-width:none; min-width:0; margin:0; padding:0 0 36px; }}
.summary {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(130px,1fr)); gap:12px; margin-bottom:28px; }}
.card {{ background:white; border:1px solid var(--line); border-radius:10px; padding:14px; display:flex; flex-direction:column; gap:8px; }}
.card strong {{ font-size:1.8rem; }} section {{ margin:26px 0; }} h2 {{ margin:0 0 12px; }}
.overview-grid {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(190px,1fr)); gap:14px; margin:18px 0; }}
.overview-card {{ background:white; border:1px solid var(--line); border-radius:12px; padding:18px; min-height:150px; }}
.overview-card h2 {{ font-size:.92rem; color:var(--muted); margin:0 0 12px; }}
.metric-caption {{ color:var(--muted); font-size:.88rem; }}
.coverage-value {{ display:block; font-size:2rem; font-weight:800; }}
.coverage-track,.phase-track {{ display:block; height:8px; overflow:hidden; border-radius:99px; background:#e9edf3; margin-top:10px; }}
.coverage-track span,.phase-track span {{ display:block; height:100%; background:#16824b; border-radius:99px; }}
.severity-grid {{ display:grid; grid-template-columns:repeat(5,minmax(90px,1fr)); gap:8px; margin:12px 0 20px; }}
.severity-card {{ background:#fff; border:1px solid var(--line); border-radius:9px; padding:10px; display:flex; flex-direction:column; gap:8px; }}
.severity-card strong {{ font-size:1.3rem; }}
.source-row {{ display:grid; grid-template-columns:95px 30px 1fr; gap:10px; align-items:center; margin:12px 0; }}
.source-track {{ display:block; height:9px; border-radius:99px; background:#e9edf3; overflow:hidden; }}
.source-track span {{ display:block; height:100%; border-radius:99px; background:#1764b0; }}
.pipeline-meta {{ display:flex; flex-wrap:wrap; align-items:center; gap:10px; color:var(--muted); font-size:.9rem; margin:-8px 0 16px; }}
.pipeline-meta a {{ color:#075985; font-weight:700; }}
.build-status {{ font-weight:800; }}
.phase-overview {{ display:grid; grid-template-columns:repeat(auto-fit,minmax(170px,1fr)); gap:12px; margin:18px 0 28px; }}
.phase-card {{ color:white; text-decoration:none; border-radius:10px; padding:16px; min-height:92px; display:flex; flex-direction:column; justify-content:space-between; box-shadow:0 2px 6px #172b4d22; }}
.phase-card:hover {{ filter:brightness(.94); }} .phase-card span {{ font-size:.88rem; opacity:.95; }}
.phase-track {{ background:#ffffff66; margin-top:8px; }} .phase-track span {{ background:#fff; }}
.phase-1 {{ background:#1764b0; }} .phase-2 {{ background:#e86b20; }} .phase-3 {{ background:#159dcc; }}
.phase-4 {{ background:#159447; }} .phase-5 {{ background:#d9212b; }}
.table-wrap {{ overflow:auto; background:white; border:1px solid var(--line); border-radius:10px; }}
table {{ width:100%; border-collapse:collapse; table-layout:fixed; min-width:820px; }}
th:nth-child(1),td:nth-child(1) {{ width:9%; }} th:nth-child(2),td:nth-child(2) {{ width:26%; }}
th:nth-child(3),td:nth-child(3) {{ width:16%; }} th:nth-child(4),td:nth-child(4) {{ width:16%; }}
th:nth-child(5),td:nth-child(5) {{ width:19%; }} th:nth-child(6),td:nth-child(6) {{ width:14%; }}
th,td {{ text-align:left; vertical-align:top; padding:13px; border-bottom:1px solid var(--line); overflow-wrap:anywhere; }}
th {{ background:#edf2f7; font-size:.83rem; text-transform:uppercase; letter-spacing:.04em; }} tr:last-child td {{ border-bottom:0; }}
.report-links {{ display:flex; flex-wrap:wrap; gap:7px; }}
.report-link {{ display:inline-flex; align-items:center; justify-content:center; min-height:38px; min-width:104px; padding:7px 11px; border:1px solid #8bbcf0; border-radius:7px; background:#eaf4ff; color:#075985; font-size:.86rem; font-weight:700; line-height:1.25; text-decoration:underline; text-decoration-thickness:1px; text-underline-offset:2px; white-space:normal; overflow-wrap:anywhere; }}
.report-link:hover,.report-link:focus {{ background:#d8ebff; border-color:#1764b0; color:#063f73; text-decoration-thickness:2px; }}
.badge {{ display:inline-block; border-radius:999px; padding:3px 9px; font-size:.78rem; font-weight:700; white-space:nowrap; }}
.passed,.manual {{ color:#126b42; background:#e2f5e9; }} .failed,.critical {{ color:#a12622; background:#ffebe6; }}
.high {{ color:#8f3f00; background:#ffeadb; }} .medium {{ color:#8a4b08; background:#fff0b3; }} .low {{ color:#42526e; background:#ebecf0; }}
.info {{ color:#1764b0; background:#e5f3ff; }}
.blocked {{ color:#8a4b08; background:#fff0b3; }} .skipped,.not_run {{ color:#42526e; background:#ebecf0; }}
.muted {{ color:var(--muted); font-size:.9rem; margin-top:4px; }} code {{ overflow-wrap:anywhere; }}
.evidence {{ margin:8px 0 0; padding-left:18px; color:#344563; font-size:.88rem; }}
.evidence li {{ margin:3px 0; }}
details {{ margin-top:8px; }} summary {{ cursor:pointer; color:#075985; }} pre {{ max-height:300px; overflow:auto; white-space:pre-wrap; background:#101828; color:#eef2f6; padding:12px; border-radius:6px; }}
.note {{ background:white; border:1px solid var(--line); border-left:4px solid #087e8b; padding:14px 18px; border-radius:8px; }}
.remediation {{ font-size:.9rem; }} .tasks {{ list-style:none; padding:0; display:grid; gap:10px; }}
.tasks li {{ background:#fff; border:1px solid var(--line); border-radius:8px; padding:12px; }}
.tasks span {{ display:block; color:var(--muted); font-size:.9rem; }}
footer {{ color:var(--muted); font-size:.85rem; margin-top:28px; }}
@media(max-width:1000px) {{
.dashboard-layout {{ grid-template-columns:1fr; padding:12px; gap:12px; }}
.side-menu {{ z-index:5; top:0; min-width:0; width:100%; padding:10px 12px; }}
.menu-title {{ margin:0 0 6px; }}
.menu-links {{ display:flex; min-width:0; max-width:100%; gap:4px; overflow-x:auto; }}
.menu-links a {{ white-space:nowrap; }}
.dashboard-layout main {{ padding:0 4px 28px; }}
table {{ min-width:0; }} th:nth-child(1),td:nth-child(1) {{ width:20%; }}
th:nth-child(2),td:nth-child(2) {{ width:48%; }} th:nth-child(3),td:nth-child(3) {{ display:none; }}
th:nth-child(4),td:nth-child(4) {{ display:none; }} th:nth-child(5),td:nth-child(5) {{ display:table-cell; width:32%; }}
th:nth-child(6),td:nth-child(6) {{ display:none; }}
}}
@media(max-width:640px) {{
header {{ padding:24px 18px; }} table {{ min-width:0; }}
th,td {{ padding:9px 6px; }} th {{ font-size:.72rem; }}
.report-links {{ flex-direction:column; align-items:stretch; }}
.report-link {{ width:100%; white-space:normal; text-align:center; }}
.severity-grid {{ grid-template-columns:repeat(3,minmax(80px,1fr)); }}
.overview-card {{ min-height:0; }} .phase-overview {{ grid-template-columns:1fr 1fr; }}
}}
</style>
</head>
<body>
<header><h1>Suivi des contrôles DevSecOps</h1>
<p>Vue globale des cinq phases DevSecOps — dernière génération : {generated_at}</p></header>
<div class="dashboard-layout">
<aside class="side-menu">
<span class="menu-title">Menu de suivi</span>
<nav class="menu-links" aria-label="Navigation du tableau de bord">
<a href="#overview">Vue générale</a>
<a href="#phases">Phases DevSecOps</a>
<a href="#findings">Findings</a>
<a href="#actions">Plan d'action</a>
<a href="#scope">Périmètre</a>
</nav>
</aside>
<main>
<section id="overview">
<h2>Vue générale</h2>
<div class="overview-grid">
<article class="overview-card">
<h2>Couverture des contrôles</h2><span class="coverage-value">{coverage}%</span>
<div class="coverage-track" aria-label="Couverture {coverage}%"><span class="width-{coverage}"></span></div>
<span class="metric-caption">{assessed_count} résultats disponibles sur {total} contrôles configurés dans le laboratoire.</span>
</article>
<article class="overview-card">
<h2>Findings des scans</h2><strong class="coverage-value">{len(vulnerabilities)}</strong>
{source_bars}
<span class="metric-caption">Constats importés des rapports de cette exécution. « Réussi » confirme l’exécution du contrôle, pas l’absence de findings.</span>
</article>
<article class="overview-card">
<h2>Dernière exécution</h2><strong class="coverage-value">#{build_number}</strong>
<span class="metric-caption build-status">{build_result}</span>
<span class="metric-caption">{build_link}</span>
</article>
</div>
<div class="summary">{summary_cards}</div>
<p class="muted">{total} contrôles suivis. Chaque phase détaille l'objectif, le résumé réel, les métriques ou constats extraits et les rapports disponibles. « Non exécuté » signifie qu'aucun résultat n'a été produit dans ce build.</p>
<h2>Répartition de sévérité — scans réels</h2><div class="severity-grid">{severity_cards}</div>
</section>
<section id="phases"><h2>Parcours des phases DevSecOps</h2>
<nav class="phase-overview" aria-label="Vue globale des phases">{phase_cards}</nav></section>
{''.join(sections)}
<section id="findings"><h2>Findings — SonarQube, Trivy SCA/IaC/images et OWASP ZAP</h2>
<p class="muted">{len(vulnerabilities)} finding(s) ou hotspot(s) issus des rapports des scanners associés au code, aux dépendances, aux images et à la configuration réellement analysés. Un hotspot SonarQube demande une revue et ne signifie pas à lui seul qu'une vulnérabilité est confirmée. Les alertes ZAP de niveau WARN sont informatives avec l'option -I et ne bloquent pas le pipeline.</p>
{finding_table}</section>
<section id="actions"><h2>Plan d'action</h2>
<p class="muted">Recommandations extraites des constats présents dans les rapports de cette exécution.</p>
<ul class="tasks">{remediation_rows}</ul></section>
<section id="scope" class="note"><h2>Périmètre et interprétation</h2>
<p>Cette dashboard présente uniquement les contrôles configurés dans le laboratoire DevSecOps. Les statuts et constats affichés sont issus des résultats et artefacts réellement produits par cette exécution; l'absence de finding dans ces rapports ne prouve pas l'absence de toute vulnérabilité.</p></section>
<footer>Résultats agrégés à partir des sorties du pipeline et des rapports liés. Les rapports détaillés restent disponibles dans les artefacts de la même exécution.</footer>
</main>
</div>
</body></html>
"""
    stylesheet_match = re.search(r"<style>\s*(.*?)\s*</style>", document, re.DOTALL)
    if stylesheet_match is None:
        raise RuntimeError("La feuille de style de la dashboard est introuvable.")
    stylesheet = stylesheet_match.group(1)
    stylesheet += "\n" + "\n".join(f".width-{percent} {{ width: {percent}%; }}" for percent in range(101))
    stylesheet_path = args.output.with_suffix(".css")
    stylesheet_path.write_text(stylesheet, encoding="utf-8")
    stylesheet_link = f'<link rel="stylesheet" href="{html.escape(stylesheet_path.name, quote=True)}">'
    document = document[:stylesheet_match.start()] + stylesheet_link + document[stylesheet_match.end():]
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(document, encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="action", required=True)

    init_parser = subparsers.add_parser("init", help="initialiser une nouvelle exécution")
    init_parser.add_argument("--project-root", type=Path, default=Path.cwd())
    init_parser.add_argument("--results", type=Path, default=Path("reports/devsecops-results.json"))
    init_parser.set_defaults(func=initialize)

    record_parser = subparsers.add_parser("record", help="enregistrer le résultat d'un contrôle")
    record_parser.add_argument("--id", required=True, choices=[item[0] for item in CONTROLS])
    record_parser.add_argument("--status", required=True, choices=list(STATUS_LABELS))
    record_parser.add_argument("--summary", required=True)
    record_parser.add_argument("--command", default="")
    record_parser.add_argument("--artifact", action="append", default=[])
    record_parser.add_argument("--output", default="")
    record_parser.add_argument("--results", type=Path, default=Path("reports/devsecops-results.json"))
    record_parser.set_defaults(func=record)

    checks_parser = subparsers.add_parser("record-check-report", help="enregistrer les contrôles d'un rapport JSON")
    checks_parser.add_argument("--report", type=Path, required=True)
    checks_parser.add_argument("--id", action="append", required=True, choices=[item[0] for item in CONTROLS])
    checks_parser.add_argument("--command", default="")
    checks_parser.add_argument("--results", type=Path, default=Path("reports/devsecops-results.json"))
    checks_parser.set_defaults(func=record_check_report)

    generate_parser = subparsers.add_parser("generate", help="générer le rapport HTML consolidé")
    generate_parser.add_argument("--results", type=Path, default=Path("reports/devsecops-results.json"))
    generate_parser.add_argument("--output", type=Path, default=Path("reports/devsecops-report.html"))
    generate_parser.add_argument("--build-number", default="")
    generate_parser.add_argument("--build-url", default="")
    generate_parser.add_argument("--public-base-url", default="")
    generate_parser.add_argument("--build-result", default="")
    generate_parser.set_defaults(func=generate)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
