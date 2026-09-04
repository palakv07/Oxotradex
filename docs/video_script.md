# Video Presentation Script: Oxotradex — Autonomous Options Alpha Agent

**Target Duration:** 2:45 – 3:00 minutes  
**Format:** Screen recording + Voiceover (or webcam in corner)  
**Hackathon:** Alpaca AI Trading Agents Hackathon (lablab.ai × Alpaca)  

---

### [0:00 – 0:30] Introduction & The Core Problem
**Visual on Screen:**  
*Show Cover Graphic ([cover_image.jpg](cover_image.jpg)), followed by Slide 2 ("Why 95% of AI Trading Bots Fail").*

**Voiceover / Speaker:**  
> "Hi everyone, welcome to our submission for the Alpaca AI Trading Agents Hackathon: **Oxotradex**, an autonomous options alpha agent.
> 
> Most AI trading agents fail because they attempt directional stock prediction—which is essentially a coin flip—and they grant unconstrained LLMs direct access to order execution. One hallucination or black swan volatility spike, and the entire portfolio blows up.
> 
> We took an institutional quantitative approach: instead of guessing stock direction, **Oxotradex** underwrites probability by monetizing the **Volatility Risk Premium** through defined-risk options spreads on liquid index ETFs like SPY, QQQ, and IWM. Most importantly, all trades are governed by **8 inviolable deterministic Python risk gates** that the AI can never override."

---

### [0:30 – 1:10] The Architecture & The Quantitative Edge
**Visual on Screen:**  
*Show Slide 4 (Architecture Diagram) and highlight the separation between the LLM Tactical Reasoner and the Deterministic Risk Engine.*

**Voiceover / Speaker:**  
> "Here is how the architecture works:
> 
> Every 15 minutes during market hours, our quantitative strategy layer ingests daily bars, EMA crossovers, 14-period RSI, and 20-day historical volatility. If the regime is neutral or range-bound, it generates Iron Condors. If it is trending, it generates Bull Put or Bear Call Spreads.
> 
> The candidate pool is pre-filtered for high liquidity and safe deltas—under 0.30—representing an initial 70 to 85 percent probability of expiring out of the money.
> 
> We then pass this structured context to our LLM tactical reasoner—powered by Google Gemini or Claude—which returns a strict JSON proposal explaining its conviction.
> 
> But the AI does not get to place the trade."

---

### [1:10 – 1:50] The 8 Inviolable Risk Gates (Code Invariants)
**Visual on Screen:**  
*Switch to VS Code showing [src/risk.py](file:///d:/Alpaca/src/risk.py) and run `pytest tests/test_risk.py -v` in terminal showing all 9 tests passing green.*

**Voiceover / Speaker:**  
> "Before any order reaches Alpaca, it must pass through 8 hardcoded Python risk gates.
> 
> Gate 1 checks the global kill-switch.  
> Gate 2 enforces a strict daily loss circuit breaker: if daily losses reach -2.5% of starting equity—which is -$2,500 on our $100k paper account—all new entries are halted for the day.  
> Gate 3 enforces a 5-position concurrent limit.  
> Gate 4 guarantees defined risk: naked options are mathematically impossible in our codebase.  
> Gate 5 enforces our 0.30 short delta ceiling.  
> Gate 6 and 7 require a minimum credit of $0.20 and tight bid-ask spreads.  
> And Gate 8 dynamically sizes the position so that the maximum possible loss per trade never exceeds 3% of our equity.
> 
> As you can see in our test suite, all 9 unit tests pass in under 0.2 seconds."

---

### [1:50 – 2:30] Live Execution & Streamlit Dashboard Demo
**Visual on Screen:**  
*Switch to Terminal running `python src/main.py --once --dry-run` to show rich formatted table logs and atomic multi-leg execution. Then switch to the browser displaying [src/dashboard.py](file:///d:/Alpaca/src/dashboard.py).*

**Voiceover / Speaker:**  
> "Let's see it in action. In the terminal, running an autonomous cycle shows market regime analysis, candidate generation, structured LLM reasoning, and verified execution of an atomic multi-leg order using Alpaca's `OrderClass.MLEG`.
> 
> Now let's look at our real-time Streamlit dashboard.  
> At the top, we track our live portfolio equity on our fresh $100,000 paper baseline, today's P&L, buying power, and our daily circuit breaker distance meter.  
> 
> Below, our Active Spreads table displays each trade's strikes, Greeks, entry credit, current liquidation mark, and percentage of theta harvested. Our Position Manager automatically takes profit at 50% max credit, cuts losses at 2.0x credit, and exits near expiration to eliminate pin risk.
> 
> We also provide an AI Decision Audit Log where judges can review the raw LLM output alongside each gate's pass or blocked verdict, plus an interactive Emergency Kill-Switch button."

---

### [2:30 – 3:00] Conclusion & Why It Wins
**Visual on Screen:**  
*Show Slide 10 (Summary) and GitHub Repository ([README.md](file:///d:/Alpaca/README.md)).*

**Voiceover / Speaker:**  
> "To summarize:
> - We deployed proven, positive-expectancy options math over retail directional gambling.
> - We integrated natively with Alpaca's Trading API, MCP Server protocol, and multi-leg order execution.
> - We engineered 100% un-bypassable risk gates that keep capital safe.
> - And the entire project is clean, documented, MIT-licensed, and running live on a $100,000 Alpaca paper account.
> 
> Thank you to lablab.ai and Alpaca for hosting this incredible hackathon. Check out our public repository and try the agent yourself!"
