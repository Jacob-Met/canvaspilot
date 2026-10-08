# Offline inbox conversations

Save one returned Canvas inbox conversation as a readable, printable HTML file:

```bash
canvaspilot export-conversation 246 --out conversation-246.html
```

Use the same `--base-url`, `--token` or `--profile` options as the existing `conversation` command. Choose a new output filename in an existing directory. Success prints a JSON receipt with the output path, requested and returned conversation IDs, creation time, HTML byte count and SHA256, and decoded-source JSON byte count and SHA256.

The command calls the existing `CanvasAPI.get_conversation()` once. That reader sends `auto_mark_as_read=false`; export does not mark the thread read, reply, archive, subscribe, follow attachments or change any Canvas state. An offline fixture gate demonstrates this request behavior; it does not establish behavior of a live school account.

## Reading the packet

Messages and participants stay in their returned order. Message IDs, author IDs and returned timestamps remain visible; export does not infer chronology from them. Author names are resolved only from a unique returned participant with the same JSON type and ID value. Unresolved and ambiguous associations are labeled. An unsupported participant/message entry stays visible instead of being discarded.

Missing fields, returned null, empty strings and empty lists have distinct labels. An empty or absent selection does not establish that a thread has no messages or that its history is complete. Conversation state and reported counts are displayed as returned. The saved observation does not refresh.

Message bodies are literal text. Markup-looking content is escaped, and line feeds, tabs, leading/trailing whitespace and ordinary Unicode are retained without stripping. Characters that HTML cannot represent reliably are displayed as `\uXXXX`: C0 controls other than LF/tab, including carriage return; DEL/C1 controls; and unpaired surrogates. Their exact decoded values remain in the source download.

**Download complete conversation JSON** saves every field of the decoded reader result, including unknown fields, attachments as metadata, forwarded data, false, zero, null and empty values. This is the complete decoded JSON object used to build the packet; it is not a copy of the original HTTP wire formatting. Its digest appears in both the document and CLI receipt. The packet has no scripts, forms, external resources or automatic requests. Source URLs are displayed as text. Use the browser's Print command for paper or PDF.

## Admission and publication

The root response must be a JSON object containing only decoded JSON values, with string object keys and finite numbers. The complete ASCII JSON serialization, including its trailing newline, is limited to 4 MiB; the complete UTF-8 HTML is limited to 16 MiB. These are export limits after the existing reader returns, not network, pagination or streaming limits. A supplied `generated_at` for the Python render/build helpers must be timezone-aware; displayed creation time is UTC.

The CLI refuses an existing file, directory, live symlink or dangling symlink before constructing a client or reading Canvas. It prepares the whole file and uses the established `page_export.write_page_packet()` writer to publish complete bytes exclusively at the new destination. It never replaces an existing entry and does not fall back to a replacing write on filesystems that lack the required operation. It does not create parent directories. A successful publication followed by temporary-file cleanup failure remains successful and includes the writer's `cleanup_warning`.

Admission, source-read, rendering or publication failure prints a structured error to stderr and exits 1. HTTPX logging state is restored. Existing reader commands and other exporters keep their own behavior. This workflow does not claim a transaction across changing remote data, hostile parent-directory changes, or durable storage after sudden device loss.

## Python helpers

`build_conversation_packet(api, conversation_id, *, generated_at=None)` makes the single existing reader call and returns `(html_bytes, receipt)`. `render_conversation_packet(source, *, generated_at=None)` renders a decoded object without altering it. Both live in `canvaspilot.conversation_export`. The builder preserves the original supplied ID in `requested_conversation_id`; the returned ID remains a separate field.
