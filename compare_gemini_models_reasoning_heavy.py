import json
import os
import pathlib
import datetime
import time
from typing import Dict, List, Set, Tuple

from nl_to_pddl import NLToPDDLGenerator
from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner, ProblemParser, make_fact


Fact = Tuple[str, ...]


def fact(predicate: str, *args: str) -> Fact:
    return make_fact(predicate, *args)


REASONING_HEAVY_CASES = [
    {
        "id": "rh_01_former_latter",
        "difficulty": "hard",
        "category": "coreference",
        "nl": (
            "Blocks A, B, C, and D are all on the table and clear. Put the former of A and B on the latter, "
            "then place D on C, and keep both supporting blocks on the table."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "d", "c"), fact("ontable", "b"), fact("ontable", "c")},
    },
    {
        "id": "rh_02_pronoun_resolution",
        "difficulty": "hard",
        "category": "coreference",
        "nl": (
            "A is on B and C is on D, with B and D on the table. Move the first top block onto the second top block, "
            "but leave its original support on the table."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("on", "a", "b"), fact("on", "c", "d"), fact("ontable", "b"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "c"), fact("handempty")},
        "expected_goal": {fact("on", "a", "c"), fact("ontable", "b"), fact("ontable", "d")},
    },
    {
        "id": "rh_03_distractor_clause",
        "difficulty": "hard",
        "category": "distractor",
        "nl": (
            "Ignore any ideas about color, weight, or size because the domain does not support them. "
            "The actual task is this: A, B, C, D, and E are on the table and clear. Build E on D on C, and separately B on A."
        ),
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "e", "d"), fact("on", "d", "c"), fact("on", "b", "a")},
    },
    {
        "id": "rh_04_nested_preservation",
        "difficulty": "hard",
        "category": "preservation",
        "nl": (
            "A is on B on the table, C is on D on the table, and E is alone on the table. Preserve the first stack exactly as it is, "
            "do not disturb the base of the second stack, and place E on top of C."
        ),
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("on", "c", "d"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "c"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "c", "d"), fact("on", "e", "c"), fact("ontable", "b"), fact("ontable", "d")},
    },
    {
        "id": "rh_05_aliasing_letters",
        "difficulty": "hard",
        "category": "aliasing",
        "nl": (
            "There are four blocks. Call them alpha, beta, gamma, and delta, corresponding respectively to A, B, C, and D. "
            "All are on the table and clear. Build delta on gamma on beta on alpha."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a")},
    },
    {
        "id": "rh_06_long_dependency_chain",
        "difficulty": "hard",
        "category": "long-context",
        "nl": (
            "Initially, A is on B, B is on the table, C is on D, D is on the table, and E and F are each on the table. "
            "After rearrangement, the block that originally supported A should support E, E should support the block that originally topped D, "
            "and that block should support F, while B remains on the table."
        ),
        "expected_objects": {"a", "b", "c", "d", "e", "f"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("on", "c", "d"), fact("ontable", "d"), fact("ontable", "e"), fact("ontable", "f"), fact("clear", "a"), fact("clear", "c"), fact("clear", "e"), fact("clear", "f"), fact("handempty")},
        "expected_goal": {fact("on", "e", "b"), fact("on", "c", "e"), fact("on", "f", "c"), fact("ontable", "b")},
    },
    {
        "id": "rh_07_negation_like_instruction",
        "difficulty": "hard",
        "category": "instruction-following",
        "nl": (
            "Do not create one tall tower. Instead, with A, B, C, D, and E all initially on the table and clear, create exactly two towers: B on A and E on D, leaving C on the table by itself."
        ),
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "b", "a"), fact("on", "e", "d"), fact("ontable", "c")},
    },
    {
        "id": "rh_08_cross_sentence_reference",
        "difficulty": "hard",
        "category": "coreference",
        "nl": (
            "A is on B. C and D are on the table. B is also on the table. The free block among C and D that comes later alphabetically should be placed on the earlier one. The original stack must remain unchanged."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "c"), fact("clear", "d"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "d", "c")},
    },
    {
        "id": "rh_09_overridden_instruction",
        "difficulty": "hard",
        "category": "override",
        "nl": (
            "At first glance you might think the goal is A on B, but ignore that. The true target is: A, B, C, and D start on the table and clear, and the final configuration should be C on B and B on A, while D stays on the table."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "d")},
    },
    {
        "id": "rh_10_multi_base_constraints",
        "difficulty": "hard",
        "category": "multi-constraint",
        "nl": (
            "Six blocks A through F are all on the table and clear. Build two towers, one with C on B on A and one with F on E on D. Both A and D must remain on the table as bases."
        ),
        "expected_objects": {"a", "b", "c", "d", "e", "f"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "c", "b"), fact("on", "b", "a"), fact("on", "f", "e"), fact("on", "e", "d"), fact("ontable", "a"), fact("ontable", "d")},
    },
    {
        "id": "rh_11_sparse_but_precise",
        "difficulty": "hard",
        "category": "sparse-context",
        "nl": (
            "Only these facts hold initially: A on B, B on table, C on table, D on table, clear A, clear C, clear D, handempty. Goal: keep A on B and add D on C."
        ),
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "c"), fact("clear", "d"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "d", "c")},
    },
    {
        "id": "rh_12_redundant_story",
        "difficulty": "hard",
        "category": "distractor",
        "nl": (
            "In a warehouse story that does not matter, blocks are mentioned as if they were crates. Ignore the story. The real planning problem is: A, B, C, D, E, and F are all on the table and clear. Build F on E, E on D, and separately C on B on A."
        ),
        "expected_objects": {"a", "b", "c", "d", "e", "f"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "f", "e"), fact("on", "e", "d"), fact("on", "c", "b"), fact("on", "b", "a")},
    },
]


class ReasoningHeavyComparison:
    def __init__(self, domain_pddl: str, api_key: str, models: List[str]):
        self.domain_pddl = domain_pddl
        self.api_key = api_key
        self.models = models
        self.validator = PDDLValidator()
        self.planner = BFSPlanner(max_nodes=80_000)
        self.parser = ProblemParser()

    def run(self, output_path: pathlib.Path) -> Dict:
        results = {
            "timestamp": datetime.datetime.now().isoformat(),
            "models": self.models,
            "total_problems": len(REASONING_HEAVY_CASES),
            "model_stats": {},
            "per_problem": [],
        }

        for model in self.models:
            print("\n" + "=" * 88)
            print(f"  REASONING-HEAVY RUN: {model}")
            print("=" * 88)
            rows = self._run_model(model)
            results["model_stats"][model] = self._compute_stats(rows)
            results["per_problem"].extend(rows)

        if len(self.models) >= 2:
            flash = results["model_stats"][self.models[0]]
            pro = results["model_stats"][self.models[1]]
            results["delta"] = {
                "overall_success_delta": pro["overall_success"] - flash["overall_success"],
                "faithfulness_success_delta": pro["faithfulness_success"] - flash["faithfulness_success"],
                "goal_match_delta": pro["goal_match"] - flash["goal_match"],
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        self._print_summary(results)
        return results

    def _run_model(self, model_name: str) -> List[Dict]:
        generator = NLToPDDLGenerator(self.domain_pddl, api_key=self.api_key, model_name=model_name)
        rows = []

        for index, case in enumerate(REASONING_HEAVY_CASES, 1):
            print(f"[{index:02d}/{len(REASONING_HEAVY_CASES)}] {case['id']} ({case['category']}) ... ", end="", flush=True)
            gen = generator.generate(case["nl"], case["id"])

            validation_valid = False
            validation_errors: List[str] = []
            objects_match = False
            init_match = False
            goal_match = False
            faithfulness_success = False
            planning_success = False
            plan_length = 0
            failure_reason = None

            if gen["success"]:
                validation = self.validator.validate(gen["pddl"])
                validation_valid = validation.is_valid
                validation_errors = validation.errors

                try:
                    parsed = self.parser.parse(gen["pddl"])
                    parsed_objects = set(obj.lower() for obj in parsed["objects"])
                    parsed_init = set(parsed["init"])
                    parsed_goal = set(parsed["goal"])
                    objects_match = parsed_objects == set(case["expected_objects"])
                    init_match = set(case["expected_init"]).issubset(parsed_init)
                    goal_match = set(case["expected_goal"]).issubset(parsed_goal)
                    faithfulness_success = validation_valid and objects_match and init_match and goal_match
                except Exception as exc:
                    validation_valid = False
                    validation_errors = validation_errors + [f"Parse error during scoring: {exc}"]

                if validation_valid:
                    plan = self.planner.solve(gen["pddl"], case["id"])
                    planning_success = plan.success
                    plan_length = plan.plan_length
                    failure_reason = plan.failure_reason or plan.error
                else:
                    failure_reason = "; ".join(validation_errors) if validation_errors else "Validation failed"
            else:
                failure_reason = gen.get("error")

            overall_success = faithfulness_success and planning_success
            print(
                f"gen={'Y' if gen['success'] else 'N'} "
                f"val={'Y' if validation_valid else 'N'} "
                f"obj={'Y' if objects_match else 'N'} "
                f"init={'Y' if init_match else 'N'} "
                f"goal={'Y' if goal_match else 'N'} "
                f"plan={'Y' if planning_success else 'N'}"
            )

            rows.append(
                {
                    "model": model_name,
                    "problem_id": case["id"],
                    "difficulty": case["difficulty"],
                    "category": case["category"],
                    "nl": case["nl"],
                    "generation_success": gen["success"],
                    "generation_error": gen.get("error"),
                    "generated_pddl": gen.get("pddl", ""),
                    "validation_valid": validation_valid,
                    "validation_errors": validation_errors,
                    "objects_match": objects_match,
                    "init_match": init_match,
                    "goal_match": goal_match,
                    "faithfulness_success": faithfulness_success,
                    "planning_success": planning_success,
                    "plan_length": plan_length,
                    "failure_reason": failure_reason,
                    "overall_success": overall_success,
                }
            )

            time.sleep(0.8)

        return rows

    def _compute_stats(self, rows: List[Dict]) -> Dict:
        total = len(rows)
        categories = sorted({row["category"] for row in rows})
        stats = {
            "total": total,
            "generation_success": sum(1 for row in rows if row["generation_success"]),
            "validation_success": sum(1 for row in rows if row["validation_valid"]),
            "object_match": sum(1 for row in rows if row["objects_match"]),
            "init_match": sum(1 for row in rows if row["init_match"]),
            "goal_match": sum(1 for row in rows if row["goal_match"]),
            "faithfulness_success": sum(1 for row in rows if row["faithfulness_success"]),
            "planning_success": sum(1 for row in rows if row["planning_success"]),
            "overall_success": sum(1 for row in rows if row["overall_success"]),
            "by_category": {},
        }
        for category in categories:
            subset = [row for row in rows if row["category"] == category]
            stats["by_category"][category] = {
                "total": len(subset),
                "goal_match": sum(1 for row in subset if row["goal_match"]),
                "faithfulness_success": sum(1 for row in subset if row["faithfulness_success"]),
                "overall_success": sum(1 for row in subset if row["overall_success"]),
            }
        return stats

    def _print_summary(self, results: Dict):
        print("\n" + "=" * 88)
        print("  REASONING-HEAVY SUMMARY")
        print("=" * 88)
        for model in self.models:
            stats = results["model_stats"][model]
            total = stats["total"]
            print(model)
            print(f"  Generation success : {stats['generation_success']}/{total}")
            print(f"  Validation success : {stats['validation_success']}/{total}")
            print(f"  Object match       : {stats['object_match']}/{total}")
            print(f"  Init match         : {stats['init_match']}/{total}")
            print(f"  Goal match         : {stats['goal_match']}/{total}")
            print(f"  Faithfulness       : {stats['faithfulness_success']}/{total}")
            print(f"  Planning success   : {stats['planning_success']}/{total}")
            print(f"  Overall success    : {stats['overall_success']}/{total}")
        if "delta" in results:
            print("-")
            print(f"  Pro minus Flash overall success : {results['delta']['overall_success_delta']}")
            print(f"  Pro minus Flash faithfulness    : {results['delta']['faithfulness_success_delta']}")
            print(f"  Pro minus Flash goal match      : {results['delta']['goal_match_delta']}")
        print("=" * 88)


def load_domain() -> str:
    script_dir = pathlib.Path(__file__).resolve().parent
    candidates = [script_dir / "blocksworld.pddl", script_dir / "domains" / "blocksworld.pddl"]
    for path in candidates:
        if path.exists():
            return path.read_text()
    raise FileNotFoundError(f"Could not find domain file. Checked: {candidates}")


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY before running comparison.")

    models = os.environ.get("COMPARISON_MODELS", "gemini-3-flash-preview,gemini-2.5-pro").split(",")
    models = [model.strip() for model in models if model.strip()]
    domain_pddl = load_domain()
    out_path = pathlib.Path(__file__).resolve().parent / "results" / "reasoning_heavy_comparison_results.json"
    runner = ReasoningHeavyComparison(domain_pddl, api_key, models)
    runner.run(out_path)


if __name__ == "__main__":
    main()