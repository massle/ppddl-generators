#!/usr/bin/env python

import argparse
import random
from collections.abc import Iterable


def get_adjacent(x: int, y: int, width: int, height: int) -> Iterable[tuple[int, int]]:
    if x > 0:
        yield (x - 1, y)
    if x + 1 < width:
        yield (x + 1, y)
    if y > 0:
        yield (x, y - 1)
    if y + 1 < height:
        yield (x, y + 1)


def fill_board(width: int, height: int, num_blocked: int) -> list[tuple[int, int]]:
    assert num_blocked < width * height
    blocked = []
    neighbors = [(x, 0) for x in range(width)]
    for _ in range(num_blocked):
        assert len(neighbors) > 0
        i = 0 if len(neighbors) == 1 else random.randint(0, len(neighbors) - 1)
        x, y = neighbors[i]
        del neighbors[i]
        blocked.append((x, y))
        if y + 1 < height:
            neighbors.append((x, y + 1))
    return blocked


PROBLEM = """
(define (problem tetris-{width}-{height}-{blocked}-{seed})
(:domain tetris)
(:objects
    {hpositions} - Hposition
    {vpositions} - Vposition
    {rounds} - round
)
(:init
    {above}
    {left}
    {nextRound}
    {initially_blocked}
    (currentRound rnd0)
    (playerMoved)
)
(:goal (and
    (currentRound rnd{goal_round})
    (playerMoved)
))
(:metric minimize (total-cost))
)
"""


def generate_problem(
    seed: int,
    width: int,
    height: int,
    rounds: int,
    initially_blocked: list[tuple[int, int]],
) -> str:
    return PROBLEM.format(
        width=width,
        height=height,
        blocked=len(initially_blocked),
        seed=seed,
        hpositions=" ".join((f"hpos{i}" for i in range(width))),
        vpositions=" ".join((f"vpos{i}" for i in range(height))),
        rounds=" ".join((f"rnd{i}" for i in range(rounds + 1))),
        above="\n    ".join([f"(ABOVE vpos{i} vpos{i-1})" for i in range(1, height)]),
        left="\n    ".join([f"(LEFT hpos{i-1} hpos{i})" for i in range(1, width)]),
        nextRound="\n    ".join([f"(NEXT rnd{i} rnd{i+1})" for i in range(rounds)]),
        initially_blocked="\n    ".join(
            [f"(blocked hpos{x} vpos{y})" for (x, y) in initially_blocked]
        ),
        goal_round=rounds,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("width", type=int, help="Width of the Tetris grid")
    p.add_argument("height", type=int, help="Height of the Tetris grid")
    p.add_argument("rounds", type=int, help="Number of rounds")
    p.add_argument(
        "--populate", type=float, help="Initial grid population ratio", default=0.0
    )
    p.add_argument("--seed", type=int, help="RNG seed", default=1734)
    args = p.parse_args()
    assert args.populate >= 0.0 and args.populate < 1.0
    assert args.width >= 4 and args.height >= 4
    assert args.rounds >= 1
    n = int(args.populate * (args.width * args.height))
    random.seed(args.seed)
    blocked = fill_board(args.width, args.height, n)
    print(generate_problem(args.seed, args.width, args.height, args.rounds, blocked))


if __name__ == "__main__":
    main()
