"""The analyst brain — decides BUY / HOLD / EXIT for one stock.

Two interchangeable brains, selected by config.BRAIN:

- "claude_code" (default): shells out to the Claude Code CLI (`claude -p`),
  which authenticates with your Claude subscription (e.g. Max plan). No
  Anthropic API credits are spent — usage counts against your subscription.
  Requires Claude Code installed and logged in on the machine running this.

- "api": calls the Anthropic Messages API directly (billed per token). Uses
  prompt caching + adaptive thinking + JSON-schema structured output.

Both return the same decision dict, so the rest of the agent doesn't care which
one is active. The analyst is advisory only — risk.py sizes trades and the
broker executes.
"""
from __future__ import annotations

import json
import shutil
import subprocess
import tempfile
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
# in code, not in the schema, since structured outputs don't enforce bounds.)
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

_SCHEMA_HINT = (
    "CRITICAL OUTPUT RULE: Reply with ONE raw JSON object and NOTHING else. "
    "No markdown, no ``` fences, no headings, no emoji, no disclaimers, no text "
    "before or after. Your entire reply must start with { and end with }. "
    'Keys: "action" (BUY|HOLD|EXIT), "confidence" (0-1 number), "entry" (number '
    'or null), "stop_loss" (number or null), "target" (number or null), '
    '"rationale" (short string), "key_risks" (array of strings).'
)


def _extract_json(text: str) -> dict:
    """Best-effort extraction of a JSON object from model output."""
    if not text:
        return {}
    s = text.strip()
    # Strip ```json ... ``` fences if present.
    if s.startswith("```"):
        s = s.split("```", 2)
        s = s[1] if len(s) > 1 else text
        if s.lstrip().lower().startswith("json"):
            s = s.lstrip()[4:]
        s = s.strip()
    try:
        return json.loads(s)
    except json.JSONDecodeError:
        pass
    # Brace-match the first balanced {...} object anywhere in the text.
    start = s.find("{")
    while start != -1:
        depth = 0
        for i in range(start, len(s)):
            if s[i] == "{":
                depth += 1
            elif s[i] == "}":
                depth -= 1
                if depth == 0:
                    try:
                        return json.loads(s[start:i + 1])
                    except json.JSONDecodeError:
                        break
        start = s.find("{", start + 1)
    return {}


def build_user_text(snapshot: dict, position: Optional[dict], equity: float) -> str:
    context = {
        "snapshot": snapshot,
        "current_position": position,  # None if flat
        "account_equity": round(equity, 2),
        "max_risk_per_trade_inr": round(equity * config.MAX_RISK_PER_TRADE_PCT, 2),
    }
    return (
        "Review this stock and respond with your decision as JSON.\n\n"
        + json.dumps(context, indent=2)
    )


def parse_decision(text: str) -> dict:
    """Parse and normalise a decision JSON from model text.

    Robust to markdown code fences and surrounding prose.
    """
    data = _extract_json(text)
    if not isinstance(data, dict):
        data = {}
    data.setdefault("action", "HOLD")
    try:
        data["confidence"] = max(0.0, min(1.0, float(data.get("confidence", 0))))
    except (TypeError, ValueError):
        data["confidence"] = 0.0
    data.setdefault("rationale", "")
    data.setdefault("key_risks", [])
    return data


class _BaseAnalyst:
    label = "analyst"

    def __init__(self):
        self.usage = {"input": 0, "output": 0, "cache_read": 0, "cache_write": 0}
        self.calls = 0

    def review(self, snapshot, position, equity) -> dict:  # pragma: no cover
        raise NotImplementedError

    def cost_summary(self) -> str:  # pragma: no cover
        return ""


# ---------------------------------------------------------------------------
# Claude Code brain (uses your Claude subscription, e.g. Max plan)
# ---------------------------------------------------------------------------
class ClaudeCodeAnalyst(_BaseAnalyst):
    label = "Claude Code (subscription)"

    def __init__(self):
        super().__init__()
        self.cli = config.CLAUDE_CLI
        if not shutil.which(self.cli):
            raise RuntimeError(
                f"'{self.cli}' not found on PATH. Install Claude Code and log in "
                "with your subscription, or set BRAIN=api / BRAIN=rules."
            )
        self.reported_cost = 0.0
        # Run the CLI in a throwaway dir so it doesn't auto-load this repo's
        # CLAUDE.md / files as context (keeps each call lean).
        self._cwd = tempfile.mkdtemp(prefix="analyst_")

    def review(self, snapshot: dict, position: Optional[dict], equity: float) -> dict:
        # Claude Code answers conversationally by default, so we force raw JSON
        # via a strict instruction and parse it (the --json-schema flag alone
        # does not make the printed result a bare JSON object).
        prompt = build_user_text(snapshot, position, equity) + "\n\n" + _SCHEMA_HINT
        system = SYSTEM_PROMPT + "\n\n" + _SCHEMA_HINT
        cmd = [
            self.cli, "-p", prompt,
            "--output-format", "json",
            "--system-prompt", system,
        ]
        if config.CLAUDE_CODE_MODEL:
            cmd += ["--model", config.CLAUDE_CODE_MODEL]
        cmd += config.CLAUDE_CLI_EXTRA_ARGS

        try:
            proc = subprocess.run(
                cmd, capture_output=True, text=True,
                timeout=config.CLAUDE_CLI_TIMEOUT, cwd=self._cwd,
            )
        except subprocess.TimeoutExpired:
            return parse_decision('{"action":"HOLD","rationale":"claude-code timeout"}')

        if proc.returncode != 0:
            err = (proc.stderr or proc.stdout or "").strip()[:200]
            return parse_decision(
                json.dumps({"action": "HOLD",
                            "rationale": f"claude-code error: {err}"})
            )

        self.calls += 1
        text = proc.stdout
        # `--output-format json` wraps the answer in an envelope; unwrap it.
        try:
            env = json.loads(proc.stdout)
            text = env.get("result", proc.stdout)
            self.reported_cost += float(env.get("total_cost_usd", 0) or 0)
            u = env.get("usage", {}) or {}
            self.usage["input"] += int(u.get("input_tokens", 0) or 0)
            self.usage["output"] += int(u.get("output_tokens", 0) or 0)
            self.usage["cache_read"] += int(u.get("cache_read_input_tokens", 0) or 0)
            self.usage["cache_write"] += int(u.get("cache_creation_input_tokens", 0) or 0)
        except (json.JSONDecodeError, TypeError):
            pass  # fall back to treating raw stdout as the answer
        return parse_decision(text)

    def cost_summary(self) -> str:
        u = self.usage
        return (
            f"Analyst: {self.label} — {self.calls} call(s); "
            f"covered by your subscription, no API charge "
            f"(reported equivalent ${self.reported_cost:.4f}).\n"
            f"  tokens: in {u['input']:,} / out {u['output']:,} / "
            f"cache-read {u['cache_read']:,}"
        )


# ---------------------------------------------------------------------------
# Anthropic API brain (billed per token)
# ---------------------------------------------------------------------------
class StockAnalyst(_BaseAnalyst):
    label = "Anthropic API"

    def __init__(self):
        super().__init__()
        if not _SDK:
            raise RuntimeError(
                "anthropic SDK not installed. Run: pip install -r requirements.txt"
            )
        self.client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY
        self.model = config.MODEL

    def review(self, snapshot: dict, position: Optional[dict], equity: float) -> dict:
        user_text = build_user_text(snapshot, position, equity)
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
            resp = self.client.messages.create(
                model=self.model, max_tokens=1500, system=system,
                messages=[{"role": "user",
                           "content": user_text + "\n\n" + _SCHEMA_HINT}],
            )
        self._track(resp)
        text = next((b.text for b in resp.content if b.type == "text"), "")
        return parse_decision(text)

    def _track(self, resp) -> None:
        u = getattr(resp, "usage", None)
        if not u:
            return
        self.calls += 1
        self.usage["input"] += getattr(u, "input_tokens", 0) or 0
        self.usage["output"] += getattr(u, "output_tokens", 0) or 0
        self.usage["cache_read"] += getattr(u, "cache_read_input_tokens", 0) or 0
        self.usage["cache_write"] += getattr(u, "cache_creation_input_tokens", 0) or 0

    def cost_usd(self) -> float:
        rates = config.PRICING.get(self.model, config.PRICING["claude-opus-4-8"])
        in_rate, out_rate = rates["in"] / 1e6, rates["out"] / 1e6
        return (
            self.usage["input"] * in_rate
            + self.usage["output"] * out_rate
            + self.usage["cache_read"] * in_rate * 0.1
            + self.usage["cache_write"] * in_rate * 1.25
        )

    def cost_summary(self) -> str:
        usd = self.cost_usd()
        u = self.usage
        return (
            f"Analyst cost: ${usd:.4f} (~₹{usd*config.USD_INR:.2f}) "
            f"over {self.calls} call(s) on {self.model}\n"
            f"  tokens: in {u['input']:,} / out {u['output']:,} / "
            f"cache-read {u['cache_read']:,}"
        )


def get_analyst() -> _BaseAnalyst:
    """Factory: pick the brain from config.BRAIN."""
    brain = config.BRAIN
    if brain == "api":
        return StockAnalyst()
    if brain in ("claude_code", "claude-code", "cli"):
        return ClaudeCodeAnalyst()
    raise RuntimeError(
        f"Unknown BRAIN={brain!r}. Use 'claude_code' or 'api'."
    )
