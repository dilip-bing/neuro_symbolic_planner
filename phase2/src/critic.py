"""
critic.py  —  Phase 2
Adversarial Critic with switchable backend: Gemini (cloud) or Qwen3.5 (local).

Set CRITIC_BACKEND=gemini (default) or CRITIC_BACKEND=local in your .env.

This separation is the paper's contribution:
  - Generator (Gemini): NL understanding + PDDL generation
  - Critic (Gemini or Qwen3.5): structured error analysis → targeted repair instruction

Phase 3 ablation: run once with CRITIC_BACKEND=gemini, once with CRITIC_BACKEND=local,
compare repair success rates → shows whether critic quality matters independently.

Error taxonomy (5 types — fixed classification is the core research contribution):
  SYNTAX         — malformed structure, missing sections, bracket errors
  PREDICATE      — wrong predicate name (e.g. 'stacked' → 'on')
  OBJECT_MISSING — object referenced but not declared in :objects
  GOAL_SEMANTIC  — goal constraints dropped, simplified, or semantically wrong
  UNSOLVABLE     — valid PDDL but init state makes goal unreachable
"""

import os
import time
import json
import re
import warnings
import logging
import httpx
from typing import List, Optional

warnings.filterwarnings("ignore", category=UserWarning, module="google_genai")
logging.getLogger("google_genai").setLevel(logging.ERROR)

from google import genai
from google.genai import types as genai_types


ERROR_TYPES = ["SYNTAX", "PREDICATE", "OBJECT_MISSING", "GOAL_SEMANTIC", "UNSOLVABLE"]

CRITIC_PROMPT = """You are an expert PDDL error analyst. Diagnose why the generated PDDL is incorrect and produce a precise repair instruction for the generator.

=== DOMAIN (reference) ===
{domain_pddl}

=== ORIGINAL NATURAL LANGUAGE DESCRIPTION ===
{nl_description}

=== GENERATED PDDL (contains errors) ===
{broken_pddl}

=== VALIDATOR ERRORS ===
{validator_errors}

=== PLANNER FAILURE (if applicable) ===
{planner_failure}

=== YOUR TASK ===
1. Classify the PRIMARY error type as exactly one of: SYNTAX | PREDICATE | OBJECT_MISSING | GOAL_SEMANTIC | UNSOLVABLE
2. Identify the exact location and nature of the error (be specific — quote the bad text)
3. Write a fix instruction precise enough for a code generator to apply without guessing

Respond with ONLY a valid JSON object, no other text:
{{
  "error_type": "PREDICATE",
  "problem": "Predicate 'stacked' used in :init is not defined. Valid predicates: on, ontable, clear, handempty, holding",
  "fix_instruction": "Replace every occurrence of 'stacked' with 'on' in the :init and :goal sections",
  "priority_section": "init"
}}

error_type: one of SYNTAX | PREDICATE | OBJECT_MISSING | GOAL_SEMANTIC | UNSOLVABLE
problem: exact description of what is wrong (quote the bad text)
fix_instruction: concrete actionable instruction for the generator
priority_section: which PDDL section to focus on (objects | init | goal | structure)"""


class AdversarialCritic:
    """
    Produces structured repair instructions for broken PDDL.

    Backend is selected via CRITIC_BACKEND env var:
      gemini  — uses Gemini (same API as generator, higher quality)
      local   — uses Qwen3.5 9B via local RAG server (Phase 3 ablation)

    Usage:
        critic = AdversarialCritic(domain_pddl)
        repair = critic.analyze(nl, broken_pddl, validator_errors, planner_failure)
    """

    def __init__(self, domain_pddl: str):
        self.domain_pddl = domain_pddl
        self.backend = os.environ.get("CRITIC_BACKEND", "gemini").lower()

        # Gemini backend config
        self.gemini_api_key = os.environ.get("GEMINI_API_KEY", "")
        self.gemini_model = os.environ.get("CRITIC_GEMINI_MODEL",
                                           os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview"))

        # Local backend config
        self.local_base_url = os.environ.get("LOCAL_LLM_BASE_URL", "")
        self.local_api_key = os.environ.get("LOCAL_LLM_API_KEY", "")
        self.local_model = os.environ.get("LOCAL_LLM_MODEL", "qwen3.5:9b-q4_K_M")
        self.local_timeout_s = int(os.environ.get("CRITIC_TIMEOUT_S", "120"))

    def analyze(
        self,
        nl_description: str,
        broken_pddl: str,
        validator_errors: List[str],
        planner_failure: Optional[str] = None,
    ) -> dict:
        prompt = CRITIC_PROMPT.format(
            domain_pddl=self.domain_pddl,
            nl_description=nl_description,
            broken_pddl=broken_pddl,
            validator_errors="\n".join(validator_errors) if validator_errors else "None",
            planner_failure=planner_failure or "None",
        )

        try:
            if self.backend == "gemini":
                raw = self._query_gemini(prompt)
            else:
                raw = self._query_local(prompt)
            parsed = self._parse_json_response(raw)
            parsed["raw_response"] = raw
            parsed["critic_success"] = True
            parsed["critic_backend"] = self.backend
            return parsed
        except Exception as e:
            return self._heuristic_fallback(validator_errors, planner_failure, str(e))

    # ── Gemini Backend ────────────────────────────────────────────────────────

    def _query_gemini(self, prompt: str) -> str:
        if not self.gemini_api_key:
            raise ValueError("GEMINI_API_KEY not set for Gemini critic backend.")

        client = genai.Client(api_key=self.gemini_api_key)
        last_error = ""
        for attempt in range(4):
            try:
                response = client.models.generate_content(
                    model=self.gemini_model,
                    contents=prompt,
                    config=genai_types.GenerateContentConfig(
                        temperature=0.1,   # low temp for deterministic structured output
                    ),
                )
                return response.text.strip()
            except Exception as e:
                last_error = str(e)
                if any(x in last_error for x in ["429", "503", "unavailable", "quota"]) and attempt < 3:
                    wait = 65 if "429" in last_error else 10 * (2 ** attempt)
                    time.sleep(wait)
                    continue
                raise
        raise RuntimeError(f"Gemini critic exhausted retries: {last_error}")

    # ── Local Backend (Qwen3.5 via RAG API) ──────────────────────────────────

    def _query_local(self, prompt: str) -> str:
        if not self.local_base_url:
            raise ValueError("LOCAL_LLM_BASE_URL not set for local critic backend.")

        headers = {"X-API-Key": self.local_api_key, "Content-Type": "application/json"}
        with httpx.Client(timeout=30) as client:
            resp = client.post(f"{self.local_base_url}/query", headers=headers, json={
                "question": prompt,
                "thinking": False,
                "model": self.local_model,
            })
            resp.raise_for_status()
            task_id = resp.json()["task_id"]

            deadline = time.time() + self.local_timeout_s
            while time.time() < deadline:
                poll = client.get(f"{self.local_base_url}/query/{task_id}", headers=headers)
                poll.raise_for_status()
                data = poll.json()
                if data["status"] == "completed":
                    return data["result"]["answer"]
                elif data["status"] == "error":
                    raise RuntimeError(f"Local critic error: {data.get('error')}")
                time.sleep(2)
        raise TimeoutError(f"Local critic timed out after {self.local_timeout_s}s")

    # ── Response Parsing ──────────────────────────────────────────────────────

    def _parse_json_response(self, raw: str) -> dict:
        # Strip <think> blocks (Qwen3 artifacts) and markdown fences
        cleaned = re.sub(r'<think>.*?</think>', '', raw, flags=re.DOTALL)
        cleaned = re.sub(r'```[a-zA-Z]*\n?', '', cleaned)
        cleaned = re.sub(r'```', '', cleaned).strip()

        json_match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
        if not json_match:
            raise ValueError(f"No JSON in critic response: {cleaned[:200]}")

        parsed = json.loads(json_match.group(0))
        missing = {"error_type", "problem", "fix_instruction"} - set(parsed.keys())
        if missing:
            raise ValueError(f"Critic response missing keys: {missing}")

        et = parsed["error_type"].upper().strip()
        parsed["error_type"] = et if et in ERROR_TYPES else "SYNTAX"
        parsed.setdefault("priority_section", "init")
        return parsed

    # ── Heuristic Fallback ────────────────────────────────────────────────────

    def _heuristic_fallback(self, validator_errors, planner_failure, exc_msg) -> dict:
        errors_text = " ".join(validator_errors or [])
        if "unknown predicate" in errors_text.lower():
            error_type, fix = "PREDICATE", "Replace invalid predicates with valid ones from the domain."
        elif "undeclared object" in errors_text.lower():
            error_type, fix = "OBJECT_MISSING", "Add all referenced objects to the :objects section."
        elif "missing" in errors_text.lower() and "section" in errors_text.lower():
            error_type, fix = "SYNTAX", "Add missing required sections: :objects, :init, :goal."
        elif planner_failure and "unsolvable" in (planner_failure or "").lower():
            error_type, fix = "UNSOLVABLE", "Review :init state — ensure goal is reachable."
        else:
            error_type, fix = "SYNTAX", "Review PDDL structure and correct syntax errors."

        return {
            "error_type": error_type,
            "problem": f"Critic unavailable ({exc_msg[:80]}). Heuristic applied.",
            "fix_instruction": fix,
            "priority_section": "init",
            "raw_response": "",
            "critic_success": False,
            "critic_backend": "heuristic",
        }
