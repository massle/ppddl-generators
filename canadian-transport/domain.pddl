;; Transport sequential
;;

(define (domain canadian-transport)
  (:requirements :typing :action-costs :negative-preconditions)

  (:types
        location target locatable - object
        vehicle package - locatable
        capacity-number - object
        road-group - object
  )

  (:constants END-GROUP - road-group)

  (:predicates 
     (at ?x - locatable ?v - location)
     (in ?x - package ?v - vehicle)
     (capacity ?v - vehicle ?s1 - capacity-number)
     (capacity-predecessor ?s1 ?s2 - capacity-number)

     (road_blocked ?l1 ?l2 - location)
     (road_free ?l1 ?l2 - location)
     (road_unknown ?l1 ?l2 - location)

    (ROAD_GROUP ?l1 ?l2 - location ?g - road-group)
    (road_group_plown ?g - road-group)
    (road_group_not_plown ?g - road-group)

    (plow)
    (current_group ?g - road-group)
    (NEXT_GROUP ?g1 ?g2 - road-group)
  )

  (:functions
     (road-length ?l1 ?l2 - location) - number
     (plow-cost ?g - road-group) - number
     (total-cost) - number
  )

  (:action plow-roads
    :parameters (?g ?gg - road-group) 
    :precondition (and
        (plow)
        (current_group ?g)
        (NEXT_GROUP ?g ?gg)
    )
    :effect (and
        (not (current_group ?g))
        (current_group ?gg)
        (road_group_plown ?g)
        (increase (total-cost) (plow-cost ?g))
    )
  )

  (:action dont-plow-roads
    :parameters (?g ?gg - road-group) 
    :precondition (and
        (plow)
        (current_group ?g)
        (NEXT_GROUP ?g ?gg)
    )
    :effect (and
        (not (current_group ?g))
        (current_group ?gg)
        (road_group_not_plown ?g)
        (increase (total-cost) 0)
    )
  )

  (:action start-delivery
    :parameters ()
    :precondition (and (plow) (current_group END-GROUP))
    :effect (and (not (plow)) (not (current_group END-GROUP)) (increase (total-cost) 0))
  )

  (:action inspect-road
    :parameters (?v - vehicle ?l1 ?l2 - location ?g - road-group)
    :precondition (and
        (not (plow))
        (at ?v ?l1)
        (road_unknown ?l1 ?l2)
        (ROAD_GROUP ?l1 ?l2 ?g)
        (road_group_not_plown ?g)
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

  (:action inspect-plown-road
    :parameters (?v - vehicle ?l1 ?l2 - location ?g - road-group)
    :precondition (and
        (not (plow))
        (at ?v ?l1)
        (road_unknown ?l1 ?l2)
        (ROAD_GROUP ?l1 ?l2 ?g)
        (road_group_plown ?g)
    )
    :effect (and
        (not (road_unknown ?l1 ?l2))
        (road_free ?l1 ?l2)
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
