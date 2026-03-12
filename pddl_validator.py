"""
pddl_validator.py
=================
Phase 1 - PDDL Structural Validator

Validates generated PDDL problem files for:
  1. Syntactic correctness (balanced parentheses, required sections)
  2. Semantic consistency (objects used are declared, predicates are valid)
  3. Domain compatibility (only allowed predicates are used)

This is the lightweight validation layer. The full planning solve is in planner_runner.py.
"""

import re
from dataclasses import dataclass, field
from typing import List, Optional


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsed: dict = field(default_factory=dict)   # structured parse of the PDDL

    def summary(self) -> str:
        status = "✅ VALID" if self.is_valid else "❌ INVALID"
        lines = [status]
        if self.errors:
            lines.append("  Errors:")
            for e in self.errors:
                lines.append(f"    - {e}")
        if self.warnings:
            lines.append("  Warnings:")
            for w in self.warnings:
                lines.append(f"    ~ {w}")
        return "\n".join(lines)


# ── Blocksworld Domain Spec ───────────────────────────────────────────────────

VALID_PREDICATES = {"on", "ontable", "clear", "handempty", "holding"}
VALID_ACTIONS    = {"pickup", "putdown", "stack", "unstack"}
REQUIRED_SECTIONS = {"objects", "init", "goal"}


# ── Validator ─────────────────────────────────────────────────────────────────

class PDDLValidator:
    """
    Validates a PDDL problem string against the Blocksworld domain.

    Usage:
        v = PDDLValidator()
        result = v.validate(pddl_string)
        print(result.summary())
    """

    def validate(self, pddl: str) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        # 1. Basic non-empty check
        if not pddl or not pddl.strip():
            result.is_valid = False
            result.errors.append("PDDL string is empty.")
            return result

        # 2. Balanced parentheses
        self._check_parens(pddl, result)

        # 3. Must start with (define (problem ...)
        if not re.search(r'\(\s*define\s*\(\s*problem\s+\w+', pddl, re.IGNORECASE):
            result.errors.append("Missing (define (problem <name>) ...) header.")
            result.is_valid = False

        # 4. Domain declaration
        domain_match = re.search(r'\(:domain\s+(\w+)\s*\)', pddl, re.IGNORECASE)
        if not domain_match:
            result.errors.append("Missing (:domain ...) declaration.")
            result.is_valid = False
        else:
            domain_name = domain_match.group(1).lower()
            if domain_name != "blocksworld":
                result.warnings.append(
                    f"Domain name is '{domain_name}', expected 'blocksworld'."
                )
            result.parsed["domain"] = domain_name

        # 5. Required sections
        sections_found = set()
        for section in REQUIRED_SECTIONS:
            if re.search(rf'\(:{section}\b', pddl, re.IGNORECASE):
                sections_found.add(section)
        missing = REQUIRED_SECTIONS - sections_found
        if missing:
            for m in missing:
                result.errors.append(f"Missing required section: (:{m} ...)")
            result.is_valid = False

        # 6. Parse objects
        objects = self._parse_objects(pddl, result)
        result.parsed["objects"] = objects

        # 7. Parse init facts
        init_facts = self._parse_init(pddl, result)
        result.parsed["init"] = init_facts

        # 8. Validate predicates in init
        self._check_predicates(init_facts, objects, "init", result)

        # 9. Validate handempty or holding is set at start
        init_predicates = [f["predicate"] for f in init_facts]
        if "handempty" not in init_predicates and "holding" not in init_predicates:
            result.warnings.append(
                "Neither (handempty) nor (holding ...) found in :init. "
                "The hand state is undefined."
            )

        # 10. Parse and validate goal
        goal_facts = self._parse_goal(pddl, result)
        result.parsed["goal"] = goal_facts
        self._check_predicates(goal_facts, objects, "goal", result)

        # 11. Every object should appear in init
        if objects:
            mentioned_in_init = set()
            for f in init_facts:
                mentioned_in_init.update(f.get("args", []))
            for obj in objects:
                if obj not in mentioned_in_init:
                    result.warnings.append(
                        f"Object '{obj}' is declared but never mentioned in :init."
                    )

        if result.errors:
            result.is_valid = False

        return result

    # ── Helpers ──────────────────────────────────────────────────────────────

    def _check_parens(self, pddl: str, result: ValidationResult):
        depth = 0
        for i, ch in enumerate(pddl):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth < 0:
                result.errors.append(
                    f"Unmatched closing parenthesis at character {i}."
                )
                result.is_valid = False
                return
        if depth != 0:
            result.errors.append(
                f"Unbalanced parentheses: {depth} unclosed '(' remaining."
            )
            result.is_valid = False

    def _parse_objects(self, pddl: str, result: ValidationResult) -> List[str]:
        m = re.search(r'\(:objects\s+(.*?)\)', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        objects = re.findall(r'\b([a-zA-Z]\w*)\b', raw)
        return [o.lower() for o in objects]

    def _parse_init(self, pddl: str, result: ValidationResult) -> List[dict]:
        m = re.search(r'\(:init\s+(.*?)\)\s*\(:goal', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            # Try alternative: init is the last section before goal
            m = re.search(r'\(:init\s+(.*?)\)(?=\s*\()', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        return self._extract_facts(raw)

    def _parse_goal(self, pddl: str, result: ValidationResult) -> List[dict]:
        m = re.search(r'\(:goal\s+(.*?)\)\s*\)', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        # Remove outer (and ...) wrapper if present
        and_m = re.match(r'\(\s*and\s+(.*)\)', raw, re.IGNORECASE | re.DOTALL)
        if and_m:
            raw = and_m.group(1)
        return self._extract_facts(raw)

    def _extract_facts(self, raw: str) -> List[dict]:
        """Extract a list of predicate facts from a block of PDDL text."""
        facts = []
        for m in re.finditer(r'\(\s*(\w+)\s*((?:\w+\s*)*)\)', raw):
            pred = m.group(1).lower()
            args = m.group(2).split() if m.group(2).strip() else []
            facts.append({"predicate": pred, "args": [a.lower() for a in args]})
        return facts

    def _check_predicates(
        self,
        facts: List[dict],
        objects: List[str],
        section: str,
        result: ValidationResult,
    ):
        for fact in facts:
            pred = fact["predicate"]
            args = fact["args"]

            # Skip PDDL structural keywords
            if pred in {"and", "or", "not", "forall", "exists", "when"}:
                continue

            # Predicate must be valid
            if pred not in VALID_PREDICATES:
                result.errors.append(
                    f"Unknown predicate '({pred})' in :{section}. "
                    f"Valid predicates: {sorted(VALID_PREDICATES)}"
                )

            # Arity checks
            arity_map = {
                "on": 2, "ontable": 1, "clear": 1,
                "handempty": 0, "holding": 1,
            }
            if pred in arity_map:
                expected = arity_map[pred]
                if len(args) != expected:
                    result.errors.append(
                        f"Predicate '{pred}' in :{section} expects {expected} "
                        f"argument(s), got {len(args)}: {args}"
                    )

            # Objects must be declared
            if objects:  # only check if objects section was parsed
                for arg in args:
                    if arg not in objects:
                        result.errors.append(
                            f"Undeclared object '{arg}' used in :{section} "
                            f"predicate ({pred}). Declared: {objects}"
                        )


# ── Standalone test ───────────────────────────────────────────────────────────

if __name__ == "__main__":
    sample_valid = """
(define (problem test-p1)
  (:domain blocksworld)
  (:objects a b)
  (:init
    (ontable a)
    (ontable b)
    (clear a)
    (clear b)
    (handempty)
  )
  (:goal (and (on a b)))
)
"""

    sample_invalid = """
(define (problem test-bad)
  (:domain blocksworld)
  (:objects a b
  (:init
    (ontable a)
    (on_top_of a b)
  )
  (:goal (and (stacked a b)))
)
"""

    v = PDDLValidator()

    print("=== Valid PDDL ===")
    print(v.validate(sample_valid).summary())

    print("\n=== Invalid PDDL ===")
    print(v.validate(sample_invalid).summary())
