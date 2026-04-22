"""
pddl_validator.py  —  Phase 2
Domain-agnostic PDDL validator.

Changes from Phase 1:
- Valid predicates and their arities are parsed from the domain PDDL at init time.
- Works for Blocksworld, Gripper, Logistics, or any STRIPS domain.
- Structural checks (parentheses, required sections) are unchanged.
- Error messages now include the domain's actual predicate list for better critic context.
"""

import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional


# ── Data Structures ───────────────────────────────────────────────────────────

@dataclass
class ValidationResult:
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    parsed: dict = field(default_factory=dict)

    def summary(self) -> str:
        status = "VALID" if self.is_valid else "INVALID"
        lines = [status]
        for e in self.errors:
            lines.append(f"  ERROR: {e}")
        for w in self.warnings:
            lines.append(f"  WARN:  {w}")
        return "\n".join(lines)

    def error_list_for_critic(self) -> List[str]:
        """Returns errors in a format ready for the critic prompt."""
        return self.errors + [f"(warning) {w}" for w in self.warnings]


REQUIRED_SECTIONS = {"objects", "init", "goal"}
PDDL_KEYWORDS = {"and", "or", "not", "forall", "exists", "when", "imply"}


# ── Domain Parser ─────────────────────────────────────────────────────────────

def parse_domain_predicates(domain_pddl: str) -> Dict[str, int]:
    """
    Parse all predicates and their arities from a PDDL domain string.
    Returns: {"predicate_name": arity, ...}

    Uses balanced-parenthesis extraction to handle multi-line :predicates blocks.
    Example for Gripper:
      {"room": 1, "ball": 1, "gripper": 1, "at-robby": 1, "at": 2, "free": 1, "carry": 2}
    """
    # Find the start of (:predicates ...
    start_m = re.search(r'\(:predicates\b', domain_pddl, re.IGNORECASE)
    if not start_m:
        return {}

    # Walk forward counting parens to find the matching close paren
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
    # Strip PDDL line comments before parsing to avoid picking up words from comments
    raw = re.sub(r';[^\n]*', '', raw)

    predicates: Dict[str, int] = {}
    # Each predicate: (name ?param1 ?param2 ...) — skip the outer (:predicates ...) wrapper
    for m in re.finditer(r'\(\s*([\w-]+)((?:\s+\?[\w-]+(?:\s+-\s+[\w-]+)?)*)\s*\)', raw):
        name = m.group(1).lower()
        if name == "predicates":
            continue
        params_str = m.group(2).strip()
        arity = len(re.findall(r'\?[\w-]+', params_str))
        predicates[name] = arity

    return predicates


def parse_domain_name(domain_pddl: str) -> str:
    m = re.search(r'\(define\s*\(domain\s+(\S+)\s*\)', domain_pddl, re.IGNORECASE)
    return m.group(1).lower() if m else "unknown"


# ── Validator ─────────────────────────────────────────────────────────────────

class PDDLValidator:
    """
    Validates a PDDL problem string against a given domain.

    Usage:
        v = PDDLValidator(domain_pddl_str)
        result = v.validate(problem_pddl_str)
        print(result.summary())
    """

    def __init__(self, domain_pddl: str):
        self.domain_name = parse_domain_name(domain_pddl)
        self.valid_predicates = parse_domain_predicates(domain_pddl)
        # 1-arg predicates that appear as positive (add) effects in any action
        # are *state* predicates (they change during execution, e.g. holding, clear,
        # ontable, free, at-robby).  Pure *type* predicates (room, ball, truck …)
        # are never effects — they are invariants set once in :init.
        self._state_predicates = self._parse_add_effect_predicates(domain_pddl)

    def validate(self, pddl: str) -> ValidationResult:
        result = ValidationResult(is_valid=True)

        if not pddl or not pddl.strip():
            result.is_valid = False
            result.errors.append("PDDL string is empty.")
            return result

        self._check_parens(pddl, result)
        self._check_define_header(pddl, result)
        self._check_domain_declaration(pddl, result)
        self._check_required_sections(pddl, result)

        objects = self._parse_objects(pddl, result)
        result.parsed["objects"] = objects

        init_facts = self._parse_init(pddl, result)
        result.parsed["init"] = init_facts
        self._check_predicates(init_facts, objects, "init", result)

        goal_facts = self._parse_goal(pddl, result)
        result.parsed["goal"] = goal_facts
        self._check_predicates(goal_facts, objects, "goal", result)

        self._check_objects_mentioned_in_init(objects, init_facts, result)
        self._check_missing_type_predicates(objects, init_facts, result)

        if result.errors:
            result.is_valid = False

        return result

    # ── Section Checks ────────────────────────────────────────────────────────

    def _check_parens(self, pddl: str, result: ValidationResult):
        depth = 0
        for i, ch in enumerate(pddl):
            if ch == "(":
                depth += 1
            elif ch == ")":
                depth -= 1
            if depth < 0:
                result.errors.append(f"Unmatched ')' at character {i}.")
                result.is_valid = False
                return
        if depth != 0:
            result.errors.append(f"Unbalanced parentheses: {depth} unclosed '(' remaining.")
            result.is_valid = False

    def _check_define_header(self, pddl: str, result: ValidationResult):
        if not re.search(r'\(\s*define\s*\(\s*problem\s+\w+', pddl, re.IGNORECASE):
            result.errors.append("Missing (define (problem <name>) ...) header.")
            result.is_valid = False

    def _check_domain_declaration(self, pddl: str, result: ValidationResult):
        m = re.search(r'\(:domain\s+(\S+?)\s*\)', pddl, re.IGNORECASE)
        if not m:
            result.errors.append("Missing (:domain ...) declaration.")
            result.is_valid = False
            return
        declared = m.group(1).lower()
        result.parsed["domain"] = declared
        if declared != self.domain_name:
            result.warnings.append(
                f"Domain declared as '{declared}' but validator loaded for '{self.domain_name}'."
            )

    def _check_required_sections(self, pddl: str, result: ValidationResult):
        for section in REQUIRED_SECTIONS:
            if not re.search(rf'\(:{section}\b', pddl, re.IGNORECASE):
                result.errors.append(f"Missing required section: (:{section} ...)")
                result.is_valid = False

    # ── Parsers ───────────────────────────────────────────────────────────────

    def _parse_objects(self, pddl: str, result: ValidationResult) -> List[str]:
        m = re.search(r'\(:objects\s+(.*?)\)', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        # Strip PDDL type annotations: "obj1 obj2 - typename" (space before hyphen).
        # Do NOT strip hyphenated object names like "airport-bos" (no space before hyphen).
        raw = re.sub(r'\s+-\s+\w+', ' ', raw)
        return [o.lower() for o in re.findall(r'\b([\w][\w-]*)\b', raw)]

    def _parse_init(self, pddl: str, result: ValidationResult) -> List[dict]:
        m = re.search(r'\(:init\s+(.*?)\)\s*\(:goal', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            m = re.search(r'\(:init\s+(.*?)\)(?=\s*\()', pddl, re.IGNORECASE | re.DOTALL)
        return self._extract_facts(m.group(1)) if m else []

    def _parse_goal(self, pddl: str, result: ValidationResult) -> List[dict]:
        m = re.search(r'\(:goal\s+(.*?)\)\s*\)', pddl, re.IGNORECASE | re.DOTALL)
        if not m:
            return []
        raw = m.group(1).strip()
        and_m = re.match(r'\(\s*and\s+(.*)\)', raw, re.IGNORECASE | re.DOTALL)
        if and_m:
            raw = and_m.group(1)
        return self._extract_facts(raw)

    def _extract_facts(self, raw: str) -> List[dict]:
        facts = []
        for m in re.finditer(r'\(\s*([\w-]+)\s*((?:[\w-]+\s*)*)\)', raw):
            pred = m.group(1).lower()
            args = m.group(2).split() if m.group(2).strip() else []
            facts.append({"predicate": pred, "args": [a.lower() for a in args]})
        return facts

    # ── Semantic Checks ───────────────────────────────────────────────────────

    def _check_predicates(
        self, facts: List[dict], objects: List[str], section: str, result: ValidationResult
    ):
        valid_names = sorted(self.valid_predicates.keys())

        for fact in facts:
            pred = fact["predicate"]
            args = fact["args"]

            if pred in PDDL_KEYWORDS:
                continue

            if pred not in self.valid_predicates:
                result.errors.append(
                    f"Unknown predicate '{pred}' in :{section}. "
                    f"Valid predicates for {self.domain_name}: {valid_names}"
                )
                continue

            expected_arity = self.valid_predicates[pred]
            if len(args) != expected_arity:
                result.errors.append(
                    f"Predicate '{pred}' in :{section} expects {expected_arity} arg(s), "
                    f"got {len(args)}: {args}"
                )

            if objects:
                for arg in args:
                    if arg not in objects:
                        result.errors.append(
                            f"Undeclared object '{arg}' in :{section} ({pred}). "
                            f"Declared objects: {objects}"
                        )

    def _check_objects_mentioned_in_init(
        self, objects: List[str], init_facts: List[dict], result: ValidationResult
    ):
        if not objects:
            return
        mentioned = set()
        for f in init_facts:
            mentioned.update(f.get("args", []))
        for obj in objects:
            if obj not in mentioned:
                result.warnings.append(
                    f"Object '{obj}' declared in :objects but never referenced in :init."
                )

    def _parse_add_effect_predicates(self, domain_pddl: str) -> set:
        """
        Return the set of 1-arg predicates that appear as positive (add) effects
        in any domain action.  These are *state* predicates that legitimately start
        false (e.g. holding, clear, ontable, free, at-robby) and must NOT be treated
        as missing type declarations when absent from :init.
        """
        state_preds: set = set()
        for eff_m in re.finditer(r':effect\b(.*?)(?=\s*\(:action|\s*\)[\s\n]*\(define|$)',
                                  domain_pddl, re.IGNORECASE | re.DOTALL):
            block = eff_m.group(1)
            # Remove (not ...) sub-expressions so we only see positive literals
            block_pos = re.sub(r'\(\s*not\s*\([^)]*\)\s*\)', '', block)
            for lm in re.finditer(r'\(\s*([\w-]+)\s+\?[\w-]+\s*\)', block_pos):
                pred = lm.group(1).lower()
                if pred in self.valid_predicates and self.valid_predicates[pred] == 1:
                    state_preds.add(pred)
        return state_preds

    def _check_missing_type_predicates(
        self, objects: List[str], init_facts: List[dict], result: ValidationResult
    ):
        """
        In untyped STRIPS domains, certain 1-arg predicates act as type declarations
        (room, ball, gripper, truck, package …) and MUST appear in :init for every
        object that needs them.

        State predicates (holding, clear, ontable, free, at-robby …) are correctly
        absent from :init when they start false, so we exclude them from this check.
        We identify state predicates by parsing which 1-arg predicates appear as
        positive add-effects in the domain actions.
        """
        if not objects:
            return

        arity1_predicates = {p for p, a in self.valid_predicates.items() if a == 1}
        if not arity1_predicates:
            return

        # Exclude state predicates: only pure type predicates (never add-effects) remain
        type_predicates = arity1_predicates - self._state_predicates
        if not type_predicates:
            # Domain has no pure type predicates (e.g. Blocksworld) — nothing to check
            return

        used_in_init = {f["predicate"] for f in init_facts if f["predicate"] in type_predicates}
        missing = type_predicates - used_in_init

        # Only warn when ALL type predicates are absent — the INJECT_TYPE_MISLEAD pattern
        if missing and len(used_in_init) == 0:
            result.warnings.append(
                f"MISSING TYPE PREDICATES: The following 1-arg domain predicates are defined "
                f"but never appear in :init — objects are likely untyped: {sorted(missing)}. "
                f"In untyped STRIPS, every object needs its type declared as a predicate fact "
                f"in :init (e.g. '(room rooma)', '(ball ball1)', '(gripper left)')."
            )
