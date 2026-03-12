; ============================================================
; BLOCKSWORLD BENCHMARK PROBLEMS - Phase 1 Evaluation Suite
; ============================================================
; These problems are used to evaluate the NL->PDDL generator.
; Each problem has a natural language description (in comments)
; and its ground-truth PDDL representation.
; ============================================================

; --- PROBLEM 1: Simple 2-block stack ---
; NL: "Stack block A on top of block B. Both blocks start on the table."
(define (problem bw-p1-2blocks)
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

; --- PROBLEM 2: 3-block tower ---
; NL: "Build a tower with block C on top of B, and B on top of A. All three blocks start on the table."
(define (problem bw-p2-3tower)
  (:domain blocksworld)
  (:objects a b c)
  (:init
    (ontable a)
    (ontable b)
    (ontable c)
    (clear a)
    (clear b)
    (clear c)
    (handempty)
  )
  (:goal (and (on c b) (on b a) (ontable a)))
)

; --- PROBLEM 3: Reverse a stack ---
; NL: "Blocks are currently stacked as A on top of B on top of C (from top to bottom). 
;      Reverse the stack so C is on top of B, and B is on top of A."
(define (problem bw-p3-reverse3)
  (:domain blocksworld)
  (:objects a b c)
  (:init
    (on a b)
    (on b c)
    (ontable c)
    (clear a)
    (handempty)
  )
  (:goal (and (on c b) (on b a) (ontable a)))
)

; --- PROBLEM 4: 4-block stack construction ---
; NL: "Stack all four blocks into a single tower: D on C, C on B, B on A, with A on the table. All blocks start on the table."
(define (problem bw-p4-4tower)
  (:domain blocksworld)
  (:objects a b c d)
  (:init
    (ontable a)
    (ontable b)
    (ontable c)
    (ontable d)
    (clear a)
    (clear b)
    (clear c)
    (clear d)
    (handempty)
  )
  (:goal (and (on d c) (on c b) (on b a) (ontable a)))
)

; --- PROBLEM 5: Swap two blocks ---
; NL: "Block A is on top of block B. Move A off B and place B on top of A instead."
(define (problem bw-p5-swap)
  (:domain blocksworld)
  (:objects a b)
  (:init
    (on a b)
    (ontable b)
    (clear a)
    (handempty)
  )
  (:goal (and (on b a) (ontable a)))
)

; --- PROBLEM 6: 5-block reverse stack (harder) ---
; NL: "Stack 5 blocks in reverse order: blocks A,B,C,D,E are all on the table. 
;      Build a tower with E on D, D on C, C on B, B on A."
(define (problem bw-p6-5tower)
  (:domain blocksworld)
  (:objects a b c d e)
  (:init
    (ontable a)
    (ontable b)
    (ontable c)
    (ontable d)
    (ontable e)
    (clear a)
    (clear b)
    (clear c)
    (clear d)
    (clear e)
    (handempty)
  )
  (:goal (and (on e d) (on d c) (on c b) (on b a) (ontable a)))
)
