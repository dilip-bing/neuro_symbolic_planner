"""
repair_loop.py  —  Phase 2
Adversarial Critic + Iterative Fix/Validate Loop.

This is the central Phase 2 contribution.

Loop logic (per problem):
  1. Generator produces initial PDDL (iteration 0)
  2. Validator checks syntax + semantics
  3. Planner attempts to solve
  4. If valid + solved → DONE (record iterations_needed)
  5. Else → Critic analyzes errors → structured repair instruction
  6. Generator receives repair instruction → produces new PDDL (iteration i+1)
  7. Repeat up to max_iterations

Stopping conditions:
  - Success: valid PDDL + executable plan found
  - Exhausted: max_iterations reached without success

The full iteration trace is saved for analysis (convergence speed, error type distribution).
"""

import os
import time
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

from .nl_to_pddl import NLToPDDLGenerator
from .pddl_validator import PDDLValidator
from .planner_runner import PDDLPlanner, PlanResult
from .critic import AdversarialCritic


# ── Result Structures ─────────────────────────────────────────────────────────

@dataclass
class IterationRecord:
    """One round of the repair loop."""
    iteration: int
    pddl: str
    validator_errors: List[str]
    validator_warnings: List[str]
    is_valid: bool
    plan_result: Optional[Dict]       # serializable version of PlanResult
    critic_output: Optional[Dict]     # what the critic said (None if not called)
    elapsed_ms: float


@dataclass
class RepairResult:
    """Complete result for one problem after the repair loop."""
    problem_id: str
    nl_description: str
    domain_name: str

    # Outcome
    success: bool
    final_pddl: str
    final_plan: List[str]

    # Metrics (key paper numbers)
    iterations_needed: int           # 0 = solved first try, -1 = never solved
    max_iterations: int
    baseline_valid: bool             # was iteration-0 PDDL valid?
    baseline_executable: bool        # was iteration-0 plan found?

    # Full trace for analysis
    iterations: List[IterationRecord] = field(default_factory=list)

    # Timing
    total_elapsed_ms: float = 0.0

    def to_dict(self) -> dict:
        return {
            "problem_id": self.problem_id,
            "nl_description": self.nl_description,
            "domain_name": self.domain_name,
            "success": self.success,
            "final_plan": self.final_plan,
            "iterations_needed": self.iterations_needed,
            "max_iterations": self.max_iterations,
            "baseline_valid": self.baseline_valid,
            "baseline_executable": self.baseline_executable,
            "total_elapsed_ms": round(self.total_elapsed_ms, 1),
            "repair_attempted": self.iterations_needed > 0,
            "iterations": [
                {
                    "iteration": r.iteration,
                    "is_valid": r.is_valid,
                    "validator_errors": r.validator_errors,
                    "plan_success": r.plan_result.get("success") if r.plan_result else False,
                    "critic_error_type": (
                        r.critic_output.get("error_type") if r.critic_output else None
                    ),
                    "critic_success": (
                        r.critic_output.get("critic_success") if r.critic_output else None
                    ),
                    "elapsed_ms": round(r.elapsed_ms, 1),
                }
                for r in self.iterations
            ],
        }


# ── Repair Loop ───────────────────────────────────────────────────────────────

class RepairLoop:
    """
    Orchestrates the adversarial critic + iterative fix/validate loop for one problem.

    Usage:
        loop = RepairLoop(domain_pddl, max_iterations=5)
        result = loop.run(problem_id, nl_description)
    """

    def __init__(
        self,
        domain_pddl: str,
        max_iterations: int = 5,
        gemini_api_key: str = None,
        gemini_model: str = None,
    ):
        self.domain_pddl = domain_pddl
        self.max_iterations = max_iterations
        self.generator = NLToPDDLGenerator(domain_pddl, api_key=gemini_api_key, model_name=gemini_model)
        self.validator = PDDLValidator(domain_pddl)
        self.planner = PDDLPlanner(domain_pddl)
        self.critic = AdversarialCritic(domain_pddl)
        self.domain_name = self.generator.domain_info["name"]

    def run(self, problem_id: str, nl_description: str) -> RepairResult:
        t_start = time.time()
        iteration_records: List[IterationRecord] = []

        result = RepairResult(
            problem_id=problem_id,
            nl_description=nl_description,
            domain_name=self.domain_name,
            success=False,
            final_pddl="",
            final_plan=[],
            iterations_needed=-1,
            max_iterations=self.max_iterations,
            baseline_valid=False,
            baseline_executable=False,
        )

        current_pddl = ""
        critic_output = None

        for i in range(self.max_iterations + 1):   # iteration 0 = initial, 1..N = repairs
            t_iter = time.time()

            # ── Generate ──────────────────────────────────────────────────────
            if i == 0:
                gen_result = self.generator.generate(nl_description, problem_id)
            else:
                gen_result = self.generator.repair(
                    nl_description, current_pddl, critic_output,
                    problem_id=problem_id, iteration=i
                )

            if not gen_result["success"]:
                # Generator API failure — record and stop
                rec = IterationRecord(
                    iteration=i, pddl="", validator_errors=[f"Generator failed: {gen_result['error']}"],
                    validator_warnings=[], is_valid=False, plan_result=None,
                    critic_output=None, elapsed_ms=(time.time() - t_iter) * 1000
                )
                iteration_records.append(rec)
                break

            current_pddl = gen_result["pddl"]

            # ── Validate ──────────────────────────────────────────────────────
            val_result = self.validator.validate(current_pddl)

            # ── Plan ──────────────────────────────────────────────────────────
            plan_result = None
            if val_result.is_valid:
                plan_result_obj = self.planner.solve(current_pddl)
                plan_result = {
                    "success": plan_result_obj.success,
                    "plan": plan_result_obj.plan,
                    "plan_length": plan_result_obj.plan_length,
                    "failure_reason": plan_result_obj.failure_reason,
                    "error": plan_result_obj.error,
                    "elapsed_ms": round(plan_result_obj.elapsed_ms, 1),
                }
            else:
                plan_result = {"success": False, "failure_reason": "Validation failed — planner not called."}

            iter_elapsed = (time.time() - t_iter) * 1000

            # Record baseline metrics from iteration 0
            if i == 0:
                result.baseline_valid = val_result.is_valid
                result.baseline_executable = plan_result.get("success", False)

            # ── Check success ─────────────────────────────────────────────────
            solved = val_result.is_valid and plan_result.get("success", False)

            if solved:
                result.success = True
                result.final_pddl = current_pddl
                result.final_plan = plan_result.get("plan", [])
                result.iterations_needed = i

                iteration_records.append(IterationRecord(
                    iteration=i, pddl=current_pddl,
                    validator_errors=val_result.errors,
                    validator_warnings=val_result.warnings,
                    is_valid=True, plan_result=plan_result,
                    critic_output=None,
                    elapsed_ms=iter_elapsed
                ))
                break

            # ── Critic analysis (only if not solved and not last iteration) ───
            # Small gap before critic call when using Gemini backend to avoid
            # back-to-back requests hitting the 15 RPM free-tier limit.
            critic_output = None
            if i < self.max_iterations:
                if os.environ.get("CRITIC_BACKEND", "gemini") == "gemini":
                    time.sleep(5)
                critic_output = self.critic.analyze(
                    nl_description=nl_description,
                    broken_pddl=current_pddl,
                    validator_errors=val_result.error_list_for_critic(),
                    planner_failure=plan_result.get("failure_reason"),
                )

            iteration_records.append(IterationRecord(
                iteration=i, pddl=current_pddl,
                validator_errors=val_result.errors,
                validator_warnings=val_result.warnings,
                is_valid=val_result.is_valid,
                plan_result=plan_result,
                critic_output=critic_output,
                elapsed_ms=iter_elapsed
            ))

        result.iterations = iteration_records
        result.total_elapsed_ms = (time.time() - t_start) * 1000
        return result
