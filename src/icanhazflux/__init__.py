"""Unofficial Python API for ICOS ecosystem station data.

Import the public API from this package root.
"""

from .client import Client
from .objects import DataObject
from .releases import AmbiguousCollection, Collection, CollectionNotFound
from .stations import AmbiguousStation, Station, StationNotFound
from .types import (
    PRODUCT_PRESETS,
    AmbiguousDataType,
    DataType,
    DataTypeInput,
    DataTypeNotFound,
    ProductPreset,
)
from .version import __version__

__all__ = [
    "PRODUCT_PRESETS",
    "AmbiguousCollection",
    "AmbiguousDataType",
    "AmbiguousStation",
    "Client",
    "Collection",
    "CollectionNotFound",
    "DataObject",
    "DataType",
    "DataTypeInput",
    "DataTypeNotFound",
    "ProductPreset",
    "Station",
    "StationNotFound",
    "__version__",
]


def main() -> None:
    """Run the ``icanhazflux`` command-line interface."""
    from .cli import main as cli_main

    cli_main()
