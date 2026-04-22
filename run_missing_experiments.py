"""
run_missing_experiments.py
Runs all missing table cells + local LLM experiments in sequence.

Always run preflight_check.py first:
    python preflight_check.py && python run_missing_experiments.py

Experiments:
  A. Blocksworld  — weak gen + weak critic          (standard)
  B. Gripper      — weak gen + no retry             (standard)
  C. Gripper      — weak gen + blind retry          (standard)
  D. Gripper      — weak gen + weak critic          (standard)
  E. Gripper      — weak gen + strong critic        (standard)
  F. Logistics    — weak gen + weak critic          (standard)
  G. Logistics    — weak gen + strong critic        (ablation INJECT_TYPE_MISLEAD)
  H. Ferry        — local LLM gen + strong critic   (standard)   [if local LLM available]
  I. Gripper      — local LLM gen + strong critic   (standard)   [if local LLM available]
  J. Logistics    — local LLM gen + strong critic   (standard)   [if local LLM available]

Results saved to: results/missing_experiments_<timestamp>.json
"""

import os
import sys
import json
import time
import pathlib
import logging
from datetime import datetime
from typing import Optional

# ── Load .env ─────────────────────────────────────────────────────────────────
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

ROOT = pathlib.Path(__file__).parent
sys.path.insert(0, str(ROOT))

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)s  %(message)s",
    datefmt="%H:%M:%S",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            ROOT / "logs" / f"missing_experiments_{datetime.now().strftime('%Y-%m-%d_%H-%M')}.log"
        ),
    ],
)
log = logging.getLogger(__name__)

from src.repair_loop import RepairLoop, RepairResult
from src.key_manager import KeyManager

DOMAINS_DIR = ROOT / "domains"
RESULTS_DIR = ROOT / "results"
RESULTS_DIR.mkdir(exist_ok=True)

from benchmarks.blocksworld_problems import PROBLEMS as BW_PROBLEMS
from benchmarks.gripper_problems import PROBLEMS as GR_PROBLEMS
from benchmarks.logistics_problems import PROBLEMS as LOG_PROBLEMS
from benchmarks.ferry_problems import PROBLEMS as FERRY_PROBLEMS

DOMAIN_PDDS = {
    "blocksworld": (DOMAINS_DIR / "blocksworld.pddl").read_text(),
    "gripper":     (DOMAINS_DIR / "gripper.pddl").read_text(),
    "logistics":   (DOMAINS_DIR / "logistics.pddl").read_text(),
    "ferry":       (DOMAINS_DIR / "ferry.pddl").read_text(),
}

INTER_PROBLEM_DELAY = 5   # seconds between problems


# ── Experiment Definitions ────────────────────────────────────────────────────

def make_experiments(local_llm_available: bool) -> list:
    weak_gen   = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    weak_crit  = os.environ.get("GEMINI_MODEL", "gemini-2.5-flash-lite")
    strong_crit = os.environ.get("CRITIC_GEMINI_MODEL", "gemini-3-flash-preview")
    local_model = os.environ.get("LOCAL_LLM_MODEL", "")
    local_url   = os.environ.get("LOCAL_LLM_BASE_URL", "")
    local_key   = os.environ.get("LOCAL_LLM_API_KEY", "")

    experiments = [
        # ── Missing Gemini experiments ─────────────────────────────────────
        dict(
            id="A", label="Blocksworld — weak gen + weak critic (standard)",
            domain="blocksworld", problems=BW_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="gemini", critic_model=weak_crit,
            inject_mislead=False,
        ),
        dict(
            id="B", label="Gripper — weak gen + no retry (standard)",
            domain="gripper", problems=GR_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend=None, critic_model=None,
            inject_mislead=False,
        ),
        dict(
            id="C", label="Gripper — weak gen + blind retry (standard)",
            domain="gripper", problems=GR_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="blind", critic_model=None,
            inject_mislead=False,
        ),
        dict(
            id="D", label="Gripper — weak gen + weak critic (standard)",
            domain="gripper", problems=GR_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="gemini", critic_model=weak_crit,
            inject_mislead=False,
        ),
        dict(
            id="E", label="Gripper — weak gen + strong critic (standard)",
            domain="gripper", problems=GR_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="gemini", critic_model=strong_crit,
            inject_mislead=False,
        ),
        dict(
            id="F", label="Logistics — weak gen + weak critic (standard)",
            domain="logistics", problems=LOG_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="gemini", critic_model=weak_crit,
            inject_mislead=False,
        ),
        dict(
            id="G", label="Logistics — weak gen + strong critic (ablation)",
            domain="logistics", problems=LOG_PROBLEMS,
            gen_backend="gemini", gen_model=weak_gen,
            critic_backend="gemini", critic_model=strong_crit,
            inject_mislead=True,
        ),
    ]

    # ── Local LLM experiments (only if available) ──────────────────────────
    if local_llm_available and local_model and local_url:
        experiments += [
            dict(
                id="H", label="Ferry — local LLM gen + strong critic (standard)",
                domain="ferry", problems=FERRY_PROBLEMS,
                gen_backend="local", gen_model=local_model,
                gen_base_url=local_url, gen_api_key=local_key,
                critic_backend="gemini", critic_model=strong_crit,
                inject_mislead=False,
            ),
            dict(
                id="I", label="Gripper — local LLM gen + strong critic (standard)",
                domain="gripper", problems=GR_PROBLEMS,
                gen_backend="local", gen_model=local_model,
                gen_base_url=local_url, gen_api_key=local_key,
                critic_backend="gemini", critic_model=strong_crit,
                inject_mislead=False,
            ),
            dict(
                id="J", label="Logistics — local LLM gen + strong critic (standard)",
                domain="logistics", problems=LOG_PROBLEMS,
                gen_backend="local", gen_model=local_model,
                gen_base_url=local_url, gen_api_key=local_key,
                critic_backend="gemini", critic_model=strong_crit,
                inject_mislead=False,
            ),
        ]
    else:
        log.info("Local LLM not available — skipping experiments H/I/J")

    return experiments


# ── Runner ────────────────────────────────────────────────────────────────────

def run_experiment(exp: dict, km: KeyManager) -> dict:
    label = f"[{exp['id']}] {exp['label']}"
    log.info(f"{'='*60}")
    log.info(f"START {label}")
    log.info(f"{'='*60}")

    # Set env vars for this experiment
    os.environ["GEMINI_MODEL"] = exp["gen_model"] or ""
    os.environ["INJECT_TYPE_MISLEAD"] = "true" if exp.get("inject_mislead") else "false"
    if exp.get("critic_model"):
        os.environ["CRITIC_GEMINI_MODEL"] = exp["critic_model"]
    if exp.get("critic_backend"):
        os.environ["CRITIC_BACKEND"] = exp["critic_backend"]

    domain_pddl = DOMAIN_PDDS[exp["domain"]]
    problems = exp["problems"]
    results = []
    solved = 0

    for i, prob in enumerate(problems):
        log.info(f"  Problem {i+1}/{len(problems)}: {prob['id']}")

        try:
            # Build repair loop based on backend
            if exp["gen_backend"] == "local":
                loop = _make_local_loop(exp, domain_pddl, km)
            else:
                loop = _make_gemini_loop(exp, domain_pddl, km)

            if exp.get("critic_backend") is None:
                # No retry — just generate once
                result = loop.run_no_retry(prob["id"], prob["nl"])
            elif exp.get("critic_backend") == "blind":
                result = loop.run_blind_retry(prob["id"], prob["nl"])
            else:
                result = loop.run(prob["id"], prob["nl"])

            results.append(_serialize(result))
            if result.success:
                solved += 1
                log.info(f"    SOLVED in {result.iterations_needed} iter(s)")
            else:
                log.info(f"    FAILED — {result.failure_reason}")

        except Exception as e:
            log.error(f"    ERROR on {prob['id']}: {e}")
            results.append({"problem_id": prob["id"], "success": False,
                            "error": str(e), "iterations_needed": 0})

        if i < len(problems) - 1:
            time.sleep(INTER_PROBLEM_DELAY)

    pct = 100 * solved / len(problems) if problems else 0
    summary = {
        "experiment_id": exp["id"],
        "label": exp["label"],
        "domain": exp["domain"],
        "total": len(problems),
        "solved": solved,
        "pct": round(pct, 1),
        "results": results,
    }
    log.info(f"DONE [{exp['id']}]: {solved}/{len(problems)} ({pct:.1f}%)")
    return summary


def _make_gemini_loop(exp: dict, domain_pddl: str, km: KeyManager) -> "RepairLoop":
    from src.nl_to_pddl import NLToPDDLGenerator, get_key_manager
    # Inject key manager so rotation works
    import src.nl_to_pddl as nl_mod
    nl_mod._key_manager = km

    max_iters = int(os.environ.get("MAX_REPAIR_ITERATIONS", 5))
    critic_model = exp.get("critic_model")
    return RepairLoop(
        domain_pddl=domain_pddl,
        max_iterations=max_iters,
        critic_model=critic_model,
    )


def _make_local_loop(exp: dict, domain_pddl: str, km: KeyManager) -> "RepairLoop":
    """Local LLM generator + cloud critic."""
    from src.nl_to_pddl import NLToPDDLGenerator
    import src.nl_to_pddl as nl_mod
    nl_mod._key_manager = km

    max_iters = int(os.environ.get("MAX_REPAIR_ITERATIONS", 5))
    critic_model = exp.get("critic_model")
    return RepairLoop(
        domain_pddl=domain_pddl,
        max_iterations=max_iters,
        critic_model=critic_model,
        gen_base_url=exp.get("gen_base_url"),
        gen_api_key=exp.get("gen_api_key"),
        gen_model=exp.get("gen_model"),
    )


def _serialize(r) -> dict:
    if hasattr(r, "__dict__"):
        d = {}
        for k, v in r.__dict__.items():
            try:
                json.dumps(v)
                d[k] = v
            except Exception:
                d[k] = str(v)
        return d
    return r


def check_local_llm() -> bool:
    """Returns True if local LLM is reachable."""
    url = os.environ.get("LOCAL_LLM_BASE_URL", "")
    if not url:
        return False
    try:
        import urllib.request
        req = urllib.request.Request(
            f"{url.rstrip('/')}/v1/models",
            headers={"Authorization": f"Bearer {os.environ.get('LOCAL_LLM_API_KEY', '')}"},
        )
        with urllib.request.urlopen(req, timeout=10):
            return True
    except Exception:
        return False


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    log.info("Initialising key manager...")
    try:
        km = KeyManager()
        log.info(f"Key manager ready: {km.status()}")
    except RuntimeError as e:
        log.error(str(e))
        sys.exit(1)

    log.info("Checking local LLM availability...")
    local_ok = check_local_llm()
    log.info(f"Local LLM: {'available' if local_ok else 'not available'}")

    experiments = make_experiments(local_ok)
    log.info(f"\nWill run {len(experiments)} experiment(s):\n")
    for exp in experiments:
        log.info(f"  [{exp['id']}] {exp['label']}")

    timestamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    output_file = RESULTS_DIR / f"missing_experiments_{timestamp}.json"

    all_summaries = []
    for exp in experiments:
        summary = run_experiment(exp, km)
        all_summaries.append(summary)
        # Save after every experiment so a crash doesn't lose everything
        output_file.write_text(json.dumps(all_summaries, indent=2))
        log.info(f"Saved progress to {output_file}")
        if not km.has_keys:
            log.error("All API keys exhausted — stopping early.")
            break

    log.info("\n" + "=" * 60)
    log.info("FINAL RESULTS SUMMARY")
    log.info("=" * 60)
    for s in all_summaries:
        log.info(f"  [{s['experiment_id']}] {s['label']}: "
                 f"{s['solved']}/{s['total']} ({s['pct']}%)")
    log.info(f"\nFull results saved to: {output_file}")


if __name__ == "__main__":
    main()
