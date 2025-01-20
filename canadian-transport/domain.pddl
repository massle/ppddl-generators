;; Transport sequential
;;

(define (domain canadian-transport)
  (:requirements :typing :action-costs)
  (:types
        location target locatable - object
        vehicle package - locatable
        capacity-number - object
  )

  (:predicates 
     (at ?x - locatable ?v - location)
     (in ?x - package ?v - vehicle)
     (capacity ?v - vehicle ?s1 - capacity-number)
     (capacity-predecessor ?s1 ?s2 - capacity-number)

     (road_blocked ?l1 ?l2 - location)
     (road_free ?l1 ?l2 - location)
     (road_unknown ?l1 ?l2 - location)

    (plow)
  )

  (:functions
     (road-length ?l1 ?l2 - location) - number
     (plow-cost ?l1 ?l2 - location) - number
     (total-cost) - number
  )

  (:action request-plow-symmetric
    :parameters (?l1 ?l2 - location) 
    :precondition (and
        (plow)
        (road_unknown ?l1 ?l2)
        (road_unknown ?l2 ?l1)
    )
    :effect (and
        (not (road_unknown ?l1 ?l2))
        (not (road_unknown ?l2 ?l1))
        (road_free ?l1 ?l2)
        (road_free ?l2 ?l1)
        (increase (total-cost) (plow-cost ?l1 ?l2))
    )
  )

  (:action request-plow-asymmetric
    :parameters (?l1 ?l2 - location) 
    :precondition (and
        (plow)
        (road_unknown ?l1 ?l2)
        (not (road_unknown ?l2 ?l1))
    )
    :effect (and
        (not (road_unknown ?l1 ?l2))
        (road_free ?l1 ?l2)
        (increase (total-cost) (plow-cost ?l1 ?l2))
    )
  )

  (:action start-delivery
    :parameters ()
    :precondition (plow)
    :effect (and (not (plow)) (increase (total-cost) 0))
  )

  (:action inspect-road-symmetric
    :parameters (?v - vehicle ?l1 ?l2 - location)
    :precondition (and
        (not (plow))
        (at ?v ?l1)
        (road_unknown ?l1 ?l2)
        (road_unknown ?l2 ?l1)
    )
    :effect (and
        (not (road_unknown ?l1 ?l2))
        (not (road_unknown ?l2 ?l1))
        (probabilistic 
            0.8 (and (road_free ?l1 ?l2) (road_free ?l2 ?l1))
            0.2 (and (road_blocked ?l1 ?l2) (road_blocked ?l2 ?l1))
        )
        (increase (total-cost) 0)
    )
  )

  (:action inspect-road-asymmetric
    :parameters (?v - vehicle ?l1 ?l2 - location)
    :precondition (and
        (not (plow))
        (at ?v ?l1)
        (road_unknown ?l1 ?l2)
        (not (road_unknown ?l2 ?l1))
    )
    :effect (and
        (not (road_unknown ?l1 ?l2))
        (probabilistic 
            0.8 (and (road_free ?l1 ?l2))
            0.2 (and (road_blocked ?l1 ?l2))
        )
        (increase (total-cost) 0)
    )
  )

  (:action drive
    :parameters (?v - vehicle ?l1 ?l2 - location)
    :precondition (and
        (not (plow))
        (at ?v ?l1)
        (road_free ?l1 ?l2)
      )
    :effect (and
        (not (at ?v ?l1))
        (at ?v ?l2)
        (increase (total-cost) (road-length ?l1 ?l2))
      )
  )

 (:action pick-up
    :parameters (?v - vehicle ?l - location ?p - package ?s1 ?s2 - capacity-number)
    :precondition (and
        (not (plow))
        (at ?v ?l)
        (at ?p ?l)
        (capacity-predecessor ?s1 ?s2)
        (capacity ?v ?s2)
      )
    :effect (and
        (not (at ?p ?l))
        (in ?p ?v)
        (capacity ?v ?s1)
        (not (capacity ?v ?s2))
        (increase (total-cost) 1)
      )
  )

  (:action drop
    :parameters (?v - vehicle ?l - location ?p - package ?s1 ?s2 - capacity-number)
    :precondition (and
        (not (plow))
        (at ?v ?l)
        (in ?p ?v)
        (capacity-predecessor ?s1 ?s2)
        (capacity ?v ?s1)
      )
    :effect (and
        (not (in ?p ?v))
        (at ?p ?l)
        (capacity ?v ?s2)
        (not (capacity ?v ?s1))
        (increase (total-cost) 1)
      )
  )

)
