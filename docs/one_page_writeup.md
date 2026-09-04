# Oxotradex: Autonomous Options Alpha Agent — Executive Summary & System Write-up

**Submission for:** Alpaca AI Trading Agents Hackathon (lablab.ai × Alpaca)  
**Agent Name:** Oxotradex  
**Strategy Focus:** High-Probability Theta-Harvesting Defined-Risk Options Spreads & Iron Condors  
**Account Baseline:** $100,000 Starting Equity (Alpaca Paper Trading Environment)  
**License:** MIT Open Source  

---

## 1. Executive Summary & Quantitative Edge
**Oxotradex** is an institutional-grade, end-to-end autonomous options trading agent engineered for consistent, positive-expectancy alpha generation via quantitative derivatives underwriting. 

Unlike retail directional betting or unconstrained LLM trading bots that suffer from hallucinated order parameters, **Oxotradex** monetizes the **Volatility Risk Premium (VRP)**—the structural market anomaly where implied volatility persistently exceeds realized volatility over time. By writing defined-risk credit spreads (Bull Put Spreads, Bear Call Spreads) and Iron Condors with 21–35 Days to Expiration (DTE), Oxotradex systematically captures accelerated non-linear time decay ($\Theta$), while completely bounding tail loss via protective long options wings.

---

## 2. Hybrid AI Reasoning + Inviolable Deterministic Risk Architecture
A core engineering breakthrough of this agent is its **strict decoupling of tactical intelligence from risk invariant enforcement**:

```
[ Market Data & Regime ] ──> [ LLM Tactical Reasoner ] ──> [ Inviolable Python Risk Engine ] ──> [ Alpaca Broker / MCP ]
(EMA, RSI, HV20, Chains)       (Gemini / Claude / GPT)        (8 Hard Deterministic Gates)          (Multi-Leg MLEG Orders)
```

1. **Market Regime Detection**: Quantitative indicators (20/50 EMA crossover, 14-period RSI, 20-day Historical Volatility) categorize the underlying regime into `BULLISH`, `BEARISH`, or `NEUTRAL` (Chop).
2. **Candidate Generation**: Generates strictly liquid, defined-risk candidate spreads on high-volume underlyings (`SPY`, `QQQ`, `IWM`, `AAPL`, `MSFT`, `NVDA`) with short leg deltas $\le 0.30$.
3. **Structured LLM Reasoner**: An institutional LLM prompt evaluates market context and returns a strict JSON payload proposing high-conviction trade entries.
4. **Deterministic Risk Gates (100% Un-bypassable)**: Under no circumstances can the LLM bypass these programmatic safety invariants:
   - **Gate 1 (Kill-Switch)**: Immediate halt if manual or programmatic kill switch is engaged.
   - **Gate 2 (Daily Loss Circuit Breaker)**: If cumulative daily loss reaches $-2.5\%$ ($- \$2,500$ on $\$100\text{k}$ equity), all new entries are halted for the remainder of the session.
   - **Gate 3 (Capacity Limit)**: Max 5 concurrent open positions.
   - **Gate 4 (Defined Risk Only)**: Every short option leg must be backed by a long protective wing; naked options are rejected.
   - **Gate 5 (Delta Cutoff)**: Short leg $|\Delta| \le 0.30$.
   - **Gate 6 (Minimum Credit)**: Net credit $\ge \$0.20$ per share ($\$20/\text{contract}$).
   - **Gate 7 (Liquidity Filter)**: Bid-ask spread $\le \$0.25$, Open Interest $\ge 50$.
   - **Gate 8 (Capital Sizing)**: Contract quantities are dynamically sized so max trade risk never exceeds $\le 3.0\%$ of total equity ($\le \$3,000$).

---

## 3. Position Lifecycle & Dynamic Risk Management
Open positions are continuously monitored by the **Position Manager**:
- **Take Profit (TP)**: Automatically closes positions at **50% of maximum credit received**, maximizing capital turnover and minimizing duration risk.
- **Stop Loss (SL)**: Closes positions if current cost reaches **2.0× initial credit received** to cap adverse market moves.
- **Time-Based Exit**: Liquidates spreads when $\text{DTE} \le 1$ day to completely avoid Friday expiration pin risk and assignment friction.

---

## 4. Alpaca MCP & Trading API Integration
- **Alpaca MCP Native Support**: Connects to the official `@alpacahq/alpaca-mcp-server` protocol for standardized tool dispatch (`get_account`, `get_clock`, `place_option_order`).
- **Resilient Multi-Leg Execution**: Leverages `alpaca-py` `OrderClass.MLEG` limit orders to atomically execute complex 2-leg and 4-leg option spreads.
- **Dry-Run Simulation**: Supports instantaneous offline and zero-risk dry-run testing with SQLite audit persistence.
- **Real-Time Streamlit Dashboard**: Provides full institutional observability into equity curves, active positions, Greeks, circuit-breaker headroom, and an AI decision audit log.
