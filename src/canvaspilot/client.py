"""Canvas LMS client — PAT or session-broker auth (full REST, including quizzes)."""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import httpx

log = logging.getLogger(__name__)

# Override with CANVAS_BASE_URL or --base-url (e.g. https://<school>.instructure.com).
DEFAULT_BASE = "https://canvas.instructure.com"
LEGACY_PROFILE = Path.home() / ".suite" / "forge" / "profiles" / "canvas-sso"
BROKER_PORT = int(os.environ.get("CANVAS_SESSION_PORT", "18765"))


class CanvasAuthError(RuntimeError):
    pass


class CanvasPaginationError(RuntimeError):
    """A session traversal could not establish a complete, valid continuation."""


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
    with_response: bool = False,
) -> Any:
    """Call Canvas via the stay-open session broker (in-page fetch)."""
    full = path
    if params:
        # Match token-mode HTTPX encoding, including arrays and booleans.
        q = str(httpx.QueryParams(params))
        if q:
            sep = "&" if "?" in full else "?"
            full = f"{full}{sep}{q}"

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
    if with_response:
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
        """Follow Link rel=next until exhausted (cap pages)."""
        if self.fixture is not None:
            data = self.request("GET", path, params=params)
            return data if isinstance(data, list) else [data]

        health = broker_health() if not self.token else None
        if health:
            if health.get("link_pagination") is True:
                return self._get_broker_link_pages(
                    path, params=params, origin=health.get("base_url") or self.base_url,
                )
            # The session broker's /fetch returns {status, json, text} with no
            # response headers on older broker versions. Keep their existing
            # numeric compatibility path until the broker is restarted/upgraded.
            params = _with_per_page(params)
            if isinstance(params, list):
                per_page = min(int(dict(params).get("per_page", 50)), 100)
                params = [(k, v) for k, v in params if k != "per_page"]
                params.append(("per_page", per_page))
            else:
                per_page = min(int(params.get("per_page", 50)), 100)
                params = {**params, "per_page": per_page}
            out: list[Any] = []
            truncated = True
            for page in range(1, 41):
                data = broker_fetch(
                    "GET", path, params=_with_page(params, page), timeout=self.timeout
                )
                if not isinstance(data, list):
                    # Mirror the token path: keep the non-list chunk, then stop.
                    out.append(data)
                    truncated = False
                    break
                out.extend(data)
                if len(data) < per_page:
                    truncated = False
                    break
            if truncated:
                log.warning(
                    "get_paginated(%s): hit 40-page cap with %d rows; result truncated",
                    path,
                    len(out),
                )
            return out

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

    def _get_broker_link_pages(
        self,
        path: str,
        *,
        params: dict[str, Any] | list[tuple[str, Any]] | None,
        origin: str,
    ) -> list[Any]:
        out: list[Any] = []
        seen: set[str] = set()
        url = path
        for page in range(40):
            if url in seen:
                raise CanvasPaginationError("session pagination repeated a continuation URL")
            seen.add(url)
            response = broker_fetch(
                "GET", url, params=_with_per_page(params) if page == 0 else None,
                timeout=self.timeout, with_response=True,
            )
            headers = response.get("headers")
            if not isinstance(headers, dict):
                raise CanvasPaginationError("session pagination response has no Link metadata")
            links = [value for key, value in headers.items()
                     if isinstance(key, str) and key.lower() == "link"]
            if len(links) != 1 or not isinstance(links[0], str):
                raise CanvasPaginationError("session pagination Link metadata is invalid")
            next_url = _session_link_next(links[0])
            chunk = response["json"] if response.get("json") is not None else response.get("text")
            if not isinstance(chunk, list):
                if next_url or page > 0:
                    raise CanvasPaginationError("session pagination returned a non-list continuing page")
                out.append(chunk)
                return out
            out.extend(chunk)
            if not next_url:
                return out
            _assert_pagination_origin(next_url, origin)
            # Canvas supplies every parameter in the opaque absolute URL. Do
            # not append the first page's filters or invent another page number.
            url = next_url
        raise CanvasPaginationError("session pagination has more results after the 40-page cap")

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


def _with_page(
    params: dict[str, Any] | list[tuple[str, Any]] | None,
    page: int,
) -> dict[str, Any] | list[tuple[str, Any]]:
    """Return params with an explicit Canvas ?page=N for explicit pagination."""
    if isinstance(params, list):
        return [(k, v) for k, v in params if k != "page"] + [("page", page)]
    out = dict(params or {})
    out["page"] = page
    return out


def _assert_pagination_origin(url: str, base: str) -> None:
    try:
        if not isinstance(base, str):
            raise TypeError("invalid broker origin")
        target, origin = urlsplit(url), urlsplit(base)
        target_port = target.port if target.port is not None else (443 if target.scheme == "https" else 80)
        origin_port = origin.port if origin.port is not None else (443 if origin.scheme == "https" else 80)
        valid = (
            target.scheme in ("http", "https")
            and target.hostname is not None
            and target.username is None and target.password is None
            and not target.fragment and "\\" not in url
            and not any(char.isspace() for char in url)
            and (target.scheme, target.hostname, target_port)
            == (origin.scheme, origin.hostname, origin_port)
        )
    except (ValueError, TypeError):
        valid = False
    if not valid:
        raise CanvasPaginationError("session pagination continuation must use the configured Canvas origin")


_LINK_PARAM_NAME = r"[!#$%&'*+\-.^_`|~0-9A-Za-z]+"
_LINK_PARAM_VALUE = r'"(?:[^"\\]|\\.)*"|[^\s;,"\\]+'
_LINK_PARAM_TEXT = rf";\s*{_LINK_PARAM_NAME}(?:\s*=\s*(?:{_LINK_PARAM_VALUE}))?\s*"
_SESSION_LINK = re.compile(rf"\s*<([^>]*)>\s*((?:{_LINK_PARAM_TEXT})*)(?:,|$)")
_SESSION_LINK_PARAM = re.compile(rf";\s*({_LINK_PARAM_NAME})(?:\s*=\s*({_LINK_PARAM_VALUE}))?\s*")


def _session_link_next(header: str) -> str | None:
    """Read Link values without splitting opaque URLs or quoted parameters."""
    if not header.strip():
        return None
    if header.rstrip().endswith(","):
        raise CanvasPaginationError("session pagination Link header is malformed")
    offset, next_url = 0, None
    while offset < len(header):
        link = _SESSION_LINK.match(header, offset)
        if link is None or not link[1]:
            raise CanvasPaginationError("session pagination Link header is malformed")
        params = list(_SESSION_LINK_PARAM.finditer(link[2]))
        # An anchor changes the link's context. This collection traversal does
        # not support alternate contexts, so ignore the entire anchored link.
        if any(param[1].lower() == "anchor" for param in params):
            offset = link.end()
            continue
        relations = [param[2] for param in params if param[1].lower() == "rel"]
        if len(relations) > 1 or (relations and relations[0] is None):
            raise CanvasPaginationError("session pagination Link relation is ambiguous")
        if relations:
            value = relations[0]
            if value.startswith('"'):
                value = re.sub(r"\\(.)", r"\1", value[1:-1])
            if "next" in value.lower().split():
                if next_url is not None:
                    raise CanvasPaginationError("session pagination has multiple next links")
                next_url = link[1]
        offset = link.end()
    return next_url


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
