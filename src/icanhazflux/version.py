from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("icanhazflux")
except PackageNotFoundError:  # pragma: no cover - editable/uninstalled edge case
    __version__ = "0.0.0+unknown"
