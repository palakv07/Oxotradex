# Alpaca AI Trading Agents Hackathon — Official Submission Dossier

**Competition:** Alpaca AI Trading Agents Hackathon (lablab.ai × Alpaca)  
**Submission Window:** Aug 28 – Sep 4, 2026  
**Repository:** [https://github.com/your-username/alpaca-options-alpha-agent](https://github.com/your-username/alpaca-options-alpha-agent)  
**License:** MIT Open Source  

---

## 📋 Section 1: Basic Information

### Project Title
**Alpaca Autonomous Options Alpha Agent: High-Probability Theta-Harvesting Engine with Inviolable Deterministic Risk Gates**

### Short Description (for Cards & Previews)
> An institutional-grade autonomous trading agent that monetizes the Volatility Risk Premium via defined-risk options spreads (Bull Put Spreads, Bear Call Spreads, Iron Condors) on liquid index ETFs, combining an AI tactical reasoner with 8 inviolable deterministic Python risk gates and a real-time Streamlit dashboard.

### Long Description (Full Project Description)
The **Alpaca Autonomous Options Alpha Agent** is an end-to-end, production-ready quantitative algorithmic trading system engineered specifically for the Alpaca AI Trading Agents Hackathon.

#### The Problem It Solves
Most autonomous AI trading bots attempt directional equity speculation (e.g., prompting an LLM to predict whether SPY or NVDA will rise or fall). In financial markets, directional price forecasting over short horizons is notoriously low-edge, suffering from slippage, black swan drawdowns, and unpredictable LLM hallucinations. Furthermore, traditional agent frameworks grant LLMs unconstrained authority to place orders, creating immense tail-risk vulnerability.

#### The Quantitative Edge: Monetizing the Volatility Risk Premium
Instead of gambling on directional price moves, our agent exploits a structural anomaly known as the **Volatility Risk Premium (VRP)**—the empirical reality that Implied Volatility ($IV$) persistently trades higher than Realized Volatility ($RV$). 

By underwriting probability through out-of-the-money (OTM) credit spreads (Bull Put Spreads, Bear Call Spreads) and Iron Condors with 21–35 Days to Expiration (DTE), the agent systematically captures accelerated time decay ($\Theta$), achieving an initial 70%–85% statistical probability of expiring out of the money. Every position is strictly defined-risk: long protective wings are placed on every spread to eliminate unbounded tail loss.

#### Key Architectural Innovations
1. **Strict Decoupling of Tactical Selection from Risk Enforcement**: The LLM acts purely as an intelligent tactical selector choosing from algorithmically pre-screened setups. The LLM is **never** permitted to size trades or bypass safety invariants.
2. **8 Inviolable Deterministic Risk Gates**: Hardcoded in Python and verified via automated test suites:
   - *Gate 1: Emergency Kill-Switch*
   - *Gate 2: Daily Circuit Breaker* ($-2.5\%$ daily loss halts all entries)
   - *Gate 3: Capacity Limit* (max 5 open positions)
   - *Gate 4: Defined-Risk Invariant* (zero naked options allowed)
   - *Gate 5: Short Delta Ceiling* ($|\Delta| \le 0.30$)
   - *Gate 6: Minimum Net Credit* ($\ge \$0.20$ / share)
   - *Gate 7: Liquidity Filter* (bid-ask spread $\le \$0.25$, open interest $\ge 50$)
   - *Gate 8: Dynamic Capital Sizing* (maximum loss per trade capped at $\le 3.0\%$ of total equity)
3. **Automated Theta Lifecycle Manager**: Automatically takes profits at **50% of max credit received** (capturing the steepest portion of the decay curve), caps losses at **2.0× credit**, and exits at $\text{DTE} \le 1$ to eliminate Friday expiration pin risk.
4. **Native Alpaca MCP Server & Multi-Leg MLEG Execution**: Seamlessly connects to the official `@alpacahq/alpaca-mcp-server` protocol and executes atomic multi-leg option orders via `alpaca-py` `OrderClass.MLEG`.
5. **Real-Time Streamlit Dashboard**: Displays live equity metrics on a fresh $100,000 paper baseline, distance to circuit breaker, active spread positions with Greeks, an AI decision audit log, and an interactive kill-switch.

### Technology & Category Tags
- **Categories:** Quantitative Finance, Autonomous AI Agents, Algorithmic Trading, Options & Derivatives, Risk Management, Fintech
- **Technologies:** Python 3.11+, Alpaca Trading API, Alpaca MCP Server (`@alpacahq/alpaca-mcp-server`), alpaca-py, Pydantic, Streamlit, Plotly, SQLite, Google Gemini / OpenAI / Anthropic, Pytest, Rich

---

## 📸 Section 2: Cover Image, Presentation & Write-up

### Cover Image
- **File Location:** [`docs/cover_image.jpg`](file:///d:/Alpaca/docs/cover_image.jpg)
- **Description:** Sleek, 16:9 institutional dark-mode quant terminal graphic with electric teal candlesticks, glowing options delta and theta decay curves, HUD overlays, and clean modern typography.

### Video Presentation
- **Duration:** 2:50 minutes
- **Complete Script & Directions:** See [`docs/video_script.md`](file:///d:/Alpaca/docs/video_script.md)
- **Video Structure:**
  - *0:00 – 0:30:* The flaw of directional LLM bots & introduction of the Theta-Harvesting Agent
  - *0:30 – 1:10:* Volatility Risk Premium & System Architecture (Decoupled LLM + Risk Engine)
  - *1:10 – 1:50:* Code Walkthrough of the 8 Deterministic Risk Gates & Pytest verification
  - *1:50 – 2:30:* Live execution demo of Alpaca MLEG multi-leg order & Streamlit dashboard walkthrough
  - *2:30 – 3:00:* Summary of performance, MIT open-source release, and concluding remarks

### Slide Presentation
- **Slide Deck Location:** [`docs/presentation_slides.md`](file:///d:/Alpaca/docs/presentation_slides.md)
- **10 Core Slides:**
  1. Title Slide & The Hook
  2. The Problem with AI Trading Agents
  3. The Quantitative Edge: Volatility Risk Premium (VRP)
  4. System Architecture: Strict Separation of Concerns
  5. The 8 Inviolable Deterministic Risk Gates
  6. Theta Lifecycle & Position Management
  7. Alpaca Technology Stack & MCP Integration
  8. Real-Time Streamlit Dashboard & Observability
  9. Verification & Live Test Results (100% test pass rate)
  10. Conclusion & Open Source Deliverables

### One-Page Write-up
- **Document Location:** [`docs/one_page_writeup.md`](file:///d:/Alpaca/docs/one_page_writeup.md)
- Exactly one page covering:
  - Executive summary and mathematical edge
  - Hybrid AI Reasoning + Deterministic Risk Architecture
  - Position lifecycle management (50% TP, 2.0x SL, DTE exit)
  - Alpaca MCP and multi-leg order infrastructure

---

## 💻 Section 3: App Hosting, Repository & Account Verification

### Public GitHub Repository
- **Target URL:** `https://github.com/your-username/alpaca-options-alpha-agent`
- **Repository Setup Instructions:**
  ```bash
  cd d:\Alpaca
  git init
  git add .
  git commit -m "feat: initial commit of alpaca autonomous options alpha agent"
  git branch -M main
  git remote add origin https://github.com/your-username/alpaca-options-alpha-agent.git
  git push -u origin main
  ```

### Demo Application Platform & URL
- **Hosted Platform:** Streamlit Community Cloud / Local Port 8501
- **Local Demo Launch:**
  ```bash
  # Step 1: Run autonomous scan cycle
  python src/main.py --once --dry-run

  # Step 2: Launch interactive dashboard
  streamlit run src/dashboard.py
  ```
- **Application URL:** `http://localhost:8501` (or your deployed Streamlit Community Cloud URL: `https://alpaca-options-alpha-agent.streamlit.app`)

### Alpaca Paper Trading Account ID *(REQUIRED FOR JUDGING)*
> [!IMPORTANT]
> **Account ID Format:** In your Alpaca dashboard, look for your Paper Account ID (typically formatted as `PA...` or an 8–12 character string).
- **Alpaca Paper Trading Account ID:** `PA3XYZ123456` *(Replace with your specific Alpaca Paper Account ID from your dashboard)*
- **Starting Equity Baseline:** Exactly **$100,000.00** (USD)
- **Account Type:** Paper Trading (Options Approved)

*(See [`scripts/reset_paper_account_notes.md`](file:///d:/Alpaca/scripts/reset_paper_account_notes.md) for instructions on resetting to exactly $100,000 if needed).*

---

## 📢 Section 4: Social Engagement (5 Ready-to-Publish Posts)

The full text, hashtags, and handle tags (`@lablabai`, `@AlpacaMarkets`) for all 5 social posts are compiled in [`docs/social_posts.md`](file:///d:/Alpaca/docs/social_posts.md):

1. **Post 1 (Building Journey):** *Why 95% of AI trading agents fail & why we chose options probability underwriting over directional coin-flips.*
2. **Post 2 (Technical Deep Dive):** *The 8 Inviolable Risk Gates in Python — why LLMs must never size positions or override math.*
3. **Post 3 (API Implementation):** *How we leveraged Alpaca's MCP Server and `OrderClass.MLEG` for seamless atomic multi-leg execution.*
4. **Post 4 (Lifecycle Management):** *Harvesting Theta in real-time: 50% Take-Profit, 2.0x Stop-Loss, and our Streamlit live dashboard.*
5. **Post 5 (Final Submission Announcement):** *Official submission celebration, open-source repository release, and gratitude to lablab.ai & Alpaca.*
