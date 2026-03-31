"""HTTP smoke checks for the NewsRadar local stack."""
from __future__ import annotations

import argparse
import json
import sys
from typing import Any

import httpx


def _request(client: httpx.Client, method: str, url: str, **kwargs: Any) -> tuple[int, Any]:
    response = client.request(method, url, **kwargs)
    payload: Any
    try:
        payload = response.json()
    except ValueError:
        payload = response.text
    return response.status_code, payload


def main() -> int:
    parser = argparse.ArgumentParser(description="Smoke test the NewsRadar local stack.")
    parser.add_argument("--backend-url", default="http://localhost:8000")
    parser.add_argument("--smcp-url", default="http://localhost:8080")
    parser.add_argument("--aiagent-url", default="http://localhost:8090")
    parser.add_argument("--window-months", type=int, default=6)
    parser.add_argument("--include-aiagent", action="store_true")
    parser.add_argument("--expect-nonempty", action="store_true")
    args = parser.parse_args()

    summary: dict[str, Any] = {"checks": []}
    failed = False

    with httpx.Client(timeout=120.0) as client:
        for name, url in [
            ("backend_health", f"{args.backend_url}/api/health"),
            ("jobs_status", f"{args.backend_url}/api/jobs/status"),
            ("catalog_sources", f"{args.backend_url}/api/catalog/sources"),
            ("smcp_health", f"{args.smcp_url}/health"),
        ]:
            status, payload = _request(client, "GET", url)
            summary["checks"].append({"name": name, "status_code": status})
            if status >= 400:
                failed = True

        trend_status, trend_payload = _request(
            client,
            "POST",
            f"{args.backend_url}/api/trendmap/generate",
            json={"window_months": args.window_months, "force": True},
        )
        summary["checks"].append({"name": "trendmap_generate", "status_code": trend_status})
        if trend_status >= 400:
            failed = True

        risk_status, risk_payload = _request(
            client,
            "POST",
            f"{args.backend_url}/api/riskmap/generate?window_months={args.window_months}&force=true",
        )
        summary["checks"].append({"name": "riskmap_generate", "status_code": risk_status})
        if risk_status >= 400:
            failed = True

        latest_trend_status, latest_trend = _request(client, "GET", f"{args.backend_url}/api/trendmap/latest")
        latest_risk_status, latest_risk = _request(client, "GET", f"{args.backend_url}/api/riskmap/latest")
        summary["checks"].append({"name": "trendmap_latest", "status_code": latest_trend_status})
        summary["checks"].append({"name": "riskmap_latest", "status_code": latest_risk_status})
        if latest_trend_status >= 400 or latest_risk_status >= 400:
            failed = True

        if args.include_aiagent:
            ai_status, ai_payload = _request(client, "GET", f"{args.aiagent_url}/health")
            summary["checks"].append({"name": "aiagent_health", "status_code": ai_status})
            if ai_status >= 400:
                failed = True

        if args.expect_nonempty:
            trend_docs = (latest_trend.get("summary") or {}).get("total_documents", 0) if isinstance(latest_trend, dict) else 0
            risk_docs = (latest_risk.get("summary") or {}).get("total_documents", 0) if isinstance(latest_risk, dict) else 0
            if trend_docs <= 0 or risk_docs <= 0:
                failed = True
                summary["checks"].append(
                    {
                        "name": "nonempty_snapshots",
                        "status_code": 500,
                        "detail": {
                            "trend_documents": trend_docs,
                            "risk_documents": risk_docs,
                        },
                    }
                )

    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
