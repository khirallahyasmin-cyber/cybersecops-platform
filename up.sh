#!/usr/bin/env bash
set -Eeuo pipefail
cd "$(dirname "${BASH_SOURCE[0]}")"
[[ -f .env ]] || cp .env.example .env
docker compose up -d --build --wait mysql backend frontend
docker compose ps
