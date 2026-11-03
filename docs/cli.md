---
title: CLI
icon: lucide/square-terminal
---

Use these commands to find a station, inspect its data objects, and download files.

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

## `collections`

List DOI collections containing ecosystem data, such as ETC releases, with the
URI to pass to `--collection`.
A collection marked "superseded (same DOI)" has been replaced by another
collection with the same DOI.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: collections
    :termynal: true
    :width: 88
    :prompt: ❯

## `objects`

List data objects available for a station, a collection, or both.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: objects
    :termynal: true
    :width: 88
    :prompt: ❯

## `download`

Download data objects for a station, a collection, or both.

::: mkdocs-typer2
    :module: icanhazflux.cli
    :name: icanhazflux
    :command: download
    :termynal: true
    :width: 88
    :prompt: ❯
