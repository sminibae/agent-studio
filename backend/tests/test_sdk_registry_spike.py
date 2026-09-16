"""Tool manifests must round-trip without importing arbitrary user modules."""

import json

import pytest
from agents import FunctionTool, function_tool

from agent_studio.spikes.sdk_registry import export_tool, restore_tool


async def weather(latitude: float, longitude: float) -> str:
    return f"{latitude},{longitude}"


def weather_factory(name: str, description: str) -> FunctionTool:
    return function_tool(weather, name_override=name, description_override=description)


def test_manifest_round_trip_restores_schema_and_description() -> None:
    original = weather_factory("weather", "first description")
    manifest = export_tool(original, "weather.current")
    restored = restore_tool(
        json.loads(json.dumps(manifest)), {"weather.current": weather_factory}
    )
    assert restored.name == original.name
    assert restored.description == original.description
    assert restored.params_json_schema == original.params_json_schema
    assert (
        weather_factory("weather", "second description").description
        != restored.description
    )


def test_unknown_registry_key_and_schema_drift_fail_closed() -> None:
    manifest = export_tool(weather_factory("weather", "description"), "weather.current")
    with pytest.raises(ValueError, match="unknown_tool_implementation"):
        restore_tool(manifest, {})
    manifest["schema"] = {"type": "object"}
    with pytest.raises(ValueError, match="tool_schema_mismatch"):
        restore_tool(manifest, {"weather.current": weather_factory})
