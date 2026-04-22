; Gripper Domain - IPC STRIPS version (untyped)
; A robot with two grippers moves between rooms carrying balls.
; Predicates use unambiguous names (at-robby vs at) to stress-test LLM disambiguation.
(define (domain gripper-strips)
  (:requirements :strips)
  (:predicates
    (room ?r)           ; r is a room
    (ball ?b)           ; b is a ball
    (gripper ?g)        ; g is a gripper
    (at-robby ?r)       ; robot is in room r
    (at ?b ?r)          ; ball b is in room r
    (free ?g)           ; gripper g is empty
    (carry ?o ?g)       ; gripper g is holding ball o
  )

  (:action move
    :parameters (?from ?to)
    :precondition (and (room ?from) (room ?to) (at-robby ?from))
    :effect (and (at-robby ?to) (not (at-robby ?from)))
  )

  (:action pick
    :parameters (?obj ?room ?gripper)
    :precondition (and (ball ?obj) (room ?room) (gripper ?gripper)
                       (at ?obj ?room) (at-robby ?room) (free ?gripper))
    :effect (and (carry ?obj ?gripper)
                 (not (at ?obj ?room))
                 (not (free ?gripper)))
  )

  (:action drop
    :parameters (?obj ?room ?gripper)
    :precondition (and (ball ?obj) (room ?room) (gripper ?gripper)
                       (carry ?obj ?gripper) (at-robby ?room))
    :effect (and (at ?obj ?room)
                 (free ?gripper)
                 (not (carry ?obj ?gripper)))
  )
)
