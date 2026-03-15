"""
nl_to_pddl.py
=============
Phase 1 - NL → PDDL Generator

Uses the configured model API to translate
natural language problem descriptions into valid PDDL problem files.

The generator is given:
  - The domain PDDL as context
  - The natural language description
    - A strict output template

It returns the raw PDDL string.
"""

import re
import os
import google.generativeai as genai


# ── Prompt Templates ────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are an expert AI planning assistant specialized in PDDL (Planning Domain Definition Language).
Your task is to translate natural language planning problem descriptions into valid PDDL problem files.

STRICT RULES:
1. Output ONLY the raw PDDL code — no explanations, no markdown fences, no comments outside PDDL.
2. Always start with: (define (problem <name>)
3. Use (:domain blocksworld)
4. Include (:objects ...), (:init ...), and (:goal ...) sections.
5. Only use these predicates: (on ?x ?y), (ontable ?x), (clear ?x), (handempty), (holding ?x)
6. Object names must be single lowercase letters (a, b, c, ...) unless specified otherwise.
7. The (:init ...) section MUST establish (handempty) if no block is held at start.
8. Every object must appear in at least one init predicate.
9. Every block that has nothing on it at the start must be (clear ...).
"""

USER_TEMPLATE = """Domain definition:
{domain_pddl}

---
Natural Language Problem:
{nl_description}

---
Translate the above into a valid PDDL problem file. Output ONLY the PDDL, nothing else."""


# ── Generator Class ───────────────────────────────────────────────────────────

class NLToPDDLGenerator:
    """
    Translates a natural language problem description into a PDDL problem string.

    Usage:
        gen = NLToPDDLGenerator(domain_pddl_str)
        pddl = gen.generate("Stack block A on top of block B.")
    """

    def __init__(self, domain_pddl: str, api_key: str = None, model_name: str = None):
        self.domain_pddl = domain_pddl
        self.api_key = api_key
        self.model_name = model_name or os.environ.get("GEMINI_MODEL", "gemini-3-flash-preview")
        self.generation_log = []   # keeps history of all calls for analysis

    def generate(self, nl_description: str, problem_id: str = "p_generated") -> dict:
        """
        Generate PDDL from a natural language description.

        Returns a dict:
          {
            "nl": str,
            "pddl": str,
            "problem_id": str,
            "success": bool,
            "error": str or None,
            "raw_response": str,
          }
        """
        result = {
            "nl": nl_description,
            "pddl": "",
            "problem_id": problem_id,
            "success": False,
            "error": None,
            "raw_response": "",
        }

        user_msg = USER_TEMPLATE.format(
            domain_pddl=self.domain_pddl,
            nl_description=nl_description,
        )

        try:
            api_key = self.api_key or os.environ.get("GEMINI_API_KEY", "")
            if not api_key:
                raise ValueError(
                    "No Gemini API key found. Set GEMINI_API_KEY environment variable."
                )
            timeout_s = int(os.environ.get("GEMINI_TIMEOUT_S", "60"))
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel(
                model_name=self.model_name,
                system_instruction=SYSTEM_PROMPT
            )
            response = model.generate_content(
                user_msg,
                request_options={"timeout": timeout_s},
            )
            raw = response.text.strip()
            result["raw_response"] = raw
            result["pddl"] = self._clean_pddl(raw)
            result["success"] = True

        except Exception as e:
            result["error"] = str(e)
            result["success"] = False

        self.generation_log.append(result)
        return result

    def _clean_pddl(self, raw: str) -> str:
        """Strip markdown fences if the model accidentally adds them."""
        # Remove ```pddl ... ``` or ``` ... ```
        raw = re.sub(r"```[a-zA-Z]*\n?", "", raw)
        raw = re.sub(r"```", "", raw)
        return raw.strip()


# ── Benchmark NL Descriptions ────────────────────────────────────────────────

BENCHMARK_PROBLEMS = [
    {
        "id": "bw_p1_2blocks",
        "nl": (
            "There are two blocks, A and B, both sitting on the table. "
            "The goal is to stack block A on top of block B."
        ),
    },
    {
        "id": "bw_p2_3tower",
        "nl": (
            "There are three blocks A, B, and C, all on the table. "
            "Build a tower where C is on top of B, and B is on top of A."
        ),
    },
    {
        "id": "bw_p3_reverse3",
        "nl": (
            "Block A is on top of block B, and block B is on top of block C, "
            "with C sitting on the table. "
            "Rearrange the blocks so that C is on top of B, and B is on top of A."
        ),
    },
    {
        "id": "bw_p4_4tower",
        "nl": (
            "Blocks A, B, C, and D are all on the table. "
            "Stack them into a single tower: D on top of C, C on top of B, "
            "B on top of A, with A remaining on the table."
        ),
    },
    {
        "id": "bw_p5_swap",
        "nl": (
            "Block A is currently stacked on top of block B, which is on the table. "
            "Swap them so that B ends up on top of A."
        ),
    },
    {
        "id": "bw_p6_5tower",
        "nl": (
            "There are five blocks: A, B, C, D, and E, all sitting on the table. "
            "Stack them into a tower with E on top of D, D on top of C, "
            "C on top of B, and B on top of A."
        ),
    },
]


# ── Quick test (run directly) ─────────────────────────────────────────────────

if __name__ == "__main__":
    import pathlib

    domain_path = pathlib.Path(__file__).parent.parent / "domains" / "blocksworld.pddl"
    domain_pddl = domain_path.read_text()

    gen = NLToPDDLGenerator(domain_pddl)
    result = gen.generate(BENCHMARK_PROBLEMS[0]["nl"], BENCHMARK_PROBLEMS[0]["id"])

    if result["success"]:
        print("✅ Generated PDDL:\n")
        print(result["pddl"])
    else:
        print(f"❌ Error: {result['error']}")
