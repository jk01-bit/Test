"""The analyst brain — Claude reviews each stock and returns a structured call.

Design notes:
- The system prompt is stable and cached (prompt caching) so repeated calls in
  a run are cheap. Only the per-stock context varies between requests.
- Adaptive thinking lets the model reason as much as the decision warrants.
- The response is constrained to a JSON schema so the runner can act on it
  without brittle text parsing.

The analyst is advisory. It never moves money — the runner applies risk sizing
and the broker executes. The model is told to prioritise capital preservation.
"""
from __future__ import annotations

import json
from typing import Optional

import config

try:
    import anthropic
    _SDK = True
except Exception:  # pragma: no cover
    _SDK = False


SYSTEM_PROMPT = """You are a disciplined Indian-equities (NSE) trading analyst \
running inside an automated agent. You manage a small retail account where \
CAPITAL PRESERVATION is the first priority and steady growth is second. You are \
NOT a hype machine and you do not chase momentum blindly.

For each stock you are given a technical snapshot and the agent's current \
position (if any). Decide ONE action:
- BUY  : open or add a long position (only with a clear, reasoned edge)
- HOLD : do nothing / keep an existing position
- EXIT : close an existing position (lock profit or cut a loss)

Hard rules:
- Default to HOLD. Only BUY when trend (SMA20 vs SMA50), momentum (RSI) and the \
recent price path genuinely align. Avoid buying into overbought RSI (>70).
- Always give a stop_loss BELOW entry and a target ABOVE entry for any BUY. \
Risk:reward should be at least 1:1.5.
- If you cannot justify a trade, say so and choose HOLD. There is no penalty \
for inaction; there is a real penalty for a bad trade.
- Be concise and specific in the rationale. No financial-advice disclaimers.

Returns of ~2-4% per month are realistic for this style; do not take reckless \
risk to chase a larger number."""


# JSON schema the model must fill. (Numeric min/max constraints are validated
# in code, not in the schema, since the API's structured outputs don't enforce
# numeric bounds.)
_SCHEMA = {
    "type": "object",
    "properties": {
        "action": {"type": "string", "enum": ["BUY", "HOLD", "EXIT"]},
        "confidence": {"type": "number"},
        "entry": {"type": ["number", "null"]},
        "stop_loss": {"type": ["number", "null"]},
        "target": {"type": ["number", "null"]},
        "rationale": {"type": "string"},
        "key_risks": {"type": "array", "items": {"type": "string"}},
    },
    "required": [
        "action", "confidence", "entry", "stop_loss",
        "target", "rationale", "key_risks",
    ],
    "additionalProperties": False,
}


class StockAnalyst:
    def __init__(self):
        if not _SDK:
            raise RuntimeError(
                "anthropic SDK not installed. Run: pip install -r requirements.txt"
            )
        # Reads ANTHROPIC_API_KEY from the environment.
        self.client = anthropic.Anthropic()
        self.model = config.MODEL

    def review(self, snapshot: dict, position: Optional[dict],
               equity: float) -> dict:
        """Return a structured decision dict for one stock."""
        context = {
            "snapshot": snapshot,
            "current_position": position,   # None if flat
            "account_equity": round(equity, 2),
            "max_risk_per_trade_inr": round(equity * config.MAX_RISK_PER_TRADE_PCT, 2),
        }
        user_text = (
            "Review this stock and respond with your decision as JSON.\n\n"
            + json.dumps(context, indent=2)
        )

        # Stable system block is cached; the per-stock user turn is not.
        system = [{
            "type": "text",
            "text": SYSTEM_PROMPT,
            "cache_control": {"type": "ephemeral"},
        }]

        try:
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                thinking={"type": "adaptive"},
                output_config={
                    "effort": "medium",
                    "format": {"type": "json_schema", "schema": _SCHEMA},
                },
                system=system,
                messages=[{"role": "user", "content": user_text}],
            )
        except TypeError:
            # Older SDK without output_config: fall back to plain JSON parsing.
            resp = self.client.messages.create(
                model=self.model,
                max_tokens=1500,
                system=system,
                messages=[{
                    "role": "user",
                    "content": user_text + "\n\nReturn ONLY valid JSON.",
                }],
            )

        text = next((b.text for b in resp.content if b.type == "text"), "")
        return self._parse(text)

    @staticmethod
    def _parse(text: str) -> dict:
        try:
            data = json.loads(text)
        except json.JSONDecodeError:
            # Salvage a JSON object if the model wrapped it in prose.
            start, end = text.find("{"), text.rfind("}")
            data = json.loads(text[start:end + 1]) if start != -1 else {}
        # Normalise / clamp.
        data.setdefault("action", "HOLD")
        try:
            data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0))))
        except (TypeError, ValueError):
            data["confidence"] = 0.0
        data.setdefault("rationale", "")
        data.setdefault("key_risks", [])
        return data
