"""
pipeline_phase2.py  —  Phase 2 Orchestrator
Adversarial Critic + Iterative Repair Pipeline

Runs the repair loop across all 3 domains (Blocksworld, Gripper, Logistics)
and saves per-domain and aggregate results to results/phase2_results.json.

Usage:
    # Set env vars first (see .env.example)
    python pipeline_phase2.py                        # run all domains
    python pipeline_phase2.py --domain blocksworld   # run one domain
    python pipeline_phase2.py --dry-run              # validate setup only (no API calls)
"""

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime
from typing import List

# Free tier: 15 requests/min → space problems 5s apart to stay safely under limit
INTER_PROBLEM_DELAY_S = 5

# Allow running from project root
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from src.repair_loop import RepairLoop
from benchmarks.blocksworld_problems import PROBLEMS as BW_PROBLEMS
from benchmarks.gripper_problems import PROBLEMS as GR_PROBLEMS
from benchmarks.logistics_problems import PROBLEMS as LOG_PROBLEMS
from benchmarks.ferry_problems import PROBLEMS as FERRY_PROBLEMS


# ── Domain Registry ───────────────────────────────────────────────────────────

DOMAINS_DIR = pathlib.Path(__file__).parent / "domains"
RESULTS_DIR = pathlib.Path(__file__).parent / "results"

DOMAIN_REGISTRY = {
    "blocksworld": {
        "pddl_file": DOMAINS_DIR / "blocksworld.pddl",
        "problems": BW_PROBLEMS,
    },
    "gripper": {
        "pddl_file": DOMAINS_DIR / "gripper.pddl",
        "problems": GR_PROBLEMS,
    },
    "logistics": {
        "pddl_file": DOMAINS_DIR / "logistics.pddl",
        "problems": LOG_PROBLEMS,
    },
    "ferry": {
        "pddl_file": DOMAINS_DIR / "ferry.pddl",
        "problems": FERRY_PROBLEMS,
    },
}


# ── Aggregate Metrics ─────────────────────────────────────────────────────────

def compute_aggregate(results: List[dict]) -> dict:
    n = len(results)
    if n == 0:
        return {}

    baseline_valid = sum(1 for r in results if r["baseline_valid"])
    baseline_exec  = sum(1 for r in results if r["baseline_executable"])
    final_success  = sum(1 for r in results if r["success"])
    repaired       = sum(1 for r in results if r["success"] and r["iterations_needed"] > 0)
    never_solved   = sum(1 for r in results if not r["success"])

    repaired_results = [r for r in results if r["success"] and r["iterations_needed"] > 0]
    avg_iters = (
        sum(r["iterations_needed"] for r in repaired_results) / len(repaired_results)
        if repaired_results else 0.0
    )

    return {
        "total_problems": n,
        "baseline_executability_rate": round(baseline_exec / n, 3),
        "final_executability_rate": round(final_success / n, 3),
        "improvement": round((final_success - baseline_exec) / n, 3),
        "baseline_valid_rate": round(baseline_valid / n, 3),
        "repaired_by_loop": repaired,
        "never_solved": never_solved,
        "avg_iterations_when_repaired": round(avg_iters, 2),
    }


# ── Runner ────────────────────────────────────────────────────────────────────

def run_domain(domain_name: str, max_iterations: int = 5, dry_run: bool = False) -> dict:
    config = DOMAIN_REGISTRY[domain_name]
    domain_pddl = config["pddl_file"].read_text()
    problems = config["problems"]

    critic_backend = os.environ.get("CRITIC_BACKEND", "gemini")
    withhold = os.environ.get("WITHHOLD_PREDICATES", "false").lower() == "true"
    mislead = os.environ.get("INJECT_TYPE_MISLEAD", "false").lower() == "true"
    agnostic = os.environ.get("USE_AGNOSTIC_NL", "false").lower() == "true"
    print(f"\n{'='*60}")
    print(f"Domain: {domain_name.upper()}  ({len(problems)} problems, max {max_iterations} repair iterations)")
    print(f"Critic backend: {critic_backend.upper()}")
    print(f"Predicates in prompt: {'WITHHELD (ablation)' if withhold else 'provided'}")
    print(f"Misleading type hint:  {'ON (ablation)' if mislead else 'off'}")
    print(f"Domain-agnostic NL:    {'ON (ablation)' if agnostic else 'off'}")
    print(f"{'='*60}")

    if dry_run:
        print(f"[dry-run] Would run {len(problems)} problems.")
        return {"domain": domain_name, "dry_run": True}

    loop = RepairLoop(
        domain_pddl=domain_pddl,
        max_iterations=max_iterations,
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        gemini_model=os.environ.get("GEMINI_MODEL"),
    )

    problem_results = []
    for i, prob in enumerate(problems):
        if i > 0:
            time.sleep(INTER_PROBLEM_DELAY_S)   # stay under free-tier 15 RPM
        # USE_AGNOSTIC_NL: prefer nl_agnostic if available and toggle is on
        nl_text = (
            prob.get("nl_agnostic", prob["nl"])
            if agnostic and "nl_agnostic" in prob
            else prob["nl"]
        )
        print(f"\n  [{prob['id']}] {nl_text[:80]}...")
        result = loop.run(prob["id"], nl_text)
        d = result.to_dict()
        problem_results.append(d)

        status = "SOLVED" if result.success else "FAILED"
        iters  = result.iterations_needed if result.success else "—"
        print(
            f"  → {status} | baseline_exec={result.baseline_executable} "
            f"| iterations_needed={iters} | {result.total_elapsed_ms:.0f}ms"
        )

        # Abort immediately if the API key's daily quota is exhausted
        last_errors = " ".join(
            " ".join(rec.get("validator_errors", []))
            for rec in (d.get("iterations") or [])
            if isinstance(rec, dict)
        )
        if "DAILY_QUOTA_EXHAUSTED" in last_errors:
            print(f"\n  !! Daily API quota exhausted — aborting remaining problems.")
            break

    agg = compute_aggregate(problem_results)

    print(f"\n  [{domain_name}] Summary:")
    print(f"    Baseline executability:  {agg['baseline_executability_rate']:.1%}")
    print(f"    Final executability:     {agg['final_executability_rate']:.1%}")
    print(f"    Improvement:            +{agg['improvement']:.1%}")
    print(f"    Repaired by loop:        {agg['repaired_by_loop']}/{agg['total_problems']}")

    return {
        "domain": domain_name,
        "aggregate": agg,
        "problems": problem_results,
    }


def main():
    parser = argparse.ArgumentParser(description="Phase 2 repair loop pipeline")
    parser.add_argument("--domain", choices=list(DOMAIN_REGISTRY.keys()), default=None,
                        help="Run a single domain (default: all)")
    parser.add_argument("--max-iterations", type=int, default=5,
                        help="Max repair iterations per problem (default: 5)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Validate setup without making API calls")
    args = parser.parse_args()

    RESULTS_DIR.mkdir(exist_ok=True)

    if not args.dry_run:
        if not os.environ.get("GEMINI_API_KEY"):
            print("ERROR: GEMINI_API_KEY not set. See .env.example")
            sys.exit(1)

    domains_to_run = [args.domain] if args.domain else list(DOMAIN_REGISTRY.keys())

    all_results = {}
    t_total = time.time()

    for domain_name in domains_to_run:
        domain_result = run_domain(domain_name, args.max_iterations, args.dry_run)
        all_results[domain_name] = domain_result

    total_elapsed = time.time() - t_total

    # ── Cross-domain aggregate ────────────────────────────────────────────────
    if not args.dry_run and len(domains_to_run) > 1:
        all_problems = []
        for dr in all_results.values():
            all_problems.extend(dr.get("problems", []))
        cross_domain_agg = compute_aggregate(all_problems)

        print(f"\n{'='*60}")
        print(f"CROSS-DOMAIN SUMMARY ({len(all_problems)} total problems)")
        print(f"{'='*60}")
        print(f"  Baseline executability:  {cross_domain_agg['baseline_executability_rate']:.1%}")
        print(f"  Final executability:     {cross_domain_agg['final_executability_rate']:.1%}")
        print(f"  Improvement:            +{cross_domain_agg['improvement']:.1%}")
        print(f"  Total elapsed:           {total_elapsed:.1f}s")

        all_results["cross_domain"] = cross_domain_agg

    # ── Save results ──────────────────────────────────────────────────────────
    if not args.dry_run:
        # Always use absolute path anchored to this file's directory
        abs_results_dir = pathlib.Path(__file__).resolve().parent / "results"
        abs_results_dir.mkdir(exist_ok=True)
        archive_dir = abs_results_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        # Build metadata header
        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        domains_run = "_".join(domains_to_run)
        gen_model = os.environ.get("GEMINI_MODEL", "unknown")
        critic_model = os.environ.get("CRITIC_GEMINI_MODEL", gen_model)
        withhold = os.environ.get("WITHHOLD_PREDICATES", "false").lower() == "true"
        mislead = os.environ.get("INJECT_TYPE_MISLEAD", "false").lower() == "true"
        agnostic = os.environ.get("USE_AGNOSTIC_NL", "false").lower() == "true"
        all_results["_meta"] = {
            "run_timestamp": ts,
            "generator_model": gen_model,
            "critic_model": critic_model,
            "critic_backend": os.environ.get("CRITIC_BACKEND", "gemini"),
            "withhold_predicates": withhold,
            "inject_type_mislead": mislead,
            "use_agnostic_nl": agnostic,
            "domains": domains_to_run,
            "max_repair_iterations": args.max_iterations,
            "total_elapsed_s": round(total_elapsed, 1) if len(domains_to_run) > 1 else None,
        }

        payload = json.dumps(all_results, indent=2)

        # Timestamped archive copy (never overwritten)
        archive_path = archive_dir / f"run_{domains_run}_{ts}_gen-{gen_model.replace('/', '-')}.json"
        archive_path.write_text(payload)
        archive_path.chmod(0o444)   # make read-only so it can't be accidentally overwritten

        # Latest symlink for easy access
        latest_path = abs_results_dir / "phase2_results_latest.json"
        latest_path.write_text(payload)

        print(f"\nResults archived → {archive_path}")
        print(f"Latest copy      → {latest_path}")


if __name__ == "__main__":
    main()
