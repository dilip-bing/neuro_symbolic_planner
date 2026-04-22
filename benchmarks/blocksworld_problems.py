"""
Blocksworld benchmark problems for Phase 2.
6 core problems carried over from Phase 1 + 4 medium + 5 hard problems (Phase 2 extension).
Each problem has an NL description and a reference PDDL for faithfulness evaluation.
"""

PROBLEMS = [
    # ── Core 6 (Phase 1 carry-over) ──────────────────────────────────────────
    {
        "id": "bw_p1",
        "nl": (
            "There are two blocks, A and B, both sitting on the table. "
            "The goal is to stack block A on top of block B."
        ),
        "nl_agnostic": (
            "Two objects, A and B, both rest on a flat surface. "
            "Place object A so it rests directly on top of object B."
        ),
        "reference_pddl": """(define (problem bw-p1)
  (:domain blocksworld)
  (:objects a b)
  (:init (ontable a) (ontable b) (clear a) (clear b) (handempty))
  (:goal (and (on a b)))
)""",
    },
    {
        "id": "bw_p2",
        "nl": (
            "There are three blocks A, B, and C, all on the table. "
            "Build a tower where C is on top of B, and B is on top of A."
        ),
        "nl_agnostic": (
            "Three objects A, B, and C all rest on a flat surface. "
            "Arrange them into a single stack: C on top of B, B on top of A."
        ),
        "reference_pddl": """(define (problem bw-p2)
  (:domain blocksworld)
  (:objects a b c)
  (:init (ontable a) (ontable b) (ontable c) (clear a) (clear b) (clear c) (handempty))
  (:goal (and (on c b) (on b a)))
)""",
    },
    {
        "id": "bw_p3",
        "nl": (
            "Block A is on top of block B, and B is on top of C, with C on the table. "
            "Rearrange so that C is on top of B, and B is on top of A."
        ),
        "nl_agnostic": (
            "Object A rests on object B, which rests on object C, which sits on a flat surface. "
            "Rearrange so C is on top of B and B is on top of A."
        ),
        "reference_pddl": """(define (problem bw-p3)
  (:domain blocksworld)
  (:objects a b c)
  (:init (on a b) (on b c) (ontable c) (clear a) (handempty))
  (:goal (and (on c b) (on b a)))
)""",
    },
    {
        "id": "bw_p4",
        "nl": (
            "Blocks A, B, C, and D are all on the table. "
            "Stack them into a single tower: D on top of C, C on top of B, B on top of A."
        ),
        "nl_agnostic": (
            "Four objects A, B, C, D all sit on a flat surface. "
            "Build one stack: D on C, C on B, B on A."
        ),
        "reference_pddl": """(define (problem bw-p4)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (ontable a) (ontable b) (ontable c) (ontable d)
         (clear a) (clear b) (clear c) (clear d) (handempty))
  (:goal (and (on d c) (on c b) (on b a)))
)""",
    },
    {
        "id": "bw_p5",
        "nl": (
            "Block A is stacked on top of block B, which is on the table. "
            "Swap them so that B ends up on top of A."
        ),
        "nl_agnostic": (
            "Object A rests on object B, and B is on a flat surface. "
            "Swap them: B should end up resting on top of A."
        ),
        "reference_pddl": """(define (problem bw-p5)
  (:domain blocksworld)
  (:objects a b)
  (:init (on a b) (ontable b) (clear a) (handempty))
  (:goal (and (on b a)))
)""",
    },
    {
        "id": "bw_p6",
        "nl": (
            "Five blocks A, B, C, D, E are all on the table. "
            "Build a tower with E on top of D, D on top of C, C on top of B, B on top of A."
        ),
        "nl_agnostic": (
            "Five objects A, B, C, D, E all sit on a flat surface. "
            "Stack them: E on D, D on C, C on B, B on A."
        ),
        "reference_pddl": """(define (problem bw-p6)
  (:domain blocksworld)
  (:objects a b c d e)
  (:init (ontable a) (ontable b) (ontable c) (ontable d) (ontable e)
         (clear a) (clear b) (clear c) (clear d) (clear e) (handempty))
  (:goal (and (on e d) (on d c) (on c b) (on b a)))
)""",
    },
    # ── New harder problems (Phase 2 extension) ───────────────────────────────
    {
        "id": "bw_p7",
        "nl": (
            "Block C is on block A, and block A is on the table. Block B is on the table. "
            "The goal is: A on B, and C on A."
        ),
        "nl_agnostic": (
            "Object C rests on object A; A sits on a flat surface. Object B also sits on the surface. "
            "Goal: A on B, C on A."
        ),
        "reference_pddl": """(define (problem bw-p7)
  (:domain blocksworld)
  (:objects a b c)
  (:init (on c a) (ontable a) (ontable b) (clear c) (clear b) (handempty))
  (:goal (and (on a b) (on c a)))
)""",
    },
    {
        "id": "bw_p8",
        "nl": (
            "You have six blocks: A, B, C, D, E, F, all on the table. "
            "Build two towers: one with C on B on A, and another with F on E on D."
        ),
        "nl_agnostic": (
            "Six objects A, B, C, D, E, F all sit on a flat surface. "
            "Build two separate stacks: one with C on B on A, and one with F on E on D."
        ),
        "reference_pddl": """(define (problem bw-p8)
  (:domain blocksworld)
  (:objects a b c d e f)
  (:init (ontable a) (ontable b) (ontable c) (ontable d) (ontable e) (ontable f)
         (clear a) (clear b) (clear c) (clear d) (clear e) (clear f) (handempty))
  (:goal (and (on c b) (on b a) (on f e) (on e d)))
)""",
    },
    {
        "id": "bw_p9",
        "nl": (
            "The current state: D is on C, C is on B, B is on A, A is on the table. "
            "Goal: reverse the entire stack so A is on B, B is on C, C is on D, D on the table."
        ),
        "nl_agnostic": (
            "Current arrangement (top to bottom): D, C, B, A — with A resting on a flat surface. "
            "Fully reverse it so (top to bottom) A, B, C, D — D resting on the surface."
        ),
        "reference_pddl": """(define (problem bw-p9)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (on d c) (on c b) (on b a) (ontable a) (clear d) (handempty))
  (:goal (and (on a b) (on b c) (on c d) (ontable d)))
)""",
    },
    {
        "id": "bw_p10",
        "nl": (
            "Block A is on block B. Block C is on block D. B and D are on the table. "
            "Rearrange so that B is on A, and D is on C."
        ),
        "nl_agnostic": (
            "Object A rests on B; object C rests on D; B and D sit on a flat surface. "
            "Swap each pair's order: place B on top of A, and D on top of C."
        ),
        "reference_pddl": """(define (problem bw-p10)
  (:domain blocksworld)
  (:objects a b c d)
  (:init (on a b) (on c d) (ontable b) (ontable d)
         (clear a) (clear c) (handempty))
  (:goal (and (on b a) (on d c)))
)""",
    },
    # ── Hard problems (Phase 2 — designed to stress-test LLM generation) ─────
    {
        "id": "bw_p11",
        "nl": (
            "Eight blocks A, B, C, D, E, F, G, H are all on the table. "
            "Build a single tall tower with H on top: H on G, G on F, F on E, "
            "E on D, D on C, C on B, B on A."
        ),
        "nl_agnostic": (
            "Eight objects A through H all rest on a flat surface. "
            "Build one tall stack: H on G, G on F, F on E, E on D, D on C, C on B, B on A."
        ),
        "reference_pddl": """(define (problem bw-p11)
  (:domain blocksworld)
  (:objects a b c d e f g h)
  (:init
    (ontable a) (ontable b) (ontable c) (ontable d)
    (ontable e) (ontable f) (ontable g) (ontable h)
    (clear a) (clear b) (clear c) (clear d)
    (clear e) (clear f) (clear g) (clear h)
    (handempty))
  (:goal (and (on h g) (on g f) (on f e) (on e d) (on d c) (on c b) (on b a)))
)""",
    },
    {
        "id": "bw_p12",
        "nl": (
            "The current state: E is on D, D is on C, C is on B, B is on A, "
            "and A is on the table. Completely reverse the stack so that A is on B, "
            "B is on C, C is on D, D is on E, and E is on the table."
        ),
        "nl_agnostic": (
            "Five objects stacked top-to-bottom: E, D, C, B, A — A on the surface. "
            "Fully reverse the arrangement: A on B, B on C, C on D, D on E, E on the surface."
        ),
        "reference_pddl": """(define (problem bw-p12)
  (:domain blocksworld)
  (:objects a b c d e)
  (:init (on e d) (on d c) (on c b) (on b a) (ontable a) (clear e) (handempty))
  (:goal (and (on a b) (on b c) (on c d) (on d e) (ontable e)))
)""",
    },
    {
        "id": "bw_p13",
        "nl": (
            "There are two separate towers: the first has C on B on A (A on the table), "
            "and the second has F on E on D (D on the table). "
            "Combine them into one tower by placing the ABC stack on top of D: "
            "goal is C on B, B on A, A on D, D on E, E on F, F on the table."
        ),
        "nl_agnostic": (
            "Two separate stacks: first has C on B on A (A on surface); second has F on E on D (D on surface). "
            "Merge into one: lift the ABC stack onto D, giving C on B on A on D on E on F (F on surface)."
        ),
        "reference_pddl": """(define (problem bw-p13)
  (:domain blocksworld)
  (:objects a b c d e f)
  (:init
    (on c b) (on b a) (ontable a) (clear c)
    (on f e) (on e d) (ontable d) (clear f)
    (handempty))
  (:goal (and (on c b) (on b a) (on a d) (on d e) (on e f) (ontable f)))
)""",
    },
    {
        "id": "bw_p14",
        "nl": (
            "Block A is on block B, block C is on block D, and block E is on block F. "
            "Blocks B, D, and F are all on the table. "
            "Perform a three-way rotation of the bases: rearrange so that A ends up on D, "
            "C ends up on F, and E ends up on B."
        ),
        "nl_agnostic": (
            "Three pairs, each sitting on a flat surface: A on B, C on D, E on F. "
            "Rotate each top object to a different base: A moves to D, C moves to F, E moves to B."
        ),
        "reference_pddl": """(define (problem bw-p14)
  (:domain blocksworld)
  (:objects a b c d e f)
  (:init
    (on a b) (on c d) (on e f)
    (ontable b) (ontable d) (ontable f)
    (clear a) (clear c) (clear e) (handempty))
  (:goal (and (on a d) (on c f) (on e b)))
)""",
    },
    {
        "id": "bw_p15",
        "nl": (
            "A tower has E on D, D on C, C on B, B on A, with A on the table. "
            "Two extra blocks F and G are separately on the table. "
            "First reverse the five-block stack so it reads (from bottom) E, D, C, B, A — "
            "meaning A on B, B on C, C on D, D on E, E on table — "
            "then place F on top of A and G on top of F."
        ),
        "nl_agnostic": (
            "A stack of five objects (top to bottom: E, D, C, B, A on surface) plus two loose objects F and G on the surface. "
            "Reverse the five-object stack (result: A on B on C on D on E, E on surface), "
            "then place F on A and G on F."
        ),
        "reference_pddl": """(define (problem bw-p15)
  (:domain blocksworld)
  (:objects a b c d e f g)
  (:init
    (on e d) (on d c) (on c b) (on b a) (ontable a) (clear e)
    (ontable f) (clear f) (ontable g) (clear g) (handempty))
  (:goal (and (on a b) (on b c) (on c d) (on d e) (ontable e) (on f a) (on g f)))
)""",
    },
]
