"""Configuration and Environment Settings for Oxotradex: Autonomous Options Alpha Agent."""

import json
from typing import List, Optional
from pydantic import Field, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings with environment variable loading and validation."""
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

    # --------------------------------------------------------------------------
    # Alpaca Trading API Credentials
    # --------------------------------------------------------------------------
    ALPACA_API_KEY: str = Field(default="", description="Alpaca Paper API Key")
    ALPACA_SECRET_KEY: str = Field(default="", description="Alpaca Paper Secret Key")
    ALPACA_BASE_URL: str = Field(default="https://paper-api.alpaca.markets", description="Alpaca Trading Base URL")
    ALPACA_DATA_URL: str = Field(default="https://data.alpaca.markets", description="Alpaca Market Data URL")

    # Safety: Enforce paper trading for this agent
    PAPER: bool = Field(default=True, description="Enforce paper trading environment")
    DRY_RUN: bool = Field(default=False, description="Simulate orders without broker execution")

    # --------------------------------------------------------------------------
    # LLM Settings
    # --------------------------------------------------------------------------
    LLM_PROVIDER: str = Field(default="mock", description="LLM provider: 'gemini', 'openai', 'anthropic', or 'mock'")
    GEMINI_API_KEY: Optional[str] = Field(default=None, description="Google Gemini API Key")
    OPENAI_API_KEY: Optional[str] = Field(default=None, description="OpenAI API Key")
    ANTHROPIC_API_KEY: Optional[str] = Field(default=None, description="Anthropic API Key")
    LLM_MODEL: str = Field(default="gemini-2.5-flash", description="Specific LLM model identifier")

    # --------------------------------------------------------------------------
    # Hard Risk Gates & Strategy Parameters
    # --------------------------------------------------------------------------
    TARGET_STARTING_EQUITY: float = Field(default=100000.0, description="Baseline starting paper equity")
    MAX_EQUITY_RISK_PER_TRADE_PCT: float = Field(default=0.03, description="Max 3% risk of equity per trade")
    MAX_CONCURRENT_POSITIONS: int = Field(default=5, description="Max concurrent open spread positions")
    DAILY_LOSS_CIRCUIT_BREAKER_PCT: float = Field(default=0.025, description="Daily loss limit (-2.5% halts trading)")
    TAKE_PROFIT_PCT: float = Field(default=0.50, description="Take profit at 50% max credit received")
    STOP_LOSS_MULTIPLE: float = Field(default=2.0, description="Stop loss at 2.0x credit received")
    MIN_DTE: int = Field(default=7, description="Minimum days to expiration for candidates")
    MAX_DTE: int = Field(default=45, description="Maximum days to expiration for candidates")
    MAX_SHORT_DELTA: float = Field(default=0.30, description="Maximum short leg delta threshold")
    MIN_CREDIT: float = Field(default=0.20, description="Minimum credit in dollars per share ($20/contract)")
    MIN_OPEN_INTEREST: int = Field(default=50, description="Minimum open interest for liquidity")
    MAX_BID_ASK_SPREAD: float = Field(default=0.25, description="Max acceptable bid-ask spread in dollars")

    # --------------------------------------------------------------------------
    # Autonomous Loop & Universe
    # --------------------------------------------------------------------------
    SCAN_INTERVAL_MINUTES: int = Field(default=15, description="Scan interval in minutes")
    UNIVERSE: List[str] = Field(
        default=["SPY", "QQQ", "IWM", "AAPL", "MSFT", "NVDA"],
        description="Universe of underlying symbols"
    )
    DB_PATH: str = Field(default="alpaca_agent.db", description="SQLite database path")

    @field_validator("UNIVERSE", mode="before")
    @classmethod
    def parse_universe(cls, v):
        if isinstance(v, str):
            try:
                parsed = json.loads(v)
                if isinstance(parsed, list):
                    return parsed
            except Exception:
                return [s.strip().upper() for s in v.split(",") if s.strip()]
        return v

    @field_validator("PAPER")
    @classmethod
    def enforce_paper_trading(cls, v):
        if not v:
            raise ValueError("Live trading is strictly prohibited in this configuration. PAPER must be True.")
        return True


# Global settings singleton
_settings: Optional[Settings] = None

def get_settings() -> Settings:
    """Retrieve or initialize the application settings singleton."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings
