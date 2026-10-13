"""
Check the Claude Code skill in .claude/skills/minecraft-build: its frontmatter
and links, and that its scripts run against the mock world with ``mciwb run``
"""

import re
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from mciwb.__main__ import cli
from mciwb.imports import Item, Vec3
from tests.mockclient import MockClient

SKILL = Path(__file__).parents[2] / ".claude" / "skills" / "minecraft-build"
SCRIPTS = SKILL / "scripts"
runner = CliRunner()


def frontmatter(path: Path) -> tuple[dict, str]:
    """the YAML frontmatter of a SKILL.md, and the text after it"""
    text = path.read_text()
    match = re.match(r"---\n(.*?)\n---\n", text, re.DOTALL)
    assert match, f"{path} must start with --- YAML frontmatter ---"
    return yaml.safe_load(match.group(1)), text[match.end() :]


def test_frontmatter():
    meta, body = frontmatter(SKILL / "SKILL.md")
    assert meta["name"] == SKILL.name
    assert re.fullmatch(r"[a-z0-9-]{1,64}", meta["name"])
    # the listing shows at most 1024 characters of the description
    assert 100 < len(meta["description"]) <= 1024
    assert "Use when" in meta["description"]
    # Claude Code keeps SKILL.md bodies short: details go in other files
    assert len(body.splitlines()) < 150


def test_links():
    """every file that the skill refers to exists"""
    text = (SKILL / "SKILL.md").read_text()
    targets = re.findall(r"\]\(([^)#:]+)\)", text)
    targets += re.findall(r"\$\{CLAUDE_SKILL_DIR\}/([\w/.]+)", text)
    assert targets
    for target in targets:
        assert (SKILL / target).is_file(), target


@pytest.fixture()
def mock_world(
    mock_client: MockClient, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """a mock server for mciwb run, with no world folder: blocks are read over RCON"""
    monkeypatch.setattr("mciwb.iwb.Client", MockClient)
    monkeypatch.setattr("mciwb.iwb.default_server_folder", tmp_path / "no-server")
    monkeypatch.chdir(tmp_path)
    return mock_client


def run(script: Path, *args: str):
    result = runner.invoke(
        cli, ["run", str(script), "--server", "localhost", "--port", "20400", *args]
    )
    return result


def test_build_template(mock_world: MockClient, tmp_path: Path):
    template = (SCRIPTS / "build_template.py").read_text()
    origin = "ORIGIN = Vec3(632, 73, -1658)"
    assert origin in template
    # the mock world only has positive coordinates
    script = tmp_path / "build.py"
    script.write_text(template.replace(origin, "ORIGIN = Vec3(10, 1, 10)"))

    result = run(script)

    assert result.exit_code == 0, (result.output, result.exception)
    assert (tmp_path / "build.png").is_file()
    assert mock_world.getblock(Vec3(10, 1, 10)) == Item.COBBLESTONE
    assert mock_world.getblock(Vec3(11, 1, 11)) == Item.SPRUCE_PLANKS
    assert mock_world.getblock(Vec3(11, 2, 11)) == Item.AIR
    assert mock_world.getblock(Vec3(9, 6, 9)) == Item.SPRUCE_SLAB
    assert mock_world.getblock(Vec3(13, 2, 15)) == Item.OAK_DOOR


def test_build_template_refuses_player(mock_world: MockClient, tmp_path: Path):
    """the template will not build over a player (georgeTest is at 0, -60, 0)"""
    script = tmp_path / "build.py"
    template = (SCRIPTS / "build_template.py").read_text()
    script.write_text(template.replace("Vec3(632, 73, -1658)", "Vec3(-2, -61, -2)", 1))

    result = run(script)

    assert result.exit_code != 0
    assert "georgeTest inside" in str(result.exception)
    assert mock_world.getblock(Vec3(-2, -61, -2)) == Item.AIR


def test_survey(mock_world: MockClient, tmp_path: Path, monkeypatch):
    # ground at y 4, a hill up to y 7, and a pond with a flower beside it
    mock_world.fill(Vec3(0, 0, 0), Vec3(20, 4, 20), Item.GRASS_BLOCK)
    mock_world.fill(Vec3(12, 5, 12), Vec3(13, 7, 13), Item.STONE)
    mock_world.fill(Vec3(6, 4, 6), Vec3(7, 4, 7), Item.WATER)
    mock_world.setblock(Vec3(9, 5, 9), Item.POPPY)
    monkeypatch.setenv("SURVEY", "10 10 4 -2 12")

    result = run(SCRIPTS / "survey.py")

    assert result.exit_code == 0, (result.output, result.exception)
    out = result.output
    assert "site x 6..14, z 6..14 (y -2..12)" in out
    assert "player georgeTest at (0, -60, 0), outside" in out
    assert "min 4, median 4, max 7" in out
    assert "minecraft:grass_block 73" in out
    assert "minecraft:water 4" in out
    rows = [line.strip()[1:-1] for line in out.splitlines() if "|" in line]
    assert len(rows) == 9
    assert rows[0] == "~~0000000"
    assert rows[6] == "000000330"
    assert (tmp_path / "survey.png").is_file()


def test_survey_around_player(mock_world: MockClient, tmp_path: Path):

    result = run(SCRIPTS / "survey.py", "--player", "georgeTest")

    # the default survey reads the whole world height, too many blocks for RCON
    assert result.exit_code != 0
    assert "give a smaller RADIUS" in str(result.exception)


def test_survey_needs_a_site(mock_world: MockClient):
    result = run(SCRIPTS / "survey.py")

    assert result.exit_code != 0
    assert "SURVEY=" in str(result.exception)
