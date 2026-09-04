# Slide Presentation: Alpaca Autonomous Options Alpha Agent

*Presentation Deck for the Alpaca AI Trading Agents Hackathon (lablab.ai × Alpaca)*  
*Presenter / Author: Quant AI Team*  
*Theme: Institutional Quant AI × Deterministic Risk Invariants*

---

## Slide 1: Title Slide (The Hook)
- **Title:** Alpaca Autonomous Options Alpha Agent
- **Subtitle:** Monetizing the Volatility Risk Premium via AI Tactical Selection & Inviolable Risk Invariants
- **Visual:** Terminal UI graphic with live theta decay curve ($\Theta$) and green candlestick overlay ([cover_image.jpg](cover_image.jpg)).
- **Key Stats:**
  - Initial Starting Equity: **$100,000.00 (Alpaca Paper)**
  - Core Focus: **Multi-Leg Credit Spreads & Iron Condors**
  - Architecture: **Hybrid AI Reasoner + 8 Deterministic Python Risk Gates**

---

## Slide 2: The Problem with AI Trading Agents
- **Headline:** Why 95% of LLM Trading Bots Fail in Production
- **Bullet Points:**
  - **Directional Hallucination:** LLMs attempting directional equity prediction (buy/sell stock) perform barely better than a coin flip ($~50\%$ win rate) after slippage and commissions.
  - **Catastrophic Unbounded Risk:** Traditional agent frameworks allow the LLM to directly place trades without hard-coded circuit breakers, risking margin calls on black swan volatility spikes.
  - **Execution Friction:** Most retail AI agents cannot handle multi-leg derivatives execution, missing the institutional edge of structured options.

---

## Slide 3: The Quantitative Edge: Volatility Risk Premium (VRP)
- **Headline:** Turning Time Decay ($\Theta$) into Systematic Alpha
- **The Core Thesis:** Implied Volatility ($IV$) persistently trades at a premium over Realized Volatility ($RV$).
- **The Strategy:**
  - Instead of guessing price direction, we **underwrite probability**.
  - We systematically sell out-of-the-money (OTM) credit spreads (Bull Put Spreads, Bear Call Spreads) and Iron Condors with 21–35 Days to Expiration (DTE).
  - Short leg deltas: $|\Delta| \le 0.30$ ($\approx 70\%-85\%$ statistical probability of expiring out-of-the-money).
  - Defined Risk: Every short option is backed by a protective long wing—**zero naked exposure**.

---

## Slide 4: System Architecture: Strict Separation of Concerns
- **Headline:** AI Proposes, Deterministic Python Enforces
- **Diagram:**
  ```
  [Market Data Layer] ──> [Strategy Engine] ──> [Structured LLM Layer] ──> [8 Deterministic Risk Gates] ──> [Alpaca Broker / MCP]
  (Bars, Chains, Greeks)   (EMA, RSI, HV20)      (Strict JSON Reasoner)      (CANNOT BE OVERRIDDEN)       (Atomic MLEG Execution)
  ```
- **Key Architectural Insight:**
  - The LLM is **never** given execution keys or allowed to calculate order sizing.
  - It acts purely as a tactical selector from an algorithmically pre-filtered pool of compliant defined-risk setups.

---

## Slide 5: The 8 Inviolable Deterministic Risk Gates
- **Headline:** Hardcoded Safety Invariants (100% Un-bypassable in Python)
- **Table:**
  - **Gate 1: Emergency Kill-Switch:** Instantly stops all order placement.
  - **Gate 2: Daily Circuit Breaker:** Cumulative daily PnL $\le -2.5\%$ ($-\$2,500$ on $\$100\text{k}$) halts trading for the session.
  - **Gate 3: Capacity Limit:** Strictly enforces a maximum of 5 concurrent open positions.
  - **Gate 4: Defined-Risk Invariant:** All short options must be hedged by long wings (no naked options).
  - **Gate 5: Delta Limit:** Short option $|\Delta| \le 0.30$.
  - **Gate 6: Minimum Credit:** Minimum net credit $\ge \$0.20$ per share ($\$20/\text{contract}$).
  - **Gate 7: Liquidity Check:** Bid-ask spread $\le \$0.25$, open interest $\ge 50$.
  - **Gate 8: Capital Sizing:** Dynamically bounds contract size so total risk never exceeds $\le 3.0\%$ of equity ($-\$3,000$).

---

## Slide 6: Theta Lifecycle & Position Management
- **Headline:** Disciplined Trade Management Over Hope
- **Rules Enforced Automatically:**
  - **Take Profit (TP) at 50%:** Closes spread when 50% of the initial credit is captured (harvests the steepest portion of the theta curve, freeing capital).
  - **Stop Loss (SL) at 2.0x Credit:** Cuts losing trades when current cost to close reaches 2.0x credit received, preventing tail blowouts.
  - **DTE Expiry Exit ($\le 1$ Day):** Exits spreads before the final expiration Friday to eliminate assignment friction and pin risk.

---

## Slide 7: Alpaca Technology Stack & MCP Integration
- **Headline:** Deep Integration with Alpaca Ecosystem
- **Alpaca MCP Server:** Native tool mapping to official `@alpacahq/alpaca-mcp-server` (`get_account`, `get_clock`, `place_option_order`).
- **Alpaca Trading API:** Utilizes `alpaca-py` with `OrderClass.MLEG` (multi-leg) to place atomic multi-leg orders with defined limit credit prices.
- **Dual-Mode Execution:** Zero-downtime transition between live paper trading and offline dry-run simulation.
- **Local Persistence:** SQLite database (`trades`, `decisions`, `daily_snapshots`, `system_state`) ensures the agent can reboot seamlessly without losing state.

---

## Slide 8: Real-Time Streamlit Dashboard & Observability
- **Headline:** Institutional Quant Control Room
- **Features:**
  - Real-time Portfolio Equity, Buying Power, and Today's PnL KPI cards.
  - Circuit Breaker Distance Gauge (visualizes distance to $-2.5\%$ trip point).
  - Active Spreads Table displaying strikes, entry credit, current mark, unrealized PnL, and theta harvested %.
  - Complete AI Decision Audit Trail showing raw LLM outputs alongside individual risk gate verification results.
  - One-Click Emergency Kill-Switch toggle and manual scan trigger.

---

## Slide 9: Verification & Live Test Results
- **Headline:** Validated, Tested, and Production-Ready
- **Unit Test Suite:**
  - `python -m pytest tests/test_risk.py -v` $\to$ **9/9 tests passing (100%) in 0.16 seconds**.
- **Execution Cycles:**
  - Tested on clean $100,000.00 paper equity baseline.
  - Automated detection of market regime on `SPY`, `QQQ`, `IWM`.
  - Seamless candidate generation, LLM reasoning, risk gate sizing, and multi-leg order execution.
  - Verified capacity throttle at 5 concurrent positions and emergency kill-switch blocking.

---

## Slide 10: Conclusion & Hackathon Submission
- **Headline:** An Institutional Framework for Autonomous Trading
- **Summary:**
  - Solves the core flaw of AI trading by enforcing hard mathematical invariants.
  - Captures proven structural alpha (Theta decay / VRP) on liquid index ETFs.
  - Complete, MIT-licensed open-source codebase ready for public GitHub.
- **Links & Resources:**
  - GitHub Repo: `https://github.com/your-username/alpaca-options-alpha-agent`
  - Documentation: [docs/one_page_writeup.md](one_page_writeup.md)
  - Dashboard: `streamlit run src/dashboard.py`
