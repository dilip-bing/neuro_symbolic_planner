"""
pipeline.py
===========
Phase 1 - End-to-End Pipeline

Orchestrates the full Phase 1 workflow:

  NL Description
       │
       ▼
    [NLToPDDLGenerator]   ← calls configured model API
       │
       ▼ generated PDDL
  [PDDLValidator]        ← structural + semantic checks
       │
       ▼ validation result
  [BFSPlanner]           ← classical BFS planner
       │
       ▼
  PipelineResult         ← full record for reporting

Results are saved to results/phase1_results.json for analysis.
"""

import json
import os
import sys
import pathlib
import datetime

# Add src to path if running directly
sys.path.insert(0, str(pathlib.Path(__file__).parent))

from nl_to_pddl   import NLToPDDLGenerator, BENCHMARK_PROBLEMS
from pddl_validator import PDDLValidator
from planner_runner import BFSPlanner


# ── Pipeline Result ───────────────────────────────────────────────────────────

class PipelineResult:
    def __init__(self, problem_id: str, nl: str):
        self.problem_id         = problem_id
        self.nl                 = nl
        self.generation_success = False
        self.generation_error   = None
        self.generated_pddl     = ""
        self.validation_valid   = False
        self.validation_errors  = []
        self.validation_warnings = []
        self.plan_success       = False
        self.plan_length        = 0
        self.plan               = []
        self.nodes_explored     = 0
        self.solve_time_s       = 0.0
        self.failure_reason     = None
        self.overall_success    = False

    def to_dict(self) -> dict:
        return {
            "problem_id":           self.problem_id,
            "nl":                   self.nl,
            "generation_success":   self.generation_success,
            "generation_error":     self.generation_error,
            "generated_pddl":       self.generated_pddl,
            "validation_valid":     self.validation_valid,
            "validation_errors":    self.validation_errors,
            "validation_warnings":  self.validation_warnings,
            "plan_success":         self.plan_success,
            "plan_length":          self.plan_length,
            "plan":                 self.plan,
            "nodes_explored":       self.nodes_explored,
            "solve_time_s":         round(self.solve_time_s, 4),
            "failure_reason":       self.failure_reason,
            "overall_success":      self.overall_success,
        }

    def summary(self) -> str:
        status = "✅ SUCCESS" if self.overall_success else "❌ FAIL"
        lines = [
            f"\n{'='*60}",
            f"  Problem : {self.problem_id}",
            f"  Status  : {status}",
            f"  NL      : {self.nl[:80]}{'...' if len(self.nl)>80 else ''}",
            f"{'─'*60}",
            f"  [1] Generation  : {'OK' if self.generation_success else 'FAILED'}",
        ]
        if not self.generation_success:
            lines.append(f"      Error: {self.generation_error}")

        lines.append(
            f"  [2] Validation  : {'VALID' if self.validation_valid else 'INVALID'}"
        )
        for e in self.validation_errors:
            lines.append(f"      ✗ {e}")
        for w in self.validation_warnings:
            lines.append(f"      ~ {w}")

        lines.append(
            f"  [3] Planning    : {'SOLVED' if self.plan_success else 'FAILED'}"
        )
        if self.plan_success:
            lines.append(f"      Plan length : {self.plan_length} steps")
            lines.append(f"      Time        : {self.solve_time_s:.3f}s")
            for i, step in enumerate(self.plan, 1):
                lines.append(f"      {i:2d}. {step}")
        else:
            lines.append(f"      Reason: {self.failure_reason}")

        lines.append(f"{'='*60}")
        return "\n".join(lines)


# ── Phase 1 Pipeline ──────────────────────────────────────────────────────────

class Phase1Pipeline:
    """
    Full Phase 1 end-to-end pipeline.

    Modes:
            - 'api'   : calls the model API to generate PDDL (requires API key)
      - 'oracle': uses ground-truth PDDL from the benchmark file (for planner testing only)
    """

    def __init__(self, domain_pddl: str, api_key: str = None, mode: str = "api"):
        self.domain_pddl = domain_pddl
        self.api_key     = api_key
        self.mode        = mode
        self.generator   = NLToPDDLGenerator(domain_pddl, api_key) if mode == "api" else None
        self.validator   = PDDLValidator()
        self.planner     = BFSPlanner()
        self.results     = []

    def run_single(self, problem: dict, oracle_pddl: str = None) -> PipelineResult:
        """Run the pipeline on a single problem dict {id, nl}."""
        pr = PipelineResult(problem["id"], problem["nl"])

        # ── Step 1: Generate PDDL ─────────────────────────────────────────
        print(f"\n[{problem['id']}] Step 1: Generating PDDL...", flush=True)

        if self.mode == "oracle" and oracle_pddl:
            pr.generation_success = True
            pr.generated_pddl     = oracle_pddl
            print("  → Using oracle (ground-truth) PDDL.")
        else:
            gen_result = self.generator.generate(problem["nl"], problem["id"])
            pr.generation_success = gen_result["success"]
            pr.generation_error   = gen_result.get("error")
            pr.generated_pddl     = gen_result.get("pddl", "")

            if pr.generation_success:
                print("  → Generation OK.")
            else:
                print(f"  → Generation FAILED: {pr.generation_error}")
                self.results.append(pr)
                return pr

        # ── Step 2: Validate ──────────────────────────────────────────────
        print(f"[{problem['id']}] Step 2: Validating PDDL...", flush=True)
        val = self.validator.validate(pr.generated_pddl)
        pr.validation_valid    = val.is_valid
        pr.validation_errors   = val.errors
        pr.validation_warnings = val.warnings

        if val.is_valid:
            print("  → Validation PASSED.")
        else:
            print(f"  → Validation FAILED: {len(val.errors)} error(s).")
            for e in val.errors:
                print(f"     ✗ {e}")
            # Even if invalid, attempt to plan (planner may still succeed)

        # ── Step 3: Plan ──────────────────────────────────────────────────
        print(f"[{problem['id']}] Step 3: Planning...", flush=True)
        plan_result = self.planner.solve(pr.generated_pddl, problem["id"])
        pr.plan_success    = plan_result.success
        pr.plan_length     = plan_result.plan_length
        pr.plan            = plan_result.plan
        pr.nodes_explored  = plan_result.nodes_explored
        pr.solve_time_s    = plan_result.solve_time_s
        pr.failure_reason  = plan_result.failure_reason or plan_result.error

        if pr.plan_success:
            print(f"  → SOLVED in {pr.plan_length} steps ({pr.solve_time_s:.3f}s).")
        else:
            print(f"  → Planning FAILED: {pr.failure_reason}")

        pr.overall_success = pr.generation_success and pr.plan_success
        self.results.append(pr)
        return pr

    def run_benchmark(self, oracle_pddls: dict = None) -> dict:
        """
        Run the full benchmark suite (all BENCHMARK_PROBLEMS).
        oracle_pddls: dict {problem_id: pddl_str} for oracle mode.
        Returns a summary statistics dict.
        """
        print(f"\n{'='*60}")
        print(f"  PHASE 1 BENCHMARK RUN — {len(BENCHMARK_PROBLEMS)} problems")
        print(f"  Mode    : {self.mode.upper()}")
        print(f"  Started : {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}")

        for prob in BENCHMARK_PROBLEMS:
            oracle = oracle_pddls.get(prob["id"]) if oracle_pddls else None
            self.run_single(prob, oracle_pddl=oracle)

        return self._compute_stats()

    def _compute_stats(self) -> dict:
        total      = len(self.results)
        gen_ok     = sum(1 for r in self.results if r.generation_success)
        val_ok     = sum(1 for r in self.results if r.validation_valid)
        plan_ok    = sum(1 for r in self.results if r.plan_success)
        overall_ok = sum(1 for r in self.results if r.overall_success)

        avg_plan_len  = (
            sum(r.plan_length for r in self.results if r.plan_success) / plan_ok
            if plan_ok else 0
        )
        avg_solve_t   = (
            sum(r.solve_time_s for r in self.results if r.plan_success) / plan_ok
            if plan_ok else 0
        )

        stats = {
            "timestamp":            datetime.datetime.now().isoformat(),
            "mode":                 self.mode,
            "total_problems":       total,
            "generation_success":   gen_ok,
            "validation_success":   val_ok,
            "planning_success":     plan_ok,
            "overall_success":      overall_ok,
            "executability_rate":   round(plan_ok / total, 4) if total else 0,
            "generation_rate":      round(gen_ok / total, 4) if total else 0,
            "avg_plan_length":      round(avg_plan_len, 2),
            "avg_solve_time_s":     round(avg_solve_t, 4),
            "per_problem":          [r.to_dict() for r in self.results],
        }
        return stats

    def print_final_report(self, stats: dict):
        total = stats["total_problems"]
        print(f"\n{'='*60}")
        print("  PHASE 1 — FINAL RESULTS SUMMARY")
        print(f"{'='*60}")
        print(f"  Total problems       : {total}")
        print(f"  Generation success   : {stats['generation_success']}/{total}  "
              f"({stats['generation_rate']*100:.1f}%)")
        print(f"  Validation success   : {stats['validation_success']}/{total}")
        print(f"  Planning success     : {stats['planning_success']}/{total}  "
              f"({stats['executability_rate']*100:.1f}%)")
        print(f"  Overall (E2E)        : {stats['overall_success']}/{total}")
        print(f"  Avg plan length      : {stats['avg_plan_length']} steps")
        print(f"  Avg solve time       : {stats['avg_solve_time_s']*1000:.1f} ms")
        print(f"{'='*60}")
        print()

        # Per-problem detail from live results list
        for pr in self.results:
            print(pr.summary())


# ── Entry Point ───────────────────────────────────────────────────────────────

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description="Phase 1: NL→PDDL→Validate→Plan pipeline"
    )
    parser.add_argument(
        "--mode",
        choices=["api", "oracle"],
        default="oracle",
        help=(
            "'api'    = call model API to generate PDDL (requires GEMINI_API_KEY)\n"
            "'oracle' = use ground-truth PDDL (tests planner only)"
        ),
    )
    parser.add_argument(
        "--api-key",
        default=None,
        help="Model API key (overrides GEMINI_API_KEY env var)",
    )
    parser.add_argument(
        "--output",
        default=None,
        help="Path to save JSON results (default: results/phase1_results.json)",
    )
    args = parser.parse_args()

    # ── Load domain ───────────────────────────────────────────────────────
    script_dir = pathlib.Path(__file__).resolve().parent
    domain_candidates = [
        script_dir / "domains" / "blocksworld.pddl",  # phase1/ layout
        script_dir / "blocksworld.pddl",               # flat repo layout
    ]
    domain_path = next((p for p in domain_candidates if p.exists()), None)
    if domain_path is None:
        raise FileNotFoundError(
            "Could not find blocksworld domain file. Checked: "
            + ", ".join(str(p) for p in domain_candidates)
        )
    domain_pddl = domain_path.read_text()

    # ── Oracle PDDL (ground-truth problems) ──────────────────────────────
    # These are the correct PDDL strings for each benchmark problem.
    # Used when mode='oracle' to isolate planner correctness.
    ORACLE_PDDLS = {
        "bw_p1_2blocks": """
(define (problem bw-p1-2blocks)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)""",
        "bw_p2_3tower": """
(define (problem bw-p2-3tower)
  (:domain blocksworld)
  (:objects a b c)
  (:init (ontable a) (ontable b) (ontable c) (clear a) (clear b) (clear c) (handempty))
  (:goal (and (on c b) (on b a) (ontable a)))
)""",
        "bw_p3_reverse3": """
(define (problem bw-p3-reverse3)
  (:domain blocksworld)
  (:objects a b c)
  (:init (on a b) (on b c) (ontable c) (clear a) (handempty))
  (:goal (and (on c b) (on b a) (ontable a)))
)""",
        "bw_p4_4tower": """
(define (problem bw-p4-4tower)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (ontable a) (ontable b) (ontable c) (ontable d)
         (clear a) (clear b) (clear c) (clear d) (handempty))
  (:goal (and (on d c) (on c b) (on b a) (ontable a)))
)""",
        "bw_p5_swap": """
(define (problem bw-p5-swap)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a b) (ontable b) (clear a) (handempty))
  (:goal (and (on b a) (ontable a)))
)""",
        "bw_p6_5tower": """
(define (problem bw-p6-5tower)
  (:domain blocksworld)
  (:objects a b c d e)
  (:init (ontable a) (ontable b) (ontable c) (ontable d) (ontable e)
         (clear a) (clear b) (clear c) (clear d) (clear e) (handempty))
  (:goal (and (on e d) (on d c) (on c b) (on b a) (ontable a)))
)""",
    }

    # ── Run pipeline ─────────────────────────────────────────────────────
    pipeline = Phase1Pipeline(
        domain_pddl=domain_pddl,
        api_key=args.api_key,
        mode=args.mode,
    )

    oracle = ORACLE_PDDLS if args.mode == "oracle" else None
    stats  = pipeline.run_benchmark(oracle_pddls=oracle)

    pipeline.print_final_report(stats)

    # ── Save results ──────────────────────────────────────────────────────
    out_path = pathlib.Path(args.output) if args.output else (
        script_dir / "results" / "phase1_results.json"
    )
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(stats, indent=2))
    print(f"\n📁 Results saved to: {out_path}")


if __name__ == "__main__":
    main()
