"""
Gripper benchmark problems for Phase 2.
Domain: robot with left+right grippers moves between rooms carrying balls.

Base 6 problems + 5 hard problems (gr_p7-gr_p11).

LLM stress-test axes:
- 'at-robby' vs 'at' confusion
- Missing type predicates (room, ball, gripper) in :init
- Multi-room routing with 4-5 rooms
- 5-6 balls with heterogeneous destinations
"""

PROBLEMS = [
    {
        "id": "gr_p1",
        "nl": (
            "There is one ball (ball1) in room A. The robot is in room A with both grippers free. "
            "Move ball1 to room B."
        ),
        "nl_agnostic": (
            "An agent with two free arms is at location A. One item (item1) is at location A. "
            "Move item1 to location B."
        ),
        "reference_pddl": """(define (problem gripper-p1)
  (:domain gripper-strips)
  (:objects rooma roomb ball1 left right)
  (:init
    (room rooma) (room roomb)
    (ball ball1)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomb)))
)""",
    },
    {
        "id": "gr_p2",
        "nl": (
            "Two balls (ball1, ball2) are in room A. The robot starts in room A with both grippers free. "
            "Transport both balls to room B."
        ),
        "nl_agnostic": (
            "Two items (item1, item2) are at location A. An agent with two free arms is at location A. "
            "Transport both items to location B."
        ),
        "reference_pddl": """(define (problem gripper-p2)
  (:domain gripper-strips)
  (:objects rooma roomb ball1 ball2 left right)
  (:init
    (room rooma) (room roomb)
    (ball ball1) (ball ball2)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 rooma)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomb) (at ball2 roomb)))
)""",
    },
    {
        "id": "gr_p3",
        "nl": (
            "Ball1 is in room A, ball2 is in room B. The robot is in room A, both grippers free. "
            "Swap them: move ball1 to room B and ball2 to room A."
        ),
        "nl_agnostic": (
            "Item1 is at location A; item2 is at location B. An agent with two free arms is at location A. "
            "Swap them: move item1 to B and item2 to A."
        ),
        "reference_pddl": """(define (problem gripper-p3)
  (:domain gripper-strips)
  (:objects rooma roomb ball1 ball2 left right)
  (:init
    (room rooma) (room roomb)
    (ball ball1) (ball ball2)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 roomb)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomb) (at ball2 rooma)))
)""",
    },
    {
        "id": "gr_p4",
        "nl": (
            "There are three rooms: A, B, C. Three balls (ball1, ball2, ball3) are all in room A. "
            "The robot starts in room A with both grippers free. "
            "Deliver ball1 and ball2 to room B, and ball3 to room C."
        ),
        "nl_agnostic": (
            "Three locations: A, B, C. Items item1, item2, item3 are all at location A. "
            "An agent with two free arms is at location A. "
            "Move item1 and item2 to location B; move item3 to location C."
        ),
        "reference_pddl": """(define (problem gripper-p4)
  (:domain gripper-strips)
  (:objects rooma roomb roomc ball1 ball2 ball3 left right)
  (:init
    (room rooma) (room roomb) (room roomc)
    (ball ball1) (ball ball2) (ball ball3)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 rooma) (at ball3 rooma)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomb) (at ball2 roomb) (at ball3 roomc)))
)""",
    },
    {
        "id": "gr_p5",
        "nl": (
            "The robot is in room B. Ball1 is in room A and ball2 is in room C. "
            "Both grippers are free. Move ball1 to room C and ball2 to room A."
        ),
        "nl_agnostic": (
            "An agent with two free arms is at location B. "
            "Item1 is at location A; item2 is at location C. "
            "Move item1 to location C and item2 to location A."
        ),
        "reference_pddl": """(define (problem gripper-p5)
  (:domain gripper-strips)
  (:objects rooma roomb roomc ball1 ball2 left right)
  (:init
    (room rooma) (room roomb) (room roomc)
    (ball ball1) (ball ball2)
    (gripper left) (gripper right)
    (at-robby roomb)
    (at ball1 rooma) (at ball2 roomc)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomc) (at ball2 rooma)))
)""",
    },
    {
        "id": "gr_p6",
        "nl": (
            "Four balls (ball1 to ball4) are all in room A. The robot is in room A with both grippers free. "
            "Move all four balls to room B."
        ),
        "nl_agnostic": (
            "Four items (item1 to item4) are all at location A. "
            "An agent with two free arms is at location A. "
            "Move all four items to location B."
        ),
        "reference_pddl": """(define (problem gripper-p6)
  (:domain gripper-strips)
  (:objects rooma roomb ball1 ball2 ball3 ball4 left right)
  (:init
    (room rooma) (room roomb)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 rooma) (at ball3 rooma) (at ball4 rooma)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomb) (at ball2 roomb) (at ball3 roomb) (at ball4 roomb)))
)""",
    },
    # ── Hard problems (Phase 2 — 4 rooms, 4-6 balls, heterogeneous routing) ──
    {
        "id": "gr_p7",
        "nl": (
            "There are four rooms: A, B, C, D. "
            "Ball1 is in room A, ball2 is in room B, ball3 is in room C, ball4 is in room D. "
            "The robot is in room A with both grippers free. "
            "Swap them in reverse order: ball1 goes to room D, ball2 to room C, "
            "ball3 to room B, ball4 to room A."
        ),
        "nl_agnostic": (
            "Four locations: A, B, C, D. Item1 at A, item2 at B, item3 at C, item4 at D. "
            "An agent with two free arms is at location A. "
            "Reverse all positions: item1 → D, item2 → C, item3 → B, item4 → A."
        ),
        "reference_pddl": """(define (problem gripper-p7)
  (:domain gripper-strips)
  (:objects rooma roomb roomc roomd ball1 ball2 ball3 ball4 left right)
  (:init
    (room rooma) (room roomb) (room roomc) (room roomd)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 roomb) (at ball3 roomc) (at ball4 roomd)
    (free left) (free right)
  )
  (:goal (and (at ball1 roomd) (at ball2 roomc) (at ball3 roomb) (at ball4 rooma)))
)""",
    },
    {
        "id": "gr_p8",
        "nl": (
            "There are five rooms: A, B, C, D, E. The robot is in room C with both grippers free. "
            "Ball1 and ball2 are in room A. Ball3 and ball4 are in room B. "
            "Ball5 is in room D, ball6 is in room E. "
            "Deliver all six balls to room C."
        ),
        "nl_agnostic": (
            "Five locations: A, B, C, D, E. An agent with two free arms is at location C. "
            "Item1 and item2 are at A; item3 and item4 are at B; item5 is at D; item6 is at E. "
            "Bring all six items to location C."
        ),
        "reference_pddl": """(define (problem gripper-p8)
  (:domain gripper-strips)
  (:objects rooma roomb roomc roomd roome ball1 ball2 ball3 ball4 ball5 ball6 left right)
  (:init
    (room rooma) (room roomb) (room roomc) (room roomd) (room roome)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4) (ball ball5) (ball ball6)
    (gripper left) (gripper right)
    (at-robby roomc)
    (at ball1 rooma) (at ball2 rooma)
    (at ball3 roomb) (at ball4 roomb)
    (at ball5 roomd) (at ball6 roome)
    (free left) (free right)
  )
  (:goal (and
    (at ball1 roomc) (at ball2 roomc) (at ball3 roomc)
    (at ball4 roomc) (at ball5 roomc) (at ball6 roomc)))
)""",
    },
    {
        "id": "gr_p9",
        "nl": (
            "Four rooms: A, B, C, D. The robot starts in room B with both grippers free. "
            "Ball1, ball2, ball3 are in room A. Ball4 is in room C, ball5 is in room D. "
            "Deliver: ball1 to room C, ball2 to room D, ball3 to room B, "
            "ball4 to room A, ball5 to room B."
        ),
        "nl_agnostic": (
            "Four locations: A, B, C, D. An agent with two free arms is at location B. "
            "Item1, item2, item3 at A; item4 at C; item5 at D. "
            "Deliver: item1 → C, item2 → D, item3 → B, item4 → A, item5 → B."
        ),
        "reference_pddl": """(define (problem gripper-p9)
  (:domain gripper-strips)
  (:objects rooma roomb roomc roomd ball1 ball2 ball3 ball4 ball5 left right)
  (:init
    (room rooma) (room roomb) (room roomc) (room roomd)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4) (ball ball5)
    (gripper left) (gripper right)
    (at-robby roomb)
    (at ball1 rooma) (at ball2 rooma) (at ball3 rooma)
    (at ball4 roomc) (at ball5 roomd)
    (free left) (free right)
  )
  (:goal (and
    (at ball1 roomc) (at ball2 roomd) (at ball3 roomb)
    (at ball4 rooma) (at ball5 roomb)))
)""",
    },
    {
        "id": "gr_p10",
        "nl": (
            "Four rooms: A, B, C, D. The robot starts in room D with both grippers free. "
            "Ball1 and ball2 are in room A; ball3 and ball4 are in room B; "
            "ball5 and ball6 are in room C. "
            "Goal: move ball1 and ball6 to room D, ball2 and ball3 to room A, "
            "ball4 and ball5 to room B."
        ),
        "nl_agnostic": (
            "Four locations: A, B, C, D. An agent with two free arms is at location D. "
            "Item1 and item2 at A; item3 and item4 at B; item5 and item6 at C. "
            "Move: item1 and item6 → D, item2 and item3 → A, item4 and item5 → B."
        ),
        "reference_pddl": """(define (problem gripper-p10)
  (:domain gripper-strips)
  (:objects rooma roomb roomc roomd ball1 ball2 ball3 ball4 ball5 ball6 left right)
  (:init
    (room rooma) (room roomb) (room roomc) (room roomd)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4) (ball ball5) (ball ball6)
    (gripper left) (gripper right)
    (at-robby roomd)
    (at ball1 rooma) (at ball2 rooma)
    (at ball3 roomb) (at ball4 roomb)
    (at ball5 roomc) (at ball6 roomc)
    (free left) (free right)
  )
  (:goal (and
    (at ball1 roomd) (at ball6 roomd)
    (at ball2 rooma) (at ball3 rooma)
    (at ball4 roomb) (at ball5 roomb)))
)""",
    },
    {
        "id": "gr_p11",
        "nl": (
            "Five rooms: A, B, C, D, E. The robot starts in room A with both grippers free. "
            "Ball1 is in room A, ball2 in room B, ball3 in room C, ball4 in room D, ball5 in room E. "
            "Rotate all balls one room forward: ball1 to B, ball2 to C, ball3 to D, "
            "ball4 to E, ball5 to A."
        ),
        "nl_agnostic": (
            "Five locations: A, B, C, D, E. An agent with two free arms is at location A. "
            "Item1 at A, item2 at B, item3 at C, item4 at D, item5 at E. "
            "Rotate each item one step forward: item1 → B, item2 → C, item3 → D, item4 → E, item5 → A."
        ),
        "reference_pddl": """(define (problem gripper-p11)
  (:domain gripper-strips)
  (:objects rooma roomb roomc roomd roome ball1 ball2 ball3 ball4 ball5 left right)
  (:init
    (room rooma) (room roomb) (room roomc) (room roomd) (room roome)
    (ball ball1) (ball ball2) (ball ball3) (ball ball4) (ball ball5)
    (gripper left) (gripper right)
    (at-robby rooma)
    (at ball1 rooma) (at ball2 roomb) (at ball3 roomc) (at ball4 roomd) (at ball5 roome)
    (free left) (free right)
  )
  (:goal (and
    (at ball1 roomb) (at ball2 roomc) (at ball3 roomd)
    (at ball4 roome) (at ball5 rooma)))
)""",
    },
]
