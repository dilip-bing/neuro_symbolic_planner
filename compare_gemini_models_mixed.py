"""
compare_gemini_models_mixed.py
==============================
Fair comparison between gemini-3-flash-preview and gemini-2.5-pro
on a mixed easy+hard+invalid dataset.

Easy cases should pass ~90% on Flash.
Medium/Hard cases should show Pro winning.
"""

import json
import os
import sys
import pathlib
import datetime
import time
from typing import List, Dict

sys.path.insert(0, str(pathlib.Path(__file__).parent))

from nl_to_pddl import NLToPDDLGenerator
from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner


# ── Mixed Benchmark Dataset ───────────────────────────────────────────────

MIXED_BENCHMARK = [
    # ────────────────────────────────────────────────────────────────────
    # EASY CASES (should pass on both models)
    # ────────────────────────────────────────────────────────────────────
    {
        "id": "easy_01_2block",
        "difficulty": "easy",
        "nl": "There are two blocks A and B on the table. Stack A on top of B.",
        "description": "Simple 2-block stack",
    },
    {
        "id": "easy_02_3tower",
        "difficulty": "easy",
        "nl": "Blocks A, B, C are on the table. Build a tower with C on B, and B on A.",
        "description": "Simple 3-block tower",
    },
    {
        "id": "easy_03_swap",
        "difficulty": "easy",
        "nl": "Block A is on B. Swap them so B is on A.",
        "description": "Simple swap operation",
    },
    {
        "id": "easy_04_keepas",
        "difficulty": "easy",
        "nl": "A and B are on table. Keep A on table. Put B on C? Wait, C doesn't exist. Just keep both on table and ensure B is clear.",
        "description": "Goal already satisfied (edge case)",
    },
    {
        "id": "easy_05_4tower",
        "difficulty": "easy",
        "nl": "Four blocks A, B, C, D are on the table. Build a tower: D on C, C on B, B on A, A on table.",
        "description": "4-block tower from scratch",
    },
    # ────────────────────────────────────────────────────────────────────
    # MEDIUM CASES (some should fail on Flash, pass on Pro)
    # ────────────────────────────────────────────────────────────────────
    {
        "id": "med_01_reverse3",
        "difficulty": "medium",
        "nl": "A is on B, B is on C, C is on table. Reverse to: C on B, B on A, A on table.",
        "description": "Reverse a 3-block stack",
    },
    {
        "id": "med_02_5tower",
        "difficulty": "medium",
        "nl": "Five blocks A, B, C, D, E all on table. Build single tower: E on D, D on C, C on B, B on A, A on table.",
        "description": "5-block tower (more search space)",
    },
    {
        "id": "med_03_partial_preserve",
        "difficulty": "medium",
        "nl": "A on B on table. C, D, E all on table. Keep A on B. Put E on D on C.",
        "description": "Partial state preservation + new tower",
    },
    {
        "id": "med_04_two_stacks_merge",
        "difficulty": "medium",
        "nl": "Two separate stacks: A on B on table, and C on D on table. Merge into one: D on B, A on D, C on table, then form: C on A.",
        "description": "Merging two towers into one",
    },
    {
        "id": "med_05_6tower",
        "difficulty": "medium",
        "nl": "Six blocks A-F on table. Build tower F on E on D on C on B on A on table.",
        "description": "6-block tower (high branching)",
    },
    # ────────────────────────────────────────────────────────────────────
    # HARD/UNSOLVABLE CASES (should fail planning on both, but Pro may handle better)
    # ────────────────────────────────────────────────────────────────────
    {
        "id": "hard_01_cyclic_goal",
        "difficulty": "hard",
        "nl": "Put A on B and B on A simultaneously.",
        "description": "Logically impossible: cyclic constraint",
    },
    {
        "id": "hard_02_impossible_goal",
        "difficulty": "hard",
        "nl": "A, B on table. Goal: A holding something and hand is empty at same time.",
        "description": "Contradictory state requirements",
    },
    {
        "id": "hard_03_too_many_blocks",
        "difficulty": "hard",
        "nl": "We have 10 blocks A through J. Stack them all in one tower on the table.",
        "description": "Very deep tower (10 blocks)",
    },
    {
        "id": "hard_04_ambiguous_pddl",
        "difficulty": "hard",
        "nl": "There is a mysterious block. Put it on another. Build a tower somehow.",
        "description": "Vague objects and goals",
    },
    {
        "id": "hard_05_reverse_6",
        "difficulty": "hard",
        "nl": "Six blocks stacked A-B-C-D-E-F with F on table. Reverse to F on E on D on C on B on A on table.",
        "description": "Reverse complex stack",
    },
    # ────────────────────────────────────────────────────────────────────
    # EDGE CASES (validation/parsing challenges)
    # ────────────────────────────────────────────────────────────────────
    {
        "id": "edge_01_empty_goal",
        "difficulty": "hard",
        "nl": "Two blocks on table. Do nothing special, just make sure the hand is empty.",
        "description": "Trivial goal (already satisfied)",
    },
    {
        "id": "edge_02_implicit_blocks",
        "difficulty": "hard",
        "nl": "Stack the red block on the blue block.",
        "description": "Color descriptors not in blocksworld domain",
    },
    {
        "id": "edge_03_complex_prestate",
        "difficulty": "medium",
        "nl": "Complex initial state: A-B-C stacked, D-E-F stacked, G on table. Rearrange to A-D-G-B-E-C on table, preserving 3-block arrangement.",
        "description": "Complex multi-tower manipulation",
    },
]


class ModelComparison:
    def __init__(self, domain_pddl: str, api_key: str, models: List[str]):
        self.domain_pddl = domain_pddl
        self.api_key = api_key
        self.models = models
        self.validator = PDDLValidator()
        self.planner = BFSPlanner(max_nodes=50_000)

    def run_comparison(self, problems: List[Dict], output_path: str = None):
        print(f"\n{'='*80}")
        print("  GEMINI MODEL COMPARISON — Mixed Easy+Hard Dataset")
        print(f"{'='*80}")
        print(f"  Models tested      : {', '.join(self.models)}")
        print(f"  Total problems     : {len(problems)}")
        print(f"  Started            : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*80}\n")

        all_results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "models": self.models,
            "total_problems": len(problems),
            "models_stats": {},
            "per_problem_comparison": [],
        }

        for model in self.models:
            print(f"\n{'─'*80}")
            print(f"  Running {model}")
            print(f"{'─'*80}")
            model_results = self._run_model(model, problems)
            all_results["models_stats"][model] = self._compute_stats(model_results)
            all_results["per_problem_comparison"].extend(model_results)

        # Save
        if output_path is None:
            output_path = pathlib.Path(__file__).parent / "results" / "model_comparison_mixed.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(all_results, indent=2))

        self._print_summary(all_results)
        print(f"\n📁 Results saved to: {output_path}\n")
        return all_results

    def _run_model(self, model: str, problems: List[Dict]) -> List[Dict]:
        """Run pipeline for a single model on all problems."""
        gen = NLToPDDLGenerator(self.domain_pddl, api_key=self.api_key, model_name=model)
        results = []

        for i, problem in enumerate(problems, 1):
            print(f"  [{i:2d}/{len(problems)}] {problem['id']:20s} ({'difficulty:' + problem['difficulty']:12s}) ... ", end="", flush=True)

            try:
                # Generation
                gen_result = gen.generate(problem["nl"], problem["id"])
                
                # Validation
                if gen_result["success"]:
                    val_result = self.validator.validate(gen_result["pddl"])
                    validation_valid = val_result.is_valid
                    validation_errors = val_result.errors
                else:
                    validation_valid = False
                    validation_errors = [gen_result["error"]]

                # Planning
                if validation_valid and gen_result["success"]:
                    plan_result = self.planner.solve(gen_result["pddl"], problem["id"])
                    planning_success = plan_result.success
                    failure_reason = plan_result.failure_reason
                    plan_length = plan_result.plan_length
                else:
                    planning_success = False
                    failure_reason = validation_errors[0] if validation_errors else "Invalid PDDL"
                    plan_length = 0

                status = "✅" if (gen_result["success"] and validation_valid and planning_success) else "❌"
                print(f"{status} (gen={gen_result['success']} val={validation_valid} plan={planning_success})")

                results.append({
                    "model": model,
                    "problem_id": problem["id"],
                    "difficulty": problem["difficulty"],
                    "nl": problem["nl"],
                    "generation_success": gen_result["success"],
                    "generation_error": gen_result.get("error"),
                    "generated_pddl": gen_result["pddl"],
                    "validation_valid": validation_valid,
                    "validation_errors": validation_errors,
                    "planning_success": planning_success,
                    "plan_length": plan_length,
                    "failure_reason": failure_reason,
                    "overall_success": gen_result["success"] and validation_valid and planning_success,
                })
            except Exception as e:
                print(f"❌ (exception: {str(e)[:50]})")
                results.append({
                    "model": model,
                    "problem_id": problem["id"],
                    "difficulty": problem["difficulty"],
                    "nl": problem["nl"],
                    "generation_success": False,
                    "generation_error": str(e),
                    "generated_pddl": "",
                    "validation_valid": False,
                    "validation_errors": [str(e)],
                    "planning_success": False,
                    "plan_length": 0,
                    "failure_reason": str(e),
                    "overall_success": False,
                })

            # Rate limit
            time.sleep(1)

        return results

    def _compute_stats(self, results: List[Dict]) -> Dict:
        """Compute summary statistics for a model."""
        total = len(results)
        gen_ok = sum(1 for r in results if r["generation_success"])
        val_ok = sum(1 for r in results if r["validation_valid"])
        plan_ok = sum(1 for r in results if r["planning_success"])
        overall_ok = sum(1 for r in results if r["overall_success"])

        # By difficulty
        by_diff = {}
        for diff in ["easy", "medium", "hard"]:
            subset = [r for r in results if r["difficulty"] == diff]
            by_diff[diff] = {
                "total": len(subset),
                "generation_success": sum(1 for r in subset if r["generation_success"]),
                "validation_success": sum(1 for r in subset if r["validation_valid"]),
                "planning_success": sum(1 for r in subset if r["planning_success"]),
                "overall_success": sum(1 for r in subset if r["overall_success"]),
            }

        return {
            "total_problems": total,
            "generation_success": gen_ok,
            "validation_success": val_ok,
            "planning_success": plan_ok,
            "overall_success": overall_ok,
            "generation_rate": round(gen_ok / total, 3) if total else 0,
            "validation_rate": round(val_ok / total, 3) if total else 0,
            "executability_rate": round(plan_ok / total, 3) if total else 0,
            "overall_success_rate": round(overall_ok / total, 3) if total else 0,
            "by_difficulty": by_diff,
        }

    def _print_summary(self, all_results: Dict):
        """Print side-by-side comparison."""
        stats = all_results["models_stats"]
        models = self.models

        print(f"\n{'='*80}")
        print("  DETAILED COMPARISON SUMMARY")
        print(f"{'='*80}")

        print(f"\n{'Metric':<30s} | {models[0]:<25s} | {models[1]:<25s}")
        print("─" * 85)

        for key in ["generation_rate", "validation_rate", "executability_rate", "overall_success_rate"]:
            val0 = f"{stats[models[0]][key]*100:.1f}%"
            val1 = f"{stats[models[1]][key]*100:.1f}%"
            print(f"{key.replace('_', ' ').title():<30s} | {val0:<25s} | {val1:<25s}")

        print(f"\n{'Difficulty':<30s} | {models[0]:<25s} | {models[1]:<25s}")
        print("─" * 85)
        for diff in ["easy", "medium", "hard"]:
            if diff in stats[models[0]]["by_difficulty"]:
                easy0 = stats[models[0]]["by_difficulty"][diff]["overall_success"]
                easy_tot = stats[models[0]]["by_difficulty"][diff]["total"]
                easy1 = stats[models[1]]["by_difficulty"][diff]["overall_success"]
                easy_tot2 = stats[models[1]]["by_difficulty"][diff]["total"]
                val0 = f"{easy0}/{easy_tot}"
                val1 = f"{easy1}/{easy_tot2}"
                print(f"{diff.upper()} cases              | {val0:<25s} | {val1:<25s}")

        print(f"\n{'='*80}")

        # Determine winner
        winner = models[0] if stats[models[0]]["overall_success_rate"] > stats[models[1]]["overall_success_rate"] else models[1]
        gap = abs(
            stats[models[0]]["overall_success_rate"] - stats[models[1]]["overall_success_rate"]
        )
        print(f"  Winner            : {winner} (gap: {gap*100:.1f}%)")
        print(f"{'='*80}\n")


def main():
    # Load domain
    domain_path = pathlib.Path(__file__).parent / "blocksworld.pddl"
    if not domain_path.exists():
        domain_path = pathlib.Path(__file__).parent.parent / "domains" / "blocksworld.pddl"
    domain_pddl = domain_path.read_text()

    # API key
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY environment variable not set")

    # Models
    models = os.environ.get("COMPARISON_MODELS", "gemini-3-flash-preview,gemini-2.5-pro").split(",")

    # Limit (for testing)
    problem_limit = int(os.environ.get("COMPARISON_CASE_LIMIT", 0))
    problems = MIXED_BENCHMARK if not problem_limit else MIXED_BENCHMARK[:problem_limit]

    # Run
    comp = ModelComparison(domain_pddl, api_key, models)
    comp.run_comparison(problems)


if __name__ == "__main__":
    main()
