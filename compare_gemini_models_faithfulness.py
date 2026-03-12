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


FAITHFULNESS_CASES = [
    {
        "id": "mix_01_easy_stack2",
        "difficulty": "easy",
        "nl": "Two blocks A and B are on the table and clear. Stack A on top of B.",
        "expected_objects": {"a", "b"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("clear", "a"), fact("clear", "b"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b")},
    },
    {
        "id": "mix_02_easy_tower3",
        "difficulty": "easy",
        "nl": "Blocks A, B, and C all start on the table and clear. Build a tower with C on B and B on A.",
        "expected_objects": {"a", "b", "c"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("ontable", "c"), fact("clear", "a"), fact("clear", "b"), fact("clear", "c"), fact("handempty")},
        "expected_goal": {fact("on", "c", "b"), fact("on", "b", "a")},
    },
    {
        "id": "mix_03_easy_swap",
        "difficulty": "easy",
        "nl": "A is on B and B is on the table. Swap them so B ends up on A and A ends up on the table.",
        "expected_objects": {"a", "b"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("clear", "a"), fact("handempty")},
        "expected_goal": {fact("on", "b", "a"), fact("ontable", "a")},
    },
    {
        "id": "mix_04_easy_keep_same",
        "difficulty": "easy",
        "nl": "A is already on B, B is on the table, and the goal is to keep that arrangement exactly.",
        "expected_objects": {"a", "b"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("clear", "a"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b")},
    },
    {
        "id": "mix_05_easy_tower4",
        "difficulty": "easy",
        "nl": "Four blocks A B C D are on the table and clear. Build a tower D on C on B on A, with A on the table.",
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "b"), fact("clear", "c"), fact("clear", "d"), fact("handempty")},
        "expected_goal": {fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "a")},
    },
    {
        "id": "mix_06_medium_reverse3",
        "difficulty": "medium",
        "nl": "A is on B, B is on C, and C is on the table. Rearrange to make C on B and B on A, with A on the table.",
        "expected_objects": {"a", "b", "c"},
        "expected_init": {fact("on", "a", "b"), fact("on", "b", "c"), fact("ontable", "c"), fact("clear", "a"), fact("handempty")},
        "expected_goal": {fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "a")},
    },
    {
        "id": "mix_07_medium_tower5",
        "difficulty": "medium",
        "nl": "Five blocks A through E are all on the table and clear. Build one tower with E on D, D on C, C on B, and B on A.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "b"), fact("clear", "c"), fact("clear", "d"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "e", "d"), fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a")},
    },
    {
        "id": "mix_08_medium_partial_preserve",
        "difficulty": "medium",
        "nl": "A is on B and B is on the table. C, D, and E are each on the table and clear. Keep A on B unchanged, and build E on D on C.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "c"), fact("clear", "d"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "e", "d"), fact("on", "d", "c")},
    },
    {
        "id": "mix_09_medium_two_towers",
        "difficulty": "medium",
        "nl": "Initially A is on B on the table, and C is on D on the table. Build a final tower with C on A, A on D, and D on B, while B remains on the table.",
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("on", "c", "d"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "c"), fact("handempty")},
        "expected_goal": {fact("on", "c", "a"), fact("on", "a", "d"), fact("on", "d", "b"), fact("ontable", "b")},
    },
    {
        "id": "mix_10_medium_distractor",
        "difficulty": "medium",
        "nl": "Ignore any mention of colors or sizes. In the real task, A B C D are all on the table and clear. Build D on C on B on A.",
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "b"), fact("clear", "c"), fact("clear", "d"), fact("handempty")},
        "expected_goal": {fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a")},
    },
    {
        "id": "mix_11_medium_case_normalize",
        "difficulty": "medium",
        "nl": "Blocks A, b, C, d, and E are on the table. Build a tower E on d on C on b on A using lowercase names in PDDL.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("ontable", "a"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "b"), fact("clear", "c"), fact("clear", "d"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "e", "d"), fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a")},
    },
    {
        "id": "mix_12_medium_statusquo_plus",
        "difficulty": "medium",
        "nl": "A is on B and B is on the table. C and D are on the table and clear. Keep A on B true, and also put D on C.",
        "expected_objects": {"a", "b", "c", "d"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("clear", "a"), fact("clear", "c"), fact("clear", "d"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "d", "c")},
    },
    {
        "id": "mix_13_hard_reverse4_extra",
        "difficulty": "hard",
        "nl": "A is on B, B is on C, C is on D, and D is on the table. E is also on the table and clear. Reverse the four-block stack so D is on C, C is on B, and B is on A, with A on the table, and leave E on the table.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("on", "a", "b"), fact("on", "b", "c"), fact("on", "c", "d"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "a"), fact("ontable", "e")},
    },
    {
        "id": "mix_14_hard_two_subgoals",
        "difficulty": "hard",
        "nl": "Seven blocks A B C D E F G all start on the table and clear. Build two independent towers: G on F on E, and D on C on B on A, with both E and A on the table.",
        "expected_objects": {"a", "b", "c", "d", "e", "f", "g"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "g", "f"), fact("on", "f", "e"), fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "e"), fact("ontable", "a")},
    },
    {
        "id": "mix_15_hard_sparse_init",
        "difficulty": "hard",
        "nl": "We have blocks A B C D E. Initially A is on B, B is on the table, and C, D, E are each on the table and clear. Build E on D on C while preserving B as the base under A.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("ontable", "c"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "c"), fact("clear", "d"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "e", "d"), fact("on", "d", "c"), fact("on", "a", "b"), fact("ontable", "b")},
    },
    {
        "id": "mix_16_hard_merge_three",
        "difficulty": "hard",
        "nl": "Three separate stacks exist: A on B, C on D, and E on F, with B D and F on the table. Merge them into one tower so A ends up on C, C ends up on E, and E ends up on B, while F stays on the table.",
        "expected_objects": {"a", "b", "c", "d", "e", "f"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("on", "c", "d"), fact("ontable", "d"), fact("on", "e", "f"), fact("ontable", "f"), fact("clear", "a"), fact("clear", "c"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "a", "c"), fact("on", "c", "e"), fact("on", "e", "b"), fact("ontable", "f")},
    },
    {
        "id": "mix_17_hard_long_tower6",
        "difficulty": "hard",
        "nl": "Six blocks A B C D E F all start on the table and clear. Build one tower F on E on D on C on B on A, with A on the table.",
        "expected_objects": {"a", "b", "c", "d", "e", "f"},
        "expected_init": {fact("handempty")},
        "expected_goal": {fact("on", "f", "e"), fact("on", "e", "d"), fact("on", "d", "c"), fact("on", "c", "b"), fact("on", "b", "a"), fact("ontable", "a")},
    },
    {
        "id": "mix_18_hard_preserve_and_attach",
        "difficulty": "hard",
        "nl": "Keep the existing stack A on B unchanged. Keep C on D unchanged. Put E on top of A. B and D should both remain on the table.",
        "expected_objects": {"a", "b", "c", "d", "e"},
        "expected_init": {fact("on", "a", "b"), fact("ontable", "b"), fact("on", "c", "d"), fact("ontable", "d"), fact("ontable", "e"), fact("clear", "a"), fact("clear", "c"), fact("clear", "e"), fact("handempty")},
        "expected_goal": {fact("on", "a", "b"), fact("on", "c", "d"), fact("on", "e", "a"), fact("ontable", "b"), fact("ontable", "d")},
    },
]


class FaithfulnessComparison:
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
            "total_problems": len(FAITHFULNESS_CASES),
            "model_stats": {},
            "per_problem": [],
        }

        for model in self.models:
            print("\n" + "=" * 84)
            print(f"  RUNNING MODEL: {model}")
            print("=" * 84)
            model_results = self._run_model(model)
            results["model_stats"][model] = self._compute_stats(model_results)
            results["per_problem"].extend(model_results)

        if len(self.models) >= 2:
            flash = results["model_stats"][self.models[0]]
            pro = results["model_stats"][self.models[1]]
            results["delta"] = {
                "overall_success_delta": pro["overall_success"] - flash["overall_success"],
                "faithfulness_success_delta": pro["faithfulness_success"] - flash["faithfulness_success"],
                "exact_goal_delta": pro["exact_goal_match"] - flash["exact_goal_match"],
            }

        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(results, indent=2))
        self._print_summary(results)
        return results

    def _run_model(self, model_name: str) -> List[Dict]:
        generator = NLToPDDLGenerator(self.domain_pddl, api_key=self.api_key, model_name=model_name)
        model_results = []

        for index, case in enumerate(FAITHFULNESS_CASES, 1):
            print(f"[{index:02d}/{len(FAITHFULNESS_CASES)}] {case['id']} ({case['difficulty']}) ... ", end="", flush=True)
            gen = generator.generate(case["nl"], case["id"])

            parsed_objects: Set[str] = set()
            parsed_init: Set[Fact] = set()
            parsed_goal: Set[Fact] = set()
            validation_valid = False
            validation_errors: List[str] = []
            plan_success = False
            plan_length = 0
            failure_reason = None
            objects_match = False
            init_match = False
            goal_match = False
            faithfulness_success = False

            if gen["success"]:
                validation = self.validator.validate(gen["pddl"])
                validation_valid = validation.is_valid
                validation_errors = validation.errors

                try:
                    parsed = self.parser.parse(gen["pddl"])
                    parsed_objects = set(o.lower() for o in parsed["objects"])
                    parsed_init = set(parsed["init"])
                    parsed_goal = set(parsed["goal"])
                except Exception as exc:
                    validation_valid = False
                    validation_errors = validation_errors + [f"Parse error during faithfulness check: {exc}"]

                objects_match = parsed_objects == set(case["expected_objects"])
                init_match = set(case["expected_init"]).issubset(parsed_init)
                goal_match = set(case["expected_goal"]).issubset(parsed_goal)
                faithfulness_success = validation_valid and objects_match and init_match and goal_match

                if validation_valid:
                    plan_result = self.planner.solve(gen["pddl"], case["id"])
                    plan_success = plan_result.success
                    plan_length = plan_result.plan_length
                    failure_reason = plan_result.failure_reason or plan_result.error
                else:
                    failure_reason = "; ".join(validation_errors) if validation_errors else "Validation failed"
            else:
                failure_reason = gen.get("error")

            overall_success = faithfulness_success and plan_success
            print(
                f"gen={'Y' if gen['success'] else 'N'} "
                f"val={'Y' if validation_valid else 'N'} "
                f"obj={'Y' if objects_match else 'N'} "
                f"init={'Y' if init_match else 'N'} "
                f"goal={'Y' if goal_match else 'N'} "
                f"plan={'Y' if plan_success else 'N'}"
            )

            model_results.append({
                "model": model_name,
                "problem_id": case["id"],
                "difficulty": case["difficulty"],
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
                "planning_success": plan_success,
                "plan_length": plan_length,
                "failure_reason": failure_reason,
                "overall_success": overall_success,
            })

            time.sleep(0.8)

        return model_results

    def _compute_stats(self, rows: List[Dict]) -> Dict:
        total = len(rows)
        stats = {
            "total": total,
            "generation_success": sum(1 for row in rows if row["generation_success"]),
            "validation_success": sum(1 for row in rows if row["validation_valid"]),
            "exact_object_match": sum(1 for row in rows if row["objects_match"]),
            "exact_init_match": sum(1 for row in rows if row["init_match"]),
            "exact_goal_match": sum(1 for row in rows if row["goal_match"]),
            "faithfulness_success": sum(1 for row in rows if row["faithfulness_success"]),
            "planning_success": sum(1 for row in rows if row["planning_success"]),
            "overall_success": sum(1 for row in rows if row["overall_success"]),
            "by_difficulty": {},
        }
        for difficulty in ["easy", "medium", "hard"]:
            subset = [row for row in rows if row["difficulty"] == difficulty]
            stats["by_difficulty"][difficulty] = {
                "total": len(subset),
                "faithfulness_success": sum(1 for row in subset if row["faithfulness_success"]),
                "planning_success": sum(1 for row in subset if row["planning_success"]),
                "overall_success": sum(1 for row in subset if row["overall_success"]),
            }
        return stats

    def _print_summary(self, results: Dict):
        print("\n" + "=" * 84)
        print("  FAITHFULNESS COMPARISON SUMMARY")
        print("=" * 84)
        for model in self.models:
            stats = results["model_stats"][model]
            total = stats["total"]
            print(model)
            print(f"  Generation success  : {stats['generation_success']}/{total}")
            print(f"  Validation success  : {stats['validation_success']}/{total}")
            print(f"  Object match        : {stats['exact_object_match']}/{total}")
            print(f"  Init match          : {stats['exact_init_match']}/{total}")
            print(f"  Goal match          : {stats['exact_goal_match']}/{total}")
            print(f"  Faithfulness        : {stats['faithfulness_success']}/{total}")
            print(f"  Planning success    : {stats['planning_success']}/{total}")
            print(f"  Overall success     : {stats['overall_success']}/{total}")
        if "delta" in results:
            print("-")
            print(f"  Pro minus Flash overall success : {results['delta']['overall_success_delta']}")
            print(f"  Pro minus Flash faithfulness    : {results['delta']['faithfulness_success_delta']}")
            print(f"  Pro minus Flash goal match      : {results['delta']['exact_goal_delta']}")
        print("=" * 84)


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
    output_path = pathlib.Path(__file__).resolve().parent / "results" / "faithfulness_comparison_results.json"

    runner = FaithfulnessComparison(domain_pddl, api_key, models)
    runner.run(output_path)


if __name__ == "__main__":
    main()
