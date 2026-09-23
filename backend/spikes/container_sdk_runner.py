"""Run one user-authored SDK tool inside the selected Python environment."""

from __future__ import annotations

import asyncio
import importlib.metadata
import json
import runpy
import sys
from pathlib import Path
from typing import Any

# ``-I`` intentionally excludes the script directory. The smoke mounts only this
# prototype package, so add its explicit read-only location rather than user paths.
sys.path.insert(0, str(Path(__file__).parent))


def _write_result(path: Path, payload: dict[str, Any]) -> None:
    path.write_text(json.dumps(payload, sort_keys=True), encoding="utf-8")


async def _run(
    prompt_path: Path,
    tool_path: Path,
    expected_contract_path: Path,
    setup_description: str,
) -> dict[str, Any]:
    try:
        from agents import (
            Agent,
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

    from user_tool_contract import (  # type: ignore[import-not-found]
        ToolContractError,
        load_user_tool,
        verify_snapshot,
        with_setup_description,
    )

    prompt_namespace = runpy.run_path(str(prompt_path))
    system_prompt = prompt_namespace.get("system_prompt")
    if not isinstance(system_prompt, str):
        return {"error": "invalid_prompt"}

    try:
        version_tool = load_user_tool(tool_path)
        expected_contract = json.loads(
            expected_contract_path.read_text(encoding="utf-8")
        )
        verify_snapshot(version_tool, expected_contract)
    except ToolContractError as error:
        return {"error": str(error)}
    tool = with_setup_description(version_tool, setup_description)

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
        "tool_description": tool.description,
        "tool_name": tool.name,
        "tool_schema": tool.params_json_schema,
    }


def main() -> None:
    if len(sys.argv) != 6:
        raise SystemExit(
            "usage: container_sdk_runner.py PROMPT TOOL CONTRACT DESCRIPTION RESULT"
        )
    prompt_path, tool_path, contract_path = map(Path, sys.argv[1:4])
    description = sys.argv[4]
    result_path = Path(sys.argv[5])
    try:
        payload = asyncio.run(_run(prompt_path, tool_path, contract_path, description))
    except BaseException as error:
        payload = {"error": "execution_error", "error_type": type(error).__name__}
    _write_result(result_path, payload)


if __name__ == "__main__":
    main()
