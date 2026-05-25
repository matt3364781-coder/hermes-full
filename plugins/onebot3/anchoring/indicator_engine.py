#!/usr/bin/env python3
"""
indicator_engine.py — 15 Technical Indicators + Fusion Signal

Indicators:
  Trend: MA_5, MA_10, MA_20, MA_50, EMA_12, EMA_26, MACD, MACD_Signal, MACD_Hist
  Volatility: ATR_14, BB_Upper, BB_Lower, BB_Width, BB_Position
  Momentum: RSI_14
  Volume: VWAP, Vol_MA_20

Fusion: weighted voting → signal + confidence + divergence
"""

import logging
from typing import Dict, Any
import numpy as np
import pandas as pd

logger = logging.getLogger("onebot3.indicators")

class IndicatorEngine:
    def compute_all(self, df: pd.DataFrame) -> Dict[str, Any]:
        if len(df) < 50:
            return {}

        close = df["close"].values
        high = df["high"].values
        low = df["low"].values
        volume = df["volume"].values

        result = {}

        # Trend
        result["MA_5"] = float(self._sma(close, 5)[-1])
        result["MA_10"] = float(self._sma(close, 10)[-1])
        result["MA_20"] = float(self._sma(close, 20)[-1])
        result["MA_50"] = float(self._sma(close, 50)[-1])
        result["EMA_12"] = float(self._ema(close, 12)[-1])
        result["EMA_26"] = float(self._ema(close, 26)[-1])

        ema12 = self._ema(close, 12)
        ema26 = self._ema(close, 26)
        macd_line = ema12 - ema26
        macd_signal = self._ema(macd_line, 9)
        macd_hist = macd_line - macd_signal
        result["MACD"] = float(macd_line[-1])
        result["MACD_Signal"] = float(macd_signal[-1])
        result["MACD_Hist"] = float(macd_hist[-1])

        # Volatility
        result["ATR_14"] = float(self._atr(high, low, close, 14)[-1])
        bb_upper, bb_lower, bb_width, bb_pos = self._bollinger(close, 20, 2)
        result["BB_Upper"] = float(bb_upper[-1])
        result["BB_Lower"] = float(bb_lower[-1])
        result["BB_Width"] = float(bb_width[-1])
        result["BB_Position"] = float(bb_pos[-1])

        # Momentum
        result["RSI_14"] = float(self._rsi(close, 14)[-1])

        # Volume
        result["VWAP"] = float(self._vwap(df)[-1])
        result["Vol_MA_20"] = float(self._sma(volume.astype(float), 20)[-1])

        return result

    def fusion_signal(self, indicators: Dict[str, float]) -> Dict[str, Any]:
        if not indicators:
            return {"signal": "NEUTRAL", "confidence": 0.0, "divergence": 0.0}

        votes = {"bull": 0, "bear": 0, "neutral": 0}
        weights = []
        signals = []

        # MA trend
        if indicators.get("MA_5", 0) > indicators.get("MA_20", 0):
            votes["bull"] += 1; weights.append(1.0); signals.append(1)
        else:
            votes["bear"] += 1; weights.append(1.0); signals.append(-1)

        # EMA trend
        if indicators.get("EMA_12", 0) > indicators.get("EMA_26", 0):
            votes["bull"] += 1; weights.append(1.0); signals.append(1)
        else:
            votes["bear"] += 1; weights.append(1.0); signals.append(-1)

        # MACD
        if indicators.get("MACD_Hist", 0) > 0:
            votes["bull"] += 1; weights.append(1.2); signals.append(1)
        else:
            votes["bear"] += 1; weights.append(1.2); signals.append(-1)

        # RSI
        rsi = indicators.get("RSI_14", 50)
        if rsi > 70:
            votes["bear"] += 1; weights.append(1.5); signals.append(-1)
        elif rsi < 30:
            votes["bull"] += 1; weights.append(1.5); signals.append(1)
        else:
            votes["neutral"] += 1; weights.append(0.5); signals.append(0)

        # BB Position
        bb_pos = indicators.get("BB_Position", 0.5)
        if bb_pos > 0.95:
            votes["bear"] += 1; weights.append(1.0); signals.append(-1)
        elif bb_pos < 0.05:
            votes["bull"] += 1; weights.append(1.0); signals.append(1)
        else:
            votes["neutral"] += 1; weights.append(0.5); signals.append(0)

        # VWAP
        vwap = indicators.get("VWAP", 0)
        price_now = indicators.get("MA_5", vwap)
        if price_now > vwap * 1.001:
            votes["bull"] += 1; weights.append(0.8); signals.append(1)
        elif price_now < vwap * 0.999:
            votes["bear"] += 1; weights.append(0.8); signals.append(-1)
        else:
            votes["neutral"] += 1; weights.append(0.3); signals.append(0)

        weighted_sum = sum(s * w for s, w in zip(signals, weights))
        total_weight = sum(weights)
        score = weighted_sum / total_weight if total_weight else 0
        confidence = min(abs(score) * 100, 1.0)

        total_votes = votes["bull"] + votes["bear"] + votes["neutral"]
        divergence = 1.0 - (abs(votes["bull"] - votes["bear"]) / total_votes) if total_votes else 0.0

        if score > 0.2:
            signal = "BULLISH"
        elif score < -0.2:
            signal = "BEARISH"
        else:
            signal = "NEUTRAL"
            confidence = confidence * 0.5

        return {
            "signal": signal,
            "confidence": round(confidence, 3),
            "divergence": round(divergence, 3),
            "score": round(score, 4),
            "votes": votes,
        }

    @staticmethod
    def _sma(arr: np.ndarray, period: int) -> np.ndarray:
        return pd.Series(arr).rolling(window=period, min_periods=1).mean().values

    @staticmethod
    def _ema(arr: np.ndarray, period: int) -> np.ndarray:
        return pd.Series(arr).ewm(span=period, adjust=False, min_periods=1).mean().values

    @staticmethod
    def _atr(high: np.ndarray, low: np.ndarray, close: np.ndarray, period: int) -> np.ndarray:
        tr1 = high[1:] - low[1:]
        tr2 = np.abs(high[1:] - close[:-1])
        tr3 = np.abs(low[1:] - close[:-1])
        tr = np.vstack([tr1, tr2, tr3]).max(axis=0)
        tr = np.concatenate([[high[0] - low[0]], tr])
        return pd.Series(tr).ewm(span=period, adjust=False, min_periods=1).mean().values

    @staticmethod
    def _bollinger(close: np.ndarray, period: int, std_dev: float):
        sma = pd.Series(close).rolling(window=period, min_periods=1).mean().values
        std = pd.Series(close).rolling(window=period, min_periods=1).std().values
        upper = sma + std_dev * std
        lower = sma - std_dev * std
        width = (upper - lower) / sma
        pos = (close - lower) / (upper - lower + 1e-10)
        return upper, lower, width, pos

    @staticmethod
    def _rsi(close: np.ndarray, period: int) -> np.ndarray:
        delta = np.diff(close, prepend=close[0])
        gain = np.where(delta > 0, delta, 0)
        loss = np.where(delta < 0, -delta, 0)
        avg_gain = pd.Series(gain).ewm(alpha=1/period, adjust=False, min_periods=1).mean().values
        avg_loss = pd.Series(loss).ewm(alpha=1/period, adjust=False, min_periods=1).mean().values
        rs = avg_gain / (avg_loss + 1e-10)
        return 100 - (100 / (1 + rs))

    @staticmethod
    def _vwap(df: pd.DataFrame) -> np.ndarray:
        typical = (df["high"] + df["low"] + df["close"]) / 3
        cum_vol = df["volume"].cumsum()
        cum_tp_vol = (typical * df["volume"]).cumsum()
        return (cum_tp_vol / cum_vol).values
