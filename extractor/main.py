"""CLI entry point for News Radar MVP."""
from __future__ import annotations

import argparse
import asyncio
import sys

from .graph import run_extraction
from .utils import setup_logging


def parse_args() -> argparse.Namespace:
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(
        prog="news_radar",
        description="News Radar MVP - Extract news from catalog sources",
    )
    
    parser.add_argument("--catalog", default="catalog.yaml", help="Path to catalog YAML")
    parser.add_argument("--days", type=int, default=7, help="Filter last N days (default: 7)")
    parser.add_argument("--max-items-per-source", type=int, default=20, help="Max items per source")
    parser.add_argument("--out", default="out", help="Output directory")
    parser.add_argument("--debug", action="store_true", help="Debug mode")
    parser.add_argument("--dry-run", action="store_true", help="Discover only, no fetch")
    parser.add_argument("--only-source", type=str, default=None, help="Process only this source")
    parser.add_argument("--no-playwright", action="store_true", help="Disable Playwright")
    parser.add_argument("--store-raw-html", action="store_true", help="Store raw HTML samples")
    
    # Focus / ad-hoc flags
    parser.add_argument(
        "--focus",
        choices=["aras_news", "riesgos_news", "vigilancia_news"],
        default=None,
        help="Focus mode",
    )
    parser.add_argument("--adhoc", action="store_true", help="Ad-hoc query mode")
    parser.add_argument("--company", type=str, default=None, help="ARAS: company name")
    parser.add_argument("--nit", type=str, default=None, help="ARAS: NIT colombiano (alternativa a --company)")
    parser.add_argument("--terms", type=str, default=None, help="Riesgos: comma-separated terms")
    parser.add_argument(
        "--terms-preset",
        choices=["ciber", "fraude", "operacional", "ambiental_social", "all"],
        default=None,
        help="Riesgos: use a predefined set of risk terms",
    )
    parser.add_argument("--date-from", type=str, default=None, help="Ad-hoc: start date YYYY-MM-DD")
    parser.add_argument("--date-to", type=str, default=None, help="Ad-hoc: end date YYYY-MM-DD")
    parser.add_argument("--topk-per-source", type=int, default=5, help="Top K per source (adhoc)")
    parser.add_argument("--max-candidates-total", type=int, default=50, help="Max total candidates")
    parser.add_argument("--match-mode", default="metadata_only", help="Match mode (fixed)")
    
    # Classifier mode
    parser.add_argument(
        "--classifier",
        choices=["rules", "llm"],
        default="rules",
        help="Classifier backend: rules (keyword-based) or llm (Amazon Bedrock)",
    )
    
    # Candidates ingestion
    parser.add_argument("--candidates", type=str, default=None, help="Path to candidates.jsonl")
    parser.add_argument("--max-text-chars", type=int, default=50000, help="Cap text length (default: 50000)")
    
    return parser.parse_args()


def validate_args(args: argparse.Namespace) -> str | None:
    """Validate argument combinations. Returns error message or None."""
    if args.adhoc and args.focus not in ("aras_news", "riesgos_news"):
        return "--adhoc currently only supports --focus aras_news or riesgos_news"

    if args.focus == "aras_news":
        if not args.adhoc:
            return "ARAS requires --adhoc mode"
        nit = getattr(args, "nit", None)
        if not args.company and not nit:
            return "ARAS requires --company or --nit"
        if args.company and nit:
            import logging
            logging.getLogger(__name__).warning(
                "--nit is ignored when --company is provided"
            )
        if not args.date_from or not args.date_to:
            return "ARAS adhoc requires --date-from and --date-to"
        if args.date_from > args.date_to:
            return f"--date-from ({args.date_from}) must be <= --date-to ({args.date_to})"
    
    elif args.focus == "riesgos_news":
        if not args.adhoc:
            return "Riesgos requires --adhoc mode"
        terms_preset = getattr(args, "terms_preset", None)
        if not args.terms and not terms_preset:
            return "Riesgos requires --terms or --terms-preset"
        if not args.date_from or not args.date_to:
            return "Riesgos adhoc requires --date-from and --date-to"
        if args.date_from > args.date_to:
            return f"--date-from ({args.date_from}) must be <= --date-to ({args.date_to})"
    
    elif args.focus == "vigilancia_news":
        if args.adhoc:
            return "Vigilancia news does not support --adhoc (use --days)"
    
    return None


def main():
    """Main entry point."""
    args = parse_args()
    
    logger = setup_logging(debug=args.debug)
    
    # Validate
    error = validate_args(args)
    if error:
        logger.error(error)
        print(f"Error: {error}", file=sys.stderr)
        return 1
    
    logger.info("News Radar MVP starting...")
    logger.info(f"Catalog: {args.catalog}")
    logger.info(f"Output: {args.out}")
    
    if args.focus:
        logger.info(f"Focus: {args.focus}")
    if args.adhoc:
        logger.info(f"Ad-hoc mode: company={args.company}, terms={args.terms}")
        logger.info(f"Date range: {args.date_from} to {args.date_to}")
    if args.classifier != "rules":
        logger.info(f"Classifier mode: {args.classifier}")
    if args.candidates:
        logger.info(f"Candidates: {args.candidates}")
    if args.dry_run:
        logger.info("DRY RUN mode")
    
    # Resolve NIT → company name if --nit provided and --company not set
    if args.nit and not args.company:
        from .capabilities.nit_resolver import NITResolver

        try:
            resolver = NITResolver()
            result = resolver.resolve(args.nit)
        except ValueError as exc:
            logger.error(str(exc))
            print(f"Error: {exc}", file=sys.stderr)
            return 1

        if result is None:
            msg = (
                "NIT no encontrado en Base ARAS.xlsx ni tabla local. "
                "Proporcione --company en su lugar."
            )
            logger.error(msg)
            print(f"Error: {msg}", file=sys.stderr)
            return 1

        args.company = result.company_name
        logger.info(
            "NIT %s resolved to company '%s' (source=%s)",
            args.nit,
            result.company_name,
            result.source,
        )
    
    # Resolve --terms-preset and merge with --terms if needed
    terms_preset = getattr(args, "terms_preset", None)
    if terms_preset:
        from .adhoc.presets import load_presets, merge_terms, resolve_preset

        presets = load_presets()
        preset_terms = resolve_preset(terms_preset, presets)
        logger.info(
            "Preset '%s' resolved to %d terms", terms_preset, len(preset_terms)
        )

        explicit_terms = (
            [t.strip() for t in args.terms.split(",") if t.strip()]
            if args.terms
            else None
        )
        merged = merge_terms(explicit_terms, preset_terms)
        args.terms = ",".join(merged)
        logger.info("Merged terms (%d): %s", len(merged), args.terms)
    
    try:
        final_state = asyncio.run(
            run_extraction(
                catalog_path=args.catalog,
                days=args.days,
                max_items_per_source=args.max_items_per_source,
                out_dir=args.out,
                debug=args.debug,
                dry_run=args.dry_run,
                only_source=args.only_source,
                no_playwright=args.no_playwright,
                store_raw_html=args.store_raw_html,
                focus=args.focus,
                adhoc=args.adhoc,
                company=args.company,
                terms=args.terms,
                date_from=args.date_from,
                date_to=args.date_to,
                topk_per_source=args.topk_per_source,
                max_candidates_total=args.max_candidates_total,
                candidates_path=args.candidates,
                classifier_mode=args.classifier,
                nit=args.nit,
                terms_preset=getattr(args, "terms_preset", None),
            )
        )
        
        logger.info("=" * 60)
        logger.info("EXTRACTION COMPLETE")
        logger.info(f"Run ID: {final_state.run_id}")
        logger.info(f"Sources processed: {len(final_state.selected_sources)}")
        logger.info(f"Documents extracted: {len(final_state.documents)}")
        logger.info(f"Output: {args.out}/articles.jsonl")
        logger.info(f"Report: {args.out}/run_report.json")
        logger.info("=" * 60)
        
        return 0
        
    except FileNotFoundError as e:
        logger.error(f"File not found: {e}")
        return 1
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
        return 130
    except Exception as e:
        logger.exception(f"Extraction failed: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
