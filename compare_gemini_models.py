import json
import os
import pathlib
import datetime

from nl_to_pddl import NLToPDDLGenerator
from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner


COMPARISON_CASES = [
    {
        "id": "cmp_01_reverse_5",
        "nl": (
            "There are five blocks A, B, C, D, and E in a single stack with A on B, B on C, "
            "C on D, D on E, and E on the table. Rearrange to the reverse stack: E on D, D on C, "
            "C on B, B on A, with A on the table."
        ),
    },
    {
        "id": "cmp_02_two_towers_merge",
        "nl": (
            "Initially, A is on B on the table, and C is on D on the table, and E is alone on the table. "
            "Build one tower with E on C, C on A, A on D, D on B, and B on the table."
        ),
    },
    {
        "id": "cmp_03_hold_conflict_avoid",
        "nl": (
            "Blocks A, B, C, D are all on the table and clear. Build a tower D on C on B on A, and ensure "
            "A remains on the table at the end."
        ),
    },
    {
        "id": "cmp_04_partial_preservation",
        "nl": (
            "A is on B, B is on the table. C and D are each on the table and clear. Keep A on B unchanged, "
            "and place D on C."
        ),
    },
    {
        "id": "cmp_05_long_chain",
        "nl": (
            "There are six blocks A, B, C, D, E, F all on the table and clear. Build a single tower "
            "F on E on D on C on B on A, with A on the table."
        ),
    },
    {
        "id": "cmp_06_rearrange_mid",
        "nl": (
            "A is on B on C on the table, and D and E are on the table and clear. Rearrange to achieve "
            "E on D on B on A, and A on C, with C on the table."
        ),
    },
    {
        "id": "cmp_07_swap_top_middle",
        "nl": (
            "A is on B, B is on C, and C is on the table. Swap A and B so the final configuration is "
            "B on A on C with C on the table."
        ),
    },
    {
        "id": "cmp_08_goal_with_table_constraints",
        "nl": (
            "A, B, C, D, E are all on the table. Final goal: C on B, B on A, E on D, and both A and D remain on the table."
        ),
    },
    {
        "id": "cmp_09_disentangle_and_stack",
        "nl": (
            "A is on B, C is on D, and B and D are on the table. E is on the table. Rearrange to get "
            "A on C, C on E, and E on B, while D stays on the table clear."
        ),
    },
    {
        "id": "cmp_10_reverse_4_with_extra",
        "nl": (
            "A is on B, B is on C, C is on D, D on table, and E on table clear. Reverse only the 4-stack to "
            "D on C on B on A, with A on table, and leave E on table."
        ),
    },
    {
        "id": "cmp_11_seven_block_two_subgoals",
        "nl": (
            "Seven blocks A B C D E F G all start on table and clear. Build two independent towers: "
            "G on F on E, and D on C on B on A with A on table. Keep E and A on table as tower bases."
        ),
    },
    {
        "id": "cmp_12_distractor_text",
        "nl": (
            "Ignore this distractor sentence about colors and sizes because those predicates do not exist. "
            "Real task: blocks a b c d are on table clear. Goal is d on c, c on b, b on a, and a ontable."
        ),
    },
    {
        "id": "cmp_13_retain_relation",
        "nl": (
            "Initial: a on b, b on table, c on table, d on table, all needed clear facts consistent. "
            "Goal: keep a on b true, additionally place d on c, and keep b ontable."
        ),
    },
    {
        "id": "cmp_14_mixed_case_names",
        "nl": (
            "Blocks A, b, C, d, E are all on the table and clear initially. Build tower e on d on c on b on a. "
            "Output must still use lowercase object symbols in PDDL."
        ),
    },
    {
        "id": "cmp_15_sparse_init_requirements",
        "nl": (
            "We have blocks a b c d e. Initial facts: on a b, ontable b, ontable c, ontable d, ontable e, clear a, clear c, clear d, clear e, handempty. "
            "Goal: e on d, d on c, and c on b while preserving ontable b."
        ),
    },
    {
        "id": "cmp_16_reverse_with_preservation",
        "nl": (
            "Initial: a on b, b on c, c on table, d on table, e on table, clear a, clear d, clear e, handempty. "
            "Goal: c on b, b on a, a on table, and d on e."
        ),
    },
]


MODELS = [
    "gemini-2.0-flash",
    "gemini-2.5-pro",
]


def _load_domain() -> str:
    script_dir = pathlib.Path(__file__).resolve().parent
    candidates = [
        script_dir / "domains" / "blocksworld.pddl",
        script_dir / "blocksworld.pddl",
    ]
    for path in candidates:
        if path.exists():
            return path.read_text()
    raise FileNotFoundError(f"Domain file not found. Checked: {candidates}")


def _run_for_model(model_name: str, api_key: str, domain_pddl: str) -> dict:
    validator = PDDLValidator()
    planner = BFSPlanner(max_nodes=80_000)
    generator = NLToPDDLGenerator(domain_pddl=domain_pddl, api_key=api_key, model_name=model_name)

    per_problem = []
    generation_success = 0
    validation_success = 0
    planning_success = 0

    print("\n" + "=" * 72)
    print(f"  MODEL RUN: {model_name}")
    print("=" * 72)

    for case in COMPARISON_CASES:
        print(f"\n[{case['id']}] Generating...")
        gen = generator.generate(case["nl"], case["id"])

        val_valid = False
        val_errors = []
        plan_ok = False
        plan = []
        plan_length = 0
        failure_reason = None

        if gen["success"]:
            generation_success += 1
            val = validator.validate(gen["pddl"])
            val_valid = val.is_valid
            val_errors = val.errors
            if val_valid:
                validation_success += 1

            solve = planner.solve(gen["pddl"], case["id"])
            plan_ok = solve.success
            plan = solve.plan
            plan_length = solve.plan_length
            failure_reason = solve.failure_reason or solve.error
            if plan_ok:
                planning_success += 1
        else:
            failure_reason = gen.get("error")

        print(f"  Generation: {'OK' if gen['success'] else 'FAIL'}")
        print(f"  Validation: {'OK' if val_valid else 'FAIL'}")
        print(f"  Planning  : {'OK' if plan_ok else 'FAIL'}")

        per_problem.append(
            {
                "problem_id": case["id"],
                "nl": case["nl"],
                "generation_success": gen["success"],
                "generation_error": gen.get("error"),
                "generated_pddl": gen.get("pddl", ""),
                "validation_valid": val_valid,
                "validation_errors": val_errors,
                "plan_success": plan_ok,
                "plan_length": plan_length,
                "plan": plan,
                "failure_reason": failure_reason,
            }
        )

    total = len(COMPARISON_CASES)
    return {
        "model": model_name,
        "total_problems": total,
        "generation_success": generation_success,
        "validation_success": validation_success,
        "planning_success": planning_success,
        "generation_rate": round(generation_success / total, 4),
        "executability_rate": round(planning_success / total, 4),
        "per_problem": per_problem,
    }


def main():
    api_key = os.environ.get("GEMINI_API_KEY", "").strip()
    if not api_key:
        raise ValueError("Set GEMINI_API_KEY before running comparison.")

    domain_pddl = _load_domain()

    models_override = os.environ.get("COMPARISON_MODELS", "").strip()
    models = [m.strip() for m in models_override.split(",") if m.strip()] if models_override else MODELS

    case_limit = int(os.environ.get("COMPARISON_CASE_LIMIT", "0"))
    if case_limit > 0:
        global COMPARISON_CASES
        COMPARISON_CASES = COMPARISON_CASES[:case_limit]

    all_runs = []
    for model_name in models:
        all_runs.append(_run_for_model(model_name, api_key, domain_pddl))

    flash_model_name = models[0] if len(models) > 0 else None
    pro_model_name = models[1] if len(models) > 1 else None
    flash = next((r for r in all_runs if r["model"] == flash_model_name), None)
    pro = next((r for r in all_runs if r["model"] == pro_model_name), None)

    comparison = {
        "timestamp": datetime.datetime.now().isoformat(),
        "suite_size": len(COMPARISON_CASES),
        "runs": all_runs,
        "delta": {
            "planning_success_delta_pro_minus_flash": (pro["planning_success"] - flash["planning_success"]) if (pro and flash) else None,
            "executability_rate_delta_pro_minus_flash": round((pro["executability_rate"] - flash["executability_rate"]), 4) if (pro and flash) else None,
            "generation_success_delta_pro_minus_flash": (pro["generation_success"] - flash["generation_success"]) if (pro and flash) else None,
        },
    }

    out = pathlib.Path(__file__).resolve().parent / "results" / "model_comparison_gemini.json"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(comparison, indent=2))

    print("\n" + "=" * 72)
    print("  COMPARISON SUMMARY")
    print("=" * 72)
    for run in all_runs:
        total = run["total_problems"]
        print(f"  {run['model']}")
        print(f"    Generation : {run['generation_success']}/{total} ({run['generation_rate']*100:.1f}%)")
        print(f"    Validation : {run['validation_success']}/{total}")
        print(f"    Planning   : {run['planning_success']}/{total} ({run['executability_rate']*100:.1f}%)")
    print("-")
    print(
        "  Delta (Pro - Flash) Planning Success: "
        f"{comparison['delta']['planning_success_delta_pro_minus_flash']}"
    )
    print(
        "  Delta (Pro - Flash) Executability  : "
        f"{comparison['delta']['executability_rate_delta_pro_minus_flash']*100:.1f}%"
    )
    print(f"  Saved: {out}")
    print("=" * 72)


if __name__ == "__main__":
    main()
