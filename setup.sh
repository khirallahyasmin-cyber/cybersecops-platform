#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"

command -v docker >/dev/null || { echo "Docker Engine is required in Ubuntu."; exit 1; }
docker compose version >/dev/null || { echo "Docker Compose v2 is required."; exit 1; }

profiles=()
case "${1:-}" in
  "")
    ;;
  --tools)
    profiles+=(--profile devops)
    ;;
  --monitoring)
    profiles+=(--profile monitoring)
    ;;
  --all)
    profiles+=(--profile devops --profile monitoring)
    ;;
  *)
    echo "Usage: $0 [--tools|--monitoring|--all]" >&2
    exit 2
    ;;
esac

if [[ ! -f .env ]]; then
  cp .env.example .env
  chmod 600 .env
  echo "Created .env with local-only development passwords. Change them before sharing this machine."
fi

docker compose "${profiles[@]}" config --quiet
docker compose "${profiles[@]}" up -d --build --wait
echo
echo "Application: http://localhost:8081"
echo "API health:  http://localhost:8080/api/health"
if [[ "${1:-}" == "--tools" || "${1:-}" == "--all" ]]; then
  echo "Jenkins:     http://localhost:8083"
  echo "SonarQube:   http://localhost:9000"
  echo "Nexus:       http://localhost:8082"
fi
if [[ "${1:-}" == "--monitoring" || "${1:-}" == "--all" ]]; then
  echo "Prometheus:  http://localhost:9090"
  echo "Grafana:     http://localhost:3000"
fi
