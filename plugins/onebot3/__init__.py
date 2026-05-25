#!/usr/bin/env python3
"""
onebot3/__init__.py — ONE Bot 3.0 Unified Plugin

L1: anchoring/ — Data Acquisition + Indicators + GEX
L2: kronos/   — Model Prediction (Kronos-base Transformer)
L3: distiller/ — Archive Distillation

部署路径: ~/.hermes/plugins/onebot3/
"""

import os
import sys
import logging
import threading
from pathlib import Path
from typing import Optional, Dict, Any, List

PLUGIN_DIR = Path(__file__).parent.resolve()
if str(PLUGIN_DIR) not in sys.path:
    sys.path.insert(0, str(PLUGIN_DIR))

logger = logging.getLogger("onebot3")
if not logger.handlers:
    h = logging.StreamHandler()
    h.setFormatter(logging.Formatter("%(asctime)s | %(name)s | %(levelname)-8s | %(message)s"))
    logger.addHandler(h)
    logger.setLevel(logging.INFO)

# ── 数据路径统一 ──
_DATA_DIR = PLUGIN_DIR / "data"
_DB_PATH = _DATA_DIR / "market.db"

def _ensure_db_dir() -> Path:
    _DATA_DIR.mkdir(parents=True, exist_ok=True)
    return _DB_PATH

_anchoring = None

def _get_anchoring(autostart: bool = False):
    global _anchoring
    if _anchoring is None:
        from anchoring.engine import AnchoringEngine
        _anchoring = AnchoringEngine()
        if autostart:
            _anchoring.start()
    return _anchoring

def register(ctx=None):
    """注册插件。如果提供了ctx，同时注册 /forgetless 命令。"""
    logger.info("[ONE Bot 3.0] Plugin registered v3.0.0")

    if ctx is not None:
        try:
            import subprocess
            import shlex
            import json
            import sys as _sys

            PLUGIN_DIR = Path(__file__).parent.resolve()
            if str(PLUGIN_DIR) not in _sys.path:
                _sys.path.insert(0, str(PLUGIN_DIR))
            FORGETLESS_PATH = str(PLUGIN_DIR / "lib" / "forgetless.py")

            def _forgetless_handler(raw_args: str) -> str:
                """/forgetless [hours] [session] — 存档对话交接给新session用"""
                raw = raw_args.strip()
                hours = "2"
                extra = ""
                if raw:
                    parts = raw.split()
                    if parts[0].isdigit():
                        hours = parts[0]
                        parts = parts[1:]
                    extra = " ".join(parts)

                cmd = ["python3", FORGETLESS_PATH, "--hours", hours]
                if "session" in extra:
                    cmd.append("--session-only")

                try:
                    result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                    if result.returncode != 0:
                        return f"❌ 脚本异常: {result.stderr[:500]}"
                    output = result.stdout.strip()
                    if not output:
                        return "📭 无对话记录"

                    # 写入临时文件给agent读
                    out_path = "/tmp/forgetless_output.txt"
                    with open(out_path, "w") as f:
                        f.write(output)
                    # 同时记session数方便回复
                    lines = output.split("\n")
                    session_count = 0
                    msg_count = 0
                    import re
                    for line in lines:
                        m = re.search(r"(\d+) 个会话, (\d+) 条消息", line)
                        if m:
                            session_count = int(m.group(1))
                            msg_count = int(m.group(2))
                            break
                    return f"📦 已加载过去{hours}小时对话（{session_count}个session/{msg_count}条），继续聊就行"
                except Exception as e:
                    return f"❌ 执行失败: {e}"

            ctx.register_command(
                name="forgetless",
                handler=_forgetless_handler,
                description="拉 archive.db N 小时内完整对话原文",
                args_hint="[hours] [session]",
            )
            logger.info("[ONE Bot 3.0] Registered /forgetless command")

            # ── /report 命令 ──────────────────────────────────────────
            def _report_handler(raw_args: str) -> str:
                """/report — 拉 L1+L2 完整数据出报告"""
                from onebot3 import (
                    get_current_snapshot, get_gex_levels, get_indicators,
                    get_sentiment, get_kronos_prediction, get_indicator_signal,
                    get_historical, get_macro_events, get_earnings, get_analyst,
                )
                snap = get_current_snapshot()
                if not snap:
                    return "📭 暂无市场数据（脉冲还没跑过？）"

                lines = ["📊 L1 行情数据"]
                lines.append(f"  标的: {snap.get('ticker', '?')}")
                lines.append(f"  现价: ${snap.get('underlying_price', '?')}")
                lines.append(f"  时间: {snap.get('timestamp', '?')}")

                gex = get_gex_levels()
                if gex:
                    lines.append(f"\n  GEX  regime={gex.get('regime','?')} net={gex.get('net_gex','?')}")
                    lines.append(f"      call_wall={gex.get('call_wall','?')} put_wall={gex.get('put_wall','?')}")
                    lines.append(f"      zero_gamma={gex.get('zero_gamma','?')} max_pain={gex.get('max_pain','?')}")

                ind = get_indicators()
                if ind:
                    lines.append(f"\n  指标: signal={ind.get('signal','?')} conf={ind.get('confidence','?')}")
                    lines.append(f"  divergence={ind.get('divergence','?')}")

                sent = get_sentiment()
                if sent:
                    lines.append(f"\n  情绪: vol_ratio={sent.get('vol_ratio','?')} oi_ratio={sent.get('oi_ratio','?')}")

                macro = get_macro_events(3)
                if macro:
                    lines.append(f"\n  宏观: {'; '.join(str(m) for m in macro)}")

                earnings = get_earnings(3)
                if earnings:
                    lines.append(f"\n  财报: {'; '.join(str(e) for e in earnings)}")

                lines.append(f"\\n📈 L2 Kronos 预测")
                try:
                    kronos = get_kronos_prediction()
                    if kronos and kronos.get("status") == "ok":
                        dir_map = {1: "CALL 🔵", 0: "NEUTRAL ⚪", -1: "PUT 🔴"}
                        d = dir_map.get(kronos.get("direction", 0), "?")
                        lines.append(f"  方向: {d} 置信度={kronos.get('confidence', 0):.0%}")
                        lines.append(f"  分歧度: {['一致','轻度分歧','严重分歧'][kronos.get('agreement', 3)-1]}")
                        lines.append(f"  分类器: {kronos.get('path_type', '?')} zone={kronos.get('zone', '?')}")
                        lines.append(f"  解码器: {kronos.get('decoder_summary', '?')}")
                        gex_a = "✅" if kronos.get("gex_aligned") else "⚠️"
                        lines.append(f"  GEX: {gex_a} net={kronos.get('gex_net', 0):,.0f} regime={kronos.get('gex_regime', '?')}")
                    else:
                        lines.append(f"  (暂无预测: {kronos.get('status', '?')})")
                except Exception as e:
                    lines.append(f"  (预测失败: {e})")

                return "\n".join(lines)

            ctx.register_command(
                name="report",
                handler=_report_handler,
                description="拉L1行情+L2预测数据，我出报告",
            )
            logger.info("[ONE Bot 3.0] Registered /report command")

            # ── 局部 import 被闭包引用，不要 del ──
        except Exception as e:
            logger.warning("[ONE Bot 3.0] Could not register /forgetless: %s", e)

    return {"name": "onebot3", "version": "3.0.0", "layers": ["anchoring", "kronos", "distiller"]}

def setup():
    return register()

def start_scheduler():
    """启动统一调度器（脉冲线程 + 备份线程）"""
    from lib.scheduler import start_all
    start_all()
    logger.info("[ONE Bot 3.0] Scheduler started")

def stop_scheduler():
    """停止统一调度器"""
    from lib.scheduler import stop_all
    stop_all()
    logger.info("[ONE Bot 3.0] Scheduler stopped")

# L1 查询接口 — 读DB缓存，不触发新脉冲
def get_current_snapshot() -> Optional[Dict[str, Any]]:
    from anchoring.db_manager import DBManager
    db_path = _ensure_db_dir()
    if not db_path.exists():
        return None
    db = DBManager(str(db_path))
    return db.get_latest_snapshot()

def get_gex_levels() -> Dict[str, Any]:
    snap = get_current_snapshot()
    if not snap:
        return {}
    gex = snap.get("gex", {})
    return {
        "ticker": snap.get("ticker"),
        "spot": snap.get("underlying_price"),
        "regime": gex.get("regime"),
        "net_gex": gex.get("net_gex"),
        "call_wall": gex.get("call_wall"),
        "put_wall": gex.get("put_wall"),
        "zero_gamma": gex.get("zero_gamma"),
        "max_pain": gex.get("max_pain"),
        "snapshot_id": snap.get("snapshot_id"),
    }

def get_indicators() -> Dict[str, Any]:
    snap = get_current_snapshot()
    if not snap:
        return {}
    return snap.get("indicators", {})

def get_indicator_signal() -> Dict[str, Any]:
    snap = get_current_snapshot()
    if not snap:
        return {"signal": "UNKNOWN", "confidence": 0.0, "divergence": 0.0}
    ind = snap.get("indicators", {})
    return {
        "signal": ind.get("signal", "NEUTRAL"),
        "confidence": ind.get("confidence", 0.0),
        "divergence": ind.get("divergence", 0.0),
        "timestamp": snap.get("timestamp"),
    }

def get_sentiment() -> Dict[str, Any]:
    snap = get_current_snapshot()
    if not snap:
        return {}
    raw = snap.get("sentiment", {})
    return {
        "vol_ratio": raw.get("pc_volume", 0.0),
        "oi_ratio": raw.get("pc_oi", 0.0),
        "iv_skew": raw.get("iv_skew", 0.0),
        "call_volume": raw.get("call_volume", 0),
        "put_volume": raw.get("put_volume", 0),
        "call_oi": raw.get("call_oi", 0),
        "put_oi": raw.get("put_oi", 0),
    }

def get_historical(days: int = 20) -> List[Dict]:
    snap = get_current_snapshot()
    if not snap:
        return []
    hist = snap.get("historical", [])
    return hist[-days:] if len(hist) > days else hist

def get_macro_events(limit: int = 5) -> List[Dict]:
    snap = get_current_snapshot()
    if not snap:
        return []
    return snap.get("macro", [])[:limit]

def get_earnings(limit: int = 5) -> List[Dict]:
    snap = get_current_snapshot()
    if not snap:
        return []
    return snap.get("earnings", [])[:limit]

def get_analyst() -> Dict[str, Any]:
    snap = get_current_snapshot()
    if not snap:
        return {}
    return snap.get("analyst", {})

def get_formatted_block() -> str:
    """格式化报告块 — 读DB，不触发脉冲"""
    from anchoring.snapshot_formatter import SnapshotFormatter
    from anchoring.db_manager import DBManager
    db_path = _ensure_db_dir()
    if not db_path.exists():
        return "[ONE Bot 3.0] Status: INITIALIZING\n[ONE Bot 3.0-END]"
    db = DBManager(str(db_path))
    snap = db.get_latest_snapshot()
    if not snap:
        return "[ONE Bot 3.0] Status: NO DATA\n[ONE Bot 3.0-END]"
    fmt = SnapshotFormatter()
    return fmt.format(snap)

def get_db_path() -> str:
    return str(_DB_PATH)

# L2 查询接口
def get_kronos_prediction() -> Dict[str, Any]:
    """从 anchoring 数据运行 Kronos 预测"""
    from kronos.engine import predict_from_anchoring
    snap = get_current_snapshot()
    return predict_from_anchoring(snap)

def get_kronos_engine():
    from kronos.engine import get_engine
    return get_engine()

# L3 查询接口
def get_distilled_daily(date: str | None = None) -> Dict[str, Any]:
    from distiller.engine import get_daily_summary
    return get_daily_summary(date)

def get_distilled_trend(days: int = 5) -> str:
    from distiller.engine import format_trend
    return format_trend(days)

def get_distilled_latest_gex(limit: int = 5) -> List[Dict[str, Any]]:
    from distiller.engine import get_latest_gex
    return get_latest_gex(limit)

def get_distiller_block(date: str | None = None) -> str:
    from distiller.engine import format_daily_block
    return format_daily_block(date)

# ── 调度器自启动 ──
threading.Thread(
    target=lambda: __import__('onebot3.lib.scheduler', fromlist=['start_all']).start_all(),
    daemon=True,
    name="onebot-autostart",
).start()
logger.info(f"[ONE Bot 3.0] Scheduler auto-start triggered")
