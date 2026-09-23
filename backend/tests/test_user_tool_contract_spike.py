"""Contract checks for user-authored Tool assets."""

import asyncio
import json
from pathlib import Path

import pytest
from agents import FunctionTool

from agent_studio.spikes.user_tool_contract import (
    ToolContractError,
    load_user_tool,
    snapshot_tool,
    verify_snapshot,
    with_setup_description,
)


def write_tool(tmp_path: Path, source: str) -> Path:
    path = tmp_path / "tool.py"
    path.write_text(source, encoding="utf-8")
    return path


@pytest.mark.parametrize("declaration", ["def", "async def"])
def test_sync_and_async_functions_generate_a_stable_snapshot(
    declaration: str, tmp_path: Path
) -> None:
    path = write_tool(
        tmp_path,
        f'''{declaration} weather(latitude: float, days: int = 1) -> str:
    """Fetch a weather forecast."""
    return f"{{latitude}}:{{days}}"

tool = weather
''',
    )

    first = load_user_tool(path)
    serialized = json.loads(json.dumps(snapshot_tool(first), sort_keys=True))
    second = load_user_tool(path)

    assert isinstance(first, FunctionTool)
    assert serialized == snapshot_tool(second)
    assert serialized["name"] == "weather"
    assert serialized["description"] == "Fetch a weather forecast."
    assert serialized["input_schema"]["properties"]["latitude"]["type"] == "number"
    assert serialized["input_schema"]["properties"]["days"]["type"] == "integer"
    verify_snapshot(second, serialized)


def test_prebuilt_sdk_function_tool_is_supported(tmp_path: Path) -> None:
    tool = load_user_tool(
        write_tool(
            tmp_path,
            '''from agents import function_tool

@function_tool
async def weather(latitude: float) -> str:
    """SDK weather."""
    return str(latitude)

tool = weather
''',
        )
    )
    assert tool.name == "weather"
    assert tool.description == "SDK weather."


@pytest.mark.parametrize(
    ("source", "error"),
    [
        ("value = 1\n", "tool_variable_missing"),
        ("tool = 1\n", "invalid_tool_object"),
        (
            "class CallableTool:\n    def __call__(self, value: int) -> str:\n"
            "        return str(value)\ntool = CallableTool()\n",
            "unsupported_tool_callable",
        ),
    ],
)
def test_missing_and_unsupported_tool_values_are_stable_errors(
    source: str, error: str, tmp_path: Path
) -> None:
    with pytest.raises(ToolContractError, match=f"^{error}$"):
        load_user_tool(write_tool(tmp_path, source))


def test_schema_description_and_name_drift_are_rejected(tmp_path: Path) -> None:
    path = write_tool(
        tmp_path,
        'def weather(latitude: float) -> str:\n    """Weather."""\n'
        "    return str(latitude)\ntool = weather\n",
    )
    expected = snapshot_tool(load_user_tool(path))

    for key, changed in (
        ("name", "renamed"),
        ("description", "Changed."),
        ("input_schema", {"type": "object"}),
    ):
        drifted = dict(expected)
        drifted[key] = changed
        with pytest.raises(ToolContractError, match=r"^tool_contract_mismatch$"):
            verify_snapshot(load_user_tool(path), drifted)  # type: ignore[arg-type]


def test_setup_descriptions_are_isolated_for_concurrent_execution(
    tmp_path: Path,
) -> None:
    source_tool = load_user_tool(
        write_tool(
            tmp_path,
            "async def weather(latitude: float) -> str:\n"
            '    """Version description."""\n'
            "    return str(latitude)\ntool = weather\n",
        )
    )

    async def build(description: str) -> str:
        await asyncio.sleep(0)
        return with_setup_description(source_tool, description).description

    async def both() -> list[str]:
        return list(await asyncio.gather(build("setup one"), build("setup two")))

    assert asyncio.run(both()) == ["setup one", "setup two"]
    assert source_tool.description == "Version description."
