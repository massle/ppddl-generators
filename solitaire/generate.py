#!/usr/bin/env python

import argparse
import random
from fractions import Fraction

MAX_RETRIES = 3

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


class DependencyGraph:
    def __init__(self, num_colors: int, num_stacks: int):
        self.nodes_by_color: list[list[tuple[int, int, int]]] = [
            [] for _ in range(num_colors)
        ]
        self.nodes_by_stack: list[list[tuple[int, int]]] = [
            [] for _ in range(num_stacks)
        ]

    def push(self, node: tuple[int, int], stack: int) -> bool:
        assert stack < len(self.nodes_by_stack)
        self.nodes_by_color[node[0]].append(
            (node[1], stack, len(self.nodes_by_stack[stack]))
        )
        self.nodes_by_stack[stack].append(node)

        closed = set()
        stack_trace = set()

        def dfs(stack_: int, idx_: int):
            assert stack_ not in stack_trace
            stack_trace.add(stack_)
            color, card = self.nodes_by_stack[stack_][idx_]
            for pred, stack2, idx2 in self.nodes_by_color[color]:
                if pred < card:
                    if (stack2, idx2) in closed:
                        continue
                    if stack2 in stack_trace:
                        return False
                    if not dfs(stack2, idx2):
                        return False
            stack_trace.remove(stack_)
            closed.add((stack_, idx_))
            return True

        for i in reversed(range(len(self.nodes_by_stack[stack]) - 1)):
            if not dfs(stack, i):
                self.nodes_by_color[node[0]].pop(-1)
                self.nodes_by_stack[stack].pop(-1)
                return False

        return True


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
    num_cards: int,
    num_colors: int,
    num_stacks: int,
    seed: int,
) -> str:
    assert num_cards > 0 and num_colors > 0 and num_stacks >= 0
    random.seed(seed)
    cards = ["DUMMY_CARD"] + [f"STACK{i}" for i in range(num_stacks)]
    depg = DependencyGraph(num_colors, num_stacks)
    available_cards = [
        (color, card) for color in range(num_colors) for card in range(num_cards)
    ]
    for stack in range(num_stacks):
        for _ in range(stack + 1):
            if len(available_cards) == 0:
                break
            for _ in range(MAX_RETRIES):
                i = random.randint(0, len(available_cards) - 1)
                if depg.push(available_cards[i], stack):
                    del available_cards[i]
                    break
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
            f"(on card{card} color{color} STACK{i} DUMMY_COLOR)"
            for i in range(num_stacks)
            for (color, card) in depg.nodes_by_stack[i][:1]
        ]
        + [
            f"(on card{depg.nodes_by_stack[i][j][1]} color{depg.nodes_by_stack[i][j][0]} card{depg.nodes_by_stack[i][j-1][1]} color{depg.nodes_by_stack[i][j-1][0]})"
            for i in range(num_stacks)
            for j in range(1, len(depg.nodes_by_stack[i]))
        ]
        + [
            f"(clear card{card} color{color})"
            for i in range(num_stacks)
            for (color, card) in depg.nodes_by_stack[i][-1:]
        ]
        + [
            f"(drawn card{card} color{color})"
            for i in range(num_stacks)
            for (color, card) in depg.nodes_by_stack[i]
        ]
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
        f.write(
            generate_problem(
                args.cards,
                args.colors,
                args.stacks,
                args.seed,
            )
        )


if __name__ == "__main__":
    main()
