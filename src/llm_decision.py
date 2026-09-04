"""LLM Decision Layer: Structured AI reasoning with multi-provider support.

Supports Google Gemini, OpenAI, Anthropic, and deterministic Mock fallback.
"""

import os
import json
import re
from typing import Any, Dict, List, Optional
from pydantic import BaseModel, Field

from src.config import Settings, get_settings
from src.logger import log_info, log_success, log_warning, log_error


class TradeActionProposal(BaseModel):
    """Structured individual trade recommendation from the LLM."""
    action_type: str = Field(default="PASS", description="OPEN_TRADE, PASS, or CLOSE_POSITION")
    candidate_id: Optional[str] = Field(default=None, description="Matching candidate ID")
    symbol: Optional[str] = Field(default=None, description="Underlying symbol")
    strategy_type: Optional[str] = Field(default=None, description="BULL_PUT_SPREAD, BEAR_CALL_SPREAD, IRON_CONDOR")
    confidence_score: float = Field(default=0.5, ge=0.0, le=1.0, description="Confidence score 0.0 - 1.0")
    trade_rationale: str = Field(default="No specific rationale provided", description="Quantitative justification")
    proposed_contracts: int = Field(default=1, ge=1, le=10, description="Suggested initial contract quantity")


class LLMDecision(BaseModel):
    """Full structured LLM decision response."""
    market_analysis: str = Field(default="", description="Macro & technical market summary")
    recommended_actions: List[TradeActionProposal] = Field(default_factory=list)
    risk_assessment: str = Field(default="", description="Evaluation of tail risks")
    raw_response: str = Field(default="", description="Raw response text")


class LLMDecisionEngine:
    """Invokes LLM provider to evaluate market context and select optimal candidate trades."""

    def __init__(self, settings: Optional[Settings] = None):
        self.settings = settings or get_settings()
        self.provider = (self.settings.LLM_PROVIDER or "mock").lower()
        self.prompt_template = self._load_prompt_template()

    def _load_prompt_template(self) -> str:
        prompt_path = os.path.join(os.path.dirname(__file__), "..", "prompts", "decision_prompt.txt")
        if os.path.exists(prompt_path):
            try:
                with open(prompt_path, "r", encoding="utf-8") as f:
                    return f.read()
            except Exception as e:
                log_warning(f"Failed to read prompt file: {e}. Using built-in template.")

        return (
            "You are an options portfolio manager. Review the market and candidates, then reply with JSON:\n"
            "market_context:\n{market_context}\n\ncandidate_spreads:\n{candidate_spreads}"
        )

    def decide(
        self,
        account_info: Dict[str, Any],
        regime_info: Dict[str, Any],
        candidates: List[Dict[str, Any]],
        open_positions: List[Dict[str, Any]]
    ) -> LLMDecision:
        """Construct prompt, query LLM, and return validated structured decision."""
        # Format Market Context
        market_context_str = json.dumps({
            "account_equity": account_info.get("equity", 100000.0),
            "cash": account_info.get("cash", 100000.0),
            "daily_pnl": account_info.get("daily_pnl", 0.0),
            "daily_pnl_pct": account_info.get("daily_pnl_pct", 0.0),
            "open_positions_count": len(open_positions),
            "active_regime": regime_info
        }, indent=2)

        # Format Candidates (pruned for concise prompt)
        pruned_candidates = []
        for c in candidates:
            pruned_candidates.append({
                "candidate_id": c.get("id"),
                "symbol": c.get("symbol"),
                "strategy_type": c.get("strategy_type"),
                "expiration": c.get("expiration"),
                "dte": c.get("dte"),
                "net_credit": c.get("net_credit"),
                "max_loss": c.get("max_loss"),
                "return_on_risk_pct": c.get("return_on_risk_pct"),
                "legs_summary": [
                    f"{leg.get('side').upper()} {leg.get('strike')}{leg.get('type')} (delta: {leg.get('delta')})"
                    for leg in c.get("legs", [])
                ]
            })

        candidate_spreads_str = json.dumps(pruned_candidates, indent=2)

        prompt = self.prompt_template.format(
            market_context=market_context_str,
            candidate_spreads=candidate_spreads_str
        )

        log_info(f"Querying LLM Layer via provider: '{self.provider.upper()}' (Model: {self.settings.LLM_MODEL})...")

        raw_text = ""
        try:
            if self.provider == "gemini":
                raw_text = self._call_gemini(prompt)
            elif self.provider == "openai":
                raw_text = self._call_openai(prompt)
            elif self.provider == "anthropic":
                raw_text = self._call_anthropic(prompt)
            else:
                raw_text = self._call_mock(pruned_candidates, regime_info)

            return self._parse_response(raw_text)

        except Exception as e:
            log_error(f"Error querying LLM provider '{self.provider}': {e}. Falling back to deterministic mock selector.")
            raw_text = self._call_mock(pruned_candidates, regime_info)
            return self._parse_response(raw_text)

    # --------------------------------------------------------------------------
    # Provider Implementations
    # --------------------------------------------------------------------------
    def _call_gemini(self, prompt: str) -> str:
        api_key = self.settings.GEMINI_API_KEY
        if not api_key:
            raise ValueError("GEMINI_API_KEY not provided")

        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = client.models.generate_content(
                model=self.settings.LLM_MODEL,
                contents=prompt
            )
            return response.text or ""
        except ImportError:
            import google.generativeai as gai
            gai.configure(api_key=api_key)
            model = gai.GenerativeModel(self.settings.LLM_MODEL)
            response = model.generate_content(prompt)
            return response.text or ""

    def _call_openai(self, prompt: str) -> str:
        api_key = self.settings.OPENAI_API_KEY
        if not api_key:
            raise ValueError("OPENAI_API_KEY not provided")

        from openai import OpenAI
        client = OpenAI(api_key=api_key)
        response = client.chat.completions.create(
            model=self.settings.LLM_MODEL or "gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"}
        )
        return response.choices[0].message.content or ""

    def _call_anthropic(self, prompt: str) -> str:
        api_key = self.settings.ANTHROPIC_API_KEY
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not provided")

        from anthropic import Anthropic
        client = Anthropic(api_key=api_key)
        response = client.messages.create(
            model=self.settings.LLM_MODEL or "claude-3-5-sonnet-20241022",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}]
        )
        return response.content[0].text if response.content else ""

    def _call_mock(self, candidates: List[Dict[str, Any]], regime_info: Dict[str, Any]) -> str:
        """Deterministic quantitative fallback selector when no LLM key is configured."""
        if not candidates:
            return json.dumps({
                "market_analysis": "No viable candidate spreads met the quantitative delta and liquidity filters.",
                "recommended_actions": [],
                "risk_assessment": "Market liquidity or volatility criteria not satisfied."
            })

        # Pick candidate with optimal return-on-risk
        sorted_candidates = sorted(
            candidates,
            key=lambda x: x.get("return_on_risk_pct", 0.0),
            reverse=True
        )
        best = sorted_candidates[0]

        decision = {
            "market_analysis": (
                f"Underlying {best.get('symbol')} displays {regime_info.get('regime', 'NEUTRAL')} regime "
                f"(RSI: {regime_info.get('rsi14', 50):.1f}, HV20: {regime_info.get('hv20_pct', 15):.1f}%). "
                f"Optimal theta harvesting via {best.get('strategy_type')}."
            ),
            "recommended_actions": [
                {
                    "action_type": "OPEN_TRADE",
                    "candidate_id": best.get("candidate_id"),
                    "symbol": best.get("symbol"),
                    "strategy_type": best.get("strategy_type"),
                    "confidence_score": 0.88,
                    "trade_rationale": (
                        f"Attractive risk/reward with {best.get('return_on_risk_pct')}% return on risk, "
                        f"favorable {best.get('dte')} DTE theta decay horizon, and well-buffered OTM short strikes."
                    ),
                    "proposed_contracts": 1
                }
            ],
            "risk_assessment": "Defined-risk structure strictly isolates max loss. Low gamma risk at 28 DTE."
        }
        return json.dumps(decision)

    # --------------------------------------------------------------------------
    # Robust JSON Parser
    # --------------------------------------------------------------------------
    def _parse_response(self, raw_text: str) -> LLMDecision:
        """Extract and validate JSON from model output."""
        cleaned = raw_text.strip()
        # Strip markdown ```json ... ``` code fences if present
        match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", cleaned)
        if match:
            cleaned = match.group(1).strip()

        try:
            data = json.loads(cleaned)
            actions = []
            for act in data.get("recommended_actions", []):
                actions.append(TradeActionProposal(**act))

            return LLMDecision(
                market_analysis=data.get("market_analysis", "Market analysis unavailable"),
                recommended_actions=actions,
                risk_assessment=data.get("risk_assessment", "Risk assessment unavailable"),
                raw_response=raw_text
            )
        except Exception as e:
            log_warning(f"Failed to parse LLM response as JSON: {e}. Raw: {raw_text[:200]}")
            return LLMDecision(
                market_analysis="Parse error on LLM response",
                recommended_actions=[],
                risk_assessment="Unable to extract valid JSON proposal",
                raw_response=raw_text
            )
