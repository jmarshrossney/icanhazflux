from typer.testing import CliRunner

from icanhazflux.cli import app
from icanhazflux.stations import AmbiguousStation, Station, StationNotFound

runner = CliRunner()


def _station(id: str = "SE-Htm", name: str = "Hyltemossa") -> Station:
    return Station(
        uri=f"http://meta.icos-cp.eu/resources/stations/ES_{id}",
        id=id,
        name=name,
        country_code="SE",
        lat=56.1,
        lon=13.4,
        elevation=115.0,
    )


class FakeClient:
    def __init__(self, stations=None, objects=None, types=None):
        self._stations = stations or [_station()]
        self._objects = objects or []
        self._types = types or []

    def stations(self, search=None, *, refresh=False):
        if not search:
            return self._stations
        q = search.casefold()
        return [
            s for s in self._stations if q in s.id.casefold() or q in s.name.casefold()
        ]

    def resolve_station(self, query, *, refresh=False):
        q = query.casefold()
        hits = [
            s for s in self._stations if s.id.casefold() == q or q in s.name.casefold()
        ]
        if len(hits) == 1:
            return hits[0]
        if len(hits) > 1:
            raise AmbiguousStation(query, hits)
        raise StationNotFound(f"No ecosystem station matching {query!r}")

    def find(self, station, **kwargs):
        return self._objects

    def download(self, objects, out, *, progress=True):
        return []

    def datatypes(self, search=None, *, refresh=False):
        return self._types


def test_sites_lists_stations(monkeypatch, stations):
    fake = FakeClient(stations=stations)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    result = runner.invoke(app, ["sites", "--search", "hylte"])
    assert result.exit_code == 0
    assert "SE-Htm" in result.stdout
    assert "Hyltemossa" in result.stdout


def test_list_unknown_site(monkeypatch):
    fake = FakeClient(stations=[_station()])
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: [],
    )
    result = runner.invoke(app, ["list", "ZZ-Zzz"])
    assert result.exit_code == 1
    assert (
        "No ecosystem station" in result.stdout
        or "No ecosystem station" in result.stderr
    )


def test_list_success(monkeypatch, sample_objects, datatypes):
    from icanhazflux.types import match_product

    fake = FakeClient(stations=[_station()], objects=sample_objects)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: match_product(datatypes, key),
    )
    result = runner.invoke(app, ["list", "SE-Htm", "--product", "l2"])
    assert result.exit_code == 0
    assert "SE-Htm" in result.stdout
    assert "ICOSETC_SE-Htm_FLUXNET_HH.zip" in result.stdout
    assert "ETC L2 Fluxnet" in result.stdout
