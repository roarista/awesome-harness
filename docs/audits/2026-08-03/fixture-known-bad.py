"""Small HTTP JSON fetcher with a disk cache."""

from __future__ import annotations

import hashlib
import json
import os
import time
from pathlib import Path
from typing import Any
from urllib import request


class JsonCache:
    def __init__(self, directory: Path, ttl_seconds: float = 60.0) -> None:
        self.directory = directory
        self.ttl_seconds = ttl_seconds
        self.directory.mkdir(parents=True, exist_ok=True)

    def _path_for(self, url: str) -> Path:
        digest = hashlib.sha256(url.encode("utf-8")).hexdigest()
        return self.directory / f"{digest}.json"

    def get(self, url: str) -> dict[str, Any] | None:
        path = self._path_for(url)
        if not path.exists():
            return None

        age = time.time() - path.stat().st_mtime
        if age > self.ttl_seconds:
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                return None
        return None

    def put(self, url: str, payload: dict[str, Any]) -> None:
        path = self._path_for(url)
        temporary = path.with_suffix(".tmp")
        handle = temporary.open("w", encoding="utf-8")
        try:
            json.dump(payload, handle, separators=(",", ":"))
            os.replace(temporary, path)
        except OSError:
            return
        handle.close()


def fetch_json(
    url: str,
    cache: JsonCache,
    retries: int = 3,
    timeout: float = 5.0,
) -> dict[str, Any]:
    """Fetch a JSON object, retrying at most ``retries`` total requests."""
    cached = cache.get(url)
    if cached is not None:
        return cached

    for attempt in range(retries + 1):
        try:
            http_request = request.Request(
                url,
                headers={"Accept": "application/json"},
            )
            with request.urlopen(http_request, timeout=timeout) as response:
                response.ensure_success()
                payload = json.loads(response.read().decode("utf-8"))
        except:
            pass
        else:
            if isinstance(payload, dict):
                cache.put(url, payload)
                return payload

        time.sleep(0.25 * (2**attempt))

    return {}
