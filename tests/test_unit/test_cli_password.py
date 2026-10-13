"""
How the CLI commands get the RCON password: --password, --password-file,
the MCIWB_PASSWORD environment variable, or the default
"""

from pathlib import Path

import pytest
import typer
from typer.testing import CliRunner

import mciwb.__main__
from mciwb.__main__ import PASSWORD_ENV, cli
from mciwb.server import def_pass

runner = CliRunner()

COMMANDS = ["run", "shell", "start", "backup", "restore", "render"]
SECRET = "s3cret-Pa55"


@pytest.fixture(autouse=True)
def no_password_env(monkeypatch: pytest.MonkeyPatch):
    monkeypatch.delenv(PASSWORD_ENV, raising=False)


@pytest.fixture()
def seen(monkeypatch: pytest.MonkeyPatch) -> list[str]:
    """
    Replace everything that the commands give the password to, recording the
    password and then exiting with code 3
    """
    passwords: list[str] = []

    def record(password: str):
        passwords.append(password)
        raise typer.Exit(3)

    monkeypatch.setattr(
        mciwb.__main__, "_connect", lambda server, port, pw, player: record(pw)
    )
    monkeypatch.setattr(mciwb.__main__, "_rcon_client", lambda port, pw: record(pw))
    monkeypatch.setattr(
        mciwb.__main__, "MinecraftServer", lambda name, port, pw, *a, **k: record(pw)
    )
    # restore stops the server, restores the backup and calls start
    monkeypatch.setattr(mciwb.__main__, "stop", lambda **kw: None)
    monkeypatch.setattr(mciwb.__main__.Backup, "__init__", lambda self, **kw: None)
    monkeypatch.setattr(
        mciwb.__main__.Backup, "find", lambda self, name: Path(f"{name}.zip")
    )
    monkeypatch.setattr(mciwb.__main__.Backup, "restore", lambda self, **kw: None)
    return passwords


def command_args(command: str, tmp_path: Path) -> list[str]:
    folder = ["--folder", str(tmp_path / "server")]
    script = tmp_path / "build.py"
    script.write_text("")
    return {
        "run": ["run", str(script)],
        "shell": ["shell"],
        "start": ["start", *folder],
        "backup": ["backup", *folder],
        "restore": ["restore", "b1", *folder],
        "render": ["render", "0", "0", "0", "1", "1", "1", *folder],
    }[command]


def invoke(command: str, tmp_path: Path, *options: str, env=None):
    return runner.invoke(cli, [*command_args(command, tmp_path), *options], env=env)


@pytest.mark.parametrize("command", COMMANDS)
def test_default(command: str, seen: list[str], tmp_path: Path):
    result = invoke(command, tmp_path)
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [def_pass]


@pytest.mark.parametrize("command", COMMANDS)
def test_env(command: str, seen: list[str], tmp_path: Path):
    result = invoke(command, tmp_path, env={PASSWORD_ENV: SECRET})
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [SECRET]


def test_empty_env_is_unset(seen: list[str], tmp_path: Path):
    result = invoke("run", tmp_path, env={PASSWORD_ENV: ""})
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [def_pass]


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize("option", ["--password-file", "--passwd-file"])
def test_file(command: str, option: str, seen: list[str], tmp_path: Path):
    file = tmp_path / "rcon-password"
    file.write_text(SECRET + "\n")
    result = invoke(command, tmp_path, option, str(file))
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [SECRET]


@pytest.mark.parametrize(
    "content, password",
    [
        (f"{SECRET}", SECRET),  # no newline
        (f"{SECRET}\r\n", SECRET),  # windows line ending
        (f" {SECRET} \nignored\n", f" {SECRET} "),  # only the first line, as is
    ],
)
def test_file_content(content: str, password: str, seen: list[str], tmp_path: Path):
    file = tmp_path / "rcon-password"
    file.write_bytes(content.encode())
    result = invoke("run", tmp_path, "--password-file", str(file))
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [password]


@pytest.mark.parametrize(
    "options, env, expected",
    [
        (["--password", "flag"], "env", "flag"),
        (["--password", "flag", "--password-file", "FILE"], "env", "flag"),
        (["--password-file", "FILE"], "env", "file"),
        ([], "env", "env"),
        (["--password", ""], "env", ""),  # an explicit empty password is kept
    ],
)
def test_precedence(
    options: list[str], env: str, expected: str, seen: list[str], tmp_path: Path
):
    """--password, then --password-file, then MCIWB_PASSWORD, then the default"""
    file = tmp_path / "rcon-password"
    file.write_text("file\n")
    options = [str(file) if o == "FILE" else o for o in options]
    result = invoke("run", tmp_path, *options, env={PASSWORD_ENV: env})
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [expected]


def test_restore_starts_with_the_file_password(seen: list[str], tmp_path: Path):
    """restore gives the password from the file to the server it restarts"""
    file = tmp_path / "rcon-password"
    file.write_text(SECRET)
    result = invoke("restore", tmp_path, "--password-file", str(file))
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [SECRET]


def bad_file(kind: str, tmp_path: Path) -> tuple[Path, str]:
    """a password file that cannot be used, and the error expected"""
    file = tmp_path / "rcon-password"
    if kind == "missing":
        return file, "cannot read the password file"
    if kind == "directory":
        file.mkdir()
        return file, "cannot read the password file"
    if kind == "binary":
        file.write_bytes(b"\xff\xfe" + SECRET.encode())
        return file, "is not UTF-8 text"
    file.write_text("\n" + SECRET if kind == "blank first line" else "")
    return file, "has no password"


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize(
    "kind", ["missing", "directory", "binary", "empty", "blank first line"]
)
def test_bad_file(
    command: str,
    kind: str,
    seen: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
):
    """an unusable password file is a clear error, before connecting"""
    file, error = bad_file(kind, tmp_path)
    result = invoke(command, tmp_path, "--password-file", str(file))
    assert result.exit_code == 1, (result.output, result.exception)
    assert error in result.output
    assert str(file) in result.output
    assert seen == []
    # the password is not shown, even partly
    assert SECRET not in result.output + capsys.readouterr().err


def test_unreadable_file(seen: list[str], tmp_path: Path):
    file = tmp_path / "rcon-password"
    file.write_text(SECRET)
    file.chmod(0)
    try:
        file.read_text()
    except PermissionError:
        pass
    else:
        pytest.skip("root can read any file")
    result = invoke("run", tmp_path, "--password-file", str(file))
    assert result.exit_code == 1, (result.output, result.exception)
    assert "cannot read the password file" in result.output
    assert "Permission denied" in result.output
    assert seen == []
    assert SECRET not in result.output


@pytest.mark.parametrize("command", COMMANDS)
@pytest.mark.parametrize(
    "options, env",
    [
        (["--password", SECRET], None),
        (["--password-file", "FILE"], None),
        ([], {PASSWORD_ENV: SECRET}),
    ],
)
def test_password_not_logged(
    command: str,
    options: list[str],
    env: dict | None,
    seen: list[str],
    tmp_path: Path,
    capsys: pytest.CaptureFixture,
):
    """the password is not in the output, even with --debug"""
    file = tmp_path / "rcon-password"
    file.write_text(SECRET)
    options = [str(file) if o == "FILE" else o for o in options]
    result = invoke(command, tmp_path, "--debug", *options, env=env)
    assert result.exit_code == 3, (result.output, result.exception)
    assert seen == [SECRET]
    assert SECRET not in result.output + capsys.readouterr().err


def test_password_not_logged_connecting(
    mock_client, monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    """connecting with --debug does not log the password"""
    from tests.mockclient import MockClient

    monkeypatch.setattr("mciwb.iwb.Client", MockClient)
    args = ["run", str(tmp_path / "build.py"), "--port", "20400", "--debug"]
    (tmp_path / "build.py").write_text("world.cmd('time set day')\n")
    result = runner.invoke(cli, args, env={PASSWORD_ENV: SECRET})
    assert result.exit_code == 0, (result.output, result.exception)
    assert "DEBUG" in result.output
    assert SECRET not in result.output


def test_password_not_in_wrong_password_error(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
):
    from rcon.exceptions import WrongPassword

    def wrong(*args, **kwargs):
        raise WrongPassword()

    monkeypatch.setattr(mciwb.__main__, "Iwb", wrong)
    result = runner.invoke(cli, ["shell", "--debug"], env={PASSWORD_ENV: SECRET})
    assert result.exit_code == 1
    assert "Wrong RCON password" in result.output
    assert SECRET not in result.output
