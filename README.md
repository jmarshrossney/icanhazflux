# icanhazflux

**Unofficial** Python API and CLI for downloading [ICOS](https://www.icos-cp.eu/) ecosystem station data, built on [`icoscp_core`](https://pypi.org/project/icoscp_core/).

This project is **not affiliated with, endorsed by, or maintained by** ICOS or the ICOS Carbon Portal. It is an independent convenience wrapper.

Discovery needs no credentials. Downloads require an [ICOS Carbon Portal](https://www.icos-cp.eu/) account with the **CC BY 4.0** licence accepted in your profile.

## Install

```bash
uv sync
# or: pip install -e .
```

## CLI

Typical workflow: discover a station with `sites`, inspect its data objects
with `objects`, then download them with `download`. Use `datatypes` when you
need to choose a product preset or exact datatype label.

```bash
icanhazflux login                          # once, interactive
icanhazflux sites --search hylte
icanhazflux datatypes                       # presets + eco datatypes
icanhazflux objects SE-Htm --product l2
icanhazflux download SE-Htm --product l2 --out ./data
icanhazflux download SE-Htm --product raw --start 2024-01-01 --end 2024-01-07 -y
```

### Product presets

| Preset    | Datatype                          |
|-----------|-----------------------------------|
| `l2` / `fluxnet` | ETC L2 Fluxnet (half-hourly) |
| `fluxes`  | ETC L2 Fluxes                     |
| `meteo`   | ETC L2 Meteo                      |
| `nrt`     | ETC NRT Fluxnet                   |
| `raw`     | Eddy flux raw daily archives      |
| `archive` | ETC L2 ARCHIVE                    |

Use `--datatype TEXT` for a free-text label match instead of a preset.

Station metadata and datatypes are cached under `~/.cache/icanhazflux/` (7-day TTL). Pass `--refresh` to reload.

## Python API

Import from the package root only. The stable public surface is:

`Client`, `Station`, `DataType`, `DataObject`, `PRODUCT_PRESETS`, and the `*NotFound` / `Ambiguous*` exceptions.

```python
from icanhazflux import Client

c = Client()
c.login()  # once

print(c.stations(search="hylte"))
objs = c.find("SE-Htm", product="l2")
c.download(objs, out="./data")

# or one-shot
c.get("SE-Htm", product="meteo", out="./data")
```

Submodules (`icanhazflux.stations`, …) and underscore-prefixed names are internal.

## Scope (v0)

- Ecosystem stations only (`ECO_STATION`)
- File downloads only (`data.save_to_folder`)
