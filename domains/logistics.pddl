; Logistics Domain - STRIPS version (untyped, IPC-compatible)
; Packages transported by trucks (within cities) and airplanes (between cities).
; Uses type-as-predicate pattern so pyperplan handles it without :typing requirement.
(define (domain logistics-strips)
  (:requirements :strips)
  (:predicates
    (package ?p)         ; p is a package
    (truck ?t)           ; t is a truck
    (airplane ?a)        ; a is an airplane
    (location ?l)        ; l is a location (city district)
    (airport ?l)         ; l is also an airport (subset of location)
    (city ?c)            ; c is a city
    (in-city ?l ?c)      ; location l is in city c
    (at ?obj ?loc)       ; object obj (package/truck/airplane) is at location loc
    (in ?pkg ?vehicle)   ; package pkg is inside vehicle (truck or airplane)
  )

  (:action load-truck
    :parameters (?pkg ?truck ?loc)
    :precondition (and (package ?pkg) (truck ?truck) (location ?loc)
                       (at ?truck ?loc) (at ?pkg ?loc))
    :effect (and (not (at ?pkg ?loc)) (in ?pkg ?truck))
  )

  (:action unload-truck
    :parameters (?pkg ?truck ?loc)
    :precondition (and (package ?pkg) (truck ?truck) (location ?loc)
                       (at ?truck ?loc) (in ?pkg ?truck))
    :effect (and (not (in ?pkg ?truck)) (at ?pkg ?loc))
  )

  (:action load-airplane
    :parameters (?pkg ?airplane ?loc)
    :precondition (and (package ?pkg) (airplane ?airplane) (airport ?loc)
                       (at ?airplane ?loc) (at ?pkg ?loc))
    :effect (and (not (at ?pkg ?loc)) (in ?pkg ?airplane))
  )

  (:action unload-airplane
    :parameters (?pkg ?airplane ?loc)
    :precondition (and (package ?pkg) (airplane ?airplane) (airport ?loc)
                       (at ?airplane ?loc) (in ?pkg ?airplane))
    :effect (and (not (in ?pkg ?airplane)) (at ?pkg ?loc))
  )

  (:action drive-truck
    :parameters (?truck ?from ?to ?city)
    :precondition (and (truck ?truck) (location ?from) (location ?to) (city ?city)
                       (at ?truck ?from) (in-city ?from ?city) (in-city ?to ?city))
    :effect (and (not (at ?truck ?from)) (at ?truck ?to))
  )

  (:action fly-airplane
    :parameters (?airplane ?from ?to)
    :precondition (and (airplane ?airplane) (airport ?from) (airport ?to)
                       (at ?airplane ?from))
    :effect (and (not (at ?airplane ?from)) (at ?airplane ?to))
  )
)
