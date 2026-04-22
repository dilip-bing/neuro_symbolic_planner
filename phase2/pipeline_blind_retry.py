"""
pipeline_blind_retry.py  —  Phase 2 Ablation: Blind Retry Baseline

Runs the same generate→validate→plan loop but WITHOUT the structured critic.
On failure the generator receives only: "Your previous attempt failed. Try again."
No error type, no targeted fix instruction — pure blind retry.

Purpose: This is the critical control condition for the paper.
  If blind retry reaches the same final executability as structured critic,
  the critic taxonomy contributes nothing and the paper's claim evaporates.
  We expect structured critic >> blind retry on harder problems.

Results are saved to results/archive/ alongside the main pipeline results.

Usage:
    python pipeline_blind_retry.py                        # all domains
    python pipeline_blind_retry.py --domain logistics     # one domain
    python pipeline_blind_retry.py --dry-run              # validate setup
"""

import argparse
import json
import os
import pathlib
import sys
import time
from datetime import datetime
from typing import List

INTER_PROBLEM_DELAY_S = 5

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from src.nl_to_pddl import NLToPDDLGenerator
from src.pddl_validator import PDDLValidator
from src.planner_runner import PDDLPlanner
from benchmarks.blocksworld_problems import PROBLEMS as BW_PROBLEMS
from benchmarks.gripper_problems import PROBLEMS as GR_PROBLEMS
from benchmarks.logistics_problems import PROBLEMS as LOG_PROBLEMS
from benchmarks.ferry_problems import PROBLEMS as FERRY_PROBLEMS

DOMAINS_DIR = pathlib.Path(__file__).resolve().parent / "domains"
RESULTS_DIR = pathlib.Path(__file__).resolve().parent / "results"

DOMAIN_REGISTRY = {
    "blocksworld": {"pddl_file": DOMAINS_DIR / "blocksworld.pddl", "problems": BW_PROBLEMS},
    "gripper":     {"pddl_file": DOMAINS_DIR / "gripper.pddl",     "problems": GR_PROBLEMS},
    "logistics":   {"pddl_file": DOMAINS_DIR / "logistics.pddl",   "problems": LOG_PROBLEMS},
    "ferry":       {"pddl_file": DOMAINS_DIR / "ferry.pddl",       "problems": FERRY_PROBLEMS},
}

# ── Blind Retry Prompt ────────────────────────────────────────────────────────
# Generic, unstructured — no error taxonomy, no targeted fix instruction.
# This is the "null hypothesis" for the structured critic.

BLIND_RETRY_TEMPLATE = """Domain definition:
{domain_pddl}

---
Natural Language Problem:
{nl_description}

---
Previous attempt — FAILED. The generated PDDL could not be executed by the planner.

Previous PDDL (for reference):
{previous_pddl}

---
Please try again. Generate a corrected PDDL problem file. Output ONLY the PDDL."""


# ── Blind Retry Loop ─────────────────────────────────────────────────────────

class BlindRetryLoop:
    """
    Same generate→validate→plan loop as RepairLoop but WITHOUT the structured critic.
    On failure: send the previous PDDL back with a generic "try again" message.
    """

    def __init__(self, domain_pddl: str, max_iterations: int = 5,
                 gemini_api_key: str = None, gemini_model: str = None):
        self.domain_pddl = domain_pddl
        self.max_iterations = max_iterations
        self.generator = NLToPDDLGenerator(domain_pddl, api_key=gemini_api_key, model_name=gemini_model)
        self.validator = PDDLValidator(domain_pddl)
        self.planner = PDDLPlanner(domain_pddl)
        self.domain_name = self.generator.domain_info["name"]

    def run(self, problem_id: str, nl_description: str) -> dict:
        t_start = time.time()
        result = {
            "problem_id": problem_id,
            "nl_description": nl_description,
            "domain_name": self.domain_name,
            "success": False,
            "final_plan": [],
            "iterations_needed": -1,
            "max_iterations": self.max_iterations,
            "baseline_valid": False,
            "baseline_executable": False,
            "repair_attempted": False,
            "total_elapsed_ms": 0.0,
            "iterations": [],
        }

        current_pddl = ""

        for i in range(self.max_iterations + 1):
            t_iter = time.time()

            # ── Generate ──────────────────────────────────────────────────────
            if i == 0:
                gen_result = self.generator.generate(nl_description, problem_id)
            else:
                # Blind retry: send the failed PDDL back with generic message, no critic insight
                from google import genai
                from google.genai import types as genai_types
                import warnings, logging
                warnings.filterwarnings("ignore")
                logging.disable(logging.CRITICAL)

                prompt = BLIND_RETRY_TEMPLATE.format(
                    domain_pddl=self.domain_pddl,
                    nl_description=nl_description,
                    previous_pddl=current_pddl,
                )
                api_key = os.environ.get("GEMINI_API_KEY", "")
                model_name = self.generator.model_name
                gen_result = {"success": False, "pddl": "", "error": None}

                client = genai.Client(api_key=api_key)
                last_error = ""
                for attempt in range(2):
                    try:
                        response = client.models.generate_content(
                            model=model_name,
                            contents=prompt,
                            config=genai_types.GenerateContentConfig(
                                system_instruction=self.generator._system_prompt,
                                temperature=0.2,
                            ),
                        )
                        raw = response.text.strip()
                        import re
                        cleaned = re.sub(r"```[a-zA-Z]*\n?", "", raw)
                        cleaned = re.sub(r"```", "", cleaned).strip()
                        gen_result = {"success": True, "pddl": cleaned, "error": None}
                        break
                    except Exception as e:
                        last_error = str(e)
                        err_lower = last_error.lower()
                        # Daily quota exhaustion — fail immediately, no sleep
                        is_daily_quota = any(x in err_lower for x in [
                            "daily", "quota exceeded", "resource_exhausted", "per day"
                        ]) and "429" in last_error
                        if is_daily_quota:
                            gen_result["error"] = f"DAILY_QUOTA_EXHAUSTED: {last_error}"
                            break
                        is_transient = any(x in err_lower for x in ["503", "429", "unavailable", "timeout"])
                        if is_transient and attempt < 1:
                            time.sleep(65)
                            continue
                        gen_result["error"] = last_error
                        break
                if not gen_result["success"] and not gen_result.get("error"):
                    gen_result["error"] = last_error

            if not gen_result["success"]:
                result["iterations"].append({
                    "iteration": i,
                    "is_valid": False,
                    "validator_errors": [f"Generator failed: {gen_result.get('error')}"],
                    "plan_success": False,
                    "critic_error_type": None,
                    "elapsed_ms": round((time.time() - t_iter) * 1000, 1),
                })
                break

            current_pddl = gen_result["pddl"]

            # ── Validate ──────────────────────────────────────────────────────
            val_result = self.validator.validate(current_pddl)

            # ── Plan ──────────────────────────────────────────────────────────
            plan_success = False
            plan = []
            failure_reason = "Validation failed — planner not called."
            if val_result.is_valid:
                plan_result_obj = self.planner.solve(current_pddl)
                plan_success = plan_result_obj.success
                plan = plan_result_obj.plan
                failure_reason = plan_result_obj.failure_reason

            iter_elapsed = (time.time() - t_iter) * 1000

            if i == 0:
                result["baseline_valid"] = val_result.is_valid
                result["baseline_executable"] = plan_success

            solved = val_result.is_valid and plan_success

            result["iterations"].append({
                "iteration": i,
                "is_valid": val_result.is_valid,
                "validator_errors": val_result.errors,
                "plan_success": plan_success,
                "critic_error_type": None,   # no critic in blind retry
                "elapsed_ms": round(iter_elapsed, 1),
            })

            if solved:
                result["success"] = True
                result["final_plan"] = plan
                result["iterations_needed"] = i
                result["repair_attempted"] = i > 0
                break

            # Rate limit buffer before next retry
            if i < self.max_iterations:
                time.sleep(5)

        result["total_elapsed_ms"] = round((time.time() - t_start) * 1000, 1)
        return result


# ── Aggregate Metrics ─────────────────────────────────────────────────────────

def compute_aggregate(results: List[dict]) -> dict:
    n = len(results)
    if n == 0:
        return {}
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
        "repaired_by_loop": repaired,
        "never_solved": never_solved,
        "avg_iterations_when_repaired": round(avg_iters, 2),
    }


# ── Runner ────────────────────────────────────────────────────────────────────

def run_domain(domain_name: str, max_iterations: int = 5, dry_run: bool = False) -> dict:
    config = DOMAIN_REGISTRY[domain_name]
    domain_pddl = config["pddl_file"].read_text()
    problems = config["problems"]

    withhold = os.environ.get("WITHHOLD_PREDICATES", "false").lower() == "true"
    mislead = os.environ.get("INJECT_TYPE_MISLEAD", "false").lower() == "true"
    agnostic = os.environ.get("USE_AGNOSTIC_NL", "false").lower() == "true"
    print(f"\n{'='*60}")
    print(f"Domain: {domain_name.upper()}  ({len(problems)} problems, max {max_iterations} blind retries)")
    print(f"Mode: BLIND RETRY (no structured critic)")
    print(f"Predicates in prompt: {'WITHHELD (ablation)' if withhold else 'provided'}")
    print(f"Misleading type hint:  {'ON (ablation)' if mislead else 'off'}")
    print(f"Domain-agnostic NL:    {'ON (ablation)' if agnostic else 'off'}")
    print(f"{'='*60}")

    if dry_run:
        print(f"[dry-run] Would run {len(problems)} problems.")
        return {"domain": domain_name, "dry_run": True}

    loop = BlindRetryLoop(
        domain_pddl=domain_pddl,
        max_iterations=max_iterations,
        gemini_api_key=os.environ.get("GEMINI_API_KEY"),
        gemini_model=os.environ.get("GEMINI_MODEL"),
    )

    problem_results = []
    for i, prob in enumerate(problems):
        if i > 0:
            time.sleep(INTER_PROBLEM_DELAY_S)
        # USE_AGNOSTIC_NL: prefer nl_agnostic if available and toggle is on
        nl_text = (
            prob.get("nl_agnostic", prob["nl"])
            if agnostic and "nl_agnostic" in prob
            else prob["nl"]
        )
        print(f"\n  [{prob['id']}] {nl_text[:80]}...")
        result = loop.run(prob["id"], nl_text)
        problem_results.append(result)

        status = "SOLVED" if result["success"] else "FAILED"
        iters  = result["iterations_needed"] if result["success"] else "—"
        print(
            f"  → {status} | baseline_exec={result['baseline_executable']} "
            f"| iterations_needed={iters} | {result['total_elapsed_ms']:.0f}ms"
        )

        # Abort immediately if the API key's daily quota is exhausted
        all_errors = " ".join(str(e) for e in result.get("errors", []))
        if "DAILY_QUOTA_EXHAUSTED" in all_errors:
            print(f"\n  !! Daily API quota exhausted — aborting remaining problems.")
            break

    agg = compute_aggregate(problem_results)

    print(f"\n  [{domain_name}] Summary:")
    print(f"    Baseline executability:  {agg['baseline_executability_rate']:.1%}")
    print(f"    Final executability:     {agg['final_executability_rate']:.1%}")
    print(f"    Improvement:            +{agg['improvement']:.1%}")
    print(f"    Repaired by blind retry: {agg['repaired_by_loop']}/{agg['total_problems']}")

    return {"domain": domain_name, "aggregate": agg, "problems": problem_results}


def main():
    parser = argparse.ArgumentParser(description="Blind retry baseline (no structured critic)")
    parser.add_argument("--domain", choices=list(DOMAIN_REGISTRY.keys()), default=None)
    parser.add_argument("--max-iterations", type=int, default=5)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if not args.dry_run and not os.environ.get("GEMINI_API_KEY"):
        print("ERROR: GEMINI_API_KEY not set.")
        sys.exit(1)

    domains_to_run = [args.domain] if args.domain else list(DOMAIN_REGISTRY.keys())
    all_results = {}
    t_total = time.time()

    for domain_name in domains_to_run:
        all_results[domain_name] = run_domain(domain_name, args.max_iterations, args.dry_run)

    total_elapsed = time.time() - t_total

    if not args.dry_run and len(domains_to_run) > 1:
        all_problems = []
        for dr in all_results.values():
            all_problems.extend(dr.get("problems", []))
        cross_domain_agg = compute_aggregate(all_problems)

        print(f"\n{'='*60}")
        print(f"CROSS-DOMAIN SUMMARY — BLIND RETRY ({len(all_problems)} problems)")
        print(f"{'='*60}")
        print(f"  Baseline executability:  {cross_domain_agg['baseline_executability_rate']:.1%}")
        print(f"  Final executability:     {cross_domain_agg['final_executability_rate']:.1%}")
        print(f"  Improvement:            +{cross_domain_agg['improvement']:.1%}")
        print(f"  Total elapsed:           {total_elapsed:.1f}s")

        all_results["cross_domain"] = cross_domain_agg

    # ── Save results ──────────────────────────────────────────────────────────
    if not args.dry_run:
        abs_results_dir = pathlib.Path(__file__).resolve().parent / "results"
        abs_results_dir.mkdir(exist_ok=True)
        archive_dir = abs_results_dir / "archive"
        archive_dir.mkdir(exist_ok=True)

        ts = datetime.utcnow().strftime("%Y-%m-%dT%H-%M-%SZ")
        domains_run = "_".join(domains_to_run)
        gen_model = os.environ.get("GEMINI_MODEL", "unknown")
        withhold = os.environ.get("WITHHOLD_PREDICATES", "false").lower() == "true"
        mislead = os.environ.get("INJECT_TYPE_MISLEAD", "false").lower() == "true"
        agnostic = os.environ.get("USE_AGNOSTIC_NL", "false").lower() == "true"
        all_results["_meta"] = {
            "run_timestamp": ts,
            "method": "blind_retry",
            "generator_model": gen_model,
            "critic_model": None,
            "withhold_predicates": withhold,
            "inject_type_mislead": mislead,
            "use_agnostic_nl": agnostic,
            "domains": domains_to_run,
            "max_repair_iterations": args.max_iterations,
            "total_elapsed_s": round(total_elapsed, 1) if len(domains_to_run) > 1 else None,
        }

        payload = json.dumps(all_results, indent=2)
        archive_path = archive_dir / f"run_blind_retry_{domains_run}_{ts}_gen-{gen_model.replace('/', '-')}.json"
        archive_path.write_text(payload)
        archive_path.chmod(0o444)

        latest_path = abs_results_dir / "blind_retry_results_latest.json"
        latest_path.write_text(payload)

        print(f"\nResults archived → {archive_path}")
        print(f"Latest copy      → {latest_path}")


if __name__ == "__main__":
    main()
