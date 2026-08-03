import pytest

from icanhazflux.types import (
    PRODUCT_PRESETS,
    AmbiguousDataType,
    DataTypeNotFound,
    ProductPreset,
    _is_sensitive_product,
    match_label,
    match_product,
)


def test_product_presets_are_str_enums():
    assert ProductPreset.L2 == "l2"
    assert list(PRODUCT_PRESETS) == list(ProductPreset)


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


# match_label must never consult PRODUCT_PRESETS. Every case below uses a query
# that is *also* a preset key, so preset leakage changes the outcome.


def test_match_label_ignores_presets_for_raw(datatypes):
    # The "raw" preset resolves cleanly to the two raw archive types; as a
    # plain label substring "raw" is ambiguous between those same two.
    assert len(match_product(datatypes, "raw")) == 2
    with pytest.raises(AmbiguousDataType):
        match_label(datatypes, "raw")


def test_match_label_ignores_presets_for_archive(datatypes):
    # Preset "archive" is an exact-label rule -> exactly one hit.
    assert match_product(datatypes, "archive")[0].label == "ETC L2 ARCHIVE"
    # As a substring, "archive" also hits both raw daily archives.
    with pytest.raises(AmbiguousDataType) as exc:
        match_label(datatypes, "archive")
    assert len(exc.value.matches) == 3


def test_match_label_preset_key_resolving_uniquely(datatypes):
    # "meteo" is a preset, but as a label substring it is ambiguous between
    # Meteo and Meteosens -- proving the preset table was not consulted.
    assert match_product(datatypes, "meteo")[0].label == "ETC L2 Meteo"
    with pytest.raises(AmbiguousDataType):
        match_label(datatypes, "meteo")


def test_match_label_exact_beats_substring(datatypes):
    hits = match_label(datatypes, "ETC L2 Meteo")
    assert len(hits) == 1
    assert hits[0].label == "ETC L2 Meteo"


def test_match_label_unique_substring(datatypes):
    assert match_label(datatypes, "meteosens")[0].label == "ETC L2 Meteosens"


def test_match_label_case_and_whitespace_insensitive(datatypes):
    assert match_label(datatypes, "  etc l2 meteo  ")[0].label == "ETC L2 Meteo"


def test_match_label_not_found(datatypes):
    with pytest.raises(DataTypeNotFound):
        match_label(datatypes, "nonexistent-datatype")
