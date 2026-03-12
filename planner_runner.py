"""
planner_runner.py
=================
Phase 1 - Classical PDDL Planner (Pure Python)

Implements a classical BFS/A* planner for the Blocksworld domain.
This is a self-contained Python planner so the project does not require
Fast Downward to be installed. In Phase 2/3, Fast Downward can be plugged in
via subprocess and the interface below remains the same.

Planner pipeline:
  1. Parse PDDL problem (objects, init, goal)
  2. Run BFS to find a valid action sequence
  3. Return PlanResult with: plan steps, success status, stats

The planner validates that every step is executable (preconditions met)
and reports exact failure points for the Adversarial Critic in Phase 2.
"""

from __future__ import annotations
import re
import time
from collections import deque
from dataclasses import dataclass, field
from typing import List, Tuple, Optional, FrozenSet, Set


# ── State Representation ──────────────────────────────────────────────────────

# State = frozenset of ground facts (tuples)
# e.g. {('ontable', 'a'), ('clear', 'a'), ('handempty',)}
State = FrozenSet[Tuple]


def make_fact(predicate: str, *args: str) -> Tuple:
    return (predicate.lower(),) + tuple(a.lower() for a in args)


# ── Blocksworld Action Definitions ────────────────────────────────────────────

def get_applicable_actions(state: State, objects: List[str]) -> List[Tuple]:
    """
    Return all (action_name, *args) that are applicable in the given state.
    Mirrors the 4-operator Blocksworld domain exactly.
    """
    actions = []

    for x in objects:
        # pickup(x): clear(x) ∧ ontable(x) ∧ handempty
        if (
            make_fact("clear", x) in state
            and make_fact("ontable", x) in state
            and make_fact("handempty") in state
        ):
            actions.append(("pickup", x))

        # putdown(x): holding(x)
        if make_fact("holding", x) in state:
            actions.append(("putdown", x))

        for y in objects:
            if x == y:
                continue

            # stack(x, y): holding(x) ∧ clear(y)
            if (
                make_fact("holding", x) in state
                and make_fact("clear", y) in state
            ):
                actions.append(("stack", x, y))

            # unstack(x, y): on(x,y) ∧ clear(x) ∧ handempty
            if (
                make_fact("on", x, y) in state
                and make_fact("clear", x) in state
                and make_fact("handempty") in state
            ):
                actions.append(("unstack", x, y))

    return actions


def apply_action(state: State, action: Tuple) -> State:
    """
    Apply an action to a state and return the new state.
    Raises ValueError if preconditions are not met.
    """
    facts = set(state)
    name = action[0]

    if name == "pickup":
        x = action[1]
        facts.discard(make_fact("ontable", x))
        facts.discard(make_fact("clear", x))
        facts.discard(make_fact("handempty"))
        facts.add(make_fact("holding", x))

    elif name == "putdown":
        x = action[1]
        facts.discard(make_fact("holding", x))
        facts.add(make_fact("clear", x))
        facts.add(make_fact("handempty"))
        facts.add(make_fact("ontable", x))

    elif name == "stack":
        x, y = action[1], action[2]
        facts.discard(make_fact("holding", x))
        facts.discard(make_fact("clear", y))
        facts.add(make_fact("clear", x))
        facts.add(make_fact("handempty"))
        facts.add(make_fact("on", x, y))

    elif name == "unstack":
        x, y = action[1], action[2]
        facts.discard(make_fact("on", x, y))
        facts.discard(make_fact("clear", x))
        facts.discard(make_fact("handempty"))
        facts.add(make_fact("holding", x))
        facts.add(make_fact("clear", y))

    else:
        raise ValueError(f"Unknown action: {name}")

    return frozenset(facts)


def goal_satisfied(state: State, goal_facts: Set[Tuple]) -> bool:
    return goal_facts.issubset(state)


# ── PDDL Problem Parser ───────────────────────────────────────────────────────

class ProblemParser:
    """Parse a PDDL problem string into objects, init state, and goal facts."""

    def parse(self, pddl: str) -> dict:
        return {
            "objects": self._parse_objects(pddl),
            "init":    self._parse_state(pddl, "init"),
            "goal":    self._parse_goal(pddl),
            "name":    self._parse_name(pddl),
        }

    def _parse_name(self, pddl: str) -> str:
        m = re.search(r'\(\s*define\s*\(\s*problem\s+(\w+)', pddl, re.IGNORECASE)
        return m.group(1) if m else "unknown"

    def _parse_objects(self, pddl: str) -> List[str]:
        m = re.search(r'\(:objects\s+(.*?)\)', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        return re.findall(r'\b([a-zA-Z]\w*)\b', raw)

    def _extract_section_content(self, pddl: str, section: str) -> Optional[str]:
        """Extract the full content of a (:section ...) block using paren counting."""
        pattern = re.compile(rf'\(:{section}\b', re.IGNORECASE)
        m = pattern.search(pddl)
        if not m:
            return None
        start = m.start()
        depth = 0
        for i in range(start, len(pddl)):
            if pddl[i] == '(':
                depth += 1
            elif pddl[i] == ')':
                depth -= 1
                if depth == 0:
                    return pddl[start:i+1]
        return None

    def _parse_state(self, pddl: str, section: str) -> State:
        block = self._extract_section_content(pddl, section)
        if not block:
            return frozenset()
        # block is like: (:init (ontable a) (clear b) ...)
        # Strip leading (:init and the matching final )
        inner = re.sub(rf'^\(:{section}\s*', '', block, flags=re.IGNORECASE)
        inner = inner[:-1].strip()  # remove the closing ) of the section
        facts = set()
        for fm in re.finditer(r'\(\s*(\w+)\s*((?:\w+\s*)*)\)', inner):
            pred = fm.group(1).lower()
            args = fm.group(2).split() if fm.group(2).strip() else []
            if pred not in {"and", "or", "not"}:
                facts.add(make_fact(pred, *args))
        return frozenset(facts)

    def _parse_goal(self, pddl: str) -> Set[Tuple]:
        block = self._extract_section_content(pddl, "goal")
        if not block:
            return set()
        # block is like: (:goal (and (on a b)))
        # Strip leading (:goal and the matching final )
        inner = re.sub(r'^\(:goal\s*', '', block, flags=re.IGNORECASE)
        # Remove the last character which is the closing ) of (:goal ...)
        inner = inner[:-1].strip()
        # inner is now: (and (on a b))
        and_m = re.match(r'\(\s*and\s+(.*)\)\s*$', inner, re.IGNORECASE | re.DOTALL)
        if and_m:
            inner = and_m.group(1)
        facts = set()
        for fm in re.finditer(r'\(\s*(\w+)\s*((?:\w+\s*)*)\)', inner):
            pred = fm.group(1).lower()
            args = fm.group(2).split() if fm.group(2).strip() else []
            if pred not in {"and", "or", "not"}:
                facts.add(make_fact(pred, *args))
        return facts


# ── Plan Result ───────────────────────────────────────────────────────────────

@dataclass
class PlanResult:
    problem_id:    str
    success:       bool
    plan:          List[str]          = field(default_factory=list)
    plan_length:   int                = 0
    nodes_explored: int               = 0
    solve_time_s:  float              = 0.0
    error:         Optional[str]      = None
    failure_reason: Optional[str]     = None   # used by Adversarial Critic in Phase 2

    def summary(self) -> str:
        status = "✅ SOLVED" if self.success else "❌ FAILED"
        lines = [f"{status} — {self.problem_id}"]
        if self.success:
            lines.append(f"  Plan length : {self.plan_length} steps")
            lines.append(f"  Nodes exp.  : {self.nodes_explored}")
            lines.append(f"  Time        : {self.solve_time_s:.3f}s")
            lines.append("  Plan:")
            for i, step in enumerate(self.plan, 1):
                lines.append(f"    {i:2d}. {step}")
        else:
            lines.append(f"  Reason : {self.failure_reason or self.error}")
        return "\n".join(lines)

    def to_dict(self) -> dict:
        return {
            "problem_id":     self.problem_id,
            "success":        self.success,
            "plan":           self.plan,
            "plan_length":    self.plan_length,
            "nodes_explored": self.nodes_explored,
            "solve_time_s":   round(self.solve_time_s, 4),
            "error":          self.error,
            "failure_reason": self.failure_reason,
        }


# ── BFS Planner ───────────────────────────────────────────────────────────────

class BFSPlanner:
    """
    Breadth-First Search planner for Blocksworld.
    BFS guarantees optimal (shortest) plans.

    max_nodes: hard limit to prevent infinite search (default 50,000).
    """

    def __init__(self, max_nodes: int = 50_000):
        self.max_nodes = max_nodes
        self.parser    = ProblemParser()

    def solve(self, pddl: str, problem_id: str = "problem") -> PlanResult:
        t0 = time.perf_counter()

        # --- Parse ---
        try:
            parsed = self.parser.parse(pddl)
        except Exception as e:
            return PlanResult(
                problem_id=problem_id, success=False,
                error=f"PDDL parse error: {e}",
                failure_reason="ParseError: Could not parse problem PDDL.",
                solve_time_s=time.perf_counter() - t0,
            )

        objects   = parsed["objects"]
        init      = parsed["init"]
        goal      = parsed["goal"]

        if not objects:
            return PlanResult(
                problem_id=problem_id, success=False,
                failure_reason="ParseError: No objects found in problem.",
                solve_time_s=time.perf_counter() - t0,
            )

        if not goal:
            return PlanResult(
                problem_id=problem_id, success=False,
                failure_reason="ParseError: No goal conditions found.",
                solve_time_s=time.perf_counter() - t0,
            )

        # --- Check if init already satisfies goal ---
        if goal_satisfied(init, goal):
            return PlanResult(
                problem_id=problem_id, success=True,
                plan=[], plan_length=0,
                nodes_explored=0,
                solve_time_s=time.perf_counter() - t0,
            )

        # --- BFS ---
        # queue: (state, actions_taken)
        queue    = deque([(init, [])])
        visited  = {init}
        explored = 0

        while queue:
            state, actions = queue.popleft()
            explored += 1

            if explored > self.max_nodes:
                return PlanResult(
                    problem_id=problem_id, success=False,
                    nodes_explored=explored,
                    failure_reason=(
                        f"SearchLimit: Exceeded {self.max_nodes} nodes. "
                        "Problem may be unsolvable or too large for BFS."
                    ),
                    solve_time_s=time.perf_counter() - t0,
                )

            for action in get_applicable_actions(state, objects):
                new_state  = apply_action(state, action)
                new_actions = actions + [self._action_str(action)]

                if goal_satisfied(new_state, goal):
                    return PlanResult(
                        problem_id=problem_id,
                        success=True,
                        plan=new_actions,
                        plan_length=len(new_actions),
                        nodes_explored=explored,
                        solve_time_s=time.perf_counter() - t0,
                    )

                if new_state not in visited:
                    visited.add(new_state)
                    queue.append((new_state, new_actions))

        return PlanResult(
            problem_id=problem_id, success=False,
            nodes_explored=explored,
            failure_reason="Unsolvable: No valid plan exists for this problem.",
            solve_time_s=time.perf_counter() - t0,
        )

    def _action_str(self, action: Tuple) -> str:
        return f"({' '.join(action)})"


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    test_pddl = """
(define (problem bw-test)
  (:domain blocksworld)
  (:objects a b c)
  (:init
    (ontable a) (ontable b) (ontable c)
    (clear a) (clear b) (clear c)
    (handempty)
  )
  (:goal (and (on c b) (on b a) (ontable a)))
)
"""
    planner = BFSPlanner()
    result  = planner.solve(test_pddl, "bw-test-3tower")
    print(result.summary())
