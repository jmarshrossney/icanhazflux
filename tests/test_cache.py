import time

from icanhazflux import cache


def test_get_or_fetch_caches(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return {"ok": True}

    a = cache.get_or_fetch("t", fetch)
    b = cache.get_or_fetch("t", fetch)
    assert a == b == {"ok": True}
    assert calls["n"] == 1


def test_refresh_bypasses_cache(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_fetch("t", fetch) == 1
    assert cache.get_or_fetch("t", fetch, refresh=True) == 2
    assert calls["n"] == 2


def test_ttl_expiry(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    calls = {"n": 0}

    def fetch():
        calls["n"] += 1
        return calls["n"]

    assert cache.get_or_fetch("t", fetch, ttl=1) == 1
    time.sleep(1.1)
    assert cache.get_or_fetch("t", fetch, ttl=1) == 2


def test_clear(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    cache.save("a", 1)
    cache.save("b", 2)
    cache.clear("a")
    assert cache.load("a") is None
    assert cache.load("b") == 2
    cache.clear()
    assert cache.load("b") is None
