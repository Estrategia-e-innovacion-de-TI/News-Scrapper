"""Bedrock adapter for embeddings and LLM invocations.

Provides a unified interface to AWS Bedrock for:
- Titan Embed v2 embeddings with JSONL file cache
- Claude Haiku invocations for classification, reranking, and cluster labelling

Validates: Requirements 1.1, 2.1, 14.2-14.3
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
from pathlib import Path
from typing import Any

logger = logging.getLogger("newsradar.bedrock")

# Default model IDs
DEFAULT_EMBED_MODEL = "amazon.titan-embed-text-v2:0"
DEFAULT_CLAUDE_MODEL = "anthropic.claude-3-haiku-20240307-v1:0"

# Embedding dimension for Titan Embed v2
EMBED_DIMENSION = 1024

# Cache directory for embeddings
DEFAULT_CACHE_DIR = Path("data/embeddings_cache")


class BedrockAdapter:
    """Adapter for AWS Bedrock runtime services.

    Provides lazy-init clients for ``bedrock-runtime`` and caches
    embeddings in a JSONL file to avoid re-computation.

    Parameters
    ----------
    region : str
        AWS region for the Bedrock client.
    embed_model : str
        Model ID for Titan Embed v2.
    claude_model : str
        Model ID for Claude Haiku.
    cache_dir : Path | str | None
        Directory for the embeddings JSONL cache.  ``None`` disables caching.
    """

    def __init__(
        self,
        region: str | None = None,
        embed_model: str = DEFAULT_EMBED_MODEL,
        claude_model: str = DEFAULT_CLAUDE_MODEL,
        cache_dir: Path | str | None = DEFAULT_CACHE_DIR,
    ) -> None:
        self.region = region or os.environ.get("AWS_REGION", "us-east-1")
        self.embed_model = embed_model
        self.claude_model = claude_model
        self._client: Any = None
        self._cache_dir = Path(cache_dir) if cache_dir else None
        self._cache: dict[str, list[float]] = {}
        self._cache_loaded = False

    # ── Lazy client ───────────────────────────────────────────────────

    def _get_client(self) -> Any:
        """Lazily create the ``bedrock-runtime`` boto3 client."""
        if self._client is None:
            try:
                import boto3

                self._client = boto3.client(
                    "bedrock-runtime",
                    region_name=self.region,
                    verify=False,
                )
                logger.info("Bedrock client initialised (region=%s)", self.region)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to create bedrock-runtime client: {exc}"
                ) from exc
        return self._client

    # ── Embeddings cache ──────────────────────────────────────────────

    @property
    def _cache_path(self) -> Path | None:
        if self._cache_dir is None:
            return None
        return self._cache_dir / "embeddings_cache.jsonl"

    def _load_cache(self) -> None:
        """Load the JSONL embeddings cache from disk."""
        if self._cache_loaded:
            return
        self._cache_loaded = True
        path = self._cache_path
        if path is None or not path.exists():
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    entry = json.loads(line)
                    key = entry.get("key", "")
                    vec = entry.get("embedding", [])
                    if key and vec:
                        self._cache[key] = vec
            logger.info("Loaded %d cached embeddings from %s", len(self._cache), path)
        except Exception as exc:
            logger.warning("Failed to load embeddings cache: %s", exc)

    def _save_to_cache(self, key: str, embedding: list[float]) -> None:
        """Append a single embedding to the JSONL cache file."""
        self._cache[key] = embedding
        path = self._cache_path
        if path is None:
            return
        try:
            path.parent.mkdir(parents=True, exist_ok=True)
            with open(path, "a", encoding="utf-8") as f:
                f.write(json.dumps({"key": key, "embedding": embedding}) + "\n")
        except Exception as exc:
            logger.warning("Failed to write to embeddings cache: %s", exc)

    @staticmethod
    def _text_hash(text: str) -> str:
        """SHA-256 hash of text for cache key."""
        return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()[:32]

    # ── Embeddings API ────────────────────────────────────────────────

    def get_embeddings(self, texts: list[str]) -> list[list[float]]:
        """Compute embeddings for a list of texts using Titan Embed v2.

        Uses a JSONL file cache to avoid re-computation.  Texts that are
        already cached are returned from the cache; only new texts are
        sent to Bedrock.

        Parameters
        ----------
        texts : list[str]
            Input texts to embed.

        Returns
        -------
        list[list[float]]
            One embedding vector per input text.

        Validates: Requirements 14.2-14.3
        """
        self._load_cache()

        results: list[list[float]] = []
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            key = self._text_hash(text)
            if key in self._cache:
                results.append(self._cache[key])
            else:
                results.append([])  # placeholder
                uncached_indices.append(i)
                uncached_texts.append(text)

        if not uncached_texts:
            logger.debug("All %d embeddings served from cache", len(texts))
            return results

        logger.info(
            "Computing %d embeddings (%d cached, %d new)",
            len(texts), len(texts) - len(uncached_texts), len(uncached_texts),
        )

        client = self._get_client()

        for idx, text in zip(uncached_indices, uncached_texts):
            try:
                body = json.dumps({
                    "inputText": text[:8000],  # Titan Embed v2 max input
                    "dimensions": EMBED_DIMENSION,
                    "normalize": True,
                })
                response = client.invoke_model(
                    modelId=self.embed_model,
                    contentType="application/json",
                    accept="application/json",
                    body=body,
                )
                resp_body = json.loads(response["body"].read())
                embedding = resp_body.get("embedding", [])

                results[idx] = embedding
                self._save_to_cache(self._text_hash(text), embedding)

            except Exception as exc:
                logger.warning("Embedding failed for text[%d]: %s", idx, exc)
                # Return zero vector as fallback
                results[idx] = [0.0] * EMBED_DIMENSION

        return results

    # ── Claude invocation ─────────────────────────────────────────────

    def invoke_claude(
        self,
        prompt: str,
        system: str = "",
        max_tokens: int = 1024,
    ) -> str:
        """Invoke Claude Haiku for classification, reranking, or labelling.

        Parameters
        ----------
        prompt : str
            User message / prompt text.
        system : str
            Optional system prompt.
        max_tokens : int
            Maximum tokens in the response.

        Returns
        -------
        str
            The text content of Claude's response.

        Validates: Requirements 1.1, 2.1
        """
        client = self._get_client()

        messages = [{"role": "user", "content": prompt}]

        body: dict[str, Any] = {
            "anthropic_version": "bedrock-2023-05-31",
            "max_tokens": max_tokens,
            "messages": messages,
        }
        if system:
            body["system"] = system

        try:
            response = client.invoke_model(
                modelId=self.claude_model,
                contentType="application/json",
                accept="application/json",
                body=json.dumps(body),
            )
            resp_body = json.loads(response["body"].read())
            content_blocks = resp_body.get("content", [])
            if content_blocks:
                return content_blocks[0].get("text", "")
            return ""
        except Exception as exc:
            logger.error("Claude invocation failed: %s", exc)
            raise

    # ── Availability check ────────────────────────────────────────────

    def is_available(self) -> bool:
        """Check if Bedrock is reachable by attempting to create the client."""
        try:
            self._get_client()
            return True
        except Exception:
            return False


__all__ = [
    "BedrockAdapter",
    "DEFAULT_EMBED_MODEL",
    "DEFAULT_CLAUDE_MODEL",
    "EMBED_DIMENSION",
]
