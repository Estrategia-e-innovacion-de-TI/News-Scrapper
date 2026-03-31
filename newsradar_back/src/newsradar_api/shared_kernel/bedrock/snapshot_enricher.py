"""Bedrock enrichment for analytical snapshots."""
from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
import hashlib
import json
import logging
import os
import re
import string
from typing import Any

from newsradar_api.application.config import ApiConfig
from newsradar_api.infrastructure.driven_adapters.bedrock_adapter import BedrockAdapter
from newsradar_api.shared_kernel.config.paths import load_yaml_file, resolve_flow_path, resolve_prompt_path

import yaml

logger = logging.getLogger(__name__)

_PROMPT_FILE_MAP = {
    "trend_mapping": "snapshot_trendmap.yaml",
    "risk_mapping": "snapshot_riskmap.yaml",
}
_FLOW_FILE_MAP = {
    "trend_mapping": "trend_mapping.yaml",
    "risk_mapping": "risk_mapping.yaml",
}


@dataclass(slots=True)
class PromptBundle:
    prompt_key: str
    version: str
    prompt_file: str
    prompt_hash: str
    cluster_system: str
    cluster_user: str
    report_system: str
    report_user: str
    content_json: dict[str, Any]


def _credential_hints_present() -> bool:
    hints = [
        "AWS_ACCESS_KEY_ID",
        "AWS_PROFILE",
        "AWS_WEB_IDENTITY_TOKEN_FILE",
        "AWS_CONTAINER_CREDENTIALS_RELATIVE_URI",
        "AWS_CONTAINER_CREDENTIALS_FULL_URI",
        "AWS_SESSION_TOKEN",
    ]
    return any(os.getenv(name) for name in hints)


def _extract_json(text: str) -> dict[str, Any]:
    for candidate in _json_candidates(text):
        parsed = _parse_json_candidate(candidate)
        if parsed:
            return parsed
    return {}


def _json_candidates(text: str) -> list[str]:
    stripped = text.strip()
    if not stripped:
        return []

    candidates: list[str] = [stripped]

    fenced_blocks = re.findall(r"```(?:json)?\s*(.*?)```", stripped, flags=re.DOTALL | re.IGNORECASE)
    candidates.extend(block.strip() for block in fenced_blocks if block.strip())

    balanced = _extract_balanced_json(stripped)
    if balanced:
        candidates.append(balanced)

    deduped: list[str] = []
    seen: set[str] = set()
    for candidate in candidates:
        normalized = candidate.strip()
        if normalized and normalized not in seen:
            seen.add(normalized)
            deduped.append(normalized)
    return deduped


def _extract_balanced_json(text: str) -> str | None:
    start = None
    opening = ""
    closing = ""
    depth = 0
    in_string = False
    escape = False

    for index, char in enumerate(text):
        if start is None:
            if char == "{":
                start = index
                opening, closing = "{", "}"
                depth = 1
            elif char == "[":
                start = index
                opening, closing = "[", "]"
                depth = 1
            continue

        if escape:
            escape = False
            continue
        if char == "\\":
            escape = True
            continue
        if char == '"':
            in_string = not in_string
            continue
        if in_string:
            continue
        if char == opening:
            depth += 1
        elif char == closing:
            depth -= 1
            if depth == 0:
                return text[start:index + 1]
    return None


def _remove_trailing_commas(text: str) -> str:
    return re.sub(r",(\s*[}\]])", r"\1", text)


def _parse_json_candidate(candidate: str) -> dict[str, Any]:
    if not candidate:
        return {}

    attempts = [
        candidate.strip(),
        _remove_trailing_commas(candidate.strip()),
    ]
    for attempt in attempts:
        try:
            parsed = json.loads(attempt)
            return parsed if isinstance(parsed, dict) else {}
        except json.JSONDecodeError:
            pass

    for attempt in attempts:
        try:
            parsed = yaml.safe_load(attempt)
            return parsed if isinstance(parsed, dict) else {}
        except yaml.YAMLError:
            pass
    return {}


def _safe_string_list(value: Any, limit: int) -> list[str]:
    if not isinstance(value, list):
        return []
    result: list[str] = []
    for item in value:
        text = str(item).strip()
        if text:
            result.append(text)
        if len(result) >= limit:
            break
    return result


def _safe_text(value: Any) -> str:
    if value is None:
        return ""
    return str(value).strip()


class SnapshotLLMEnricher:
    """Enrich trend/risk snapshot payloads using Amazon Bedrock."""

    def __init__(
        self,
        report_type: str,
        *,
        model_id: str | None = None,
        region: str | None = None,
        llm_mode: str | None = None,
    ) -> None:
        cfg = ApiConfig.load()
        self.report_type = report_type
        self.model_id = model_id or cfg.bedrock_model_id
        self.region = region or cfg.aws_region
        self.llm_mode = (llm_mode or os.getenv("NEWSRADAR_SNAPSHOT_LLM_MODE", "auto")).lower()
        self._bundle: PromptBundle | None = None
        self._adapter: BedrockAdapter | None = None

    def enrich_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        parameters = payload.setdefault("parameters", {})
        trace = {
            "enabled": self.llm_mode != "disabled",
            "used": False,
            "report_type": self.report_type,
            "model_id": self.model_id,
            "provider": "bedrock",
            "mode": self.llm_mode,
            "cluster_calls": 0,
            "report_calls": 0,
            "errors": [],
        }

        if not self._should_attempt():
            trace["reason"] = "snapshot llm disabled or no aws runtime hints"
            parameters["llm_enrichment"] = trace
            return payload

        bundle = self._load_prompt_bundle()
        if bundle is None:
            trace["reason"] = "prompt bundle not found"
            parameters["llm_enrichment"] = trace
            return payload

        trace.update(
            {
                "prompt_key": bundle.prompt_key,
                "prompt_version": bundle.version,
                "prompt_file": bundle.prompt_file,
                "prompt_hash": bundle.prompt_hash,
                "_content_json": bundle.content_json,
            }
        )

        try:
            self._adapter = BedrockAdapter(
                region=self.region,
                claude_model=self.model_id,
                cache_dir=None,
            )
            self._enrich_clusters(payload, bundle, trace)
            self._enrich_report(payload, bundle, trace)
            trace["used"] = True
            payload["llm_analysis"] = {
                "provider": "bedrock",
                "model_id": self.model_id,
                "cluster_calls": trace["cluster_calls"],
                "report_calls": trace["report_calls"],
                "errors": trace["errors"],
            }
        except Exception as exc:  # noqa: BLE001
            logger.warning("Snapshot LLM enrichment failed for %s: %s", self.report_type, exc)
            trace["errors"].append(str(exc))
            trace["reason"] = f"fallback after llm error: {exc}"

        parameters["llm_enrichment"] = trace
        return payload

    def _should_attempt(self) -> bool:
        if self.llm_mode == "disabled":
            return False
        if self.llm_mode == "enabled":
            return True
        return _credential_hints_present()

    def _load_prompt_bundle(self) -> PromptBundle | None:
        if self._bundle is not None:
            return self._bundle
        filename = self._resolve_prompt_filename()
        if not filename:
            return None
        path = resolve_prompt_path(filename)
        if not path.exists():
            return None
        with open(path, "r", encoding="utf-8") as fh:
            data = yaml.safe_load(fh) or {}
        raw_text = json.dumps(data, ensure_ascii=False, sort_keys=True)
        self._bundle = PromptBundle(
            prompt_key=str(data.get("prompt_key") or path.stem),
            version=str(data.get("version") or "v1"),
            prompt_file=str(path),
            prompt_hash=hashlib.sha256(raw_text.encode("utf-8")).hexdigest(),
            cluster_system=str(data.get("cluster_system") or ""),
            cluster_user=str(data.get("cluster_user") or ""),
            report_system=str(data.get("report_system") or ""),
            report_user=str(data.get("report_user") or ""),
            content_json=data,
        )
        return self._bundle

    def _resolve_prompt_filename(self) -> str | None:
        flow_filename = _FLOW_FILE_MAP.get(self.report_type)
        if flow_filename:
            flow_path = resolve_flow_path(flow_filename)
            if flow_path.exists():
                flow_config = load_yaml_file(flow_path)
                analytics = flow_config.get("analytics", {})
                prompt_filename = analytics.get("snapshot_llm_prompt")
                if isinstance(prompt_filename, str) and prompt_filename.strip():
                    return prompt_filename.strip()
        return _PROMPT_FILE_MAP.get(self.report_type)

    def _invoke(self, system_prompt: str, user_template: str, **kwargs: str) -> dict[str, Any]:
        if self._adapter is None:
            raise RuntimeError("Bedrock adapter not initialised")
        rendered = string.Template(user_template).safe_substitute(**kwargs)
        text = self._adapter.invoke_claude(rendered, system=system_prompt, max_tokens=700)
        parsed = _extract_json(text)
        if not parsed:
            preview = " ".join(text.split())[:220]
            raise ValueError(f"invalid JSON returned by Bedrock: {preview}")
        return parsed

    def _enrich_clusters(self, payload: dict[str, Any], bundle: PromptBundle, trace: dict[str, Any]) -> None:
        clusters = payload.get("clusters") or []
        documents = payload.get("documents") or payload.get("articles") or []
        document_index = {}
        for item in documents:
            cluster_id = item.get("cluster_id")
            if cluster_id:
                document_index.setdefault(cluster_id, []).append(item)

        for cluster in clusters[:12]:
            cluster_id = cluster.get("cluster_id")
            top_documents = cluster.get("top_documents") or document_index.get(cluster_id, [])[:3]
            response = self._invoke(
                bundle.cluster_system,
                bundle.cluster_user,
                report_type=self.report_type,
                allowed_categories_json=json.dumps(bundle.content_json.get("allowed_categories") or [], ensure_ascii=False),
                cluster_json=json.dumps(cluster, ensure_ascii=False),
                top_documents_json=json.dumps(top_documents, ensure_ascii=False),
            )
            trace["cluster_calls"] += 1
            if response.get("label"):
                cluster["label"] = str(response["label"]).strip()
            if response.get("category"):
                cluster["category"] = str(response["category"]).strip()
            if response.get("summary"):
                cluster["summary"] = str(response["summary"]).strip()
            keywords = _safe_string_list(response.get("keywords"), 6)
            if keywords:
                cluster["keywords"] = keywords
                cluster["top_keywords"] = keywords
            if response.get("relevance"):
                cluster["relevance"] = str(response["relevance"]).strip().lower()
            if response.get("executive_takeaway"):
                cluster["executive_takeaway"] = str(response["executive_takeaway"]).strip()
            if self.report_type == "risk_mapping":
                if response.get("dominant_risk"):
                    cluster["dominant_risk"] = str(response["dominant_risk"]).strip()
                elif cluster.get("category"):
                    cluster["dominant_risk"] = str(cluster["category"]).strip()
            cluster["semantic_source"] = "llm"
            cluster["category_source"] = "llm"

        self._refresh_payload_views(payload)
        payload.setdefault("parameters", {})["cluster_semantics_source"] = "llm"

    def _enrich_report(self, payload: dict[str, Any], bundle: PromptBundle, trace: dict[str, Any]) -> None:
        summary = payload.get("summary") or {}
        clusters = payload.get("clusters") or []
        top_documents = payload.get("top_documents") or []
        source_mix = (
            payload.get("sources_used")
            if isinstance(payload.get("sources_used"), list)
            else payload.get("charts", {}).get("source_mix", [])
        )
        response = self._invoke(
            bundle.report_system,
            bundle.report_user,
            report_type=self.report_type,
            summary_json=json.dumps(summary, ensure_ascii=False),
            clusters_json=json.dumps(clusters[:8], ensure_ascii=False),
            top_documents_json=json.dumps(top_documents[:5], ensure_ascii=False),
            source_mix_json=json.dumps(source_mix, ensure_ascii=False),
        )
        trace["report_calls"] += 1

        executive = response.get("executive_summary")
        if executive:
            summary["executive_summary"] = str(executive).strip()
            payload["executive_summary"] = str(executive).strip()
        insights = _safe_string_list(response.get("insights"), 6)
        if insights:
            payload["insights"] = insights
        recommendations = _safe_string_list(response.get("recommendations"), 6)
        if recommendations:
            payload["recommendations"] = recommendations
        risk_signals = response.get("risk_signals")
        if isinstance(risk_signals, list):
            normalized_signals: list[dict[str, Any]] = []
            for signal in risk_signals[:6]:
                if not isinstance(signal, dict):
                    continue
                normalized_signals.append(
                    {
                        "type": str(signal.get("type") or "signal").strip(),
                        "description": str(signal.get("description") or "").strip(),
                        "severity": str(signal.get("severity") or "M").strip().upper()[:1] or "M",
                        "related_clusters": _safe_string_list(signal.get("related_clusters"), 5),
                    }
                )
            if normalized_signals:
                payload["risk_signals"] = normalized_signals

    def _refresh_payload_views(self, payload: dict[str, Any]) -> None:
        clusters = payload.get("clusters") or []
        labels_by_cluster = {
            _safe_text(cluster.get("cluster_id")): _safe_text(cluster.get("label"))
            for cluster in clusters
            if cluster.get("cluster_id")
        }
        categories_by_cluster = {
            _safe_text(cluster.get("cluster_id")): _safe_text(
                cluster.get("dominant_risk") if self.report_type == "risk_mapping" else cluster.get("category")
            )
            for cluster in clusters
            if cluster.get("cluster_id")
        }

        documents = payload.get("documents") or payload.get("articles") or []
        for item in documents:
            cluster_id = _safe_text(item.get("cluster_id"))
            if not cluster_id or cluster_id == "sin_cluster":
                continue
            if cluster_id in labels_by_cluster:
                item["cluster_label"] = labels_by_cluster[cluster_id]
            if cluster_id in categories_by_cluster:
                if self.report_type == "risk_mapping":
                    item["dominant_risk"] = categories_by_cluster[cluster_id]
                else:
                    item["category"] = categories_by_cluster[cluster_id]

        for entry in payload.get("timeline") or payload.get("trends") or []:
            cluster_id = _safe_text(entry.get("cluster_id"))
            if not cluster_id or cluster_id not in labels_by_cluster:
                continue
            if "topic" in entry:
                entry["topic"] = labels_by_cluster[cluster_id]
            if "risk" in entry:
                entry["risk"] = labels_by_cluster[cluster_id]

        super_clusters = self._build_super_clusters(clusters)
        if "super_clusters" in payload:
            payload["super_clusters"] = super_clusters

        summary = payload.get("summary")
        if isinstance(summary, dict):
            summary["total_clusters"] = len(clusters)
            if self.report_type == "trend_mapping":
                summary["dominant_topics"] = [
                    label
                    for label in (_safe_text(cluster.get("label")) for cluster in clusters[:5])
                    if label
                ]
                summary["emerging_topics"] = [
                    _safe_text(cluster.get("label"))
                    for cluster in clusters
                    if _safe_text(cluster.get("direction")) == "up"
                    and float(cluster.get("horizon_score") or 0) >= 0.45
                ][:3]
                summary["consolidating_topics"] = [
                    _safe_text(cluster.get("label"))
                    for cluster in clusters
                    if _safe_text(cluster.get("maturity_stage")) in {"slope_of_enlightenment", "plateau_of_productivity"}
                ][:3]
            else:
                summary["dominant_risks"] = [
                    label
                    for label in (
                        _safe_text(cluster.get("dominant_risk") or cluster.get("category") or cluster.get("label"))
                        for cluster in clusters[:5]
                    )
                    if label
                ]

        meta = payload.get("meta")
        if isinstance(meta, dict):
            meta["total_clusters"] = len(clusters)
            meta["total_categories"] = len(super_clusters)

        charts = payload.get("charts")
        if isinstance(charts, dict):
            charts["cluster_sizes"] = [
                {
                    "label": _safe_text(cluster.get("label")),
                    "count": int(cluster.get("item_count") or cluster.get("documents") or 0),
                }
                for cluster in clusters
            ]
            charts["hype_cycle"] = [
                {
                    "label": _safe_text(cluster.get("label")),
                    "x": round(float(cluster.get("horizon_score") or 0) * 100, 2),
                    "y": float(cluster.get("impact_score") or cluster.get("avg_score") or 0),
                }
                for cluster in clusters
            ]

    def _build_super_clusters(self, clusters: list[dict[str, Any]]) -> list[dict[str, Any]]:
        grouped: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for cluster in clusters:
            category = _safe_text(
                cluster.get("dominant_risk") if self.report_type == "risk_mapping" else cluster.get("category")
            ) or ("Otros riesgos" if self.report_type == "risk_mapping" else "Innovacion general")
            grouped[category].append(cluster)

        result: list[dict[str, Any]] = []
        for category, related_clusters in sorted(grouped.items(), key=lambda item: len(item[1]), reverse=True):
            result.append(
                {
                    "category": category,
                    "clusters": [
                        _safe_text(cluster.get("cluster_id"))
                        for cluster in related_clusters
                        if cluster.get("cluster_id")
                    ],
                    "hull_polygon": [
                        [
                            float((cluster.get("coords") or {}).get("x", 0.0)),
                            float((cluster.get("coords") or {}).get("y", 0.0)),
                        ]
                        for cluster in related_clusters
                    ],
                    "total_items": sum(int(cluster.get("item_count") or cluster.get("documents") or 0) for cluster in related_clusters),
                    "avg_impact": round(
                        sum(float(cluster.get("impact_score") or cluster.get("avg_score") or 0) for cluster in related_clusters)
                        / max(len(related_clusters), 1),
                        1,
                    ),
                }
            )
        return result
