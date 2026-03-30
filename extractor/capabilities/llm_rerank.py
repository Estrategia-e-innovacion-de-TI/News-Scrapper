"""LLM-based re-ranking of documents via Amazon Bedrock.

Loads an editable prompt template from ``prompts/rerank.yaml`` and uses
it to score each document's relevance with a language model.  Falls back
to the heuristic score when Bedrock is unavailable or the prompt file is
missing.

Activated only when ``--classifier llm`` is used.
"""
from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

# ── Prompt loading ───────────────────────────────────────────────────

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"

_PROMPT_MAP: dict[str, str] = {
    "aras_news": "rerank_riesgo.yaml",
    "riesgos_news": "rerank_riesgo.yaml",
    "vigilancia_news": "rerank_vigilancia.yaml",
}

_LATAM_SIGNALS = {
    "colombia", "bogotá", "bogota", "medellín", "medellin", "cali",
    "barranquilla", "cartagena",
    "panamá", "panama", "ciudad de panamá", "azuero",
    "el salvador", "san salvador", "salvadoreño",
    "guatemala", "ciudad de guatemala", "guatemalteco",
    "perú", "peru", "ecuador", "chile", "méxico", "mexico",
    "brasil", "argentina", "costa rica", "honduras", "nicaragua",
    "latinoamérica", "latinoamerica", "latam",
    "centroamérica", "centroamerica",
}


def _load_prompt(flow: str | None = None, path: Path | None = None) -> dict[str, str]:
    """Load system + user prompt templates from YAML.

    Selects the prompt file based on *flow* (``aras_news``, ``riesgos_news``,
    ``vigilancia_news``).  An explicit *path* overrides the automatic selection.

    Returns ``{"system": "...", "user": "..."}`` or empty dict on error.
    """
    if path is None:
        filename = _PROMPT_MAP.get(flow or "", "rerank_riesgo.yaml")
        path = _PROMPTS_DIR / filename
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return {
            "system": data.get("system", ""),
            "user": data.get("user", ""),
        }
    except FileNotFoundError:
        logger.warning("rerank prompt not found at %s — LLM rerank disabled", path)
        return {}
    except Exception:
        logger.warning("Failed to load rerank prompt", exc_info=True)
        return {}


def _detect_geo(text: str) -> str:
    """Return geo region based on text signals.

    Priority regions: Colombia, Panamá, El Salvador, Guatemala.
    """
    lower = text[:3000].lower()
    # Priority countries
    if any(s in lower for s in ("colombia", "bogotá", "bogota", "medellín",
                                 "medellin", "cali", "barranquilla", "cartagena")):
        return "Colombia"
    if any(s in lower for s in ("panamá", "panama", "ciudad de panamá",
                                 "azuero", "chiriquí", "colón")):
        return "Panamá"
    if any(s in lower for s in ("el salvador", "san salvador", "salvadoreño")):
        return "El Salvador"
    if any(s in lower for s in ("guatemala", "ciudad de guatemala", "guatemalteco")):
        return "Guatemala"
    if any(s in lower for s in _LATAM_SIGNALS):
        return "Latam"
    return "Global"


# ── Re-ranker ────────────────────────────────────────────────────────


class LLMReranker:
    """Re-rank documents using Amazon Bedrock (Claude).

    Parameters
    ----------
    model_id : str
        Bedrock model identifier.
    prompt_path : Path | None
        Override path to the prompt YAML.
    max_excerpt : int
        Max characters of article text sent to the LLM.
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        flow: str | None = None,
        prompt_path: Path | None = None,
        max_excerpt: int = 1500,
    ) -> None:
        self.model_id = model_id
        self.max_excerpt = max_excerpt
        self._prompts = _load_prompt(flow=flow, path=prompt_path)
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name="us-east-1",
                verify=False,
            )
        return self._client

    def rerank(
        self,
        doc: Any,
        query_context: str,
        heuristic_score: int = 0,
    ) -> tuple[int, str]:
        """Score a single document.

        Returns ``(score, reasoning)`` where score is 0-100.
        Falls back to *heuristic_score* on any error.
        """
        if not self._prompts:
            return heuristic_score, "prompt not loaded"

        title = getattr(doc, "title", "") or ""
        text = getattr(doc, "text", "") or ""
        source_id = getattr(doc, "source_id", "") or ""
        published = getattr(doc, "published_at", "") or ""
        geo = _detect_geo(title + " " + text)
        excerpt = text[: self.max_excerpt]

        user_msg = self._prompts["user"]
        # Use safe substitution to avoid KeyError on JSON braces in the template
        import string
        tpl = string.Template(self._prompts["user"])
        user_msg = tpl.safe_substitute(
            query_context=query_context,
            title=title,
            excerpt=excerpt,
            source=source_id,
            published_at=published,
            geo_region=geo,
        )
        system_msg = self._prompts["system"]

        try:
            client = self._get_client()
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 256,
                "temperature": 0.0,
                "system": system_msg,
                "messages": [{"role": "user", "content": user_msg}],
            })

            response = client.invoke_model(
                modelId=self.model_id,
                contentType="application/json",
                accept="application/json",
                body=body,
            )

            result = json.loads(response["body"].read())
            text_out = result["content"][0]["text"].strip()

            # Parse JSON from response (handle markdown code blocks)
            json_match = re.search(r"\{[^}]+\}", text_out, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                score = int(parsed.get("relevance_score", heuristic_score))
                reasoning = parsed.get("reasoning", "")
                score = max(0, min(100, score))
                return score, reasoning

            logger.warning("LLM rerank: could not parse JSON from response")
            return heuristic_score, "parse error"

        except Exception as exc:
            logger.warning("LLM rerank failed for '%s': %s", title[:50], exc)
            return heuristic_score, f"error: {exc}"

    def rerank_batch(
        self,
        docs: list[Any],
        query_context: str,
    ) -> list[tuple[int, str]]:
        """Re-rank a batch of documents. Returns list of (score, reasoning)."""
        results = []
        for doc in docs:
            heuristic = getattr(doc, "relevance_score", 0) or 0
            score, reason = self.rerank(doc, query_context, heuristic)
            results.append((score, reason))
        return results
