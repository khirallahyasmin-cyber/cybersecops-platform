#!/usr/bin/env python3
"""Download all SonarQube security issues and hotspots for a project."""

from __future__ import annotations

import argparse
import base64
import json
import os
from pathlib import Path
from urllib.parse import urlencode
from urllib.request import Request, urlopen


PAGE_SIZE = 100


def fetch_all(
    base_url: str,
    endpoint: str,
    collection: str,
    query: dict[str, str],
    authorization: str,
) -> dict:
    items = []
    page = 1
    total = None
    while total is None or len(items) < total:
        parameters = {**query, "p": str(page), "ps": str(PAGE_SIZE)}
        url = f"{base_url.rstrip('/')}/api/{endpoint}?{urlencode(parameters)}"
        request = Request(url, headers={"Authorization": authorization})
        with urlopen(request, timeout=30) as response:
            payload = json.load(response)
        page_items = payload.get(collection)
        if not isinstance(page_items, list):
            raise RuntimeError(f"SonarQube API response has no {collection} list.")
        items.extend(page_items)
        paging = payload.get("paging", {})
        total = int(paging.get("total", len(page_items)))
        if not page_items:
            break
        page += 1
    return {"paging": {"total": len(items)}, collection: items}


def download(args: argparse.Namespace) -> None:
    token = os.environ["SONAR_TOKEN"]
    authorization = "Basic " + base64.b64encode(f"{token}:".encode("utf-8")).decode("ascii")
    reports = (
        (
            "issues",
            "issues/search",
            "issues",
            {"componentKeys": args.project_key, "types": "VULNERABILITY", "resolved": "false"},
        ),
        (
            "hotspots",
            "hotspots/search",
            "hotspots",
            {"projectKey": args.project_key},
        ),
    )
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for name, endpoint, collection, query in reports:
        payload = fetch_all(
            args.base_url,
            endpoint,
            collection,
            query,
            authorization,
        )
        output = args.output_dir / f"sonarqube-{name}.json"
        output.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", required=True)
    parser.add_argument("--project-key", required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    download(parser.parse_args())


if __name__ == "__main__":
    main()
