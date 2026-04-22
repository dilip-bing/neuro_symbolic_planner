"""
Logistics benchmark problems for Phase 2.
Domain: packages transported by trucks (within cities) and airplanes (between cities).

Base 6 problems + 5 hard problems (log_p7-log_p11).

Key LLM challenge axes:
- Must include type predicates (package, truck, airplane, location, airport, city,
  in-city) in :init — the most common failure point the critic should catch.
- Multi-city chains requiring both intra-city truck delivery AND inter-city flights.
- Multiple packages going in opposite directions simultaneously.
- Hyphenated object names (e.g. depot-bos, downtown-chi) must not be mangled.
"""

PROBLEMS = [
    {
        "id": "log_p1",
        "nl": (
            "There is one package (pkg1) at location downtown in city Boston. "
            "A truck (truck1) is also at downtown. "
            "Deliver pkg1 to location airport-bos, also in Boston."
        ),
        "nl_agnostic": (
            "One shipment (pkg1) is at site downtown inside region Boston. "
            "A ground vehicle (truck1) is also at downtown. "
            "Deliver pkg1 to site airport-bos, also inside Boston."
        ),
        "reference_pddl": """(define (problem logistics-p1)
  (:domain logistics-strips)
  (:objects pkg1 truck1 downtown airport-bos boston)
  (:init
    (package pkg1) (truck truck1)
    (location downtown) (location airport-bos) (airport airport-bos)
    (city boston)
    (in-city downtown boston) (in-city airport-bos boston)
    (at pkg1 downtown) (at truck1 downtown)
  )
  (:goal (and (at pkg1 airport-bos)))
)""",
    },
    {
        "id": "log_p2",
        "nl": (
            "Package pkg1 is at location depot in city New York. "
            "Truck truck1 is at location warehouse, also in New York. "
            "Move pkg1 to the warehouse location."
        ),
        "nl_agnostic": (
            "Cargo pkg1 is at site depot inside region New York. "
            "Ground vehicle truck1 is at site warehouse, also inside New York. "
            "Move pkg1 to the warehouse."
        ),
        "reference_pddl": """(define (problem logistics-p2)
  (:domain logistics-strips)
  (:objects pkg1 truck1 depot warehouse newyork)
  (:init
    (package pkg1) (truck truck1)
    (location depot) (location warehouse)
    (city newyork)
    (in-city depot newyork) (in-city warehouse newyork)
    (at pkg1 depot) (at truck1 warehouse)
  )
  (:goal (and (at pkg1 warehouse)))
)""",
    },
    {
        "id": "log_p3",
        "nl": (
            "Package pkg1 is at airport JFK in New York. "
            "Airplane plane1 is at JFK. Airport LAX is in Los Angeles. "
            "Fly pkg1 from JFK to LAX."
        ),
        "nl_agnostic": (
            "Cargo pkg1 is at air terminal jfk inside region New York. "
            "Aircraft plane1 is at jfk. Air terminal lax is inside region Los Angeles. "
            "Transport pkg1 from jfk to lax by air."
        ),
        "reference_pddl": """(define (problem logistics-p3)
  (:domain logistics-strips)
  (:objects pkg1 plane1 jfk lax newyork losangeles)
  (:init
    (package pkg1) (airplane plane1)
    (airport jfk) (airport lax)
    (location jfk) (location lax)
    (city newyork) (city losangeles)
    (in-city jfk newyork) (in-city lax losangeles)
    (at pkg1 jfk) (at plane1 jfk)
  )
  (:goal (and (at pkg1 lax)))
)""",
    },
    {
        "id": "log_p4",
        "nl": (
            "Package pkg1 is at downtown Chicago. Truck truck1 is also at downtown Chicago. "
            "Chicago has an airport called ohare. "
            "Deliver pkg1 to ohare airport so it can be loaded onto a plane."
        ),
        "nl_agnostic": (
            "Cargo pkg1 is at site downtown inside region Chicago. "
            "Ground vehicle truck1 is also at downtown. "
            "Region Chicago has an air terminal called ohare. "
            "Move pkg1 to the ohare terminal."
        ),
        "reference_pddl": """(define (problem logistics-p4)
  (:domain logistics-strips)
  (:objects pkg1 truck1 downtown ohare chicago)
  (:init
    (package pkg1) (truck truck1)
    (location downtown) (location ohare) (airport ohare)
    (city chicago)
    (in-city downtown chicago) (in-city ohare chicago)
    (at pkg1 downtown) (at truck1 downtown)
  )
  (:goal (and (at pkg1 ohare)))
)""",
    },
    {
        "id": "log_p5",
        "nl": (
            "Two packages (pkg1 and pkg2) are at location hub in city Dallas. "
            "Two trucks (truck1, truck2) are also at hub. "
            "Deliver pkg1 to location east-dallas and pkg2 to location west-dallas. "
            "Both destinations are in Dallas."
        ),
        "nl_agnostic": (
            "Two shipments (pkg1, pkg2) are at site hub inside region Dallas. "
            "Two ground vehicles (truck1, truck2) are also at hub. "
            "Deliver pkg1 to site east-dallas and pkg2 to site west-dallas, both inside Dallas."
        ),
        "reference_pddl": """(define (problem logistics-p5)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 truck1 truck2 hub east-dallas west-dallas dallas)
  (:init
    (package pkg1) (package pkg2)
    (truck truck1) (truck truck2)
    (location hub) (location east-dallas) (location west-dallas)
    (city dallas)
    (in-city hub dallas) (in-city east-dallas dallas) (in-city west-dallas dallas)
    (at pkg1 hub) (at pkg2 hub)
    (at truck1 hub) (at truck2 hub)
  )
  (:goal (and (at pkg1 east-dallas) (at pkg2 west-dallas)))
)""",
    },
    {
        "id": "log_p6",
        "nl": (
            "Package pkg1 starts at location depot in city Boston. "
            "There is a truck (truck1) at depot. Airport logan is in Boston. "
            "Airplane plane1 is at logan. Airport sfo is in San Francisco. "
            "Deliver pkg1 to sfo airport in San Francisco."
        ),
        "nl_agnostic": (
            "Cargo pkg1 is at site depot inside region Boston. "
            "Ground vehicle truck1 is at depot. Air terminal logan is in Boston; aircraft plane1 is at logan. "
            "Air terminal sfo is in region San Francisco. "
            "Deliver pkg1 to sfo."
        ),
        "reference_pddl": """(define (problem logistics-p6)
  (:domain logistics-strips)
  (:objects pkg1 truck1 plane1 depot logan sfo boston sanfrancisco)
  (:init
    (package pkg1) (truck truck1) (airplane plane1)
    (location depot) (location logan) (location sfo)
    (airport logan) (airport sfo)
    (city boston) (city sanfrancisco)
    (in-city depot boston) (in-city logan boston)
    (in-city sfo sanfrancisco)
    (at pkg1 depot) (at truck1 depot) (at plane1 logan)
  )
  (:goal (and (at pkg1 sfo)))
)""",
    },
    # ── Hard problems (Phase 2 — multi-city chains, opposing directions) ──────
    {
        "id": "log_p7",
        "nl": (
            "Two cities: Boston and Chicago. "
            "Package pkg1 is at depot-bos in Boston; package pkg2 is at warehouse-chi in Chicago. "
            "Truck1 is at depot-bos; truck2 is at warehouse-chi. "
            "Airplane plane1 is at logan-bos (Boston airport); plane2 is at ohare-chi (Chicago airport). "
            "Send pkg1 to Chicago (deliver to warehouse-chi) and pkg2 to Boston (deliver to depot-bos). "
            "Both airports are both a location and an airport."
        ),
        "nl_agnostic": (
            "Two regions: Boston and Chicago. "
            "Cargo pkg1 is at site depot-bos in Boston; cargo pkg2 is at site warehouse-chi in Chicago. "
            "Ground vehicle truck1 is at depot-bos; truck2 is at warehouse-chi. "
            "Aircraft plane1 is at air terminal logan-bos (Boston); plane2 is at air terminal ohare-chi (Chicago). "
            "Send pkg1 to warehouse-chi in Chicago and pkg2 to depot-bos in Boston."
        ),
        "reference_pddl": """(define (problem logistics-p7)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 truck1 truck2 plane1 plane2
            depot-bos logan-bos warehouse-chi ohare-chi
            boston chicago)
  (:init
    (package pkg1) (package pkg2)
    (truck truck1) (truck truck2)
    (airplane plane1) (airplane plane2)
    (location depot-bos) (location logan-bos) (airport logan-bos)
    (location warehouse-chi) (location ohare-chi) (airport ohare-chi)
    (city boston) (city chicago)
    (in-city depot-bos boston) (in-city logan-bos boston)
    (in-city warehouse-chi chicago) (in-city ohare-chi chicago)
    (at pkg1 depot-bos) (at pkg2 warehouse-chi)
    (at truck1 depot-bos) (at truck2 warehouse-chi)
    (at plane1 logan-bos) (at plane2 ohare-chi)
  )
  (:goal (and (at pkg1 warehouse-chi) (at pkg2 depot-bos)))
)""",
    },
    {
        "id": "log_p8",
        "nl": (
            "Three cities: Boston, Chicago, and Los Angeles. "
            "Package pkg1 starts at downtown-boston in Boston. "
            "Truck1 is at downtown-boston; airplane plane1 is at Logan (Boston airport). "
            "In Chicago: truck2 is at downtown-chicago; airplane plane2 is at O'Hare airport. "
            "In Los Angeles: truck3 is at downtown-la; LAX is the LA airport. "
            "Deliver pkg1 all the way to downtown-la in Los Angeles "
            "(it must be trucked to Logan, flown to O'Hare, trucked to downtown-chicago, "
            "flown to LAX, then trucked to downtown-la)."
        ),
        "nl_agnostic": (
            "Three regions: Boston, Chicago, Los Angeles. "
            "Cargo pkg1 starts at site downtown-boston in Boston. "
            "Ground vehicle truck1 at downtown-boston; aircraft plane1 at air terminal logan (Boston). "
            "In Chicago: truck2 at downtown-chicago; plane2 at air terminal ohare. "
            "In Los Angeles: truck3 at downtown-la; air terminal lax. "
            "Ship pkg1 to downtown-la (multi-hop: ground → air → ground → air → ground)."
        ),
        "reference_pddl": """(define (problem logistics-p8)
  (:domain logistics-strips)
  (:objects pkg1 truck1 truck2 truck3 plane1 plane2
            downtown-boston logan downtown-chicago ohare downtown-la lax
            boston chicago losangeles)
  (:init
    (package pkg1)
    (truck truck1) (truck truck2) (truck truck3)
    (airplane plane1) (airplane plane2)
    (location downtown-boston) (location logan) (airport logan)
    (location downtown-chicago) (location ohare) (airport ohare)
    (location downtown-la) (location lax) (airport lax)
    (city boston) (city chicago) (city losangeles)
    (in-city downtown-boston boston) (in-city logan boston)
    (in-city downtown-chicago chicago) (in-city ohare chicago)
    (in-city downtown-la losangeles) (in-city lax losangeles)
    (at pkg1 downtown-boston)
    (at truck1 downtown-boston) (at truck2 downtown-chicago) (at truck3 downtown-la)
    (at plane1 logan) (at plane2 ohare)
  )
  (:goal (and (at pkg1 downtown-la)))
)""",
    },
    {
        "id": "log_p9",
        "nl": (
            "Three cities: Boston, Chicago, Dallas. "
            "Pkg1 is at downtown-boston (Boston) and must be delivered to downtown-dallas (Dallas). "
            "Pkg2 is at downtown-chicago (Chicago) and must go to downtown-boston (Boston). "
            "Pkg3 is at downtown-dallas (Dallas) and must go to downtown-chicago (Chicago). "
            "Trucks: truck1 at downtown-boston, truck2 at downtown-chicago, truck3 at downtown-dallas. "
            "Planes: plane1 at logan (Boston airport), plane2 at ohare (Chicago airport), "
            "plane3 at dfw (Dallas airport)."
        ),
        "nl_agnostic": (
            "Three regions: Boston, Chicago, Dallas. "
            "Cargo pkg1 at downtown-boston → must reach downtown-dallas. "
            "Cargo pkg2 at downtown-chicago → must reach downtown-boston. "
            "Cargo pkg3 at downtown-dallas → must reach downtown-chicago. "
            "Ground vehicles: truck1 at downtown-boston, truck2 at downtown-chicago, truck3 at downtown-dallas. "
            "Aircraft: plane1 at air terminal logan (Boston), plane2 at ohare (Chicago), plane3 at dfw (Dallas)."
        ),
        "reference_pddl": """(define (problem logistics-p9)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 pkg3 truck1 truck2 truck3 plane1 plane2 plane3
            downtown-boston logan downtown-chicago ohare downtown-dallas dfw
            boston chicago dallas)
  (:init
    (package pkg1) (package pkg2) (package pkg3)
    (truck truck1) (truck truck2) (truck truck3)
    (airplane plane1) (airplane plane2) (airplane plane3)
    (location downtown-boston) (location logan) (airport logan)
    (location downtown-chicago) (location ohare) (airport ohare)
    (location downtown-dallas) (location dfw) (airport dfw)
    (city boston) (city chicago) (city dallas)
    (in-city downtown-boston boston) (in-city logan boston)
    (in-city downtown-chicago chicago) (in-city ohare chicago)
    (in-city downtown-dallas dallas) (in-city dfw dallas)
    (at pkg1 downtown-boston) (at pkg2 downtown-chicago) (at pkg3 downtown-dallas)
    (at truck1 downtown-boston) (at truck2 downtown-chicago) (at truck3 downtown-dallas)
    (at plane1 logan) (at plane2 ohare) (at plane3 dfw)
  )
  (:goal (and
    (at pkg1 downtown-dallas) (at pkg2 downtown-boston) (at pkg3 downtown-chicago)))
)""",
    },
    {
        "id": "log_p10",
        "nl": (
            "Two cities: New York and Los Angeles. "
            "Pkg1 is at JFK airport (New York); pkg2 is at downtown-ny (New York); "
            "pkg3 is at downtown-la (Los Angeles). "
            "Truck1 is at downtown-ny; truck2 is at downtown-la. "
            "Airplane plane1 is at JFK. Airports: jfk in New York, lax in LA. "
            "Goals: deliver pkg1 to downtown-la, deliver pkg2 to jfk (stay in NY), "
            "deliver pkg3 to lax airport."
        ),
        "nl_agnostic": (
            "Two regions: New York and Los Angeles. "
            "Cargo pkg1 at air terminal jfk (New York); pkg2 at site downtown-ny; pkg3 at site downtown-la. "
            "Ground vehicles: truck1 at downtown-ny, truck2 at downtown-la. Aircraft plane1 at jfk. "
            "Deliver: pkg1 → downtown-la, pkg2 → jfk, pkg3 → air terminal lax."
        ),
        "reference_pddl": """(define (problem logistics-p10)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 pkg3 truck1 truck2 plane1
            jfk downtown-ny downtown-la lax
            newyork losangeles)
  (:init
    (package pkg1) (package pkg2) (package pkg3)
    (truck truck1) (truck truck2)
    (airplane plane1)
    (location jfk) (airport jfk) (location downtown-ny)
    (location downtown-la) (location lax) (airport lax)
    (city newyork) (city losangeles)
    (in-city jfk newyork) (in-city downtown-ny newyork)
    (in-city downtown-la losangeles) (in-city lax losangeles)
    (at pkg1 jfk) (at pkg2 downtown-ny) (at pkg3 downtown-la)
    (at truck1 downtown-ny) (at truck2 downtown-la)
    (at plane1 jfk)
  )
  (:goal (and (at pkg1 downtown-la) (at pkg2 jfk) (at pkg3 lax)))
)""",
    },
    {
        "id": "log_p11",
        "nl": (
            "Four cities: Boston, Chicago, Dallas, Los Angeles. "
            "Pkg1 is at depot-boston and must reach depot-la. "
            "Pkg2 is at depot-la and must reach depot-boston. "
            "Each city has a truck at its depot and a plane at its airport: "
            "plane1 at logan-bos (Boston), plane2 at ohare-chi (Chicago), "
            "plane3 at dfw-dal (Dallas), plane4 at lax-la (LA). "
            "Truck1 at depot-boston, truck2 at depot-chicago, "
            "truck3 at depot-dallas, truck4 at depot-la."
        ),
        "nl_agnostic": (
            "Four regions: Boston, Chicago, Dallas, Los Angeles. "
            "Cargo pkg1 at depot-boston must reach depot-la; cargo pkg2 at depot-la must reach depot-boston. "
            "Each region has a ground vehicle at its depot and an aircraft at its air terminal: "
            "plane1 at logan-bos, plane2 at ohare-chi, plane3 at dfw-dal, plane4 at lax-la. "
            "truck1 at depot-boston, truck2 at depot-chicago, truck3 at depot-dallas, truck4 at depot-la."
        ),
        "reference_pddl": """(define (problem logistics-p11)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 truck1 truck2 truck3 truck4 plane1 plane2 plane3 plane4
            depot-boston logan-bos depot-chicago ohare-chi
            depot-dallas dfw-dal depot-la lax-la
            boston chicago dallas losangeles)
  (:init
    (package pkg1) (package pkg2)
    (truck truck1) (truck truck2) (truck truck3) (truck truck4)
    (airplane plane1) (airplane plane2) (airplane plane3) (airplane plane4)
    (location depot-boston) (location logan-bos) (airport logan-bos)
    (location depot-chicago) (location ohare-chi) (airport ohare-chi)
    (location depot-dallas) (location dfw-dal) (airport dfw-dal)
    (location depot-la) (location lax-la) (airport lax-la)
    (city boston) (city chicago) (city dallas) (city losangeles)
    (in-city depot-boston boston) (in-city logan-bos boston)
    (in-city depot-chicago chicago) (in-city ohare-chi chicago)
    (in-city depot-dallas dallas) (in-city dfw-dal dallas)
    (in-city depot-la losangeles) (in-city lax-la losangeles)
    (at pkg1 depot-boston) (at pkg2 depot-la)
    (at truck1 depot-boston) (at truck2 depot-chicago)
    (at truck3 depot-dallas) (at truck4 depot-la)
    (at plane1 logan-bos) (at plane2 ohare-chi)
    (at plane3 dfw-dal) (at plane4 lax-la)
  )
  (:goal (and (at pkg1 depot-la) (at pkg2 depot-boston)))
)""",
    },
    # ── Partial-specification problems (Phase 2 ablation) ─────────────────────
    # Goal: only one package has a specified destination; the others must stay
    # put.  Common LLM failure modes:
    #   • GOAL_SEMANTIC: invents movements for unconstrained packages
    #   • GOAL_SEMANTIC: over-specifies goal by adding (at pkg2 current-loc) when
    #     the problem says nothing about pkg2
    {
        "id": "log_p12",
        "nl": (
            "Two packages: pkg1 and pkg2. "
            "pkg1 is at downtown-boston in city Boston. "
            "pkg2 is also at downtown-boston. "
            "Truck truck1 is at downtown-boston. "
            "Airport logan is in Boston; airplane plane1 is at logan. "
            "Airport jfk is in New York. "
            "Deliver pkg1 to jfk in New York. "
            "pkg2 should stay where it is — do not include it in the goal."
        ),
        "nl_agnostic": (
            "Two cargo units: pkg1 and pkg2, both at site downtown-boston inside region Boston. "
            "Ground vehicle truck1 is at downtown-boston. "
            "Air terminal logan is in Boston; aircraft plane1 at logan. "
            "Air terminal jfk is in region New York. "
            "Deliver only pkg1 to jfk. pkg2 requires no movement — do NOT include pkg2 in the goal."
        ),
        "reference_pddl": """(define (problem logistics-p12)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 truck1 plane1 downtown-boston logan jfk boston newyork)
  (:init
    (package pkg1) (package pkg2)
    (truck truck1) (airplane plane1)
    (location downtown-boston) (location logan) (airport logan)
    (location jfk) (airport jfk)
    (city boston) (city newyork)
    (in-city downtown-boston boston) (in-city logan boston)
    (in-city jfk newyork)
    (at pkg1 downtown-boston) (at pkg2 downtown-boston)
    (at truck1 downtown-boston) (at plane1 logan)
  )
  (:goal (and (at pkg1 jfk)))
)""",
    },
    {
        "id": "log_p13",
        "nl": (
            "Three packages: pkg1, pkg2, pkg3. "
            "pkg1 is at depot-chicago; pkg2 is at depot-chicago; pkg3 is at ohare-chi. "
            "Truck truck1 is at depot-chicago; airplane plane1 is at ohare-chi (Chicago airport). "
            "Airport lax is in Los Angeles. "
            "Deliver pkg1 to lax. "
            "pkg2 and pkg3 must stay where they currently are — do not move them."
        ),
        "nl_agnostic": (
            "Three cargo units: pkg1 and pkg2 at site depot-chicago; pkg3 at air terminal ohare-chi. "
            "All inside region Chicago. "
            "Ground vehicle truck1 at depot-chicago; aircraft plane1 at ohare-chi. "
            "Air terminal lax is in region Los Angeles. "
            "Deliver pkg1 to lax only. pkg2 and pkg3 must remain — do NOT include them in the goal."
        ),
        "reference_pddl": """(define (problem logistics-p13)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 pkg3 truck1 plane1 depot-chicago ohare-chi lax chicago losangeles)
  (:init
    (package pkg1) (package pkg2) (package pkg3)
    (truck truck1) (airplane plane1)
    (location depot-chicago) (location ohare-chi) (airport ohare-chi)
    (location lax) (airport lax)
    (city chicago) (city losangeles)
    (in-city depot-chicago chicago) (in-city ohare-chi chicago)
    (in-city lax losangeles)
    (at pkg1 depot-chicago) (at pkg2 depot-chicago) (at pkg3 ohare-chi)
    (at truck1 depot-chicago) (at plane1 ohare-chi)
  )
  (:goal (and (at pkg1 lax)))
)""",
    },
    {
        "id": "log_p14",
        "nl": (
            "Four packages: pkg1, pkg2, pkg3, pkg4. "
            "pkg1 and pkg2 are at depot-dallas in city Dallas; "
            "pkg3 and pkg4 are at dfw airport (Dallas airport). "
            "Truck truck1 is at depot-dallas; airplane plane1 is at dfw. "
            "Airport sfo is in San Francisco; airport jfk is in New York. "
            "Deliver pkg1 to sfo and pkg2 to jfk. "
            "pkg3 and pkg4 should stay at dfw — do not add them to the goal."
        ),
        "nl_agnostic": (
            "Four cargo units: pkg1 and pkg2 at site depot-dallas; pkg3 and pkg4 at air terminal dfw. "
            "All inside region Dallas. "
            "Ground vehicle truck1 at depot-dallas; aircraft plane1 at dfw. "
            "Air terminal sfo in region San Francisco; air terminal jfk in region New York. "
            "Deliver pkg1 to sfo and pkg2 to jfk. "
            "pkg3 and pkg4 stay at dfw — do NOT add them to the goal."
        ),
        "reference_pddl": """(define (problem logistics-p14)
  (:domain logistics-strips)
  (:objects pkg1 pkg2 pkg3 pkg4 truck1 plane1 depot-dallas dfw sfo jfk dallas sanfrancisco newyork)
  (:init
    (package pkg1) (package pkg2) (package pkg3) (package pkg4)
    (truck truck1) (airplane plane1)
    (location depot-dallas) (location dfw) (airport dfw)
    (location sfo) (airport sfo)
    (location jfk) (airport jfk)
    (city dallas) (city sanfrancisco) (city newyork)
    (in-city depot-dallas dallas) (in-city dfw dallas)
    (in-city sfo sanfrancisco)
    (in-city jfk newyork)
    (at pkg1 depot-dallas) (at pkg2 depot-dallas)
    (at pkg3 dfw) (at pkg4 dfw)
    (at truck1 depot-dallas) (at plane1 dfw)
  )
  (:goal (and (at pkg1 sfo) (at pkg2 jfk)))
)""",
    },
]
