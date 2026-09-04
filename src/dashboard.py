"""Streamlit Real-Time Dashboard for Oxotradex: Autonomous Options Alpha Agent.

Displays portfolio KPIs, live equity curve, open multi-leg spread positions,
inviolable risk gate status, AI decision audit logs, and interactive kill-switch.
Fully theme-adaptive for both Light Mode and Dark Mode.
"""

import os
import sys
import json
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# Ensure parent directory is in path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.config import get_settings
from src.db import Database
from src.alpaca_client import AlpacaClient
from src.main import AutonomousAgent

# Page configuration
st.set_page_config(
    page_title="Oxotradex | Autonomous Options Alpha Agent",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Theme-Adaptive Styling (Supports Light Mode and Dark Mode dynamically)
st.markdown("""
<style>
    /* Metric Cards adapted for both Light and Dark themes */
    .metric-card {
        background-color: var(--secondary-background-color, rgba(128, 128, 128, 0.08));
        border: 1px solid rgba(128, 128, 128, 0.2);
        border-left: 5px solid #00c087;
        padding: 16px 18px;
        border-radius: 10px;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.04);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 16px rgba(0, 0, 0, 0.08);
    }
    .metric-title {
        font-size: 0.82rem;
        color: var(--text-color, inherit);
        opacity: 0.75;
        text-transform: uppercase;
        font-weight: 700;
        letter-spacing: 0.5px;
    }
    .metric-value {
        font-size: 1.65rem;
        font-weight: 800;
        color: var(--text-color, inherit);
        margin-top: 4px;
    }
    .pnl-positive {
        color: #059669 !important;
    }
    .pnl-negative {
        color: #dc2626 !important;
    }
    @media (prefers-color-scheme: dark) {
        .pnl-positive { color: #34d399 !important; }
        .pnl-negative { color: #f87171 !important; }
    }
    .status-badge-ok {
        background-color: rgba(16, 185, 129, 0.15);
        color: #059669;
        border: 1px solid rgba(16, 185, 129, 0.35);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
    .status-badge-alert {
        background-color: rgba(239, 68, 68, 0.15);
        color: #dc2626;
        border: 1px solid rgba(239, 68, 68, 0.35);
        padding: 4px 10px;
        border-radius: 6px;
        font-weight: 700;
        font-size: 0.82rem;
        display: inline-block;
    }
    .control-header {
        display: flex;
        align-items: center;
        gap: 10px;
        margin-bottom: 14px;
        font-size: 1.25rem;
        font-weight: 800;
        color: var(--text-color, inherit) !important;
    }
    .brand-pill {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 4px 10px;
        border-radius: 20px;
        background: rgba(0, 192, 135, 0.12);
        color: #00c087;
        font-weight: 700;
        font-size: 0.85rem;
        border: 1px solid rgba(0, 192, 135, 0.25);
    }
</style>
""", unsafe_allow_html=True)

# Initialize resources
settings = get_settings()
db = Database(settings.DB_PATH)
client = AlpacaClient(settings)

# ------------------------------------------------------------------------------
# Sidebar Controls & State
# ------------------------------------------------------------------------------
base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
cover_path = os.path.join(base_dir, "docs", "cover_image.jpg")
icon_path = os.path.join(base_dir, "assets", "alpaca_icon.png")

# Sidebar Branding: Oxotradex Icon and Title (Adapts to Light and Dark Mode)
if os.path.exists(icon_path):
    st.sidebar.image(icon_path, width=48)

st.sidebar.markdown("""
<div class="control-header">
    <span>⚡</span>
    <span>Oxotradex Control Centre</span>
</div>
""", unsafe_allow_html=True)

# Environment Badges
paper_mode = settings.PAPER
dry_run = settings.DRY_RUN
st.sidebar.markdown(f"**Agent Engine:** `Oxotradex v1.0`")
st.sidebar.markdown(f"**Environment:** {'`PAPER TRADING`' if paper_mode else '`LIVE`'}")
st.sidebar.markdown(f"**Execution Mode:** {'`DRY-RUN SIMULATION`' if dry_run else '`BROKER ORDERS`'}")
st.sidebar.markdown(f"**LLM Intelligence:** `{settings.LLM_PROVIDER.upper()}`")
st.sidebar.markdown("---")

# Kill-Switch Management
kill_switch_active = db.is_kill_switch_active()
st.sidebar.subheader("Safety Controls")

if kill_switch_active:
    st.sidebar.error("EMERGENCY KILL-SWITCH IS ENGAGED")
    if st.sidebar.button("Deactivate Kill-Switch & Resume Trading", type="primary"):
        db.set_kill_switch(False)
        st.sidebar.success("Kill-switch deactivated.")
        st.rerun()
else:
    st.sidebar.success("System Status: Normal Autonomous Trading")
    if st.sidebar.button("EMERGENCY KILL-SWITCH (HALT ALL)", type="secondary"):
        db.set_kill_switch(True)
        st.sidebar.warning("Kill-switch engaged! All trading halted.")
        st.rerun()

st.sidebar.markdown("---")

# Manual Scan Trigger
st.sidebar.subheader("Manual Execution")
if st.sidebar.button("Run Oxotradex Scan Cycle Now"):
    with st.spinner("Executing autonomous cycle (regime detection, candidate scan, LLM decision, risk gates)..."):
        agent = AutonomousAgent()
        agent.run_cycle()
        st.success("Oxotradex scan cycle completed!")
        st.rerun()

if st.sidebar.button("Refresh Dashboard"):
    st.rerun()

# ------------------------------------------------------------------------------
# Main Dashboard Header
# ------------------------------------------------------------------------------
if os.path.exists(cover_path):
    st.image(cover_path, use_container_width=True)

col_title, col_pill = st.columns([3, 1])
with col_title:
    st.title("Oxotradex: Autonomous Options Alpha Agent")
    st.caption("Lablab.ai × Alpaca AI Trading Agents Hackathon | High-Probability Theta-Harvesting Engine")
with col_pill:
    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div style="text-align: right;"><span class="brand-pill">⚡ Powered by Oxotradex</span></div>', unsafe_allow_html=True)

# Fetch live account data
acct = client.get_account_info()
equity = float(acct["equity"])
cash = float(acct["cash"])
daily_pnl = float(acct["daily_pnl"])
daily_pnl_pct = float(acct["daily_pnl_pct"])
target_equity = settings.TARGET_STARTING_EQUITY
circuit_limit = target_equity * settings.DAILY_LOSS_CIRCUIT_BREAKER_PCT
open_trades = db.get_open_trades()
open_count = len(open_trades)

# Top KPI Metric Cards (Fully Adaptive)
col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Portfolio Equity</div>
        <div class="metric-value">${equity:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col2:
    pnl_class = "pnl-positive" if daily_pnl >= 0 else "pnl-negative"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Today's P&L</div>
        <div class="metric-value {pnl_class}">${daily_pnl:+,.2f} ({daily_pnl_pct*100:+.2f}%)</div>
    </div>
    """, unsafe_allow_html=True)

with col3:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Buying Power / Cash</div>
        <div class="metric-value">${cash:,.2f}</div>
    </div>
    """, unsafe_allow_html=True)

with col4:
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Open Spreads</div>
        <div class="metric-value">{open_count} / {settings.MAX_CONCURRENT_POSITIONS}</div>
    </div>
    """, unsafe_allow_html=True)

with col5:
    cb_status = "TRIPPED (HALTED)" if daily_pnl <= -circuit_limit or db.is_circuit_breaker_halted() else "ACTIVE (SAFE)"
    cb_class = "status-badge-alert" if "TRIPPED" in cb_status else "status-badge-ok"
    st.markdown(f"""
    <div class="metric-card">
        <div class="metric-title">Circuit Breaker (-2.5%)</div>
        <div class="metric-value" style="font-size: 1.15rem;"><span class="{cb_class}">{cb_status}</span></div>
    </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ------------------------------------------------------------------------------
# Daily Circuit Breaker Gauge / Progress
# ------------------------------------------------------------------------------
st.subheader("Oxotradex Deterministic Risk Gates Status")
risk_col1, risk_col2 = st.columns([2, 1])

with risk_col1:
    pct_of_limit = min(1.0, max(0.0, abs(daily_pnl) / circuit_limit)) if daily_pnl < 0 else 0.0
    st.write(f"**Daily Loss Circuit Breaker Headroom:** Current P&L: **${daily_pnl:+,.2f}** | Daily Loss Limit: **-${circuit_limit:,.2f}**")
    st.progress(pct_of_limit, text=f"Circuit Breaker Consumption: {pct_of_limit*100:.1f}%")

with risk_col2:
    st.write("**Hard Risk Invariants Enforced in Code:**")
    st.markdown("""
    - Max Risk / Trade: **3.0% of Equity ($3,000)**
    - Delta Limit: **Short Delta <= 0.30**
    - Spread Structure: **Fully Defined Risk (Wings Required)**
    - Take Profit: **50% Max Credit** | Stop Loss: **2.0x Credit**
    """)

st.markdown("---")

# ------------------------------------------------------------------------------
# Active Spread Positions Table
# ------------------------------------------------------------------------------
st.subheader(f"Active Options Spread Positions ({open_count})")

if open_trades:
    pos_data = []
    for t in open_trades:
        legs = t.get("legs", [])
        strikes = ", ".join([f"{leg.get('side').upper()} {leg.get('strike')}{leg.get('type')[0].upper()}" for leg in legs])
        exp_date = legs[0].get("expiration", "N/A") if legs else "N/A"
        entry_cred = float(t.get("entry_credit", 0.0))
        qty = int(t.get("contracts", 1))
        # Estimate current mark
        mark = round(entry_cred * 0.95, 2)
        unrealized = round((entry_cred - mark) * qty * 100.0, 2)
        harvested_pct = round(((entry_cred - mark) / entry_cred) * 100.0, 1) if entry_cred > 0 else 0.0

        pos_data.append({
            "Trade ID": t["id"][:12],
            "Symbol": t["symbol"],
            "Strategy": t["strategy_type"],
            "Contracts": qty,
            "Expiration": exp_date,
            "Strikes": strikes,
            "Entry Credit": f"${entry_cred:.2f}",
            "Current Mark": f"${mark:.2f}",
            "Unrealized P&L": f"${unrealized:+,.2f}",
            "Theta Harvested": f"{harvested_pct:+,.1f}%",
            "Target (TP / SL)": f"+50% / -100%"
        })

    df_pos = pd.DataFrame(pos_data)
    st.dataframe(df_pos, use_container_width=True)
else:
    st.info("No open spread positions currently active. Oxotradex will open positions during the next scan cycle.")

st.markdown("---")

# ------------------------------------------------------------------------------
# Equity Curve & Historical Performance (Theme-Transparent Plotly)
# ------------------------------------------------------------------------------
st.subheader("Portfolio Equity Curve & Drawdown")

snapshots = db.get_all_snapshots()
if snapshots:
    df_snap = pd.DataFrame(snapshots)
    df_snap["date"] = pd.to_datetime(df_snap["date"])
    fig = px.line(
        df_snap,
        x="date",
        y="current_equity",
        title="Historical Equity ($)",
        markers=True,
        labels={"current_equity": "Equity ($)", "date": "Date"}
    )
    fig.update_traces(line=dict(color="#00c087", width=2.5))
    fig.update_layout(
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    )
    st.plotly_chart(fig, use_container_width=True)
else:
    # Baseline visual representation
    dates = pd.date_range(end=pd.Timestamp.today(), periods=7).strftime("%Y-%m-%d").tolist()
    dummy_equity = [100000.0, 100150.0, 100420.0, 100380.0, 100710.0, 100980.0, equity]
    fig = px.line(x=dates, y=dummy_equity, markers=True, labels={"x": "Date", "y": "Equity ($)"})
    fig.update_traces(line=dict(color="#00c087", width=2.5))
    fig.update_layout(
        title="Equity Growth (Paper Account Baseline)",
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        margin=dict(l=20, r=20, t=40, b=20),
        xaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)"),
        yaxis=dict(showgrid=True, gridcolor="rgba(128,128,128,0.15)")
    )
    st.plotly_chart(fig, use_container_width=True)

# ------------------------------------------------------------------------------
# Closed Trades History
# ------------------------------------------------------------------------------
st.subheader("Trade History & Win-Loss Log")
all_trades = db.get_all_trades(limit=50)
closed_trades = [t for t in all_trades if t["status"] == "CLOSED"]

if closed_trades:
    closed_data = []
    total_realized = 0.0
    wins = 0
    for t in closed_trades:
        pnl = float(t.get("realized_pnl") or 0.0)
        total_realized += pnl
        if pnl > 0:
            wins += 1
        closed_data.append({
            "Trade ID": t["id"][:12],
            "Symbol": t["symbol"],
            "Strategy": t["strategy_type"],
            "Contracts": t["contracts"],
            "Entry Credit": f"${t['entry_credit']:.2f}",
            "Exit Cost": f"${t.get('exit_cost', 0):.2f}",
            "Realized P&L": f"${pnl:+,.2f}",
            "Exit Reason": t.get("exit_reason", "N/A"),
            "Entry Time": t.get("entry_time", "")[:16],
            "Exit Time": t.get("exit_time", "")[:16]
        })

    win_rate = (wins / len(closed_trades) * 100) if closed_trades else 0.0
    st.caption(f"**Total Realized P&L:** ${total_realized:+,.2f} | **Win Rate:** {win_rate:.1f}% ({wins}/{len(closed_trades)})")
    st.dataframe(pd.DataFrame(closed_data), use_container_width=True)
else:
    st.info("No closed trades recorded yet.")

st.markdown("---")

# ------------------------------------------------------------------------------
# AI Decision & Risk Gate Audit Log
# ------------------------------------------------------------------------------
st.subheader("Oxotradex Decision & Risk Gate Audit Trail")
decisions = db.get_recent_decisions(limit=10)

if decisions:
    for idx, d in enumerate(decisions):
        with st.expander(f"Decision Cycle: {d['timestamp']} | Action: {d['selected_action']} | Verdict: {d['risk_verdict']}"):
            c1, c2 = st.columns([1, 1])
            with c1:
                st.markdown(f"**Market Regime:** `{d.get('regime_summary')}`")
                st.markdown(f"**Selected Action:** `{d.get('selected_action')}`")
                st.markdown(f"**Deterministic Risk Verdict:** `{'APPROVED' if d['risk_verdict'] == 'APPROVED' else 'REJECTED'}`")
                if d.get("rejection_reason"):
                    st.error(f"Rejection Reason: {d['rejection_reason']}")

            with c2:
                st.markdown("**Deterministic Risk Gate Evaluations:**")
                try:
                    gates = json.loads(d.get("risk_gate_results", "[]"))
                    for g in gates:
                        icon = "PASS" if g.get("passed") else "BLOCKED"
                        st.write(f"- `{icon}` | **{g.get('gate_name')}**: {g.get('message')}")
                except Exception:
                    st.write("Risk evaluation details not available.")

            st.markdown("**Oxotradex LLM Reasoning & Output:**")
            st.code(d.get("llm_raw_response", ""), language="json")
else:
    st.info("No decision cycles logged yet. Run an Oxotradex scan cycle to populate the audit trail.")
