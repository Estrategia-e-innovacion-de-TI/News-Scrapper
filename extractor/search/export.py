"""Export search results to JSONL and report."""
from __future__ import annotations

import json
from pathlib import Path

from .models import SearchCandidate, SearchReport


def save_candidates_jsonl(
    candidates: list[SearchCandidate],
    out_dir: str | Path,
) -> Path:
    """Save candidates to JSONL file."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    path = out_dir / "candidates.jsonl"
    with open(path, "w", encoding="utf-8") as f:
        for c in candidates:
            f.write(json.dumps(c.model_dump(), ensure_ascii=False) + "\n")
    
    return path


def save_search_report(
    report: SearchReport,
    out_dir: str | Path,
) -> Path:
    """Save search report to JSON."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    path = out_dir / "search_report.json"
    with open(path, "w", encoding="utf-8") as f:
        json.dump(report.model_dump(), f, indent=2, ensure_ascii=False)
    
    return path


def load_candidates_jsonl(path: str | Path) -> list[SearchCandidate]:
    """Load candidates from JSONL file."""
    path = Path(path)
    candidates = []
    
    with open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                data = json.loads(line)
                candidates.append(SearchCandidate(**data))
    
    return candidates
