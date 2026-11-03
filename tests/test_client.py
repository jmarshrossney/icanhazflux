import pytest

from icanhazflux import client as client_mod
from icanhazflux.client import Client
from icanhazflux.types import match_product


@pytest.fixture
def patched_client(monkeypatch, datatypes, sample_objects):
    """Stub _find_objects and download; record how often each is called."""
    calls: dict = {"find": [], "download": []}
    resolved: list = []

    def fake_find_objects(station, **kwargs):
        calls["find"].append(kwargs)
        return resolved, sample_objects

    def fake_download(self, objects, out=".", *, progress=True):
        calls["download"].append((objects, out, progress))
        return []

    monkeypatch.setattr(client_mod, "_find_objects", fake_find_objects)
    monkeypatch.setattr(Client, "download", fake_download)
    monkeypatch.setattr(
        client_mod, "list_datatypes", lambda *, refresh=False: datatypes
    )
    return calls, resolved


def test_get_warns_on_raw_types(patched_client, datatypes, capsys):
    """Regression: the raw-data warning must fire for URI-list datatypes.

    Previously Client.get filtered a list[str] through isinstance(t, DataType),
    got [], and silently skipped the warning on the most deliberate raw path.
    """
    _, resolved = patched_client
    resolved.extend(match_product(datatypes, "raw"))

    Client().get("SE-Htm", datatype=[t.uri for t in resolved])

    assert "PI consultation" in capsys.readouterr().out


def test_get_silent_for_l2(patched_client, datatypes, capsys):
    _, resolved = patched_client
    resolved.extend(match_product(datatypes, "l2"))

    Client().get("SE-Htm", product="l2")

    assert "PI consultation" not in capsys.readouterr().out


def test_get_silent_when_progress_false(patched_client, datatypes, capsys):
    _, resolved = patched_client
    resolved.extend(match_product(datatypes, "raw"))

    Client().get("SE-Htm", product="raw", progress=False)

    assert "PI consultation" not in capsys.readouterr().out


def test_get_resolves_once(patched_client, datatypes):
    """get() must not re-resolve datatypes that _find_objects already resolved."""
    calls, resolved = patched_client
    resolved.extend(match_product(datatypes, "raw"))

    Client().get("SE-Htm", product="raw")

    assert len(calls["find"]) == 1


def test_get_threads_refresh(patched_client, datatypes):
    calls, resolved = patched_client
    resolved.extend(match_product(datatypes, "l2"))

    Client().get("SE-Htm", product="l2", refresh=True)

    assert calls["find"][0]["refresh"] is True


def test_get_downloads_found_objects(patched_client, datatypes, sample_objects):
    calls, resolved = patched_client
    resolved.extend(match_product(datatypes, "l2"))

    Client().get("SE-Htm", product="l2", out="./somewhere")

    objects, out, _ = calls["download"][0]
    assert objects == sample_objects
    assert out == "./somewhere"


def test_find_returns_objects_only(patched_client, sample_objects):
    assert Client().find("SE-Htm") == sample_objects


def test_products_maps_presets_to_labels(patched_client, datatypes):
    products = Client().products()

    assert products["l2"] == ["ETC L2 Fluxnet (half-hourly)"]
    assert products["meteo"] == ["ETC L2 Meteo"]
    assert products["raw"] == [
        "ICOS ETC Eddy Flux Raw ASCII daily archive",
        "ICOS ETC Eddy Flux Raw binary daily archive",
    ]


def test_products_empty_for_unmatched_preset(monkeypatch):
    """A preset that matches nothing maps to [] rather than raising."""
    monkeypatch.setattr(client_mod, "list_datatypes", lambda *, refresh=False: [])

    products = Client().products()

    assert products
    assert all(labels == [] for labels in products.values())


def test_total_size_bytes(sample_objects):
    assert Client.total_size_bytes(sample_objects) == 10 * 1024 * 1024


def test_find_collection_without_station(monkeypatch):
    from icanhazflux import client as client_mod

    seen = {}

    def fake_find_objects(station, **kwargs):
        seen["station"] = station
        seen.update(kwargs)
        return [], []

    monkeypatch.setattr(client_mod, "_find_objects", fake_find_objects)
    Client().find(collection="10.18160/S6HM-CP8Q")
    assert seen["station"] is None
    assert seen["collection"] == "10.18160/S6HM-CP8Q"
