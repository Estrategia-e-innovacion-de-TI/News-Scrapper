"""CLI for search: papers, repos, patents."""
from __future__ import annotations

import argparse
import asyncio
import sys

from dotenv import load_dotenv
load_dotenv()  # Load .env from current directory or parents

from ..utils import setup_logging
from .orchestrator import run_search


def main():
    """Search CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="extractor.search",
        description="Search for papers, repos, or patents",
    )
    
    parser.add_argument("--terms", required=True, help="Path to terms YAML")
    parser.add_argument(
        "--mode",
        required=True,
        choices=["papers", "repos", "patents"],
        help="Search mode",
    )
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--since-days", type=int, default=30, help="Days back")
    parser.add_argument("--max-per-term", type=int, default=20, help="Max per term")
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    
    args = parser.parse_args()
    
    logger = setup_logging(debug=args.debug)
    logger.info(f"Search: mode={args.mode}, terms={args.terms}")
    
    try:
        candidates, report = asyncio.run(
            run_search(
                terms_path=args.terms,
                mode=args.mode,
                out_dir=args.out,
                since_days=args.since_days,
                max_per_term=args.max_per_term,
            )
        )
        
        logger.info(f"Found {len(candidates)} candidates")
        logger.info(f"Output: {args.out}/candidates.jsonl")
        logger.info(f"Report: {args.out}/search_report.json")
        return 0
        
    except Exception as e:
        logger.exception(f"Search failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
