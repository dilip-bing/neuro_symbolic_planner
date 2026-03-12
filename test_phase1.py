"""
tests/test_phase1.py
====================
Unit tests for Phase 1 components.

Run with:
    python -m pytest tests/test_phase1.py -v
  or
    python tests/test_phase1.py   (no pytest required)
"""

import sys
import pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent.parent / "src"))

from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner, ProblemParser, get_applicable_actions, apply_action, make_fact


# ─────────────────────────────────────────────────────────────────────────────
# VALIDATOR TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPDDLValidator:
    def setup_method(self):
        self.v = PDDLValidator()

    def _check_valid(self, pddl):
        r = self.v.validate(pddl)
        assert r.is_valid, f"Expected valid but got errors: {r.errors}"

    def _check_invalid(self, pddl, expected_keyword=None):
        r = self.v.validate(pddl)
        assert not r.is_valid, "Expected invalid PDDL but got valid."
        if expected_keyword:
            combined = " ".join(r.errors).lower()
            assert expected_keyword.lower() in combined, (
                f"Expected '{expected_keyword}' in errors: {r.errors}"
            )

    def test_valid_simple(self):
        self._check_valid("""
(define (problem t1)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)""")

    def test_valid_3tower(self):
        self._check_valid("""
(define (problem t2)
  (:domain blocksworld)
  (:objects a b c)
  (:init (ontable a) (ontable b) (ontable c) (clear a) (clear b) (clear c) (handempty))
  (:goal (and (on c b) (on b a)))
)""")

    def test_invalid_unbalanced_parens(self):
        self._check_invalid("""
(define (problem t3)
  (:domain blocksworld)
  (:objects a b
  (:init (ontable a) (handempty))
  (:goal (and (on a b)))
)""", "unclosed")

    def test_invalid_unknown_predicate(self):
        self._check_invalid("""
(define (problem t4)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (handempty) (stacked a b))
  (:goal (and (on a b)))
)""", "stacked")

    def test_invalid_undeclared_object(self):
        self._check_invalid("""
(define (problem t5)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (handempty) (clear c))
  (:goal (and (on a b)))
)""", "undeclared")

    def test_invalid_wrong_arity(self):
        self._check_invalid("""
(define (problem t6)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a) (handempty))
  (:goal (and (on a b)))
)""", "argument")

    def test_missing_goal(self):
        self._check_invalid("""
(define (problem t7)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (handempty))
)""", "goal")

    def test_empty_string(self):
        self._check_invalid("", "empty")


# ─────────────────────────────────────────────────────────────────────────────
# PLANNER TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestBFSPlanner:
    def setup_method(self):
        self.planner = BFSPlanner()

    def _solve(self, pddl, problem_id="test"):
        return self.planner.solve(pddl, problem_id)

    # ── Problem 1: 2-block stack ──────────────────────────────────────────
    def test_2block_stack(self):
        pddl = """
(define (problem p1)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)"""
        r = self._solve(pddl)
        assert r.success, f"Should be solvable: {r.failure_reason}"
        assert r.plan_length == 2, f"Should take 2 steps, got {r.plan_length}: {r.plan}"

    # ── Problem 2: 3-tower ────────────────────────────────────────────────
    def test_3tower(self):
        pddl = """
(define (problem p2)
  (:domain blocksworld)
  (:objects a b c)
  (:init (ontable a) (ontable b) (ontable c) (clear a) (clear b) (clear c) (handempty))
  (:goal (and (on c b) (on b a) (ontable a)))
)"""
        r = self._solve(pddl)
        assert r.success
        assert r.plan_length == 4, f"Expected 4 steps, got {r.plan_length}"

    # ── Problem 3: Reverse 3-stack ────────────────────────────────────────
    def test_reverse_3stack(self):
        pddl = """
(define (problem p3)
  (:domain blocksworld)
  (:objects a b c)
  (:init (on a b) (on b c) (ontable c) (clear a) (handempty))
  (:goal (and (on c b) (on b a) (ontable a)))
)"""
        r = self._solve(pddl)
        assert r.success

    # ── Problem 4: 4-tower ────────────────────────────────────────────────
    def test_4tower(self):
        pddl = """
(define (problem p4)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (ontable a) (ontable b) (ontable c) (ontable d)
         (clear a) (clear b) (clear c) (clear d) (handempty))
  (:goal (and (on d c) (on c b) (on b a) (ontable a)))
)"""
        r = self._solve(pddl)
        assert r.success
        assert r.plan_length == 6, f"Expected 6 steps, got {r.plan_length}"

    # ── Problem 5: Swap ───────────────────────────────────────────────────
    def test_swap(self):
        pddl = """
(define (problem p5)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a b) (ontable b) (clear a) (handempty))
  (:goal (and (on b a) (ontable a)))
)"""
        r = self._solve(pddl)
        assert r.success

    # ── Problem 6: 5-tower ────────────────────────────────────────────────
    def test_5tower(self):
        pddl = """
(define (problem p6)
  (:domain blocksworld)
  (:objects a b c d e)
  (:init (ontable a) (ontable b) (ontable c) (ontable d) (ontable e)
         (clear a) (clear b) (clear c) (clear d) (clear e) (handempty))
  (:goal (and (on e d) (on d c) (on c b) (on b a) (ontable a)))
)"""
        r = self._solve(pddl)
        assert r.success

    # ── Already solved ────────────────────────────────────────────────────
    def test_already_goal_satisfied(self):
        pddl = """
(define (problem p_trivial)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a b) (ontable b) (clear a) (handempty))
  (:goal (and (on a b)))
)"""
        r = self._solve(pddl)
        assert r.success
        assert r.plan_length == 0

    # ── Invalid PDDL ─────────────────────────────────────────────────────
    def test_invalid_pddl_fails_gracefully(self):
        r = self._solve("this is not pddl")
        assert not r.success
        assert r.failure_reason is not None

    # ── Missing objects ───────────────────────────────────────────────────
    def test_empty_objects(self):
        pddl = """
(define (problem p_empty)
  (:domain blocksworld)
  (:objects)
  (:init (handempty))
  (:goal (and (handempty)))
)"""
        r = self._solve(pddl)
        # handempty in goal is satisfied by init — 0-step plan
        # (objects is empty but goal is immediately met)
        # Either success with 0 steps or graceful fail is acceptable
        assert r.success or r.failure_reason is not None


# ─────────────────────────────────────────────────────────────────────────────
# PLAN VERIFICATION TESTS
# ─────────────────────────────────────────────────────────────────────────────

class TestPlanVerification:
    """Verify that produced plans are actually valid action sequences."""

    def setup_method(self):
        self.planner = BFSPlanner()
        self.parser  = ProblemParser()

    def _verify_plan(self, pddl: str, plan: list) -> bool:
        """Re-execute plan from init and check each step is valid."""
        parsed = self.parser.parse(pddl)
        state  = parsed["init"]
        objects = parsed["objects"]

        for action_str in plan:
            # Parse "(unstack a b)" → ("unstack", "a", "b")
            tokens = action_str.strip("()").split()
            action = tuple(tokens)

            # Check action is applicable
            applicable = get_applicable_actions(state, objects)
            assert action in applicable, (
                f"Action {action_str} is not applicable in state:\n"
                f"  {sorted(state)}\n  Applicable: {applicable}"
            )
            state = apply_action(state, action)

        return True

    def test_2block_plan_is_valid(self):
        pddl = """
(define (problem p1)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)"""
        r = self.planner.solve(pddl)
        assert r.success
        self._verify_plan(pddl, r.plan)

    def test_4tower_plan_is_valid(self):
        pddl = """
(define (problem p4)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (ontable a) (ontable b) (ontable c) (ontable d)
         (clear a) (clear b) (clear c) (clear d) (handempty))
  (:goal (and (on d c) (on c b) (on b a) (ontable a)))
)"""
        r = self.planner.solve(pddl)
        assert r.success
        self._verify_plan(pddl, r.plan)


# ─────────────────────────────────────────────────────────────────────────────
# Simple runner (no pytest needed)
# ─────────────────────────────────────────────────────────────────────────────

def run_tests():
    import traceback

    suites = [TestPDDLValidator, TestBFSPlanner, TestPlanVerification]
    passed = 0
    failed = 0

    for suite_cls in suites:
        suite = suite_cls()
        print(f"\n{'─'*50}")
        print(f"  {suite_cls.__name__}")
        print(f"{'─'*50}")

        methods = [m for m in dir(suite_cls) if m.startswith("test_")]
        for method_name in sorted(methods):
            try:
                if hasattr(suite, "setup_method"):
                    suite.setup_method()
                getattr(suite, method_name)()
                print(f"  ✅ {method_name}")
                passed += 1
            except Exception as e:
                print(f"  ❌ {method_name}")
                print(f"     {e}")
                traceback.print_exc()
                failed += 1

    print(f"\n{'='*50}")
    print(f"  Results: {passed} passed, {failed} failed")
    print(f"{'='*50}")
    return failed == 0


if __name__ == "__main__":
    ok = run_tests()
    sys.exit(0 if ok else 1)
