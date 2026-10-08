# Normalized reader boundary correction

Independent receiving found that the existing token paginator wraps a singleton HTTP object into a list and the existing full module reader can replace unusable inline items with a fallback response. The digest receives those normalized rows. Earlier source/evidence must not be read as certification of raw HTTP array shape.

Native correction `96e4f3d37b4e2e222e30ff34a0bab96bed95b8cd` adds `reader_source: "CanvasAPI.list_modules(detail=full)"` and `upstream_response_shape: "not_observed"`, and clarifies the guide, function contract and malformed-shape error wording. It does not alter the owned paginator, broker or module reader.

The focused suite passes **70/70**: 67 prior module projection/admission cases plus three new real CLI and MCP cases for a singleton Module response, singleton fallback ModuleItem response, and invalid inline items replaced by valid fallback rows. Both public interfaces return the same truthful normalized digest and explicit boundary markers. The complete upstream fixture, wire outputs and GET request list for each case are retained.

Ruff and source whitespace checks pass. All source hashes remained unchanged during receiving. Historical initial source/evidence and the independent review's original failing contract observations remain separate immutable evidence.
