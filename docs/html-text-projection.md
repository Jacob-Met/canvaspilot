# HTML text in assignment briefs

CanvasPilot projects returned HTML into plain text for assignment descriptions,
assignment briefs and several other existing readers. For example, an assignment
containing `<p>If x < 5 and y > 2, explain.</p>` now keeps the complete instruction
`If x < 5 and y > 2, explain.`. A `>` inside a quoted tag attribute does not end
the tag or leak the attribute into the prompt.

The shared `canvaspilot.api.strip_html` helper has a limited text-projection
contract:

- Recognize start/end tag prefixes with an ASCII letter after `<` or `</`,
  declarations beginning `<!`, and processing instructions beginning `<?`.
  Single- and double-quoted attribute text stays inside the token, including
  embedded `>` and `<` characters.
- Replace each complete markup token with a space. Complete
  `<!-- ... -->` comments are removed as one token, including internal `>`.
- Preserve numeric or spaced comparisons such as `x<5` and `x < 5`.
  Literal text resembling a complete tag, such as `<canvas>`, must still be
  escaped as `&lt;canvas&gt;` in source HTML.
- Decode HTML entities exactly once after recognizing literal markup, then
  collapse whitespace and trim the result. Escaped markup survives as text;
  `&amp;lt;b&amp;gt;` becomes `&lt;b&gt;`, not `<b>`.
  Unknown entity spellings are passed to the same standard-library
  `html.unescape` behavior without inserting a missing semicolon.
- Retain an unfinished tag, quoted attribute or comment suffix as literal text.
  An unquoted nested `<` leaves the unsupported prefix literal and lets the next
  token be considered. These are limited text-preservation rules, not a complete
  malformed-HTML grammar.

Script and style bodies remain text, with the same one-pass entity conversion
and markup recognition; this helper does not compute browser visibility. It
does not execute scripts or styles, inspect attributes for visible content,
fetch images or linked resources, or sanitize HTML for safe rendering. Use
proper output escaping in the actual rendering consumer.

The API and `assignment_brief` signatures, requests and metadata are unchanged.
The repair also benefits existing callers of the shared helper, including
search and export consumers, without changing their own filtering or writing
rules.

## Qualification

The maintained regression tests cover literal comparisons, quoted attributes,
complete comments, entity spelling, separators, unfinished text, script/style
compatibility and the actual assignment-brief projection with authored response
transport. The complete API module was also executed in memory with its exact
standard-library dependencies. Independent consumer and helper checks are
recorded under `docs/receiving/html-text-fidelity-ultra-1b3276062063/`.

These checks do not establish installed CanvasPilot, live Canvas/HTTP, browser,
full repository suite or Ruff qualification. No account, token, provider data,
CLI command, dependency or workflow changed.
