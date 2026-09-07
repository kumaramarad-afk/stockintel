from __future__ import annotations

import json
import logging
import re
from typing import Any

from anthropic import Anthropic

from app.config import settings
from services.keys import anthropic_key
from services.language import scrub_copy

logger = logging.getLogger(__name__)


def summarize(ticker: str, snapshot: dict[str, Any]) -> dict[str, Any] | None:
    api_key = anthropic_key()
    if not api_key:
        return None
    prompt = (
        f"You are a research desk editor writing a factual briefing about {ticker}.\n"
        "Use only the JSON snapshot. Do not invent numbers, events, or product launches.\n"
        "Never use the words buy, sell, hold, or invest. Never say we recommend or you should.\n"
        "Never give a recommendation. Attribute every claim to analysts or data.\n"
        "Use phrasing such as: Analysts suggest..., The data indicates..., Consensus points to..., "
        "X out of Y analysts tracking this stock have a positive outlook.\n"
        "Write in third person. Facts only.\n\n"
        f"```json\n{json.dumps(snapshot, default=str)[:12000]}\n```\n\n"
        "Return ONLY JSON with keys:\n"
        '  "what_the_data_shows": one paragraph summarizing what analysts and data collectively indicate\n'
        '  "key_risks": array of specific risk factors the data reveals\n'
        '  "upcoming_catalysts": array of upcoming events that could move the stock '
        "(earnings date, product launches only if present in the snapshot, macro/sector items from the snapshot)\n"
        "If a catalyst is not in the snapshot, omit it."
    )
    try:
        client = Anthropic(api_key=api_key)
        message = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=1200,
            messages=[{"role": "user", "content": prompt}],
        )
    except Exception:
        logger.exception("Research briefing failed for %s", ticker)
        return None
    parts = [block.text for block in message.content if getattr(block, "type", None) == "text"]
    text = "\n\n".join(part.strip() for part in parts if part and part.strip())
    if not text:
        return None
    match = re.search(r"\{[\s\S]*\}", text)
    if match:
        try:
            payload = json.loads(match.group(0))
            return {
                "what_the_data_shows": scrub_copy(str(payload.get("what_the_data_shows") or payload.get("why_it_scores") or "")),
                "why_it_scores": scrub_copy(str(payload.get("what_the_data_shows") or payload.get("why_it_scores") or "")),
                "key_risks": payload.get("key_risks") or [],
                "upcoming_catalysts": payload.get("upcoming_catalysts") or payload.get("outlook") or [],
            }
        except json.JSONDecodeError:
            pass
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", text) if part.strip()]
    return {
        "what_the_data_shows": scrub_copy(paragraphs[0] if paragraphs else text),
        "why_it_scores": scrub_copy(paragraphs[0] if paragraphs else text),
        "key_risks": paragraphs[1] if len(paragraphs) > 1 else [],
        "upcoming_catalysts": paragraphs[2] if len(paragraphs) > 2 else [],
    }
