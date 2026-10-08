"""Independent admission boundaries; no owner source changes."""
import asyncio
import copy
import os

import pytest

from test_inbox_receiving import (
    RESULTS, CanvasAPI, api_for, child_arguments, receiving,
)

INVALID_IDS = [
    "501#fragment", "501?auto_mark_as_read=true", "../501", "501/../501",
    "%35%30%31", "５01", "٥٠١", " 501 ", "", "000",
    0, -501, True, False, 501.0, None, [], {},
]

def test_invalid_ids_refuse_before_any_transport_and_positive_strings_remain_admitted(receiving):
    fixture, mode = receiving
    before = copy.deepcopy(fixture.rows)
    with api_for(fixture, mode) as api:
        for value in INVALID_IDS:
            with pytest.raises(TypeError if type(value) not in (int, str) else ValueError):
                api.get_conversation(value)
    assert fixture.requests == []

    class AdmissionOnly:
        def __init__(self):
            self.calls = []
        def request(self, method, path, *, params):
            self.calls.append({"method": method, "path": path, "params": params})
            return {"admission_only": True}

    admission = AdmissionOnly()
    api = CanvasAPI(admission)
    for value in [501, "501", "000501"]:
        assert api.get_conversation(value) == {"admission_only": True}
    assert admission.calls == [
        {"method": "GET", "path": f"/api/v1/conversations/{value}", "params": {"auto_mark_as_read": False}}
        for value in [501, "501", "000501"]
    ]
    fixture.processes.append({"kind": "positive admission only; no server-semantic claim", "calls": admission.calls})

    async def call():
        from mcp import ClientSession, StdioServerParameters
        from mcp.client.stdio import stdio_client
        args = child_arguments(fixture, "mcp")
        parameters = StdioServerParameters(command=args[0], args=args[1:], env=dict(os.environ))
        RESULTS.mkdir(parents=True, exist_ok=True)
        with (RESULTS / f"admission-mcp-{mode}-stderr.log").open("w") as stderr:
            async with (
                stdio_client(parameters, errlog=stderr) as (read, write),
                ClientSession(read, write, read_timeout_seconds=15) as session,
            ):
                await session.initialize()
                for value in INVALID_IDS:
                    response = await session.call_tool("canvas_get_conversation", {"conversation_id": value})
                    wire = response.model_dump(by_alias=True)
                    fixture.processes.append({"kind": "MCP invalid-ID admission", "argument": value, "result": wire})
                    assert wire.get("isError") is True
    asyncio.run(call())
    assert fixture.requests == []
    assert fixture.rows == before
