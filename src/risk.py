"""Deterministic Hard Risk Gates for Oxotradex: Autonomous Options Alpha Agent.

CRITICAL INVARIANT:
These gates are 100% un-bypassable in Python code. Under no circumstances
can an LLM prompt, recommendation, or confidence score override these checks.
"""

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional
from src.config import Settings, get_settings
from src.logger import log_risk_gate


@dataclass
class GateCheckResult:
    """Individual risk gate check outcome."""
    gate_name: str
    passed: bool
    message: str
    details: Dict[str, Any] = field(default_factory=dict)


@dataclass
class RiskEvaluation:
    """Overall deterministic risk evaluation result."""
    approved: bool
    rejection_reason: Optional[str]
    allowed_contracts: int
    gate_results: List[GateCheckResult]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "approved": self.approved,
            "rejection_reason": self.rejection_reason,
            "allowed_contracts": self.allowed_contracts,
            "gate_results": [
                {
                    "gate_name": g.gate_name,
                    "passed": g.passed,
                    "message": g.message,
                    "details": g.details
                }
                for g in self.gate_results
            ]
        }


class RiskEngine:
    """Inviolable deterministic risk enforcement engine."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()

    def evaluate_order(
        self,
        candidate: Dict[str, Any],
        equity: float,
        daily_pnl: float,
        open_positions_count: int,
        kill_switch_active: bool = False,
        circuit_breaker_tripped: bool = False
    ) -> RiskEvaluation:
        """Run all hard deterministic gates against a proposed trade setup.

        Args:
            candidate: Option spread candidate dictionary.
            equity: Current portfolio equity in dollars.
            daily_pnl: Current day's cumulative realized + unrealized PnL in dollars.
            open_positions_count: Current count of active open spread positions.
            kill_switch_active: Boolean flag if manual or emergency kill switch is engaged.
            circuit_breaker_tripped: Boolean flag if daily loss circuit breaker was tripped.

        Returns:
            RiskEvaluation with approved flag, allowed sizing, and audit trail.
        """
        gate_results: List[GateCheckResult] = []

        # ----------------------------------------------------------------------
        # Gate 1: Kill-Switch Check
        # ----------------------------------------------------------------------
        if kill_switch_active:
            res = GateCheckResult(
                gate_name="Gate 1: Kill-Switch",
                passed=False,
                message="Emergency kill-switch is ACTIVE. Trading is completely halted.",
                details={"kill_switch": True}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(
                approved=False,
                rejection_reason=res.message,
                allowed_contracts=0,
                gate_results=gate_results
            )
        else:
            res = GateCheckResult(
                gate_name="Gate 1: Kill-Switch",
                passed=True,
                message="Kill-switch inactive.",
                details={"kill_switch": False}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 2: Daily Loss Circuit Breaker (-2.5% of Starting Equity)
        # ----------------------------------------------------------------------
        target_equity = self.settings.TARGET_STARTING_EQUITY
        max_daily_loss = target_equity * self.settings.DAILY_LOSS_CIRCUIT_BREAKER_PCT
        # daily_pnl is negative when in a loss
        daily_loss_pct = (daily_pnl / target_equity) if target_equity > 0 else 0.0

        if circuit_breaker_tripped or (daily_pnl <= -max_daily_loss):
            msg = (
                f"Daily loss circuit breaker TRIPPED! Daily PnL is ${daily_pnl:.2f} "
                f"({daily_loss_pct*100:.2f}%), exceeding limit of -${max_daily_loss:.2f} "
                f"(-{self.settings.DAILY_LOSS_CIRCUIT_BREAKER_PCT*100:.1f}%). All entries halted."
            )
            res = GateCheckResult(
                gate_name="Gate 2: Daily Circuit Breaker",
                passed=False,
                message=msg,
                details={"daily_pnl": daily_pnl, "max_daily_loss": max_daily_loss, "daily_loss_pct": daily_loss_pct}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(
                approved=False,
                rejection_reason=msg,
                allowed_contracts=0,
                gate_results=gate_results
            )
        else:
            res = GateCheckResult(
                gate_name="Gate 2: Daily Circuit Breaker",
                passed=True,
                message=f"Daily PnL is ${daily_pnl:.2f} ({daily_loss_pct*100:.2f}%), within limit -${max_daily_loss:.2f}.",
                details={"daily_pnl": daily_pnl, "limit": -max_daily_loss}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 3: Max Concurrent Open Positions (Limit: 5)
        # ----------------------------------------------------------------------
        max_positions = self.settings.MAX_CONCURRENT_POSITIONS
        if open_positions_count >= max_positions:
            msg = f"Maximum concurrent positions reached ({open_positions_count}/{max_positions}). New trades blocked."
            res = GateCheckResult(
                gate_name="Gate 3: Max Concurrent Positions",
                passed=False,
                message=msg,
                details={"open_positions": open_positions_count, "max_allowed": max_positions}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(
                approved=False,
                rejection_reason=msg,
                allowed_contracts=0,
                gate_results=gate_results
            )
        else:
            res = GateCheckResult(
                gate_name="Gate 3: Max Concurrent Positions",
                passed=True,
                message=f"Current positions: {open_positions_count}/{max_positions}.",
                details={"open_positions": open_positions_count, "max_allowed": max_positions}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 4: Defined-Risk Spread Integrity (NO Naked Short Options)
        # ----------------------------------------------------------------------
        legs = candidate.get("legs", [])
        if not legs or len(legs) < 2:
            msg = "Trade rejected: Defined-risk spreads require at least 2 legs (short + long hedge)."
            res = GateCheckResult(gate_name="Gate 4: Defined Risk Check", passed=False, message=msg)
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

        # Count short vs long legs to guarantee all short legs are hedged
        short_puts = sum(1 for leg in legs if leg.get("side") == "sell" and leg.get("type") == "put")
        long_puts = sum(1 for leg in legs if leg.get("side") == "buy" and leg.get("type") == "put")
        short_calls = sum(1 for leg in legs if leg.get("side") == "sell" and leg.get("type") == "call")
        long_calls = sum(1 for leg in legs if leg.get("side") == "buy" and leg.get("type") == "call")

        if short_puts > long_puts or short_calls > long_calls:
            msg = (
                f"Trade rejected: Naked short risk detected! Short puts: {short_puts}, Long puts: {long_puts}; "
                f"Short calls: {short_calls}, Long calls: {long_calls}."
            )
            res = GateCheckResult(gate_name="Gate 4: Defined Risk Check", passed=False, message=msg)
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

        res = GateCheckResult(
            gate_name="Gate 4: Defined Risk Check",
            passed=True,
            message=f"Spread is fully defined risk with {len(legs)} hedged legs.",
            details={"legs_count": len(legs)}
        )
        gate_results.append(res)
        log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 5: Delta Limit on Short Options (Delta <= 0.30)
        # ----------------------------------------------------------------------
        max_short_delta = self.settings.MAX_SHORT_DELTA
        for leg in legs:
            if leg.get("side") == "sell":
                delta = abs(float(leg.get("delta", 0.0)))
                if delta > max_short_delta:
                    msg = (
                        f"Trade rejected: Short leg {leg.get('symbol', 'unknown')} delta {delta:.2f} "
                        f"exceeds maximum allowed threshold of {max_short_delta:.2f}."
                    )
                    res = GateCheckResult(
                        gate_name="Gate 5: Short Delta Check",
                        passed=False,
                        message=msg,
                        details={"delta": delta, "max_delta": max_short_delta}
                    )
                    gate_results.append(res)
                    log_risk_gate(res.gate_name, res.passed, res.message)
                    return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

        res = GateCheckResult(
            gate_name="Gate 5: Short Delta Check",
            passed=True,
            message=f"All short leg deltas are <= {max_short_delta:.2f}.",
            details={"max_delta_limit": max_short_delta}
        )
        gate_results.append(res)
        log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 6: Minimum Net Credit Threshold ($0.20 per share / $20 per contract)
        # ----------------------------------------------------------------------
        net_credit = float(candidate.get("net_credit", 0.0))
        min_credit = self.settings.MIN_CREDIT
        if net_credit < min_credit:
            msg = f"Trade rejected: Net credit ${net_credit:.2f} is below minimum required ${min_credit:.2f}."
            res = GateCheckResult(
                gate_name="Gate 6: Minimum Credit Check",
                passed=False,
                message=msg,
                details={"net_credit": net_credit, "min_credit": min_credit}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

        res = GateCheckResult(
            gate_name="Gate 6: Minimum Credit Check",
            passed=True,
            message=f"Net credit of ${net_credit:.2f} meets minimum requirement >= ${min_credit:.2f}.",
            details={"net_credit": net_credit}
        )
        gate_results.append(res)
        log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 7: Liquidity & Bid-Ask Spread Check
        # ----------------------------------------------------------------------
        max_spread = self.settings.MAX_BID_ASK_SPREAD
        min_oi = self.settings.MIN_OPEN_INTEREST
        for leg in legs:
            bid = float(leg.get("bid", 0.0))
            ask = float(leg.get("ask", 0.0))
            spread = ask - bid
            oi = int(leg.get("open_interest", 0))

            if spread > max_spread and ask > 0.0:
                msg = f"Trade rejected: Leg {leg.get('symbol')} bid-ask spread ${spread:.2f} exceeds max ${max_spread:.2f}."
                res = GateCheckResult(gate_name="Gate 7: Liquidity Check", passed=False, message=msg)
                gate_results.append(res)
                log_risk_gate(res.gate_name, res.passed, res.message)
                return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

            if oi < min_oi and oi > 0:  # If OI is reported and below min
                msg = f"Trade rejected: Leg {leg.get('symbol')} open interest {oi} below minimum {min_oi}."
                res = GateCheckResult(gate_name="Gate 7: Liquidity Check", passed=False, message=msg)
                gate_results.append(res)
                log_risk_gate(res.gate_name, res.passed, res.message)
                return RiskEvaluation(approved=False, rejection_reason=msg, allowed_contracts=0, gate_results=gate_results)

        res = GateCheckResult(
            gate_name="Gate 7: Liquidity Check",
            passed=True,
            message=f"Liquidity validated (spreads <= ${max_spread:.2f}, OI >= {min_oi}).",
            details={"max_spread": max_spread, "min_oi": min_oi}
        )
        gate_results.append(res)
        log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Gate 8: Deterministic Position Sizing (Max 3% Equity Risk Per Trade)
        # ----------------------------------------------------------------------
        # Max loss per 1 contract spread = (width of spread - net credit) * 100
        max_loss_per_contract = float(candidate.get("max_loss", 0.0))
        if max_loss_per_contract <= 0:
            # Fallback estimation based on strike width
            strikes = [float(leg.get("strike", 0.0)) for leg in legs]
            if len(strikes) >= 2:
                width = abs(strikes[0] - strikes[1])
                max_loss_per_contract = max(10.0, (width - net_credit) * 100.0)
            else:
                max_loss_per_contract = 500.0  # Safe conservative fallback

        max_allowed_risk_dollars = equity * self.settings.MAX_EQUITY_RISK_PER_TRADE_PCT

        # Calculate maximum contracts permissible under the 3% cap
        calculated_contracts = int(max_allowed_risk_dollars // max_loss_per_contract)

        # Proposed contracts from LLM or candidate, capped strictly by risk engine
        requested_contracts = candidate.get("contracts", 1)
        final_contracts = min(requested_contracts, calculated_contracts)

        if final_contracts < 1:
            msg = (
                f"Trade rejected: Required capital risk per contract (${max_loss_per_contract:.2f}) "
                f"exceeds 3% equity limit (${max_allowed_risk_dollars:.2f} on ${equity:.2f} equity)."
            )
            res = GateCheckResult(
                gate_name="Gate 8: Position Sizing",
                passed=False,
                message=msg,
                details={"max_loss_per_contract": max_loss_per_contract, "max_allowed_risk": max_allowed_risk_dollars}
            )
            gate_results.append(res)
            log_risk_gate(res.gate_name, res.passed, res.message)
            return RiskEvaluation(
                approved=False,
                rejection_reason=msg,
                allowed_contracts=0,
                gate_results=gate_results
            )

        res = GateCheckResult(
            gate_name="Gate 8: Position Sizing",
            passed=True,
            message=(
                f"Sized to {final_contracts} contract(s). Max risk: ${final_contracts * max_loss_per_contract:.2f} "
                f"<= ${max_allowed_risk_dollars:.2f} (3.0% of ${equity:.2f} equity)."
            ),
            details={
                "contracts": final_contracts,
                "total_risk": final_contracts * max_loss_per_contract,
                "equity_risk_pct": (final_contracts * max_loss_per_contract) / equity if equity > 0 else 0
            }
        )
        gate_results.append(res)
        log_risk_gate(res.gate_name, res.passed, res.message)

        # ----------------------------------------------------------------------
        # Final Verdict: ALL GATES PASSED DETERMINISTICALLY
        # ----------------------------------------------------------------------
        return RiskEvaluation(
            approved=True,
            rejection_reason=None,
            allowed_contracts=final_contracts,
            gate_results=gate_results
        )
