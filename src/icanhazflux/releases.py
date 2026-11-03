import re
from dataclasses import asdict, dataclass, field

from icoscp_core.icos import meta
from icoscp_core.queries.dataobjlist import Filter
from icoscp_core.sparql import Binding, as_opt_uri, as_string, as_uri

from . import cache
from .types import ECO_THEME

# Collections live under https IRIs in the triple store, whereas stations and
# datatypes use http. A collection IRI with the wrong scheme matches nothing.
_COLLECTION_RE = re.compile(r"^https?://meta\.icos-cp\.eu/collections/([\w-]+)/?$")
_DOI_PREFIXES = (
    "https://doi.org/",
    "http://doi.org/",
    "https://dx.doi.org/",
    "http://dx.doi.org/",
    "doi:",
)

_PREFIXES = """prefix cpmeta: <http://meta.icos-cp.eu/ontologies/cpmeta/>
prefix dcterms: <http://purl.org/dc/terms/>
prefix prov: <http://www.w3.org/ns/prov#>
prefix rdfs: <http://www.w3.org/2000/01/rdf-schema#>
prefix xsd: <http://www.w3.org/2001/XMLSchema#>
"""


@dataclass(frozen=True)
class Collection:
    """A static Carbon Portal collection with a DOI, such as an ETC release.

    The collection URI identifies a fixed set of files. A DOI may be shared by
    several collections, typically a release and a later replacement with
    more files.

    Attributes:
        uri: Collection landing-page URI.
        title: Collection title.
        doi: DOI of the collection, without a resolver prefix.
        n_objects: Number of direct members.
        previous_version: URI of the collection this one replaces, if any.
        next_versions: URIs of listed collections that replace this one.
    """

    uri: str
    title: str
    doi: str
    n_objects: int
    previous_version: str | None = None
    next_versions: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, d: dict) -> "Collection":
        return cls(
            uri=d["uri"],
            title=d["title"],
            doi=d["doi"],
            n_objects=int(d["n_objects"]),
            previous_version=d.get("previous_version"),
            next_versions=list(d.get("next_versions", [])),
        )


class CollectionNotFound(LookupError):
    """Raised when a collection query matches no collection."""


class AmbiguousCollection(LookupError):
    """Raised when a DOI is shared by more than one collection.

    Pass one of the collection URIs instead.

    Attributes:
        query: The original query string.
        matches: All collections with that DOI.
    """

    def __init__(self, query: str, matches: list[Collection]) -> None:
        self.query = query
        self.matches = matches
        uris = ", ".join(m.uri for m in matches)
        super().__init__(
            f"DOI {query!r} is shared by {len(matches)} collections; "
            f"pass one collection URI instead: {uris}"
        )


# The ecosystem filter runs in a subquery: joining it with the member count in
# one pattern times out on the portal.
_COLLECTIONS_QUERY = (
    _PREFIXES
    + f"""
select ?coll ?title ?doi ?prev (count(?member) as ?n)
where {{
    {{
        select distinct ?coll where {{
            ?coll a cpmeta:Collection ; cpmeta:hasDoi [] .
            FILTER EXISTS {{
                ?coll dcterms:hasPart+ ?d .
                ?d cpmeta:hasObjectSpec/cpmeta:hasDataTheme/rdfs:label "{ECO_THEME}" .
            }}
        }}
    }}
    ?coll dcterms:title ?title ; cpmeta:hasDoi ?doi ; dcterms:hasPart ?member .
    OPTIONAL {{ ?coll cpmeta:isNextVersionOf ?prev }}
}}
group by ?coll ?title ?doi ?prev
order by ?title ?coll
"""
)


def _parse_collections(rows: list[Binding]) -> list[dict]:
    """Parse query rows; ``next_versions`` is the inverse of ``previous_version``."""
    colls = [
        Collection(
            uri=as_uri("coll", r),
            title=as_string("title", r),
            doi=as_string("doi", r),
            n_objects=int(as_string("n", r)),
            previous_version=as_opt_uri("prev", r),
        )
        for r in rows
    ]
    nexts: dict[str, list[str]] = {}
    for c in colls:
        if c.previous_version is not None:
            nexts.setdefault(c.previous_version, []).append(c.uri)
    return [asdict(c) | {"next_versions": nexts.get(c.uri, [])} for c in colls]


def _fetch_collections() -> list[dict]:
    return _parse_collections(meta.sparql_select(_COLLECTIONS_QUERY).bindings)


def list_collections(
    *, search: str | None = None, refresh: bool = False
) -> list[Collection]:
    """List DOI collections with ecosystem data. Prefer ``Client.collections``."""
    raw = cache.get_or_fetch("collections", _fetch_collections, refresh=refresh)
    colls = [Collection.from_dict(d) for d in raw]
    if not search:
        return colls
    q = search.casefold()
    return [c for c in colls if q in c.title.casefold() or q in c.doi.casefold()]


def normalise_doi(query: str) -> str | None:
    """Strip resolver prefixes and casefold; ``None`` if not a DOI (internal)."""
    q = query.strip()
    for prefix in _DOI_PREFIXES:
        if q.casefold().startswith(prefix):
            q = q[len(prefix) :]
            break
    q = q.casefold()
    return q if q.startswith("10.") else None


def normalise_collection_uri(query: str) -> str | None:
    """Return the https collection URI, or ``None`` if not one (internal)."""
    m = _COLLECTION_RE.match(query.strip())
    return f"https://meta.icos-cp.eu/collections/{m.group(1)}" if m else None


def match_collection(collections: list[Collection], query: str) -> str:
    """Resolve a collection URI or 1-1 DOI to a collection URI (pure, internal).

    A URI is returned as-is without consulting ``collections``. A DOI must be
    held by exactly one collection; there is no rule to choose between several.
    """
    uri = normalise_collection_uri(query)
    if uri is not None:
        return uri

    doi = normalise_doi(query)
    if doi is None:
        raise CollectionNotFound(
            f"{query!r} is neither a collection URI nor a DOI; "
            "use Client.collections(search=...) to find one"
        )
    hits = [c for c in collections if c.doi.casefold() == doi]
    if len(hits) == 1:
        return hits[0].uri
    if len(hits) > 1:
        raise AmbiguousCollection(query, hits)
    raise CollectionNotFound(f"No ecosystem collection with DOI {query!r}")


def resolve_collection(query: str, *, refresh: bool = False) -> str:
    """Resolve a collection query to a URI. Prefer ``Client.resolve_collection``."""
    if normalise_collection_uri(query) is not None:
        return match_collection([], query)
    return match_collection(list_collections(refresh=refresh), query)


def _values(var: str, uris: list[str]) -> str:
    if not uris:
        return ""
    joined = " ".join(f"<{u.replace('https://', 'http://', 1)}>" for u in uris)
    return f"VALUES ?{var} {{ {joined} }}"


def _collection_objects_query(
    collection_uri: str,
    *,
    datatype_uris: list[str] | None = None,
    station_uris: list[str] | None = None,
    filters: list[Filter] | None = None,
    limit: int = 1000,
) -> str:
    """Build a SPARQL query for the data objects in a collection (internal).

    Selects the same variables as ``icoscp_core``'s data object list so rows
    parse with ``parse_dobj_lite``. Deprecated objects are deliberately kept:
    a past release consists mostly of superseded versions. ``hasPart+``
    flattens nested collections.
    """
    station_uris = station_uris or []
    station_link = "?dobj cpmeta:wasAcquiredBy/prov:wasAssociatedWith ?station ."
    if not station_uris:
        station_link = f"OPTIONAL {{ {station_link} }}"
    rendered = [f.render() for f in filters or []]
    filter_clause = f"FILTER({' && '.join(rendered)})" if rendered else ""
    return (
        _PREFIXES
        + f"""
select ?dobj ?spec ?station ?samplingHeight ?fileName ?size ?submTime ?timeStart ?timeEnd
where {{
    <{collection_uri}> dcterms:hasPart+ ?dobj .
    {_values("spec", datatype_uris or [])}
    ?dobj cpmeta:hasObjectSpec ?spec .
    {_values("station", station_uris)}
    {station_link}
    OPTIONAL {{ ?dobj cpmeta:wasAcquiredBy/cpmeta:hasSamplingHeight ?samplingHeight }}
    ?dobj cpmeta:hasSizeInBytes ?size .
    ?dobj cpmeta:hasName ?fileName .
    ?dobj cpmeta:wasSubmittedBy/prov:endedAtTime ?submTime .
    ?dobj cpmeta:hasStartTime | (cpmeta:wasAcquiredBy / prov:startedAtTime) ?timeStart .
    ?dobj cpmeta:hasEndTime | (cpmeta:wasAcquiredBy / prov:endedAtTime) ?timeEnd .
    {filter_clause}
}}
order by ?fileName
limit {min(limit, 10000)}"""
    )
