"""icanhazflux — unofficial wrapper around icoscp_core for ecosystem flux data.

Not affiliated with ICOS or the ICOS Carbon Portal.

Public API (stable):
    Client, Station, DataType, DataObject, PRODUCT_PRESETS,
    StationNotFound, AmbiguousStation, DataTypeNotFound, AmbiguousDataType

Import only from this package root in application code::

    from icanhazflux import Client

Submodules and names not listed in ``__all__`` are internal and may change.
"""

from .client import Client
from .objects import DataObject
from .stations import AmbiguousStation, Station, StationNotFound
from .types import (
    PRODUCT_PRESETS,
    AmbiguousDataType,
    DataType,
    DataTypeNotFound,
)
from .version import __version__

__all__ = [
    "PRODUCT_PRESETS",
    "AmbiguousDataType",
    "AmbiguousStation",
    "Client",
    "DataObject",
    "DataType",
    "DataTypeNotFound",
    "Station",
    "StationNotFound",
    "__version__",
]


def main() -> None:
    """CLI entry point (``icanhazflux`` console script). Not part of the public library API."""
    from .cli import main as cli_main

    cli_main()
