from datetime import datetime
from pathlib import Path

from icoscp_core.icos import auth

from .download import _download_objects, _total_size_bytes
from .objects import DataObject, _find_objects
from .releases import Collection, list_collections, resolve_collection
from .stations import Station, list_stations, resolve_station
from .types import (
    _RAW_WARNING,
    PRODUCT_PRESETS,
    DataType,
    DataTypeInput,
    DataTypeNotFound,
    _is_sensitive_product,
    list_datatypes,
    match_product,
    resolve_product,
)


class Client:
    """Access ICOS ecosystem station metadata and data files."""

    def login(self) -> None:
        """Prompt for Carbon Portal credentials and store them locally."""
        auth.init_config_file()

    def stations(
        self, search: str | None = None, *, refresh: bool = False
    ) -> list[Station]:
        """List ecosystem stations, optionally filtered.

        Args:
            search: Case-insensitive substring matched against station id,
                name, or country code. ``None`` returns all stations.
            refresh: Bypass the local station cache.

        Returns:
            Matching stations, ordered as returned by the portal.
        """
        return list_stations(search=search, refresh=refresh)

    def resolve_station(self, query: str, *, refresh: bool = False) -> Station:
        """Resolve a user query to a single ecosystem station.

        Matching tries exact id, exact name, URI, then a unique partial match.

        Args:
            query: Station id (e.g. ``SE-Htm``), name, or metadata URI.
            refresh: Bypass the local station cache.

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
            refresh: Bypass the local datatype cache.

        Returns:
            Matching datatypes.
        """
        return list_datatypes(search=search, refresh=refresh)

    def resolve_product(self, product: str, *, refresh: bool = False) -> list[DataType]:
        """Resolve a product preset or datatype label to datatypes.

        Known presets are listed in `PRODUCT_PRESETS` (e.g. ``l2``,
        ``meteo``, ``raw``). Non-preset strings match datatype labels
        exactly, then by unique substring.

        Args:
            product: Preset key or datatype label / substring.
            refresh: Bypass the local datatype cache.

        Returns:
            One or more matching datatypes (presets like ``raw`` may
            return several).

        Raises:
            DataTypeNotFound: No datatype matched.
            AmbiguousDataType: Substring matched more than one label.
        """
        return resolve_product(product, refresh=refresh)

    def products(self, *, refresh: bool = False) -> dict[str, list[str]]:
        """Map each product preset to its matching datatype labels.

        Args:
            refresh: Bypass the local datatype cache.

        Returns:
            Mapping of preset name to matching datatype labels.
        """
        types = list_datatypes(refresh=refresh)
        out: dict[str, list[str]] = {}
        for name in PRODUCT_PRESETS:
            try:
                out[name.value] = [t.label for t in match_product(types, name)]
            except DataTypeNotFound:
                out[name.value] = []
        return out

    def collections(
        self, search: str | None = None, *, refresh: bool = False
    ) -> list[Collection]:
        """List DOI collections that contain ecosystem data, such as ETC releases.

        Args:
            search: Case-insensitive substring matched against title or DOI.
                ``None`` returns all collections.
            refresh: Bypass the local collection cache.

        Returns:
            Matching collections, ordered by title.
        """
        return list_collections(search=search, refresh=refresh)

    def resolve_collection(self, query: str, *, refresh: bool = False) -> str:
        """Resolve a collection URI or DOI to a collection URI.

        A collection URI resolves if it is a listed ecosystem collection, and
        is returned normalised to https. A DOI, bare or as a ``doi.org`` URL,
        resolves only if exactly one collection has it. Several collections
        can share a DOI and hold different files, so pass the URI when
        reproducibility matters. On a miss the collection list is refetched
        once, so a release published since the cache was filled is found.

        Args:
            query: Collection URI, DOI, or ``doi.org`` URL.
            refresh: Bypass the local collection cache.

        Returns:
            The collection URI.

        Raises:
            CollectionNotFound: No collection matched.
            AmbiguousCollection: The DOI is shared by several collections.
        """
        return resolve_collection(query, refresh=refresh)

    def find(
        self,
        station: str | Station | None = None,
        *,
        collection: str | None = None,
        product: str | None = "l2",
        datatype: DataTypeInput | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        limit: int = 1000,
        include_deprecated: bool = False,
        refresh: bool = False,
    ) -> list[DataObject]:
        """List data objects for a station, a collection, or both.

        With ``collection``, only the collection's members are returned,
        including superseded versions, and ``station``, ``product``,
        ``datatype`` and the time bounds filter within it.

        Time bounds use observation-period overlap: an object is included
        if its coverage intersects ``[start, end]``. Date-only strings
        are interpreted as start-of-day (``start``) and end-of-day
        (``end``) UTC.

        Args:
            station: Station id, name, URI, or a `Station`. Required unless
                ``collection`` is given.
            collection: Collection URI, or a DOI held by exactly one
                collection (see `Client.resolve_collection`).
            product: Product preset (default ``l2``). Ignored when
                ``datatype`` is set.
            datatype: Datatype label, URI list, or a `DataType`
                list. Overrides ``product`` when given.
            start: Include objects whose coverage extends past this instant.
                Date-only values are treated as start-of-day UTC.
            end: Include objects whose coverage begins before this instant.
                Date-only values are treated as end-of-day UTC.
            limit: Maximum number of objects to return. Results beyond it
                are dropped without warning. Collection queries are capped
                at 10000.
            include_deprecated: If True, include superseded versions.
                Implied by ``collection``.
            refresh: Bypass station and datatype caches.

        Returns:
            Matching data objects, ordered by filename.

        Raises:
            ValueError: Neither ``station`` nor ``collection`` was given.
            StationNotFound: Station query failed.
            AmbiguousStation: Station query was ambiguous.
            CollectionNotFound: Collection query failed.
            AmbiguousCollection: The DOI is shared by several collections.
            DataTypeNotFound: Product/datatype query failed.
            AmbiguousDataType: Product/datatype query was ambiguous.
        """
        _, objs = _find_objects(
            station,
            collection=collection,
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

        Requires prior `login`. Existing files with the same name are
        overwritten. Files from different releases often share a name, so use
        a separate ``out`` directory per release.

        Args:
            objects: Objects to download (e.g. from `find`).
            out: Destination directory (created if missing).
            progress: Print per-file progress to stdout.

        Returns:
            Paths of the saved files.
        """
        return _download_objects(objects, out, progress=progress)

    def get(
        self,
        station: str | Station | None = None,
        *,
        collection: str | None = None,
        product: str | None = "l2",
        datatype: DataTypeInput | None = None,
        start: str | datetime | None = None,
        end: str | datetime | None = None,
        out: str | Path = ".",
        limit: int = 1000,
        refresh: bool = False,
        progress: bool = True,
    ) -> list[Path]:
        """Find and download data objects in one step.

        This is equivalent to `find` followed by `download`. Existing files
        with the same name are overwritten; use a separate ``out`` directory
        per release.

        Args:
            station: Station id, name, URI, or a `Station`. Required unless
                ``collection`` is given.
            collection: Collection URI, or a DOI held by exactly one
                collection (see `Client.resolve_collection`).
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
            refresh: Bypass station and datatype caches.
            progress: Print progress and policy warnings.

        Returns:
            Paths of the saved files.
        """
        types, objs = _find_objects(
            station,
            collection=collection,
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
        """Return the combined size of data objects in bytes."""
        return _total_size_bytes(objects)
