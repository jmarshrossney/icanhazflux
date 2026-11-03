---
title: Home
icon: lucide/house
---

# icanhazflux

Unofficial Python API and CLI for downloading [ICOS](https://www.icos-cp.eu/)
ecosystem station data, built on
[`icoscp_core`](https://pypi.org/project/icoscp_core/). It is not affiliated with
ICOS or the ICOS Carbon Portal.

Discovery needs no credentials. Downloads require an
[ICOS Carbon Portal](https://cpauth.icos-cp.eu/) account with the **CC BY 4.0**
licence accepted in your profile.

## Install

```bash
uv sync
# or: pip install -e .
```

## Command line

The typical workflow is discover, inspect, then download. Run `login` once before
downloading.

```bash
icanhazflux login                          # once, interactive
icanhazflux sites --search hylte           # find a station
icanhazflux objects SE-Htm --product l2    # inspect what's available (no auth)
icanhazflux download SE-Htm --product l2 --out ./data
```

Use `datatypes` to browse the ecosystem datatype catalogue and product presets.

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

### Reproducing a release

ETC publishes releases as Carbon Portal collections, each with a DOI. Most files
in a past release have since been superseded, so `--collection` includes
superseded versions. `SITE`, `--product`, `--datatype` and the time bounds
filter within the collection.

```bash
icanhazflux collections --search "release 2025-1"
icanhazflux objects --product l2 \
    --collection https://meta.icos-cp.eu/collections/1-HA2r4l5QUjAgQr5CCEfJe3
icanhazflux download BE-Bra --product l2 --collection 10.18160/S6HM-CP8Q \
    --out ./data/2025-1
```

`--collection` takes a collection URI, or a DOI held by exactly one
collection. Several collections can share a DOI, typically a release and a
later replacement with more files, and icanhazflux will not choose between
them: it lists the candidates and stops. Pass the collection URI when
reproducibility matters, since only the URI identifies a fixed set of files.

Files from different releases often share a filename, and downloads overwrite
existing files, so use a separate `--out` directory per release.

### Caching

Station, datatype and collection metadata is cached under `~/.cache/icanhazflux/` with a
7-day TTL. Pass `--refresh` to any command to bypass it, or use
`icanhazflux cache clear` to delete it outright.

## Python API

Import the stable public API from the package root: `Client`,
`Station`, `DataType`, `DataTypeInput`, `ProductPreset`, `DataObject`,
`Collection`, `PRODUCT_PRESETS`, and the `*NotFound` / `Ambiguous*`
exceptions.

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

# every station's L2 file in release 2025-1
print(c.collections(search="release 2025-1"))
objs = c.find(product="l2", collection="10.18160/S6HM-CP8Q")
```

See the [API reference](api.md) for full signatures.

Downloads save original portal files. Tabular export is not currently provided.
