#!/usr/bin/env python3
"""
distiller/engine.py — L3: 蒸馏归档引擎

职责：
  • 读取 anchoring SQLite DB 中的原始数据
  • 按日/周/月生成结构化摘要（价格 + GEX + 情绪 + 宏观）
  • 供 Agent 查询历史行情/信号

依赖：
  - anchoring 的 DB（onebot_data.db）
  - DB 中的 daily_summaries / weekly_summaries / monthly_summaries 表
"""

from __future__ import annotations

import json
import sqlite3
import logging
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger("onebot3.distiller")

_DEFAULT_DB = Path(__file__).parent.parent / "data" / "market.db"


class DistillerEngine:
    """L3 蒸馏引擎：读 DB → 结构化归档 → 查询接口"""

    def __init__(self, db_path: str | Path = str(_DEFAULT_DB)):
        self.db_path = str(Path(db_path).expanduser().resolve())
        self._conn: Optional[sqlite3.Connection] = None

    @property
    def conn(self) -> sqlite3.Connection:
        if self._conn is None:
            self._conn = sqlite3.connect(self.db_path)
            self._conn.row_factory = sqlite3.Row
        return self._conn

    # ── 查询接口 ──

    def get_daily_summary(self, date: str | None = None) -> Dict[str, Any]:
        """获取单日摘要"""
        if date is None:
            date = datetime.now().strftime("%Y-%m-%d")
        cur = self.conn.execute(
            "SELECT * FROM daily_summaries WHERE date = ?",
            (date,),
        )
        row = cur.fetchone()
        if not row:
            return {"date": date, "status": "not_available"}
        return dict(row)

    def get_daily_range(self, start: str, end: str) -> List[Dict[str, Any]]:
        """获取日期范围摘要"""
        cur = self.conn.execute(
            "SELECT * FROM daily_summaries WHERE date >= ? AND date <= ? ORDER BY date",
            (start, end),
        )
        return [dict(r) for r in cur.fetchall()]

    def get_weekly_summary(self, week_start: str | None = None) -> Dict[str, Any]:
        if week_start is None:
            today = datetime.now()
            monday = today - timedelta(days=today.weekday())
            week_start = monday.strftime("%Y-%m-%d")
        cur = self.conn.execute(
            "SELECT * FROM weekly_summaries WHERE week_start = ?",
            (week_start,),
        )
        row = cur.fetchone()
        return dict(row) if row else {"week_start": week_start, "status": "not_available"}

    def get_monthly_summary(self, month: str | None = None) -> Dict[str, Any]:
        if month is None:
            month = datetime.now().strftime("%Y-%m")
        cur = self.conn.execute(
            "SELECT * FROM monthly_summaries WHERE month = ?",
            (month,),
        )
        row = cur.fetchone()
        return dict(row) if row else {"month": month, "status": "not_available"}

    def get_latest_gex(self, limit: int = 5) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT timestamp, ticker, gex_json FROM raw_snapshots "
            "WHERE gex_json IS NOT NULL ORDER BY timestamp DESC LIMIT ?",
            (limit,),
        )
        results = []
        for r in cur.fetchall():
            item = {"timestamp": r["timestamp"], "ticker": r["ticker"]}
            try:
                item["gex"] = json.loads(r["gex_json"])
            except Exception:
                item["gex"] = {}
            results.append(item)
        return results

    def get_historical_spot(self, days: int = 5) -> List[Dict[str, Any]]:
        cur = self.conn.execute(
            "SELECT timestamp, underlying_price, vix FROM raw_snapshots "
            "ORDER BY timestamp DESC LIMIT ?",
            (days * 288,),  # 5min * 288 = 1 day
        )
        rows = cur.fetchall()
        # 去重采样到小时级别
        seen = set()
        result = []
        for r in reversed(rows):
            hour_slot = r["timestamp"][:13]
            if hour_slot not in seen:
                seen.add(hour_slot)
                result.append({"time": r["timestamp"], "spot": r["underlying_price"], "vix": r["vix"]})
        return result[-days * 8:]

    # ── 格式化输出 ──

    def format_daily_block(self, date: str | None = None) -> str:
        daily = self.get_daily_summary(date)
        if daily.get("status") == "not_available":
            return f"[Distiller] Daily {date or 'today'}: no data"

        weekly = self.get_weekly_summary()
        monthly = self.get_monthly_summary()

        lines = [
            f"[ONE Bot 3.0] Distilled Report — {daily.get('date', 'N/A')}",
            f"Price: O={daily.get('open_price', 'N/A')} H={daily.get('high_price', 'N/A')} "
            f"L={daily.get('low_price', 'N/A')} C={daily.get('close_price', 'N/A')}",
            f"VIX: {daily.get('vix_open', 'N/A')} → {daily.get('vix_close', 'N/A')}",
            f"GEX: Net=${daily.get('net_gex', 0):,.0f} | "
            f"Call=${daily.get('call_wall', 0):.1f} Put=${daily.get('put_wall', 0):.1f}",
            f"Sentiment: P/C Vol={daily.get('pc_vol', 0):.2f} OI={daily.get('pc_oi', 0):.2f} "
            f"Skew={daily.get('iv_skew', 0):.4f}",
            f"Analyst: {daily.get('analyst_consensus', 'N/A')}",
            f"Macro: {daily.get('macro_count', 0)} events | "
            f"Earnings: {daily.get('earnings_count', 0)} reports",
        ]

        if weekly.get("status") != "not_available":
            lines.append(f"Weekly: {weekly.get('week_start')}–{weekly.get('week_end')} "
                         f"| {weekly.get('regime', 'N/A')}")

        lines.append("[ONE Bot 3.0-END]")
        return "\n".join(lines)

    def format_trend(self, days: int = 5) -> str:
        daily_list = self.get_daily_range(
            (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d"),
            datetime.now().strftime("%Y-%m-%d"),
        )
        if not daily_list:
            return "[Distiller] No daily data available"

        closes = [d.get("close_price", 0) for d in daily_list if d.get("close_price")]
        trend = "up" if closes and closes[-1] > closes[0] else "down" if closes and closes[-1] < closes[0] else "flat"
        change = ((closes[-1] / closes[0]) - 1) * 100 if len(closes) >= 2 else 0

        gex_drift = "rising" if len(daily_list) >= 3 and daily_list[-1].get("net_gex", 0) > daily_list[-3].get("net_gex", 0) else "falling" if len(daily_list) >= 3 else "stable"

        lines = [
            f"[ONE Bot 3.0] Trend — Last {len(closes)} days",
            f"Trend: {trend} ({change:+.2f}%)",
            f"GEX drift: {gex_drift}",
        ]
        for d in daily_list[-5:]:
            g = d.get("net_gex", 0)
            gex_label = "Call" if g > 0 else "Put" if g < 0 else "Flat"
            lines.append(f"{d['date']}: C={d.get('close_price', 0):.1f} "
                         f"VIX={d.get('vix_close', 0):.1f} GEX={gex_label}(${g:,.0f})")

        lines.append("[ONE Bot 3.0-END]")
        return "\n".join(lines)


# ── 模块级单例 ──

_engine: DistillerEngine | None = None


def get_engine() -> DistillerEngine:
    global _engine
    if _engine is None:
        _engine = DistillerEngine()
    return _engine


def get_daily_summary(date: str | None = None) -> Dict[str, Any]:
    return get_engine().get_daily_summary(date)


def get_daily_range(start: str, end: str) -> List[Dict[str, Any]]:
    return get_engine().get_daily_range(start, end)


def format_daily_block(date: str | None = None) -> str:
    return get_engine().format_daily_block(date)


def format_trend(days: int = 5) -> str:
    return get_engine().format_trend(days)


def get_latest_gex(limit: int = 5) -> List[Dict[str, Any]]:
    return get_engine().get_latest_gex(limit)
