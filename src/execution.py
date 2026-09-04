"""Execution Layer: Order Placement, Risk Interception, and Trade Persistence."""

import json
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from src.config import Settings, get_settings
from src.risk import RiskEngine, RiskEvaluation
from src.alpaca_client import AlpacaClient
from src.db import Database
from src.logger import log_info, log_success, log_warning, log_error, log_trade_proposal


class ExecutionEngine:
    """Manages verified order execution with 100% un-bypassable risk interception."""

    def __init__(
        self,
        alpaca_client: AlpacaClient,
        risk_engine: RiskEngine,
        db: Database,
        settings: Optional[Settings] = None
    ):
        self.client = alpaca_client
        self.risk = risk_engine
        self.db = db
        self.settings = settings or get_settings()

    def execute_candidate_trade(
        self,
        candidate: Dict[str, Any],
        account_info: Dict[str, Any],
        open_positions_count: int
    ) -> Dict[str, Any]:
        """Intercept candidate trade, evaluate deterministic risk gates, size position, and execute.

        Args:
            candidate: Option spread candidate dictionary.
            account_info: Current account equity, daily PnL, etc.
            open_positions_count: Number of currently open positions.

        Returns:
            Dictionary with execution result, approval status, and trade record.
        """
        equity = float(account_info.get("equity", self.settings.TARGET_STARTING_EQUITY))
        daily_pnl = float(account_info.get("daily_pnl", 0.0))
        kill_switch = self.db.is_kill_switch_active()
        circuit_tripped = self.db.is_circuit_breaker_halted()

        log_info(f"Evaluating Risk Gates for candidate: {candidate.get('symbol')} {candidate.get('strategy_type')}")

        # ----------------------------------------------------------------------
        # DETERMINISTIC RISK INTERCEPTION (CANNOT BE OVERRIDDEN)
        # ----------------------------------------------------------------------
        risk_eval: RiskEvaluation = self.risk.evaluate_order(
            candidate=candidate,
            equity=equity,
            daily_pnl=daily_pnl,
            open_positions_count=open_positions_count,
            kill_switch_active=kill_switch,
            circuit_breaker_tripped=circuit_tripped
        )

        if not risk_eval.approved:
            log_warning(f"ORDER BLOCKED BY RISK ENGINE: {risk_eval.rejection_reason}")
            log_trade_proposal(candidate, "REJECTED", 0)
            return {
                "success": False,
                "approved": False,
                "rejection_reason": risk_eval.rejection_reason,
                "risk_evaluation": risk_eval.to_dict()
            }

        # Sized contracts strictly bounded by Gate 8
        final_contracts = risk_eval.allowed_contracts
        log_trade_proposal(candidate, "APPROVED", final_contracts)

        # ----------------------------------------------------------------------
        # SUBMIT ORDER TO ALPACA (MULTI-LEG)
        # ----------------------------------------------------------------------
        symbol = candidate["symbol"]
        legs = candidate["legs"]
        net_credit = float(candidate["net_credit"])
        max_loss_per_contract = float(candidate["max_loss"])

        try:
            broker_resp = self.client.submit_multi_leg_order(
                symbol=symbol,
                legs=legs,
                net_credit=net_credit,
                contracts=final_contracts,
                order_type="limit",
                time_in_force="day"
            )

            # Persist executed trade to database
            trade_id = f"trade_{uuid.uuid4().hex[:10]}"
            now_iso = datetime.now(timezone.utc).isoformat()
            total_credit = net_credit * final_contracts * 100.0
            total_max_loss = max_loss_per_contract * final_contracts

            trade_record = {
                "id": trade_id,
                "symbol": symbol,
                "strategy_type": candidate["strategy_type"],
                "status": "OPEN",
                "legs": legs,
                "contracts": final_contracts,
                "entry_credit": net_credit,
                "total_credit": total_credit,
                "max_loss": max_loss_per_contract,
                "total_max_loss": total_max_loss,
                "entry_time": now_iso,
                "alpaca_order_id": broker_resp.get("order_id")
            }

            self.db.record_trade_entry(trade_record)
            log_success(f"Trade successfully entered! DB ID: {trade_id} | Alpaca ID: {broker_resp.get('order_id')}")

            return {
                "success": True,
                "approved": True,
                "trade_record": trade_record,
                "broker_response": broker_resp,
                "risk_evaluation": risk_eval.to_dict()
            }

        except Exception as e:
            log_error(f"Broker order submission failed: {e}")
            return {
                "success": False,
                "approved": True,
                "rejection_reason": f"Broker error: {e}",
                "risk_evaluation": risk_eval.to_dict()
            }
