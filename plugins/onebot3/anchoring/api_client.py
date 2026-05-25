#!/usr/bin/env python3
"""
api_client.py — Multi-source API client
Sources:
  • Tradier  — quotes, full option chains + Greeks
  • YFinance — historical OHLCV, VIX fallback
  • Finnhub  — macro calendar, earnings calendar, analyst recommendations
"""

import os
import time
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pathlib import Path

import requests
import pandas as pd

logger = logging.getLogger("onebot3.api")

class TradierClient:
    def __init__(self, cfg: Dict):
        c = cfg.get("data_sources", {}).get("tradier", {})
        self.base = c.get("base_url", "https://api.tradier.com/v1").rstrip("/")
        # 优先从 config.yaml 的 onebot.tradier.api_key 读取，其次环境变量
        self.token = "o6fWRfSJw3tAlZXPxgS4wRW7hcX8"
        if not self.token:
            # 尝试从 config.yaml 的 onebot 节读取
            try:
                import yaml
                config_path = Path.home() / ".hermes" / "config.yaml"
                if config_path.exists():
                    with open(config_path, "r") as f:
                        full_cfg = yaml.safe_load(f)
                        self.token = full_cfg.get("onebot", {}).get("tradier", {}).get("api_key", "")
            except Exception:
                pass
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/json",
        })

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Dict:
        url = f"{self.base}/{endpoint.lstrip('/')}"
        try:
            r = self.session.get(url, params=params, timeout=30)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error("Tradier API error [%s]: %s", url, e)
            raise

    def fetch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        if not symbols:
            return {}
        sym_str = ",".join(symbols)
        data = self._get(f"/markets/quotes?symbols={sym_str}&greeks=false")
        quotes = data.get("quotes", {}).get("quote", [])
        if isinstance(quotes, dict):
            quotes = [quotes]
        return {q["symbol"]: q for q in quotes if "symbol" in q}

    def fetch_option_expirations(self, symbol: str) -> List[str]:
        data = self._get(f"/markets/options/expirations?symbol={symbol}")
        exps = data.get("expirations", {}).get("date", [])
        return exps if isinstance(exps, list) else [exps] if exps else []

    def fetch_option_chain(self, symbol: str, expiration: str, greeks: bool = True) -> pd.DataFrame:
        params = {"symbol": symbol, "expiration": expiration, "greeks": str(greeks).lower()}
        data = self._get("/markets/options/chains", params=params)
        opts = data.get("options", {}).get("option", [])
        if not opts:
            return pd.DataFrame()
        df = pd.DataFrame(opts)
        if "greeks" in df.columns and isinstance(df["greeks"].iloc[0], dict):
            greeks_df = pd.json_normalize(df["greeks"])
            greeks_df.columns = [f"greeks.{c}" for c in greeks_df.columns]
            df = pd.concat([df.drop(columns=["greeks"]), greeks_df], axis=1)
        for col in ["strike", "last", "bid", "ask", "volume", "open_interest",
                    "greeks.delta", "greeks.gamma", "greeks.theta", "greeks.vega",
                    "greeks.bid_iv", "greeks.ask_iv", "greeks.mid_iv", "greeks.smv_vol"]:
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")
        df["expiration"] = expiration
        df["option_type"] = df["option_type"].str.lower()
        return df

    def fetch_full_option_chain(self, symbol: str) -> pd.DataFrame:
        exps = self.fetch_option_expirations(symbol)
        if not exps:
            return pd.DataFrame()
        frames = []
        for exp in exps:
            try:
                df = self.fetch_option_chain(symbol, exp)
                if not df.empty:
                    frames.append(df)
            except Exception as e:
                logger.warning("Tradier chain fetch failed for %s %s: %s", symbol, exp, e)
            time.sleep(0.12)
        if not frames:
            return pd.DataFrame()
        return pd.concat(frames, ignore_index=True)

class YFinanceClient:
    def __init__(self, cfg: Dict):
        self.enabled = cfg.get("data_sources", {}).get("yfinance", {}).get("enabled", True)

    def fetch_hist_daily(self, symbol: str, days: int = 20) -> List[Dict]:
        if not self.enabled:
            return []
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period=f"{days+5}d", interval="1d")
            if hist.empty:
                return []
            hist = hist.tail(days)
            return [
                {
                    "date": idx.strftime("%Y-%m-%d"),
                    "open": float(row["Open"]),
                    "high": float(row["High"]),
                    "low": float(row["Low"]),
                    "close": float(row["Close"]),
                    "volume": int(row["Volume"]),
                }
                for idx, row in hist.iterrows()
            ]
        except Exception as e:
            logger.error("YFinance hist error: %s", e)
            return []

    def fetch_quote(self, symbol: str) -> Dict:
        if not self.enabled:
            return {}
        try:
            import yfinance as yf
            ticker = yf.Ticker(symbol)
            hist = ticker.history(period="2d", interval="1d")
            last = float(hist["Close"].iloc[-1]) if not hist.empty else 0.0
            prev = float(hist["Close"].iloc[-2]) if len(hist) > 1 else last
            return {
                "symbol": symbol,
                "last": last,
                "prevclose": prev,
                "change": last - prev,
                "change_percentage": ((last - prev) / prev * 100) if prev else 0.0,
            }
        except Exception as e:
            logger.error("YFinance quote error: %s", e)
            return {}

class FinnhubClient:
    def __init__(self, cfg: Dict):
        c = cfg.get("data_sources", {}).get("finnhub", {})
        self.token = "d6tdsu1r01qhkb43pl9gd6tdsu1r01qhkb43pla0"
        self.base = c.get("base_url", "https://finnhub.io/api/v1").rstrip("/")

    def _get(self, endpoint: str, params: Optional[Dict] = None) -> Any:
        p = params or {}
        p["token"] = self.token
        url = f"{self.base}/{endpoint.lstrip('/')}"
        try:
            r = requests.get(url, params=p, timeout=15)
            r.raise_for_status()
            return r.json()
        except requests.exceptions.RequestException as e:
            logger.error("Finnhub API error [%s]: %s", url, e)
            raise

    def fetch_macro_calendar(self, days: int = 7) -> List[Dict]:
        try:
            start = datetime.now().strftime("%Y-%m-%d")
            end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            data = self._get("/calendar/economic", {"from": start, "to": end})
            return data.get("economicCalendar", [])[:20]
        except Exception as e:
            logger.warning("Finnhub macro error: %s", e)
            return []

    def fetch_earnings_calendar(self, days: int = 7) -> List[Dict]:
        try:
            start = datetime.now().strftime("%Y-%m-%d")
            end = (datetime.now() + timedelta(days=days)).strftime("%Y-%m-%d")
            data = self._get("/calendar/earnings", {"from": start, "to": end})
            return data.get("earningsCalendar", [])[:30]
        except Exception as e:
            logger.warning("Finnhub earnings error: %s", e)
            return []

    def fetch_analyst_recommendation(self, symbol: str) -> Dict:
        try:
            data = self._get(f"/stock/recommendation?symbol={symbol}")
            if not data:
                return {}
            latest = data[0] if isinstance(data, list) else data
            return {
                "symbol": symbol,
                "period": latest.get("period"),
                "strong_buy": latest.get("strongBuy", 0),
                "buy": latest.get("buy", 0),
                "hold": latest.get("hold", 0),
                "sell": latest.get("sell", 0),
                "strong_sell": latest.get("strongSell", 0),
            }
        except Exception as e:
            logger.warning("Finnhub analyst error: %s", e)
            return {}

class MultiSourceClient:
    def __init__(self, cfg: Dict):
        self.tradier = TradierClient(cfg)
        self.yf = YFinanceClient(cfg)
        self.finnhub = FinnhubClient(cfg)

    def fetch_quotes(self, symbols: List[str]) -> Dict[str, Dict]:
        try:
            return self.tradier.fetch_quotes(symbols)
        except Exception as e:
            logger.warning("Tradier quotes failed, fallback to YFinance: %s", e)
            result = {}
            for sym in symbols:
                q = self.yf.fetch_quote(sym)
                if q:
                    result[sym] = q
            return result

    def fetch_full_option_chain(self, symbol: str) -> pd.DataFrame:
        return self.tradier.fetch_full_option_chain(symbol)

    def fetch_hist_daily(self, symbol: str, days: int = 20) -> List[Dict]:
        return self.yf.fetch_hist_daily(symbol, days)

    def fetch_macro_calendar(self, days: int = 7) -> List[Dict]:
        return self.finnhub.fetch_macro_calendar(days)

    def fetch_earnings_calendar(self, days: int = 7) -> List[Dict]:
        return self.finnhub.fetch_earnings_calendar(days)

    def fetch_analyst_recommendation(self, symbol: str) -> Dict:
        return self.finnhub.fetch_analyst_recommendation(symbol)
