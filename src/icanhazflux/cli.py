from pathlib import Path
from typing import Annotated, NoReturn

import typer
from rich.console import Console
from rich.table import Table

from . import cache
from .client import Client
from .stations import AmbiguousStation, StationNotFound
from .types import (
    _RAW_WARNING,
    PRODUCT_PRESETS,
    AmbiguousDataType,
    DataTypeNotFound,
    _is_sensitive_product,
    match_product,
    resolve_label,
    resolve_product,
)
from .version import __version__

# Prompt before downloading more than this. Module-level so tests can patch it.
_CONFIRM_THRESHOLD_BYTES = 50 * 1024 * 1024

app = typer.Typer(
    name="icanhazflux",
    help="Unofficial tool to download ICOS ecosystem station data via icoscp_core.",
    no_args_is_help=True,
    context_settings={"help_option_names": ["-h", "--help"]},
)
console = Console()
err_console = Console(stderr=True)


def _client() -> Client:
    return Client()


def _die(msg: str, code: int = 1) -> NoReturn:
    err_console.print(f"[red]{msg}[/red]")
    raise typer.Exit(code)


def _format_size(n: int) -> str:
    if n >= 1024**3:
        return f"{n / 1024**3:.2f} GB"
    if n >= 1024**2:
        return f"{n / 1024**2:.1f} MB"
    if n >= 1024:
        return f"{n / 1024:.0f} KB"
    return f"{n} B"


@app.command()
def login() -> None:
    """Store ICOS Carbon Portal credentials (interactive)."""
    console.print(
        "Log in with your [link=https://cpauth.icos-cp.eu/]ICOS CP[/link] account. "
        "Accept the CC BY 4.0 licence in your profile before downloading."
    )
    _client().login()
    console.print("[green]Credentials saved.[/green]")


@app.command("sites")
def sites_cmd(
    search: str | None = typer.Option(
        None, "--search", "-s", help="Filter by id/name/country"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Bust local station cache"),
) -> None:
    """List ecosystem stations."""
    stations = _client().stations(search=search, refresh=refresh)
    if not stations:
        _die("No stations matched.")
    table = Table(show_header=True, header_style="bold")
    table.add_column("ID")
    table.add_column("Name")
    table.add_column("CC", width=4)
    table.add_column("Lat")
    table.add_column("Lon")
    table.add_column("Elev")
    for s in stations:
        table.add_row(
            s.id,
            s.name,
            s.country_code,
            f"{s.lat:.4f}" if s.lat is not None else "",
            f"{s.lon:.4f}" if s.lon is not None else "",
            f"{s.elevation:.0f}" if s.elevation is not None else "",
        )
    console.print(table)
    console.print(f"[dim]{len(stations)} station(s)[/dim]")


@app.command("datatypes")
def datatypes_cmd(
    search: str | None = typer.Option(
        None, "--search", "-s", help="Filter by label/project"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Bust local datatype cache"),
) -> None:
    """List ecosystem datatypes and product presets."""
    types = _client().datatypes(search=search, refresh=refresh)
    if not types:
        _die("No datatypes matched.")

    if search is None:
        # Unfiltered, so `types` is the full catalog and presets can be
        # resolved to real labels without a second fetch.
        console.print("[bold]Product presets[/bold]")
        for name in PRODUCT_PRESETS:
            try:
                shown = ", ".join(t.label for t in match_product(types, name))
            except DataTypeNotFound:
                shown = "[dim](no match)[/dim]"
            console.print(f"  {name:10} → {shown}")
        console.print()

    table = Table(show_header=True, header_style="bold")
    table.add_column("Level", width=5)
    table.add_column("Access", width=6)
    table.add_column("Label")
    table.add_column("Project")
    table.add_column("Format")
    for t in sorted(types, key=lambda x: (x.data_level, x.label)):
        table.add_row(
            f"L{t.data_level}",
            "yes" if t.has_data_access else "no",
            t.label,
            t.project,
            t.format,
        )
    console.print(table)
    console.print(f"[dim]{len(types)} type(s)[/dim]")


def _resolve_query(
    site: str,
    product: str | None,
    datatype: str | None,
    start: str | None,
    end: str | None,
    limit: int,
    refresh: bool,
    include_deprecated: bool = False,
):
    c = _client()
    try:
        st = c.resolve_station(site, refresh=refresh)
    except StationNotFound as e:
        _die(str(e))
    except AmbiguousStation as e:
        lines = "\n".join(f"  {m.id:10} {m.name}" for m in e.matches)
        _die(f"{e}\n{lines}")

    # --datatype is a label match only; presets belong to --product.
    try:
        if datatype is not None:
            resolved_types = resolve_label(datatype, refresh=refresh)
        else:
            resolved_types = resolve_product(product or "l2", refresh=refresh)
    except DataTypeNotFound as e:
        _die(str(e))
    except AmbiguousDataType as e:
        lines = "\n".join(f"  {m.label}" for m in e.matches)
        _die(f"{e}\n{lines}")

    objs = c.find(
        st,
        product=None,
        datatype=resolved_types,
        start=start,
        end=end,
        limit=limit,
        include_deprecated=include_deprecated,
        refresh=refresh,
    )
    return c, st, resolved_types, objs


@app.command("objects")
def objects_cmd(
    site: str = typer.Argument(..., help="Station id, name, or URI (e.g. SE-Htm)"),
    product: str | None = typer.Option(
        None,
        "--product",
        "-p",
        help=f"Preset: {', '.join(PRODUCT_PRESETS)} (default: l2)",
    ),
    datatype: str | None = typer.Option(
        None,
        "--datatype",
        "-d",
        help="Exact datatype label or unique substring; never a preset. "
        "Overrides --product.",
    ),
    start: str | None = typer.Option(
        None, "--start", help="Obs start lower bound (YYYY-MM-DD)"
    ),
    end: str | None = typer.Option(
        None, "--end", help="Obs end upper bound (YYYY-MM-DD)"
    ),
    limit: int = typer.Option(1000, "--limit", "-n", help="Max objects to return"),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include superseded object versions"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Bust metadata caches"),
) -> None:
    """List available data objects for a station (no auth)."""
    _, st, resolved_types, objs = _resolve_query(
        site, product, datatype, start, end, limit, refresh, include_deprecated
    )
    console.print(f"[bold]{st.id}[/bold] {st.name}  ({st.uri})")
    console.print("Types: " + ", ".join(t.label for t in resolved_types))
    if _is_sensitive_product(resolved_types):
        console.print(f"[yellow]{_RAW_WARNING}[/yellow]")

    if not objs:
        console.print("[dim]No objects found.[/dim]")
        raise typer.Exit(0)

    table = Table(show_header=True, header_style="bold")
    table.add_column("Filename")
    table.add_column("Start")
    table.add_column("End")
    table.add_column("Size", justify="right")
    for o in objs:
        table.add_row(
            o.filename,
            o.time_start.date().isoformat(),
            o.time_end.date().isoformat(),
            _format_size(o.size_bytes),
        )
    console.print(table)
    total = sum(o.size_bytes for o in objs)
    console.print(f"[dim]{len(objs)} object(s), {_format_size(total)} total[/dim]")


@app.command("download")
def download_cmd(
    site: str = typer.Argument(..., help="Station id, name, or URI (e.g. SE-Htm)"),
    product: str | None = typer.Option(
        None,
        "--product",
        "-p",
        help=f"Preset: {', '.join(PRODUCT_PRESETS)} (default: l2)",
    ),
    datatype: str | None = typer.Option(
        None,
        "--datatype",
        "-d",
        help="Exact datatype label or unique substring; never a preset. "
        "Overrides --product.",
    ),
    start: str | None = typer.Option(
        None, "--start", help="Obs start lower bound (YYYY-MM-DD)"
    ),
    end: str | None = typer.Option(
        None, "--end", help="Obs end upper bound (YYYY-MM-DD)"
    ),
    out: Annotated[Path, typer.Option("--out", "-o", help="Output directory")] = Path(
        "."
    ),
    limit: int = typer.Option(1000, "--limit", "-n", help="Max objects to download"),
    yes: bool = typer.Option(False, "--yes", "-y", help="Skip size confirmation"),
    include_deprecated: bool = typer.Option(
        False, "--include-deprecated", help="Include superseded object versions"
    ),
    refresh: bool = typer.Option(False, "--refresh", help="Bust metadata caches"),
) -> None:
    """Download data objects for a station (requires login)."""
    c, st, resolved_types, objs = _resolve_query(
        site, product, datatype, start, end, limit, refresh, include_deprecated
    )
    console.print(f"[bold]{st.id}[/bold] {st.name}")
    console.print("Types: " + ", ".join(t.label for t in resolved_types))
    if _is_sensitive_product(resolved_types):
        console.print(f"[yellow]{_RAW_WARNING}[/yellow]")

    if not objs:
        console.print("[dim]No objects found.[/dim]")
        raise typer.Exit(0)

    total = sum(o.size_bytes for o in objs)
    console.print(f"{len(objs)} file(s), {_format_size(total)} → {out.resolve()}")

    if not yes and total > _CONFIRM_THRESHOLD_BYTES and not typer.confirm("Continue?"):
        raise typer.Exit(1)

    try:
        paths = c.download(objs, out)
    except Exception as e:  # noqa: BLE001 - CLI boundary; report and exit cleanly
        _die(f"Download failed: {e}")

    console.print(f"[green]Saved {len(paths)} file(s) to {out.resolve()}[/green]")


@app.command("version")
def version_cmd() -> None:
    """Prints the version."""
    typer.echo(f"icanhazflux version {__version__}")


cache_app = typer.Typer(
    help="Inspect and clear the local metadata caches.",
    no_args_is_help=True,
)
app.add_typer(cache_app, name="cache")


@cache_app.command("path")
def cache_path_cmd() -> None:
    """Print the local cache directory."""
    console.print(str(cache.cache_dir()))


@cache_app.command("clear")
def cache_clear_cmd(
    name: str | None = typer.Argument(
        None, help="Cache to clear, e.g. stations or datatypes (default: all)"
    ),
) -> None:
    """Delete cached station and datatype metadata."""
    cache.clear(name)
    target = f"{name!r} cache" if name else "all caches"
    console.print(f"[green]Cleared {target}.[/green]")


def main() -> None:
    app()


if __name__ == "__main__":
    main()
