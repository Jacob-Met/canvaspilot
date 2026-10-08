"""Canvas LMS client — PAT or session-broker auth (full REST, including quizzes)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any

import httpx

from canvaspilot.pagination import CanvasPaginationError, broker_path, next_link, with_query

# Override with CANVAS_BASE_URL or --base-url (e.g. https://<school>.instructure.com).
DEFAULT_BASE = "https://canvas.instructure.com"
LEGACY_PROFILE = Path.home() / ".suite" / "forge" / "profiles" / "canvas-sso"
BROKER_PORT = int(os.environ.get("CANVAS_SESSION_PORT", "18765"))


class CanvasAuthError(RuntimeError):
    pass


def broker_base() -> str:
    return f"http://127.0.0.1:{BROKER_PORT}"


def _broker_request(method: str, url: str, **kwargs: Any) -> httpx.Response:
    """Broker traffic targets hardcoded 127.0.0.1 and must never consult proxy env.

    A proxy must never see localhost traffic anyway; and a malformed NO_PROXY
    entry (e.g. bracketed IPv6 ``[::1]``) makes httpx raise ``InvalidURL`` at
    Client construction, which callers do not expect. See issue #20.
    """
    kwargs.setdefault("trust_env", False)
    return httpx.request(method, url, **kwargs)


def broker_health() -> dict[str, Any] | None:
    try:
        r = _broker_request("GET", f"{broker_base()}/health", timeout=2.0)
        if r.status_code == 200:
            return r.json()
    except (httpx.HTTPError, httpx.InvalidURL, ValueError):
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
    include_response: bool = False,
) -> Any:
    """Call Canvas via the stay-open session broker (in-page fetch).

    ``include_response`` retains the broker's response metadata for pagination.
    Ordinary callers continue to receive only the decoded body.
    """
    full = with_query(path, params)

    body: Any = None
    headers = {"Accept": "application/json"}
    if json_body is not None:
        body = json_body
        headers["Content-Type"] = "application/json"
    elif data is not None:
        body = str(httpx.QueryParams(data))
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    r = _broker_request(
        "POST",
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
    if include_response:
        return resp
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

    def __enter__(self) -> CanvasClient:  # noqa: PYI034 — false positive, returns self (verified by isolated repro)
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
        url = path
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
        """Read a complete collection via same-origin Link URLs, or raise.

        A next link remaining after 40 pages is incomplete, even if earlier
        pages succeeded. Initial filters are sent only with the first request.
        """
        if self.fixture is not None:
            data = self.request("GET", path, params=params)
            return data if isinstance(data, list) else [data]

        if not self.token and broker_health():
            # Canvas may cap page sizes and uses opaque continuation URLs:
            # https://developerdocs.instructure.com/services/canvas/basics/file.pagination
            url = with_query(broker_path(path, self.base_url), _with_per_page(params))
            out: list[Any] = []
            seen: set[str] = set()
            for _ in range(40):
                if url in seen:
                    raise CanvasPaginationError("Canvas pagination repeated a page; collection incomplete.")
                seen.add(url)
                response = broker_fetch(
                    "GET", url, timeout=self.timeout, include_response=True
                )
                if not isinstance(response, dict) or "link" not in response:
                    raise CanvasPaginationError(
                        "The session broker does not provide pagination metadata. "
                        "Restart it with the current CanvasPilot version and retry the read."
                    )
                following = next_link(response["link"])
                data = response.get("json")
                if data is None:
                    raise CanvasPaginationError("Canvas pagination expected a JSON response; collection incomplete.")
                if not isinstance(data, list):
                    # Preserve the existing single-object response convention.
                    if following:
                        raise CanvasPaginationError("Canvas pagination returned a non-list page with a next link.")
                    out.append(data)
                    return out
                out.extend(data)
                if following is None:
                    return out
                url = broker_path(following, self.base_url)
            raise CanvasPaginationError("Canvas pagination exceeded the 40-page cap; collection incomplete.")

        http = self._ensure_http()
        url = broker_path(path, self.base_url)
        # Retain token mode's native HTTPX scalar/array encoding. Keep an
        # authored starting query and send these initial parameters only once.
        query = str(httpx.QueryParams(_with_per_page(params)))
        if query:
            url = f"{url}{'&' if '?' in url else '?'}{query}"
        out: list[Any] = []
        seen: set[str] = set()
        for _ in range(40):
            if url in seen:
                raise CanvasPaginationError("Canvas pagination repeated a page; collection incomplete.")
            seen.add(url)
            r = http.get(url)
            if r.status_code in (401, 403):
                raise CanvasAuthError(f"Canvas auth failed ({r.status_code})")
            r.raise_for_status()
            following = next_link(r.headers.get("link"))
            chunk = r.json()
            if isinstance(chunk, list):
                out.extend(chunk)
            else:
                if following:
                    raise CanvasPaginationError("Canvas pagination returned a non-list page with a next link.")
                out.append(chunk)
                return out
            if following is None:
                return out
            # Never give an absolute foreign next URL to the client carrying
            # the configured Authorization header. Redirect policy is unchanged.
            url = broker_path(following, self.base_url)
        raise CanvasPaginationError("Canvas pagination exceeded the 40-page cap; collection incomplete.")

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
        if path.endswith(("/users/self/profile", "/users/self")):
            return self.fixture.get("profile", {"id": 1, "name": "Fixture User"})
        raise KeyError(f"fixture miss: {key}")


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
