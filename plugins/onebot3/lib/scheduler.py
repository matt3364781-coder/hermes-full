#!/usr/bin/env python3
"""
scheduler.py — ONE Bot 3.0 统一调度器

职责：
  • 线程A: 脉冲循环（每5分钟，L1数据采集+计算+存储）
  • 线程B: 备份循环（每60分钟，archive.db 增量导出到 data/memory_backups/）
  • 线程C: 日蒸馏循环（每工作日20:00 CDT，生成盘后摘要供 Hermes 读取）

启动方式：
  from scheduler import start_all, stop_all
  start_all()  → 启动 daemon 线程

不依赖 cron，不依赖 gateway 插件系统。
"""

import os
import sys
import time
import json
import gzip
import sqlite3
import logging
import threading
from datetime import datetime, timezone, timedelta
from pathlib import Path

logger = logging.getLogger("onebot3.scheduler")

# ── 路径常量 ──
PLUGIN_DIR = Path(__file__).parent.resolve()
DATA_DIR = PLUGIN_DIR / "data"
MARKET_DB = DATA_DIR / "market.db"
MEMORY_BACKUPS = DATA_DIR / "memory_backups"
DAILY_REPORTS = DATA_DIR / "daily_reports"
ARCHIVE_DB = Path.home() / ".hermes" / "memory" / "archive.db"
CHECKPOINT = MEMORY_BACKUPS / "checkpoint.json"

# 备份只导这三个表
BACKUP_TABLES = {
    "conversations": "id",
    "facts": "id",
    "skill_refs": "id",
}

FULL_SNAPSHOT_INTERVAL = 7 * 24 * 3600  # 7天

# ── 全局状态 ──
_stop = threading.Event()
_threads: list[threading.Thread] = []
_pulse_count = 0


def _start_pulse_loop():
    """线程A: 每5分钟跑一次脉冲"""
    global _pulse_count
    # 延迟导入，避免 import 时加载
    sys.path.insert(0, str(PLUGIN_DIR))
    from anchoring.engine import AnchoringEngine

    eng = AnchoringEngine()
    logger.info("[SCHEDULER] Pulse loop started (5min interval)")

    while not _stop.is_set():
        try:
            eng._pulse()
            _pulse_count += 1
            snap = eng._latest_snapshot
            if snap:
                spot = snap.get("underlying_price", 0)
                contracts = snap.get("chain_summary", {}).get("total_contracts", 0)
                gex_net = snap.get("gex", {}).get("net_gex", 0)
                signal = snap.get("indicators", {}).get("signal", "N/A")
                logger.info(
                    "[PULSE] #%d | $%.2f | %d contracts | GEX=$%s | %s",
                    _pulse_count, spot, contracts,
                    f"{gex_net:,.0f}" if gex_net else "0",
                    signal,
                )
        except Exception as e:
            logger.error("[PULSE] Error: %s", e, exc_info=True)
        _stop.wait(300)  # 5 min


def _start_backup_loop():
    """线程B: 每60分钟备份 archive.db 增量到 data/memory_backups/"""
    logger.info("[SCHEDULER] Backup loop started (60min interval)")

    while not _stop.is_set():
        try:
            _do_backup()
        except Exception as e:
            logger.error("[BACKUP] Error: %s", e, exc_info=True)
        _stop.wait(3600)  # 60 min


def _load_checkpoint() -> dict:
    if CHECKPOINT.exists():
        with open(CHECKPOINT) as f:
            return json.load(f)
    return {}


def _save_checkpoint(state: dict):
    MEMORY_BACKUPS.mkdir(parents=True, exist_ok=True)
    with open(CHECKPOINT, "w") as f:
        json.dump(state, f, indent=2)


def _do_backup():
    """增量备份核心逻辑"""
    if not ARCHIVE_DB.exists():
        logger.warning("[BACKUP] archive.db not found at %s", ARCHIVE_DB)
        return

    MEMORY_BACKUPS.mkdir(parents=True, exist_ok=True)
    state = _load_checkpoint()
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    batch = {}
    total_new = 0

    conn = sqlite3.connect(str(ARCHIVE_DB))
    conn.row_factory = sqlite3.Row

    for table, pk in BACKUP_TABLES.items():
        last_id = state.get(f"last_{table}_id", 0)
        rows = conn.execute(
            f"SELECT * FROM {table} WHERE {pk} > ? ORDER BY {pk}", (last_id,)
        ).fetchall()
        if rows:
            batch[table] = [dict(r) for r in rows]
            total_new += len(rows)
            state[f"last_{table}_id"] = max(r[pk] for r in rows)

    conn.close()

    if total_new == 0:
        logger.info("[BACKUP] No new data, skip")
        return

    # 写入增量文件
    fname = f"incremental.{timestamp}.json.gz"
    fpath = MEMORY_BACKUPS / fname
    data = json.dumps(batch, ensure_ascii=False, default=str)
    with gzip.open(fpath, "wt", encoding="utf-8") as f:
        f.write(data)

    state["last_incremental_ts"] = timestamp
    _save_checkpoint(state)

    # 全量快照（每7天）
    last_full = state.get("last_full_snapshot_ts", 0)
    if time.time() - last_full >= FULL_SNAPSHOT_INTERVAL:
        _do_full_snapshot(state)

    fsize = os.path.getsize(fpath) / (1024 * 1024)
    logger.info("[BACKUP] Done: %s (%.2f MB, %d rows)", fname, fsize, total_new)


def _do_full_snapshot(state: dict):
    import shutil
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    fname = f"full.{timestamp}.sqlite.gz"
    fpath = MEMORY_BACKUPS / fname

    # gzip 压缩拷贝
    with open(str(ARCHIVE_DB), "rb") as f_in:
        with gzip.open(str(fpath), "wb") as f_out:
            f_out.write(f_in.read())

    state["last_full_snapshot"] = f"{fpath.name}"
    state["last_full_snapshot_ts"] = time.time()
    _save_checkpoint(state)

    # 清理过期增量文件（>14天）
    now = time.time()
    for f in MEMORY_BACKUPS.iterdir():
        if f.name == "checkpoint.json" or not f.is_file():
            continue
        if now - f.stat().st_mtime > FULL_SNAPSHOT_INTERVAL * 2:
            f.unlink()
            logger.info("[BACKUP] Cleaned old: %s", f.name)

    fsize = os.path.getsize(fpath) / (1024 * 1024)
    logger.info("[BACKUP] Full snapshot: %s (%.2f MB)", fname, fsize)


def _start_daily_distill_loop():
    """线程C: 每工作日20:00 CDT跑日蒸馏 → 直接推Telegram"""
    logger.info("[SCHEDULER] Daily distill loop started (weekdays 20:00 CDT)")

    # 从 .env 读 bot token
    env_path = Path.home() / ".hermes" / ".env"
    bot_token = None
    if env_path.exists():
        with open(env_path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN="):
                    bot_token = line.split("=", 1)[1]
                    break

    if not bot_token:
        logger.error("[DISTILL] TELEGRAM_BOT_TOKEN not found, thread disabled")
        return

    _last_run_date = ""

    while not _stop.is_set():
        try:
            now = datetime.now()
            date_str = now.strftime("%Y-%m-%d")

            # 工作日 + 20:00 整點 + 當天還沒跑過
            if (now.weekday() < 5 and now.hour == 20 and now.minute == 0
                    and date_str != _last_run_date):
                _do_daily_distill(bot_token, date_str)
                _last_run_date = date_str
                _stop.wait(120)  # 等過1分鐘，避免重複觸發
            else:
                _stop.wait(30)  # 每30秒檢查一次
        except Exception as e:
            logger.error("[DISTILL] Error: %s", e, exc_info=True)
            _stop.wait(60)


def _do_daily_distill(bot_token: str, date_str: str):
    """执行日蒸馏 → 存檔 + Telegram推送"""
    import urllib.request
    import urllib.parse

    logger.info("[DISTILL] Running daily distill for %s...", date_str)

    sys.path.insert(0, str(PLUGIN_DIR))
    from distiller.engine import format_daily_block

    report = format_daily_block(date_str)

    # 存檔
    DAILY_REPORTS.mkdir(parents=True, exist_ok=True)
    report_path = DAILY_REPORTS / f"{date_str}.txt"
    report_path.write_text(report)
    logger.info("[DISTILL] Report saved: %s (%d chars)", report_path, len(report))

    # Telegram 推送
    chat_id = "5947296921"
    payload = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": report,
        "parse_mode": "HTML",
    }).encode()
    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    req = urllib.request.Request(url, data=payload, method="POST")
    resp = urllib.request.urlopen(req, timeout=15)
    logger.info("[DISTILL] Telegram push OK: %s", resp.read().decode()[:120])



def start_all():
    """启动所有定时线程"""
    global _threads
    if _threads:
        logger.warning("[SCHEDULER] Already running, skip")
        return

    _stop.clear()

    t1 = threading.Thread(target=_start_pulse_loop, daemon=True, name="onebot-pulse")
    t2 = threading.Thread(target=_start_backup_loop, daemon=True, name="onebot-backup")
    t3 = threading.Thread(target=_start_daily_distill_loop, daemon=True, name="onebot-distill")
    t1.start()
    t2.start()
    t3.start()
    _threads = [t1, t2, t3]
    logger.info("[SCHEDULER] Started: pulse=5min, backup=60min, distill=weekday 20:00")


def stop_all():
    """停止所有定时线程"""
    global _threads
    if not _threads:
        return
    _stop.set()
    _threads = []
    logger.info("[SCHEDULER] Stopped")
