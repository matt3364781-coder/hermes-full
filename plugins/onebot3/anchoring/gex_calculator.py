#!/usr/bin/env python3
"""
gex_calculator.py — GEX & Sentiment computation
"""

import logging
from typing import Dict, Any, Optional
import numpy as np
import pandas as pd

logger = logging.getLogger("onebot3.gex")

class GEXCalculator:
    MULTIPLIER = 100

    def compute(self, chain_df: pd.DataFrame, spot: float) -> Dict[str, Any]:
        if chain_df.empty or spot <= 0:
            return {"regime": "neutral"}

        req = {"strike", "option_type", "open_interest", "greeks.gamma"}
        if not req.issubset(chain_df.columns):
            missing = req - set(chain_df.columns)
            logger.warning("GEX missing columns: %s", missing)
            return {"regime": "neutral"}

        chain_df = chain_df.copy()
        chain_df["gex"] = (
            chain_df["greeks.gamma"].fillna(0)
            * chain_df["open_interest"].fillna(0)
            * self.MULTIPLIER * spot
        )
        chain_df["signed_gex"] = chain_df.apply(
            lambda r: r["gex"] if r["option_type"] == "call" else -r["gex"], axis=1
        )

        pivot = chain_df.groupby("strike").apply(
            lambda g: pd.Series({
                "call_gex": g[g["option_type"] == "call"]["gex"].sum(),
                "put_gex": g[g["option_type"] == "put"]["gex"].sum(),
                "net_gex": g["signed_gex"].sum(),
                "call_oi": g[g["option_type"] == "call"]["open_interest"].sum(),
                "put_oi": g[g["option_type"] == "put"]["open_interest"].sum(),
            })
        ).reset_index()

        if pivot.empty:
            return {"regime": "neutral"}

        call_wall = float(pivot.loc[pivot["call_gex"].idxmax(), "strike"]) if pivot["call_gex"].sum() > 0 else spot
        put_wall = float(pivot.loc[pivot["put_gex"].idxmax(), "strike"]) if pivot["put_gex"].sum() > 0 else spot
        net_gex = float(pivot["net_gex"].sum())
        zero_gamma = self._find_zero_crossing(pivot["strike"].values, pivot["net_gex"].values)
        max_pain = self._calc_max_pain(chain_df)
        regime = self._classify_regime(net_gex, spot, zero_gamma)

        pivot["abs_net"] = pivot["net_gex"].abs()
        top = pivot.nlargest(20, "abs_net")[["strike", "call_gex", "put_gex", "net_gex"]]
        strike_detail = [
            {"strike": float(r["strike"]), "call_gex": float(r["call_gex"]),
             "put_gex": float(r["put_gex"]), "net_gex": float(r["net_gex"])}
            for _, r in top.iterrows()
        ]

        return {
            "net_gex": net_gex, "call_wall": call_wall, "put_wall": put_wall,
            "zero_gamma": zero_gamma, "max_pain": max_pain, "regime": regime,
            "strike_detail": strike_detail,
        }

    @staticmethod
    def _find_zero_crossing(strikes: np.ndarray, net_gex: np.ndarray) -> Optional[float]:
        for i in range(len(net_gex) - 1):
            if net_gex[i] == 0:
                return float(strikes[i])
            if net_gex[i] * net_gex[i + 1] < 0:
                x1, x2 = strikes[i], strikes[i + 1]
                y1, y2 = net_gex[i], net_gex[i + 1]
                return float(x1 - y1 * (x2 - x1) / (y2 - y1))
        return None

    @staticmethod
    def _calc_max_pain(df: pd.DataFrame) -> Optional[float]:
        if df.empty or "strike" not in df.columns:
            return None
        # 向量化: O(n) 替代 O(n²)
        pivot = df.groupby(["strike", "option_type"])["open_interest"].sum().unstack(fill_value=0)
        strikes = np.sort(pivot.index.values)
        call_oi = pivot.get("call", pd.Series(0, index=pivot.index)).values
        put_oi = pivot.get("put", pd.Series(0, index=pivot.index)).values
        call_oi = np.nan_to_num(call_oi, 0.0)
        put_oi = np.nan_to_num(put_oi, 0.0)

        # call_pain = S * cumsum_call_oi - cumsum(strike * call_oi)
        cum_call_oi = np.cumsum(call_oi)
        cum_call_w = np.cumsum(strikes * call_oi)
        call_pain = strikes * cum_call_oi - cum_call_w

        # put_pain = cumsum(strike * put_oi)_from_right - S * cumsum_put_oi_from_right
        total_poi = np.sum(put_oi)
        total_pw = np.sum(strikes * put_oi)
        cum_put_oi_r = total_poi - np.cumsum(put_oi) + put_oi  # OI for >= current
        cum_put_w_r = total_pw - np.cumsum(strikes * put_oi) + strikes * put_oi
        put_pain = cum_put_w_r - strikes * cum_put_oi_r

        total_pain = call_pain + put_pain
        return float(strikes[np.argmin(total_pain)])

    @staticmethod
    def _classify_regime(net_gex: float, spot: float, zero_gamma: Optional[float]) -> str:
        if zero_gamma is None:
            return "neutral"
        if abs(net_gex) < 1e8:
            return "neutral"
        return "positive" if net_gex > 0 else "negative"

class SentimentAnalyzer:
    def compute(self, chain_df: pd.DataFrame) -> Dict[str, Any]:
        if chain_df.empty:
            return {}

        call_vol = chain_df[chain_df["option_type"] == "call"]["volume"].sum()
        put_vol = chain_df[chain_df["option_type"] == "put"]["volume"].sum()
        pc_vol = (put_vol / call_vol) if call_vol else 0.0

        call_oi = chain_df[chain_df["option_type"] == "call"]["open_interest"].sum()
        put_oi = chain_df[chain_df["option_type"] == "put"]["open_interest"].sum()
        pc_oi = (put_oi / call_oi) if call_oi else 0.0

        iv_skew = 0.0
        if "greeks.mid_iv" in chain_df.columns:
            strikes = chain_df["strike"].unique()
            if len(strikes) > 0:
                atm = chain_df["strike"].median()
                atm_df = chain_df[chain_df["strike"] == atm]
                put_iv = atm_df[atm_df["option_type"] == "put"]["greeks.mid_iv"].mean()
                call_iv = atm_df[atm_df["option_type"] == "call"]["greeks.mid_iv"].mean()
                iv_skew = (put_iv - call_iv) if pd.notna(put_iv) and pd.notna(call_iv) else 0.0

        return {
            "pc_volume": float(pc_vol), "pc_oi": float(pc_oi), "iv_skew": float(iv_skew),
            "call_volume": int(call_vol), "put_volume": int(put_vol),
            "call_oi": int(call_oi), "put_oi": int(put_oi),
        }
