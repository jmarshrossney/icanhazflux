---
title: Home
icon: lucide/house
---

# icanhazflux

**Unofficial** Python API and CLI for downloading [ICOS](https://www.icos-cp.eu/)
ecosystem station data, built on
[`icoscp_core`](https://pypi.org/project/icoscp_core/).

!!! warning "Not an official ICOS tool"

    This project is **not affiliated with, endorsed by, or maintained by** ICOS
    or the ICOS Carbon Portal. It is an independent convenience wrapper.

Discovery needs no credentials. Downloads require an
[ICOS Carbon Portal](https://cpauth.icos-cp.eu/) account with the **CC BY 4.0**
licence accepted in your profile.

## Install

```bash
uv sync
# or: pip install -e .
```

## Command line

The typical workflow is discover → inspect → download. Run `login` once first if
you intend to download anything.

```bash
icanhazflux login                          # once, interactive
icanhazflux sites --search hylte           # find a station
icanhazflux objects SE-Htm --product l2    # inspect what's available (no auth)
icanhazflux download SE-Htm --product l2 --out ./data
```

Use `datatypes` to browse the ecosystem datatype catalogue and see which
datatypes each product preset currently resolves to.

See the [CLI reference](cli.md) for every command and flag.

### Product presets

`--product` accepts a friendly preset name:

| Preset           | Datatype                      |
|------------------|-------------------------------|
| `l2` / `fluxnet` | ETC L2 Fluxnet (half-hourly)  |
| `fluxes`         | ETC L2 Fluxes                 |
| `meteo`          | ETC L2 Meteo                  |
| `nrt`            | ETC NRT Fluxnet               |
| `raw`            | Eddy flux raw daily archives  |
| `archive`        | ETC L2 ARCHIVE                |

Presets resolve against the live catalogue, so they keep working across portal
renames. To bypass presets entirely and match a datatype label directly, use
`--datatype TEXT` — an exact label match, falling back to a unique substring
match.

### Caching

Station and datatype metadata is cached under `~/.cache/icanhazflux/` with a
7-day TTL. Pass `--refresh` to any command to bypass it, or use
`icanhazflux cache clear` to delete it outright.

## Python API

Import from the package root only. The stable public surface is `Client`,
`Station`, `DataType`, `DataTypeInput`, `ProductPreset`, `DataObject`,
`PRODUCT_PRESETS`, and the `*NotFound` /
`Ambiguous*` exceptions. Submodules and underscore-prefixed names are internal
and may change.

```python
from icanhazflux import Client

c = Client()
c.login()  # once

print(c.stations(search="hylte"))

objs = c.find("SE-Htm", product="l2")
print(Client.total_size_bytes(objs))
c.download(objs, out="./data")

# or in one step
c.get("SE-Htm", product="meteo", out="./data")
```

See the [API reference](api.md) for full signatures.

## Scope

- Ecosystem stations only (`ECO_STATION`)
- File downloads only (`data.save_to_folder`)
- Tabular DataFrame / CSV / Parquet export is planned but not implemented
