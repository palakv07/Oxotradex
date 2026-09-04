"""Comprehensive Unit Tests for Inviolable Deterministic Risk Gates."""

import pytest
from src.config import Settings
from src.risk import RiskEngine, RiskEvaluation


@pytest.fixture
def mock_settings():
    """Create test settings with standard hackathon thresholds."""
    return Settings(
        TARGET_STARTING_EQUITY=100000.0,
        MAX_EQUITY_RISK_PER_TRADE_PCT=0.03,       # 3% = $3,000
        MAX_CONCURRENT_POSITIONS=5,
        DAILY_LOSS_CIRCUIT_BREAKER_PCT=0.025,    # 2.5% = $2,500
        TAKE_PROFIT_PCT=0.50,
        STOP_LOSS_MULTIPLE=2.0,
        MIN_DTE=7,
        MAX_DTE=45,
        MAX_SHORT_DELTA=0.30,
        MIN_CREDIT=0.20,
        MIN_OPEN_INTEREST=50,
        MAX_BID_ASK_SPREAD=0.25,
        PAPER=True,
        DRY_RUN=True
    )


@pytest.fixture
def valid_candidate():
    """Create a fully compliant 28-DTE Bull Put Spread candidate."""
    return {
        "id": "cand_test_valid",
        "symbol": "SPY",
        "strategy_type": "BULL_PUT_SPREAD",
        "expiration": "2026-10-02",
        "dte": 28,
        "net_credit": 0.85,  # $85 per contract
        "max_loss": 415.0,   # ($5.00 width - $0.85 credit) * 100
        "contracts": 2,
        "legs": [
            {
                "symbol": "SPY261002P00520000",
                "strike": 520.0,
                "type": "put",
                "side": "sell",
                "position_intent": "sell_to_open",
                "ratio_qty": 1,
                "delta": -0.20,
                "bid": 1.25,
                "ask": 1.30,
                "open_interest": 1500,
                "expiration": "2026-10-02"
            },
            {
                "symbol": "SPY261002P00515000",
                "strike": 515.0,
                "type": "put",
                "side": "buy",
                "position_intent": "buy_to_open",
                "ratio_qty": 1,
                "delta": -0.10,
                "bid": 0.40,
                "ask": 0.45,
                "open_interest": 2000,
                "expiration": "2026-10-02"
            }
        ]
    }


def test_valid_trade_passes_all_gates(mock_settings, valid_candidate):
    """Ensure a compliant candidate passes all 8 deterministic gates."""
    engine = RiskEngine(mock_settings)
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=250.0,
        open_positions_count=2,
        kill_switch_active=False,
        circuit_breaker_tripped=False
    )
    assert eval_res.approved is True
    assert eval_res.rejection_reason is None
    assert eval_res.allowed_contracts == 2
    assert len(eval_res.gate_results) == 8


def test_gate1_kill_switch_blocks_trade(mock_settings, valid_candidate):
    """Gate 1: Emergency kill-switch must block all new trade execution."""
    engine = RiskEngine(mock_settings)
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0,
        kill_switch_active=True
    )
    assert eval_res.approved is False
    assert "kill-switch is ACTIVE" in eval_res.rejection_reason
    assert eval_res.allowed_contracts == 0


def test_gate2_daily_circuit_breaker(mock_settings, valid_candidate):
    """Gate 2: Loss >= 2.5% of starting equity ($2,500) must trip circuit breaker."""
    engine = RiskEngine(mock_settings)

    # -2,501 loss on 100k equity trips the breaker
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=97499.0,
        daily_pnl=-2501.0,
        open_positions_count=1
    )
    assert eval_res.approved is False
    assert "Daily loss circuit breaker TRIPPED" in eval_res.rejection_reason
    assert eval_res.allowed_contracts == 0


def test_gate3_max_concurrent_positions(mock_settings, valid_candidate):
    """Gate 3: Open positions count >= 5 must block new trades."""
    engine = RiskEngine(mock_settings)
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=100.0,
        open_positions_count=5  # Cap reached
    )
    assert eval_res.approved is False
    assert "Maximum concurrent positions reached" in eval_res.rejection_reason


def test_gate4_naked_short_options_strictly_rejected(mock_settings):
    """Gate 4: Naked short options (unhedged) must be immediately rejected."""
    engine = RiskEngine(mock_settings)
    naked_candidate = {
        "id": "cand_naked",
        "symbol": "SPY",
        "strategy_type": "NAKED_PUT",
        "net_credit": 2.50,
        "max_loss": 52000.0,
        "legs": [
            {
                "symbol": "SPY261002P00520000",
                "strike": 520.0,
                "type": "put",
                "side": "sell",
                "position_intent": "sell_to_open",
                "delta": -0.20
            }
        ]
    }
    eval_res = engine.evaluate_order(
        candidate=naked_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0
    )
    assert eval_res.approved is False
    assert "Defined-risk spreads require at least 2 legs" in eval_res.rejection_reason


def test_gate5_short_delta_cutoff(mock_settings, valid_candidate):
    """Gate 5: Short leg delta > 0.30 must be rejected."""
    engine = RiskEngine(mock_settings)
    # Set short leg delta to 0.35 (too aggressive)
    valid_candidate["legs"][0]["delta"] = -0.35
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0
    )
    assert eval_res.approved is False
    assert "exceeds maximum allowed threshold of 0.30" in eval_res.rejection_reason


def test_gate6_minimum_credit_rejection(mock_settings, valid_candidate):
    """Gate 6: Net credit below $0.20 must be rejected."""
    engine = RiskEngine(mock_settings)
    valid_candidate["net_credit"] = 0.12  # Below $0.20 minimum
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0
    )
    assert eval_res.approved is False
    assert "below minimum required $0.20" in eval_res.rejection_reason


def test_gate7_liquidity_bid_ask_spread(mock_settings, valid_candidate):
    """Gate 7: Bid-ask spread > $0.25 must be rejected."""
    engine = RiskEngine(mock_settings)
    # Set bid 1.00, ask 1.40 (spread $0.40 > $0.25)
    valid_candidate["legs"][0]["bid"] = 1.00
    valid_candidate["legs"][0]["ask"] = 1.40
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0
    )
    assert eval_res.approved is False
    assert "bid-ask spread $0.40 exceeds max $0.25" in eval_res.rejection_reason


def test_gate8_position_sizing_enforces_3_percent_cap(mock_settings, valid_candidate):
    """Gate 8: Sizing must strictly enforce max 3% equity risk ($3,000 on $100k)."""
    engine = RiskEngine(mock_settings)
    # 3% of $100,000 is $3,000 max risk.
    # Max loss per contract is $415. $3,000 // $415 = 7 contracts.
    # Even if LLM proposes 50 contracts, risk engine MUST cap to 7!
    valid_candidate["contracts"] = 50
    eval_res = engine.evaluate_order(
        candidate=valid_candidate,
        equity=100000.0,
        daily_pnl=0.0,
        open_positions_count=0
    )
    assert eval_res.approved is True
    assert eval_res.allowed_contracts == 7  # 7 * 415 = $2,905 <= $3,000
