#!/usr/bin/env python3
"""
kronos/cluster.py — KronosCluster v1.0

5 个独立 KronosEngine 实例，各自不同配置：
- scalper:   超短周期，早入场，假信号多
- swing:     波段趋势
- trend:     日线级趋势，迟入场
- vol:       波动率自适应
- pattern:   纯 K 线形态，忽视成交量

融合：动态权重 + 分歧检测
"""

import logging
from collections import deque, Counter
from typing import Any

import numpy as np

from kronos.engine import KronosEngine

logger = logging.getLogger("onebot3.kronos.cluster")


# ── 5 个实例的独立配置 ──

INSTANCE_CONFIGS = {
    "scalper": {
        "name": "scalper",
        "lookback": 10,
        "threshold": 0.005,   # 敏感阈值，早入场
        "ema_period": 5,      # 快 EMA
        "vol_weight": 0.0,    # 不看成交量
        "ignore_volume": True,
        "pattern_only": False,
        "vol_regime": False,
        "clip": 5.0,
    },
    "swing": {
        "name": "swing",
        "lookback": 40,
        "threshold": 0.015,
        "ema_period": 20,
        "vol_weight": 0.3,
        "ignore_volume": False,
        "pattern_only": False,
        "vol_regime": False,
        "clip": 5.0,
    },
    "trend": {
        "name": "trend",
        "lookback": 120,
        "threshold": 0.03,    # 迟钝阈值，晚入场
        "ema_period": 50,     # 长周期 EMA
        "vol_weight": 0.5,    # 成交量必须确认
        "ignore_volume": False,
        "pattern_only": False,
        "vol_regime": False,
        "clip": 5.0,
    },
    "vol": {
        "name": "vol",
        "lookback": 60,
        "threshold": "adaptive",  # 自适应：高波时提高阈值
        "ema_period": 20,
        "vol_weight": 0.4,
        "ignore_volume": False,
        "pattern_only": False,
        "vol_regime": True,       # 启用波动率自适应
        "clip": 5.0,
    },
    "pattern": {
        "name": "pattern",
        "lookback": 20,
        "threshold": 0.01,
        "ema_period": 0,       # 无 EMA 平滑
        "vol_weight": 0.0,
        "ignore_volume": True, # 忽略成交量
        "pattern_only": True,  # 只看 K 线形态
        "vol_regime": False,
        "clip": 5.0,
    },
}

# ── 基础权重（市场未知时的默认值） ──

BASE_WEIGHTS = {
    "scalper": 0.15,
    "swing":   0.25,
    "trend":   0.25,
    "vol":     0.15,
    "pattern": 0.20,
}


class KronosCluster:
    """
    KronosCluster v1.0 — N 个独立 KronosEngine 实例的异构集群。

    每个实例有完全独立的配置（lookback/threshold/EMA/etc.），
    但共享同一份模型权重（内存优化）。

    用法:
        cluster = KronosCluster()
        result = cluster.predict(klines)
        # result = {direction, confidence, details: {...每个实例的原始输出...}}
    """

    def __init__(self):
        self.instances: dict[str, KronosEngine] = {}
        for name, cfg in INSTANCE_CONFIGS.items():
            self.instances[name] = KronosEngine(cfg)

        # 准确率跟踪（滚动窗口 100 次）
        self.accuracy_window: dict[str, deque] = {
            name: deque(maxlen=100) for name in INSTANCE_CONFIGS
        }

        logger.info(f"KronosCluster initialized: {list(self.instances.keys())}")

    # ── 主预测接口 ──

    def predict(self, klines: list[dict], market_regime: str = "unknown") -> dict[str, Any]:
        """
        对所有实例并行推理，融合输出。

        klines: list of {open, high, low, close, volume, date}
        market_regime: "trending" | "ranging" | "high_vol" | "unknown"

        返回:
        {
            "direction": 1 | 0 | -1,
            "direction_label": "CALL" | "NEUTRAL" | "PUT",
            "confidence": float (0~1),
            "agreement": int (1=全一致, 2=轻度分歧, 3=严重分歧),
            "size": float (0~1, 仓位建议),
            "weighted_sum": float,
            "alert": str | None,
            "details": {每个实例的原始 dict},
            "weights": {每个实例的权重},
        }
        """
        if not klines or len(klines) < 5:
            return {
                "direction": 0,
                "direction_label": "NEUTRAL",
                "confidence": 0.0,
                "agreement": 3,
                "size": 0.0,
                "weighted_sum": 0.0,
                "alert": "insufficient_data",
                "details": {},
                "weights": {},
            }

        # 1. 每个实例独立推理
        signals = {}
        for name, engine in self.instances.items():
            try:
                raw = engine.predict(klines)
                signals[name] = raw
            except Exception as e:
                logger.error(f"[{name}] predict error: {e}")
                signals[name] = {
                    "direction": 0,
                    "direction_label": "NEUTRAL",
                    "confidence": 0.0,
                    "engine_name": name,
                    "reason": f"error: {e}",
                }

        # 2. 计算动态权重
        weights = self._get_weights(market_regime)

        # 3. 融合
        fused = self._fuse(signals, weights)

        return fused

    # ── 动态权重 ──

    def _get_weights(self, market_regime: str) -> dict[str, float]:
        """根据市场状态计算动态权重"""
        w = dict(BASE_WEIGHTS)  # 拷贝基础权重

        # 状态调整
        if market_regime == "trending":
            w["trend"] += 0.15
            w["scalper"] -= 0.10
        elif market_regime == "ranging":
            w["scalper"] += 0.15
            w["trend"] -= 0.10
        elif market_regime == "high_vol":
            w["vol"] += 0.20
            w["scalper"] += 0.05

        # 准确率惩罚：近期准确率低于 0.4 的实例降权
        for name in w:
            acc = self._get_recent_accuracy(name)
            if acc is not None and acc < 0.4:
                w[name] *= 0.5

        # 确保无负权重 + 归一化
        for name in w:
            w[name] = max(w[name], 0.01)
        total = sum(w.values())
        for name in w:
            w[name] /= total

        return w

    def _get_recent_accuracy(self, name: str) -> float | None:
        """取某实例近期的滚动准确率"""
        dq = self.accuracy_window.get(name)
        if not dq or len(dq) < 10:
            return None
        return sum(dq) / len(dq)

    # ── 融合逻辑（分歧检测是灵魂） ──

    def _fuse(self, signals: dict[str, dict], weights: dict[str, float]) -> dict[str, Any]:
        """
        融合各实例的输出。

        核心策略:
        - 完全一致（分歧度=1）→ 高置信执行（confidence=0.9, size=1.0）
        - 轻度分歧（分歧度=2 且 |sum|>0.3）→ 中等置信（confidence=0.6, size=0.5）
        - 严重分歧（分歧度=3）→ 空仓（confidence=0.0, size=0.0）
        """
        # 提取各实例的方向 (-1, 0, 1)
        dirs = {}
        for name, sig in signals.items():
            d = sig.get("direction", 0)
            if d is None:
                d = 0
            dirs[name] = d

        # 加权求和
        weighted_sum = sum(dirs.get(name, 0) * weights.get(name, 0) for name in self.instances)

        # 分歧度：不同方向值的数量
        unique_dirs = set(v for v in dirs.values() if v != 0)
        non_zero_count = sum(1 for v in dirs.values() if v != 0)
        if non_zero_count == 0:
            agreement = 3  # 全中性也算严重分歧
        elif len(unique_dirs) == 1:
            agreement = 1  # 完全一致
        elif len(unique_dirs) == 2:
            agreement = 2  # 轻度分歧
        else:
            agreement = 3  # 3 种方向都出现 = 严重分歧

        # 共识度
        abs_sum = abs(weighted_sum)

        # 最终信号
        if agreement == 1:
            # 完全一致
            final_dir = 1 if weighted_sum > 0 else (-1 if weighted_sum < 0 else 0)
            confidence = 0.9
            size = 1.0
            alert = None
        elif agreement == 2 and abs_sum > 0.3:
            # 轻度分歧但方向明确
            final_dir = 1 if weighted_sum > 0 else (-1 if weighted_sum < 0 else 0)
            confidence = 0.6
            size = 0.5
            alert = None
        else:
            # 严重分歧 → 空仓
            final_dir = 0
            confidence = 0.0
            size = 0.0
            alert = "high_divergence"

        # 降权：如果置信度高的实例（vol, trend）一致，可提升最终置信度
        high_weight_agreement = (
            dirs.get("trend", 0) == final_dir
            and dirs.get("vol", 0) == final_dir
            and final_dir != 0
        )
        if high_weight_agreement:
            confidence = min(confidence + 0.15, 1.0)

        return {
            "direction": final_dir,
            "direction_label": "CALL" if final_dir > 0 else ("PUT" if final_dir < 0 else "NEUTRAL"),
            "confidence": round(float(confidence), 3),
            "agreement": agreement,
            "size": round(float(size), 3),
            "weighted_sum": round(float(weighted_sum), 4),
            "alert": alert,
            "zone": final_dir_to_zone(final_dir),
            "details": {
                name: {
                    "direction": sig.get("direction", 0),
                    "direction_label": sig.get("direction_label", "NEUTRAL"),
                    "confidence": sig.get("confidence", 0.0),
                    "zone": sig.get("zone", 1),
                    "zone_label": sig.get("zone_label", "?"),
                    "engine_name": sig.get("engine_name", name),
                }
                for name, sig in signals.items()
            },
            "weights": {name: round(float(w), 4) for name, w in weights.items()},
        }

    # ── 准确率反馈（外部调用，用于在线学习） ──

    def feedback(self, name: str, correct: bool):
        """
        反馈某实例预测是否正确，用于滚动准确率跟踪。

        用法:
            cluster.feedback("scalper", True)   # scalper 猜对了
            cluster.feedback("swing", False)     # swing 猜错了
        """
        if name in self.accuracy_window:
            self.accuracy_window[name].append(1 if correct else 0)

    # ── 重置内部状态 ──

    def reset_all(self):
        """重置所有实例的内部状态（EMA 缓存）"""
        for engine in self.instances.values():
            engine.reset_state()
        for dq in self.accuracy_window.values():
            dq.clear()
        logger.info("KronosCluster: all states reset")


# ── 工具函数 ──

def final_dir_to_zone(direction: int) -> int:
    """集群最终方向 → 区间标签"""
    return {1: 0, 0: 1, -1: 2}.get(direction, 1)


# ── 模块级单例 ──

_cluster: KronosCluster | None = None


def get_cluster() -> KronosCluster:
    global _cluster
    if _cluster is None:
        _cluster = KronosCluster()
    return _cluster


def predict(klines: list[dict], market_regime: str = "unknown") -> dict[str, Any]:
    return get_cluster().predict(klines, market_regime)
