"""CLI for source evaluation."""
from __future__ import annotations

import argparse
import asyncio
import sys

from ..utils import setup_logging
from .evaluator import evaluate_sources


def main():
    """Source evaluator CLI."""
    parser = argparse.ArgumentParser(
        prog="extractor.source_eval",
        description="Evaluate new sources for catalog inclusion",
    )
    
    parser.add_argument("--input", required=True, help="Path to new_sources.yaml")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Debug logging")
    
    args = parser.parse_args()
    
    logger = setup_logging(debug=args.debug)
    logger.info(f"Evaluating sources from {args.input}")
    
    try:
        evaluations = asyncio.run(
            evaluate_sources(args.input, args.out)
        )
        
        logger.info(f"Evaluated {len(evaluations)} sources")
        logger.info(f"Patch: {args.out}/catalog_patch.yaml")
        logger.info(f"Scorecard: {args.out}/source_scorecard.json")
        return 0
        
    except Exception as e:
        logger.exception(f"Evaluation failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
