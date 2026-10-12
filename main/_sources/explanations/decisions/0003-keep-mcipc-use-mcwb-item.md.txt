# 3. Keep mcipc for RCON, take block identifiers from mcwb

Date: 2026-10-12

## Status

Accepted

## Context

mciwb talks to Minecraft through [mcipc](https://github.com/conqp/mcipc) (an RCON
client with a Python wrapper for every server command) and
[rcon](https://github.com/conqp/rcon) (the underlying protocol implementation).

- mcipc's last release is 2.4.2 (2022) and its upstream repository is effectively
  unmaintained. rcon's repository is archived. Both still install and import cleanly
  on Python 3.11-3.14.
- mcipc's command wrappers just build command strings, so they keep working on
  current Minecraft (26.x) releases.
- mcipc's `Item` enum, however, stops at Minecraft 1.16. Reading any newer block
  (deepslate, cherry, mangrove, pale oak, copper bulbs, ...) via `mcwb.get_block`,
  `grab` or `Iwb.get_block` raised `ValueError`.

Alternatives considered: forking mcipc, switching to a maintained async client
(aio-mc-rcon), or writing a small in-house RCON client. All of these would change
the `Client` object that mciwb exposes to users through `get_client()`, and its
tab-completable command methods are part of the learning experience.

## Decision

- Keep mcipc and rcon, pinned to the last known-good releases (`mcipc==2.4.2`,
  `rcon==2.4.9`).
- Use `mcwb.Item` everywhere instead of `mcipc.rcon.enumerations.Item`. It is generated
  from the block and item identifiers of a recent Minecraft release by
  `scripts/generate_items.py` in mcwb, so it can be refreshed without any mcipc change.
  It is a `str` enum with the same member names as mcipc's, so its members compare and
  hash equal to mcipc members and to plain `"minecraft:..."` strings.
- Until mcwb publishes a release that contains `mcwb.Item`, depend on it as a git
  dependency pinned to a commit SHA (see the TODO in `pyproject.toml`).

## Consequences

- `mciwb.imports.Item` now knows every block in the Minecraft release recorded in
  `mcwb.MINECRAFT_VERSION`. When a new Minecraft release adds blocks, regenerate the enum
  in mcwb and release it.
- mciwb cannot be published to PyPI while it uses a git dependency, because PyPI rejects
  direct URL dependencies. Switch to the released mcwb before the next mciwb release.
- If mcipc or rcon stop working on a future Python version, replace them with a small
  RCON client that keeps the `Client` command-method interface.
