import json
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

DEFAULT_TTL_SECONDS = 7 * 24 * 3600


def cache_dir() -> Path:
    root = Path.home() / ".cache" / "icanhazflux"
    root.mkdir(parents=True, exist_ok=True)
    return root


def cache_path(name: str) -> Path:
    return cache_dir() / f"{name}.json"


def load(name: str, ttl: int = DEFAULT_TTL_SECONDS) -> Any | None:
    path = cache_path(name)
    if not path.exists():
        return None
    try:
        payload = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError):
        return None
    if time.time() - payload.get("ts", 0) > ttl:
        return None
    return payload.get("data")


def save(name: str, data: Any) -> None:
    path = cache_path(name)
    path.write_text(json.dumps({"ts": time.time(), "data": data}, default=str))


def get_or_fetch(
    name: str,
    fetch: Callable[[], Any],
    *,
    refresh: bool = False,
    ttl: int = DEFAULT_TTL_SECONDS,
) -> Any:
    if not refresh:
        cached = load(name, ttl=ttl)
        if cached is not None:
            return cached
    data = fetch()
    save(name, data)
    return data


def clear(name: str | None = None) -> None:
    if name is None:
        for path in cache_dir().glob("*.json"):
            path.unlink(missing_ok=True)
    else:
        cache_path(name).unlink(missing_ok=True)
