from datetime import UTC, datetime

import pytest

from icanhazflux.objects import _find_objects, build_time_filters, parse_time
from icanhazflux.types import _is_sensitive_product, match_product


def test_parse_time_none():
    assert parse_time(None) is None


def test_parse_time_datetime_passthrough():
    dt = datetime(2024, 6, 1, tzinfo=UTC)
    assert parse_time(dt) is dt


def test_parse_time_date_start_of_day():
    assert parse_time("2024-06-01") == "2024-06-01T00:00:00Z"


def test_parse_time_date_end_of_day():
    assert parse_time("2024-06-01", end_of_day=True) == "2024-06-01T23:59:59Z"


def test_parse_time_full_iso_unchanged():
    assert parse_time("2024-06-01T12:30:00Z") == "2024-06-01T12:30:00Z"


def test_build_time_filters_empty():
    assert build_time_filters() == []


def test_build_time_filters_start_only():
    filters = build_time_filters(start="2024-06-01")
    assert len(filters) == 1
    f = filters[0]
    assert f.prop == "timeEnd"
    assert f.op == ">"
    assert f.value == "2024-06-01T00:00:00Z"


def test_build_time_filters_end_only():
    filters = build_time_filters(end="2024-06-03")
    assert len(filters) == 1
    f = filters[0]
    assert f.prop == "timeStart"
    assert f.op == "<"
    assert f.value == "2024-06-03T23:59:59Z"


def test_build_time_filters_range_overlap_semantics():
    filters = build_time_filters(start="2024-06-01", end="2024-06-03")
    assert len(filters) == 2
    by_prop = {f.prop: f for f in filters}
    assert by_prop["timeEnd"].op == ">"
    assert by_prop["timeEnd"].value == "2024-06-01T00:00:00Z"
    assert by_prop["timeStart"].op == "<"
    assert by_prop["timeStart"].value == "2024-06-03T23:59:59Z"


# _find_objects resolution: returns the resolved datatypes alongside the objects,
# so callers (Client.get) can run the raw-data check without re-resolving.


@pytest.fixture
def patched_objects(monkeypatch, datatypes, stations, sample_objects):
    """Stub the portal calls in icanhazflux.objects; record the query kwargs."""
    from icanhazflux import objects as objects_mod

    calls: dict = {"list_datatypes": 0, "query": None}

    def fake_list_datatypes(*, refresh=False):
        calls["list_datatypes"] += 1
        return datatypes

    def fake_list_data_objects(**kwargs):
        calls["query"] = kwargs
        return []

    monkeypatch.setattr(objects_mod, "list_datatypes", fake_list_datatypes)
    monkeypatch.setattr(objects_mod.meta, "list_data_objects", fake_list_data_objects)
    monkeypatch.setattr(
        objects_mod, "resolve_station", lambda q, refresh=False: stations[0]
    )
    monkeypatch.setattr(
        objects_mod,
        "resolve_product",
        lambda p, refresh=False: match_product(datatypes, p),
    )
    return calls


def test_find_objects_uri_list_resolves_types(patched_objects, datatypes):
    """Regression: a list[str] of URIs must still yield resolved DataTypes.

    Client.get relies on these to decide whether to print the raw-data
    warning; previously it got an empty list and stayed silent.
    """
    raw = match_product(datatypes, "raw")
    uris = [t.uri for t in raw]

    types, _ = _find_objects("SE-Htm", datatype=uris)

    assert [t.uri for t in types] == uris
    assert _is_sensitive_product(types) is True
    assert patched_objects["query"]["datatype"] == uris


def test_find_objects_unknown_uri_still_queried(patched_objects):
    """URIs absent from the eco catalog pass through but resolve to nothing."""
    types, _ = _find_objects("SE-Htm", datatype=["http://example.invalid/nope"])

    assert types == []
    assert patched_objects["query"]["datatype"] == ["http://example.invalid/nope"]


def test_find_objects_datatype_overrides_product(patched_objects, datatypes):
    """datatype wins over product, per the documented precedence."""
    types, _ = _find_objects("SE-Htm", product="l2", datatype="ETC L2 Meteo")

    assert [t.label for t in types] == ["ETC L2 Meteo"]


def test_find_objects_datatype_list_of_datatypes(patched_objects, datatypes):
    meteo = match_product(datatypes, "meteo")
    types, _ = _find_objects("SE-Htm", datatype=meteo)

    assert types == meteo
    assert patched_objects["query"]["datatype"] == [t.uri for t in meteo]


def test_find_objects_product_preset(patched_objects):
    types, _ = _find_objects("SE-Htm", product="l2")

    assert [t.label for t in types] == ["ETC L2 Fluxnet (half-hourly)"]


def test_find_objects_include_deprecated_passed_through(patched_objects):
    _find_objects("SE-Htm", product="l2", include_deprecated=True)

    assert patched_objects["query"]["include_deprecated"] is True


@pytest.fixture
def patched_collection(monkeypatch, patched_objects):
    """Stub the SPARQL path; record the query text."""
    from types import SimpleNamespace

    from icanhazflux import objects as objects_mod

    def fake_sparql_select(query):
        patched_objects["sparql"] = query
        return SimpleNamespace(bindings=[])

    monkeypatch.setattr(objects_mod.meta, "sparql_select", fake_sparql_select)
    monkeypatch.setattr(
        objects_mod,
        "resolve_collection",
        lambda q, refresh=False: "https://meta.icos-cp.eu/collections/r2025",
    )
    return patched_objects


def test_find_objects_collection_without_station(patched_collection, datatypes):
    types, objs = _find_objects(collection="10.18160/S6HM-CP8Q", product="l2")

    q = patched_collection["sparql"]
    assert "<https://meta.icos-cp.eu/collections/r2025> dcterms:hasPart+" in q
    assert "VALUES ?station" not in q
    assert types[0].uri in q.replace("https://", "http://")
    assert patched_collection["query"] is None
    assert objs == []


def test_find_objects_collection_with_station(patched_collection, stations):
    _find_objects("SE-Htm", collection="10.18160/S6HM-CP8Q", product="l2")

    assert f"VALUES ?station {{ <{stations[0].uri}> }}" in patched_collection["sparql"]


def test_find_objects_requires_station_or_collection(patched_objects):
    with pytest.raises(ValueError, match="station, a collection"):
        _find_objects(product="l2")
