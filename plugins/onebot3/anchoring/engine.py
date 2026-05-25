#!/usr/bin/env python3
"""
anchoring/engine.py — L1 Data Engine
职责:
  • 5-minute pulse: 全链期权 + Greeks + 报价 + 宏观 + 财报 + 分析师
  • 实时计算: GEX + 15种技术指标 + 融合信号
  • SQLite 持久化 + 自动清理
  • 格式化输出供 Hermes 注入
"""

import os
import sys
import json
import time
import threading
import logging
from datetime import datetime, timedelta
from typing import Optional, Dict, Any, List
from pathlib import Path

import numpy as np
import pandas as pd

PLUGIN_DIR = Path(__file__).parent.parent.resolve()
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

from anchoring.api_client import MultiSourceClient
from anchoring.db_manager import DBManager
from anchoring.gex_calculator import GEXCalculator, SentimentAnalyzer
from anchoring.indicator_engine import IndicatorEngine
from anchoring.snapshot_formatter import SnapshotFormatter

logger = logging.getLogger("onebot3.anchoring")

def _load_config() -> Dict[str, Any]:
    import yaml
    cfg_path = PLUGIN_DIR / "plugin.yaml"
    if not cfg_path.exists():
        return {}
    with open(cfg_path, "r") as f:
        return yaml.safe_load(f).get("config", {})

def _is_market_open(cfg: Dict) -> bool:
    try:
        import pytz
    except ImportError:
        return True
    tz = pytz.timezone(cfg.get("market_hours", {}).get("timezone", "America/Chicago"))
    now = datetime.now(tz)
    if now.weekday() >= 5:
        return False
    open_t = datetime.strptime(cfg["market_hours"]["open"], "%H:%M").time()
    close_t = datetime.strptime(cfg["market_hours"]["close"], "%H:%M").time()
    return open_t <= now.time() <= close_t

class AnchoringEngine:
    def __init__(self):
        self.cfg = _load_config()
        raw_db = self.cfg.get("db_path", "~/.hermes/plugins/onebot3/onebot_data.db")
        self.db_path = Path(raw_db).expanduser().resolve()
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        self.client = MultiSourceClient(self.cfg)
        self.db = DBManager(str(self.db_path), retention_cfg=self.cfg.get("retention", {}))
        self.gex_calc = GEXCalculator()
        self.sentiment = SentimentAnalyzer()
        self.indicators = IndicatorEngine()
        self.formatter = SnapshotFormatter()

        self._pulse_interval = self.cfg.get("pulse_interval_sec", 300)
        self._thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._lock = threading.Lock()
        self._latest_snapshot: Optional[Dict[str, Any]] = None
        self._running = False

    def start(self) -> None:
        if self._running:
            return
        logger.info("[ANCHORING] Starting L1 engine...")
        self.db.init_tables()
        self._pulse()
        self._thread = threading.Thread(target=self._loop, daemon=True, name="anchoring-pulse")
        self._thread.start()
        self._running = True
        logger.info("[ANCHORING] Pulse started (%ds)", self._pulse_interval)

    def stop(self) -> None:
        if not self._running:
            return
        logger.info("[ANCHORING] Stopping...")
        self._stop_event.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=5.0)
        self._running = False
        self._latest_snapshot = None

    def get_latest_snapshot(self) -> Optional[Dict[str, Any]]:
        with self._lock:
            snap = self._latest_snapshot
        if snap:
            return snap
        return self.db.get_latest_snapshot()

    def get_formatted_block(self) -> str:
        snap = self.get_latest_snapshot()
        if not snap:
            return "[ONE Bot 3.0] Status: INITIALIZING\n[ONE Bot 3.0-END]"
        return self.formatter.format(snap)

    def _loop(self) -> None:
        while not self._stop_event.is_set():
            try:
                if _is_market_open(self.cfg):
                    self._pulse()
                else:
                    logger.debug("Market closed — skip")
            except Exception as e:
                logger.error("[ANCHORING] Pulse error: %s", e, exc_info=True)
            self._stop_event.wait(self._pulse_interval)

    def _pulse(self) -> None:
        t0 = time.time()
        primary = self.cfg.get("tickers", {}).get("primary", "SPY")
        secondaries = self.cfg.get("tickers", {}).get("secondary", [])

        try:
            quotes = self.client.fetch_quotes([primary] + [s for s in secondaries if s])
            spot = quotes.get(primary, {}).get("last", 0.0)
            vix = quotes.get("VIX", {}).get("last", 0.0)

            raw_chain = self.client.fetch_full_option_chain(primary)
            # 过滤到 ±30% 现价范围，排除深虚/深实期权（无OI，只拖慢GEX计算）
            if not raw_chain.empty and spot > 0:
                lo = spot * 0.70
                hi = spot * 1.30
                chain_df = raw_chain[(raw_chain["strike"] >= lo) & (raw_chain["strike"] <= hi)].copy()
                pct = (hi - lo) / spot * 100
                logger.info("Chain filtered: %d → %d rows (%.0f%%: $%.0f–$%.0f, spot=$%.2f)",
                            len(raw_chain), len(chain_df), pct, lo, hi, spot)
            else:
                chain_df = raw_chain
            gex_data = self.gex_calc.compute(chain_df, spot) if not chain_df.empty else {}
            sentiment = self.sentiment.compute(chain_df) if not chain_df.empty else {}

            hist = self.client.fetch_hist_daily(primary, days=60)
            macro = self.client.fetch_macro_calendar(days=7)
            earnings = self.client.fetch_earnings_calendar(days=7)
            analyst = self.client.fetch_analyst_recommendation(primary)

            indicators = {}
            indicator_signal = {"signal": "NEUTRAL", "confidence": 0.0, "divergence": 0.0}
            if hist and len(hist) >= 50:
                df_hist = pd.DataFrame(hist)
                df_hist["date"] = pd.to_datetime(df_hist["date"])
                df_hist = df_hist.sort_values("date").reset_index(drop=True)
                indicators = self.indicators.compute_all(df_hist)
                indicator_signal = self.indicators.fusion_signal(indicators)

            ts = datetime.now().strftime("%Y%m%d_%H%M%S")
            snap_id = f"{primary}_{ts}_CT"
            snapshot = {
                "snapshot_id": snap_id,
                "ticker": primary,
                "timestamp": datetime.now().isoformat(),
                "market_open": _is_market_open(self.cfg),
                "quotes": quotes,
                "underlying_price": spot,
                "vix": vix,
                "chain_summary": {
                    "total_contracts": len(chain_df),
                    "expirations": sorted(chain_df["expiration"].unique().tolist()) if not chain_df.empty else [],
                    "strike_range": [float(chain_df["strike"].min()), float(chain_df["strike"].max())] if not chain_df.empty else [0, 0],
                },
                "gex": gex_data,
                "sentiment": sentiment,
                "indicators": {**indicators, **indicator_signal},
                "historical": hist,
                "macro": macro,
                "earnings": earnings,
                "analyst": analyst,
            }

            self.db.save_raw_snapshot(snapshot)
            self.db.distill_if_needed(snapshot)
            self.db.cleanup_old()

            with self._lock:
                self._latest_snapshot = snapshot

            logger.info(
                "[ANCHORING] Pulse done | %s | Spot=%.2f | VIX=%.2f | Contracts=%d | GEX=%s | Signal=%s | %.2fs",
                snap_id, spot, vix, len(chain_df),
                gex_data.get("regime", "N/A"),
                indicator_signal.get("signal", "N/A"),
                time.time() - t0
            )

        except Exception as e:
            logger.error("[ANCHORING] Pulse failed: %s", e, exc_info=True)
