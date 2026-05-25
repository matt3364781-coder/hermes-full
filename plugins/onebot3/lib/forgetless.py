#!/usr/bin/env python3
"""
forgetless — 拉 archive.db N 小时内完整对话原文

用法:
  python3 forgetless.py --hours 2
  python3 forgetless.py --hours 6 --session-only
  python3 forgetless.py --since "2026-05-24 05:00"
"""
import sqlite3
import time
import argparse
from datetime import datetime, timedelta
from pathlib import Path

ARCHIVE_DB = Path.home() / ".hermes" / "memory" / "archive.db"

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--hours", type=float, default=None, help="拉过去N小时")
    parser.add_argument("--since", type=str, default=None, help="起始时间 'YYYY-MM-DD HH:MM'")
    parser.add_argument("--session-only", action="store_true", help="只列session清单，不输出消息")
    args = parser.parse_args()

    if not ARCHIVE_DB.exists():
        print(f"❌ archive.db 不存在: {ARCHIVE_DB}")
        return

    # 计算时间范围
    if args.since:
        since = datetime.strptime(args.since, "%Y-%m-%d %H:%M").timestamp()
    elif args.hours:
        since = time.time() - args.hours * 3600
    else:
        since = time.time() - 2 * 3600  # 默认2小时

    since_str = datetime.fromtimestamp(since).strftime("%Y-%m-%d %H:%M")
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")

    conn = sqlite3.connect(str(ARCHIVE_DB))
    conn.row_factory = sqlite3.Row

    # 获取该时间范围内的session
    sessions = conn.execute("""
        SELECT session_id, MIN(timestamp) as first, MAX(timestamp) as last, COUNT(*) as cnt
        FROM conversations
        WHERE timestamp > ?
        GROUP BY session_id
        ORDER BY first
    """, (since,)).fetchall()

    if not sessions:
        print(f"📭 {since_str} → {now_str} 无对话记录")
        return

    total_msgs = sum(s["cnt"] for s in sessions)
    print(f"📋 {since_str} → {now_str}  |  {len(sessions)} 个会话, {total_msgs} 条消息\n")

    if args.session_only:
        for s in sessions:
            first = datetime.fromtimestamp(s["first"]).strftime("%H:%M")
            last = datetime.fromtimestamp(s["last"]).strftime("%H:%M")
            print(f"  [{first}→{last}] {s['session_id'][:32]}... ({s['cnt']}条)")
        return

    # 输出每个session的消息
    for s in sessions:
        sid = s["session_id"]
        first = datetime.fromtimestamp(s["first"]).strftime("%H:%M")
        last = datetime.fromtimestamp(s["last"]).strftime("%H:%M")
        print(f"{'='*60}")
        print(f"📌 {first}→{last}  {sid}  ({s['cnt']}条)")
        print(f"{'='*60}")

        msgs = conn.execute("""
            SELECT role, content, timestamp
            FROM conversations
            WHERE session_id = ?
            ORDER BY timestamp
        """, (sid,)).fetchall()

        for m in msgs:
            ts = datetime.fromtimestamp(m["timestamp"]).strftime("%H:%M:%S")
            role = m["role"]
            content = m["content"]

            if role == "user":
                print(f"\n🧑 [{ts}] {content}")
            elif role == "assistant":
                # 截断太长回复，留前300字
                text = content[:300] + "..." if len(content) > 300 else content
                print(f"\n🤖 [{ts}] {text}")
            elif role == "tool":
                # 工具输出只显示关键信息
                out = content[:150].replace("\n", " ")
                print(f"\n  🔧 {out}")

        print()

    conn.close()

if __name__ == "__main__":
    main()
