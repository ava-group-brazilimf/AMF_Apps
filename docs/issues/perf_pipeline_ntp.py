#!/usr/bin/env python3
"""
perf_pipeline_ntp.py — AVA Fabric Pipeline NTP Performance Analyzer
====================================================================
NTP-style measurement: reconstructs pipeline phase timings from file mtime
stamps, identifies idle gaps (subagent call periods), reports token budgets,
and flags projects that exceed the context-window danger threshold.

Usage:
    python docs/issues/perf_pipeline_ntp.py --project processaERP-008
    python docs/issues/perf_pipeline_ntp.py --project processaERP-008 --phase f1
    python docs/issues/perf_pipeline_ntp.py --all           # analyze all projects

Exit codes:
    0 — HEALTHY  (no threshold exceeded)
    1 — WARNING  (token threshold > 400K or gap > 30 min)
    2 — CRITICAL (token threshold > 700K or gap > 60 min)
"""

import argparse
import datetime
import json
import os
import sys

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
PROJECTS_DIR = os.path.join(REPO_ROOT, "projects")

TOKEN_WARN_THRESHOLD  = 400_000   # tokens → WARNING
TOKEN_CRIT_THRESHOLD  = 700_000   # tokens → CRITICAL
GAP_WARN_THRESHOLD_S  = 1_800     # 30 min → WARNING gap
GAP_CRIT_THRESHOLD_S  = 3_600     # 60 min → CRITICAL gap

F1_EXPECTED_ARTIFACTS = [
    "master-report.md",
    "architecture-blueprint.md",
    "bounded-context-map.md",
    "inventory-report.md",
    "gaps-risks-report.md",
    os.path.join("docs", "functional-requirements.md"),
    os.path.join("docs", "business-rules.md"),
    os.path.join("docs", "screen-navigation-map.md"),
    os.path.join("db", "schema-inventory.md"),
    os.path.join("db", "er-diagram.mmd"),
    os.path.join("db", "stored-procedures-map.md"),
]

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def fmt_dur(seconds: float) -> str:
    if seconds < 60:
        return f"{seconds:.0f}s"
    m, s = divmod(int(seconds), 60)
    return f"{m}m {s:02d}s"


def fmt_ts(ts_unix: float) -> str:
    return datetime.datetime.fromtimestamp(ts_unix).strftime("%H:%M:%S")


def walk_outputs(project: str, phase: str = "asis") -> list:
    base = os.path.join(PROJECTS_DIR, project, "outputs", phase)
    if not os.path.isdir(base):
        return []
    files = []
    for root, _, fnames in os.walk(base):
        for fname in fnames:
            fp = os.path.join(root, fname)
            st = os.stat(fp)
            rel = os.path.relpath(fp, base)
            files.append({
                "path": rel,
                "abs": fp,
                "mtime": st.st_mtime,
                "size_kb": round(st.st_size / 1024, 1),
            })
    files.sort(key=lambda x: x["mtime"])
    return files


def load_token_metrics(project: str) -> dict:
    """Read compressed/metrics.jsonl to get token counts."""
    metrics_path = os.path.join(
        PROJECTS_DIR, project, "outputs", "asis",
        "delphi-ast-raw", "compressed", "metrics.jsonl"
    )
    log_path = os.path.join(
        PROJECTS_DIR, project, "outputs", "asis",
        "delphi-ast-raw", "run_delphi_ast_analysis.log"
    )
    result = {"total_raw": 0, "total_compressed": 0, "per_artifact": {}, "source": "none"}

    # Try log file first (reliable source)
    if os.path.exists(log_path):
        with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()
        import re
        total_match = re.search(r"TOTAL:\s*([\d,]+)\s*->\s*([\d,]+)\s*tokens", content)
        if total_match:
            result["total_raw"] = int(total_match.group(1).replace(",", ""))
            result["total_compressed"] = int(total_match.group(2).replace(",", ""))
            result["source"] = "log"

        # Per-artifact
        art_matches = re.findall(
            r"\[(\d+)/\d+\]\s+(\S+)\s+([\d,]+)\s+->\s+([\d,]+)\s+tok\s+\((-?[\d.]+)%\)",
            content
        )
        for idx, name, raw, comp, pct in art_matches:
            result["per_artifact"][name] = {
                "raw": int(raw.replace(",", "")),
                "compressed": int(comp.replace(",", "")),
                "reduction_pct": float(pct),
            }
    return result


def find_gaps(files: list, min_gap_s: float = 60) -> list:
    gaps = []
    prev = files[0]
    for f in files[1:]:
        gap = f["mtime"] - prev["mtime"]
        if gap >= min_gap_s:
            gaps.append({
                "gap_s": gap,
                "from_path": prev["path"],
                "from_ts": prev["mtime"],
                "to_path": f["path"],
                "to_ts": f["mtime"],
            })
        prev = f
    gaps.sort(key=lambda x: -x["gap_s"])
    return gaps


def check_f1_completeness(project: str, files: list) -> tuple:
    actual = {f["path"] for f in files}
    missing = [a for a in F1_EXPECTED_ARTIFACTS if a not in actual]
    found   = [a for a in F1_EXPECTED_ARTIFACTS if a in actual]
    return found, missing


# ---------------------------------------------------------------------------
# Report
# ---------------------------------------------------------------------------

def analyze_project(project: str, phase: str = "asis") -> int:
    """Analyze a single project. Returns exit code."""
    print()
    print("=" * 76)
    print(f"  PROJECT: {project}   PHASE: F1 {phase.upper()}")
    print("=" * 76)

    files = walk_outputs(project, phase)
    if not files:
        print(f"  [ERROR] No output files found in projects/{project}/outputs/{phase}/")
        return 2

    first = files[0]
    last  = files[-1]
    wall_s = last["mtime"] - first["mtime"]

    print(f"\n  ⏱  Wall time:     {fmt_dur(wall_s)}")
    print(f"  📁  Files found:   {len(files)}")
    print(f"  🕐  First file:    {fmt_ts(first['mtime'])}  {first['path']}")
    print(f"  🕐  Last file:     {fmt_ts(last['mtime'])}   {last['path']}")

    # Token analysis
    tokens = load_token_metrics(project)
    exit_code = 0

    print()
    print("  TOKEN BUDGET")
    print("  " + "-" * 60)
    if tokens["total_compressed"]:
        raw  = tokens["total_raw"]
        comp = tokens["total_compressed"]
        pct  = round((1 - comp / raw) * 100, 1) if raw else 0
        flag = ""
        if comp >= TOKEN_CRIT_THRESHOLD:
            flag = "  ⛔ CRITICAL"
            exit_code = max(exit_code, 2)
        elif comp >= TOKEN_WARN_THRESHOLD:
            flag = "  ⚠️  WARNING"
            exit_code = max(exit_code, 1)
        else:
            flag = "  ✅ OK"
        print(f"  Raw tokens:        {raw:>12,}")
        print(f"  Compressed tokens: {comp:>12,}   (reduced {pct}%){flag}")
        print(f"  Threshold WARN:    {TOKEN_WARN_THRESHOLD:>12,}")
        print(f"  Threshold CRIT:    {TOKEN_CRIT_THRESHOLD:>12,}")
        if tokens["per_artifact"]:
            print()
            print("  Per-artifact:")
            for name, v in sorted(tokens["per_artifact"].items(),
                                   key=lambda x: -x[1]["compressed"]):
                bar = "█" * min(40, int(v["compressed"] / 15000))
                print(f"    {name:<30} {v['compressed']:>10,} tok  {bar}")
    else:
        print("  [INFO] No token data found (log not available)")

    # Gap analysis
    gaps = find_gaps(files, min_gap_s=60)
    print()
    print("  TIME GAPS (suspected subagent calls / idle periods)")
    print("  " + "-" * 60)
    if gaps:
        for g in gaps[:8]:
            flag = ""
            if g["gap_s"] >= GAP_CRIT_THRESHOLD_S:
                flag = "  ⛔ CRITICAL"
                exit_code = max(exit_code, 2)
            elif g["gap_s"] >= GAP_WARN_THRESHOLD_S:
                flag = "  ⚠️  WARNING"
                exit_code = max(exit_code, 1)
            print(f"  {fmt_dur(g['gap_s']):>10}{flag}")
            print(f"    FROM: [{fmt_ts(g['from_ts'])}] {g['from_path']}")
            print(f"    TO:   [{fmt_ts(g['to_ts'])}] {g['to_path']}")
            print()
    else:
        print("  No significant gaps (>60s) detected.")

    # F1 completeness
    found, missing = check_f1_completeness(project, files)
    print()
    print("  F1 ARTIFACT COMPLETENESS")
    print("  " + "-" * 60)
    pct_done = round(len(found) / len(F1_EXPECTED_ARTIFACTS) * 100)
    status = "✅ COMPLETE" if not missing else f"❌ INCOMPLETE ({pct_done}%)"
    print(f"  Status: {status}   ({len(found)}/{len(F1_EXPECTED_ARTIFACTS)} artifacts)")
    if missing:
        exit_code = max(exit_code, 1)
        print("  Missing:")
        for m in missing:
            print(f"    ❌  {m}")

    # Recommendation
    print()
    print("  RECOMMENDATION")
    print("  " + "-" * 60)
    comp_tok = tokens.get("total_compressed", 0)
    if comp_tok >= TOKEN_CRIT_THRESHOLD:
        print("  ⛔ CRITICAL — Token budget exceeds 700K.")
        print("     Use BC-scoped subagent dispatch (M-3) or inline execution (M-2).")
        print("     Do NOT dispatch full artifact set to a single runSubagent call.")
    elif comp_tok >= TOKEN_WARN_THRESHOLD:
        print("  ⚠️  WARNING — Token budget exceeds 400K.")
        print("     Consider artifact-level context slicing (M-1).")
        print("     Monitor for >30-min gaps during run — may need inline fallback.")
    else:
        print("  ✅ Token budget within safe range. Standard subagent dispatch OK.")

    if missing:
        print()
        print("  ACTION REQUIRED — Missing F1 artifacts:")
        print("    Run inline execution for each missing agent.")
        print("    See ISSUE-002 for inline fallback instructions.")

    # Summary line
    labels = {0: "HEALTHY", 1: "WARNING", 2: "CRITICAL"}
    print()
    print(f"  Overall status: {'⛔' if exit_code == 2 else '⚠️' if exit_code == 1 else '✅'} {labels[exit_code]}")
    print("=" * 76)
    return exit_code


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(
        description="AVA Fabric Pipeline NTP Performance Analyzer"
    )
    parser.add_argument("--project", "-p", help="Project name (e.g. processaERP-008)")
    parser.add_argument("--phase", default="asis", help="Phase subfolder (default: asis)")
    parser.add_argument("--all", "-a", action="store_true", help="Analyze all projects")
    args = parser.parse_args()

    global_exit = 0

    if args.all:
        if not os.path.isdir(PROJECTS_DIR):
            print(f"[ERROR] projects/ dir not found: {PROJECTS_DIR}", file=sys.stderr)
            sys.exit(2)
        projects = [d for d in os.listdir(PROJECTS_DIR)
                    if os.path.isdir(os.path.join(PROJECTS_DIR, d))
                    and not d.startswith("_")]
        for proj in sorted(projects):
            code = analyze_project(proj, args.phase)
            global_exit = max(global_exit, code)
    elif args.project:
        global_exit = analyze_project(args.project, args.phase)
    else:
        parser.print_help()
        sys.exit(0)

    sys.exit(global_exit)


if __name__ == "__main__":
    main()
