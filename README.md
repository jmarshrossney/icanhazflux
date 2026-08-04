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
```

Product presets and direct datatype matching are described in the [CLI reference](docs/cli.md).

## Python API

Import the stable public API from the package root:

`Client`, `Station`, `DataType`, `DataTypeInput`, `ProductPreset`, `DataObject`,
`PRODUCT_PRESETS`, and the `*NotFound` / `Ambiguous*` exceptions.

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

Downloads currently save the original portal files.
