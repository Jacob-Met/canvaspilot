"""Canvas LMS client — PAT or session-broker auth (full REST, including quizzes)."""

from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

import httpx

# Override with CANVAS_BASE_URL or --base-url (e.g. https://<school>.instructure.com).
DEFAULT_BASE = "https://canvas.instructure.com"
LEGACY_PROFILE = Path.home() / ".suite" / "forge" / "profiles" / "canvas-sso"
BROKER_PORT = int(os.environ.get("CANVAS_SESSION_PORT", "18765"))


class CanvasAuthError(RuntimeError):
    pass


def broker_base() -> str:
    return f"http://127.0.0.1:{BROKER_PORT}"


def broker_health() -> dict[str, Any] | None:
    try:
        r = httpx.get(f"{broker_base()}/health", timeout=2.0)
        if r.status_code == 200:
            return r.json()
    except Exception:
        return None
    return None


def broker_fetch(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    json_body: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> Any:
    """Call Canvas via the stay-open session broker (in-page fetch)."""
    from urllib.parse import urlencode

    full = path
    if params:
        if isinstance(params, list):
            q = urlencode([(k, str(v)) for k, v in params])
        else:
            q = urlencode({k: str(v) for k, v in params.items()})
        sep = "&" if "?" in full else "?"
        full = f"{full}{sep}{q}"

    body: Any = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        body = json_body
        headers["Content-Type"] = "application/json"
    elif data is not None:
        body = urlencode({k: str(v) for k, v in data.items()})
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    r = httpx.post(
        f"{broker_base()}/fetch",
        json={"op": "fetch", "method": method, "path": full, "headers": headers, "body": body},
        timeout=timeout,
    )
    payload = r.json()
    if not payload.get("ok"):
        raise CanvasAuthError(payload.get("error") or "broker fetch failed")
    resp = payload.get("response") or {}
    status = resp.get("status")
    if status in (401, 403):
        raise CanvasAuthError(
            f"Canvas auth failed ({status}) via session broker. Log in in the broker window."
        )
    if status and int(status) >= 400:
        raise httpx.HTTPStatusError(
            f"Canvas HTTP {status}",
            request=httpx.Request(method, full),
            response=httpx.Response(int(status), text=str(resp.get("text") or resp.get("json"))),
        )
    if resp.get("json") is not None:
        return resp["json"]
    return resp.get("text")


def default_profile() -> Path:
    env = os.environ.get("CANVAS_PROFILE", "").strip()
    if env:
        return Path(env)
    new = Path.home() / ".canvaspilot" / "profile"
    if not new.exists() and LEGACY_PROFILE.exists():
        return LEGACY_PROFILE  # Suite monorepo users keep their logged-in profile
    return new


def default_base_url() -> str:
    return (os.environ.get("CANVAS_BASE_URL") or DEFAULT_BASE).rstrip("/")


class CanvasClient:
    """Thin Canvas REST wrapper.

    Auth modes:
    - token: ``CANVAS_API_TOKEN`` / constructor token → Bearer
    - session: stay-open Playwright broker (schools that disable student PATs / SSO)
    - fixture: offline dict backend for tests
    """

    def __init__(
        self,
        *,
        base_url: str | None = None,
        token: str | None = None,
        profile: Path | None = None,
        fixture: dict[str, Any] | None = None,
        timeout: float = 60.0,
    ) -> None:
        self.base_url = (base_url or default_base_url()).rstrip("/")
        self.token = (token if token is not None else os.environ.get("CANVAS_API_TOKEN", "")).strip() or None
        self.profile = profile or default_profile()
        self.fixture = fixture
        self.timeout = timeout
        self._http: httpx.Client | None = None
        self._pw = None
        self._pw_ctx = None

    @property
    def mode(self) -> str:
        if self.fixture is not None:
            return "fixture"
        if self.token:
            return "token"
        if broker_health():
            return "session_broker"
        return "session"

    def close(self) -> None:
        if self._http is not None:
            self._http.close()
            self._http = None
        if self._pw_ctx is not None:
            self._pw_ctx.close()
            self._pw_ctx = None
        if self._pw is not None:
            self._pw.stop()
            self._pw = None

    def __enter__(self) -> CanvasClient:
        return self

    def __exit__(self, *args: object) -> None:
        self.close()

    def _ensure_http(self) -> httpx.Client:
        if self._http is not None:
            return self._http
        headers = {"Accept": "application/json"}
        if not self.token:
            raise CanvasAuthError(
                "No session broker running and no CANVAS_API_TOKEN. "
                "Start: canvaspilot session start"
            )
        headers["Authorization"] = f"Bearer {self.token}"
        self._http = httpx.Client(
            base_url=self.base_url,
            headers=headers,
            timeout=self.timeout,
            follow_redirects=True,
        )
        return self._http

    def request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
        json_body: dict[str, Any] | None = None,
        data: dict[str, Any] | None = None,
    ) -> Any:
        if self.fixture is not None:
            return self._fixture_request(method, path, params=params, json_body=json_body)
        if not self.token and broker_health():
            return broker_fetch(
                method,
                path,
                params=_with_per_page(params),
                json_body=json_body,
                data=data,
                timeout=self.timeout,
            )

        http = self._ensure_http()
        params = _with_per_page(params)
        url = path if path.startswith("http") else path
        r = http.request(method.upper(), url, params=params, json=json_body, data=data)
        if r.status_code in (401, 403):
            raise CanvasAuthError(
                f"Canvas auth failed ({r.status_code}) for {method} {path}. "
                "Start session broker: canvaspilot session start"
            )
        r.raise_for_status()
        if not r.content:
            return None
        ctype = r.headers.get("content-type", "")
        if "json" in ctype:
            return r.json()
        return r.text

    def get_paginated(
        self,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    ) -> list[Any]:
        """Follow Link rel=next until exhausted (cap pages)."""
        if self.fixture is not None:
            data = self.request("GET", path, params=params)
            return data if isinstance(data, list) else [data]

        if not self.token and broker_health():
            params = _with_per_page(params)
            if isinstance(params, dict):
                params = {**params, "per_page": min(int(params.get("per_page", 50)), 100)}
            data = broker_fetch("GET", path, params=params, timeout=self.timeout)
            return data if isinstance(data, list) else [data]

        http = self._ensure_http()
        params = _with_per_page(params)
        out: list[Any] = []
        url: str | None = path
        pages = 0
        while url and pages < 40:
            pages += 1
            r = http.get(url, params=params if pages == 1 and not str(url).startswith("http") else None)
            if r.status_code in (401, 403):
                raise CanvasAuthError(f"Canvas auth failed ({r.status_code})")
            r.raise_for_status()
            chunk = r.json()
            if isinstance(chunk, list):
                out.extend(chunk)
            else:
                out.append(chunk)
                break
            next_url = _link_next(r.headers.get("link") or r.headers.get("Link") or "")
            url = next_url
            params = None
        return out

    def _fixture_request(
        self,
        method: str,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None,
        json_body: dict[str, Any] | None,
    ) -> Any:
        assert self.fixture is not None
        key = f"{method.upper()} {path}"
        table = self.fixture.get("routes", {})
        if key in table:
            return table[key]
        norm_path = re.sub(r"/\d+", "/:id", path)
        for pattern, value in table.items():
            meth, _, pat = pattern.partition(" ")
            if meth != method.upper():
                continue
            if path == pat or norm_path == pat or norm_path == re.sub(r"/\d+", "/:id", pat):
                return value
            if norm_path.startswith(re.sub(r"/\d+", "/:id", pat).rstrip("/") + "/") and isinstance(value, list):
                want_id = path.rstrip("/").split("/")[-1]
                for item in value:
                    if str(item.get("id")) == str(want_id):
                        return item
        if path.endswith("/users/self/profile") or path.endswith("/users/self"):
            return self.fixture.get("profile", {"id": 1, "name": "Fixture User"})
        raise KeyError(f"fixture miss: {key}")


def _link_next(link_header: str) -> str | None:
    for part in link_header.split(","):
        if 'rel="next"' in part or "rel=next" in part:
            m = re.search(r"<([^>]+)>", part)
            if m:
                return m.group(1)
    return None


def _with_per_page(
    params: dict[str, Any] | list[tuple[str, Any]] | None,
) -> dict[str, Any] | list[tuple[str, Any]]:
    if params is None:
        return {"per_page": 50}
    if isinstance(params, list):
        if not any(k == "per_page" for k, _ in params):
            return [*params, ("per_page", 50)]
        return params
    out = dict(params)
    out.setdefault("per_page", 50)
    return out
