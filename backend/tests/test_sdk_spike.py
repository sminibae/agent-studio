"""Executable compatibility checks for the pinned Agents SDK, without API calls."""

import asyncio

import pytest
from agents import Agent, FunctionTool, ModelSettings, RunConfig, Runner, function_tool
from agents.exceptions import MaxTurnsExceeded, ModelBehaviorError
from agents.testing import ModelStep, ScriptedModel, assistant_message, function_call


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
