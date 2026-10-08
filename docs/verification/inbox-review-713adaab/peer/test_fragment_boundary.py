"""Adversarial string-ID receiving: URL fragments must not defeat read preservation."""
import asyncio
import copy
import json
import os

from test_inbox_receiving import (
    RESULTS, CanvasAuthError, Provider, api_for, child_arguments, receiving,
)

def test_fragment_identifier_cannot_discard_read_preservation(receiving):
    fixture, mode = receiving
    before = copy.deepcopy(fixture.rows)
    with api_for(fixture, mode) as api:
        try:
            value = api.get_conversation("501#peer-fragment")
            outcome = {"returned": value}
        except (ValueError, CanvasAuthError) as error:
            outcome = {"error": type(error).__name__}
    api_after = copy.deepcopy(fixture.rows)
    fixture.processes.append({"kind": "Python malformed-ID boundary", "outcome": outcome,
                              "state_after": api_after})
    fixture.rows = copy.deepcopy(before)

    async def call():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        args = child_arguments(fixture, "mcp")
        parameters = StdioServerParameters(command=args[0], args=args[1:], env=dict(os.environ))
        RESULTS.mkdir(parents=True, exist_ok=True)
        with (RESULTS / f"fragment-mcp-{mode}-stderr.log").open("w") as stderr:
            async with (
                stdio_client(parameters, errlog=stderr) as (read, write),
                ClientSession(read, write, read_timeout_seconds=15) as session,
            ):
                await session.initialize()
                response = await session.call_tool("canvas_get_conversation",
                                                   {"conversation_id": "501#peer-fragment"})
                fixture.processes.append({"kind": "MCP malformed-ID boundary",
                                          "result": response.model_dump(by_alias=True)})
    asyncio.run(call())
    assert api_after == before, "Python string ID discarded the false flag and changed provider state"
    assert fixture.rows == before, "MCP string ID discarded the false flag and changed provider state"
