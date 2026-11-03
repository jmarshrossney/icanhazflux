import pytest
from icoscp_core.queries.dataobjlist import TimeFilter
from icoscp_core.sparql import BoundLiteral, BoundUri

from icanhazflux import cache
from icanhazflux.releases import (
    AmbiguousCollection,
    CollectionNotFound,
    _collection_objects_query,
    _parse_collections,
    list_collections,
    match_collection,
    normalise_collection_uri,
    normalise_doi,
)

R2025 = "https://meta.icos-cp.eu/collections/r2025"


@pytest.mark.parametrize(
    "query",
    [
        "10.18160/S6HM-CP8Q",
        "10.18160/s6hm-cp8q",
        "doi:10.18160/S6HM-CP8Q",
        "https://doi.org/10.18160/S6HM-CP8Q",
        "HTTPS://DOI.ORG/10.18160/S6HM-CP8Q",
        "http://dx.doi.org/10.18160/S6HM-CP8Q",
        "  10.18160/S6HM-CP8Q  ",
    ],
)
def test_normalise_doi_forms(query):
    assert normalise_doi(query) == "10.18160/s6hm-cp8q"


@pytest.mark.parametrize("query", ["release 2025-1", "", "https://example.org/x"])
def test_normalise_doi_rejects_non_doi(query):
    assert normalise_doi(query) is None


@pytest.mark.parametrize(
    "query",
    [
        "https://meta.icos-cp.eu/collections/1-HA2r4l5QUjAgQr5CCEfJe3",
        "http://meta.icos-cp.eu/collections/1-HA2r4l5QUjAgQr5CCEfJe3",
        "https://meta.icos-cp.eu/collections/1-HA2r4l5QUjAgQr5CCEfJe3/",
    ],
)
def test_normalise_collection_uri_to_https(query):
    assert (
        normalise_collection_uri(query)
        == "https://meta.icos-cp.eu/collections/1-HA2r4l5QUjAgQr5CCEfJe3"
    )


def test_normalise_collection_uri_rejects_object_uri():
    assert normalise_collection_uri("https://meta.icos-cp.eu/objects/abc") is None


def test_match_uri_passthrough_without_listing():
    uri = "http://meta.icos-cp.eu/collections/unlisted"
    assert match_collection([], uri) == uri.replace("http://", "https://")


def test_match_unique_doi(collections):
    assert match_collection(collections, "https://doi.org/10.18160/S6HM-CP8Q") == R2025


def test_match_shared_doi_is_ambiguous(collections):
    with pytest.raises(AmbiguousCollection) as exc:
        match_collection(collections, "10.18160/S6TB-567H")
    assert {m.n_objects for m in exc.value.matches} == {210, 470}
    assert "new2026" in str(exc.value)


def test_match_unknown_doi(collections):
    with pytest.raises(CollectionNotFound, match="No ecosystem collection"):
        match_collection(collections, "10.18160/NOPE")


def test_match_neither_uri_nor_doi(collections):
    with pytest.raises(CollectionNotFound, match="neither"):
        match_collection(collections, "release 2025-1")


def test_parse_collections_derives_next_versions():
    def row(slug, prev=None):
        r = {
            "coll": BoundUri(f"https://meta.icos-cp.eu/collections/{slug}"),
            "title": BoundLiteral(f"release {slug}", None),
            "doi": BoundLiteral("10.1/x", None),
            "n": BoundLiteral("3", "http://www.w3.org/2001/XMLSchema#integer"),
        }
        if prev:
            r["prev"] = BoundUri(f"https://meta.icos-cp.eu/collections/{prev}")
        return r

    out = {
        d["uri"].rsplit("/", 1)[1]: d
        for d in _parse_collections([row("a"), row("b", prev="a")])
    }
    assert out["a"]["next_versions"] == ["https://meta.icos-cp.eu/collections/b"]
    assert out["b"]["next_versions"] == []
    assert out["a"]["n_objects"] == 3


def test_list_collections_search_and_cache(monkeypatch, tmp_path, collections):
    from dataclasses import asdict

    from icanhazflux import releases

    monkeypatch.setattr(cache, "cache_dir", lambda: tmp_path)
    calls = []

    def fake_fetch():
        calls.append(1)
        return [asdict(c) for c in collections]

    monkeypatch.setattr(releases, "_fetch_collections", fake_fetch)
    assert list_collections() == collections
    assert [c.uri for c in list_collections(search="2025-1")] == [R2025]
    assert len(list_collections(search="s6tb")) == 2
    assert len(calls) == 1


def test_collection_objects_query_shape():
    q = _collection_objects_query(
        R2025,
        datatype_uris=["https://meta.icos-cp.eu/resources/cpmeta/etcL2Fluxnet"],
        station_uris=["http://meta.icos-cp.eu/resources/stations/ES_BE-Bra"],
        filters=[TimeFilter("timeEnd", ">", "2024-01-01T00:00:00Z")],
        limit=50,
    )
    assert f"<{R2025}> dcterms:hasPart+ ?dobj" in q
    # Specs and stations are http IRIs in the triple store.
    assert (
        "VALUES ?spec { <http://meta.icos-cp.eu/resources/cpmeta/etcL2Fluxnet> }" in q
    )
    assert (
        "VALUES ?station { <http://meta.icos-cp.eu/resources/stations/ES_BE-Bra> }" in q
    )
    assert "OPTIONAL { ?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith" not in q
    assert '?timeEnd > "2024-01-01T00:00:00Z"^^xsd:dateTime' in q
    assert "isNextVersionOf" not in q
    assert q.rstrip().endswith("limit 50")


def test_collection_objects_query_without_station_is_optional():
    q = _collection_objects_query(R2025)
    assert "VALUES" not in q
    assert "OPTIONAL { ?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith" in q
    assert "FILTER" not in q
