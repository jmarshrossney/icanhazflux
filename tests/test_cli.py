import pytest
from typer.testing import CliRunner

from icanhazflux import __version__
from icanhazflux.cli import app
from icanhazflux.releases import match_collection
from icanhazflux.stations import AmbiguousStation, Station, StationNotFound
from icanhazflux.types import match_label, match_product

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
    def __init__(self, stations=None, objects=None, types=None, collections=None):
        self._stations = stations or [_station()]
        self._collections = collections or []
        self._objects = objects or []
        self._types = types or []
        self.find_kwargs = None
        self.find_station = None
        self.downloaded = None
        self.download_error = None

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

    def collections(self, search=None, *, refresh=False):
        if not search:
            return self._collections
        q = search.casefold()
        return [c for c in self._collections if q in c.title.casefold()]

    def resolve_collection(self, query, *, refresh=False):
        return match_collection(self._collections, query)

    def find(self, station, **kwargs):
        self.find_station = station
        self.find_kwargs = kwargs
        return self._objects

    def download(self, objects, out, *, progress=True):
        if self.download_error is not None:
            raise self.download_error
        self.downloaded = (objects, out)
        return [f"/tmp/{o.filename}" for o in objects]

    def datatypes(self, search=None, *, refresh=False):
        return self._types


def test_sites_lists_stations(monkeypatch, stations):
    fake = FakeClient(stations=stations)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    result = runner.invoke(app, ["sites", "--search", "hylte"])
    assert result.exit_code == 0
    assert "SE-Htm" in result.stdout
    assert "Hyltemossa" in result.stdout


def test_objects_unknown_site(monkeypatch):
    fake = FakeClient(stations=[_station()])
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: [],
    )
    result = runner.invoke(app, ["objects", "ZZ-Zzz"])
    assert result.exit_code == 1
    assert (
        "No ecosystem station" in result.stdout
        or "No ecosystem station" in result.stderr
    )


def test_objects_success(monkeypatch, sample_objects, datatypes):
    from icanhazflux.types import match_product

    fake = FakeClient(stations=[_station()], objects=sample_objects)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: match_product(datatypes, key),
    )
    result = runner.invoke(app, ["objects", "SE-Htm", "--product", "l2"])
    assert result.exit_code == 0
    assert "SE-Htm" in result.stdout
    assert "ICOSETC_SE-Htm_FLUXNET_HH.zip" in result.stdout
    assert "ETC L2 Fluxnet" in result.stdout


@pytest.fixture
def wired(monkeypatch, datatypes, sample_objects):
    """Wire a FakeClient plus real preset/label resolution over the fixtures."""
    fake = FakeClient(stations=[_station()], objects=sample_objects, types=datatypes)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: match_product(datatypes, key),
    )
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_label",
        lambda key, refresh=False: match_label(datatypes, key),
    )
    return fake


def test_datatype_flag_matches_label_not_preset(wired):
    """Regression: --datatype must bypass PRODUCT_PRESETS.

    'meteosens' is a plain label; the old code funnelled --datatype through
    the preset table first, so preset-named queries never reached the label
    matcher at all.
    """
    result = runner.invoke(app, ["objects", "SE-Htm", "--datatype", "meteosens"])
    assert result.exit_code == 0
    assert "ETC L2 Meteosens" in result.stdout


def test_datatype_ambiguous_label_lists_candidates(wired):
    """'raw' is a preset key but an ambiguous label -- must report ambiguity."""
    result = runner.invoke(app, ["objects", "SE-Htm", "--datatype", "raw"])
    assert result.exit_code == 1
    combined = result.stdout + result.stderr
    assert "Ambiguous datatype" in combined


def test_product_flag_still_uses_presets(wired):
    result = runner.invoke(app, ["objects", "SE-Htm", "--product", "raw"])
    assert result.exit_code == 0
    assert "Eddy Flux Raw" in result.stdout


def test_datatypes_lists_presets_with_real_labels(wired):
    result = runner.invoke(app, ["datatypes"])
    assert result.exit_code == 0
    assert "ETC L2 Fluxnet (half-hourly)" in result.stdout
    # The internal "~" substring marker must not leak into CLI output.
    assert "~" not in result.stdout


def test_include_deprecated_reaches_find(wired):
    result = runner.invoke(app, ["objects", "SE-Htm", "--include-deprecated"])
    assert result.exit_code == 0
    assert wired.find_kwargs["include_deprecated"] is True


def test_include_deprecated_defaults_false(wired):
    runner.invoke(app, ["objects", "SE-Htm"])
    assert wired.find_kwargs["include_deprecated"] is False


def test_objects_warns_on_raw(wired):
    result = runner.invoke(app, ["objects", "SE-Htm", "--product", "raw"])
    assert "PI consultation" in result.stdout


def test_download_confirms_above_threshold(wired, monkeypatch):
    monkeypatch.setattr("icanhazflux.cli._CONFIRM_THRESHOLD_BYTES", 1)
    result = runner.invoke(app, ["download", "SE-Htm"], input="n\n")
    assert result.exit_code == 1
    assert wired.downloaded is None


def test_download_proceeds_when_confirmed(wired, monkeypatch):
    monkeypatch.setattr("icanhazflux.cli._CONFIRM_THRESHOLD_BYTES", 1)
    result = runner.invoke(app, ["download", "SE-Htm"], input="y\n")
    assert result.exit_code == 0
    assert wired.downloaded is not None


def test_download_yes_skips_confirmation(wired, monkeypatch):
    monkeypatch.setattr("icanhazflux.cli._CONFIRM_THRESHOLD_BYTES", 1)
    result = runner.invoke(app, ["download", "SE-Htm", "--yes"])
    assert result.exit_code == 0
    assert wired.downloaded is not None
    assert "Saved 1 file(s)" in result.stdout


def test_download_no_confirmation_below_threshold(wired):
    result = runner.invoke(app, ["download", "SE-Htm"])
    assert result.exit_code == 0
    assert wired.downloaded is not None


def test_download_no_objects_exits_zero(monkeypatch, datatypes):
    fake = FakeClient(stations=[_station()], objects=[], types=datatypes)
    monkeypatch.setattr("icanhazflux.cli._client", lambda: fake)
    monkeypatch.setattr(
        "icanhazflux.cli.resolve_product",
        lambda key, refresh=False: match_product(datatypes, key),
    )
    result = runner.invoke(app, ["download", "SE-Htm"])
    assert result.exit_code == 0
    assert "No objects found" in result.stdout
    assert fake.downloaded is None


def test_download_failure_reports_and_exits(wired):
    wired.download_error = RuntimeError("401 Unauthorized")
    result = runner.invoke(app, ["download", "SE-Htm", "--yes"])
    assert result.exit_code == 1
    combined = result.stdout + result.stderr
    assert "Download failed" in combined
    assert "401 Unauthorized" in combined


def test_cache_path_prints_directory(monkeypatch, tmp_path):
    monkeypatch.setattr("icanhazflux.cache.cache_dir", lambda: tmp_path)
    result = runner.invoke(app, ["cache", "path"])
    assert result.exit_code == 0
    assert str(tmp_path) in result.stdout


def test_cache_clear_all(monkeypatch, tmp_path):
    monkeypatch.setattr("icanhazflux.cache.cache_dir", lambda: tmp_path)
    (tmp_path / "stations.json").write_text("{}")
    result = runner.invoke(app, ["cache", "clear"])
    assert result.exit_code == 0
    assert list(tmp_path.iterdir()) == []


def test_cache_clear_named(monkeypatch, tmp_path):
    monkeypatch.setattr("icanhazflux.cache.cache_dir", lambda: tmp_path)
    (tmp_path / "stations.json").write_text("{}")
    (tmp_path / "datatypes.json").write_text("{}")
    result = runner.invoke(app, ["cache", "clear", "stations"])
    assert result.exit_code == 0
    assert [p.name for p in tmp_path.iterdir()] == ["datatypes.json"]


def test_version_prints_version():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert __version__ in result.stdout


@pytest.fixture
def wired_collections(wired, collections):
    wired._collections = collections
    return wired


def test_collections_lists_and_marks_superseded(wired_collections):
    result = runner.invoke(app, ["collections"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    assert "10.18160/S6HM-CP8Q" in result.stdout
    assert "r2025" in result.stdout
    assert result.stdout.count("superseded") == 1


def test_collections_no_match_exits_one(wired_collections):
    result = runner.invoke(app, ["collections", "--search", "nope"])
    assert result.exit_code == 1


def test_objects_collection_without_site(wired_collections):
    result = runner.invoke(
        app, ["objects", "--collection", "10.18160/S6HM-CP8Q", "--product", "l2"]
    )
    assert result.exit_code == 0
    assert "Collection: https://meta.icos-cp.eu/collections/r2025" in result.stdout
    assert wired_collections.find_station is None
    assert (
        wired_collections.find_kwargs["collection"]
        == "https://meta.icos-cp.eu/collections/r2025"
    )


def test_objects_collection_with_site(wired_collections):
    result = runner.invoke(app, ["objects", "SE-Htm", "-c", "10.18160/S6HM-CP8Q"])
    assert result.exit_code == 0
    assert wired_collections.find_station.id == "SE-Htm"


def test_objects_ambiguous_doi_lists_uris(wired_collections):
    result = runner.invoke(app, ["objects", "--collection", "10.18160/S6TB-567H"])
    assert result.exit_code == 1
    combined = result.stdout + result.stderr
    assert "old2026" in combined
    assert "new2026" in combined
    assert wired_collections.find_kwargs is None


def test_objects_unknown_collection(wired_collections):
    result = runner.invoke(app, ["objects", "--collection", "release 2025-1"])
    assert result.exit_code == 1
    assert "neither" in result.stdout + result.stderr


def test_objects_requires_site_or_collection(wired):
    result = runner.invoke(app, ["objects"])
    assert result.exit_code == 1
    assert "--collection" in result.stdout + result.stderr


def test_download_collection_without_site(wired_collections):
    result = runner.invoke(
        app, ["download", "--collection", "10.18160/S6HM-CP8Q", "--yes"]
    )
    assert result.exit_code == 0
    assert wired_collections.downloaded is not None
