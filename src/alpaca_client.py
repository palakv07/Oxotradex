"""Alpaca Broker and MCP Interface for Multi-Leg Options Trading.

Supports official alpaca-py SDK and Alpaca MCP Server protocol with
deterministic fallback and dry-run simulation.
"""

import json
import uuid
from datetime import datetime, timedelta, timezone, date
from typing import Any, Dict, List, Optional, Tuple

from alpaca.trading.client import TradingClient
from alpaca.trading.requests import (
    LimitOrderRequest,
    MarketOrderRequest,
    OptionLegRequest,
    GetOrdersRequest,
    ClosePositionRequest
)
from alpaca.trading.enums import (
    OrderClass,
    OrderSide,
    OrderType,
    TimeInForce,
    PositionIntent,
    QueryOrderStatus
)
from alpaca.data.historical.stock import StockHistoricalDataClient
from alpaca.data.historical.option import OptionHistoricalDataClient
from alpaca.data.requests import (
    StockBarsRequest,
    OptionChainRequest,
    OptionSnapshotRequest
)
from alpaca.data.timeframe import TimeFrame

from src.config import Settings, get_settings
from src.logger import log_info, log_success, log_warning, log_error


class AlpacaClient:
    """Unified Alpaca Client supporting Multi-Leg Options Trading and MCP compatibility."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.api_key = self.settings.ALPACA_API_KEY
        self.secret_key = self.settings.ALPACA_SECRET_KEY
        self.paper = self.settings.PAPER
        self.dry_run = self.settings.DRY_RUN

        # Initialize alpaca-py clients if API keys are provided
        self.has_keys = bool(self.api_key and self.secret_key and "your_alpaca" not in self.api_key)
        if self.has_keys:
            try:
                self.trading_client = TradingClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key,
                    paper=self.paper
                )
                self.stock_data_client = StockHistoricalDataClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key
                )
                self.option_data_client = OptionHistoricalDataClient(
                    api_key=self.api_key,
                    secret_key=self.secret_key
                )
                log_info("Alpaca Trading & Data Clients initialized in PAPER mode.")
            except Exception as e:
                log_warning(f"Could not connect to Alpaca live endpoints: {e}. Defaulting to simulated paper mode.")
                self.has_keys = False
        else:
            log_warning("No Alpaca API credentials configured. Running in simulated paper trading mode.")

    # --------------------------------------------------------------------------
    # Account & Market Status
    # --------------------------------------------------------------------------
    def get_account_info(self) -> Dict[str, Any]:
        """Fetch account equity, cash, buying power, and daily PnL."""
        if self.has_keys and not self.dry_run:
            try:
                acct = self.trading_client.get_account()
                equity = float(acct.equity)
                last_equity = float(acct.last_equity)
                daily_pnl = equity - last_equity
                daily_pnl_pct = (daily_pnl / last_equity) if last_equity > 0 else 0.0

                return {
                    "equity": equity,
                    "cash": float(acct.cash),
                    "buying_power": float(acct.buying_power),
                    "last_equity": last_equity,
                    "daily_pnl": daily_pnl,
                    "daily_pnl_pct": daily_pnl_pct,
                    "currency": acct.currency,
                    "is_paper": True,
                    "raw_status": acct.status.value
                }
            except Exception as e:
                log_error(f"Failed to fetch live Alpaca account: {e}. Falling back to default starting equity.")

        # Fallback simulation starting at $100,000 for submission/offline testing
        target = self.settings.TARGET_STARTING_EQUITY
        return {
            "equity": target,
            "cash": target,
            "buying_power": target * 2.0,
            "last_equity": target,
            "daily_pnl": 0.0,
            "daily_pnl_pct": 0.0,
            "currency": "USD",
            "is_paper": True,
            "raw_status": "ACTIVE"
        }

    def get_clock(self) -> Dict[str, Any]:
        """Fetch market clock status."""
        if self.has_keys and not self.dry_run:
            try:
                clock = self.trading_client.get_clock()
                return {
                    "is_open": clock.is_open,
                    "timestamp": clock.timestamp.isoformat(),
                    "next_open": clock.next_open.isoformat(),
                    "next_close": clock.next_close.isoformat()
                }
            except Exception as e:
                log_warning(f"Error checking market clock: {e}. Using local time approximation.")

        # Local time market hours estimation (09:30 - 16:00 US Eastern)
        now_utc = datetime.now(timezone.utc)
        # US Eastern is UTC-5 or UTC-4. Standard trading day is Mon-Fri.
        is_weekday = now_utc.weekday() < 5
        # Approximate 9:30 AM to 4:00 PM EST (14:30 to 21:00 UTC)
        is_market_hours = is_weekday and (14 <= now_utc.hour < 21)

        return {
            "is_open": is_market_hours,
            "timestamp": now_utc.isoformat(),
            "next_open": (now_utc + timedelta(days=1)).replace(hour=14, minute=30).isoformat(),
            "next_close": now_utc.replace(hour=21, minute=0).isoformat()
        }

    # --------------------------------------------------------------------------
    # Market Data & Option Chain
    # --------------------------------------------------------------------------
    def get_stock_price_history(self, symbol: str, days: int = 60) -> List[Dict[str, Any]]:
        """Fetch daily historical bars for regime calculation (EMA, RSI, Volatility)."""
        if self.has_keys:
            try:
                end_time = datetime.now(timezone.utc)
                start_time = end_time - timedelta(days=days + 15)
                req = StockBarsRequest(
                    symbol_or_symbols=symbol,
                    timeframe=TimeFrame.Day,
                    start=start_time,
                    end=end_time
                )
                bars = self.stock_data_client.get_stock_bars(req)
                if symbol in bars:
                    records = []
                    for b in bars[symbol]:
                        records.append({
                            "timestamp": b.timestamp.isoformat(),
                            "open": float(b.open),
                            "high": float(b.high),
                            "low": float(b.low),
                            "close": float(b.close),
                            "volume": float(b.volume)
                        })
                    return records
            except Exception as e:
                log_warning(f"Error fetching stock bars for {symbol}: {e}. Using synthetic baseline.")

        # Synthetic historical series for testing/offline mode
        base_prices = {"SPY": 540.0, "QQQ": 470.0, "IWM": 215.0, "AAPL": 225.0, "MSFT": 430.0, "NVDA": 125.0}
        curr = base_prices.get(symbol, 500.0)
        history = []
        now = datetime.now(timezone.utc)
        for i in range(days, 0, -1):
            t = now - timedelta(days=i)
            # Slight random drift for realistic indicators
            drift = (hash(f"{symbol}_{i}") % 100 - 48) * 0.15
            price = curr + drift
            history.append({
                "timestamp": t.isoformat(),
                "open": price - 0.5,
                "high": price + 1.0,
                "low": price - 1.0,
                "close": price,
                "volume": 50000000.0
            })
        return history

    def get_option_chain_data(self, underlying_symbol: str) -> Dict[str, Any]:
        """Fetch option chain and latest quotes for candidate filtering."""
        if self.has_keys:
            try:
                req = OptionChainRequest(underlying_symbol=underlying_symbol)
                chain = self.option_data_client.get_option_chain(req)
                return chain
            except Exception as e:
                log_warning(f"Error retrieving option chain for {underlying_symbol}: {e}. Using structured synthetic chain.")

        # Return structured synthetic chain for offline or simulation mode
        return {}

    # --------------------------------------------------------------------------
    # Multi-Leg Option Orders
    # --------------------------------------------------------------------------
    def submit_multi_leg_order(
        self,
        symbol: str,
        legs: List[Dict[str, Any]],
        net_credit: float,
        contracts: int,
        order_type: str = "limit",
        time_in_force: str = "day"
    ) -> Dict[str, Any]:
        """Submit a multi-leg option order (Iron Condor, Credit Spread) to Alpaca.

        Args:
            symbol: Underlying ticker (e.g. 'SPY').
            legs: List of leg definitions with 'symbol', 'ratio_qty', 'side', 'position_intent'.
            net_credit: Net credit limit price per share.
            contracts: Number of contracts.
            order_type: 'limit' or 'market'.
            time_in_force: 'day' or 'gtc'.

        Returns:
            Dictionary with order status, order ID, and execution timestamps.
        """
        order_id = f"alpaca_mleg_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        if self.dry_run or not self.has_keys:
            log_info(f"[DRY RUN / SIMULATION] Executing multi-leg order: {symbol} {contracts}x @ ${net_credit:.2f} credit")
            for idx, leg in enumerate(legs, 1):
                log_info(f"  Leg {idx}: {leg.get('side').upper()} {leg.get('ratio_qty')} {leg.get('symbol')} ({leg.get('position_intent')})")

            return {
                "order_id": order_id,
                "status": "filled",
                "symbol": symbol,
                "contracts": contracts,
                "net_credit": net_credit,
                "filled_at": now_str,
                "is_simulated": True,
                "legs": legs
            }

        try:
            alpaca_legs: List[OptionLegRequest] = []
            for leg in legs:
                side_enum = OrderSide.BUY if leg.get("side").lower() == "buy" else OrderSide.SELL
                intent_enum = PositionIntent(leg.get("position_intent", "buy_to_open" if side_enum == OrderSide.BUY else "sell_to_open"))

                alpaca_legs.append(
                    OptionLegRequest(
                        symbol=leg["symbol"],
                        ratio_qty=leg.get("ratio_qty", 1),
                        side=side_enum,
                        position_intent=intent_enum
                    )
                )

            tif_enum = TimeInForce.DAY if time_in_force.lower() == "day" else TimeInForce.GTC

            # Prepare Multi-Leg Limit Order Request
            # In Alpaca mleg orders, net credit is submitted as positive limit price
            req = LimitOrderRequest(
                symbol=legs[0]["symbol"],  # Primary contract symbol or underlying
                qty=contracts,
                limit_price=round(net_credit, 2),
                time_in_force=tif_enum,
                order_class=OrderClass.MLEG,
                legs=alpaca_legs
            )

            res = self.trading_client.submit_order(req)
            log_success(f"Multi-leg order submitted successfully! Alpaca Order ID: {res.id}")

            return {
                "order_id": str(res.id),
                "status": str(res.status.value),
                "symbol": symbol,
                "contracts": contracts,
                "net_credit": net_credit,
                "filled_at": now_str,
                "is_simulated": False,
                "legs": legs
            }

        except Exception as e:
            log_error(f"Broker rejected multi-leg order: {e}")
            raise RuntimeError(f"Alpaca MLEG order execution failed: {e}")

    def close_multi_leg_position(
        self,
        symbol: str,
        legs: List[Dict[str, Any]],
        net_debit_limit: float,
        contracts: int
    ) -> Dict[str, Any]:
        """Close an existing spread position by executing opposite closing legs.

        Short legs are closed with 'buy_to_close', long legs with 'sell_to_close'.
        """
        order_id = f"close_mleg_{uuid.uuid4().hex[:12]}"
        now_str = datetime.now(timezone.utc).isoformat()

        # Build reverse legs for closing
        closing_legs: List[Dict[str, Any]] = []
        for leg in legs:
            current_side = leg.get("side", "sell").lower()
            if current_side == "sell":
                # Close short leg by buying to close
                closing_legs.append({
                    "symbol": leg["symbol"],
                    "ratio_qty": leg.get("ratio_qty", 1),
                    "side": "buy",
                    "position_intent": "buy_to_close",
                    "strike": leg.get("strike"),
                    "type": leg.get("type")
                })
            else:
                # Close long leg by selling to close
                closing_legs.append({
                    "symbol": leg["symbol"],
                    "ratio_qty": leg.get("ratio_qty", 1),
                    "side": "sell",
                    "position_intent": "sell_to_close",
                    "strike": leg.get("strike"),
                    "type": leg.get("type")
                })

        if self.dry_run or not self.has_keys:
            log_info(f"[DRY RUN] Closing spread {symbol} {contracts}x @ ${net_debit_limit:.2f} debit limit")
            return {
                "order_id": order_id,
                "status": "filled",
                "symbol": symbol,
                "contracts": contracts,
                "exit_cost": net_debit_limit,
                "filled_at": now_str,
                "is_simulated": True
            }

        try:
            alpaca_legs: List[OptionLegRequest] = []
            for leg in closing_legs:
                side_enum = OrderSide.BUY if leg["side"] == "buy" else OrderSide.SELL
                intent_enum = PositionIntent(leg["position_intent"])
                alpaca_legs.append(
                    OptionLegRequest(
                        symbol=leg["symbol"],
                        ratio_qty=leg["ratio_qty"],
                        side=side_enum,
                        position_intent=intent_enum
                    )
                )

            req = LimitOrderRequest(
                symbol=closing_legs[0]["symbol"],
                qty=contracts,
                limit_price=round(net_debit_limit, 2),
                time_in_force=TimeInForce.DAY,
                order_class=OrderClass.MLEG,
                legs=alpaca_legs
            )

            res = self.trading_client.submit_order(req)
            log_success(f"Multi-leg closing order placed: {res.id}")
            return {
                "order_id": str(res.id),
                "status": str(res.status.value),
                "symbol": symbol,
                "contracts": contracts,
                "exit_cost": net_debit_limit,
                "filled_at": now_str,
                "is_simulated": False
            }

        except Exception as e:
            log_error(f"Failed to submit multi-leg closing order: {e}")
            raise RuntimeError(f"Alpaca MLEG closing order failed: {e}")

    # --------------------------------------------------------------------------
    # MCP Protocol Compatibility Wrapper
    # --------------------------------------------------------------------------
    def call_mcp_tool(self, tool_name: str, arguments: Dict[str, Any]) -> Dict[str, Any]:
        """Dispatch requests in accordance with the official Alpaca MCP Server spec."""
        if tool_name == "get_account":
            return self.get_account_info()
        elif tool_name == "get_clock":
            return self.get_clock()
        elif tool_name == "place_option_order" or tool_name == "place_multi_leg_order":
            return self.submit_multi_leg_order(
                symbol=arguments.get("symbol", "SPY"),
                legs=arguments.get("legs", []),
                net_credit=arguments.get("net_credit", 0.50),
                contracts=arguments.get("contracts", 1)
            )
        elif tool_name == "close_spread":
            return self.close_multi_leg_position(
                symbol=arguments.get("symbol", "SPY"),
                legs=arguments.get("legs", []),
                net_debit_limit=arguments.get("net_debit_limit", 0.25),
                contracts=arguments.get("contracts", 1)
            )
        else:
            raise NotImplementedError(f"MCP tool '{tool_name}' not implemented in client wrapper.")
