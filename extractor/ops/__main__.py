"""CLI for operations: tiering and diagnostics."""
from __future__ import annotations

import argparse
import asyncio
import json
import subprocess
import sys
from pathlib import Path

from ..catalog import load_catalog
from .tiering import (
    classify_sources,
    build_prod_set,
    export_prod_plan,
    export_tiers,
    load_run_report,
)
from .catalog_filter import write_catalog_prod, write_tier_catalogs


def cmd_tier(args: argparse.Namespace) -> int:
    """Execute tier classification and catalog generation."""
    print(f"Loading run report: {args.run_report}")
    report = load_run_report(args.run_report)
    
    print(f"Loading catalog: {args.catalog}")
    catalog = load_catalog(args.catalog)
    
    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    
    # Classify sources
    print("Classifying sources into tiers...")
    tiers = classify_sources(report)
    
    print(f"  Tier0 (prod-ready): {len(tiers['tier0'])} sources")
    print(f"  Tier1 (conditional): {len(tiers['tier1'])} sources")
    print(f"  Tier2 (problematic): {len(tiers['tier2'])} sources")
    
    # Export tiers.json
    tiers_path = export_tiers(tiers, out_dir / "tiers.json")
    print(f"  -> {tiers_path}")
    
    # Write tier catalogs
    print("Writing tier catalogs...")
    tier_paths = write_tier_catalogs(args.catalog, tiers, out_dir)
    for tier_name, path in tier_paths.items():
        print(f"  -> {path}")
    
    # Build prod set
    print(f"Building production set (mode {args.prod_mode})...")
    prod_set = build_prod_set(report, mode=args.prod_mode)
    
    print(f"  HTTP lane: {len(prod_set['http_lane'])} sources")
    print(f"  Browser lane: {len(prod_set['browser_lane'])} sources")
    print(f"  Excluded: {len(prod_set['excluded'])} sources")
    
    # Export prod_plan.json
    plan_path = export_prod_plan(
        prod_set,
        args.prod_mode,
        out_dir / "prod_plan.json",
        notes=f"Generated from {args.run_report}",
    )
    print(f"  -> {plan_path}")
    
    # Write catalog_prod.yaml
    prod_catalog_path = write_catalog_prod(catalog, prod_set, out_dir / "catalog_prod.yaml")
    print(f"  -> {prod_catalog_path}")
    
    # Summary
    print("\n" + "=" * 60)
    print("TIER CLASSIFICATION COMPLETE")
    print("=" * 60)
    print(f"Tier0: {tiers['tier0']}")
    print(f"Tier1: {tiers['tier1']}")
    print(f"Tier2: {tiers['tier2']}")
    
    if prod_set["excluded"]:
        print("\nExcluded from PROD:")
        for exc in prod_set["excluded"]:
            print(f"  - {exc['source_id']}: {exc['reason']}")
    
    return 0


def cmd_diagnose_tier2(args: argparse.Namespace) -> int:
    """Run diagnostics on Tier2 sources."""
    out_dir = Path(args.out_dir)
    tiers_path = out_dir / "tiers.json"
    
    # Load or recalculate tiers
    if tiers_path.exists():
        print(f"Loading tiers from {tiers_path}")
        with open(tiers_path, "r") as f:
            tiers = json.load(f)
    else:
        print(f"Calculating tiers from {args.run_report}")
        report = load_run_report(args.run_report)
        tiers = classify_sources(report)
    
    tier2_sources = tiers.get("tier2", [])
    
    if not tier2_sources:
        print("No Tier2 sources to diagnose.")
        return 0
    
    print(f"Diagnosing {len(tier2_sources)} Tier2 sources...")
    
    diagnostics_dir = out_dir / "diagnostics"
    diagnostics_dir.mkdir(parents=True, exist_ok=True)
    
    results = []
    
    for source_id in tier2_sources:
        print(f"\n[{source_id}] Running diagnostic...")
        
        source_out = diagnostics_dir / source_id
        source_out.mkdir(parents=True, exist_ok=True)
        
        cmd = [
            sys.executable, "-m", "extractor.main",
            "--catalog", args.catalog,
            "--only-source", source_id,
            "--days", "3",
            "--max-items-per-source", "5",
            "--out", str(source_out),
            "--debug",
        ]
        
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,
                cwd=Path(__file__).parent.parent.parent,
            )
            
            # Check for run_report in output
            source_report_path = source_out / "run_report.json"
            if source_report_path.exists():
                with open(source_report_path) as f:
                    source_report = json.load(f)
                
                by_source = source_report.get("by_source", {})
                metrics = by_source.get(source_id, {})
                
                results.append({
                    "source_id": source_id,
                    "status": "completed",
                    "discovered": metrics.get("discovered", 0),
                    "fetched_ok": metrics.get("fetched_ok", 0),
                    "text_ok": metrics.get("text_ok", 0),
                    "errors": metrics.get("errors", 0),
                    "errors_by_type": metrics.get("errors_by_type", {}),
                    "exit_code": result.returncode,
                })
                
                status = "OK" if metrics.get("text_ok", 0) > 0 else "FAILED"
                print(f"  [{status}] discovered={metrics.get('discovered', 0)}, "
                      f"text_ok={metrics.get('text_ok', 0)}, errors={metrics.get('errors', 0)}")
            else:
                results.append({
                    "source_id": source_id,
                    "status": "no_report",
                    "exit_code": result.returncode,
                    "stderr": result.stderr[:500] if result.stderr else "",
                })
                print(f"  [NO REPORT] exit_code={result.returncode}")
                
        except subprocess.TimeoutExpired:
            results.append({
                "source_id": source_id,
                "status": "timeout",
            })
            print(f"  [TIMEOUT]")
        except Exception as e:
            results.append({
                "source_id": source_id,
                "status": "error",
                "error": str(e),
            })
            print(f"  [ERROR] {e}")
    
    # Write diagnose report
    diagnose_report_path = diagnostics_dir / "diagnose_report.json"
    with open(diagnose_report_path, "w", encoding="utf-8") as f:
        json.dump({
            "total": len(tier2_sources),
            "results": results,
        }, f, indent=2, ensure_ascii=False)
    
    print(f"\n-> Diagnose report: {diagnose_report_path}")
    
    # Summary
    ok_count = sum(1 for r in results if r.get("text_ok", 0) > 0)
    print(f"\nSummary: {ok_count}/{len(tier2_sources)} sources recovered")
    
    return 0


def main():
    """Main CLI entry point."""
    parser = argparse.ArgumentParser(
        prog="extractor.ops",
        description="Operations tools for News Radar MVP",
    )
    
    subparsers = parser.add_subparsers(dest="command", required=True)
    
    # tier subcommand
    tier_parser = subparsers.add_parser("tier", help="Classify sources and generate catalogs")
    tier_parser.add_argument("--catalog", required=True, help="Path to catalog.yaml")
    tier_parser.add_argument("--run-report", required=True, help="Path to run_report.json")
    tier_parser.add_argument("--out-dir", default="out", help="Output directory")
    tier_parser.add_argument("--prod-mode", choices=["A", "B"], default="B", help="Production mode")
    
    # diagnose-tier2 subcommand
    diag_parser = subparsers.add_parser("diagnose-tier2", help="Run diagnostics on Tier2 sources")
    diag_parser.add_argument("--catalog", required=True, help="Path to catalog.yaml")
    diag_parser.add_argument("--run-report", required=True, help="Path to run_report.json")
    diag_parser.add_argument("--out-dir", default="out", help="Output directory")
    
    args = parser.parse_args()
    
    if args.command == "tier":
        return cmd_tier(args)
    elif args.command == "diagnose-tier2":
        return cmd_diagnose_tier2(args)
    
    return 1


if __name__ == "__main__":
    sys.exit(main())
