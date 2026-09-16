"""Serializable SDK tool registry experiment, separate from the product registry."""

from collections.abc import Callable, Mapping
from typing import Any, TypedDict

from agents import FunctionTool


class ToolManifest(TypedDict):
    registry_key: str
    name: str
    description: str
    schema: dict[str, Any]  # SDK JSON schema boundary


def export_tool(tool: FunctionTool, registry_key: str) -> ToolManifest:
    return {
        "registry_key": registry_key,
        "name": tool.name,
        "description": tool.description,
        "schema": tool.params_json_schema,
    }


def restore_tool(
    manifest: ToolManifest,
    registry: Mapping[str, Callable[[str, str], FunctionTool]],
) -> FunctionTool:
    factory = registry.get(manifest["registry_key"])
    if factory is None:
        raise ValueError("unknown_tool_implementation")
    tool = factory(manifest["name"], manifest["description"])
    if tool.params_json_schema != manifest["schema"]:
        raise ValueError("tool_schema_mismatch")
    return tool
