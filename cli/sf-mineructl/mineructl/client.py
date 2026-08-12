"""MinerU HTTP API client."""
from __future__ import annotations

from typing import Any

import requests


class MinerUClient:
    def __init__(self, base_url: str, timeout: int = 30) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def _get(self, path: str) -> dict[str, Any]:
        resp = requests.get(f"{self.base_url}{path}", timeout=self.timeout)
        resp.raise_for_status()
        return resp.json()

    def _post(self, path: str, json: dict[str, Any]) -> dict[str, Any]:
        resp = requests.post(
            f"{self.base_url}{path}", json=json, timeout=self.timeout
        )
        resp.raise_for_status()
        return resp.json()

    def probe(self) -> dict[str, Any]:
        """Quick health probe (no auth required)."""
        try:
            data = self._get("/health")
            return {"ok": True, "info": data}
        except Exception as exc:
            return {"ok": False, "error": str(exc)}

    def doctor(self) -> dict[str, Any]:
        """Full connectivity + health + version check."""
        checks: list[dict[str, Any]] = []

        # connectivity
        probe = self.probe()
        checks.append({
            "name": "connectivity",
            "ok": probe["ok"],
            "base_url": self.base_url,
            **({"error": probe["error"]} if not probe["ok"] else {}),
        })

        # version
        if probe["ok"]:
            info = probe.get("info", {})
            checks.append({
                "name": "version",
                "ok": True,
                "version": info.get("version", "unknown"),
                "status": info.get("status", "unknown"),
            })

        return {"ok": all(c["ok"] for c in checks), "checks": checks}

    def version(self) -> dict[str, Any]:
        """Get server version."""
        data = self._get("/health")
        return {"version": data.get("version", "unknown"), "status": data.get("status", "unknown")}

    def submit(self, url: str, output_format: str = "markdown") -> dict[str, Any]:
        """Submit a document parsing task."""
        return self._post("/extract", {"url": url, "output_format": output_format})

    def status(self, task_id: str) -> dict[str, Any]:
        """Get task status."""
        return self._get(f"/extract/{task_id}")

    def result(self, task_id: str) -> dict[str, Any]:
        """Get task result."""
        return self._get(f"/extract/{task_id}/result")

    def tasks(self, limit: int = 20, status: str | None = None) -> dict[str, Any]:
        """List recent tasks."""
        params = f"?limit={limit}"
        if status:
            params += f"&status={status}"
        return self._get(f"/tasks{params}")
