"""Prototype contract for loading a user-authored Python tool."""

from __future__ import annotations

import copy
import dataclasses
import inspect
import runpy
from pathlib import Path
from typing import Any, TypedDict

from agents import FunctionTool, function_tool


class ToolContractError(ValueError):
    """A stable failure raised while evaluating a user Tool asset."""


class ToolSnapshot(TypedDict):
    name: str
    description: str
    input_schema: dict[str, Any]


def load_user_tool(path: Path) -> FunctionTool:
    """Evaluate ``path`` and convert its designated ``tool`` value."""
    namespace = runpy.run_path(str(path))
    if "tool" not in namespace:
        raise ToolContractError("tool_variable_missing")

    value = namespace["tool"]
    if isinstance(value, FunctionTool):
        return value
    if inspect.isfunction(value):
        try:
            return function_tool(value, failure_error_function=None)
        except (TypeError, ValueError) as error:
            raise ToolContractError("invalid_tool_callable") from error
    if callable(value):
        raise ToolContractError("unsupported_tool_callable")
    raise ToolContractError("invalid_tool_object")


def snapshot_tool(tool: FunctionTool) -> ToolSnapshot:
    """Return the JSON-compatible fields persisted with a Tool Version."""
    return {
        "name": tool.name,
        "description": tool.description,
        "input_schema": copy.deepcopy(tool.params_json_schema),
    }


def verify_snapshot(tool: FunctionTool, expected: ToolSnapshot) -> None:
    """Fail closed when re-evaluation no longer matches the published Version."""
    if snapshot_tool(tool) != expected:
        raise ToolContractError("tool_contract_mismatch")


def with_setup_description(tool: FunctionTool, description: str) -> FunctionTool:
    """Build an execution-local Tool without mutating the Version instance."""
    return dataclasses.replace(tool, description=description)
