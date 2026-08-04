from dataclasses import asdict, dataclass
from enum import StrEnum

from icoscp_core.icos import meta
from icoscp_core.queries.speclist import DobjSpecLite

from . import cache

ECO_THEME = "Ecosystem data"


class ProductPreset(StrEnum):
    """Friendly product preset names supported by the package."""

    L2 = "l2"
    FLUXNET = "fluxnet"
    FLUXES = "fluxes"
    METEO = "meteo"
    NRT = "nrt"
    RAW = "raw"
    ARCHIVE = "archive"


# Friendly preset → substrings matched against datatype labels (casefold).
# Values are exact labels (casefold) unless prefixed with "~" (substring match).
PRODUCT_PRESETS: dict[ProductPreset, list[str]] = {
    ProductPreset.L2: ["etc l2 fluxnet (half-hourly)"],
    ProductPreset.FLUXNET: ["etc l2 fluxnet (half-hourly)"],
    ProductPreset.FLUXES: ["etc l2 fluxes"],
    ProductPreset.METEO: ["etc l2 meteo"],
    ProductPreset.NRT: ["~etc nrt fluxnet"],
    ProductPreset.RAW: ["~eddy flux raw"],
    ProductPreset.ARCHIVE: ["etc l2 archive"],
}
"""Map of friendly product names to datatype label match rules.

Keys are preset names accepted by `Client.resolve_product` and the
CLI ``--product`` flag (e.g. ``l2``, ``meteo``, ``raw``).

Values are lists of casefolded label patterns: an exact label match
unless the pattern is prefixed with ``~``, which means substring match.
"""

_RAW_WARNING = (
    "Raw / archive eddy-covariance data may require PI consultation "
    "before use. Check the object landing page and data policy."
)


@dataclass(frozen=True)
class DataType:
    """An ICOS ecosystem data object type.

    Attributes:
        uri: Datatype metadata URI.
        label: Human-readable type label.
        data_level: ICOS data level (0 raw … 3 elaborated).
        has_data_access: Whether structured data access is supported.
        theme: Data theme label.
        project: Affiliated project label.
        format: File format label.
    """

    uri: str
    label: str
    data_level: int
    has_data_access: bool
    theme: str
    project: str
    format: str

    @classmethod
    def from_lite(cls, d: DobjSpecLite) -> "DataType":
        return cls(
            uri=d.uri,
            label=d.label or "",
            data_level=d.data_level,
            has_data_access=d.has_data_access,
            theme=d.theme.label or "",
            project=d.project.label or "",
            format=d.format.label or "",
        )

    @classmethod
    def from_dict(cls, d: dict) -> "DataType":
        return cls(
            uri=d["uri"],
            label=d["label"],
            data_level=int(d["data_level"]),
            has_data_access=bool(d["has_data_access"]),
            theme=d.get("theme", ""),
            project=d.get("project", ""),
            format=d.get("format", ""),
        )


type DataTypeInput = str | list[str] | list[DataType]


class DataTypeNotFound(LookupError):
    """Raised when no ecosystem datatype matches a product or label query."""


class AmbiguousDataType(LookupError):
    """Raised when more than one datatype matches a label query.

    Attributes:
        query: The original query string.
        matches: All datatypes that matched.
    """

    def __init__(self, query: str, matches: list[DataType]) -> None:
        self.query = query
        self.matches = matches
        labels = ", ".join(m.label for m in matches)
        super().__init__(f"Ambiguous datatype {query!r}: {labels}")


def _fetch_datatypes() -> list[dict]:
    out = []
    for d in meta.list_datatypes():
        if (d.theme.label or "") != ECO_THEME:
            continue
        out.append(asdict(DataType.from_lite(d)))
    return out


def list_datatypes(
    *, search: str | None = None, refresh: bool = False
) -> list[DataType]:
    """List ecosystem datatypes. Prefer ``Client.datatypes`` in application code."""
    raw = cache.get_or_fetch("datatypes", _fetch_datatypes, refresh=refresh)
    types = [DataType.from_dict(d) for d in raw]
    if not search:
        return types
    q = search.casefold()
    return [
        t
        for t in types
        if q in t.label.casefold()
        or q in t.project.casefold()
        or q in t.format.casefold()
    ]


def match_label(types: list[DataType], query: str) -> list[DataType]:
    """Resolve an exact or unique-substring label match (pure, package-internal).

    Never consults `PRODUCT_PRESETS`; use `match_product` for preset support.
    """
    key = query.strip().casefold()

    exact = [t for t in types if t.label.casefold() == key]
    if exact:
        return exact

    partial = [t for t in types if key in t.label.casefold()]
    if len(partial) == 1:
        return partial
    if len(partial) > 1:
        raise AmbiguousDataType(query, partial)
    raise DataTypeNotFound(f"No ecosystem datatype matching {query!r}")


def match_product(types: list[DataType], product: str) -> list[DataType]:
    """Resolve preset/label against an in-memory list (pure, package-internal)."""
    key = product.strip().casefold()

    try:
        preset = ProductPreset(key)
    except ValueError:
        preset = None

    if preset is not None:
        hits: list[DataType] = []
        for needle in PRODUCT_PRESETS[preset]:
            if needle.startswith("~"):
                sub = needle[1:]
                hits.extend(t for t in types if sub in t.label.casefold())
            else:
                hits.extend(t for t in types if t.label.casefold() == needle)
        seen: set[str] = set()
        uniq: list[DataType] = []
        for t in hits:
            if t.uri not in seen:
                seen.add(t.uri)
                uniq.append(t)
        if not uniq:
            raise DataTypeNotFound(f"Preset {product!r} matched no ecosystem datatypes")
        return uniq

    return match_label(types, product)


def resolve_product(product: str, *, refresh: bool = False) -> list[DataType]:
    """Resolve a product preset or label. Prefer ``Client.resolve_product``."""
    return match_product(list_datatypes(refresh=refresh), product)


def resolve_label(query: str, *, refresh: bool = False) -> list[DataType]:
    """Resolve a datatype label, never consulting presets. Package-internal."""
    return match_label(list_datatypes(refresh=refresh), query)


def _is_sensitive_product(types: list[DataType]) -> bool:
    return any(
        "raw" in t.label.casefold() or "archive" in t.label.casefold() for t in types
    )
