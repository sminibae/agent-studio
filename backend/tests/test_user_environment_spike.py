"""Prototype checks; subprocess separation alone is not a security sandbox."""

import sys
import venv
from pathlib import Path

import pytest

from agent_studio.spikes.user_environment import (
    EnvironmentError,
    evaluate_prompt,
    resolve_named_environment,
)


@pytest.fixture
def user_venv(tmp_path: Path) -> Path:
    path = tmp_path / "my-weather-venv"
    venv.EnvBuilder(with_pip=False).create(path)
    python = path / "bin" / "python"
    assert python.exists()
    return python


def test_named_venv_and_dotenv_are_used_without_service_environment(
    user_venv: Path, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    dotenv = tmp_path / ".env.weather"
    dotenv.write_text("OPENAI_API_KEY=user-key\nCUSTOM_VALUE=first\n")
    monkeypatch.setenv("AGENT_STUDIO_DATABASE_URL", "service-secret")
    source = (
        "import os\n"
        "system_prompt = os.environ['CUSTOM_VALUE'] + ':' + "
        "str('AGENT_STUDIO_DATABASE_URL' in os.environ)\n"
    )
    assert evaluate_prompt(user_venv, dotenv, source) == "first:False"
    dotenv.write_text("CUSTOM_VALUE=second\n")
    assert evaluate_prompt(user_venv, dotenv, source) == "second:False"


def test_result_type_and_timeout_are_distinct(user_venv: Path, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env.test"
    dotenv.write_text("")
    with pytest.raises(EnvironmentError, match="invalid_result_type"):
        evaluate_prompt(user_venv, dotenv, "system_prompt = 123")
    with pytest.raises(EnvironmentError, match="timeout"):
        evaluate_prompt(user_venv, dotenv, "while True: pass", timeout_s=0.2)


def test_source_can_observe_its_own_dotenv(user_venv: Path, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env.test"
    dotenv.write_text("CUSTOM_VALUE=visible-to-user-code\n")
    assert (
        evaluate_prompt(
            user_venv, dotenv, "import os\nsystem_prompt = os.environ['CUSTOM_VALUE']"
        )
        == "visible-to-user-code"
    )


def test_test_interpreter_is_distinct_from_user_venv(user_venv: Path) -> None:
    assert user_venv.resolve() != Path(sys.executable).resolve()


def test_output_limit_and_path_escape(user_venv: Path, tmp_path: Path) -> None:
    dotenv = tmp_path / ".env.test"
    dotenv.write_text("")
    with pytest.raises(EnvironmentError, match="output_limit_exceeded"):
        evaluate_prompt(user_venv, dotenv, "print('x' * 10000)\nsystem_prompt='ok'")
    with pytest.raises(EnvironmentError, match="invalid_environment_name"):
        resolve_named_environment(tmp_path, "owner", "../other", ".env.test")
    owner = tmp_path / "owner"
    (owner / "venvs").mkdir(parents=True)
    (owner / "venvs" / "bad").symlink_to(tmp_path)
    with pytest.raises(EnvironmentError, match="environment_path_escape"):
        resolve_named_environment(tmp_path, "owner", "bad", ".env.test")


def test_host_subprocess_still_reads_unmounted_host_files(
    user_venv: Path, tmp_path: Path
) -> None:
    """Demonstrates why this prototype cannot be wired into the product."""
    dotenv = tmp_path / ".env.test"
    dotenv.write_text("")
    outside = tmp_path / "other-owner-secret"
    outside.write_text("visible")
    assert (
        evaluate_prompt(
            user_venv, dotenv, f"system_prompt = open({str(outside)!r}).read()"
        )
        == "visible"
    )
