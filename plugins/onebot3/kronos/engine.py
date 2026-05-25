#!/usr/bin/env python3
"""
kronos/engine.py — KronosEngine: Kronos-base + 训练好的区间分类头

每个引擎共享模型权重 + 分类器，但独立后处理参数。
输出: 区间标签 0-4 + 置信度
"""

import os
import sys
import pickle
import logging
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd
import torch
from huggingface_hub import snapshot_download

logger = logging.getLogger("onebot3.kronos.engine")

# ── 路径 ──
MODEL_ID = "NeoQuasar/Kronos-base"
TOKENIZER_ID = "NeoQuasar/Kronos-Tokenizer-base"
ZONE_CLASSIFIER_PATH = Path(__file__).parent / "models" / "zone_classifier.pkl"

# ── 共享单例（模型 + 分类器） ──
_shared_model = None
_shared_tokenizer = None
_shared_classifier = None
_shared_device = None

LABEL_NAMES = {0: "支撑区", 1: "中性区", 2: "阻力区", 3: "A+1突破", 4: "A-1突破"}

# ── 方向判定常量 ──
DECODER_DIRECTION_LABELS = {1: "CALL", -1: "PUT", 0: "NEUTRAL"}


def _get_device():
    global _shared_device
    if _shared_device is None:
        _shared_device = "cuda:0" if torch.cuda.is_available() else "cpu"
        logger.info(f"Using {_shared_device}")
    return _shared_device


# ── 归一化 ──

def _normalize_klines(arr, clip=5.0):
    mean = np.mean(arr, axis=0)
    std = np.where(np.std(arr, axis=0) < 1e-8, 1e-8, np.std(arr, axis=0))
    return np.clip((arr - mean) / std, -clip, clip), mean, std


def _build_time_stamp(timestamps, device):
    ts = pd.DatetimeIndex(pd.to_datetime(timestamps))
    df = pd.DataFrame({
        'minute': ts.minute, 'hour': ts.hour, 'weekday': ts.weekday,
        'day': ts.day, 'month': ts.month,
    })
    return torch.from_numpy(df.values.astype(np.float32)).unsqueeze(0).to(device)


# ── Zone → 方向映射（为 perma-bull 设计） ──

ZONE_TO_DIRECTION = {0: 1, 1: 0, 2: -1, 3: 1, 4: -1}
ZONE_TO_CONFIDENCE = {0: 0.70, 1: 0.30, 2: 0.60, 3: 0.85, 4: 0.80}
ZONE_TO_LABEL = {0: "CALL", 1: "NEUTRAL", 2: "PUT", 3: "CALL", 4: "PUT"}


# ── 百分位区间标签（回滚版） ──

def detect_range(df_close, df_high, df_low, window: int = 100):
    """
    百分位区间标签 —— 3-class

    0=支撑区 (close <= P5 of rolling window)
    1=中性区
    2=阻力区 (close >= P95 of rolling window)
    """
    import pandas as pd
    import numpy as np

    if isinstance(df_close, pd.Series):
        close = df_close
    else:
        close = pd.Series(df_close)

    low_q = close.rolling(window=window, min_periods=1).quantile(0.05)
    high_q = close.rolling(window=window, min_periods=1).quantile(0.95)

    labels = pd.Series(1, index=close.index, dtype=int)
    labels[close <= low_q] = 0
    labels[close >= high_q] = 2
    return labels.values


# ── KronosEngine ──

class KronosEngine:
    """Kronos 引擎 — 共享模型 + 分类头，独立后处理参数"""

    _shared_model = None
    _shared_tokenizer = None
    _shared_classifier = None
    _shared_predictor = None
    _device = None

    def __init__(self, config: dict):
        self.name = config.get("name", "unknown")
        self.lookback = config.get("lookback", 60)
        self.threshold = config.get("threshold", 0.01)
        self.ema_period = config.get("ema_period", 0)
        self.vol_weight = config.get("vol_weight", 0.3)
        self.pattern_only = config.get("pattern_only", False)
        self.ignore_volume = config.get("ignore_volume", False)
        self.vol_regime = config.get("vol_regime", False)
        self.clip = config.get("clip", 5.0)

        self._ema_signal = None
        self._last_prediction = None
        KronosEngine._load_once()
        self._log(f"init — lookback={self.lookback}")

    @classmethod
    def _load_once(cls):
        if cls._shared_model is not None:
            return
        cls._device = _get_device()
        kronos_dir = str(Path(__file__).parent)
        if kronos_dir not in sys.path:
            sys.path.insert(0, kronos_dir)
        from model.kronos import Kronos, KronosTokenizer, KronosPredictor

        logger.info("[KronosEngine] Loading Kronos-base from HF cache...")
        try:
            cls._shared_tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_ID, local_files_only=True)
            cls._shared_model = Kronos.from_pretrained(MODEL_ID, local_files_only=True)
        except Exception as e:
            logger.warning(f"local fallback: {e}")
            snapshot_download(TOKENIZER_ID)
            snapshot_download(MODEL_ID)
            cls._shared_tokenizer = KronosTokenizer.from_pretrained(TOKENIZER_ID)
            cls._shared_model = Kronos.from_pretrained(MODEL_ID)

        cls._shared_tokenizer = cls._shared_tokenizer.to(cls._device)
        cls._shared_model = cls._shared_model.to(cls._device)
        cls._shared_model.eval()

        # KronosPredictor（凍結推理，不訓練）
        cls._shared_predictor = KronosPredictor(
            cls._shared_model, cls._shared_tokenizer, cls._device
        )

        # 加载区间分类器
        if ZONE_CLASSIFIER_PATH.exists():
            with open(ZONE_CLASSIFIER_PATH, "rb") as f:
                data = pickle.load(f)
            cls._shared_classifier = data["model"]
            logger.info(f"Zone classifier loaded: test_acc={data['test_accuracy']:.3f}")
        else:
            logger.warning("No zone_classifier.pkl found — will use fallback")
            cls._shared_classifier = None

        logger.info(f"[KronosEngine] Ready, device={cls._device}")

    def _log(self, msg):
        logger.debug(f"[{self.name}] {msg}")

    def _get_hidden_state(self, normed, stamps):
        """对归一化后的 klines 跑 Kronos → 返回 832-dim hidden state"""
        x_t = torch.from_numpy(normed).unsqueeze(0).to(KronosEngine._device)
        with torch.no_grad():
            tokens = KronosEngine._shared_tokenizer.encode(x_t, half=True)
            _, context = KronosEngine._shared_model.decode_s1(tokens[0], tokens[1], stamps)
            return context[0, -1, :].cpu().numpy()

    def _classify_zone(self, hidden_state: np.ndarray) -> tuple:
        """
        用训练好的分类头预测区间。

        返回: (zone, prob_vector)
        """
        clf = KronosEngine._shared_classifier
        if clf is None:
            return 1, np.zeros(5)  # fallback 中性

        probs = clf.predict_proba(hidden_state.reshape(1, -1))[0]
        zone = int(np.argmax(probs))
        return zone, probs

    def predict(self, klines: list[dict]) -> dict[str, Any]:
        if not klines:
            return self._fallback("no_data")

        window = klines[-self.lookback:] if len(klines) > self.lookback else klines
        n = len(window)
        if n < 10:
            return self._fallback(f"too_few:{n}")

        # 提取 numpy
        arr = np.zeros((n, 6), dtype=np.float32)
        for i, k in enumerate(window):
            arr[i, 0] = k.get("open", 0.0)
            arr[i, 1] = k.get("high", 0.0)
            arr[i, 2] = k.get("low", 0.0)
            arr[i, 3] = k.get("close", 0.0)
            arr[i, 4] = k.get("volume", 0.0) if not self.ignore_volume else 0.0
            arr[i, 5] = k.get("amount", 0.0) if not self.ignore_volume else 0.0

        # 归一化 + 时间戳
        normed, _, _ = _normalize_klines(arr, self.clip)
        ts_list = [k.get("date", "") or str(pd.Timestamp.now()) for k in window]
        stamp = _build_time_stamp(ts_list, KronosEngine._device)

        # Kronos forward → hidden state → 分类
        hidden = self._get_hidden_state(normed, stamp)
        zone, probs = self._classify_zone(hidden)

        # Zone → 方向
        direction = ZONE_TO_DIRECTION.get(zone, 0)
        confidence = float(probs[zone]) * ZONE_TO_CONFIDENCE.get(zone, 0.5)
        label = ZONE_TO_LABEL.get(zone, "NEUTRAL")

        # EMA 平滑（基于连续的 zone score）
        zone_score = {0: 0.8, 1: 0.0, 2: -0.6, 3: 1.0, 4: -1.0}.get(zone, 0.0)
        if self.ema_period > 0:
            alpha = 2.0 / (self.ema_period + 1)
            if self._ema_signal is None:
                self._ema_signal = zone_score
            else:
                self._ema_signal = alpha * zone_score + (1 - alpha) * self._ema_signal

            threshold = self._get_threshold(arr[:, 3])
            if abs(self._ema_signal) < threshold:
                direction = 0
                label = "NEUTRAL"
                confidence = 0.0

        result = {
            "symbol": "SPY",
            "direction": direction,
            "direction_label": label,
            "confidence": round(float(confidence), 3),
            "engine_name": self.name,
            "zone": zone,
            "zone_label": LABEL_NAMES.get(zone, "?"),
            "zone_probs": {str(k): round(float(v), 3) for k, v in enumerate(probs)},
            "lookback": n,
        }

        self._last_prediction = result
        return result

    def _get_threshold(self, closes):
        if isinstance(self.threshold, (int, float)):
            return float(self.threshold)
        if self.threshold == "adaptive" and self.vol_regime and len(closes) > 5:
            returns = np.diff(closes) / (closes[:-1] + 1e-8)
            vol = np.std(returns[-20:]) if len(returns) > 20 else np.std(returns)
            return min(max(vol * 3.0, 0.003), 0.05)
        return 0.01

    def _fallback(self, reason: str) -> dict:
        return {
            "symbol": "SPY", "direction": 0, "direction_label": "NEUTRAL",
            "confidence": 0.0, "engine_name": self.name, "zone": 1,
            "zone_label": "中性区", "lookback": 0, "reason": reason,
        }

    def reset_state(self):
        self._ema_signal = None
        self._last_prediction = None


# ── 快捷接口 ──

def predict_from_anchoring(snap: dict | None) -> dict:
    if not snap:
        return {"status": "no_data", "path_type": "mean_reversion", "confidence": 0.0}
    hist = snap.get("historical", [])
    if len(hist) < 10:
        return {"status": f"insufficient:{len(hist)}", "path_type": "mean_reversion", "confidence": 0.0}

    from kronos.cluster import KronosCluster
    cluster = KronosCluster()
    result = cluster.predict(hist)

    # ── GEX 二次确认 ──
    gex = snap.get("gex", {})
    gex_net = gex.get("net_gex", 0) or 0
    gex_regime = gex.get("regime", "?")
    gex_confirm = 0  # -1=看空, 0=中性, 1=看多
    if gex_net > 0:
        gex_confirm = 1   # 正GEX → 支撑 → 看多
    elif gex_net < 0:
        gex_confirm = -1  # 负GEX → 阻力 → 看空

    dir_kronos = result.get("direction", 0)
    conf = result.get("confidence", 0.0)
    gex_aligned = (dir_kronos == gex_confirm and dir_kronos != 0)

    # 如果 GEX 与大方向一致 → 升置信度
    if gex_aligned:
        conf = min(conf + 0.15, 0.95)

    return {
        "status": "ok",
        "path_type": result.get("direction_label", "NEUTRAL"),
        "direction": dir_kronos,
        "confidence": round(conf, 3),
        "agreement": result.get("agreement", 0),
        "model_source": "KronosCluster-v1.0",
        "zone": result.get("zone", 1),
        "price_count": len(hist),
        "details": result.get("details", {}),
        "weights": result.get("weights", {}),
        # ── GEX 二次确认 ──
        "gex_net": round(gex_net, 0),
        "gex_regime": gex_regime,
        "gex_confirm": gex_confirm,
        "gex_aligned": gex_aligned,
    }
