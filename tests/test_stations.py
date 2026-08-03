import pytest

from icanhazflux.stations import AmbiguousStation, StationNotFound, match_station


def test_exact_id(stations):
    s = match_station(stations, "SE-Htm")
    assert s.id == "SE-Htm"
    assert s.name == "Hyltemossa"


def test_exact_id_case_insensitive(stations):
    assert match_station(stations, "se-htm").id == "SE-Htm"


def test_exact_name(stations):
    assert match_station(stations, "Hyltemossa").id == "SE-Htm"


def test_exact_name_case_insensitive(stations):
    assert match_station(stations, "hyltemossa").id == "SE-Htm"


def test_uri(stations):
    uri = stations[0].uri
    assert match_station(stations, uri).id == "SE-Htm"


def test_uri_https_variant(stations):
    https = stations[0].uri.replace("http://", "https://")
    assert match_station(stations, https).id == "SE-Htm"


def test_partial_unique(stations):
    assert match_station(stations, "hylte").id == "SE-Htm"


def test_partial_ambiguous(stations):
    with pytest.raises(AmbiguousStation) as exc:
        match_station(stations, "SE-")
    assert len(exc.value.matches) >= 2
    assert {m.id for m in exc.value.matches} >= {"SE-Htm", "SE-Nor", "SE-Deg"}


def test_not_found(stations):
    with pytest.raises(StationNotFound, match="No ecosystem station"):
        match_station(stations, "ZZ-Zzz")


def test_strips_whitespace(stations):
    assert match_station(stations, "  SE-Htm  ").id == "SE-Htm"


def test_id_preferred_over_partial_name(stations):
    # exact id wins even if another name partially matches
    assert match_station(stations, "SE-Nor").name == "Norunda"
