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


def test_corrupt_cache_falls_back_to_refetch(tmp_path, monkeypatch):
    """A truncated file must trigger a refetch, not raise."""
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    cache.cache_path("t").write_text('{"ts": 123, "data": [1, 2')  # truncated

    assert cache.load("t") is None
    assert cache.get_or_fetch("t", lambda: {"ok": True}) == {"ok": True}
    assert cache.load("t") == {"ok": True}


def test_save_is_atomic_and_leaves_no_residue(tmp_path, monkeypatch):
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    cache.save("t", {"ok": True})

    assert cache.load("t") == {"ok": True}
    assert list(tmp_path.iterdir()) == [cache.cache_path("t")]


def test_clear_sweeps_temp_files(tmp_path, monkeypatch):
    """Temp files from an interrupted save are swept by a full clear."""
    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    cache.save("t", 1)
    (tmp_path / ".t.abc123.tmp").write_text("partial")

    cache.clear()

    assert list(tmp_path.iterdir()) == []
