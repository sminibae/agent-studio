"""Executable compatibility checks for the pinned Agents SDK, without API calls."""

import asyncio

import pytest
from agents import (
    Agent,
    FunctionTool,
    ModelSettings,
    RunConfig,
    RunContextWrapper,
    RunHooks,
    Runner,
    Tool,
    ToolExecutionConfig,
    function_tool,
)
from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError, UserError
from agents.items import ModelResponse
from agents.model_settings import ModelRetryBackoffSettings, ModelRetrySettings
from agents.retry import ModelRetryAdvice, retry_policies
from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call
from agents.usage import Usage


def weather_tool(description: str) -> FunctionTool:
    async def weather(latitude: float, longitude: float) -> str:
        return f"{latitude},{longitude}: 20 C"

    return function_tool(
        weather, name_override="weather", description_override=description
    )


def test_typed_tool_schema_and_description_are_per_instance() -> None:
    first = weather_tool("first description")
    second = weather_tool("second description")
    assert first.params_json_schema["properties"]["latitude"]["type"] == "number"
    assert first.description == "first description"
    assert second.description == "second description"


def test_concurrent_setups_keep_their_own_description() -> None:
    async def one(description: str) -> str:
        model = ScriptedModel([ModelStep(output=[assistant_message("done")])])
        await Runner.run(
            Agent(name="weather", model=model, tools=[weather_tool(description)]),
            "weather?",
            run_config=RunConfig(tracing_disabled=True),
        )
        tool = model.calls[0].tools[0]
        assert isinstance(tool, FunctionTool)
        return tool.description

    async def both() -> list[str]:
        return list(await asyncio.gather(one("first"), one("second")))

    assert asyncio.run(both()) == [
        "first",
        "second",
    ]


@pytest.mark.parametrize("arguments", ['{"latitude":"bad","longitude":2}', "{"])
def test_invalid_tool_arguments_do_not_invoke_weather(arguments: str) -> None:
    async def run() -> None:
        model = ScriptedModel(
            [
                ModelStep(output=[function_call("weather", arguments, call_id="bad")]),
                ModelStep(output=[assistant_message("done")]),
            ]
        )
        result = await Runner.run(
            Agent(name="weather", model=model, tools=[weather_tool("weather")]),
            "weather?",
            run_config=RunConfig(tracing_disabled=True),
        )
        assert "37.5,127.0" not in str(result.new_items)
        assert "Error" in str(result.new_items)

    asyncio.run(run())


def test_explicit_error_policy_rejects_bad_arguments_and_tool_exception() -> None:
    async def broken(value: int) -> str:
        raise ValueError(f"bad value: {value}")

    async def run() -> None:
        tool = function_tool(broken, failure_error_function=None)
        bad_args = ScriptedModel(
            [
                ModelStep(
                    output=[function_call("broken", '{"value":"bad"}', call_id="a")]
                )
            ]
        )
        with pytest.raises(ModelBehaviorError):
            await Runner.run(
                Agent(name="broken", model=bad_args, tools=[tool]),
                "go",
                run_config=RunConfig(tracing_disabled=True),
            )
        raised = ScriptedModel(
            [ModelStep(output=[function_call("broken", {"value": 1}, call_id="b")])]
        )
        with pytest.raises(UserError, match="Error running tool broken"):
            await Runner.run(
                Agent(name="broken", model=raised, tools=[tool]),
                "go",
                run_config=RunConfig(tracing_disabled=True),
            )

    asyncio.run(run())


def test_local_hooks_survive_disabled_external_tracing() -> None:
    class LocalEvents(RunHooks[None]):
        def __init__(self) -> None:
            self.events: list[str] = []

        async def on_llm_end(
            self,
            context: RunContextWrapper[None],
            agent: Agent[None],
            response: ModelResponse,
        ) -> None:
            self.events.append(f"model:{response.usage.input_tokens}")

        async def on_tool_end(
            self,
            context: RunContextWrapper[None],
            agent: Agent[None],
            tool: Tool,
            result: object,
        ) -> None:
            self.events.append(f"tool:{tool.name}")

    async def run() -> None:
        model = ScriptedModel(
            [
                ModelStep(
                    output=[
                        function_call(
                            "weather", {"latitude": 1, "longitude": 2}, call_id="a"
                        )
                    ],
                    usage=Usage(input_tokens=7, output_tokens=3, total_tokens=10),
                ),
                ModelStep(output=[assistant_message("done")]),
            ]
        )
        events = LocalEvents()
        await Runner.run(
            Agent(name="weather", model=model, tools=[weather_tool("weather")]),
            "weather?",
            hooks=events,
            run_config=RunConfig(tracing_disabled=True),
        )
        assert events.events == ["model:7", "tool:weather", "model:0"]

    asyncio.run(run())


def test_runner_retry_is_explicit_and_counts_model_attempts() -> None:
    async def run(retries: int) -> tuple[str, int]:
        model = ScriptedModel(
            [
                ModelStep(
                    error=RuntimeError("transient"),
                    retry_advice=ModelRetryAdvice(suggested=True, replay_safety="safe"),
                ),
                ModelStep(output=[assistant_message("recovered")]),
            ]
        )
        agent = Agent(
            name="retry",
            model=model,
            model_settings=ModelSettings(
                retry=ModelRetrySettings(
                    max_retries=retries,
                    backoff=ModelRetryBackoffSettings(
                        initial_delay=0, max_delay=0, jitter=False
                    ),
                    policy=retry_policies.provider_suggested(),
                )
            ),
        )
        if retries == 0:
            with pytest.raises(RuntimeError, match="transient"):
                await Runner.run(
                    agent, "go", run_config=RunConfig(tracing_disabled=True)
                )
            return "failed", len(model.calls)
        result = await Runner.run(
            agent, "go", run_config=RunConfig(tracing_disabled=True)
        )
        return str(result.final_output), len(model.calls)

    assert asyncio.run(run(0)) == ("failed", 1)
    assert asyncio.run(run(1)) == ("recovered", 2)


def test_cancelled_async_tool_allows_heartbeat_and_no_second_model_call() -> None:
    async def run() -> None:
        entered = asyncio.Event()
        heartbeat = 0

        async def slow_tool() -> str:
            entered.set()
            await asyncio.sleep(10)
            return "late"

        async def tick() -> None:
            nonlocal heartbeat
            while True:
                heartbeat += 1
                await asyncio.sleep(0.01)

        model = ScriptedModel(
            [ModelStep(output=[function_call("slow_tool", {}, call_id="a")])]
        )
        agent = Agent(
            name="slow",
            model=model,
            tools=[function_tool(slow_tool, failure_error_function=None)],
        )
        ticker = asyncio.create_task(tick())
        task = asyncio.create_task(
            Runner.run(agent, "go", run_config=RunConfig(tracing_disabled=True))
        )
        try:
            await asyncio.wait_for(entered.wait(), timeout=1)
            await asyncio.sleep(0.03)
            assert heartbeat >= 2
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
            assert len(model.calls) == 1
        finally:
            ticker.cancel()
            await asyncio.gather(ticker, return_exceptions=True)

    asyncio.run(run())


@pytest.mark.parametrize("concurrency,expected", [(1, 1), (2, 2)])
def test_local_tool_concurrency_is_explicit(concurrency: int, expected: int) -> None:
    async def run() -> int:
        active = 0
        maximum = 0

        async def slow(value: int) -> str:
            nonlocal active, maximum
            active += 1
            maximum = max(maximum, active)
            await asyncio.sleep(0.02)
            active -= 1
            return str(value)

        model = ScriptedModel(
            [
                ModelStep(
                    output=[
                        function_call("slow", {"value": 1}, call_id="a"),
                        function_call("slow", {"value": 2}, call_id="b"),
                    ]
                ),
                ModelStep(output=[assistant_message("done")]),
            ]
        )
        await Runner.run(
            Agent(
                name="parallel",
                model=model,
                tools=[function_tool(slow)],
                model_settings=ModelSettings(parallel_tool_calls=True),
            ),
            "go",
            run_config=RunConfig(
                tracing_disabled=True,
                tool_execution=ToolExecutionConfig(
                    max_function_tool_concurrency=concurrency
                ),
            ),
        )
        return maximum

    assert asyncio.run(run()) == expected


@pytest.mark.parametrize("parallel", [True, False])
def test_scripted_model_calls_weather_without_provider(parallel: bool) -> None:
    async def run() -> None:
        model = ScriptedModel(
            [
                ModelStep(
                    output=[
                        function_call(
                            "weather",
                            {"latitude": 37.5, "longitude": 127.0},
                            call_id="call-1",
                        )
                    ]
                ),
                ModelStep(output=[assistant_message("The weather is 20 C")]),
            ]
        )
        agent = Agent(
            name="weather",
            model=model,
            tools=[weather_tool("weather description")],
            model_settings=ModelSettings(parallel_tool_calls=parallel),
        )
        result = await Runner.run(
            agent, "weather?", run_config=RunConfig(tracing_disabled=True)
        )
        assert result.final_output == "The weather is 20 C"
        assert "37.5,127.0: 20 C" in str(result.new_items)
        assert len(model.calls) == 2
        assert model.calls[0].model_settings.parallel_tool_calls is parallel

    asyncio.run(run())


def test_unknown_tool_is_an_error() -> None:
    async def run() -> None:
        model = ScriptedModel(
            [ModelStep(output=[function_call("unknown", {}, call_id="call-1")])]
        )
        agent = Agent(name="weather", model=model, tools=[weather_tool("weather")])
        with pytest.raises(ModelBehaviorError):
            await Runner.run(
                agent, "weather?", run_config=RunConfig(tracing_disabled=True)
            )

    asyncio.run(run())


def test_turn_limit_stops_repeated_tool_loop() -> None:
    async def run() -> None:
        model = ScriptedModel(
            [
                ModelStep(
                    output=[
                        function_call(
                            "weather", {"latitude": 1, "longitude": 2}, call_id="a"
                        )
                    ]
                )
            ]
        )
        agent = Agent(name="weather", model=model, tools=[weather_tool("weather")])
        with pytest.raises(MaxTurnsExceeded):
            await Runner.run(
                agent,
                "weather?",
                max_turns=1,
                run_config=RunConfig(tracing_disabled=True),
            )

    asyncio.run(run())
