"""Memory Archive Plugin — SQLite + FTS5 + Skill Index for Hermes.

Hybrid approach (方案 C):
- Skill files remain the source of truth (readable, version-controlled)
- SQLite FTS5 indexes conversations + skill file references
- archive_search returns results with skill file paths for skill_view lookup

Config: ~/.hermes/config.yaml
  memory:
    provider: archive
"""

from __future__ import annotations

import json
import logging
import re
import sqlite3
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

import sys as _sys
_ANCHORING_PATH = str(Path.home() / ".hermes" / "plugins" / "anchoring")
if _ANCHORING_PATH not in _sys.path:
    _sys.path.insert(0, _ANCHORING_PATH)

from agent.memory_provider import MemoryProvider
from tools.registry import tool_error

# --- Anchoring plugin integration ---
try:
    from api_client import TradierClient, MarketSnapshot
    from snapshot_formatter import format_full_anchor_text, format_data_constraints_block
    _ANCHORING_AVAILABLE = True
except ImportError:
    _ANCHORING_AVAILABLE = False
    TradierClient = None  # type: ignore
    MarketSnapshot = None  # type: ignore
    format_full_anchor_text = None  # type: ignore
    format_data_constraints_block = lambda: ""  # type: ignore

_ANCHOR_SYMBOL = "SPY"
_ANCHOR_TARGET_DTES = [0, 30]
_ANCHOR_CACHE_TTL = 30

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Database schema
# ---------------------------------------------------------------------------

SCHEMA = """
-- Conversations: raw session transcripts
CREATE TABLE IF NOT EXISTS conversations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL,
    platform TEXT,
    topic TEXT
);

-- Facts: extracted key-value pairs
CREATE TABLE IF NOT EXISTS facts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    key TEXT NOT NULL,
    value TEXT NOT NULL,
    source TEXT,
    frequency INTEGER DEFAULT 1,
    last_seen REAL NOT NULL
);

-- Skill references: index pointing to skill files
CREATE TABLE IF NOT EXISTS skill_refs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    skill_name TEXT NOT NULL,
    file_path TEXT NOT NULL,
    content_summary TEXT,
    tags TEXT,
    timestamp REAL NOT NULL
);

-- Distilled: weekly summaries
CREATE TABLE IF NOT EXISTS distilled (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    week_start TEXT NOT NULL UNIQUE,
    summary TEXT NOT NULL,
    key_facts TEXT NOT NULL,
    created_at REAL NOT NULL
);

-- FTS5 virtual table for conversations
CREATE VIRTUAL TABLE IF NOT EXISTS conversations_fts USING fts5(
    content,
    content='conversations',
    content_rowid='id'
);

-- FTS5 virtual table for skill refs
CREATE VIRTUAL TABLE IF NOT EXISTS skill_refs_fts USING fts5(
    content_summary,
    content='skill_refs',
    content_rowid='id'
);

-- Triggers for conversations FTS
CREATE TRIGGER IF NOT EXISTS conversations_ai AFTER INSERT ON conversations BEGIN
    INSERT INTO conversations_fts(rowid, content) VALUES (new.id, new.content);
END;
CREATE TRIGGER IF NOT EXISTS conversations_ad AFTER DELETE ON conversations BEGIN
    INSERT INTO conversations_fts(conversations_fts, rowid, content) VALUES ('delete', old.id, old.content);
END;

-- Triggers for skill_refs FTS
CREATE TRIGGER IF NOT EXISTS skill_refs_ai AFTER INSERT ON skill_refs BEGIN
    INSERT INTO skill_refs_fts(rowid, content_summary) VALUES (new.id, new.content_summary);
END;
CREATE TRIGGER IF NOT EXISTS skill_refs_ad AFTER DELETE ON skill_refs BEGIN
    INSERT INTO skill_refs_fts(skill_refs_fts, rowid, content_summary) VALUES ('delete', old.id, old.content_summary);
END;

-- Indexes
CREATE INDEX IF NOT EXISTS idx_conv_session ON conversations(session_id);
CREATE INDEX IF NOT EXISTS idx_conv_time ON conversations(timestamp);
CREATE INDEX IF NOT EXISTS idx_facts_key ON facts(key);
CREATE INDEX IF NOT EXISTS idx_facts_freq ON facts(frequency DESC);
CREATE INDEX IF NOT EXISTS idx_skill_name ON skill_refs(skill_name);
"""


# ---------------------------------------------------------------------------
# ArchiveManager
# ---------------------------------------------------------------------------

class ArchiveManager:
    """SQLite-backed memory archive with FTS5 search + skill indexing."""

    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            home = Path.home() / ".hermes" / "memory"
            home.mkdir(parents=True, exist_ok=True)
            db_path = str(home / "archive.db")
        self.db_path = db_path
        self._local = threading.local()
        self._init_db()

    def _conn(self) -> sqlite3.Connection:
        if not hasattr(self._local, "conn") or self._local.conn is None:
            self._local.conn = sqlite3.connect(self.db_path, check_same_thread=False)
            self._local.conn.row_factory = sqlite3.Row
        return self._local.conn

    def _init_db(self) -> None:
        conn = self._conn()
        conn.executescript(SCHEMA)
        conn.commit()

    # -- Conversation archiving --

    def archive_message(self, session_id: str, role: str, content: str,
                        platform: str = "", topic: str = "") -> None:
        conn = self._conn()
        conn.execute(
            "INSERT INTO conversations (session_id, timestamp, role, content, platform, topic) VALUES (?, ?, ?, ?, ?, ?)",
            (session_id, time.time(), role, content, platform, topic),
        )
        conn.commit()

    def archive_session(self, session_id: str, messages: List[Dict[str, Any]],
                        platform: str = "") -> None:
        conn = self._conn()
        for msg in messages:
            role = msg.get("role", "")
            content = msg.get("content", "") or ""
            # Tool calls are in a separate key — serialize them into content
            tool_calls = msg.get("tool_calls") or msg.get("function_call")
            if tool_calls:
                content += "\n<!-- tool_calls: " + json.dumps(tool_calls, ensure_ascii=False) + " -->"
            if not content:
                continue
            topic = self._extract_topic(content)
            conn.execute(
                "INSERT INTO conversations (session_id, timestamp, role, content, platform, topic) VALUES (?, ?, ?, ?, ?, ?)",
                (session_id, time.time(), role, content, platform, topic),
            )
        conn.commit()

    # -- Skill indexing --

    def index_skill(self, skill_name: str, file_path: str,
                    content_summary: str = "", tags: str = "") -> None:
        """Index a skill file for search."""
        conn = self._conn()
        # Delete old entry for this skill
        conn.execute("DELETE FROM skill_refs WHERE skill_name = ?", (skill_name,))
        conn.execute(
            "INSERT INTO skill_refs (skill_name, file_path, content_summary, tags, timestamp) VALUES (?, ?, ?, ?, ?)",
            (skill_name, file_path, content_summary, tags, time.time()),
        )
        conn.commit()

    def index_all_skills(self, skills_dir: Optional[str] = None) -> int:
        """Scan ~/.hermes/skills/ and index all SKILL.md files."""
        if skills_dir is None:
            skills_dir = str(Path.home() / ".hermes" / "skills")

        count = 0
        skills_path = Path(skills_dir)
        if not skills_path.exists():
            return 0

        for skill_dir in skills_path.iterdir():
            if not skill_dir.is_dir() or skill_dir.name.startswith(("_", ".")):
                continue
            skill_md = skill_dir / "SKILL.md"
            if skill_md.exists():
                content = skill_md.read_text(errors="replace")
                # Extract first 500 chars as summary
                summary = content[:500].replace("\n", " ")
                # Extract tags from frontmatter or content
                tags = self._extract_skill_tags(content)
                self.index_skill(skill_dir.name, str(skill_md), summary, tags)
                count += 1

        return count

    # -- Search (unified) --

    def search(self, query: str, limit: int = 10,
               days: Optional[int] = None,
               include_skills: bool = True) -> Dict[str, Any]:
        """Unified search across conversations and skills."""
        results = {
            "conversations": self._search_conversations(query, limit, days),
            "facts": self._search_facts(query, limit),
        }
        if include_skills:
            results["skills"] = self._search_skills(query, limit)
        return results

    def _search_conversations(self, query: str, limit: int = 10,
                              days: Optional[int] = None) -> List[Dict[str, Any]]:
        """Search conversations with context — return paired user/assistant messages."""
        conn = self._conn()
        params: List[Any] = []
        time_filter = ""
        if days:
            cutoff = time.time() - days * 86400
            time_filter = "AND c.timestamp > ?"
            params.append(cutoff)

        # Step 1: Find matching messages via FTS5
        sql = f"""
            SELECT
                c.id, c.session_id, c.timestamp, c.role, c.content, c.topic,
                snippet(conversations_fts, 0, '**', '**', '...', 32) as snippet,
                rank
            FROM conversations_fts fts
            JOIN conversations c ON c.id = fts.rowid
            WHERE conversations_fts MATCH ? {time_filter}
            ORDER BY rank
            LIMIT ?
        """
        params = [query] + params + [limit * 3]  # fetch more to get context
        rows = conn.execute(sql, params).fetchall()

        if not rows:
            return []

        # Step 2: For each match, fetch surrounding context (±2 messages in same session)
        results = []
        seen_ids = set()
        for row in rows:
            match_id = row["id"]
            session_id = row["session_id"]
            match_ts = row["timestamp"]

            if match_id in seen_ids:
                continue

            # Fetch context: messages in same session near this timestamp
            context_rows = conn.execute(
                """
                SELECT id, session_id, timestamp, role, content, topic
                FROM conversations
                WHERE session_id = ? AND timestamp BETWEEN ? AND ?
                ORDER BY timestamp
                LIMIT 10
                """,
                (session_id, match_ts - 300, match_ts + 300),
            ).fetchall()

            context_messages = []
            for cr in context_rows:
                seen_ids.add(cr["id"])
                context_messages.append({
                    "id": cr["id"],
                    "timestamp": cr["timestamp"],
                    "role": cr["role"],
                    "content": cr["content"],
                    "is_match": cr["id"] == match_id,
                })

            results.append({
                "id": match_id,
                "session_id": session_id,
                "timestamp": match_ts,
                "role": row["role"],
                "content": row["content"],
                "snippet": row["snippet"],
                "topic": row["topic"],
                "context": context_messages,
            })

            if len(results) >= limit:
                break

        return results

    def _search_skills(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT
                s.id, s.skill_name, s.file_path, s.tags,
                snippet(skill_refs_fts, 0, '**', '**', '...', 32) as snippet,
                rank
            FROM skill_refs_fts fts
            JOIN skill_refs s ON s.id = fts.rowid
            WHERE skill_refs_fts MATCH ?
            ORDER BY rank
            LIMIT ?
            """,
            (query, limit),
        ).fetchall()
        return [dict(r) for r in rows]

    def _search_facts(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        conn = self._conn()
        rows = conn.execute(
            """
            SELECT key, value, frequency, last_seen
            FROM facts
            WHERE key LIKE ? OR value LIKE ?
            ORDER BY frequency DESC, last_seen DESC
            LIMIT ?
            """,
            (f"%{query}%", f"%{query}%", limit),
        ).fetchall()
        return [dict(r) for r in rows]

    # -- Fact extraction --

    def extract_facts(self, session_id: str, content: str) -> None:
        conn = self._conn()

        # Pattern 1: "X is Y" / "X = Y" / "X: Y"
        for match in re.finditer(
            r"(?:^|\n)\s*(?:[\-•*]\s*)?(?:user\s+)?(?:prefers|likes|uses|hates|values)?\s*"
            r"([A-Za-z0-9_\-\/\.\s]+?)(?:\s+(?:is|at|=|:)\s+|\s*=\s*)(.+?)(?:\n|$)",
            content, re.IGNORECASE,
        ):
            key = match.group(1).strip().rstrip(".: ")
            value = match.group(2).strip()
            if len(key) >= 3 and len(value) >= 3:
                self._upsert_fact(conn, key, value, session_id)

        # Pattern 2: GitHub repo patterns
        for match in re.finditer(
            r"(?:github|仓库|repo)\s*(?:地址|url|path|is|=|:)?\s*[:=]?\s*([a-zA-Z0-9_\-]+\/[a-zA-Z0-9_\-\.]+)",
            content, re.IGNORECASE,
        ):
            self._upsert_fact(conn, "github_repo", match.group(1).strip(), session_id)

        # Pattern 3: Path patterns
        for match in re.finditer(
            r"((?:/home/|/Users/|~/)[a-zA-Z0-9_\-\/\.]+)\s+(?:is|contains|has)",
            content, re.IGNORECASE,
        ):
            self._upsert_fact(conn, "path", match.group(1).strip(), session_id)

        conn.commit()

    def _upsert_fact(self, conn: sqlite3.Connection, key: str, value: str,
                     session_id: str) -> None:
        now = time.time()
        row = conn.execute(
            "SELECT id, frequency FROM facts WHERE key = ? AND value = ?",
            (key, value),
        ).fetchone()
        if row:
            conn.execute(
                "UPDATE facts SET frequency = frequency + 1, last_seen = ? WHERE id = ?",
                (now, row["id"]),
            )
        else:
            conn.execute(
                "INSERT INTO facts (session_id, timestamp, key, value, last_seen) VALUES (?, ?, ?, ?, ?)",
                (session_id, now, key, value, now),
            )

    # -- Distillation --
    def distill_week(self, week_start: Optional[str] = None) -> Dict[str, Any]:
        """Generate weekly summary + write to skill file."""
        if week_start is None:
            today = datetime.now()
            week_start = (today - timedelta(days=today.weekday())).strftime("%Y-%m-%d")

        conn = self._conn()
        facts = conn.execute(
            "SELECT key, value, frequency FROM facts ORDER BY frequency DESC LIMIT 20"
        ).fetchall()

        topics = conn.execute(
            """
            SELECT topic, COUNT(*) as cnt
            FROM conversations
            WHERE topic != '' AND timestamp > ?
            GROUP BY topic
            ORDER BY cnt DESC
            LIMIT 10
            """,
            (time.time() - 7 * 86400,),
        ).fetchall()

        total_messages = conn.execute(
            "SELECT COUNT(*) FROM conversations WHERE timestamp > ?",
            (time.time() - 7 * 86400,),
        ).fetchone()[0]

        summary = {
            "week_start": week_start,
            "top_facts": [dict(f) for f in facts],
            "top_topics": [dict(t) for t in topics],
            "total_messages": total_messages,
        }

        # Save to SQLite
        conn.execute(
            "INSERT OR REPLACE INTO distilled (week_start, summary, key_facts, created_at) VALUES (?, ?, ?, ?)",
            (
                week_start,
                json.dumps(summary, ensure_ascii=False),
                json.dumps([dict(f) for f in facts], ensure_ascii=False),
                time.time(),
            ),
        )
        conn.commit()

        # Write to skill file
        self._write_skill_file(facts, topics, total_messages, week_start)

        return summary

    def _write_skill_file(
        self,
        facts: List[sqlite3.Row],
        topics: List[sqlite3.Row],
        total_messages: int,
        week_start: str,
    ) -> None:
        """Write distilled facts to memory-archive SKILL.md."""
        skill_path = Path.home() / ".hermes" / "skills" / "memory-archive" / "SKILL.md"
        skill_path.parent.mkdir(parents=True, exist_ok=True)

        # Build facts section
        facts_lines = []
        if facts:
            for f in facts:
                facts_lines.append(f"- **{f['key']}**: {f['value']} (seen {f['frequency']}x)")
        else:
            facts_lines.append("_No facts distilled yet._")

        # Build topics section
        topics_lines = []
        if topics:
            for t in topics:
                topics_lines.append(f"- {t['topic']}: {t['cnt']} messages")
        else:
            topics_lines.append("_No topics recorded yet._")

        # Build skills section (top 10 indexed skills)
        conn = self._conn()
        skills = conn.execute(
            "SELECT skill_name, file_path, tags FROM skill_refs ORDER BY timestamp DESC LIMIT 10"
        ).fetchall()
        skills_lines = []
        if skills:
            for s in skills:
                tag_str = f" tags: [{s['tags']}]" if s['tags'] else ""
                skills_lines.append(f"- `{s['skill_name']}`{tag_str}")
                skills_lines.append(f"  → {s['file_path']}")
        else:
            skills_lines.append("_No skills indexed yet._")

        # Assemble content
        content = f"""---
name: memory-archive
category: memory
description: "Auto-generated memory archive — distilled facts from conversations. Updated weekly by archive plugin."
tags: [memory, archive, facts, auto-generated]
related_skills: []
---

# Memory Archive

> **Auto-generated**: This file is updated by the `archive` memory plugin.
> Last distilled: {week_start} | Total messages this week: {total_messages}
> Do not edit manually — your changes will be overwritten on next distillation.

## High-Frequency Facts

<!-- FACTS_START -->
{chr(10).join(facts_lines)}
<!-- FACTS_END -->

## Recent Topics

<!-- TOPICS_START -->
{chr(10).join(topics_lines)}
<!-- TOPICS_END -->

## Skill Index

<!-- SKILLS_START -->
{chr(10).join(skills_lines)}
<!-- SKILLS_END -->

## How to Use

- **Search archive**: Say "搜记忆: {{query}}" or I call `archive_search`
- **Weekly distillation**: Say "蒸馏上周记忆" or I call `archive_distill`
- **Check status**: Say "记忆状态" or I call `archive_stats`

## Archive Location

- Database: `~/.hermes/memory/archive.db`
- Plugin: `~/.hermes/plugins/archive/`
"""
        skill_path.write_text(content, encoding="utf-8")
        logger.debug("Memory archive skill updated: %s", skill_path)

    # -- Stats --

    def stats(self) -> Dict[str, Any]:
        conn = self._conn()
        return {
            "total_conversations": conn.execute("SELECT COUNT(*) FROM conversations").fetchone()[0],
            "total_facts": conn.execute("SELECT COUNT(*) FROM facts").fetchone()[0],
            "total_skills": conn.execute("SELECT COUNT(*) FROM skill_refs").fetchone()[0],
            "total_distilled": conn.execute("SELECT COUNT(*) FROM distilled").fetchone()[0],
            "db_size_bytes": Path(self.db_path).stat().st_size,
            "db_path": self.db_path,
        }

    # -- Helpers --

    @staticmethod
    def _extract_topic(content: str) -> str:
        topics = {
            "ONEBOT": r"\bONEBOT\b",
            "SPY": r"\bSPY\b",
            "量化": r"量化",
            "DeepSeek": r"DeepSeek|DS",
            "Kimi": r"Kimi|KimiClaw",
            "期权": r"期权|option",
            "宏观": r"宏观|FOMC|CPI|PCE|GDP",
            "skill": r"skill|SKILL",
            "memory": r"memory|记忆",
            "github": r"github|仓库|repo",
        }
        found = []
        for topic, pattern in topics.items():
            if re.search(pattern, content, re.IGNORECASE):
                found.append(topic)
        return ",".join(found) if found else ""

    @staticmethod
    def _extract_skill_tags(content: str) -> str:
        """Extract tags from skill content: category, tools mentioned, etc."""
        tags = []
        # Look for category in frontmatter
        cat_match = re.search(r'^category:\s*(.+)$', content, re.MULTILINE | re.IGNORECASE)
        if cat_match:
            tags.append(cat_match.group(1).strip())
        # Look for tool mentions
        tools = re.findall(r'\b(terminal|browser|web_search|file|patch|cronjob|delegate_task)\b',
                          content, re.IGNORECASE)
        tags.extend(set(tools))
        return ",".join(tags) if tags else ""


# ---------------------------------------------------------------------------
# MemoryProvider implementation
# ---------------------------------------------------------------------------

class ArchiveMemoryProvider(MemoryProvider):
    """SQLite + FTS5 + Skill Index memory provider for Hermes."""

    def __init__(self):
        self._manager: Optional[ArchiveManager] = None
        self._session_id: str = ""
        self._platform: str = ""
        self._turn_buffer: List[Dict[str, Any]] = []
        self._buffer_lock = threading.Lock()
        # --- Anchoring integration ---
        self._anchor_client: Optional[Any] = TradierClient() if _ANCHORING_AVAILABLE and TradierClient else None
        self._anchor_cache: Optional[MarketSnapshot] = None  # type: ignore
        self._anchor_cache_time: float = 0.0

    @property
    def name(self) -> str:
        return "archive"

    def is_available(self) -> bool:
        return True

    def initialize(self, session_id: str, **kwargs) -> None:
        self._manager = ArchiveManager()
        self._session_id = session_id
        self._platform = kwargs.get("platform", "")
        # Index all skills on init
        try:
            count = self._manager.index_all_skills()
            logger.debug("Archive indexed %d skills", count)
        except Exception as e:
            logger.debug("Skill indexing failed: %s", e)
        logger.debug("Archive memory initialized: session=%s", session_id)

    def system_prompt_block(self) -> str:
        """Return data constraints block for market data anchoring."""
        if not _ANCHORING_AVAILABLE or not format_data_constraints_block:
            return ""
        return format_data_constraints_block()

    def _anchor_is_cache_valid(self) -> bool:
        if self._anchor_cache is None:
            return False
        return (time.time() - self._anchor_cache_time) < _ANCHOR_CACHE_TTL

    def _anchor_sync_fetch(self) -> Optional[MarketSnapshot]:
        """Synchronously fetch market snapshot using Tradier API."""
        if not self._anchor_client:
            return None
        try:
            import asyncio
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                snapshot = loop.run_until_complete(
                    self._anchor_client.fetch_snapshot(_ANCHOR_SYMBOL, _ANCHOR_TARGET_DTES)
                )
            finally:
                loop.close()
            self._anchor_cache = snapshot
            self._anchor_cache_time = time.time()
            return snapshot
        except Exception as e:
            logger.warning("[Archive/Anchoring] sync_fetch failed: %s", e)
            return None

    def _anchor_background_refresh(self) -> None:
        """Background thread to refresh anchor cache."""
        if self._anchor_is_cache_valid():
            return
        self._anchor_sync_fetch()
        if self._anchor_cache:
            logger.info("[Archive/Anchoring] background refresh complete: %s", 
                        getattr(self._anchor_cache, 'snapshot_id', 'unknown'))

    def _get_anchor_block(self) -> str:
        """Return formatted anchor block with live market data."""
        if not _ANCHORING_AVAILABLE or not format_full_anchor_text:
            return ""
        snapshot = None
        if self._anchor_is_cache_valid():
            snapshot = self._anchor_cache
        if snapshot is None:
            snapshot = self._anchor_sync_fetch()
        if snapshot is None:
            return ""
        if not snapshot.quote.last:
            return ""
        return format_full_anchor_text(snapshot)

    def prefetch(self, query: str = "", *, session_id: str = "") -> str:
        """Return relevant context from archive based on user query."""
        if not self._manager:
            return ""

        context_parts = []

        # 1. If query provided, do FTS5 search for relevant conversations
        if query and len(query) > 2:
            try:
                conn = self._manager._conn()
                # Sanitize query for FTS5 (escape special chars, use OR for multi-word)
                words = [w for w in query.split() if len(w) > 2 and w.isalnum()]
                if words:
                    fts_query = " OR ".join(words)
                    # FTS5 search in conversations
                    cursor = conn.execute(
                        """SELECT c.content, c.role, c.timestamp 
                           FROM conversations c
                           JOIN conversations_fts fts ON c.id = fts.rowid
                           WHERE conversations_fts MATCH ?
                           ORDER BY c.timestamp DESC LIMIT 3""",
                        (fts_query,)
                    )
                    rows = cursor.fetchall()
                    if rows:
                        context_parts.append("## Relevant past conversations:")
                        for row in rows:
                            content = row[0][:200] + "..." if len(row[0]) > 200 else row[0]
                            context_parts.append(f"- [{row[1]}] {content}")
            except Exception as e:
                logger.debug("FTS5 conversation search failed: %s", e)

            # 2. Search relevant facts
            try:
                facts = self._manager.search_facts(query, limit=3)
                if facts:
                    context_parts.append("\n## Relevant facts:")
                    for f in facts:
                        context_parts.append(f"- {f['key']}: {f['value']} (seen {f['frequency']}x)")
            except Exception as e:
                logger.debug("Fact search failed: %s", e)

            # 3. Search relevant skills
            try:
                conn = self._manager._conn()
                cursor = conn.execute(
                    """SELECT skill_name, file_path, content_summary
                       FROM skill_refs
                       WHERE skill_name LIKE ? OR content_summary LIKE ?
                       LIMIT 2""",
                    (f"%{query}%", f"%{query}%")
                )
                rows = cursor.fetchall()
                if rows:
                    context_parts.append("\n## Relevant skills:")
                    for row in rows:
                        context_parts.append(f"- {row[0]}: {row[1]}")
            except Exception as e:
                logger.debug("Skill search failed: %s", e)

        # 4. Fallback: high-frequency facts if no query or no results
        if not context_parts:
            facts = self._manager.search_facts("", limit=5)
            if facts:
                context_parts.append("## Key facts from memory:")
                for f in facts:
                    context_parts.append(f"- {f['key']}: {f['value']} (seen {f['frequency']}x)")

        # --- Prepend live market anchor block ---
        anchor_block = self._get_anchor_block()
        if anchor_block:
            context_parts.insert(0, anchor_block)

        return "\n".join(context_parts) if context_parts else ""

    def queue_prefetch(self, query: str, *, session_id: str = "") -> None:
        """Trigger background refresh of anchor cache."""
        t = threading.Thread(target=self._anchor_background_refresh, daemon=True)
        t.start()

    def on_turn_start(self, turn_number: int, message: str, **kwargs) -> None:
        with self._buffer_lock:
            self._turn_buffer.append({
                "role": "user",
                "content": message,
                "turn": turn_number,
            })

    def sync_turn(self, user_content: str, assistant_content: str, *, session_id: str = "") -> None:
        if not self._manager:
            return

        with self._buffer_lock:
            self._turn_buffer.append({
                "role": "assistant",
                "content": assistant_content,
            })
            for msg in self._turn_buffer:
                self._manager.archive_message(
                    session_id or self._session_id,
                    msg["role"],
                    msg["content"],
                    self._platform,
                )
                self._manager.extract_facts(self._session_id, msg["content"])
            self._turn_buffer.clear()

        if user_content:
            self._manager.extract_facts(self._session_id, user_content)

    def on_session_end(self, messages: List[Dict[str, Any]]) -> None:
        if not self._manager:
            return

        with self._buffer_lock:
            for msg in self._turn_buffer:
                self._manager.archive_message(
                    self._session_id,
                    msg["role"],
                    msg["content"],
                    self._platform,
                )
            self._turn_buffer.clear()

        if messages:
            self._manager.archive_session(self._session_id, messages, self._platform)

        logger.debug("Archive session end: %s", self._session_id)

    def on_memory_write(self, action: str, target: str, content: str,
                        metadata: Optional[Dict[str, Any]] = None) -> None:
        if action == "add" and target == "user" and content and self._manager:
            self._manager.extract_facts(self._session_id, content)

    def get_tool_schemas(self) -> List[Dict[str, Any]]:
        return [
            {
                "name": "archive_search",
                "description": "Search the memory archive for past conversations, facts, and skills. Uses SQLite FTS5. Returns conversation snippets + skill file references (use skill_view to read full skill content).",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Search query"},
                        "limit": {"type": "integer", "description": "Max results per category (default 10)", "default": 10},
                        "days": {"type": "integer", "description": "Limit conversations to last N days (optional)", "default": None},
                        "include_skills": {"type": "boolean", "description": "Include skill index in search (default true)", "default": True},
                    },
                    "required": ["query"],
                },
            },
            {
                "name": "archive_distill",
                "description": "Generate weekly distilled summary of high-frequency facts and topics.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "week_start": {"type": "string", "description": "Week start date YYYY-MM-DD (optional)"},
                    },
                    "required": [],
                },
            },
            {
                "name": "archive_stats",
                "description": "Get archive statistics (size, message count, fact count, skill count).",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },
            {
                "name": "archive_index_skills",
                "description": "Re-index all skill files for search.",
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": [],
                },
            },

        ]

    def handle_tool_call(self, tool_name: str, args: dict, **kwargs) -> str:
        if not self._manager:
            return tool_error("Archive memory not initialized.")

        try:
            if tool_name == "archive_search":
                query = args.get("query", "")
                if not query:
                    return tool_error("Missing required parameter: query")
                limit = min(int(args.get("limit", 10)), 50)
                days = args.get("days")
                if days is not None:
                    days = int(days)
                include_skills = args.get("include_skills", True)

                results = self._manager.search(query, limit=limit, days=days, include_skills=include_skills)

                output = []

                # Conversations
                convs = results.get("conversations", [])
                if convs:
                    output.append(f"## Conversations ({len(convs)} matches)")
                    for r in convs:
                        ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
                        output.append(f"\n### [{ts}] Session: {r.get('session_id', 'unknown')[:16]}...")
                        # Show context: user + assistant paired
                        for ctx in r.get("context", []):
                            ctx_ts = datetime.fromtimestamp(ctx["timestamp"]).strftime("%H:%M:%S")
                            role_icon = "🧑" if ctx["role"] == "user" else "🤖" if ctx["role"] == "assistant" else "🔧"
                            match_marker = " **← MATCH**" if ctx.get("is_match") else ""
                            content_preview = ctx["content"][:300].replace("\n", " ")
                            output.append(f"{role_icon} [{ctx_ts}] {ctx['role']}: {content_preview}{match_marker}")
                        output.append("")  # blank line between sessions

                # Facts
                facts = results.get("facts", [])
                if facts:
                    output.append(f"\n## Facts ({len(facts)} matches)")
                    for f in facts:
                        output.append(f"- {f['key']}: {f['value']} (seen {f['frequency']}x)")

                # Skills
                skills = results.get("skills", [])
                if skills:
                    output.append(f"\n## Skills ({len(skills)} matches)")
                    for s in skills:
                        snippet = s.get('snippet', '')
                        output.append(f"- {s['skill_name']}: {snippet[:200] if snippet else '(no preview)'}")
                        output.append(f"  File: {s['file_path']} (use skill_view to read)")

                if not output:
                    return json.dumps({"result": "No matches found."})

                return json.dumps({
                    "result": f"Found {len(convs)} conversations, {len(facts)} facts, {len(skills)} skills",
                    "details": "\n".join(output),
                })

            elif tool_name == "archive_distill":
                week_start = args.get("week_start")
                summary = self._manager.distill_week(week_start)
                return json.dumps({
                    "result": f"Distilled week starting {summary['week_start']}",
                    "total_messages": summary["total_messages"],
                    "top_facts": summary["top_facts"],
                    "top_topics": summary["top_topics"],
                })

            elif tool_name == "archive_stats":
                stats = self._manager.stats()
                return json.dumps({"result": "Archive statistics", **stats})

            elif tool_name == "archive_index_skills":
                count = self._manager.index_all_skills()
                return json.dumps({"result": f"Indexed {count} skills"})

            return tool_error(f"Unknown tool: {tool_name}")

        except Exception as e:
            logger.error("Archive tool %s failed: %s", tool_name, e)
            return tool_error(f"Archive {tool_name} failed: {e}")

    def shutdown(self) -> None:
        pass


# ---------------------------------------------------------------------------
# Plugin entry point
# ---------------------------------------------------------------------------

def register(ctx) -> None:
    ctx.register_memory_provider(ArchiveMemoryProvider())
