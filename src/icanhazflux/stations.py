from dataclasses import asdict, dataclass

from icoscp_core.icos import ECO_STATION, meta
from icoscp_core.queries.stationlist import StationLite

from . import cache


@dataclass(frozen=True)
class Station:
    """An ICOS ecosystem measurement station.

    Attributes:
        uri: Station metadata URI.
        id: Network station id (e.g. ``SE-Htm``).
        name: Human-readable station name.
        country_code: ISO 3166-1 alpha-2 country code.
        lat: WGS-84 latitude of the principal location, if known.
        lon: WGS-84 longitude of the principal location, if known.
        elevation: Elevation above sea level in metres, if known.
    """

    uri: str
    id: str
    name: str
    country_code: str
    lat: float | None
    lon: float | None
    elevation: float | None

    @classmethod
    def from_lite(cls, s: StationLite) -> "Station":
        return cls(
            uri=s.uri,
            id=s.id,
            name=s.name,
            country_code=s.country_code,
            lat=s.lat,
            lon=s.lon,
            elevation=s.elevation,
        )

    @classmethod
    def from_dict(cls, d: dict) -> "Station":
        return cls(
            uri=d["uri"],
            id=d["id"],
            name=d["name"],
            country_code=d["country_code"],
            lat=d.get("lat"),
            lon=d.get("lon"),
            elevation=d.get("elevation"),
        )


class StationNotFound(LookupError):
    """Raised when no ecosystem station matches a query."""


class AmbiguousStation(LookupError):
    """Raised when more than one ecosystem station matches a query.

    Attributes:
        query: The original query string.
        matches: All stations that matched.
    """

    def __init__(self, query: str, matches: list[Station]) -> None:
        self.query = query
        self.matches = matches
        ids = ", ".join(m.id for m in matches)
        super().__init__(f"Ambiguous station {query!r}: {ids}")


def _fetch_stations() -> list[dict]:
    return [asdict(Station.from_lite(s)) for s in meta.list_stations(ECO_STATION)]


def list_stations(*, search: str | None = None, refresh: bool = False) -> list[Station]:
    """List ecosystem stations. Prefer ``Client.stations`` in application code."""
    raw = cache.get_or_fetch("stations", _fetch_stations, refresh=refresh)
    stations = [Station.from_dict(d) for d in raw]
    if not search:
        return stations
    q = search.casefold()
    return [
        s
        for s in stations
        if q in s.id.casefold()
        or q in s.name.casefold()
        or q in s.country_code.casefold()
    ]


def match_station(stations: list[Station], query: str) -> Station:
    """Resolve query against an in-memory station list (pure, package-internal)."""
    q = query.strip()
    qf = q.casefold()

    exact_id = [s for s in stations if s.id.casefold() == qf]
    if len(exact_id) == 1:
        return exact_id[0]
    if len(exact_id) > 1:
        raise AmbiguousStation(query, exact_id)

    exact_name = [s for s in stations if s.name.casefold() == qf]
    if len(exact_name) == 1:
        return exact_name[0]
    if len(exact_name) > 1:
        raise AmbiguousStation(query, exact_name)

    if q.startswith(("http://", "https://")):
        uri_hits = [
            s
            for s in stations
            if s.uri == q or s.uri.replace("http://", "https://") == q
        ]
        if len(uri_hits) == 1:
            return uri_hits[0]
        if len(uri_hits) > 1:
            raise AmbiguousStation(query, uri_hits)

    partial = [s for s in stations if qf in s.id.casefold() or qf in s.name.casefold()]
    if len(partial) == 1:
        return partial[0]
    if len(partial) > 1:
        raise AmbiguousStation(query, partial)
    raise StationNotFound(f"No ecosystem station matching {query!r}")


def resolve_station(query: str, *, refresh: bool = False) -> Station:
    """Resolve a station query. Prefer ``Client.resolve_station`` in application code."""
    return match_station(list_stations(refresh=refresh), query)
