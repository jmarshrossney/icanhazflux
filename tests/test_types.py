import pytest

from icanhazflux.types import (
    AmbiguousDataType,
    DataTypeNotFound,
    _is_sensitive_product,
    match_product,
)


def test_preset_l2(datatypes):
    hits = match_product(datatypes, "l2")
    assert len(hits) == 1
    assert hits[0].label == "ETC L2 Fluxnet (half-hourly)"


def test_preset_fluxnet_alias(datatypes):
    assert (
        match_product(datatypes, "fluxnet")[0].label == "ETC L2 Fluxnet (half-hourly)"
    )


def test_preset_meteo_excludes_meteosens(datatypes):
    hits = match_product(datatypes, "meteo")
    assert len(hits) == 1
    assert hits[0].label == "ETC L2 Meteo"


def test_preset_raw_substring(datatypes):
    hits = match_product(datatypes, "raw")
    labels = {h.label for h in hits}
    assert "ICOS ETC Eddy Flux Raw ASCII daily archive" in labels
    assert "ICOS ETC Eddy Flux Raw binary daily archive" in labels
    assert len(hits) == 2


def test_preset_nrt(datatypes):
    hits = match_product(datatypes, "nrt")
    assert len(hits) == 1
    assert "NRT Fluxnet" in hits[0].label


def test_preset_archive(datatypes):
    hits = match_product(datatypes, "archive")
    assert len(hits) == 1
    assert hits[0].label == "ETC L2 ARCHIVE"


def test_preset_fluxes(datatypes):
    assert match_product(datatypes, "fluxes")[0].label == "ETC L2 Fluxes"


def test_exact_label(datatypes):
    hits = match_product(datatypes, "ETC L2 Meteosens")
    assert len(hits) == 1
    assert hits[0].label == "ETC L2 Meteosens"


def test_partial_unique(datatypes):
    hits = match_product(datatypes, "meteosens")
    assert len(hits) == 1


def test_partial_ambiguous_non_preset(datatypes):
    with pytest.raises(AmbiguousDataType) as exc:
        match_product(datatypes, "ETC L2")
    assert len(exc.value.matches) > 1


def test_not_found(datatypes):
    with pytest.raises(DataTypeNotFound):
        match_product(datatypes, "quantum gravity fluxes")


def test_preset_empty_catalog():
    with pytest.raises(DataTypeNotFound, match="Preset"):
        match_product([], "l2")


def test_is_sensitive_raw(datatypes):
    raw = match_product(datatypes, "raw")
    assert _is_sensitive_product(raw) is True


def test_is_sensitive_archive(datatypes):
    arch = match_product(datatypes, "archive")
    assert _is_sensitive_product(arch) is True


def test_is_sensitive_l2(datatypes):
    assert _is_sensitive_product(match_product(datatypes, "l2")) is False
