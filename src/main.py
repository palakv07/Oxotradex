"""Oxotradex: Autonomous Options Alpha Agent - Main Execution Loop.

Orchestrates market scanning, position management, quantitative regime analysis,
structured LLM reasoning, deterministic risk gates, and multi-leg order execution.
"""

import argparse
import time
import sys
import os
from datetime import datetime, timezone
from typing import Optional

# Ensure project root is on sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import Settings, get_settings
from src.db import Database
from src.alpaca_client import AlpacaClient
from src.risk import RiskEngine
from src.strategy import StrategyEngine
from src.llm_decision import LLMDecisionEngine
from src.position_manager import PositionManager
from src.execution import ExecutionEngine
from src.logger import log_header, log_info, log_success, log_warning, log_error


class AutonomousAgent:
    """End-to-End Autonomous Trading Agent powered by Oxotradex."""

    def __init__(self, settings: Optional[Settings] = None, dry_run: bool = False):
        self.settings = settings or get_settings()
        if dry_run:
            self.settings.DRY_RUN = True

        log_header(
            "Oxotradex: Autonomous Options Alpha Agent",
            f"Paper Mode: {self.settings.PAPER} | Dry Run: {self.settings.DRY_RUN} | LLM: {self.settings.LLM_PROVIDER}"
        )

        self.db = Database(self.settings.DB_PATH)
        self.client = AlpacaClient(self.settings)
        self.risk = RiskEngine(self.settings)
        self.strategy = StrategyEngine(self.client, self.settings)
        self.llm = LLMDecisionEngine(self.settings)
        self.pos_manager = PositionManager(self.client, self.db, self.settings)
        self.execution = ExecutionEngine(self.client, self.risk, self.db, self.settings)

    def run_cycle(self) -> bool:
        """Execute one complete autonomous decision and management cycle.

        Returns:
            True if cycle completed normally, False if halted by risk gate or kill-switch.
        """
        cycle_start = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        log_info(f"--- Starting Oxotradex Scan Cycle at {cycle_start} ---")

        # ----------------------------------------------------------------------
        # Step 1: Check Emergency Kill Switch
        # ----------------------------------------------------------------------
        if self.db.is_kill_switch_active():
            log_warning("EMERGENCY KILL-SWITCH IS ENGAGED. Autonomous loop will not execute trades.")
            return False

        # ----------------------------------------------------------------------
        # Step 2: Fetch Account Metrics & Market Clock
        # ----------------------------------------------------------------------
        account_info = self.client.get_account_info()
        clock = self.client.get_clock()
        equity = float(account_info["equity"])
        daily_pnl = float(account_info["daily_pnl"])
        daily_pnl_pct = float(account_info["daily_pnl_pct"])

        log_info(
            f"Account Status: Equity: ${equity:,.2f} | Cash: ${account_info['cash']:,.2f} | "
            f"Daily PnL: ${daily_pnl:+,.2f} ({daily_pnl_pct*100:+.2f}%)"
        )

        # ----------------------------------------------------------------------
        # Step 3: Record Daily Snapshot & Check Daily Circuit Breaker
        # ----------------------------------------------------------------------
        open_trades = self.db.get_open_trades()
        open_count = len(open_trades)

        target_equity = self.settings.TARGET_STARTING_EQUITY
        max_daily_loss = target_equity * self.settings.DAILY_LOSS_CIRCUIT_BREAKER_PCT
        circuit_tripped = (daily_pnl <= -max_daily_loss)

        self.db.record_daily_snapshot(
            current_equity=equity,
            starting_equity=target_equity,
            open_positions=open_count,
            circuit_breaker=circuit_tripped
        )

        if circuit_tripped:
            self.db.set_circuit_breaker_halt(True)
            log_error(
                f"DAILY CIRCUIT BREAKER TRIPPED! Daily loss -${abs(daily_pnl):,.2f} exceeds "
                f"limit of -${max_daily_loss:,.2f} (-2.5%). Halting new entries for today."
            )
            # We still evaluate existing positions to manage risk
            self.pos_manager.evaluate_open_positions()
            return False
        else:
            self.db.set_circuit_breaker_halt(False)

        # ----------------------------------------------------------------------
        # Step 4: Manage Active Open Positions (Take Profit, Stop Loss, Expiry)
        # ----------------------------------------------------------------------
        self.pos_manager.evaluate_open_positions()

        # Refresh open count after any TP/SL closures
        open_trades = self.db.get_open_trades()
        open_count = len(open_trades)

        # ----------------------------------------------------------------------
        # Step 5: Check Concurrent Position Capacity Limit
        # ----------------------------------------------------------------------
        if open_count >= self.settings.MAX_CONCURRENT_POSITIONS:
            log_info(f"Portfolio at maximum capacity ({open_count}/{self.settings.MAX_CONCURRENT_POSITIONS} positions). Skipping new entry scan.")
            return True

        # ----------------------------------------------------------------------
        # Step 6: Strategy Regime Detection & Candidate Generation
        # ----------------------------------------------------------------------
        primary_regime = self.strategy.detect_market_regime("SPY")
        log_info(
            f"Market Regime (SPY): {primary_regime['regime']} ({primary_regime['bias']}) | "
            f"EMA20: {primary_regime['ema20']} | EMA50: {primary_regime['ema50']} | RSI: {primary_regime['rsi14']}"
        )

        candidates = self.strategy.generate_candidates()
        if not candidates:
            log_info("No viable spread candidates identified matching filters.")
            return True

        # ----------------------------------------------------------------------
        # Step 7: Structured LLM Decision
        # ----------------------------------------------------------------------
        decision = self.llm.decide(
            account_info=account_info,
            regime_info=primary_regime,
            candidates=candidates,
            open_positions=open_trades
        )

        log_info(f"LLM Macro Analysis: {decision.market_analysis}")
        log_info(f"LLM Risk Assessment: {decision.risk_assessment}")

        # Map candidates by ID for lookup
        candidate_map = {c["id"]: c for c in candidates}

        # ----------------------------------------------------------------------
        # Step 8: Deterministic Risk Gate & Execution
        # ----------------------------------------------------------------------
        actions_taken = 0
        for action in decision.recommended_actions:
            if action.action_type == "OPEN_TRADE" and action.candidate_id:
                cand = candidate_map.get(action.candidate_id)
                if not cand:
                    # Fallback lookup by symbol if ID was generated dynamically
                    for c in candidates:
                        if c["symbol"] == action.symbol and c["strategy_type"] == action.strategy_type:
                            cand = c
                            break

                if not cand:
                    log_warning(f"Candidate {action.candidate_id} not found in current pool. Skipping.")
                    continue

                # Pass through inviolable execution engine
                cand["contracts"] = action.proposed_contracts
                result = self.execution.execute_candidate_trade(
                    candidate=cand,
                    account_info=account_info,
                    open_positions_count=open_count
                )

                # Persist decision audit
                self.db.record_decision(
                    regime_summary=f"{primary_regime['regime']} ({primary_regime['bias']})",
                    candidates=[cand],
                    llm_response=decision.raw_response,
                    selected_action=f"{action.action_type} {cand['symbol']} {cand['strategy_type']}",
                    risk_results=result.get("risk_evaluation", {}).get("gate_results", []),
                    risk_verdict="APPROVED" if result.get("approved") else "REJECTED",
                    rejection_reason=result.get("rejection_reason")
                )

                if result.get("success"):
                    actions_taken += 1
                    open_count += 1
                    if open_count >= self.settings.MAX_CONCURRENT_POSITIONS:
                        break

        log_success(f"--- Oxotradex Scan Cycle Completed. Executed {actions_taken} new trade(s). ---")
        return True

    def start_loop(self, interval_minutes: Optional[int] = None):
        """Run the autonomous agent continuously on the configured schedule."""
        interval = interval_minutes or self.settings.SCAN_INTERVAL_MINUTES
        log_info(f"Starting Oxotradex autonomous loop. Polling every {interval} minute(s)...")

        try:
            while True:
                try:
                    self.run_cycle()
                except Exception as e:
                    log_error(f"Unexpected error in autonomous cycle: {e}")

                log_info(f"Sleeping for {interval} minute(s)... (Press Ctrl+C to stop)")
                time.sleep(interval * 60)

        except KeyboardInterrupt:
            log_warning("Oxotradex loop manually interrupted by user. Shutting down gracefully.")
            sys.exit(0)


def main():
    parser = argparse.ArgumentParser(description="Oxotradex: Autonomous Options Alpha Agent")
    parser.add_argument("--once", action="store_true", help="Run a single scan cycle and exit")
    parser.add_argument("--dry-run", action="store_true", help="Force dry-run simulation mode")
    parser.add_argument("--interval", type=int, default=None, help="Scan interval in minutes")
    args = parser.parse_args()

    agent = AutonomousAgent(dry_run=args.dry_run)

    if args.once:
        agent.run_cycle()
    else:
        agent.start_loop(interval_minutes=args.interval)


if __name__ == "__main__":
    main()
