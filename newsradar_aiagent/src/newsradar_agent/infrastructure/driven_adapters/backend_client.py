"""Backend client adapter for canonical NewsRadar APIs."""
from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)


class BackendClientError(Exception):
    """Raised when the backend API cannot be reached or returns invalid data."""


class BackendClient:
    """Thin HTTP client for backend read capabilities consumed by the agent."""

    def __init__(self, base_url: str = "http://localhost:8000", timeout: float = 60.0) -> None:
        self._base_url = base_url.rstrip("/")
        self._timeout = timeout

    def get_json(self, path: str) -> Any:
        url = f"{self._base_url}{path}"
        try:
            with httpx.Client(timeout=self._timeout) as client:
                response = client.get(url)
                response.raise_for_status()
                return response.json()
        except httpx.HTTPStatusError as exc:
            logger.error("Backend GET %s failed with HTTP %s", url, exc.response.status_code)
            raise BackendClientError(
                f"Backend request failed with HTTP {exc.response.status_code}"
            ) from exc
        except httpx.RequestError as exc:
            logger.error("Backend GET %s failed: %s", url, exc)
            raise BackendClientError(f"Backend request unreachable: {exc}") from exc
        except ValueError as exc:
            logger.error("Backend GET %s returned invalid JSON: %s", url, exc)
            raise BackendClientError("Backend returned invalid JSON") from exc

    def health(self) -> dict[str, Any]:
        return self.get_json("/api/health")

    def jobs_status(self) -> list[dict[str, Any]]:
        payload = self.get_json("/api/jobs/status")
        return payload if isinstance(payload, list) else []

    def tech_watch_executions(self) -> list[dict[str, Any]]:
        payload = self.get_json("/api/tech-watch/executions")
        return payload if isinstance(payload, list) else []

    def trendmap_latest(self) -> dict[str, Any]:
        return self.get_json("/api/trendmap/latest")

    def riskmap_latest(self) -> dict[str, Any]:
        return self.get_json("/api/riskmap/latest")
