"""Canvas LMS client — PAT or session-broker auth (full REST, including quizzes)."""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Any
from urllib.parse import urljoin, urlsplit

import httpx

# Override with CANVAS_BASE_URL or --base-url (e.g. https://<school>.instructure.com).
DEFAULT_BASE = "https://canvas.instructure.com"
LEGACY_PROFILE = Path.home() / ".suite" / "forge" / "profiles" / "canvas-sso"
BROKER_PORT = int(os.environ.get("CANVAS_SESSION_PORT", "18765"))


class CanvasAuthError(RuntimeError):
    pass


class CanvasPaginationError(RuntimeError):
    """A collection could not be retrieved completely; no partial list is returned."""


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
) -> Any:
    """Call Canvas via the stay-open session broker (in-page fetch)."""
    resp = _broker_fetch_response(
        method, path, params=params, json_body=json_body, data=data, timeout=timeout
    )
    return resp["json"] if resp.get("json") is not None else resp.get("text")


def _broker_fetch_response(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | list[tuple[str, Any]] | None = None,
    json_body: dict[str, Any] | None = None,
    data: dict[str, Any] | None = None,
    timeout: float = 120.0,
) -> dict[str, Any]:
    """Decode the existing broker envelope without discarding pagination metadata."""
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
    return resp


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
        """Follow opaque next links; raise if the complete collection is unavailable."""
        if self.fixture is not None:
            data = self.request("GET", path, params=params)
            return data if isinstance(data, list) else [data]

        use_broker = not self.token and bool(broker_health())
        http = None if use_broker else self._ensure_http()
        params = _with_per_page(params)
        out: list[Any] = []
        url = path
        origin = None
        seen: set[tuple[Any, ...]] = set()
        for _ in range(40):
            if use_broker:
                resp = _broker_fetch_response("GET", url, params=params, timeout=self.timeout)
                chunk = resp["json"] if resp.get("json") is not None else resp.get("text")
                if isinstance(chunk, list) and ("link" not in resp or not resp.get("url")):
                    raise CanvasPaginationError(
                        "Restart the session broker from the updated CanvasPilot installation: "
                        "this running broker lacks pagination metadata; the collection is incomplete."
                    )
                response_url, link = resp.get("url"), resp.get("link")
            else:
                # httpx replaces an absolute URL's query when params is supplied.
                # As before, an absolute Canvas URL carries its own query.
                r = http.get(url, params=params if not url.startswith("http") else None)
                if r.status_code in (401, 403):
                    raise CanvasAuthError(f"Canvas auth failed ({r.status_code})")
                r.raise_for_status()
                chunk = r.json()
                response_url, link = str(r.url), r.headers.get("link")
            params = None  # Every next URL already includes its complete, opaque query.
            if not isinstance(chunk, list):
                out.append(chunk)
                return out
            response_origin, page_key = _pagination_identity(response_url)
            if origin is None:
                origin = response_origin
            if response_origin != origin:
                raise CanvasPaginationError("Canvas pagination response changed origin; collection incomplete.")
            if page_key in seen:
                raise CanvasPaginationError("Canvas pagination repeated a page; collection incomplete.")
            seen.add(page_key)
            out.extend(chunk)
            next_url = _link_next(link)
            if next_url is None:
                return out
            if any(ord(c) <= 32 or ord(c) == 127 or c == "\\" for c in next_url):
                raise CanvasPaginationError("Canvas pagination URL is invalid; collection incomplete.")
            url = urljoin(response_url, next_url)
            next_origin, next_key = _pagination_identity(url)
            if next_origin != origin:
                raise CanvasPaginationError("Canvas pagination next link changed origin; collection incomplete.")
            if next_key in seen:
                raise CanvasPaginationError("Canvas pagination repeated a next link; collection incomplete.")
        raise CanvasPaginationError("Canvas pagination reached the 40-page limit; collection incomplete.")

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


def _pagination_identity(url: str) -> tuple[tuple[str, str, int], tuple[Any, ...]]:
    """Validate without rewriting an opaque URL, and identify its origin/page."""
    if not isinstance(url, str) or any(ord(c) <= 32 or ord(c) == 127 or c == "\\" for c in url):
        raise CanvasPaginationError("Canvas pagination URL is invalid; collection incomplete.")
    try:
        parsed = urlsplit(url)
        if (parsed.scheme not in ("http", "https") or not parsed.hostname
                or parsed.username is not None or parsed.password is not None or parsed.fragment):
            raise ValueError("invalid pagination URL")
        port = parsed.port if parsed.port is not None else (443 if parsed.scheme == "https" else 80)
    except ValueError as exc:
        raise CanvasPaginationError("Canvas pagination URL is invalid; collection incomplete.") from exc
    origin = (parsed.scheme, parsed.hostname, port)
    return origin, (origin, parsed.path or "/", parsed.query)


# Commas/semicolons inside <URLs> and quoted parameters are not link separators.
_LINK_TOKEN = r"[!#$%&'*+.^_`|~0-9A-Za-z-]+"
_LINK_VALUE = rf'(?:"(?:[^"\\]|\\.)*"|{_LINK_TOKEN})'
_LINK_PARAM = rf"\s*;\s*{_LINK_TOKEN}(?:\s*=\s*{_LINK_VALUE})?"
_LINK = re.compile(rf"\s*<([^<>]*)>((?:{_LINK_PARAM})*)\s*(?:,|$)")
_PARAM = re.compile(rf"\s*;\s*({_LINK_TOKEN})(?:\s*=\s*({_LINK_VALUE}))?")
_RELATION = re.compile(
    r"(?:[A-Za-z][A-Za-z0-9.-]*|"
    r"[A-Za-z][A-Za-z0-9+.-]*:(?:[A-Za-z0-9._~:/?#\[\]@!$&'()*+,;=-]|%[0-9A-Fa-f]{2})*)"
)


def _link_next(link_header: str | None) -> str | None:
    if link_header is None or link_header == "":
        return None
    if not isinstance(link_header, str):
        raise CanvasPaginationError("Canvas pagination Link header is invalid; collection incomplete.")
    pos = 0
    next_url = None
    while link_header[pos:].strip():
        match = _LINK.match(link_header, pos)
        if match is None:
            raise CanvasPaginationError("Canvas pagination Link header is malformed; collection incomplete.")
        has_relation = False
        for param in _PARAM.finditer(match[2]):
            if param[1].lower() == "anchor":
                raise CanvasPaginationError("Canvas pagination Link header has an unsupported anchor context; collection incomplete.")
            if param[1].lower() != "rel":
                continue
            if has_relation:
                raise CanvasPaginationError("Canvas pagination Link header has repeated rel parameters; collection incomplete.")
            has_relation = True
            value = param[2] or ""
            if value.startswith('"'):
                value = re.sub(r"\\(.)", r"\1", value[1:-1])
            if not value.strip():
                raise CanvasPaginationError("Canvas pagination Link header has an empty relation; collection incomplete.")
            relations = value.split(" ")
            if any(_RELATION.fullmatch(item) is None for item in relations if item):
                raise CanvasPaginationError("Canvas pagination Link header has an invalid relation; collection incomplete.")
            if "next" in [item.lower() for item in relations]:
                if next_url is not None:
                    raise CanvasPaginationError("Canvas pagination Link header has multiple next links; collection incomplete.")
                next_url = match[1]
        if not has_relation:
            raise CanvasPaginationError("Canvas pagination Link header has no relation; collection incomplete.")
        pos = match.end()
    return next_url


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
