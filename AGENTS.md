# AGENTS.md

`icanhazflux` is an **unofficial** thin Python API + Typer CLI over `icoscp_core` for discovering and downloading **ICOS ecosystem** station data. It is not affiliated with ICOS or the Carbon Portal.

## Non-obvious constraints

- **Python ≥ 3.12.** Do not add `from __future__ import annotations`. Use modern syntax (`X | None`, `list[str]`, `collections.abc.Callable`).
- **Public API is only what `__init__.__all__` exports** (`Client`, dataclasses, exceptions, `PRODUCT_PRESETS`). Prefer extending `Client`; do not grow the root export surface casually. Underscore-prefixed names and non-exported helpers are internal.
- **Docstrings: Google style**, written for **MkDocs Material / Markdown** rendering (backticks, plain cross-refs like ``Client.find``). Do **not** use Sphinx/RST roles (`:meth:`, `:class:`, `:param:`, etc.). Omit types in Args/Returns — signatures carry types.
- **Ecosystem scope only** (`ECO_STATION` / theme `Ecosystem data`). Do not add atmosphere/ocean/SITES/cities unless explicitly requested. Same physical site can be both AS and ES (e.g. `HTM` vs `SE-Htm`) — never collapse domains.
- **Downloads are original files** via `data.save_to_folder` unless implementing the planned tabular path (`docs/plan-tabular-export.md`). Do not silently switch structured types to DataFrame/CSV.
- **Auth split:** metadata/discovery needs no credentials; byte downloads need `login` / portal account + CC BY 4.0 accepted. Don’t require auth for `sites` / `types` / `list` / `find`.
- **Product presets resolve at runtime** from `list_datatypes()` (see `PRODUCT_PRESETS`). Prefer label matching over hardcoding datatype URIs so portal renames don’t break us.
- **Time filters use observation-period overlap**, not submission time; date-only `--end` is end-of-day. `TimeFilter` only supports exclusive `<`/`>`.
- **`__version__`** comes from `importlib.metadata`, not a hardcoded string.
- **Tests stay offline:** unit-test pure resolvers and CliRunner with mocks. No live portal calls in CI. Optional deps (e.g. pandas) stay extras, imported lazily.
- **Branding:** keep “unofficial / not affiliated” wording; avoid names or copy that imply official ICOS tooling.
- Dev commands are in justfile: `just lint` (ruff), `just typecheck` (pyright), `just test` (pytest), `just docs` (zensical build).
