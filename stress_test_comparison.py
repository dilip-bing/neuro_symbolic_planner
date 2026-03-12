"""
stress_test_comparison.py
=========================
Extended benchmark with 30 challenging problems to differentiate Pro from Flash.
Includes edge cases, complex multi-tower operations, and ambiguous descriptions.
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


STRESS_BENCHMARK = [
    # BASELINE EASY (should both pass 100%)
    {"id": "s_01", "diff": "easy", "nl": "Two blocks A, B on table. Stack A on B.", "desc": "2-block"},
    {"id": "s_02", "diff": "easy", "nl": "Three blocks A, B, C on table. Build tower C-B-A.", "desc": "3-block tower"},
    {"id": "s_03", "diff": "easy", "nl": "Block A on B on table. Unstack and put A back on table.", "desc": "Unstack"},
    
    # MEDIUM INCREASING COMPLEXITY
    {"id": "s_04", "diff": "medium", "nl": "Five blocks A-E all on table. Build tower E-D-C-B-A on A.", "desc": "5-block"},
    {"id": "s_05", "diff": "medium", "nl": "A-B-C stacked with A on B on C on table. Reverse to C-B-A.", "desc": "Reverse 3"},
    {"id": "s_06", "diff": "medium", "nl": "Two stacks: A-B on table and C-D on table. Merge into A-C-B-D.", "desc": "Merge 2 stacks"},
    {"id": "s_07", "diff": "medium", "nl": "Six blocks all on table. Build tower F-E-D-C-B-A.", "desc": "6-block"},
    
    # HARD: COMPLEX MULTI-TOWER OPERATIONS
    {"id": "s_08", "diff": "hard", "nl": "Three separate stacks: A-B, C-D, E-F all on table. Create one tower F-E-D-C-B-A.", "desc": "3-stacks→1"},
    {"id": "s_09", "diff": "hard", "nl": "Complex: A-B-C stacked, D alone, E-F stacked. Goal: All in one tower preserving ABC order:", "desc": "Complex merge"},
    
    # AMBIGUOUS/UNDERSPECIFIED NL (tests inference)
    {"id": "s_10", "diff": "hard", "nl": "Several blocks. Stack them somehow with the tallest one on top.", "desc": "Ambiguous tall"},
    {"id": "s_11", "diff": "hard", "nl": "Build a tower as described but the description is missing. Use default blocksworld setup.", "desc": "Missing desc"},
    {"id": "s_12", "diff": "hard", "nl": "The blocks be stacks. Make them good.", "desc": "Grammar poor"},
    
    # IMPOSSIBLE/CONTRADICTORY GOALS
    {"id": "s_13", "diff": "hard", "nl": "A must be on B and B must be on A at the same time.", "desc": "Cyclic"},
    {"id": "s_14", "diff": "hard", "nl": "Block A must be held and hand must be empty simultaneously.", "desc": "Contradictory"},
    {"id": "s_15", "diff": "hard", "nl": "Ten blocks A-J. Build a single tower with all of them.", "desc": "10-block tower"},
    
    # ZERO/TRIVIAL GOALS
    {"id": "s_16", "diff": "medium", "nl": "Two blocks already stacked as A on B. Keep them as is.", "desc": "Status quo"},
    {"id": "s_17", "diff": "easy", "nl": "Hand is empty. Ensure it stays empty.", "desc": "Trivial goal"},
    
    # PARTIAL STATE PRESERVATION (multiple constraints)
    {"id": "s_18", "diff": "hard", "nl": "Keep A-B stacked, keep C-D stacked, put E on A, and preserve D-C.", "desc": "Partial preserve"},
    {"id": "s_19", "diff": "hard", "nl": "Three towers: (A-B), (C-D), (E-F). Merge into one but keep relative order B-D-F as top.", "desc": "Complex preserve"},
    
    # VERY LARGE/DEEP STACKS
    {"id": "s_20", "diff": "hard", "nl": "Seven blocks G-H-I-J-K-L-M on table. Create tower M-L-K-J-I-H-G.", "desc": "7-block"},
    {"id": "s_21", "diff": "hard", "nl": "Eight blocks all on table. Stack them in pyramid order.", "desc": "8-block"},
    
    # REFERENCE AMBIGUITY
    {"id": "s_22", "diff": "hard", "nl": "The block is on the other block. Stack the third block on the first.", "desc": "Reference ambig"},
    {"id": "s_23", "diff": "hard", "nl": "Block X and block Y... swap them. Use standard naming.", "desc": "Named X,Y"},
    
    # DOMAIN CONFUSION (non-blocksworld mentions)
    {"id": "s_24", "diff": "hard", "nl": "Put the red component next to the blue structure.", "desc": "Color terms"},
    {"id": "s_25", "diff": "hard", "nl": "Arrange the items in descending height order.", "desc": "Height order"},
    
    # MIXED PRECISION REQUIREMENTS
    {"id": "s_26", "diff": "hard", "nl": "Place block A somewhere on or under block B depending on feasibility.", "desc": "Conditional"},
    {"id": "s_27", "diff": "hard", "nl": "Move blocks until the tallest tower has exactly 3 blocks or all blocks are on table.", "desc": "Conditional goal"},
    
    # CHAINED REASONING
    {"id": "s_28", "diff": "hard", "nl": "A is on B. B is on C. C is on D which is on table. If D is clear, unstack all. Otherwise, do nothing.", "desc": "Conditional chain"},
    
    # UNUSUAL BUT VALID
    {"id": "s_29", "diff": "medium", "nl": "Empty initial state with only (handempty). Create any valid tower.", "desc": "No blocks?"},
    {"id": "s_30", "diff": "medium", "nl": "All five blocks on table. Goal: keep them on table but permute their positions.", "desc": "Permute on table"},
]


class StressComparison:
    def __init__(self, domain_pddl: str, api_key: str, models: List[str]):
        self.domain_pddl = domain_pddl
        self.api_key = api_key
        self.models = models
        self.validator = PDDLValidator()
        self.planner = BFSPlanner(max_nodes=50_000)

    def run(self, output_path: str = None):
        print(f"\n{'='*90}")
        print("  GEMINI STRESS TEST — 30 Complex Problems")
        print(f"{'='*90}")
        print(f"  Models: {', '.join(self.models)}")
        print(f"  Problems: {len(STRESS_BENCHMARK)}")
        print(f"{'='*90}\n")

        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "models": self.models,
            "total_problems": len(STRESS_BENCHMARK),
            "model_stats": {},
            "per_problem": [],
        }

        for model in self.models:
            print(f"\n{'─'*90}")
            print(f"  {model}")
            print(f"{'─'*90}")
            model_results = self._test_model(model)
            results["model_stats"][model] = self._stats(model_results)
            results["per_problem"].extend(model_results)

        if output_path is None:
            output_path = pathlib.Path(__file__).parent / "results" / "stress_test_results.json"
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))

        self._summary(results)
        print(f"\n📁 Saved: {output_path}\n")
        return results

    def _test_model(self, model: str) -> List[Dict]:
        gen = NLToPDDLGenerator(self.domain_pddl, api_key=self.api_key, model_name=model)
        results = []

        for i, prob in enumerate(STRESS_BENCHMARK, 1):
            print(f"  [{i:2d}/30] {prob['id']:6s} {prob['desc']:20s} ... ", end="", flush=True)
            try:
                gen_res = gen.generate(prob["nl"], prob["id"])
                if gen_res["success"]:
                    val_res = self.validator.validate(gen_res["pddl"])
                    val_ok = val_res.is_valid
                    val_err = val_res.errors
                else:
                    val_ok = False
                    val_err = [gen_res["error"]]

                if val_ok and gen_res["success"]:
                    plan_res = self.planner.solve(gen_res["pddl"], prob["id"])
                    plan_ok = plan_res.success
                    plan_reason = plan_res.failure_reason
                    plan_len = plan_res.plan_length
                else:
                    plan_ok = False
                    plan_reason = val_err[0] if val_err else "Invalid"
                    plan_len = 0

                overall = gen_res["success"] and val_ok and plan_ok
                status = "✅" if overall else "❌"
                print(f"{status}")

                results.append({
                    "model": model,
                    "problem_id": prob["id"],
                    "difficulty": prob["diff"],
                    "description": prob["desc"],
                    "nl": prob["nl"],
                    "generation_success": gen_res["success"],
                    "validation_valid": val_ok,
                    "planning_success": plan_ok,
                    "plan_length": plan_len,
                    "error": val_err[0] if val_err else None,
                    "overall_success": overall,
                })
            except Exception as e:
                print(f"❌ ({str(e)[:40]})")
                results.append({
                    "model": model,
                    "problem_id": prob["id"],
                    "difficulty": prob["diff"],
                    "description": prob["desc"],
                    "nl": prob["nl"],
                    "generation_success": False,
                    "validation_valid": False,
                    "planning_success": False,
                    "plan_length": 0,
                    "error": str(e)[:100],
                    "overall_success": False,
                })
            time.sleep(0.5)

        return results

    def _stats(self, results: List[Dict]) -> Dict:
        total = len(results)
        return {
            "total": total,
            "generation": sum(1 for r in results if r["generation_success"]),
            "validation": sum(1 for r in results if r["validation_valid"]),
            "planning": sum(1 for r in results if r["planning_success"]),
            "overall": sum(1 for r in results if r["overall_success"]),
            "gen_rate": round(sum(1 for r in results if r["generation_success"]) / total, 3),
            "val_rate": round(sum(1 for r in results if r["validation_valid"]) / total, 3),
            "exec_rate": round(sum(1 for r in results if r["planning_success"]) / total, 3),
            "overall_rate": round(sum(1 for r in results if r["overall_success"]) / total, 3),
        }

    def _summary(self, results):
        stats = results["model_stats"]
        m1, m2 = self.models[0], self.models[1]
        s1, s2 = stats[m1], stats[m2]

        print(f"\n{'='*90}")
        print("  STRESS TEST RESULTS SUMMARY")
        print(f"{'='*90}")
        print(f"\n{'Metric':<25s} | {m1:<30s} | {m2:<30s}")
        print("─" * 95)
        print(f"{'Generation Rate':<25s} | {s1['gen_rate']*100:>6.1f}% ({s1['generation']}/30) | {s2['gen_rate']*100:>6.1f}% ({s2['generation']}/30)")
        print(f"{'Validation Rate':<25s} | {s1['val_rate']*100:>6.1f}% ({s1['validation']}/30) | {s2['val_rate']*100:>6.1f}% ({s2['validation']}/30)")
        print(f"{'Executability Rate':<25s} | {s1['exec_rate']*100:>6.1f}% ({s1['planning']}/30) | {s2['exec_rate']*100:>6.1f}% ({s2['planning']}/30)")
        print(f"{'Overall Success Rate':<25s} | {s1['overall_rate']*100:>6.1f}% ({s1['overall']}/30) | {s2['overall_rate']*100:>6.1f}% ({s2['overall']}/30)")
        print(f"{'='*90}")

        diff = abs(s1["overall_rate"] - s2["overall_rate"])
        if s1["overall_rate"] > s2["overall_rate"]:
            winner = m1
        elif s2["overall_rate"] > s1["overall_rate"]:
            winner = m2
        else:
            winner = "TIE"

        print(f"  **WINNER:** {winner} (gap: {diff*100:.1f}%)")
        print(f"{'='*90}\n")


def main():
    domain_path = pathlib.Path(__file__).parent / "blocksworld.pddl"
    if not domain_path.exists():
        domain_path = pathlib.Path(__file__).parent.parent / "domains" / "blocksworld.pddl"
    domain_pddl = domain_path.read_text()

    api_key = os.environ.get("GEMINI_API_KEY", "")
    if not api_key:
        raise ValueError("GEMINI_API_KEY not set")

    models = os.environ.get("STRESS_MODELS", "gemini-3-flash-preview,gemini-2.5-pro").split(",")

    comp = StressComparison(domain_pddl, api_key, models)
    comp.run()


if __name__ == "__main__":
    main()
