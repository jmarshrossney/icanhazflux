import re

import pytest
from icoscp_core.queries.dataobjlist import (
    TimeFilter,
    dataobj_lite_list,
    parse_dobj_lite,
)
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
    resolve_collection,
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


def test_match_listed_uri_normalised(collections):
    assert match_collection(collections, R2025.replace("https://", "http://")) == R2025


def test_match_unlisted_uri_not_found(collections):
    with pytest.raises(CollectionNotFound, match="No ecosystem collection with URI"):
        match_collection(collections, "https://meta.icos-cp.eu/collections/typo")


def test_match_doi_dedupes_repeated_uri(collections):
    r2025 = collections[0]
    assert match_collection([r2025, r2025], r2025.doi) == R2025


def test_collection_is_hashable(collections):
    assert len(set(collections)) == len(collections)


@pytest.fixture
def listing(monkeypatch, collections):
    """Stub list_collections: a stale cache without r2025, a fresh fetch with it."""
    from icanhazflux import releases

    calls = []

    def fake_list(*, search=None, refresh=False):
        calls.append(refresh)
        return collections if refresh else collections[1:]

    monkeypatch.setattr(releases, "list_collections", fake_list)
    return calls


@pytest.mark.parametrize("query", [R2025, "10.18160/S6HM-CP8Q"])
def test_resolve_refetches_once_on_miss(listing, query):
    assert resolve_collection(query) == R2025
    assert listing == [False, True]


def test_resolve_does_not_refetch_non_identifier(listing):
    with pytest.raises(CollectionNotFound, match="neither"):
        resolve_collection("release 2025-1")
    assert listing == [False]


def test_resolve_with_refresh_does_not_refetch_again(listing):
    with pytest.raises(CollectionNotFound):
        resolve_collection("10.18160/NOPE", refresh=True)
    assert listing == [True]


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
    base = "https://meta.icos-cp.eu/collections/"

    def row(slug, *prevs):
        return {
            "coll": BoundUri(base + slug),
            "title": BoundLiteral(f"release {slug}", None),
            "doi": BoundLiteral("10.1/x", None),
            "n": BoundLiteral("3", "http://www.w3.org/2001/XMLSchema#integer"),
            # group_concat binds an empty string when there is no predecessor.
            "prevs": BoundLiteral(" ".join(base + p for p in prevs), None),
        }

    out = {
        d["uri"].rsplit("/", 1)[1]: d
        for d in _parse_collections([row("a"), row("b"), row("c", "a", "b")])
    }
    assert out["a"]["next_versions"] == [base + "c"]
    assert out["b"]["next_versions"] == [base + "c"]
    assert out["c"]["previous_versions"] == (base + "a", base + "b")
    assert out["c"]["next_versions"] == []
    assert out["a"]["previous_versions"] == ()
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
    assert '?spec cpmeta:hasDataTheme/rdfs:label "Ecosystem data"' in q
    assert "isNextVersionOf" not in q
    assert q.rstrip().endswith("limit 50")


def test_collection_objects_query_without_station_is_optional():
    q = _collection_objects_query(R2025)
    assert "VALUES" not in q
    assert "OPTIONAL { ?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith" in q
    assert "FILTER" not in q


def test_collection_objects_query_always_restricts_theme():
    q = _collection_objects_query(R2025)
    assert '?spec cpmeta:hasDataTheme/rdfs:label "Ecosystem data"' in q


def test_collection_objects_query_caps_limit():
    assert (
        _collection_objects_query(R2025, limit=50000).rstrip().endswith("limit 10000")
    )


def _select_vars(query: str) -> list[str]:
    m = re.search(r"^select (.+)$", query, re.MULTILINE | re.IGNORECASE)
    assert m is not None
    return re.findall(r"\?(\w+)", m.group(1))


def test_collection_objects_query_matches_upstream_select():
    """Our query is a copy of icoscp_core's; fail if upstream's SELECT moves."""
    upstream = dataobj_lite_list(None, None, [], False, None, 10, 0)
    assert _select_vars(_collection_objects_query(R2025)) == _select_vars(upstream)


def test_collection_objects_rows_parse_with_upstream_parser():
    xsd = "http://www.w3.org/2001/XMLSchema#"
    typed = {
        "dobj": BoundUri("https://meta.icos-cp.eu/objects/x"),
        "spec": BoundUri("http://meta.icos-cp.eu/resources/cpmeta/etcL2Fluxnet"),
        "station": BoundUri("http://meta.icos-cp.eu/resources/stations/ES_BE-Bra"),
        "samplingHeight": BoundLiteral("2.0", xsd + "float"),
        "fileName": BoundLiteral("x.zip", None),
        "size": BoundLiteral("10", xsd + "long"),
        "submTime": BoundLiteral("2025-01-01T00:00:00Z", xsd + "dateTime"),
        "timeStart": BoundLiteral("2024-01-01T00:00:00Z", xsd + "dateTime"),
        "timeEnd": BoundLiteral("2024-12-31T00:00:00Z", xsd + "dateTime"),
    }
    row = {v: typed[v] for v in _select_vars(_collection_objects_query(R2025))}
    assert parse_dobj_lite(row).filename == "x.zip"
