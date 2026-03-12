import json
import pathlib
from dataclasses import dataclass
from typing import List, Dict

from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner


@dataclass
class ComplexCase:
    case_id: str
    description: str
    pddl: str
    expected_validation: bool
    expected_planning: bool


COMPLEX_CASES: List[ComplexCase] = [
    ComplexCase(
        case_id="cx_01_6tower_solvable",
        description="6-block tower from all blocks on table (high branching, solvable).",
        expected_validation=True,
        expected_planning=True,
        pddl="""
(define (problem cx-01)
  (:domain blocksworld)
  (:objects a b c d e f)
  (:init (ontable a) (ontable b) (ontable c) (ontable d) (ontable e) (ontable f)
         (clear a) (clear b) (clear c) (clear d) (clear e) (clear f) (handempty))
  (:goal (and (on f e) (on e d) (on d c) (on c b) (on b a) (ontable a)))
)
""",
    ),
    ComplexCase(
        case_id="cx_02_cycle_goal_unsat",
        description="Cyclic goal (on a b and on b a) is unsatisfiable.",
        expected_validation=True,
        expected_planning=False,
        pddl="""
(define (problem cx-02)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b) (on b a)))
)
""",
    ),
    ComplexCase(
        case_id="cx_03_handempty_holding_unsat",
        description="Goal requires (handempty) and (holding a) simultaneously (unsatisfiable).",
        expected_validation=True,
        expected_planning=False,
        pddl="""
(define (problem cx-03)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (holding a) (handempty)))
)
""",
    ),
    ComplexCase(
        case_id="cx_04_invalid_predicate",
                description="Unknown predicate in init should fail validation and planning.",
        expected_validation=False,
        expected_planning=False,
        pddl="""
(define (problem cx-04)
  (:domain blocksworld)
  (:objects a b)
    (:init (ontable a) (ontable b) (clear a) (clear b) (handempty) (stacked a b))
    (:goal (and (on a b) (on b a)))
)
""",
    ),
    ComplexCase(
        case_id="cx_05_undeclared_object",
                description="Init references undeclared object c (invalid + unsatisfiable).",
        expected_validation=False,
        expected_planning=False,
        pddl="""
(define (problem cx-05)
  (:domain blocksworld)
  (:objects a b)
    (:init (ontable a) (ontable b) (clear a) (clear b) (handempty) (clear c))
    (:goal (and (holding a) (handempty)))
)
""",
    ),
    ComplexCase(
        case_id="cx_06_deep_reversal_solvable",
        description="Reverse a 4-block stack, solvable with longer plan.",
        expected_validation=True,
        expected_planning=True,
        pddl="""
(define (problem cx-06)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (on a b) (on b c) (on c d) (ontable d) (clear a) (handempty))
  (:goal (and (on d c) (on c b) (on b a) (ontable a)))
)
""",
    ),
    ComplexCase(
        case_id="cx_07_missing_goal",
        description="Missing goal section should fail validation and planning.",
        expected_validation=False,
        expected_planning=False,
        pddl="""
(define (problem cx-07)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
)
""",
    ),
    ComplexCase(
        case_id="cx_08_wrong_arity",
        description="Wrong predicate arity in init should fail validation.",
        expected_validation=False,
        expected_planning=False,
        pddl="""
(define (problem cx-08)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)
""",
    ),
]


def run_complex_cases() -> Dict:
    validator = PDDLValidator()
    planner = BFSPlanner(max_nodes=50_000)

    results = []
    validation_expected_hits = 0
    planning_expected_hits = 0

    print("\n" + "=" * 68)
    print("  COMPLEX CASE SUITE (MIXED PASS/FAIL)")
    print("=" * 68)

    for case in COMPLEX_CASES:
        validation = validator.validate(case.pddl)
        plan_result = planner.solve(case.pddl, problem_id=case.case_id)

        validation_match = validation.is_valid == case.expected_validation
        planning_match = plan_result.success == case.expected_planning

        if validation_match:
            validation_expected_hits += 1
        if planning_match:
            planning_expected_hits += 1

        status = "✅" if (validation_match and planning_match) else "❌"
        print(f"\n[{case.case_id}] {status}")
        print(f"  Description          : {case.description}")
        print(
            f"  Validation           : got={validation.is_valid} expected={case.expected_validation}"
        )
        print(
            f"  Planning             : got={plan_result.success} expected={case.expected_planning}"
        )
        if not validation.is_valid and validation.errors:
            print(f"  Validation errors    : {validation.errors}")
        if not plan_result.success:
            print(f"  Failure reason       : {plan_result.failure_reason or plan_result.error}")
        else:
            print(f"  Plan length          : {plan_result.plan_length}")

        results.append(
            {
                "case_id": case.case_id,
                "description": case.description,
                "expected_validation": case.expected_validation,
                "expected_planning": case.expected_planning,
                "validation_valid": validation.is_valid,
                "validation_errors": validation.errors,
                "planning_success": plan_result.success,
                "plan_length": plan_result.plan_length,
                "plan": plan_result.plan,
                "failure_reason": plan_result.failure_reason,
                "expectation_match": validation_match and planning_match,
            }
        )

    summary = {
        "total_cases": len(COMPLEX_CASES),
        "validation_expectation_match": f"{validation_expected_hits}/{len(COMPLEX_CASES)}",
        "planning_expectation_match": f"{planning_expected_hits}/{len(COMPLEX_CASES)}",
        "cases": results,
    }

    out_path = pathlib.Path(__file__).parent / "results" / "complex_case_results.json"
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(summary, indent=2))

    print("\n" + "=" * 68)
    print("  COMPLEX SUITE SUMMARY")
    print("=" * 68)
    print(f"  Total cases                    : {summary['total_cases']}")
    print(f"  Validation expectation match   : {summary['validation_expectation_match']}")
    print(f"  Planning expectation match     : {summary['planning_expectation_match']}")
    print(f"  Results saved                  : {out_path}")
    print("=" * 68)

    return summary


if __name__ == "__main__":
    run_complex_cases()
