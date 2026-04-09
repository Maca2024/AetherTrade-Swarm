"""
AETHERTRADE-SWARM — Chat Routes
POST /api/v1/chat — AI-powered chatbot with regime context
"""
from __future__ import annotations

import logging
import os
from datetime import datetime, timezone
from pathlib import Path

from fastapi import APIRouter, HTTPException, status
from pydantic import BaseModel, Field

from api.deps import SimulatorDep

logger = logging.getLogger("oracle.chat")

router = APIRouter(prefix="/api/v1/chat", tags=["chat"])

# ---------------------------------------------------------------------------
# Load system prompt from prompt-stack
# ---------------------------------------------------------------------------

# In Docker: /app/prompt-stack/ | Local dev: ../prompt-stack/
_APP_DIR = Path(__file__).resolve().parent.parent.parent
_PROMPT_STACK_DIR = _APP_DIR / "prompt-stack"
if not _PROMPT_STACK_DIR.exists():
    # Fallback: try two levels up (repo root / prompt-stack)
    _PROMPT_STACK_DIR = _APP_DIR.parent / "prompt-stack"
_SYSTEM_PROMPT_PATH = _PROMPT_STACK_DIR / "SYSTEM-PROMPT-AETHERTRADE.md"

_system_prompt_cache: str | None = None


def _load_system_prompt() -> str:
    global _system_prompt_cache
    if _system_prompt_cache is not None:
        return _system_prompt_cache

    if _SYSTEM_PROMPT_PATH.exists():
        _system_prompt_cache = _SYSTEM_PROMPT_PATH.read_text(encoding="utf-8")
        logger.info("Loaded system prompt from %s", _SYSTEM_PROMPT_PATH)
    else:
        _system_prompt_cache = (
            "You are AETHERTRADE, the AI assistant for the AETHERTRADE-SWARM trading platform. "
            "Help users understand market regimes, strategy performance, risk metrics, "
            "and portfolio positioning. Be concise, data-driven, and transparent about uncertainty."
        )
        logger.warning("prompt-stack not found at %s — using fallback prompt", _SYSTEM_PROMPT_PATH)

    return _system_prompt_cache


# ---------------------------------------------------------------------------
# Request / Response
# ---------------------------------------------------------------------------

class ChatMessage(BaseModel):
    role: str = Field(description="user | assistant | system")
    content: str


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1)


class ChatResponse(BaseModel):
    reply: str
    regime_context: str | None = None
    timestamp: str = Field(default_factory=lambda: datetime.now(timezone.utc).isoformat())


# ---------------------------------------------------------------------------
# LiteLLM client (uses Hetzner LiteLLM proxy at :4000 or falls back)
# ---------------------------------------------------------------------------

async def _call_llm(messages: list[dict], regime_context: str) -> str:
    """Call LLM via litellm or httpx fallback."""
    try:
        import litellm

        system_prompt = _load_system_prompt()
        context_block = (
            f"\n\n## CURRENT CONTEXT\n"
            f"Timestamp: {datetime.now(timezone.utc).isoformat()}\n"
            f"{regime_context}"
        )

        full_messages = [
            {"role": "system", "content": system_prompt + context_block},
            *messages,
        ]

        response = await litellm.acompletion(
            model=os.getenv("CHAT_MODEL", "anthropic/claude-haiku-4-5-20251001"),
            messages=full_messages,
            max_tokens=1024,
            temperature=0.7,
            api_base=os.getenv("LITELLM_API_BASE", "http://localhost:4000"),
        )
        return response.choices[0].message.content

    except ImportError:
        logger.warning("litellm not installed — using echo fallback")
        return _fallback_response(messages, regime_context)
    except Exception as e:
        logger.error("LLM call failed: %s", e)
        return _fallback_response(messages, regime_context)


def _fallback_response(messages: list[dict], regime_context: str) -> str:
    """Deterministic fallback when LLM is unavailable."""
    last_msg = messages[-1]["content"] if messages else ""
    lower = last_msg.lower()

    if "regime" in lower:
        return (
            f"Based on our HMM detection model:\n\n{regime_context}\n\n"
            "The regime drives all pod allocation weights through our "
            "regime-conditional allocation table."
        )
    if "risk" in lower:
        return (
            "Our 4-layer risk framework monitors:\n"
            "- L1: Agent-level drawdown (max 15%)\n"
            "- L2: Strategy group correlation (max 85%)\n"
            "- L3: Portfolio VaR/CVaR (95% max 5%)\n"
            "- L4: Systemic kill switches (VIX > 40 = HALT)\n\n"
            f"Current context:\n{regime_context}"
        )
    if "strateg" in lower or "pod" in lower:
        return (
            "AETHERTRADE-SWARM runs 9 independent strategy pods:\n"
            "MOM, MR, GMC, SA, VOL, BEH, AI, MF, MM\n\n"
            "Each pod generates signals independently. The Alpha Combinator "
            "fuses them using Black-Litterman optimization with regime-conditional weights.\n\n"
            f"Current context:\n{regime_context}"
        )
    return (
        "I'm AETHERTRADE, your AI trading intelligence assistant. I can help you with:\n"
        "- **Market regime** analysis (HMM detection)\n"
        "- **Strategy pod** performance and signals\n"
        "- **Risk management** metrics and kill switches\n"
        "- **Portfolio** positioning and allocation\n\n"
        f"Current context:\n{regime_context}"
    )


# ---------------------------------------------------------------------------
# Route
# ---------------------------------------------------------------------------

@router.post("", response_model=ChatResponse, summary="Chat with AETHERTRADE AI")
async def chat(
    request: ChatRequest,
    sim: SimulatorDep,
) -> ChatResponse:
    """
    Send messages to AETHERTRADE's AI assistant. The system automatically injects
    live regime data, portfolio context, and risk status into each response.
    No API key required for chat.
    """
    # Build regime context
    try:
        regime_data = sim.get_regime()
        perf_data = sim.get_performance_metrics()
        regime_context = (
            f"Regime: {regime_data['regime'].upper()} "
            f"(confidence: {regime_data['confidence']:.0%})\n"
            f"Duration: {regime_data['duration_days']} days\n"
            f"Portfolio Return: {perf_data['total_return']:.1f}% total, "
            f"{perf_data['ytd_return']:.1f}% YTD\n"
            f"Sharpe: {perf_data['sharpe_ratio']:.2f} | "
            f"Max DD: {perf_data['max_drawdown']:.1f}% | "
            f"Win Rate: {perf_data['win_rate']:.0%}"
        )
    except Exception:
        regime_context = "Regime data unavailable."

    messages = [{"role": m.role, "content": m.content} for m in request.messages]

    reply = await _call_llm(messages, regime_context)

    return ChatResponse(
        reply=reply,
        regime_context=regime_context,
    )
