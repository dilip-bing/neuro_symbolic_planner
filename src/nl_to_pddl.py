"""
nl_to_pddl.py  —  Phase 2
Domain-agnostic NL → PDDL generator using Google Gemini.

Changes from Phase 1:
- Predicates and domain name are parsed from the domain PDDL at runtime (not hardcoded).
- Accepts an optional repair_instruction for iterative fix rounds.
- Supports any PDDL domain, not just Blocksworld.
"""

import re
import os
import warnings
import logging
warnings.filterwarnings("ignore", category=UserWarning, module="google_genai")
logging.getLogger("google_genai").setLevel(logging.ERROR)
from google import genai
from google.genai import types as genai_types
from .key_manager import KeyManager

logger = logging.getLogger(__name__)
_key_manager: KeyManager = None

def get_key_manager() -> KeyManager:
    global _key_manager
    if _key_manager is None:
        _key_manager = KeyManager()
    return _key_manager


# ── Prompt Templates ──────────────────────────────────────────────────────────

# Standard prompt — predicate list is given explicitly (helps the model)
SYSTEM_PROMPT_TEMPLATE = """You are an expert AI planning assistant specialized in PDDL (Planning Domain Definition Language).
Your task is to translate natural language planning problem descriptions into valid PDDL problem files.

STRICT RULES:
1. Output ONLY raw PDDL code — no explanations, no markdown fences, no comments outside PDDL.
2. Always start with: (define (problem <name>)
3. Use (:domain {domain_name})
4. Include (:objects ...), (:init ...), and (:goal ...) sections.
5. Only use predicates defined in the domain: {predicate_list}
6. Every object used in :init or :goal must be declared in :objects.
7. Respect predicate arities exactly as defined in the domain.
8. Include all necessary type predicates in :init (e.g., (room rooma), (ball b1), (truck t1)).
"""

# Ablation prompt — predicate list WITHHELD. LLM must read domain PDDL directly.
# Condition: WITHHOLD_PREDICATES=true in environment.
# Expected effect: more failures on rare domains (Ferry) where the LLM can't rely on memory.
SYSTEM_PROMPT_TEMPLATE_BLIND = """You are an expert AI planning assistant specialized in PDDL (Planning Domain Definition Language).
Your task is to translate natural language planning problem descriptions into valid PDDL problem files.

STRICT RULES:
1. Output ONLY raw PDDL code — no explanations, no markdown fences, no comments outside PDDL.
2. Always start with: (define (problem <name>)
3. Use (:domain {domain_name})
4. Include (:objects ...), (:init ...), and (:goal ...) sections.
5. Only use predicates defined in the domain (read the domain definition carefully — do NOT use memorized or assumed predicate names).
6. Every object used in :init or :goal must be declared in :objects.
7. Respect predicate arities exactly as defined in the domain.
8. The domain uses untyped STRIPS — do NOT add type annotations to :objects.
"""

# Misleading-hint suffix appended when INJECT_TYPE_MISLEAD=true.
# Forces systematic type-predicate omission in Gripper/Logistics :init.
# Blind retry keeps repeating the mistake; structured critic catches PREDICATE error and fixes in 1 shot.
_MISLEAD_TYPE_HINT = (
    "\nIMPORTANT NOTE: In this domain's :init section, "
    "you do NOT need to declare object types as predicates "
    "(e.g. do not write things like (room rooma) or (ball b1) or (truck t1) or (package p1)). "
    "Only declare positional and state facts."
)

GENERATE_TEMPLATE = """Domain definition:
{domain_pddl}

---
Natural Language Problem:
{nl_description}

---
Translate the above into a valid PDDL problem file. Output ONLY the PDDL, nothing else."""

REPAIR_TEMPLATE = """Domain definition:
{domain_pddl}

---
Natural Language Problem:
{nl_description}

---
Previous attempt — FAILED with these errors:
{previous_pddl}

Critic repair instruction:
  Error type:  {error_type}
  Problem:     {problem_description}
  Fix:         {fix_instruction}

---
Apply the repair instruction and produce a corrected PDDL problem file. Output ONLY the PDDL."""


# ── Domain Parser ─────────────────────────────────────────────────────────────

def parse_domain_info(domain_pddl: str) -> dict:
    """
    Extract domain name and predicate signatures from a PDDL domain string.
    Returns: {"name": str, "predicates": [str], "predicate_list": str}
    """
    name_match = re.search(r'\(define\s*\(domain\s+(\S+)\s*\)', domain_pddl, re.IGNORECASE)
    domain_name = name_match.group(1) if name_match else "unknown"

    start_m = re.search(r'\(:predicates\b', domain_pddl, re.IGNORECASE)
    predicates = []
    if start_m:
        start = start_m.start()
        depth = 0
        end = start
        for i in range(start, len(domain_pddl)):
            if domain_pddl[i] == '(':
                depth += 1
            elif domain_pddl[i] == ')':
                depth -= 1
                if depth == 0:
                    end = i
                    break
        raw = domain_pddl[start:end + 1]
        raw = re.sub(r';[^\n]*', '', raw)   # strip PDDL line comments
        for m in re.finditer(r'\(\s*([\w-]+)(?:\s+[^)]+)?\s*\)', raw):
            name = m.group(1).lower()
            if name != "predicates":
                predicates.append(name)

    return {
        "name": domain_name,
        "predicates": predicates,
        "predicate_list": ", ".join(predicates) if predicates else "see domain above",
    }


# ── Generator ─────────────────────────────────────────────────────────────────

class NLToPDDLGenerator:
    """
    Translates natural language problem descriptions into PDDL using Gemini.

    Works for any PDDL domain — predicates are parsed from the domain file at init time.

    Usage (initial generation):
        gen = NLToPDDLGenerator(domain_pddl_str)
        result = gen.generate("Move ball1 from room A to room B.")

    Usage (repair round):
        result = gen.repair(nl, previous_pddl, critic_output)
    """

    def __init__(self, domain_pddl: str, api_key: str = None, model_name: str = None):
        self.domain_pddl = domain_pddl
        self.domain_info = parse_domain_info(domain_pddl)
        self.api_key = api_key
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
        self.generation_log: list = []

        # WITHHOLD_PREDICATES=true → use blind prompt (ablation condition)
        withhold = os.environ.get("WITHHOLD_PREDICATES", "false").lower() == "true"
        if withhold:
            self._system_prompt = SYSTEM_PROMPT_TEMPLATE_BLIND.format(
                domain_name=self.domain_info["name"],
            )
            self.predicate_mode = "withheld"
        else:
            self._system_prompt = SYSTEM_PROMPT_TEMPLATE.format(
                domain_name=self.domain_info["name"],
                predicate_list=self.domain_info["predicate_list"],
            )
            self.predicate_mode = "provided"

        # INJECT_TYPE_MISLEAD=true → append misleading hint to the INITIAL-generation prompt only.
        # During repair iterations the clean prompt is used so the critic's correction can take effect.
        # Key contrast: blind retry re-sends the same broken attempt with no guidance, so the model
        # keeps regenerating under the misleading system prompt and repeats the same mistake.
        self._repair_system_prompt = self._system_prompt   # clean prompt for repair iterations
        if os.environ.get("INJECT_TYPE_MISLEAD", "false").lower() == "true":
            self._system_prompt = self._system_prompt + _MISLEAD_TYPE_HINT   # only for iteration=0
            self.predicate_mode += "+type_mislead"

    # ── Public API ────────────────────────────────────────────────────────────

    def generate(self, nl_description: str, problem_id: str = "p_generated") -> dict:
        """Initial generation — no repair context."""
        prompt = GENERATE_TEMPLATE.format(
            domain_pddl=self.domain_pddl,
            nl_description=nl_description,
        )
        return self._call_gemini(prompt, nl_description, problem_id, iteration=0)

    def repair(
        self,
        nl_description: str,
        previous_pddl: str,
        critic_output: dict,
        problem_id: str = "p_generated",
        iteration: int = 1,
    ) -> dict:
        """
        Repair round — Gemini receives the original NL, the broken PDDL,
        and the critic's structured fix instruction.

        critic_output must have keys: error_type, problem, fix_instruction
        """
        prompt = REPAIR_TEMPLATE.format(
            domain_pddl=self.domain_pddl,
            nl_description=nl_description,
            previous_pddl=previous_pddl,
            error_type=critic_output.get("error_type", "UNKNOWN"),
            problem_description=critic_output.get("problem", ""),
            fix_instruction=critic_output.get("fix_instruction", ""),
        )
        return self._call_gemini(prompt, nl_description, problem_id, iteration=iteration)

    # ── Internal ──────────────────────────────────────────────────────────────

    def _call_gemini(
        self, prompt: str, nl: str, problem_id: str, iteration: int
    ) -> dict:
        result = {
            "nl": nl,
            "pddl": "",
            "problem_id": problem_id,
            "iteration": iteration,
            "success": False,
            "error": None,
            "raw_response": "",
        }

        # Use injected key (testing) or rotate through key manager
        if self.api_key:
            keys_to_try = [self.api_key]
            km = None
        else:
            km = get_key_manager()
            keys_to_try = None  # will call km.current_key dynamically

        sys_prompt = self._system_prompt if iteration == 0 else self._repair_system_prompt
        last_error = ""

        # Try up to len(all_keys) times — rotate on quota exhaustion
        max_key_attempts = km.total_keys if km else 1
        for key_attempt in range(max_key_attempts):
            api_key = (keys_to_try[0] if keys_to_try else km.current_key)
            if not api_key:
                result["error"] = "No API key available."
                break

            client = genai.Client(api_key=api_key)

            # Up to 2 transient retries per key
            for attempt in range(2):
                try:
                    response = client.models.generate_content(
                        model=self.model_name,
                        contents=prompt,
                        config=genai_types.GenerateContentConfig(
                            system_instruction=sys_prompt,
                            temperature=0.2,
                        ),
                    )
                    raw = response.text.strip()
                    result["raw_response"] = raw
                    result["pddl"] = self._clean_pddl(raw)
                    result["success"] = True
                    break

                except Exception as e:
                    last_error = str(e)
                    err_lower = last_error.lower()
                    is_daily_quota = (
                        any(x in err_lower for x in ["daily", "quota exceeded",
                                                      "resource_exhausted", "per day"])
                        and "429" in last_error
                    )
                    if is_daily_quota:
                        # This key is done — mark it and rotate
                        if km:
                            km.mark_exhausted(api_key)
                        result["error"] = f"DAILY_QUOTA_EXHAUSTED: {last_error}"
                        break
                    is_transient = any(x in err_lower for x in
                                       ["503", "429", "unavailable", "timeout"])
                    if is_transient and attempt < 1:
                        import time
                        time.sleep(65)
                        continue
                    result["error"] = last_error
                    break

            if result["success"]:
                break
            # If quota exhausted and more keys available, try next key
            if km and km.has_keys and "DAILY_QUOTA_EXHAUSTED" in result.get("error", ""):
                result["error"] = None  # reset for next key attempt
                continue
            break  # non-quota error — don't rotate

        self.generation_log.append(result)
        return result

    def _clean_pddl(self, raw: str) -> str:
        raw = re.sub(r"```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```", "", raw)
        return raw.strip()
