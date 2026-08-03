import json
import os
import tempfile
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
    # Write-then-rename so a crash or a concurrent refresh can never leave a
    # truncated file behind. The temp file must share a filesystem with the
    # target for os.replace to be atomic, hence dir=path.parent.
    path = cache_path(name)
    payload = json.dumps({"ts": time.time(), "data": data}, default=str)
    fd, tmp = tempfile.mkstemp(dir=path.parent, prefix=f".{name}.", suffix=".tmp")
    try:
        with os.fdopen(fd, "w") as f:
            f.write(payload)
        os.replace(tmp, path)
    except BaseException:
        Path(tmp).unlink(missing_ok=True)
        raise


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
        root = cache_dir()
        # Also sweep temp files left by an interrupted save.
        for pattern in ("*.json", ".*.tmp"):
            for path in root.glob(pattern):
                path.unlink(missing_ok=True)
    else:
        cache_path(name).unlink(missing_ok=True)
