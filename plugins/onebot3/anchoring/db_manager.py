#!/usr/bin/env python3
"""
db_manager.py — SQLite persistence + auto-distillation + TTL cleanup
"""

import json
import logging
import sqlite3
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List

logger = logging.getLogger("onebot3.db")

class DBManager:
    def __init__(self, db_path: str, retention_cfg: Optional[Dict] = None):
        self.db_path = db_path
        self.cfg = retention_cfg or {}
        self.raw_ttl_hours = self.cfg.get("raw_hours", 4)
        self.daily_ttl_days = self.cfg.get("daily_days", 10)
        self.weekly_ttl_weeks = self.cfg.get("weekly_weeks", 8)
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

    def init_tables(self) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            CREATE TABLE IF NOT EXISTS raw_snapshots (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                snapshot_id TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                market_open INTEGER NOT NULL,
                underlying_price REAL,
                vix REAL,
                chain_count INTEGER,
                chain_expirations TEXT,
                gex_json TEXT,
                sentiment_json TEXT,
                hist_json TEXT,
                macro_json TEXT,
                earnings_json TEXT,
                analyst_json TEXT,
                full_json TEXT NOT NULL,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS daily_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                date TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                volume INTEGER,
                vix_open REAL,
                vix_close REAL,
                net_gex REAL,
                call_wall REAL,
                put_wall REAL,
                zero_gamma REAL,
                max_pain REAL,
                pc_vol REAL,
                pc_oi REAL,
                iv_skew REAL,
                macro_count INTEGER,
                earnings_count INTEGER,
                analyst_consensus TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS weekly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                week_start TEXT NOT NULL,
                week_end TEXT NOT NULL,
                ticker TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                net_gex_start REAL,
                net_gex_end REAL,
                regime TEXT,
                pc_vol_avg REAL,
                pc_oi_avg REAL,
                iv_skew_avg REAL,
                key_events TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("""
            CREATE TABLE IF NOT EXISTS monthly_summaries (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                month TEXT UNIQUE NOT NULL,
                ticker TEXT NOT NULL,
                open_price REAL,
                high_price REAL,
                low_price REAL,
                close_price REAL,
                trend TEXT,
                gex_drift TEXT,
                sentiment_arc TEXT,
                key_events TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_ticker_ts ON raw_snapshots(ticker, timestamp)")
        cur.execute("CREATE INDEX IF NOT EXISTS idx_raw_created ON raw_snapshots(created_at)")
        self.conn.commit()
        logger.info("[DB] Tables initialized at %s", self.db_path)

    def save_raw_snapshot(self, snap: Dict[str, Any]) -> None:
        cur = self.conn.cursor()
        gex = snap.get("gex", {})
        sentiment = snap.get("sentiment", {})
        cur.execute("""
            INSERT OR REPLACE INTO raw_snapshots (
                snapshot_id, ticker, timestamp, market_open, underlying_price, vix,
                chain_count, chain_expirations,
                gex_json, sentiment_json, hist_json, macro_json, earnings_json, analyst_json,
                full_json
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            snap["snapshot_id"], snap["ticker"], snap["timestamp"],
            1 if snap.get("market_open") else 0,
            snap.get("underlying_price"), snap.get("vix"),
            snap.get("chain_summary", {}).get("total_contracts", 0),
            json.dumps(snap.get("chain_summary", {}).get("expirations", [])),
            json.dumps(gex), json.dumps(sentiment),
            json.dumps(snap.get("historical", [])),
            json.dumps(snap.get("macro", [])),
            json.dumps(snap.get("earnings", [])),
            json.dumps(snap.get("analyst", {})),
            json.dumps(snap),
        ))
        self.conn.commit()

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        cur = self.conn.cursor()
        cur.execute("SELECT full_json FROM raw_snapshots ORDER BY timestamp DESC LIMIT 1")
        row = cur.fetchone()
        return json.loads(row["full_json"]) if row else None

    def distill_if_needed(self, snap: Dict[str, Any]) -> None:
        ticker = snap["ticker"]
        today = datetime.now().strftime("%Y-%m-%d")
        cur = self.conn.cursor()
        cur.execute("SELECT 1 FROM daily_summaries WHERE date = ? AND ticker = ?", (today, ticker))
        if cur.fetchone():
            return
        self._update_daily_summary(today, ticker)

    def _update_daily_summary(self, date: str, ticker: str) -> None:
        cur = self.conn.cursor()
        cur.execute("""
            SELECT underlying_price, vix, gex_json, sentiment_json, macro_json, earnings_json, analyst_json
            FROM raw_snapshots WHERE ticker = ? AND DATE(timestamp) = ? ORDER BY timestamp
        """, (ticker, date))
        rows = cur.fetchall()
        if not rows:
            return
        prices = [r["underlying_price"] for r in rows if r["underlying_price"]]
        vixs = [r["vix"] for r in rows if r["vix"]]
        gexs = [json.loads(r["gex_json"] or "{}") for r in rows]
        sentiments = [json.loads(r["sentiment_json"] or "{}") for r in rows]

        open_p = prices[0] if prices else 0.0
        close_p = prices[-1] if prices else 0.0
        high_p = max(prices) if prices else 0.0
        low_p = min(prices) if prices else 0.0
        vix_o = vixs[0] if vixs else 0.0
        vix_c = vixs[-1] if vixs else 0.0

        last_gex = gexs[-1] if gexs else {}
        last_sent = sentiments[-1] if sentiments else {}

        macro_count = len(json.loads(rows[-1]["macro_json"] or "[]"))
        earnings_count = len(json.loads(rows[-1]["earnings_json"] or "[]"))
        analyst = json.loads(rows[-1]["analyst_json"] or "{}")
        consensus = "neutral"
        if analyst:
            total = sum([analyst.get(k, 0) for k in ["strong_buy", "buy", "hold", "sell", "strong_sell"]])
            if total:
                score = (analyst.get("strong_buy", 0)*2 + analyst.get("buy", 0)*1 +
                         analyst.get("sell", 0)*-1 + analyst.get("strong_sell", 0)*-2) / total
                consensus = "bullish" if score > 0.3 else "bearish" if score < -0.3 else "neutral"

        cur.execute("""
            INSERT OR REPLACE INTO daily_summaries (
                date, ticker, open_price, high_price, low_price, close_price, volume,
                vix_open, vix_close, net_gex, call_wall, put_wall, zero_gamma, max_pain,
                pc_vol, pc_oi, iv_skew, macro_count, earnings_count, analyst_consensus
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            date, ticker, open_p, high_p, low_p, close_p, 0, vix_o, vix_c,
            last_gex.get("net_gex"), last_gex.get("call_wall"), last_gex.get("put_wall"),
            last_gex.get("zero_gamma"), last_gex.get("max_pain"),
            last_sent.get("pc_volume"), last_sent.get("pc_oi"), last_sent.get("iv_skew"),
            macro_count, earnings_count, consensus,
        ))
        self.conn.commit()
        logger.info("[DB] Daily summary distilled: %s %s", date, ticker)

    def cleanup_old(self) -> None:
        cur = self.conn.cursor()
        # SQLite CURRENT_TIMESTAMP = UTC, 用 datetime.utcnow() 保持时区一致
        raw_cutoff = (datetime.utcnow() - timedelta(hours=self.raw_ttl_hours)).strftime("%Y-%m-%d %H:%M:%S")
        cur.execute("DELETE FROM raw_snapshots WHERE created_at < ?", (raw_cutoff,))
        raw_del = cur.rowcount
        daily_cutoff = (datetime.utcnow() - timedelta(days=self.daily_ttl_days)).strftime("%Y-%m-%d")
        cur.execute("DELETE FROM daily_summaries WHERE date < ?", (daily_cutoff,))
        daily_del = cur.rowcount
        weekly_cutoff = (datetime.utcnow() - timedelta(weeks=self.weekly_ttl_weeks)).strftime("%Y-%m-%d")
        cur.execute("DELETE FROM weekly_summaries WHERE week_start < ?", (weekly_cutoff,))
        weekly_del = cur.rowcount
        self.conn.commit()
        if raw_del or daily_del or weekly_del:
            logger.info("[DB] Cleanup: raw=%d daily=%d weekly=%d", raw_del, daily_del, weekly_del)
