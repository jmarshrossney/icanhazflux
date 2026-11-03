from datetime import UTC, datetime

import pytest

from icanhazflux.objects import DataObject
from icanhazflux.releases import Collection
from icanhazflux.stations import Station
from icanhazflux.types import DataType


def _station(
    id: str,
    name: str,
    *,
    country: str = "SE",
    uri: str | None = None,
) -> Station:
    return Station(
        uri=uri or f"http://meta.icos-cp.eu/resources/stations/ES_{id}",
        id=id,
        name=name,
        country_code=country,
        lat=56.0,
        lon=13.0,
        elevation=100.0,
    )


def _dtype(
    label: str,
    *,
    uri: str | None = None,
    level: int = 2,
    access: bool = True,
) -> DataType:
    slug = label.lower().replace(" ", "-")
    return DataType(
        uri=uri or f"http://meta.icos-cp.eu/resources/cpmeta/{slug}",
        label=label,
        data_level=level,
        has_data_access=access,
        theme="Ecosystem data",
        project="ICOS",
        format="CSV",
    )


@pytest.fixture
def stations() -> list[Station]:
    return [
        _station("SE-Htm", "Hyltemossa"),
        _station("SE-Nor", "Norunda"),
        _station("SE-Deg", "Degero"),
        _station("DE-Tha", "Tharandt", country="DE"),
        _station("FR-Pue", "Puechabon", country="FR"),
    ]


@pytest.fixture
def datatypes() -> list[DataType]:
    return [
        _dtype("ETC L2 Fluxnet (half-hourly)", level=2, access=True),
        _dtype("ETC L2 Fluxes", level=2, access=True),
        _dtype("ETC L2 Meteo", level=2, access=True),
        _dtype("ETC L2 Meteosens", level=2, access=True),
        _dtype("ETC NRT Fluxnet (half-hourly)", level=1, access=True),
        _dtype("ETC L2 ARCHIVE", level=2, access=False),
        _dtype("ICOS ETC Eddy Flux Raw ASCII daily archive", level=0, access=False),
        _dtype("ICOS ETC Eddy Flux Raw binary daily archive", level=0, access=False),
        _dtype("Fluxnet Product", level=2, access=True),
    ]


@pytest.fixture
def sample_objects() -> list[DataObject]:
    ts = datetime(2024, 1, 1, tzinfo=UTC)
    te = datetime(2024, 12, 31, tzinfo=UTC)
    sub = datetime(2025, 1, 15, tzinfo=UTC)
    return [
        DataObject(
            uri="http://meta.icos-cp.eu/objects/abc",
            filename="ICOSETC_SE-Htm_FLUXNET_HH.zip",
            size_bytes=10 * 1024 * 1024,
            datatype_uri="http://meta.icos-cp.eu/resources/cpmeta/etc-l2-fluxnet",
            station_uri="http://meta.icos-cp.eu/resources/stations/ES_SE-Htm",
            submission_time=sub,
            time_start=ts,
            time_end=te,
        )
    ]


def _collection(
    slug: str,
    doi: str,
    *,
    title: str = "Ecosystem final quality (L2) product - release 2026-1",
    n: int = 10,
    prev: str | None = None,
    nexts: list[str] | None = None,
) -> Collection:
    return Collection(
        uri=f"https://meta.icos-cp.eu/collections/{slug}",
        title=title,
        doi=doi,
        n_objects=n,
        previous_version=prev,
        next_versions=nexts or [],
    )


@pytest.fixture
def collections() -> list[Collection]:
    old = "https://meta.icos-cp.eu/collections/old2026"
    new = "https://meta.icos-cp.eu/collections/new2026"
    return [
        _collection(
            "r2025",
            "10.18160/S6HM-CP8Q",
            title="Ecosystem final quality (L2) product - release 2025-1",
            n=423,
        ),
        _collection("old2026", "10.18160/S6TB-567H", n=210, nexts=[new]),
        _collection("new2026", "10.18160/S6TB-567H", n=470, prev=old),
    ]
