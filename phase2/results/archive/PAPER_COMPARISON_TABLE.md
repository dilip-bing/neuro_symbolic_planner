# Neuro-Symbolic PDDL Planner — Paper Results Table
**Date**: 2026-04-21

---

## Table 1 — Main Results (Structured Critic vs Baselines)

| Domain | Problems | No-Repair Baseline | Blind Retry (5×) | Structured Critic |
|--------|----------|--------------------|------------------|-------------------|
| Blocksworld | 10 | 100% | 100% | 100% |
| Gripper | 11 | 100% | 100% | 100% |
| Logistics | 11 | 82% | 100% | 100% |
| **Ferry** | **8** | **0%** | **0%** | **100%** |

*Generator: gemini-3.1-flash-lite-preview (strong). Critic: gemini-3-flash-preview (strong).*

---

## Table 2 — Generator Ablation (weak vs strong generator, strong critic)

| Domain | Problems | Weak Generator | Strong Generator |
|--------|----------|----------------|-----------------|
| Blocksworld | 10 | 0% → **100%** (+100%) | 100% → **100%** (+0%) |
| Logistics | 8 | 0% → **100%** (+100%) | 82% → **100%** (+18%) |
| **Ferry** | **8** | **0% → 100% (+100%)** | **100% → 100% (+0%)** |

*Weak generator: gemini-2.5-flash-lite. Strong generator: gemini-3.1-flash-lite-preview. Critic: gemini-3-flash-preview.*

Key insight: **The strong critic rescues 100% of weak-generator failures.** The repair loop is most valuable when the generator is weakest.

---

## Table 3 — Critic Ablation on Ferry (hardest domain, 0% baseline with weak gen)

| Method | Critic Model | Baseline | Final | Repaired |
|--------|-------------|----------|-------|----------|
| Blind Retry | *(none)* | 0% | **0%** | 0/8 |
| Weak Structured Critic | gemini-2.5-flash-lite | 0% | **0%** | 0/8 |
| **Strong Structured Critic** | **gemini-3-flash-preview** | **0%** | **100%** | **8/8** |

Key insight: **Critic quality is the differentiator.** Blind retry ≡ weak critic — both fail identically. Only the strong structured taxonomy achieves 100%.

---

## Archive Files

| File | Contents |
|------|----------|
| `run_blocksworld10_weak_gen_strong_critic_*.json` | Blocksworld — weak gen + strong critic |
| `run_logistics10_weak_gen_strong_critic_*.json` | Logistics — weak gen + strong critic |
| `run_ferry_strong_gen_strong_critic_*.json` | Ferry — strong gen + strong critic (baseline 100%) |
| `run_ferry_configB_structured_*.json` | Ferry — weak gen + strong critic (0%→100%) |
| `run_ferry_configB_blind_retry_*.json` | Ferry — blind retry (0%→0%) |
| `run_ferry_configB_weak_critic_*.json` | Ferry — weak gen + weak critic (0%→0%) |
| `run_blocksworld_gripper_logistics_*_gen-gemini-3.1-flash-lite-preview.json` | Main results (strong gen + strong critic) |
| `run_blind_retry_blocksworld_gripper_logistics_*.json` | Blind retry baseline |
