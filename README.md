# Phase 1: Neuro-Symbolic Planning — Baseline Pipeline

**Course:** Introduction to Artificial Intelligence  
**Student:** Dilip Kumar Thirukonda Chandrasekaran (B01173289)  
**Project:** Neuro-Symbolic Planning via Adversarial Repair and Compilation

---

## Phase 1 Goal

Establish a working end-to-end baseline:

```
Natural Language  →  [Generator]  →  PDDL  →  [Validator]  →  [Planner]  →  Plan
```

Record the **executability rate** without any feedback loops (zero-shot baseline). This is the baseline that Phase 2's Adversarial Critic will improve upon.

---

## Architecture

```
phase1/
├── domains/
│   └── blocksworld.pddl          # Standard 4-operator Blocksworld domain (IPC)
├── problems/
│   └── blocksworld_benchmark.pddl # 6 benchmark problems with ground-truth PDDL
├── src/
│   ├── nl_to_pddl.py             # NL → PDDL generator (model API)
│   ├── pddl_validator.py         # Structural + semantic PDDL validator
│   ├── planner_runner.py         # Pure-Python BFS classical planner
│   └── pipeline.py               # End-to-end orchestrator + reporting
├── tests/
│   └── test_phase1.py            # Unit tests (19 tests, 0 failures)
├── results/
│   └── phase1_results.json       # Saved benchmark results
└── README.md
```

---

## Components

### 1. `nl_to_pddl.py` — NL→PDDL Generator

Calls the configured model API (`GEMINI_MODEL`) to translate natural language planning problem descriptions into PDDL problem files.

**Key design choices:**
- System prompt enforces strict PDDL-only output (no markdown, no explanations)
- Prompt includes the full domain PDDL as context
- Logs all generation attempts for Phase 2 failure analysis

**Usage:**
```python
from src.nl_to_pddl import NLToPDDLGenerator

gen = NLToPDDLGenerator(domain_pddl)
result = gen.generate("Stack block A on top of block B.")
print(result["pddl"])
```

### 2. `pddl_validator.py` — Structural Validator

Validates generated PDDL for:
- Balanced parentheses
- Required sections (`(:objects ...)`, `(:init ...)`, `(:goal ...)`)
- Valid predicates (only `on`, `ontable`, `clear`, `handempty`, `holding`)
- Correct arity per predicate
- Undeclared objects
- Missing hand state in `:init`

This provides structured **error messages** that the Adversarial Critic (Phase 2) will parse to fix the PDDL.

**Usage:**
```python
from src.pddl_validator import PDDLValidator

v = PDDLValidator()
result = v.validate(pddl_string)
print(result.summary())   # ✅ VALID or ❌ INVALID with error list
```

### 3. `planner_runner.py` — Classical BFS Planner

A pure-Python **Breadth-First Search** planner for the Blocksworld domain.

**Why BFS?**
- Guarantees **optimal (shortest) plans**
- No external dependencies (no Fast Downward installation required)
- Identical interface — swappable with Fast Downward in Phase 3

**State representation:** Frozensets of ground fact tuples  
**Actions:** Exact 4-operator Blocksworld (`pickup`, `putdown`, `stack`, `unstack`)  
**Search limit:** 50,000 nodes (configurable)

**Usage:**
```python
from src.planner_runner import BFSPlanner

planner = BFSPlanner()
result = planner.solve(pddl_string)
print(result.summary())
```

The `PlanResult.failure_reason` field is designed to feed into the Phase 2 Adversarial Critic.

### 4. `pipeline.py` — End-to-End Orchestrator

Runs all 3 stages for each benchmark problem and produces a JSON report.

**Two modes:**
- `--mode oracle` — uses ground-truth PDDL (tests planner in isolation)
- `--mode api` — calls the configured model API to generate PDDL (full E2E test, requires API key)

**Usage:**
```bash
# Oracle mode (no API key needed):
python src/pipeline.py --mode oracle

# API mode (generates PDDL via model API):
export GEMINI_API_KEY="your-key-here"
python src/pipeline.py --mode api

# Save results to custom path:
python src/pipeline.py --mode api --output my_results.json
```

---

## Benchmark Problems

| ID | Description | Complexity |
|----|-------------|-----------|
| `bw_p1_2blocks` | Stack A on B (2 blocks on table) | Easy |
| `bw_p2_3tower` | Build 3-block tower (all on table) | Easy |
| `bw_p3_reverse3` | Reverse a 3-block stack | Medium |
| `bw_p4_4tower` | Build 4-block tower | Medium |
| `bw_p5_swap` | Swap 2 blocks | Medium |
| `bw_p6_5tower` | Build 5-block tower | Hard |

---

## Phase 1 Baseline Results (Oracle Mode)

Oracle mode confirms the **planner is correct** on all 6 problems.

| Problem | Plan Length | Solve Time | Status |
|---------|-------------|------------|--------|
| bw_p1_2blocks | 2 steps | <1ms | ✅ |
| bw_p2_3tower | 4 steps | <1ms | ✅ |
| bw_p3_reverse3 | 6 steps | <1ms | ✅ |
| bw_p4_4tower | 6 steps | 4ms | ✅ |
| bw_p5_swap | 4 steps | <1ms | ✅ |
| bw_p6_5tower | 8 steps | 31ms | ✅ |

**Executability Rate (oracle): 6/6 = 100%**

When `--mode api` is used with the configured model API, the baseline executability rate
represents the model's **zero-shot PDDL generation accuracy** — this is the number
Phase 2 will improve upon with the Adversarial Critic feedback loop.

---

## Evaluation Metrics (as specified in proposal)

1. **Executability Rate** = (problems with valid executable plans) / (total problems)
   - Oracle baseline: 100% (planner verified correct)
   - API baseline: measured from `results/phase1_results.json`

2. **Repair Efficiency** — not applicable in Phase 1 (no repair loop)
   - Will be measured in Phase 2 as: avg iterations to fix a failing plan

---

## Running the Tests

```bash
python tests/test_phase1.py
```

Expected output: **19 tests, 0 failures**

Tests cover:
- `TestPDDLValidator` — 8 tests (valid/invalid PDDL cases)
- `TestBFSPlanner` — 9 tests (all benchmark problems + edge cases)
- `TestPlanVerification` — 2 tests (step-by-step plan execution verification)

---

## Phase 2 Preview

Phase 2 adds the **Adversarial Critic** component:

```
NL  →  [Generator]  →  PDDL
                          │
                     [Validator + Planner]
                          │
                    FAILED? → [Adversarial Critic LLM]
                                   │ parses error messages
                                   ▼
                          refined PDDL  ←──── feedback loop
```

The `failure_reason` and `validation_errors` fields already produced by Phase 1 components
are the structured inputs the Critic will consume.

---

## Dependencies

- Python 3.10+
- Standard library only (`re`, `collections`, `json`, `urllib`, `dataclasses`)
- Model API key (`GEMINI_API_KEY`, only for `--mode api`)

No external packages required.
