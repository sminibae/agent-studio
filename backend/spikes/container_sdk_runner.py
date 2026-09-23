"""Run one user-authored SDK tool inside the selected Python environment."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import runpy
import sys
from pathlib import Path
from typing import Any


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


async def _run(
    prompt_path: Path, tool_path: Path, expected_schema_path: Path
) -> dict[str, Any]:
    try:
        from agents import (
            Agent,
            FunctionTool,
            RunConfig,
            RunContextWrapper,
            RunHooks,
            Runner,
        )
        from agents.items import ModelResponse
        from agents.testing import (
            ModelStep,
            ScriptedModel,
            assistant_message,
            function_call,
        )
    except ModuleNotFoundError as error:
        if error.name == "agents":
            return {"error": "sdk_unavailable"}
        raise

    prompt_namespace = runpy.run_path(str(prompt_path))
    system_prompt = prompt_namespace.get("system_prompt")
    if not isinstance(system_prompt, str):
        return {"error": "invalid_prompt"}

    tool_namespace = runpy.run_path(str(tool_path))
    tool = tool_namespace.get("tool")
    if not isinstance(tool, FunctionTool):
        return {"error": "invalid_tool_object"}

    expected_schema = json.loads(expected_schema_path.read_text(encoding="utf-8"))
    if tool.params_json_schema != expected_schema:
        return {"error": "tool_schema_mismatch"}

    class LocalEvents(RunHooks[None]):
        def __init__(self) -> None:
            self.values: list[str] = []

        async def on_llm_end(
            self,
            context: RunContextWrapper[None],
            agent: Agent[None],
            response: ModelResponse,
        ) -> None:
            self.values.append("model")

        async def on_tool_end(
            self,
            context: RunContextWrapper[None],
            agent: Agent[None],
            completed_tool: object,
            result: object,
        ) -> None:
            name = getattr(completed_tool, "name", "unknown")
            self.values.append(f"tool:{name}:{result}")

    model = ScriptedModel(
        [
            ModelStep(
                output=[
                    function_call(
                        tool.name,
                        {"latitude": 37.5, "longitude": 127.0},
                        call_id="weather-call",
                    )
                ]
            ),
            ModelStep(output=[assistant_message("weather complete")]),
        ]
    )
    events = LocalEvents()
    result = await Runner.run(
        Agent(
            name="container-spike",
            instructions=system_prompt,
            model=model,
            tools=[tool],
        ),
        "weather?",
        hooks=events,
        run_config=RunConfig(tracing_disabled=True),
    )
    return {
        "events": events.values,
        "final_output": str(result.final_output),
        "sdk_version": importlib.metadata.version("openai-agents"),
        "system_prompt": system_prompt,
        "tool_name": tool.name,
        "tool_schema": tool.params_json_schema,
    }


def main() -> None:
    if len(sys.argv) != 5:
        raise SystemExit("usage: container_sdk_runner.py PROMPT TOOL SCHEMA RESULT")
    prompt_path, tool_path, schema_path, result_path = map(Path, sys.argv[1:])
    try:
        payload = asyncio.run(_run(prompt_path, tool_path, schema_path))
    except BaseException as error:
        payload = {"error": "execution_error", "error_type": type(error).__name__}
    _write_result(result_path, payload)


if __name__ == "__main__":
    main()
