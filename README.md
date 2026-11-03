# icanhazflux

Unofficial Python API and CLI for downloading [ICOS](https://www.icos-cp.eu/) ecosystem station data, built on [`icoscp_core`](https://pypi.org/project/icoscp_core/). It is not affiliated with ICOS or the ICOS Carbon Portal.

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
icanhazflux collections --search "release 2025-1"   # releases with DOI and URI
icanhazflux download --product l2 --collection 10.18160/S6HM-CP8Q --out ./data/2025-1
```

`--collection` selects the files in one release, including versions that have
since been superseded; without `--product` or `--datatype` it selects every
ecosystem file in the release. It takes a collection URI, or a DOI held by
exactly one collection. A DOI can be shared by several collections with
different files, so pass the URI when reproducibility matters.

Product presets and direct datatype matching are described in the [CLI reference](docs/cli.md).

## Python API

Import the stable public API from the package root:

`Client`, `Station`, `DataType`, `DataTypeInput`, `ProductPreset`, `DataObject`,
`Collection`, `PRODUCT_PRESETS`, and the `*NotFound` / `Ambiguous*` exceptions.

```python
from icanhazflux import Client

c = Client()
c.login()  # once

print(c.stations(search="hylte"))
objs = c.find("SE-Htm", product="l2")
c.download(objs, out="./data")

# or one-shot
c.get("SE-Htm", product="meteo", out="./data")

# every station's L2 file in release 2025-1
objs = c.find(product="l2", collection="10.18160/S6HM-CP8Q")
```

Downloads currently save the original portal files.
