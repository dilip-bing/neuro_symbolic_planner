; Blocksworld Domain - Standard 4-operator version (IPC)
(define (domain blocksworld)
  (:requirements :strips)
  (:predicates
    (on ?x ?y)         ; block x is on block y
    (ontable ?x)       ; block x is on the table
    (clear ?x)         ; block x has nothing on top
    (handempty)        ; the robot hand is empty
    (holding ?x)       ; the robot is holding block x
  )

  ; Pick up a block from the table
  (:action pickup
    :parameters (?x)
    :precondition (and (clear ?x) (ontable ?x) (handempty))
    :effect (and (not (ontable ?x))
                 (not (clear ?x))
                 (not (handempty))
                 (holding ?x))
  )

  ; Put down a block onto the table
  (:action putdown
    :parameters (?x)
    :precondition (holding ?x)
    :effect (and (not (holding ?x))
                 (clear ?x)
                 (handempty)
                 (ontable ?x))
  )

  ; Stack a block on top of another block
  (:action stack
    :parameters (?x ?y)
    :precondition (and (holding ?x) (clear ?y))
    :effect (and (not (holding ?x))
                 (not (clear ?y))
                 (clear ?x)
                 (handempty)
                 (on ?x ?y))
  )

  ; Unstack a block from another block
  (:action unstack
    :parameters (?x ?y)
    :precondition (and (on ?x ?y) (clear ?x) (handempty))
    :effect (and (holding ?x)
                 (clear ?y)
                 (not (clear ?x))
                 (not (handempty))
                 (not (on ?x ?y)))
  )
)
