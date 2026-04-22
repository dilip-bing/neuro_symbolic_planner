#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# Full ablation suite — run ALL configs sequentially to avoid rate-limit fights.
#
# Generator : gemini-2.5-flash-lite  (weak, systematic errors)
# Critic    : gemini-3-flash-preview (strong, separate model)
#
# Runs:
#   Config A-critic  : INJECT_TYPE_MISLEAD=true  → Gripper + Logistics  (structured critic)
#   Config A-blind   : INJECT_TYPE_MISLEAD=true  → Gripper + Logistics  (blind retry)
#   Config B-critic  : Ferry, predicates given   → Ferry                (structured critic)
#   Config B-blind   : Ferry, predicates given   → Ferry                (blind retry)
#
# Why this matters:
#   • Weak generator hits ~40-60% baseline failures on these configs
#   • Structured critic (strong model) fixes them in 1 shot
#   • Blind retry (weak model, no guidance) keeps repeating the same mistake
#   • → Clear critic > blind retry differentiation for the paper
# ─────────────────────────────────────────────────────────────────────────────
set -e
cd "$(dirname "$0")"

# Load .env into environment
while IFS= read -r line; do
  [[ -z "$line" || "$line" == \#* ]] && continue
  if [[ "$line" == *"="* ]]; then
    key="${line%%=*}"; val="${line#*=}"
    export "${key// /}=${val}"
  fi
done < .env

echo ""
echo "Generator : $GEMINI_MODEL"
echo "Critic    : $CRITIC_GEMINI_MODEL"
echo ""

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG A — INJECT_TYPE_MISLEAD=true | WITHHOLD_PREDICATES=false
# Domains : Gripper + Logistics
# Effect  : Model omits type predicates in :init on iteration 0
#           Structured critic identifies PREDICATE error → fixes in 1 shot
#           Blind retry re-sends with same mislead hint → repeats mistake
# ═══════════════════════════════════════════════════════════════════════════
export INJECT_TYPE_MISLEAD=true
export WITHHOLD_PREDICATES=false

echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CONFIG A  |  STRUCTURED CRITIC  |  Gripper + Logistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PYTHONUNBUFFERED=1 python3 -u pipeline_phase2.py      --domain gripper   --max-iterations 5
PYTHONUNBUFFERED=1 python3 -u pipeline_phase2.py      --domain logistics --max-iterations 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CONFIG A  |  BLIND RETRY        |  Gripper + Logistics"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PYTHONUNBUFFERED=1 python3 -u pipeline_blind_retry.py --domain gripper   --max-iterations 5
PYTHONUNBUFFERED=1 python3 -u pipeline_blind_retry.py --domain logistics --max-iterations 5

# ═══════════════════════════════════════════════════════════════════════════
# CONFIG B — INJECT_TYPE_MISLEAD=false | WITHHOLD_PREDICATES=false
# Domain  : Ferry
# Effect  : Unfamiliar predicates (empty-ferry, 1-arg on) cause ~50% natural fails
#           Structured critic classifies error precisely → fixes recoverable ones
#           Blind retry guesses randomly → lower repair rate
# ═══════════════════════════════════════════════════════════════════════════
export INJECT_TYPE_MISLEAD=false
export WITHHOLD_PREDICATES=false

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CONFIG B  |  STRUCTURED CRITIC  |  Ferry (predicates given)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PYTHONUNBUFFERED=1 python3 -u pipeline_phase2.py      --domain ferry     --max-iterations 5

echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "CONFIG B  |  BLIND RETRY        |  Ferry (predicates given)"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
PYTHONUNBUFFERED=1 python3 -u pipeline_blind_retry.py --domain ferry     --max-iterations 5

echo ""
echo "══════════════════════════════════════════════════════════════════════"
echo "ALL ABLATION RUNS COMPLETE — check results/archive/ for JSON files"
echo "══════════════════════════════════════════════════════════════════════"
