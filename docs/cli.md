---
title: CLI
icon: lucide/square-terminal
---

Use the commands below to find a station, inspect its available data objects, and download the files you need.

1. Use `sites` to find an ICOS ecosystem station.
2. Use `objects STATION` to inspect the station's available data objects.
3. Use `download STATION` to download the selected files.
4. Use `login` before downloading if you have not configured portal credentials.

Use `datatypes` when you need to choose a product preset or find an exact datatype label for `--datatype`. 

## `login`

Store ICOS Carbon Portal credentials for authenticated downloads.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: login
    :termynal: true
    :width: 88
    :prompt: ❯

## `sites`

List available ICOS ecosystem stations, optionally filtered by search text.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: sites
    :termynal: true
    :width: 88
    :prompt: ❯

## `datatypes`

Inspect the global ecosystem datatype catalog and the product presets accepted by `--product`.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: datatypes
    :termynal: true
    :width: 88
    :prompt: ❯

## `objects`

List data objects available for a station without downloading them or requiring authentication.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: objects
    :termynal: true
    :width: 88
    :prompt: ❯

## `download`

Download data objects for a station. This requires portal credentials and an accepted CC BY 4.0 licence.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: download
    :termynal: true
    :width: 88
    :prompt: ❯
