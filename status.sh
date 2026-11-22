#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
docker compose ps
echo
curl --fail --silent --show-error http://localhost:8080/api/health
echo
