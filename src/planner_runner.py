"""
planner_runner.py  —  Phase 2
General PDDL planner using pyperplan (pure Python, handles any STRIPS domain).

Changes from Phase 1:
- Replaces the hardcoded Blocksworld BFS with pyperplan's general planner.
- Accepts domain PDDL as a string alongside the problem PDDL.
- Returns structured PlanResult with failure_reason for the critic.
- Plan steps are cleaned to action names only (not pyperplan's internal repr).
"""

import re
import os
import time
import tempfile
import logging
from dataclasses import dataclass, field
from typing import List, Optional

# Suppress pyperplan's verbose logging
logging.getLogger("pyperplan").setLevel(logging.ERROR)

from pyperplan.planner import _parse, _ground, _search, SEARCHES


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class PlanResult:
    success: bool
    plan: List[str] = field(default_factory=list)   # ["(pick ball1 rooma left)", ...]
    plan_length: int = 0
    nodes_expanded: int = 0
    elapsed_ms: float = 0.0
    failure_reason: Optional[str] = None             # fed to critic on failure
    error: Optional[str] = None

    def summary(self) -> str:
        if self.success:
            return (
                f"SOLVED in {self.plan_length} steps "
                f"({self.elapsed_ms:.1f}ms)"
            )
        return f"FAILED: {self.failure_reason or self.error}"


# ── Planner ───────────────────────────────────────────────────────────────────

class PDDLPlanner:
    """
    Solves a PDDL problem using pyperplan's BFS.

    Usage:
        planner = PDDLPlanner(domain_pddl_str)
        result = planner.solve(problem_pddl_str)
    """

    def __init__(self, domain_pddl: str, search_algorithm: str = "bfs"):
        self.domain_pddl = domain_pddl
        self.search_fn = SEARCHES.get(search_algorithm, SEARCHES["bfs"])

    def solve(self, problem_pddl: str, timeout_s: int = 30) -> PlanResult:
        result = PlanResult(success=False)
        domain_path = problem_path = None

        try:
            # Write to temp files — pyperplan requires file paths
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pddl", delete=False, prefix="domain_"
            ) as df:
                df.write(self.domain_pddl)
                domain_path = df.name

            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".pddl", delete=False, prefix="problem_"
            ) as pf:
                pf.write(problem_pddl)
                problem_path = pf.name

            t0 = time.time()

            parsed = _parse(domain_path, problem_path)
            task = _ground(parsed)
            solution = _search(task, self.search_fn, None)

            elapsed_ms = (time.time() - t0) * 1000

            if solution is None:
                result.failure_reason = (
                    "Planner exhausted search space — problem is unsolvable with the "
                    "given :init state and :goal. Likely cause: incomplete :init "
                    "(missing objects, wrong predicate values, or unsatisfiable goal)."
                )
                result.elapsed_ms = elapsed_ms
            else:
                result.success = True
                result.plan = [_clean_action(str(a)) for a in solution]
                result.plan_length = len(result.plan)
                result.elapsed_ms = elapsed_ms

        except Exception as e:
            err = str(e)
            result.error = err
            result.failure_reason = _classify_parse_error(err)

        finally:
            for p in [domain_path, problem_path]:
                if p and os.path.exists(p):
                    try:
                        os.unlink(p)
                    except OSError:
                        pass

        return result


# ── Helpers ───────────────────────────────────────────────────────────────────

def _clean_action(raw: str) -> str:
    """
    Extract just the action call from pyperplan's verbose action repr.
    Input:  "(pick ball1 rooma left)\n  PRE: ...\n  ADD: ...\n  DEL: ..."
    Output: "(pick ball1 rooma left)"
    """
    m = re.match(r'(\([^)]+\))', raw.strip())
    return m.group(1) if m else raw.split("\n")[0].strip()


def _classify_parse_error(error: str) -> str:
    """Map pyperplan parse errors to human-readable failure reasons for the critic."""
    e = error.lower()
    if "undefined" in e or "unknown" in e or "not defined" in e:
        return (
            f"Parse error — reference to undefined predicate or object: {error}. "
            "Check that all predicates in :init/:goal are declared in the domain "
            "and all objects are declared in :objects."
        )
    if "syntax" in e or "unexpected" in e or "token" in e:
        return f"PDDL syntax error: {error}. Check parentheses and section structure."
    if "attribute" in e or "none" in e.lower():
        return (
            f"Domain/problem structure error: {error}. "
            "Likely a missing section or malformed predicate definition."
        )
    return f"Planner error: {error}"
