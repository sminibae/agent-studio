"""Named-venv/dotenv execution prototype; does not isolate host filesystem."""

import json
import os
import re
import signal
import subprocess
import tempfile
from pathlib import Path


class EnvironmentError(Exception):
    """A prototype execution failed with a stable error code."""


_KEY = re.compile(r"[A-Za-z_][A-Za-z0-9_]*\Z")
_NAME = re.compile(r"\.?[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_CHILD = """
import json
import resource
import runpy
import sys

source, result, output_limit = sys.argv[1:]
resource.setrlimit(resource.RLIMIT_FSIZE, (int(output_limit), int(output_limit)))
try:
    namespace = runpy.run_path(source)
    if 'system_prompt' not in namespace:
        payload = {'error': 'missing_result'}
    elif not isinstance(namespace['system_prompt'], str):
        payload = {'error': 'invalid_result_type'}
    else:
        payload = {'value': namespace['system_prompt']}
except BaseException:
    payload = {'error': 'execution_error'}
with open(result, 'w', encoding='utf-8') as stream:
    json.dump(payload, stream)
"""


def _read_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if not line or line.lstrip().startswith("#"):
            continue
        key, separator, value = line.partition("=")
        if not separator or not _KEY.fullmatch(key):
            raise EnvironmentError("invalid_dotenv")
        if key.startswith("AGENT_STUDIO_") or key in {
            "PATH",
            "PYTHONPATH",
            "PYTHONHOME",
            "VIRTUAL_ENV",
        }:
            raise EnvironmentError("reserved_dotenv_key")
        if key in values:
            raise EnvironmentError("duplicate_dotenv_key")
        values[key] = value
    return values


def resolve_named_environment(
    root: Path, owner_id: str, venv_name: str, env_name: str
) -> tuple[Path, Path]:
    """Resolve owner-scoped names; refuse traversal and directory symlinks."""
    if not all(
        _NAME.fullmatch(name) and ".." not in name
        for name in (owner_id, venv_name, env_name)
    ):
        raise EnvironmentError("invalid_environment_name")
    owner = root / owner_id
    venv = owner / "venvs" / venv_name
    dotenv = owner / "envs" / env_name
    if not venv.resolve().is_relative_to(owner.resolve()):
        raise EnvironmentError("environment_path_escape")
    if not dotenv.resolve().is_relative_to(owner.resolve()):
        raise EnvironmentError("environment_path_escape")
    return venv / "bin" / "python", dotenv


def evaluate_prompt(
    python: Path,
    dotenv: Path,
    source: str,
    *,
    timeout_s: float = 2.0,
    output_limit_bytes: int = 4096,
) -> str:
    """Evaluate one prompt with the selected Python and dotenv in a fresh process.

    This only proves interpreter/env selection. Host file, network and memory isolation
    are intentionally unproven and must be added before product integration.
    """
    if not python.is_file() or not os.access(python, os.X_OK):
        raise EnvironmentError("python_unavailable")
    if timeout_s <= 0 or output_limit_bytes < 1024:
        raise EnvironmentError("invalid_limit")
    values = _read_dotenv(dotenv)
    child_env = {
        "PATH": str(python.parent),
        "PYTHONNOUSERSITE": "1",
        "PYTHONDONTWRITEBYTECODE": "1",
        "LANG": "C.UTF-8",
        **values,
    }
    with tempfile.TemporaryDirectory(prefix="agent-studio-spike-") as directory:
        work = Path(directory)
        source_path = work / "asset.py"
        result_path = work / "result.json"
        source_path.write_text(source, encoding="utf-8")
        with (work / "output.txt").open("w+b") as output:
            process = subprocess.Popen(
                [
                    str(python),
                    "-I",
                    "-c",
                    _CHILD,
                    str(source_path),
                    str(result_path),
                    str(output_limit_bytes),
                ],
                cwd=work,
                env=child_env,
                stdin=subprocess.DEVNULL,
                stdout=output,
                stderr=subprocess.STDOUT,
                start_new_session=True,
            )
            try:
                process.wait(timeout=timeout_s)
            except subprocess.TimeoutExpired as error:
                os.killpg(process.pid, signal.SIGKILL)
                process.wait()
                raise EnvironmentError("timeout") from error
            output.seek(0, os.SEEK_END)
            if output.tell() >= output_limit_bytes:
                raise EnvironmentError("output_limit_exceeded")
        if process.returncode != 0 or not result_path.exists():
            raise EnvironmentError("execution_error")
        try:
            payload = json.loads(result_path.read_text(encoding="utf-8"))
        except (json.JSONDecodeError, UnicodeError) as error:
            raise EnvironmentError("invalid_result") from error
        if "error" in payload:
            raise EnvironmentError(payload["error"])
        value = payload.get("value")
        if not isinstance(value, str):
            raise EnvironmentError("invalid_result_type")
        return value
