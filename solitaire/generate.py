#!/usr/bin/env python

import argparse
import random
from fractions import Fraction

DOMAIN = """
(define (domain lucky-solitaire)
(:requirements :probabilistic-effects :typing :negative-preconditions :strips)
(:types card color)
(:predicates
    (home ?card - card ?color - color)
    (on ?card0 - card ?color0 - color ?card1 - card ?color1 - color)
    (clear ?card - card ?color - color)
    (stock ?card - card ?color - color)
    (drawn ?card - card ?color - color)
    (IS-LESS ?c0 ?c1 - card)
    (NEXT ?c0 ?c1 - card)
)
(:constants
    {0} - card
    {1} - color
)
(:action stock-to-home
    :parameters (?card ?home-card - card ?color - color)
    :precondition (and (stock ?card ?color) (not (drawn ?card ?color)) (home ?home-card ?color) (NEXT ?home-card ?card))
    :effect (and (drawn ?card ?color) (home ?card ?color) (not (home ?home-card ?color)) (increase (total-cost) 1))
)
(:action stock-to-card
    :parameters (?card - card ?color - color ?card0 - card ?color0 - color)
    :precondition (and (stock ?card ?color) (not (drawn ?card ?color)) (clear ?card0 ?color0) (IS-LESS ?card ?card0))
    :effect (and (drawn ?card ?color) (not (clear ?card0 ?color0)) (on ?card ?color ?card0 ?color0) (clear ?card ?color) (increase (total-cost) 1))
)
(:action move-to-home
    :parameters (?card ?home-card - card ?color - color ?card0 - card ?color0 - color)
    :precondition (and (on ?card ?color ?card0 ?color0) (clear ?card ?color) (home ?home-card ?color) (NEXT ?home-card ?card))
    :effect (and (home ?card ?color) (not (home ?home-card ?color)) (not (on ?card ?color ?card0 ?color0)) (clear ?card0 ?color0) (increase (total-cost) 1))
)
(:action move-to-card
    :parameters (?card - card ?color - color ?card0 - card ?color0 - color ?card1 - card ?color1 - color)
    :precondition (and (on ?card ?color ?card0 ?color0) (clear ?card1 ?color1) (IS-LESS ?card ?card1))
    :effect (and (not (on ?card ?color ?card0 ?color0)) (on ?card ?color ?card1 ?color1) (clear ?card0 ?color0) (not (clear ?card1 ?color1)) (increase (total-cost) 1))
)
(:action re-draw-free
    :parameters (?card - card ?color - color)
    :precondition (and (drawn ?card ?color) (stock ?card ?color))
    :effect (and
        (not (stock ?card ?color))
        (probabilistic
{2}
        )
        (increase (total-cost) 0)
    )
)
(:action re-draw
    :parameters (?card - card ?color - color)
    :precondition (and (not (drawn ?card ?color)) (stock ?card ?color))
    :effect (and
        (not (stock ?card ?color))
        (probabilistic
{2}
        )
        (increase (total-cost) 10)
    )
)
)
"""

PROBLEM = """
(define (problem lucky-solitaire-{num_cards}-{num_colors}-{num_stacks}-{seed})
(:domain lucky-solitaire)
(:objects
    DUMMY_COLOR - color
    {cards} - card
)
(:init
    {init}
)
(:goal (and
    {goal}
))
(:metric minimize (total-cost))
)
"""


def generate_domain(num_cards: int, num_colors: int) -> str:
    assert num_cards > 0 and num_colors > 0
    cards = [f"card{i}" for i in range(num_cards)]
    colors = [f"color{i}" for i in range(num_colors)]
    prob = Fraction(1, num_cards * num_colors)
    stock = [
        12 * " " + f"{prob} (stock card{i} color{j})"
        for i in range(num_cards)
        for j in range(num_colors)
    ]
    return DOMAIN.format(" ".join(cards), " ".join(colors), "\n".join(stock))


def generate_problem(
    num_cards: int, num_colors: int, num_stacks: int, seed: int
) -> str:
    assert (
        num_cards > 0
        and num_colors > 0
        and num_stacks >= 0
        and num_stacks < num_cards * num_colors
    )
    random.seed(seed)
    cards = ["DUMMY_CARD"] + [f"STACK{i}" for i in range(num_stacks)]
    stacks = []
    n = num_stacks
    while n > 0:
        card = random.randint(0, num_cards - 1)
        color = random.randint(0, num_colors - 1)
        if (card, color) in stacks:
            continue
        stacks.append((card, color))
        n -= 1
    init = (
        [f"(home DUMMY_CARD color{i})" for i in range(num_colors)]
        + [
            "(drawn DUMMY_CARD DUMMY_COLOR)",
            "(stock DUMMY_CARD DUMMY_COLOR)",
            "(NEXT DUMMY_CARD card0)",
        ]
        + [f"(NEXT card{i} card{i+1})" for i in range(num_cards - 1)]
        + [
            f"(IS-LESS card{i} card{j})"
            for i in range(num_cards - 1)
            for j in range(i + 1, num_cards)
        ]
        + [
            f"(on card{i} color{j} STACK{k} DUMMY_COLOR)"
            for (k, (i, j)) in enumerate(stacks)
        ]
        + [f"(clear card{i} color{j})" for (i, j) in stacks]
        + [f"(drawn card{i} color{j})" for (i, j) in stacks]
    )
    goal = [f"(home card{num_cards - 1} color{i})" for i in range(num_colors)]
    return PROBLEM.format(
        num_cards=num_cards,
        num_colors=num_colors,
        num_stacks=num_stacks,
        seed=seed,
        cards=" ".join(cards),
        init="\n    ".join(init),
        goal="\n    ".join(goal),
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("domain_file", help="Name of resulting domain file")
    p.add_argument("problem_file", help="Name of resulting problem file")
    p.add_argument("cards", help="Number of cards per color", type=int)
    p.add_argument("colors", help="Number of colors (stacks to build)", type=int)
    p.add_argument(
        "stacks",
        help="Number of auxiliary stacks used to temporarily store cards",
        type=int,
    )
    p.add_argument("--seed", help="RNG seed", type=int, default=1734)
    args = p.parse_args()
    with open(args.domain_file, "w", encoding="ascii") as f:
        f.write(generate_domain(args.cards, args.colors))
    with open(args.problem_file, "w", encoding="ascii") as f:
        f.write(generate_problem(args.cards, args.colors, args.stacks, args.seed))


if __name__ == "__main__":
    main()
