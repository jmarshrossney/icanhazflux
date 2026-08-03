from datetime import datetime
from pathlib import Path

from icoscp_core.icos import auth

from .download import _download_objects, _total_size_bytes
from .objects import DataObject, _find_objects
from .stations import Station, list_stations, resolve_station
from .types import (
    _RAW_WARNING,
    PRODUCT_PRESETS,
    DataType,
    DataTypeNotFound,
    _is_sensitive_product,
    list_datatypes,
    match_product,
    resolve_product,
)


class Client:
    """Facade over ``icoscp_core`` for ICOS ecosystem station data.

    Use this class for discovery (no auth) and downloads (auth required).
    Station and datatype lists are cached under ``~/.cache/icanhazflux/``.
    """

    def login(self) -> None:
        """Prompt for ICOS Carbon Portal credentials and store them locally.

        Credentials are written via ``icoscp_core`` to the user config
        directory. Accept the CC BY 4.0 licence in your portal profile
        before downloading data.
        """
        auth.init_config_file()

    def stations(
        self, search: str | None = None, *, refresh: bool = False
    ) -> list[Station]:
        """List ecosystem stations, optionally filtered.

        Args:
            search: Case-insensitive substring matched against station id,
                name, or country code. ``None`` returns all stations.
            refresh: If True, bypass the local station cache.

        Returns:
            Matching stations, ordered as returned by the portal.
        """
        return list_stations(search=search, refresh=refresh)

    def resolve_station(self, query: str, *, refresh: bool = False) -> Station:
        """Resolve a user query to a single ecosystem station.

        Resolution order: exact id, exact name, URI, then unique partial
        match on id or name (all case-insensitive).

        Args:
            query: Station id (e.g. ``SE-Htm``), name, or metadata URI.
            refresh: If True, bypass the local station cache.

        Returns:
            The unique matching station.

        Raises:
            StationNotFound: No station matched.
            AmbiguousStation: More than one station matched.
        """
        return resolve_station(query, refresh=refresh)

    def datatypes(
        self, search: str | None = None, *, refresh: bool = False
    ) -> list[DataType]:
        """List ecosystem datatypes, optionally filtered.

        Args:
            search: Case-insensitive substring matched against label,
                project, or format. ``None`` returns all ecosystem types.
            refresh: If True, bypass the local datatype cache.

        Returns:
            Matching datatypes.
        """
        return list_datatypes(search=search, refresh=refresh)

    def resolve_product(self, product: str, *, refresh: bool = False) -> list[DataType]:
        """Resolve a product preset name or datatype label to datatypes.

        Known presets are listed in `PRODUCT_PRESETS` (e.g. ``l2``,
        ``meteo``, ``raw``). Non-preset strings match datatype labels
        exactly, then by unique substring.

        Args:
            product: Preset key or datatype label / substring.
            refresh: If True, bypass the local datatype cache.

        Returns:
            One or more matching datatypes (presets like ``raw`` may
            return several).

        Raises:
            DataTypeNotFound: No datatype matched.
            AmbiguousDataType: Substring matched more than one label.
        """
        return resolve_product(product, refresh=refresh)

    def products(self, *, refresh: bool = False) -> dict[str, list[str]]:
        """Map each product preset to the datatype labels it currently resolves to.

        Presets resolve against the live catalog, so a preset that matches
        nothing (e.g. after a portal rename) maps to an empty list rather
        than raising.

        Args:
            refresh: If True, bypass the local datatype cache.

        Returns:
            Mapping of preset name to matching datatype labels.
        """
        types = list_datatypes(refresh=refresh)
        out: dict[str, list[str]] = {}
        for name in PRODUCT_PRESETS:
            try:
                out[name] = [t.label for t in match_product(types, name)]
            except DataTypeNotFound:
                out[name] = []
        return out

    def find(
        self,
        station: str | Station,
        *,
        product: str | None = "l2",
        datatype: str | list[str] | list[DataType] | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit: int = 1000,
        include_deprecated: bool = False,
        refresh: bool = False,
    ) -> list[DataObject]:
        """List data objects for a station (metadata only; no auth).

        Time bounds use observation-period overlap: an object is included
        if its coverage intersects ``[start, end]``. Date-only strings
        are interpreted as start-of-day (``start``) and end-of-day
        (``end``) UTC.

        Args:
            station: Station id, name, URI, or a `Station`.
            product: Product preset (default ``l2``). Ignored when
                ``datatype`` is set.
            datatype: Datatype label, URI list, or a `DataType`
                list. Overrides ``product`` when given.
            start: Include objects whose coverage extends past this instant.
                Date-only values are treated as start-of-day UTC.
            end: Include objects whose coverage begins before this instant.
                Date-only values are treated as end-of-day UTC.
            limit: Maximum number of objects to return.
            include_deprecated: If True, include superseded versions.
            refresh: If True, bypass station/datatype caches.

        Returns:
            Matching data objects, ordered by filename.

        Raises:
            StationNotFound: Station query failed.
            AmbiguousStation: Station query was ambiguous.
            DataTypeNotFound: Product/datatype query failed.
            AmbiguousDataType: Product/datatype query was ambiguous.
        """
        _, objs = _find_objects(
            station,
            product=product,
            datatype=datatype,
            start=start,
            end=end,
            limit=limit,
            include_deprecated=include_deprecated,
            refresh=refresh,
        )
        return objs

    def download(
        self,
        objects: list[DataObject],
        out: str | Path = ".",
        *,
        progress: bool = True,
    ) -> list[Path]:
        """Download data objects as original portal files.

        Requires prior `login` (or an existing ``icoscp_core``
        credentials file). Overwrites existing files with the same name.

        Args:
            objects: Objects to download (e.g. from `find`).
            out: Destination directory (created if missing).
            progress: If True, print per-file progress to stdout.

        Returns:
            Paths of the saved files.
        """
        return _download_objects(objects, out, progress=progress)

    def get(
        self,
        station: str | Station,
        *,
        product: str | None = "l2",
        datatype: str | list[str] | list[DataType] | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        out: str | Path = ".",
        limit: int = 1000,
        refresh: bool = False,
        progress: bool = True,
    ) -> list[Path]:
        """Find and download data objects in one step.

        Equivalent to `find` followed by `download`. Prints a
        warning when the resolved product looks like raw or archive data.

        Args:
            station: Station id, name, URI, or a `Station`.
            product: Product preset (default ``l2``). Ignored when
                ``datatype`` is set.
            datatype: Datatype label, URI list, or a `DataType`
                list. Overrides ``product`` when given.
            start: Include objects whose coverage extends past this instant.
                Date-only values are treated as start-of-day UTC.
            end: Include objects whose coverage begins before this instant.
                Date-only values are treated as end-of-day UTC.
            out: Destination directory (created if missing).
            limit: Maximum number of objects to download.
            refresh: If True, bypass station/datatype caches.
            progress: If True, print progress and policy warnings.

        Returns:
            Paths of the saved files.
        """
        types, objs = _find_objects(
            station,
            product=product,
            datatype=datatype,
            start=start,
            end=end,
            limit=limit,
            refresh=refresh,
        )
        if progress and types and _is_sensitive_product(types):
            print(_RAW_WARNING)
        return self.download(objs, out, progress=progress)

    @staticmethod
    def total_size_bytes(objects: list[DataObject]) -> int:
        """Sum the byte sizes of data objects.

        Args:
            objects: Objects whose sizes to sum.

        Returns:
            Total size in bytes.
        """
        return _total_size_bytes(objects)
