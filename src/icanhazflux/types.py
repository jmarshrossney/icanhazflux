from dataclasses import asdict, dataclass

from icoscp_core.icos import meta
from icoscp_core.queries.speclist import DobjSpecLite

from . import cache

ECO_THEME = "Ecosystem data"

# Friendly preset → substrings matched against datatype labels (casefold).
# Values are exact labels (casefold) unless prefixed with "~" (substring match).
PRODUCT_PRESETS: dict[str, list[str]] = {
    "l2": ["etc l2 fluxnet (half-hourly)"],
    "fluxnet": ["etc l2 fluxnet (half-hourly)"],
    "fluxes": ["etc l2 fluxes"],
    "meteo": ["etc l2 meteo"],
    "nrt": ["~etc nrt fluxnet"],
    "raw": ["~eddy flux raw"],
    "archive": ["etc l2 archive"],
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
    """An ICOS ecosystem data object type (data object specification).

    Attributes:
        uri: Datatype metadata URI.
        label: Human-readable type label.
        data_level: ICOS data level (0 raw … 3 elaborated).
        has_data_access: True if columnar/array access is supported by
            the portal for this type (vs original-file download only).
        theme: Data theme label (ecosystem types use ``Ecosystem data``).
        project: Affiliated project label (e.g. ``ICOS``).
        format: File/format label (e.g. CSV, zip archive).
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


def match_product(types: list[DataType], product: str) -> list[DataType]:
    """Resolve preset/label against an in-memory list (pure, package-internal)."""
    key = product.strip().casefold()

    if key in PRODUCT_PRESETS:
        hits: list[DataType] = []
        for needle in PRODUCT_PRESETS[key]:
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

    exact = [t for t in types if t.label.casefold() == key]
    if exact:
        return exact

    partial = [t for t in types if key in t.label.casefold()]
    if len(partial) == 1:
        return partial
    if len(partial) > 1:
        raise AmbiguousDataType(product, partial)
    raise DataTypeNotFound(f"No ecosystem datatype matching {product!r}")


def resolve_product(product: str, *, refresh: bool = False) -> list[DataType]:
    """Resolve a product preset or label. Prefer ``Client.resolve_product``."""
    return match_product(list_datatypes(refresh=refresh), product)


def _is_sensitive_product(types: list[DataType]) -> bool:
    return any(
        "raw" in t.label.casefold() or "archive" in t.label.casefold() for t in types
    )
