from dataclasses import dataclass
from datetime import datetime
from typing import cast

from icoscp_core.icos import meta
from icoscp_core.queries.dataobjlist import DataObjectLite, Filter, TimeFilter

from .stations import Station, resolve_station
from .types import DataType, DataTypeInput, list_datatypes, resolve_product


@dataclass(frozen=True)
class DataObject:
    """A data object available from the Carbon Portal.

    Attributes:
        uri: Landing-page URI of the object.
        filename: Original filename.
        size_bytes: Object size in bytes.
        datatype_uri: URI of the object's datatype specification.
        station_uri: URI of the associated station, if available.
        submission_time: When the object was submitted to the portal.
        time_start: Start of the object's observation coverage.
        time_end: End of the object's observation coverage.
    """

    uri: str
    filename: str
    size_bytes: int
    datatype_uri: str
    station_uri: str | None
    submission_time: datetime
    time_start: datetime
    time_end: datetime

    @classmethod
    def from_lite(cls, o: DataObjectLite) -> "DataObject":
        return cls(
            uri=o.uri,
            filename=o.filename,
            size_bytes=o.size_bytes,
            datatype_uri=o.datatype_uri,
            station_uri=o.station_uri,
            submission_time=o.submission_time,
            time_start=o.time_start,
            time_end=o.time_end,
        )

    @property
    def size_mb(self) -> float:
        """Object size in mebibytes (``size_bytes / 1024**2``)."""
        return self.size_bytes / (1024 * 1024)


def parse_time(
    value: str | datetime | None, *, end_of_day: bool = False
) -> datetime | str | None:
    """Parse CLI/API time strings. Package-internal helper (not part of public API)."""
    if value is None or isinstance(value, datetime):
        return value
    v = value.strip()
    if len(v) == 10 and v[4] == "-" and v[7] == "-":
        return f"{v}T23:59:59Z" if end_of_day else f"{v}T00:00:00Z"
    return v


def build_time_filters(
    start: str | datetime | None = None,
    end: str | datetime | None = None,
) -> list[TimeFilter]:
    """Overlap semantics: object intersects [start, end].

    TimeFilter only supports exclusive < />; date-only end becomes end-of-day.
    Package-internal helper (not part of public API).
    """
    filters: list[TimeFilter] = []
    start_v = parse_time(start)
    end_v = parse_time(end, end_of_day=True)
    if start_v is not None:
        filters.append(TimeFilter("timeEnd", ">", start_v))
    if end_v is not None:
        filters.append(TimeFilter("timeStart", "<", end_v))
    return filters


def _find_objects(
    station: str | Station,
    *,
    product: str | None = None,
    datatype: DataTypeInput | None = None,
    start: str | datetime | None = None,
    end: str | datetime | None = None,
    limit: int = 1000,
    include_deprecated: bool = False,
    refresh: bool = False,
) -> tuple[list[DataType], list[DataObject]]:
    """Resolve a query and run it. Returns the resolved datatypes and the objects.

    ``datatype`` takes precedence over ``product`` when both are given.
    Package-internal helper (not part of the public API).
    """
    st = (
        station
        if isinstance(station, Station)
        else resolve_station(station, refresh=refresh)
    )

    resolved: list[DataType] = []
    dtype_uris: list[str] | None = None
    if datatype is not None:
        if isinstance(datatype, str):
            resolved = resolve_product(datatype, refresh=refresh)
            dtype_uris = [t.uri for t in resolved]
        elif datatype and isinstance(datatype[0], DataType):
            resolved = cast(list[DataType], list(datatype))
            dtype_uris = [t.uri for t in resolved]
        else:
            dtype_uris = list(cast(list[str], datatype))
            # Best-effort reverse lookup so callers can inspect the resolved
            # types (e.g. for the raw-data warning). Unknown URIs still go to
            # the query; they just don't contribute to that check.
            known = {t.uri: t for t in list_datatypes(refresh=refresh)}
            resolved = [known[u] for u in dtype_uris if u in known]
    elif product is not None:
        resolved = resolve_product(product, refresh=refresh)
        dtype_uris = [t.uri for t in resolved]

    filters = build_time_filters(start, end)

    objs = meta.list_data_objects(
        datatype=dtype_uris,
        station=st.uri,
        filters=cast(list[Filter], filters),
        include_deprecated=include_deprecated,
        order_by="fileName",
        limit=limit,
    )
    return resolved, [DataObject.from_lite(o) for o in objs]
