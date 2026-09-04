"""SQLite Database storage and state persistence for Alpaca Autonomous Options Alpha Agent."""

import sqlite3
import json
from datetime import datetime, date, timezone
from typing import Any, Dict, List, Optional
from src.config import get_settings


class Database:
    """Thread-safe SQLite database manager for persisting trades, decisions, and system state."""

    def __init__(self, db_path: Optional[str] = None):
        self.db_path = db_path or get_settings().DB_PATH
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema if tables do not exist."""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # Trades Table: Track spread lifecycle
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS trades (
                    id TEXT PRIMARY KEY,
                    symbol TEXT NOT NULL,
                    strategy_type TEXT NOT NULL,
                    status TEXT NOT NULL, -- OPEN, CLOSED, CANCELLED
                    legs_json TEXT NOT NULL,
                    contracts INTEGER NOT NULL,
                    entry_credit REAL NOT NULL,
                    total_credit REAL NOT NULL,
                    max_loss REAL NOT NULL,
                    total_max_loss REAL NOT NULL,
                    entry_time TEXT NOT NULL,
                    exit_time TEXT,
                    exit_cost REAL,
                    realized_pnl REAL,
                    exit_reason TEXT,
                    alpaca_order_id TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Decisions Table: Full AI & Risk Gate Audit Trail
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TEXT NOT NULL,
                    regime_summary TEXT,
                    candidates_json TEXT,
                    llm_raw_response TEXT,
                    selected_action TEXT,
                    risk_gate_results TEXT,
                    risk_verdict TEXT NOT NULL, -- APPROVED, REJECTED
                    rejection_reason TEXT
                )
            """)

            # Daily Snapshots Table: Track equity, daily PnL, circuit breaker status
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS daily_snapshots (
                    date TEXT PRIMARY KEY,
                    starting_equity REAL NOT NULL,
                    current_equity REAL NOT NULL,
                    daily_pnl REAL NOT NULL,
                    daily_pnl_pct REAL NOT NULL,
                    open_positions_count INTEGER NOT NULL,
                    circuit_breaker_tripped INTEGER NOT NULL DEFAULT 0,
                    updated_at TEXT NOT NULL
                )
            """)

            # System State Table: Kill switch & operational state
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS system_state (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)

            # Set initial default system state
            cursor.execute("""
                INSERT OR IGNORE INTO system_state (key, value, updated_at)
                VALUES ('kill_switch', '0', ?)
            """, (datetime.now(timezone.utc).isoformat(),))

            cursor.execute("""
                INSERT OR IGNORE INTO system_state (key, value, updated_at)
                VALUES ('circuit_breaker_halt', '0', ?)
            """, (datetime.now(timezone.utc).isoformat(),))

            conn.commit()

    # --------------------------------------------------------------------------
    # System State & Kill-Switch Methods
    # --------------------------------------------------------------------------
    def get_state(self, key: str, default: str = "") -> str:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT value FROM system_state WHERE key = ?", (key,))
            row = cursor.fetchone()
            return row["value"] if row else default

    def set_state(self, key: str, value: str):
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO system_state (key, value, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET value = excluded.value, updated_at = excluded.updated_at
            """, (key, str(value), datetime.now(timezone.utc).isoformat()))
            conn.commit()

    def is_kill_switch_active(self) -> bool:
        return self.get_state("kill_switch", "0") == "1"

    def set_kill_switch(self, active: bool):
        self.set_state("kill_switch", "1" if active else "0")

    def is_circuit_breaker_halted(self) -> bool:
        return self.get_state("circuit_breaker_halt", "0") == "1"

    def set_circuit_breaker_halt(self, halted: bool):
        self.set_state("circuit_breaker_halt", "1" if halted else "0")

    # --------------------------------------------------------------------------
    # Trades Persistence Methods
    # --------------------------------------------------------------------------
    def record_trade_entry(self, trade_data: Dict[str, Any]):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO trades (
                    id, symbol, strategy_type, status, legs_json, contracts,
                    entry_credit, total_credit, max_loss, total_max_loss,
                    entry_time, exit_time, exit_cost, realized_pnl, exit_reason,
                    alpaca_order_id, created_at, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                trade_data["id"],
                trade_data["symbol"],
                trade_data["strategy_type"],
                trade_data.get("status", "OPEN"),
                json.dumps(trade_data["legs"]),
                trade_data["contracts"],
                trade_data["entry_credit"],
                trade_data["total_credit"],
                trade_data["max_loss"],
                trade_data["total_max_loss"],
                trade_data.get("entry_time", now),
                None,
                None,
                None,
                None,
                trade_data.get("alpaca_order_id"),
                now,
                now
            ))
            conn.commit()

    def update_trade_exit(self, trade_id: str, exit_cost: float, realized_pnl: float, exit_reason: str):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                UPDATE trades
                SET status = 'CLOSED',
                    exit_time = ?,
                    exit_cost = ?,
                    realized_pnl = ?,
                    exit_reason = ?,
                    updated_at = ?
                WHERE id = ?
            """, (now, exit_cost, realized_pnl, exit_reason, now, trade_id))
            conn.commit()

    def get_open_trades(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades WHERE status = 'OPEN'")
            rows = cursor.fetchall()
            trades = []
            for row in rows:
                t = dict(row)
                t["legs"] = json.loads(t["legs_json"])
                trades.append(t)
            return trades

    def get_all_trades(self, limit: int = 100) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM trades ORDER BY created_at DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            trades = []
            for row in rows:
                t = dict(row)
                t["legs"] = json.loads(t["legs_json"])
                trades.append(t)
            return trades

    # --------------------------------------------------------------------------
    # Decision Audit Logging
    # --------------------------------------------------------------------------
    def record_decision(
        self,
        regime_summary: str,
        candidates: List[Dict[str, Any]],
        llm_response: str,
        selected_action: str,
        risk_results: List[Dict[str, Any]],
        risk_verdict: str,
        rejection_reason: Optional[str] = None
    ):
        now = datetime.now(timezone.utc).isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO decisions (
                    timestamp, regime_summary, candidates_json, llm_raw_response,
                    selected_action, risk_gate_results, risk_verdict, rejection_reason
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                now,
                regime_summary,
                json.dumps(candidates),
                llm_response,
                selected_action,
                json.dumps(risk_results),
                risk_verdict,
                rejection_reason
            ))
            conn.commit()

    def get_recent_decisions(self, limit: int = 20) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM decisions ORDER BY timestamp DESC LIMIT ?", (limit,))
            rows = cursor.fetchall()
            return [dict(r) for r in rows]

    # --------------------------------------------------------------------------
    # Daily Snapshot & Circuit Breaker Tracking
    # --------------------------------------------------------------------------
    def record_daily_snapshot(
        self,
        current_equity: float,
        starting_equity: float,
        open_positions: int,
        circuit_breaker: bool
    ):
        today_str = date.today().isoformat()
        daily_pnl = current_equity - starting_equity
        daily_pnl_pct = daily_pnl / starting_equity if starting_equity > 0 else 0.0
        now = datetime.now(timezone.utc).isoformat()

        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO daily_snapshots (
                    date, starting_equity, current_equity, daily_pnl, daily_pnl_pct,
                    open_positions_count, circuit_breaker_tripped, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(date) DO UPDATE SET
                    current_equity = excluded.current_equity,
                    daily_pnl = excluded.daily_pnl,
                    daily_pnl_pct = excluded.daily_pnl_pct,
                    open_positions_count = excluded.open_positions_count,
                    circuit_breaker_tripped = excluded.circuit_breaker_tripped,
                    updated_at = excluded.updated_at
            """, (
                today_str, starting_equity, current_equity, daily_pnl, daily_pnl_pct,
                open_positions, 1 if circuit_breaker else 0, now
            ))
            conn.commit()

    def get_latest_daily_snapshot(self) -> Optional[Dict[str, Any]]:
        today_str = date.today().isoformat()
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_snapshots WHERE date = ?", (today_str,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_all_snapshots(self) -> List[Dict[str, Any]]:
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM daily_snapshots ORDER BY date ASC")
            return [dict(r) for r in cursor.fetchall()]
