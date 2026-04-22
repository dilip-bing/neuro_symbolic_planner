; Ferry Domain — IPC variant (untyped STRIPS)
;
; A ferry transports cars between locations (e.g. river banks).
; The ferry carries exactly ONE car at a time.
;
; COMMON LLM FAILURE MODES (this domain is rarely in training data):
;   - (on ?car ?ferry)   wrong arity — should be (on ?car)  [0-arg ferry implicit]
;   - 'carry' or 'loaded' instead of 'on'
;   - 'empty' instead of 'empty-ferry'
;   - (at-ferry ?from ?to) wrong arity — should be (at-ferry ?loc) [1-arg]
;   - typed :objects when domain is untyped STRIPS
;   - missing (empty-ferry) in :init
;
; Predicates:
;   (at-ferry ?loc)   — ferry is at location ?loc
;   (at ?obj ?loc)    — car ?obj is at location ?loc
;   (on ?car)         — car ?car is currently on the ferry  [NOTE: 1-arg only]
;   (empty-ferry)     — the ferry is carrying no car        [NOTE: 0-arg]

(define (domain ferry)
  (:requirements :strips)

  (:predicates
    (at-ferry ?loc)      ; ferry position
    (at ?obj ?loc)       ; car position
    (on ?car)            ; car is aboard the ferry (1-arg — no ferry object!)
    (empty-ferry)        ; ferry holds no car (0-arg)
  )

  ; Move the ferry from one location to another (whether loaded or not)
  (:action sail
    :parameters (?from ?to)
    :precondition (and (at-ferry ?from))
    :effect (and (not (at-ferry ?from))
                 (at-ferry ?to))
  )

  ; Load a car onto the ferry (ferry must be empty and at same location as car)
  (:action board
    :parameters (?car ?loc)
    :precondition (and (at ?car ?loc)
                       (at-ferry ?loc)
                       (empty-ferry))
    :effect (and (not (at ?car ?loc))
                 (not (empty-ferry))
                 (on ?car))
  )

  ; Unload a car from the ferry at current location
  (:action debark
    :parameters (?car ?loc)
    :precondition (and (on ?car)
                       (at-ferry ?loc))
    :effect (and (not (on ?car))
                 (at ?car ?loc)
                 (empty-ferry))
  )
)
