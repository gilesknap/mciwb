"""
Run the scripts of the Claude Code skill in .claude/skills/minecraft-build
against the test server, as an agent following the skill would
"""

from pathlib import Path

import pytest
from typer.testing import CliRunner

from mciwb.__main__ import cli
from mciwb.blockgrid import grab_blocks
from mciwb.imports import Item, Vec3, Volume
from mciwb.threads import Client
from tests.conftest import HOST, RCON_P, RCON_PORT

SCRIPTS = Path(__file__).parents[2] / ".claude" / "skills" / "minecraft-build"
SCRIPTS = SCRIPTS / "scripts"
# a clear patch of the flat world, inside the chunks the test server keeps
# loaded and away from the other tests
SITE = Vec3(33, -60, -32)
runner = CliRunner()


def run_script(script: Path):
    result = runner.invoke(
        cli,
        ["run", str(script), "--server", HOST, "--port", str(RCON_PORT)]
        + ["--passwd", RCON_P],
    )
    assert result.exit_code == 0, (result.output, result.exception)
    return result.output


def test_survey_then_build(
    minecraft_client: Client, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    client = minecraft_client
    # the flat world: grass at y -61 with nothing above it
    client.fill(SITE + Vec3(-13, -1, -13), SITE + Vec3(13, -1, 13), Item.GRASS_BLOCK)
    client.fill(SITE + Vec3(-13, 0, -13), SITE + Vec3(13, 20, 13), Item.AIR)
    monkeypatch.chdir(tmp_path)

    # survey over RCON (the test server's world is not where Iwb looks), so
    # give a small Y range
    monkeypatch.setenv("SURVEY", f"{SITE.x} {SITE.z} 6 -64 -45")
    out = run_script(SCRIPTS / "survey.py")

    assert "min -61, median -61, max -61" in out
    assert "ground blocks: minecraft:grass_block 169" in out
    assert (tmp_path / "survey.png").is_file()

    # build the template's hut on the surveyed ground
    template = (SCRIPTS / "build_template.py").read_text()
    script = tmp_path / "hut.py"
    origin = "ORIGIN = Vec3(632, 73, -1658)"
    assert origin in template
    script.write_text(
        template.replace(origin, f"ORIGIN = Vec3({SITE.x}, {SITE.y}, {SITE.z})")
    )
    run_script(script)

    assert (tmp_path / "hut.png").is_file()
    door = SITE + Vec3(3, 1, 5)
    grid = grab_blocks(client, Volume.from_corners(SITE, door))
    assert grid[SITE] == "minecraft:cobblestone"
    assert grid[door] == "minecraft:oak_door"
