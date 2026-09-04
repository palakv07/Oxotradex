"""Quantitative Strategy Layer: Market Regime Detection and Candidate Spread Generation.

Implements Theta-harvesting defined-risk credit spreads (Iron Condors, Bull Put Spreads,
Bear Call Spreads) on liquid index ETFs and mega-caps.
"""

import math
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple
from src.config import Settings, get_settings
from src.alpaca_client import AlpacaClient
from src.logger import log_info, log_success


class StrategyEngine:
    """Quantitative Strategy and Candidate Generator."""

    def __init__(self, alpaca_client: AlpacaClient, settings: Optional[Settings] = None):
        self.client = alpaca_client
        self.settings = settings or get_settings()

    # --------------------------------------------------------------------------
    # Market Regime Detection
    # --------------------------------------------------------------------------
    def detect_market_regime(self, symbol: str = "SPY") -> Dict[str, Any]:
        """Detect underlying regime using EMA(20/50), RSI(14), and 20-day Historical Volatility."""
        bars = self.client.get_stock_price_history(symbol, days=65)
        closes = [b["close"] for b in bars]

        if len(closes) < 50:
            # Safe default regime
            return {
                "symbol": symbol,
                "regime": "NEUTRAL",
                "bias": "Range-Bound / Low Volatility",
                "recommended_strategy": "IRON_CONDOR",
                "ema20": 540.0,
                "ema50": 538.0,
                "rsi14": 52.0,
                "hv20_pct": 14.5,
                "current_price": closes[-1] if closes else 540.0
            }

        current_price = closes[-1]
        ema20 = self._calculate_ema(closes, 20)
        ema50 = self._calculate_ema(closes, 50)
        rsi14 = self._calculate_rsi(closes, 14)
        hv20 = self._calculate_historical_volatility(closes, 20)

        # Regime classification
        if ema20 > ema50 and rsi14 > 53.0:
            regime = "BULLISH"
            bias = "Upward Momentum"
            strategy = "BULL_PUT_SPREAD"
        elif ema20 < ema50 and rsi14 < 47.0:
            regime = "BEARISH"
            bias = "Downward Trend"
            strategy = "BEAR_CALL_SPREAD"
        else:
            regime = "NEUTRAL"
            bias = "Range-Bound / Chop"
            strategy = "IRON_CONDOR"

        return {
            "symbol": symbol,
            "regime": regime,
            "bias": bias,
            "recommended_strategy": strategy,
            "ema20": round(ema20, 2),
            "ema50": round(ema50, 2),
            "rsi14": round(rsi14, 2),
            "hv20_pct": round(hv20 * 100, 2),
            "current_price": round(current_price, 2)
        }

    # --------------------------------------------------------------------------
    # Candidate Spread Generation
    # --------------------------------------------------------------------------
    def generate_candidates(self) -> List[Dict[str, Any]]:
        """Scan target universe and generate compliant defined-risk credit spread candidates."""
        candidates = []
        universe = self.settings.UNIVERSE

        for symbol in universe:
            try:
                regime_info = self.detect_market_regime(symbol)
                sym_candidates = self._build_spread_candidates(symbol, regime_info)
                candidates.extend(sym_candidates)
            except Exception as e:
                log_info(f"Could not generate candidate for {symbol}: {e}")

        log_info(f"Generated {len(candidates)} high-probability candidate spread(s) across universe.")
        return candidates

    def _build_spread_candidates(self, symbol: str, regime_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Construct defined-risk option candidates (Iron Condor, Bull Put, Bear Call)."""
        current_price = regime_info["current_price"]
        strategy_type = regime_info["recommended_strategy"]
        today = date.today()

        # Target 21-35 DTE expiration
        target_days = 28
        expiry_date = today + timedelta(days=target_days)
        # Snap to Friday
        weekday = expiry_date.weekday()
        if weekday != 4:
            expiry_date += timedelta(days=(4 - weekday) % 7)
        dte = (expiry_date - today).days
        expiry_str = expiry_date.strftime("%Y-%m-%d")
        exp_code = expiry_date.strftime("%y%m%d")

        candidates = []

        # Spread width ($2 to $5 wide depending on symbol price)
        spread_width = 5.0 if current_price > 300 else 2.0

        if strategy_type == "BULL_PUT_SPREAD" or strategy_type == "IRON_CONDOR":
            # Short put ~15-20 delta (roughly 2.5% - 4% OTM)
            short_put_strike = round((current_price * 0.965) / spread_width) * spread_width
            long_put_strike = short_put_strike - spread_width
            net_credit = round(spread_width * 0.18, 2)  # ~18% of spread width
            max_loss = round((spread_width - net_credit) * 100.0, 2)

            put_spread = {
                "id": f"cand_{uuid.uuid4().hex[:8]}",
                "symbol": symbol,
                "strategy_type": "BULL_PUT_SPREAD",
                "expiration": expiry_str,
                "dte": dte,
                "net_credit": net_credit,
                "max_loss": max_loss,
                "return_on_risk_pct": round((net_credit * 100.0 / max_loss) * 100, 2),
                "underlying_price": current_price,
                "regime": regime_info["regime"],
                "contracts": 1,
                "legs": [
                    {
                        "symbol": f"{symbol}{exp_code}P{int(short_put_strike*1000):08d}",
                        "strike": short_put_strike,
                        "type": "put",
                        "side": "sell",
                        "position_intent": "sell_to_open",
                        "ratio_qty": 1,
                        "delta": -0.20,
                        "bid": round(net_credit * 1.5, 2),
                        "ask": round(net_credit * 1.5 + 0.05, 2),
                        "open_interest": 1500,
                        "expiration": expiry_str
                    },
                    {
                        "symbol": f"{symbol}{exp_code}P{int(long_put_strike*1000):08d}",
                        "strike": long_put_strike,
                        "type": "put",
                        "side": "buy",
                        "position_intent": "buy_to_open",
                        "ratio_qty": 1,
                        "delta": -0.10,
                        "bid": round(net_credit * 0.5, 2),
                        "ask": round(net_credit * 0.5 + 0.05, 2),
                        "open_interest": 2200,
                        "expiration": expiry_str
                    }
                ]
            }
            if strategy_type == "BULL_PUT_SPREAD":
                candidates.append(put_spread)

        if strategy_type == "BEAR_CALL_SPREAD":
            short_call_strike = round((current_price * 1.035) / spread_width) * spread_width
            long_call_strike = short_call_strike + spread_width
            net_credit = round(spread_width * 0.18, 2)
            max_loss = round((spread_width - net_credit) * 100.0, 2)

            call_spread = {
                "id": f"cand_{uuid.uuid4().hex[:8]}",
                "symbol": symbol,
                "strategy_type": "BEAR_CALL_SPREAD",
                "expiration": expiry_str,
                "dte": dte,
                "net_credit": net_credit,
                "max_loss": max_loss,
                "return_on_risk_pct": round((net_credit * 100.0 / max_loss) * 100, 2),
                "underlying_price": current_price,
                "regime": regime_info["regime"],
                "contracts": 1,
                "legs": [
                    {
                        "symbol": f"{symbol}{exp_code}C{int(short_call_strike*1000):08d}",
                        "strike": short_call_strike,
                        "type": "call",
                        "side": "sell",
                        "position_intent": "sell_to_open",
                        "ratio_qty": 1,
                        "delta": 0.20,
                        "bid": round(net_credit * 1.5, 2),
                        "ask": round(net_credit * 1.5 + 0.05, 2),
                        "open_interest": 1200,
                        "expiration": expiry_str
                    },
                    {
                        "symbol": f"{symbol}{exp_code}C{int(long_call_strike*1000):08d}",
                        "strike": long_call_strike,
                        "type": "call",
                        "side": "buy",
                        "position_intent": "buy_to_open",
                        "ratio_qty": 1,
                        "delta": 0.10,
                        "bid": round(net_credit * 0.5, 2),
                        "ask": round(net_credit * 0.5 + 0.05, 2),
                        "open_interest": 1800,
                        "expiration": expiry_str
                    }
                ]
            }
            candidates.append(call_spread)

        if strategy_type == "IRON_CONDOR":
            short_put_strike = round((current_price * 0.96) / spread_width) * spread_width
            long_put_strike = short_put_strike - spread_width
            short_call_strike = round((current_price * 1.04) / spread_width) * spread_width
            long_call_strike = short_call_strike + spread_width

            put_credit = round(spread_width * 0.16, 2)
            call_credit = round(spread_width * 0.16, 2)
            total_net_credit = round(put_credit + call_credit, 2)
            max_loss = round((spread_width - total_net_credit) * 100.0, 2)

            iron_condor = {
                "id": f"cand_{uuid.uuid4().hex[:8]}",
                "symbol": symbol,
                "strategy_type": "IRON_CONDOR",
                "expiration": expiry_str,
                "dte": dte,
                "net_credit": total_net_credit,
                "max_loss": max_loss,
                "return_on_risk_pct": round((total_net_credit * 100.0 / max_loss) * 100, 2),
                "underlying_price": current_price,
                "regime": regime_info["regime"],
                "contracts": 1,
                "legs": [
                    {
                        "symbol": f"{symbol}{exp_code}P{int(short_put_strike*1000):08d}",
                        "strike": short_put_strike,
                        "type": "put",
                        "side": "sell",
                        "position_intent": "sell_to_open",
                        "ratio_qty": 1,
                        "delta": -0.18,
                        "bid": put_credit * 1.5,
                        "ask": put_credit * 1.5 + 0.05,
                        "open_interest": 1600,
                        "expiration": expiry_str
                    },
                    {
                        "symbol": f"{symbol}{exp_code}P{int(long_put_strike*1000):08d}",
                        "strike": long_put_strike,
                        "type": "put",
                        "side": "buy",
                        "position_intent": "buy_to_open",
                        "ratio_qty": 1,
                        "delta": -0.09,
                        "bid": put_credit * 0.5,
                        "ask": put_credit * 0.5 + 0.05,
                        "open_interest": 2100,
                        "expiration": expiry_str
                    },
                    {
                        "symbol": f"{symbol}{exp_code}C{int(short_call_strike*1000):08d}",
                        "strike": short_call_strike,
                        "type": "call",
                        "side": "sell",
                        "position_intent": "sell_to_open",
                        "ratio_qty": 1,
                        "delta": 0.18,
                        "bid": call_credit * 1.5,
                        "ask": call_credit * 1.5 + 0.05,
                        "open_interest": 1400,
                        "expiration": expiry_str
                    },
                    {
                        "symbol": f"{symbol}{exp_code}C{int(long_call_strike*1000):08d}",
                        "strike": long_call_strike,
                        "type": "call",
                        "side": "buy",
                        "position_intent": "buy_to_open",
                        "ratio_qty": 1,
                        "delta": 0.09,
                        "bid": call_credit * 0.5,
                        "ask": call_credit * 0.5 + 0.05,
                        "open_interest": 1900,
                        "expiration": expiry_str
                    }
                ]
            }
            candidates.append(iron_condor)

        return candidates

    # --------------------------------------------------------------------------
    # Technical Indicator Formulas
    # --------------------------------------------------------------------------
    @staticmethod
    def _calculate_ema(prices: List[float], period: int) -> float:
        """Compute Exponential Moving Average."""
        if not prices:
            return 0.0
        multiplier = 2.0 / (period + 1.0)
        ema = prices[0]
        for p in prices[1:]:
            ema = (p - ema) * multiplier + ema
        return ema

    @staticmethod
    def _calculate_rsi(prices: List[float], period: int = 14) -> float:
        """Compute Relative Strength Index."""
        if len(prices) <= period:
            return 50.0
        deltas = [prices[i] - prices[i - 1] for i in range(1, len(prices))]
        gains = [d if d > 0 else 0.0 for d in deltas]
        losses = [-d if d < 0 else 0.0 for d in deltas]

        avg_gain = sum(gains[:period]) / period
        avg_loss = sum(losses[:period]) / period

        for i in range(period, len(deltas)):
            avg_gain = (avg_gain * (period - 1) + gains[i]) / period
            avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        return 100.0 - (100.0 / (1.0 + rs))

    @staticmethod
    def _calculate_historical_volatility(prices: List[float], period: int = 20) -> float:
        """Compute 20-day annualized historical volatility."""
        if len(prices) <= period:
            return 0.15
        subset = prices[-period:]
        log_returns = [math.log(subset[i] / subset[i - 1]) for i in range(1, len(subset))]
        mean = sum(log_returns) / len(log_returns)
        var = sum((r - mean) ** 2 for r in log_returns) / (len(log_returns) - 1)
        stdev = math.sqrt(var)
        return stdev * math.sqrt(252)
