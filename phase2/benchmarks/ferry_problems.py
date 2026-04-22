"""
Ferry benchmark problems for Phase 2.
Domain: a ferry carries cars (one at a time) between locations.

8 problems — graded easy→hard.

Why this domain is valuable for the paper:
  - Rarely cited in papers → LLMs have not memorized predicate names
  - Key failure modes:
      * (on ?car ?ferry) — wrong arity (should be (on ?car), 1-arg)
      * 'carry' / 'loaded' instead of 'on'
      * 'empty' instead of 'empty-ferry'
      * (at-ferry ?from ?to) — wrong arity (should be (at-ferry ?loc), 1-arg)
      * typed :objects in untyped STRIPS domain
      * missing (empty-ferry) in :init
  - Combined with WITHHOLD_PREDICATES=true, this domain reliably produces
    failures that the structured critic can fix but blind retry cannot.

Predicate summary (for reference):
  (at-ferry ?loc)   — 1-arg
  (at ?obj ?loc)    — 2-arg
  (on ?car)         — 1-arg  ← most common error point
  (empty-ferry)     — 0-arg  ← second most common error point
"""

PROBLEMS = [
    # ── Easy (1–3): basic ferry mechanics ─────────────────────────────────────
    {
        "id": "fe_p1",
        "nl": (
            "There are two locations: left bank (l1) and right bank (l2). "
            "A car (car1) is at l1. The ferry is also at l1 and is empty. "
            "Transport car1 to l2."
        ),
        "nl_agnostic": (
            "Two docking points: l1 and l2. "
            "A vehicle (car1) is at l1. A transport vessel is also at l1 and carries nothing. "
            "Move car1 to l2 using the vessel."
        ),
        "reference_pddl": """(define (problem ferry-p1)
  (:domain ferry)
  (:objects car1 l1 l2)
  (:init
    (at-ferry l1)
    (at car1 l1)
    (empty-ferry)
  )
  (:goal (and (at car1 l2)))
)""",
    },
    {
        "id": "fe_p2",
        "nl": (
            "Two cars (car1 and car2) are both at location l1. "
            "The ferry is at l1 and is empty. "
            "Transport both cars to location l2."
        ),
        "nl_agnostic": (
            "Two vehicles (car1, car2) are both at docking point l1. "
            "A transport vessel is at l1 and carries nothing. "
            "Move both vehicles to docking point l2."
        ),
        "reference_pddl": """(define (problem ferry-p2)
  (:domain ferry)
  (:objects car1 car2 l1 l2)
  (:init
    (at-ferry l1)
    (at car1 l1)
    (at car2 l1)
    (empty-ferry)
  )
  (:goal (and (at car1 l2) (at car2 l2)))
)""",
    },
    {
        "id": "fe_p3",
        "nl": (
            "There are three locations: l1, l2, l3. "
            "Car1 is at l1. The ferry is at l2 (the middle) and is empty. "
            "Deliver car1 to l3."
        ),
        "nl_agnostic": (
            "Three docking points: l1, l2, l3. "
            "Vehicle car1 is at l1. A transport vessel is at the middle point l2, carrying nothing. "
            "Move car1 to l3."
        ),
        "reference_pddl": """(define (problem ferry-p3)
  (:domain ferry)
  (:objects car1 l1 l2 l3)
  (:init
    (at-ferry l2)
    (at car1 l1)
    (empty-ferry)
  )
  (:goal (and (at car1 l3)))
)""",
    },
    # ── Medium (4–5): multi-car with routing ──────────────────────────────────
    {
        "id": "fe_p4",
        "nl": (
            "Two locations: l1 and l2. "
            "Car1 is at l1 and needs to go to l2. "
            "Car2 is at l2 and needs to go to l1. "
            "The ferry starts at l1 and is empty. Swap the two cars."
        ),
        "nl_agnostic": (
            "Two docking points: l1 and l2. "
            "Vehicle car1 at l1 must reach l2; vehicle car2 at l2 must reach l1. "
            "The transport vessel starts at l1, carrying nothing. Swap the two vehicles."
        ),
        "reference_pddl": """(define (problem ferry-p4)
  (:domain ferry)
  (:objects car1 car2 l1 l2)
  (:init
    (at-ferry l1)
    (at car1 l1)
    (at car2 l2)
    (empty-ferry)
  )
  (:goal (and (at car1 l2) (at car2 l1)))
)""",
    },
    {
        "id": "fe_p5",
        "nl": (
            "Three locations: l1, l2, l3. "
            "Car1 is at l1 (needs to go to l3). "
            "Car2 is at l2 (needs to go to l3). "
            "The ferry starts at l1 and is empty. "
            "Deliver both cars to l3."
        ),
        "nl_agnostic": (
            "Three docking points: l1, l2, l3. "
            "Vehicle car1 at l1 must reach l3; vehicle car2 at l2 must also reach l3. "
            "Transport vessel starts at l1, carrying nothing. Deliver both vehicles to l3."
        ),
        "reference_pddl": """(define (problem ferry-p5)
  (:domain ferry)
  (:objects car1 car2 l1 l2 l3)
  (:init
    (at-ferry l1)
    (at car1 l1)
    (at car2 l2)
    (empty-ferry)
  )
  (:goal (and (at car1 l3) (at car2 l3)))
)""",
    },
    # ── Hard (6–8): 3 locations, 3–5 cars, complex routing ────────────────────
    {
        "id": "fe_p6",
        "nl": (
            "Three locations: l1, l2, l3. "
            "Car1 and car2 are at l1 (both need to reach l3). "
            "Car3 is at l3 (needs to reach l1). "
            "The ferry starts at l2 and is empty."
        ),
        "nl_agnostic": (
            "Three docking points: l1, l2, l3. "
            "Vehicles car1 and car2 at l1, both must reach l3. "
            "Vehicle car3 at l3 must reach l1. "
            "Transport vessel starts at l2, carrying nothing."
        ),
        "reference_pddl": """(define (problem ferry-p6)
  (:domain ferry)
  (:objects car1 car2 car3 l1 l2 l3)
  (:init
    (at-ferry l2)
    (at car1 l1)
    (at car2 l1)
    (at car3 l3)
    (empty-ferry)
  )
  (:goal (and (at car1 l3) (at car2 l3) (at car3 l1)))
)""",
    },
    {
        "id": "fe_p7",
        "nl": (
            "Four locations: l1, l2, l3, l4. "
            "Car1 is at l1 (needs to reach l4). "
            "Car2 is at l2 (needs to reach l4). "
            "Car3 is at l4 (needs to reach l1). "
            "Car4 is at l3 (needs to reach l2). "
            "The ferry starts at l1 and is empty."
        ),
        "nl_agnostic": (
            "Four docking points: l1, l2, l3, l4. "
            "Vehicle car1 at l1 → l4; car2 at l2 → l4; car3 at l4 → l1; car4 at l3 → l2. "
            "Transport vessel starts at l1, carrying nothing."
        ),
        "reference_pddl": """(define (problem ferry-p7)
  (:domain ferry)
  (:objects car1 car2 car3 car4 l1 l2 l3 l4)
  (:init
    (at-ferry l1)
    (at car1 l1)
    (at car2 l2)
    (at car3 l4)
    (at car4 l3)
    (empty-ferry)
  )
  (:goal (and (at car1 l4) (at car2 l4) (at car3 l1) (at car4 l2)))
)""",
    },
    {
        "id": "fe_p8",
        "nl": (
            "Three locations: l1, l2, l3. "
            "Five cars: car1 and car2 are at l1 (need to reach l3). "
            "Car3 is at l2 (needs to reach l1). "
            "Car4 and car5 are at l3 (car4 needs to reach l1, car5 needs to reach l2). "
            "The ferry starts at l3 and is empty."
        ),
        "nl_agnostic": (
            "Three docking points: l1, l2, l3. Five vehicles. "
            "car1 and car2 at l1 → l3; car3 at l2 → l1; car4 at l3 → l1; car5 at l3 → l2. "
            "Transport vessel starts at l3, carrying nothing."
        ),
        "reference_pddl": """(define (problem ferry-p8)
  (:domain ferry)
  (:objects car1 car2 car3 car4 car5 l1 l2 l3)
  (:init
    (at-ferry l3)
    (at car1 l1)
    (at car2 l1)
    (at car3 l2)
    (at car4 l3)
    (at car5 l3)
    (empty-ferry)
  )
  (:goal (and
    (at car1 l3) (at car2 l3)
    (at car3 l1)
    (at car4 l1) (at car5 l2)))
)""",
    },
]
