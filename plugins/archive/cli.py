"""CLI commands for the archive memory plugin."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


def register_cli(subparser):
    """Register CLI subcommands for archive memory."""
    archive_parser = subparser.add_parser(
        "archive",
        help="Manage local memory archive (SQLite + FTS5)",
        description="Search, distill, and inspect the local conversation archive.",
    )
    archive_sub = archive_parser.add_subparsers(dest="archive_cmd")

    # Search
    search_cmd = archive_sub.add_parser("search", help="Search archive conversations")
    search_cmd.add_argument("query", help="Search query")
    search_cmd.add_argument("-n", "--limit", type=int, default=10, help="Max results")
    search_cmd.add_argument("-d", "--days", type=int, help="Limit to last N days")

    # Distill
    distill_cmd = archive_sub.add_parser("distill", help="Generate weekly summary")
    distill_cmd.add_argument("--week", help="Week start YYYY-MM-DD")

    # Stats
    archive_sub.add_parser("stats", help="Show archive statistics")

    # Import legacy memories
    import_cmd = archive_sub.add_parser("import", help="Import legacy MEMORY.md/USER.md")
    import_cmd.add_argument("path", nargs="?", help="Path to memory file (default: ~/.hermes/memories/)")

    return archive_parser


def archive_command(args):
    """Handle archive CLI commands."""
    from plugins.memory.archive import ArchiveManager

    manager = ArchiveManager()
    cmd = getattr(args, "archive_cmd", None)

    if cmd == "search":
        results = manager.search(args.query, limit=args.limit, days=args.days)
        if not results:
            print("No matches found.")
            return 0
        for r in results:
            from datetime import datetime
            ts = datetime.fromtimestamp(r["timestamp"]).strftime("%Y-%m-%d %H:%M")
            print(f"\n[{ts}] {r['role']}")
            print(f"  {r.get('snippet', r['content'][:200])}")
        return 0

    elif cmd == "distill":
        summary = manager.distill_week(args.week)
        print(json.dumps(summary, indent=2, ensure_ascii=False))
        return 0

    elif cmd == "stats":
        stats = manager.stats()
        print(json.dumps(stats, indent=2))
        return 0

    elif cmd == "import":
        path = args.path or str(Path.home() / ".hermes" / "memories")
        p = Path(path)
        if p.is_dir():
            files = list(p.glob("*.md"))
        else:
            files = [p] if p.exists() else []

        total = 0
        for f in files:
            content = f.read_text()
            # Simple import: treat each paragraph as a fact
            for line in content.split("\n"):
                line = line.strip()
                if line and not line.startswith("#"):
                    # Extract key-value-ish lines
                    if ":" in line or "=" in line or "is" in line.lower():
                        manager.extract_facts("legacy-import", line)
                        total += 1
        print(f"Imported {total} facts from {len(files)} files.")
        return 0

    else:
        print("Usage: hermes archive {search|distill|stats|import}")
        return 1
