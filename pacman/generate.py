#!/usr/bin/env python

import argparse
from collections import defaultdict

import ghostAgents
from layout import Layout
from game import Directions, Actions

def backslash_join (x, tab = 0):

    return "\n".join([(' '*tab) + y for y in x])

def loc_name(x):
    return f"loc-{int(x[0])}-{int(x[1])}"

def get_probabilistic_effect (effects, tab):
    if len(effects) == 1:
        return " "*tab + effects[0][1]
    return (" "*tab + "(probabilistic \n"
            + backslash_join([f"{prob} {effect}" for (prob, effect) in effects], tab=tab+4) +
            '\n' + " "*tab + ")")

def generate(
    layout : Layout
) -> (str, str):

    CONNECTED_GHOST_PREDICATES = []
    MOVE_GHOST_ACTIONS = []
    OBJECTS = []
    INITIAL_STATE = []
    GOAL = []
    
    positions = layout.getLegalPositions()
    ghostAgent = ghostAgents.RandomGhost()

    probability_distributions = set()
    sources_to_distributions = defaultdict(list)
    sources_to_targets = defaultdict(list)

    directions = [Directions.NORTH, Directions.SOUTH, Directions.EAST, Directions.WEST, Directions.STOP]

    OBJECTS.append(" ".join(directions) + " - direction")
    OBJECTS.append(" ".join(map(loc_name, positions)) + " - location")

    for position in positions:
        #INITIAL_STATE.append(f"(CONNECTED_PACMAN {loc_name(position)} {loc_name(position)})")

        for dir in directions:
            dist = ghostAgent.getDistribution(layout, position, dir)
            sorted_dist = sorted(dist.items(), key=lambda x: x[1], reverse=True)
            dist_probabilities = tuple(list([prob for (act, prob) in sorted_dist]))
            sources_to_distributions[(position, dir)] = dist_probabilities

            if Actions.getSuccessor(position, dir) in positions:
                INITIAL_STATE.append(f"(CONNECTED_PACMAN {loc_name(position)} {loc_name(Actions.getSuccessor(position, dir))})")

            Actions.getSuccessor(position, dir)

            probability_distributions.add(dist_probabilities)
            for (act, prob) in sorted_dist:
                new_pos = Actions.getSuccessor(position, act)
                sources_to_targets[(position, dir)].append((new_pos, act))


    probability_distributions_by_id = {id : prob_dist for id, prob_dist in enumerate(sorted(probability_distributions, reverse=True), start=1)}
    id_map = { prob_dist : id for id, prob_dist in probability_distributions_by_id.items()}

    sources_to_distribution_ids = {src : id_map [prob] for (src, prob) in sources_to_distributions.items()}

    for (probability_distribution_id, prob_dist) in probability_distributions_by_id.items():
        parameters = ["?a_loc - location", "?a_dir - direction"]
        parameter_names = ["?a_loc", "?a_dir"]
        probabilistic_effects = []
        for i in range(1, len(prob_dist) + 1):
            parameters += [f"?x{i} - location", f"?d{i} - direction"]
            parameter_names += [f"?x{i}", f"?d{i}"]
            probabilistic_effects += [(f"{prob_dist[i-1]}", f"(and (at ?a ?x{i}) (looking ?a ?d{i}))")]

        CONNECTED_GHOST_PREDICATES.append(f"(CONNECTED_GHOST_{probability_distribution_id} {' '.join(parameters)})")

        MOVE_GHOST_ACTIONS.append(f"""
(:action move-ghost-{probability_distribution_id}
    :parameters (?a - ghost ?p - pacmanagent ?p_loc - location {' '.join(parameters)})
    :precondition (and
        (CONNECTED_GHOST_{probability_distribution_id} {' '.join(parameter_names)})
        (at ?a ?a_loc)
        (at ?p ?p_loc)
        (not (= ?a_loc ?p_loc))
        (looking ?a ?a_dir)
        (turn ?a)
    )
    :effect (and  
        (not (turn ?a)) (turn_check_kill ?a)
        (not (at ?a ?a_loc)) (not (looking ?a ?a_dir))
{get_probabilistic_effect (probabilistic_effects, tab=8)}
    )
)
""")

    for (pos_src, dir_src), target in sources_to_targets.items():
        parameter_list = [f"{loc_name(pos_src)}", f"{dir_src}"]
        for (pos_target, dir_target) in target:
            parameter_list += [f"{loc_name(pos_target)}", f"{dir_target}"]

        INITIAL_STATE.append(f"(CONNECTED_GHOST_{sources_to_distribution_ids[(pos_src, dir_src)]} {' '.join(parameter_list)})")

    num_points = 0
    for position in positions:
        if layout.isFood(position):
            INITIAL_STATE.append(f"(has-point {loc_name(position)})")
            num_points += 1
            #GOAL.append(f"(not (has-point {loc_name(position)}))")

    OBJECTS += [f"num{i} - num" for i in range(num_points + 1)]
    INITIAL_STATE.append(f"(WINNING_POINTS num{num_points})")
    INITIAL_STATE.append(f"(eaten num0)")
    INITIAL_STATE += [f"(NEXT_NUMBER num{i} num{i+1})" for i in range(num_points)]
    GOAL.append(f"(eaten num{num_points})")


    INITIAL_STATE += [f"(= (lose-cost num{i}) {500 + 10*(num_points - i)})" for i in range(num_points)]
    previous_agent = None
    for i, (is_pacman, position) in enumerate(layout.agentPositions):
        if is_pacman:
            agent_name = f"pacman{i}" if i > 0 else "pacman"
            OBJECTS.append(f"{agent_name} - pacmanagent")
        else:
            agent_name = f"ghost{i}"
            OBJECTS.append(f"{agent_name} - ghost")
            INITIAL_STATE.append(f"(looking {agent_name} {Directions.STOP})")

        INITIAL_STATE.append(f"(at {agent_name} {loc_name(position)})")


        if i == 0:
            first_agent = agent_name

        if previous_agent:
            INITIAL_STATE.append(f"(TURN_ORDER {previous_agent} {agent_name})")
        previous_agent = agent_name


    INITIAL_STATE.append(f"(TURN_ORDER {previous_agent} {first_agent})")
    INITIAL_STATE.append(f"(turn {first_agent})")
    #INITIAL_STATE.append(f"(alive)")
    # GOAL.append(f"(alive)")

    DOMAIN_TEMPLATE = f"""
(define (domain pacman)
    (:requirements :strips :typing :negative-preconditions :action-costs :probabilistic-effects)

    (:types location agent direction num - object
            pacmanagent ghost - agent)
            
    (:predicates
        (has-point ?x - location)
        (at ?a - agent ?x - location)
        (looking ?a - ghost ?d - direction)
        (turn ?a - agent)
        (turn_check_kill ?a - ghost) 
        (eaten ?x - num)
        (CONNECTED_PACMAN ?x ?y - location)
        (TURN_ORDER ?x ?y - agent)
        (NEXT_NUMBER ?x ?y - num)
        (WINNING_POINTS ?x - num)
{backslash_join(CONNECTED_GHOST_PREDICATES, tab=8)}
       )

    (:functions (total-cost) - number
                (lose-cost ?x - num) - number
    )

    (:action move-pacman
        :parameters (?a - pacmanagent ?old_loc ?new_loc - location ?next_agent - agent)
        :precondition (and
            (CONNECTED_PACMAN ?old_loc ?new_loc)
            (at ?a ?old_loc)
            (turn ?a)
            (TURN_ORDER ?a ?next_agent)
            (not (has-point ?new_loc))
        )
        :effect (and (increase (total-cost) 1)
            (not (at ?a ?old_loc)) (at ?a ?new_loc)
            (not (turn ?a))  (turn ?next_agent)
        )
    )
    
    (:action move-pacman-eat
        :parameters (?a - pacmanagent ?x ?y - location ?n - agent ?cur_points ?next_points - num)
        :precondition (and
            (CONNECTED_PACMAN ?x ?y)
            (at ?a ?x)
            (turn ?a)
            (TURN_ORDER ?a ?n)
            (eaten ?cur_points)
            (NEXT_NUMBER ?cur_points ?next_points)
            (has-point ?y)
        )
        :effect (and (increase (total-cost) 1)
            (not (at ?a ?x)) (at ?a ?y)
            (not (turn ?a))  (turn ?n)
            (not (eaten ?cur_points)) (eaten ?next_points)
            (not (has-point ?y))
        )
    )

{backslash_join(MOVE_GHOST_ACTIONS, tab=4)}

    (:action kill-pacman
        :parameters (?a - ghost ?p - pacmanagent ?x - location ?curr_points ?win - num)
        :precondition (and
            (at ?a ?x)
            (at ?p ?x)
            (eaten ?curr_points)
            (WINNING_POINTS ?win)
            (not (WINNING_POINTS ?curr_points))
        )
        :effect (and (increase (total-cost) (lose-cost ?curr_points))
                     (not (eaten ?curr_points)) (eaten ?win)
        )
    )

    (:action pass-turn
        :parameters (?a - ghost ?p - pacmanagent ?x ?y - location ?n - agent)
        :precondition (and
            (at ?a ?x)
            (not (= ?x ?y))
            (at ?p ?y)
            (turn_check_kill ?a)
            (TURN_ORDER ?a ?n)
        )
        :effect (and 
            (not (turn_check_kill ?a)) (turn ?n)
        )
    )
)
    """
    PROBLEM_TEMPLATE = f"""
(define (problem pacman-problem)
    (:domain pacman)
    (:objects
{backslash_join(OBJECTS, tab=8)}
    )
    (:init
{backslash_join(INITIAL_STATE, tab=8)}
    (= (total-cost) 0)
    )
    (:goal {backslash_join(GOAL)})

    (:metric minimize (total-cost))
)"""
#    {backslash_join(GOAL, tab=8)}

    return DOMAIN_TEMPLATE, PROBLEM_TEMPLATE

def main():
    p = argparse.ArgumentParser()
    p.add_argument("layout", type=str, help="Layout file")
    args = p.parse_args()

    with open(args.layout) as f:
        layout = Layout(f.read().splitlines())

        domain, problem = generate(layout)
        with open('domain.pddl', 'w') as f:
            f.write(domain)

        with open('problem.pddl', 'w') as f:
            f.write(problem)

if __name__ == "__main__":
    main()
