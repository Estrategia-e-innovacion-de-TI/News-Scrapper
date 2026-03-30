"""LLM-based historical analysis via Amazon Bedrock.

Sends article summaries to the LLM and gets back structured analysis:
clusters, trends, insights, recommendations, risk signals.

Falls back to ClusterEngine (TF-IDF) when Bedrock is unavailable.
"""
from __future__ import annotations

import json
import logging
import re
import string
from pathlib import Path
from typing import Any

import yaml

logger = logging.getLogger(__name__)

_PROMPTS_DIR = Path(__file__).resolve().parents[2] / "prompts"


def _load_prompt() -> dict[str, str]:
    path = _PROMPTS_DIR / "analyze_historical.yaml"
    try:
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh)
        return {"system": data.get("system", ""), "user": data.get("user", "")}
    except Exception:
        logger.warning("analyze prompt not found at %s", path)
        return {}


class LLMAnalyzer:
    """Analyze articles using Amazon Bedrock (Claude).

    Parameters
    ----------
    model_id : str
        Bedrock model. Use a larger model for better analysis.
    max_articles : int
        Max articles to send (to fit context window).
    """

    def __init__(
        self,
        model_id: str = "anthropic.claude-3-haiku-20240307-v1:0",
        max_articles: int = 80,
    ) -> None:
        self.model_id = model_id
        self.max_articles = max_articles
        self._prompts = _load_prompt()
        self._client: Any = None

    def _get_client(self) -> Any:
        if self._client is None:
            import boto3
            self._client = boto3.client(
                "bedrock-runtime", region_name="us-east-1", verify=False,
            )
        return self._client

    def analyze(
        self,
        articles: list[dict],
        focus: str = "vigilancia",
        date_range: str = "",
    ) -> dict[str, Any] | None:
        """Run LLM analysis on articles.

        Returns parsed JSON dict or None on failure.
        """
        if not self._prompts:
            return None

        # Build article summaries (compact format to fit context)
        sorted_arts = sorted(
            articles, key=lambda a: a.get("relevance_score", 0), reverse=True,
        )
        summaries = []
        for i, art in enumerate(sorted_arts[: self.max_articles]):
            score = art.get("relevance_score", 0)
            title = art.get("title", "")[:100]
            source = art.get("source_id", "")
            summaries.append(f"{i}. {title} | score={score} | {source}")

        article_text = "\n".join(summaries)

        tpl = string.Template(self._prompts["user"])
        user_msg = tpl.safe_substitute(
            article_summaries=article_text,
            total_articles=len(summaries),
            date_range=date_range or "no especificado",
            focus=focus,
        )

        try:
            client = self._get_client()
            body = json.dumps({
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": 4096,
                "temperature": 0.1,
                "system": self._prompts["system"],
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

            # Parse JSON from response
            json_match = re.search(r"\{.*\}", text_out, re.DOTALL)
            if json_match:
                parsed = json.loads(json_match.group())
                return parsed

            logger.warning("LLM analyze: could not parse JSON")
            return None

        except Exception as exc:
            logger.warning("LLM analyze failed: %s", exc)
            return None
