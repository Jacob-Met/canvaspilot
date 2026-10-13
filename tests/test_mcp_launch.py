"""Exercise parsed MCP connection options and invocation client ownership."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path

import httpx
import pytest

from canvaspilot import cli, mcp_server
from canvaspilot.api import CanvasAPI
from canvaspilot.client import CanvasClient


@pytest.fixture(autouse=True)
def connection_environment(monkeypatch):
    monkeypatch.setenv("CANVAS_BASE_URL", "https://environment.example.test/")
    monkeypatch.setenv("CANVAS_API_TOKEN", " synthetic-environment-token ")
    monkeypatch.setenv("CANVAS_PROFILE", "/synthetic-canvaspilot-environment-profile")
    monkeypatch.setattr(mcp_server, "_api", None)


@pytest.mark.parametrize(
    ("flags", "expected_url", "expected_token", "expected_profile"),
    [
        ([], "https://environment.example.test", "synthetic-environment-token", "/synthetic-canvaspilot-environment-profile"),
        (["--base-url", "https://explicit.example.test/"], "https://explicit.example.test", "synthetic-environment-token", "/synthetic-canvaspilot-environment-profile"),
        (["--token", " synthetic-explicit-token "], "https://environment.example.test", "synthetic-explicit-token", "/synthetic-canvaspilot-environment-profile"),
        (["--profile", "relative profile"], "https://environment.example.test", "synthetic-environment-token", "relative profile"),
        (["--token", ""], "https://environment.example.test", None, "/synthetic-canvaspilot-environment-profile"),
        (["--base-url", "", "--profile", ""], "https://environment.example.test", "synthetic-environment-token", "/synthetic-canvaspilot-environment-profile"),
        (["--base-url", "https://explicit.example.test", "--token", "synthetic-explicit-token", "--profile", "/synthetic-canvaspilot-explicit-profile"], "https://explicit.example.test", "synthetic-explicit-token", "/synthetic-canvaspilot-explicit-profile"),
    ],
)
def test_cli_options_reach_real_client(monkeypatch, flags, expected_url, expected_token, expected_profile):
    before = dict(os.environ)
    observed = []

    def run():
        client = mcp_server._get_api().client
        assert isinstance(client, CanvasClient)
        observed.append((client.base_url, client.token, client.profile))
        assert client._http is None
        assert not client.profile.exists()

    monkeypatch.setattr(mcp_server.mcp, "run", run)
    cli.main(["mcp", *flags])
    assert observed == [(expected_url, expected_token, Path(expected_profile))]
    assert dict(os.environ) == before


@pytest.mark.parametrize("server_failure", [False, True])
def test_invocation_client_is_closed_and_prior_binding_restored(monkeypatch, server_failure):
    previous = CanvasAPI(CanvasClient(base_url="https://prior.example.test", token="synthetic-prior-token"))
    previous_http = httpx.Client(transport=httpx.MockTransport(lambda request: httpx.Response(200, json={})))
    previous.client._http = previous_http
    monkeypatch.setattr(mcp_server, "_api", previous)
    requests = []
    active = []

    class ServerStopped(Exception):
        pass

    def transport(request):
        requests.append((str(request.url), request.headers.get("Authorization")))
        return httpx.Response(200, json={"id": 7, "name": "Synthetic user"})

    def run():
        current = mcp_server._get_api()
        assert current is not previous
        assert current is mcp_server._get_api()
        http = httpx.Client(
            base_url=current.client.base_url,
            headers={"Authorization": f"Bearer {current.client.token}"},
            transport=httpx.MockTransport(transport),
        )
        current.client._http = http
        active.append((current.client, http))
        result = json.loads(asyncio.run(mcp_server.canvas_whoami()))
        assert result["profile"] == {"id": 7, "name": "Synthetic user"}
        if server_failure:
            raise ServerStopped

    monkeypatch.setattr(mcp_server.mcp, "run", run)
    try:
        if server_failure:
            with pytest.raises(ServerStopped):
                cli.main(["mcp", "--base-url", "https://explicit.example.test", "--token", "synthetic-explicit-token"])
        else:
            cli.main(["mcp", "--base-url", "https://explicit.example.test", "--token", "synthetic-explicit-token"])
        assert len(active) == 1
        assert active[0][0]._http is None
        assert active[0][1].is_closed
        assert mcp_server._api is previous
        assert not previous_http.is_closed
        assert requests == [("https://explicit.example.test/api/v1/users/self/profile?per_page=50", "Bearer synthetic-explicit-token")]
    finally:
        previous.client.close()
        for client, http in active:
            client.close()
            http.close()


def test_direct_no_argument_server_uses_environment_and_restores_empty_binding(monkeypatch):
    seen = []

    def run():
        client = mcp_server._get_api().client
        seen.append((client.base_url, client.token, client.profile))

    monkeypatch.setattr(mcp_server.mcp, "run", run)
    mcp_server.main()
    assert seen == [("https://environment.example.test", "synthetic-environment-token", Path("/synthetic-canvaspilot-environment-profile"))]
    assert mcp_server._api is None


def test_unknown_mcp_option_refuses_before_client_or_server(monkeypatch):
    def forbidden(*args, **kwargs):
        pytest.fail("invalid CLI arguments reached client/server construction")

    monkeypatch.setattr(mcp_server, "CanvasClient", forbidden)
    monkeypatch.setattr(mcp_server.mcp, "run", forbidden)
    with pytest.raises(SystemExit) as error:
        cli.main(["mcp", "--unknown-connection-option"])
    assert error.value.code == 2
