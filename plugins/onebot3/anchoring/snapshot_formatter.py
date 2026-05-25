#!/usr/bin/env python3
"""
snapshot_formatter.py — Format L1 snapshot with Indicators + GEX
"""

import json
from typing import Dict, Any

class SnapshotFormatter:
    def format(self, snap: Dict[str, Any]) -> str:
        ticker = snap.get("ticker", "UNKNOWN")
        sid = snap.get("snapshot_id", "N/A")
        spot = snap.get("underlying_price", 0.0)
        vix = snap.get("vix", 0.0)
        market_open = snap.get("market_open", False)

        quotes = snap.get("quotes", {})
        spy_q = quotes.get(ticker, {})
        change = spy_q.get("change", 0.0)
        change_pct = spy_q.get("change_percentage", 0.0)

        gex = snap.get("gex", {})
        sentiment = snap.get("sentiment", {})
        indicators = snap.get("indicators", {})
        macro = snap.get("macro", [])
        earnings = snap.get("earnings", [])
        analyst = snap.get("analyst", {})
        hist = snap.get("historical", [])

        support = gex.get("call_wall", 0.0)
        pressure = gex.get("put_wall", 0.0)
        flip = gex.get("zero_gamma")
        max_pain = gex.get("max_pain")
        regime = gex.get("regime", "neutral").upper()
        net_gex = gex.get("net_gex", 0.0)

        pc_vol = sentiment.get("pc_volume", 0.0)
        pc_oi = sentiment.get("pc_oi", 0.0)
        iv_skew = sentiment.get("iv_skew", 0.0)

        ind = indicators
        signal = ind.get("signal", "N/A")
        conf = ind.get("confidence", 0.0)
        div = ind.get("divergence", 0.0)

        macro_lines = []
        for m in macro[:3]:
            evt = m.get("event", "")
            dt = m.get("time", "")
            if evt:
                macro_lines.append(f"{dt} {evt}")
        macro_str = " | ".join(macro_lines) if macro_lines else "None"

        earn_tickers = [e.get("symbol", "") for e in earnings[:5] if e.get("symbol")]
        earn_str = ", ".join(earn_tickers) if earn_tickers else "None"

        consensus = "N/A"
        if analyst:
            total = sum([analyst.get(k, 0) for k in ["strong_buy", "buy", "hold", "sell", "strong_sell"]])
            if total:
                score = (analyst.get("strong_buy", 0)*2 + analyst.get("buy", 0)*1 +
                         analyst.get("sell", 0)*-1 + analyst.get("strong_sell", 0)*-2) / total
                consensus = "BULLISH" if score > 0.3 else "BEARISH" if score < -0.3 else "NEUTRAL"

        hist_closes = [h["close"] for h in hist[-5:]] if hist else []
        hist_str = ", ".join([f"${c:.2f}" for c in hist_closes]) if hist_closes else "N/A"

        lines = [
            f"[ONE Bot 3.0] Snapshot_ID: {sid}",
            f"Status: {'MARKET_OPEN' if market_open else 'MARKET_CLOSED'}",
            f"Price: ${spot:.2f} ({change:+.2f} / {change_pct:+.2f}%) | VIX: {vix:.2f}",
            f"Regime: {regime} | NetGEX: ${net_gex:,.0f}",
            f"GEX: Support ${support:.2f} | Pressure ${pressure:.2f} | Flip {f'${flip:.2f}' if flip else 'N/A'} | MaxPain {f'${max_pain:.2f}' if max_pain else 'N/A'}",
            f"Sentiment: P/C Vol {pc_vol:.2f} | P/C OI {pc_oi:.2f} | IV Skew {iv_skew:.4f}",
            f"Signal: {signal} | Confidence: {conf:.1%} | Divergence: {div:.2f}",
            f"Indicators: MA5={ind.get('MA_5', 0):.2f} MA20={ind.get('MA_20', 0):.2f} RSI={ind.get('RSI_14', 0):.1f} MACD={ind.get('MACD_Hist', 0):.3f} BB_Pos={ind.get('BB_Position', 0):.3f}",
            f"Macro: {macro_str}",
            f"Earnings: {earn_str}",
            f"Analyst: {consensus}",
            f"Hist5D: {hist_str}",
            f"[ONE Bot 3.0-END]",
        ]
        return "\n".join(lines)
