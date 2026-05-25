# Archive DB Schema & Content State

**Last verified:** 2026-05-24

## Location

`~/.hermes/memory/archive.db` — 79MB, ~33,500 messages, 525 sessions

## Schema

```sql
conversations:
  id          INTEGER PRIMARY KEY AUTOINCREMENT
  session_id  TEXT NOT NULL   -- format: YYYYMMDD_HHMMSS_random
  timestamp   REAL NOT NULL   -- time.time()
  role        TEXT NOT NULL   -- 'user' | 'assistant' | 'tool'
  content     TEXT NOT NULL   -- see content gaps below
  platform    TEXT            -- nullable, usually empty
  topic       TEXT            -- nullable, extracted via _extract_topic()

FTS5: conversations_fts(content, content='conversations', content_rowid='id')
```

## What's Stored vs Missing

| Role | Content | Complete? |
|------|---------|-----------|
| `user` | Full text of user's message | ✅ Yes |
| `assistant` | Free-text response only | ✅ Text, ❌ No tool_calls metadata |
| `tool` | Result payload (JSON string) | ✅ Yes |

## Data Flow: Two Write Paths

**sync_turn() — per-turn (the main path):**
- Framework passes only `user_content: str` and `assistant_content: str`
- NO tool_calls metadata available at this stage
- This is a framework API limitation, not an Archive plugin bug
- The `content` field for assistant tool-call messages is often `None` or empty string

**on_session_end() — session boundary (the recovery path):**
- Framework passes `messages: List[Dict]` — FULL message objects including tool_calls
- `archive_session()` now serializes `msg["tool_calls"]` into content (fixed 2026-05-24)
- This only captures data when a session explicitly ends (CLI exit, /reset, gateway timeout)
- Does NOT capture the running session's turns

## Content Gap Detail

When an assistant message includes `tool_calls` (e.g., calling `terminal("ls -la")`):
- `content` only gets the text portion of the assistant response (or None/empty if only tool_calls)
- The structured `tool_calls` array (function name, arguments, tool_call_id) is **not persisted** at turn level
- Tool results DO get stored (role='tool'), but lack explicit linkage to which tool_call they belong to
- Ordering by `timestamp` is the only way to reconstruct the conversation flow

**Older sessions (before 2026-05-24 fix):** Some assistant messages read `"Session summary — no more tool calls."` — these are compressed summaries, not original content.

## Role Distribution (approx as of 2026-05-24)

- `tool`: ~16,700 (50%) — actual tool outputs
- `assistant`: ~10,800 (32%) — text responses only
- `user`: ~6,000 (18%) — user inputs

## Session Format

Session IDs follow: `YYYYMMDD_HHMMSS_random`, e.g. `20260524_052130_57d514b4`

## Query Pattern for Full Session Recovery

**Forgetless pattern (preferred — no framework tool needed):**  
User says "forgetless" or "查记录", ask N hours, then:

```python
import sqlite3, json, datetime, time

db = sqlite3.connect("/home/ubuntu/.hermes/memory/archive.db")
db.row_factory = sqlite3.Row
cutoff = time.time() - N * 3600

rows = db.execute("""
    SELECT role, content, timestamp
    FROM conversations
    WHERE timestamp > ?
    ORDER BY timestamp
""", (cutoff,)).fetchall()

for m in rows:
    ts = datetime.datetime.fromtimestamp(m["timestamp"]).strftime("%H:%M")
    icon = {"user":"🧑","assistant":"🤖","tool":"🔧"}.get(m["role"], "❓")
    print(f"{icon} [{ts}] {m['role']}: {m['content'][:200]}")
```

Trigger word stored in memory — survives session handoff without framework tool registration.

## Known Limitations

1. **tool_calls metadata at turn level:** Cannot reconstruct exact OpenAI/Anthropic message format because sync_turn() only gets strings. The transcript is human-readable but not machine-replayable.
2. **Compressed vs original:** Some assistant messages show "Session summary — no more tool calls." instead of original content (from ContextCompressor output stored post-compaction).
3. **No linkage between tool_call and tool result:** The tool_call_id is not stored; ordering by timestamp is the only correlation.
4. **get_session_raw framework tool was rolled back 2026-05-24:** User rejected it as over-engineering. Use forgetless pattern (memory + execute_code) instead.
