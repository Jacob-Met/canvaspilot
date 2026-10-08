<<<<<<< HEAD
Tests use offline fixtures and disposable loopback HTTP servers. Feedback tests
also exercise CLI subprocesses and the real MCP stdio interface; no Canvas account
or running browser is needed.
=======
Tests use authored fixtures and loopback HTTP servers without Canvas access.

The optional native-browser check executes the production in-page fetch against
an authored loopback response in a fresh Chromium profile. It uses no school
session and verifies that the fixture cookie remains in the browser while only
Link metadata reaches the caller:

```bash
CANVASPILOT_CHROMIUM_BIN=/path/to/chromium python -m pytest -q tests/test_browser_link_metadata.py
```

`CANVASPILOT_CHROMIUM_PROFILE_ROOT` can select a writable parent for temporary
profiles (useful for a confined browser package). The browser test skips only
when `CANVASPILOT_CHROMIUM_BIN` is unset; an invalid configured executable fails.
All regular HTTP/client tests run offline without a browser binary.
>>>>>>> 857a226d54c9784ca528bccc6ace7b4f02d90f4d
