#!/usr/bin/env python

import argparse
import os
import random
import re
from collections.abc import Iterable
from fractions import Fraction

DOMAIN = """
(define (domain snake)
    (:requirements :strips :negative-preconditions :typing :probabilistic-effects)

    (:types
        num
        loc
    )

    (:constants
        {locs} - loc
    )

    (:predicates 
        (tailSnake ?x - loc) ;the last field of the snake
        (headSnake ?x - loc) ;the first field of the snake
        (nextSnake ?x ?y) ;pieces of the snake that are connected. from front to back
        (blocked ?x - loc) ;a field that is occupied by the snake or by an obstacle
        (isPoint ?x - loc) ;a field that has a point that can be collected by the snake
        (collectedPoints ?n - num)
        (ADJACENT ?x ?y - loc) ;up down left right of a field
        (NEXT ?n0 ?n1 - num)
        (RESPAWN-POINT ?x - loc)
    )

    (:action respawn
        :parameters (?head)
        :precondition (and
            (headSnake ?head)
            (RESPAWN-POINT ?head)
        )
        :effect (and 
            (increase (total-cost) {exit_cost})
            (not (headSnake ?head))
            (not (blocked ?head))
            (probabilistic
{exit_effect}
            )
        )
    )

    (:action unit-move
    :parameters (?head ?newHead - loc)
    :precondition (and
        (headSnake ?head)
        (tailSnake ?head)
        (ADJACENT ?head ?newHead)
        (not (blocked ?newHead))
        (not (isPoint ?newHead))
        )
    :effect (and
        (blocked ?newHead)
        (headSnake ?newHead)
        (tailSnake ?newHead)
        (not (headSnake ?head))
        (not (tailSnake ?head))
        (not (blocked ?head))
        (increase (total-cost) 1)
        )
    )

    (:action move
    :parameters (?head ?newHead ?tail ?newTail - loc)
    :precondition (and
        (headSnake ?head)
        (ADJACENT ?head ?newHead)
        (tailSnake ?tail)
        (nextSnake ?tail ?newTail)
        (not (blocked ?newHead))
        (not (isPoint ?newHead))
        (not (= ?head ?tail))
        )
    :effect (and
        (blocked ?newHead)
        (headSnake ?newHead)
        (nextSnake ?head ?newHead)
        (not (headSnake ?head))
        (not (blocked ?tail))
        (not (tailSnake ?tail))
        (not (nextSnake ?tail ?newTail))
        (tailSnake ?newTail)
        (increase (total-cost) 1)
        )
    )

    (:action move-and-eat
    :parameters  (?head ?newHead - loc ?curPoints ?newPoints - num)
    :precondition (and
        (headSnake ?head)
        (ADJACENT ?head ?newHead)
        (not (blocked ?newHead))
        (isPoint ?newHead)
        (collectedPoints ?curPoints)
        (NEXT ?curPoints ?newPoints)
    )
    :effect (and
        (blocked ?newHead)
        (headSnake ?newHead)
        (nextSnake ?head ?newHead)
        (not (headSnake ?head))
        (not (isPoint ?newHead))
        (not (collectedPoints ?curPoints))
        (collectedPoints ?newPoints)
        (probabilistic
            {spawns}
        )
        (increase (total-cost) 1)
    ))
)
"""


PROBLEM = """
(define (problem snake-{name}-{seed})
(:domain snake)
(:objects
    {num} - num
)
(:init
    (= (total-cost) 0)
    {nexxt}
    {adjac}
    {border}
    {blocked}
    {apples}
    (blocked grid-{x0}-{y0})
    (headSnake grid-{x0}-{y0})
    (tailSnake grid-{x0}-{y0})
    (collectedPoints n0)
)
(:goal (and
    (collectedPoints n{points})
))
(:metric minimize (total-cost))
)
"""


class Board:
    WALL = "*"
    CLEAR = "_"
    APPLE = "a"

    def __init__(self, path: str, ignore_apples: bool = False):
        self.name: str = re.sub(r"[^\w]+", "-", os.path.basename(path).split(".")[0])
        self.board: list[list[str]] = []
        with open(path, encoding="ascii") as f:
            for line in f.readlines():
                line = line.lower().strip()
                if len(line) == 0:
                    break
                row = []
                for c in line:
                    if c == Board.WALL:
                        row.append(Board.WALL)
                    elif c == Board.APPLE and not ignore_apples:
                        row.append(Board.APPLE)
                    else:
                        row.append(Board.CLEAR)
                self.board.append(row)
        assert len(self.board) > 0
        assert len(set((len(r) for r in self.board))) == 1
        self.dim0: int = len(self.board)
        self.dim1: int = len(self.board[0])

    def _join_effs(self, atoms: list[str]) -> str:
        return "\n            ".join(atoms)

    def _join_atoms(self, atoms: list[str]) -> str:
        return "\n    ".join(atoms)

    def _dim(self) -> Iterable[tuple[int, int]]:
        for x in range(self.dim0):
            for y in range(self.dim1):
                yield x, y

    def _i_non_walls(self) -> Iterable[tuple[int, int]]:
        for x, y in self._dim():
            if self.board[x][y] != Board.WALL:
                yield x, y

    def _adj(self, x: int, y: int) -> Iterable[tuple[int, int]]:
        yield (self.dim0 + x - 1) % self.dim0, y
        yield (self.dim0 + x + 1) % self.dim0, y
        yield x, (self.dim1 + y - 1) % self.dim1
        yield x, (self.dim1 + y + 1) % self.dim1

    def _get_not_blocked(self, ignore: list[tuple[int, int]] = []) -> str:
        return self._join_effs(
            [
                f"(not (blocked grid-{x}-{y}))"
                for x, y in self._dim()
                if (x, y) not in ignore and self.board[x][y] != Board.WALL
            ]
        )

    def _get_not_tail(self) -> str:
        return self._join_effs(
            [
                f"(not (tailSnake grid-{x}-{y}))"
                for x, y in self._dim()
                if self.board[x][y] != Board.WALL
            ]
        )

    def _get_not_snake(self) -> str:
        return self._join_effs(
            [
                f"(not (nextSnake grid-{xA}-{yA} grid-{xB}-{yB}))"
                for (xA, yA) in self._dim()
                for (xB, yB) in self._adj(xA, yA)
                if self.board[xA][yA] != Board.WALL and self.board[xB][yB] != Board.WALL
            ]
        )

    def get_exit_effect(self) -> str:
        outcomes = []
        non_walls = list(self._i_non_walls())
        for x, y in non_walls:
            outcomes.append(
                16 * " "
                + f"1/{len(non_walls)} (and"
                + " (headSnake grid-{x}-{y})"
                + " (tailSnake grid-{x}-{y})"
                + " (blocked grid-{x}-{y})"
                + " ".join(
                    [
                        " ".join(
                            [
                                f"(not (blocked grid-{a}-{b})) (not (tailSnake grid-{a}-{b}))"
                                for a, b in non_walls
                                if (a, b) != (x, y)
                            ]
                        ),
                        " ".join(
                            [
                                f"(not (nextSnake grid-{xA}-{yA} grid-{xB}-{yB}))"
                                for (xA, yA) in self._dim()
                                for (xB, yB) in self._adj(xA, yA)
                                if self.board[xA][yA] != Board.WALL
                                and self.board[xB][yB] != Board.WALL
                            ]
                        ),
                    ]
                )
                + ")"
            )

        return "\n".join(outcomes)

    def get_adjacent(self) -> str:
        return self._join_atoms(
            [
                f"(ADJACENT grid-{x0}-{y0} grid-{x1}-{y1})"
                for x0, y0 in self._dim()
                for x1, y1 in self._adj(x0, y0)
            ]
        )

    def _is_border(self, x: int, y: int) -> bool:
        return (x == 0 or x == self.dim0 - 1) and (y == 0 or y == self.dim1 - 1)

    def get_border(self) -> str:
        return self._join_atoms(
            [
                f"(BORDER_ADJACENT grid-{x0}-{y0} grid-{x1}-{y1})"
                for (x0, y0) in self._dim()
                for (x1, y1) in self._adj(x0, y0)
                if self._is_border(x0, y0) and self._is_border(x1, y1)
            ]
        )

    def get_next(self, n: int) -> str:
        return self._join_atoms([f"(NEXT n{i} n{i+1})" for i in range(n - 1)])

    def get_locations(self) -> str:
        return " ".join([f"grid-{x}-{y}" for x, y in self._dim()])

    def get_spawns(self) -> str:
        cells = list((x, y) for (x, y) in self._dim() if self.board[x][y] != Board.WALL)
        prob = Fraction(1, len(cells))
        return self._join_effs([f"{prob} (isPoint grid-{x}-{y})" for x, y in cells])

    def get_blocked(self) -> str:
        return self._join_atoms(
            [
                f"(blocked grid-{x}-{y})"
                for x, y in self._dim()
                if self.board[x][y] == Board.WALL
            ]
        )

    def get_apples(self, apples: list[tuple[int, int]]) -> str:
        return self._join_atoms([f"(isPoint grid-{x}-{y})" for (x, y) in apples])


def generate_domain(board: Board, exit_cost: int) -> str:
    return DOMAIN.format(
        locs=board.get_locations(),
        exit_effect=board.get_exit_effect(),
        spawns=board.get_spawns(),
        exit_cost=exit_cost,
    )


def generate_problem(
    board: Board, seed: int, numPoints: int, respawn_points: int
) -> str:
    non_walls = list(board._i_non_walls())
    assert len(non_walls) >= 1 + respawn_points
    random.shuffle(non_walls)
    x0, y0 = non_walls[0]
    respawn_points = non_walls[1 : 1 + respawn_points]
    apples = [(x, y) for x, y in board._dim() if board.board[x][y] == Board.APPLE]
    if len(apples) == 0:
        i = random.randint(0, len(non_walls) - 1)
        apples.append(non_walls[i])
    return PROBLEM.format(
        name=board.name,
        seed=seed,
        num=" ".join((f"n{i}" for i in range(numPoints + 1))),
        nexxt=board.get_next(numPoints + 1),
        adjac=board.get_adjacent(),
        border=board._join_atoms(
            [f"(RESPAWN-POINT grid-{x}-{y})" for (x, y) in respawn_points]
        ),
        blocked=board.get_blocked(),
        apples=board.get_apples(apples),
        x0=x0,
        y0=y0,
        points=numPoints,
    )


def _distribute_apples(board: Board, num_apples: int):
    cells = []
    for x in range(board.dim0):
        for y in range(board.dim1):
            if board.board[x][y] == Board.CLEAR:
                cells.append((x, y))
    random.shuffle(cells)
    for i in range(min(num_apples, len(cells))):
        x, y = cells[i]
        board.board[x][y] = Board.APPLE


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--map", help="Path to map file")
    p.add_argument("--seed", type=int, default=1734, help="Seed")
    p.add_argument(
        "--respawn-cost", type=int, default=10, help="Cost of respawn action"
    )
    p.add_argument(
        "--ignore-apples",
        action="store_true",
        help="Ignore apples defined in board",
        default=False,
    )
    p.add_argument(
        "--initial-apples",
        type=int,
        help="Number of apples placed initially on map",
        default=0,
    )
    p.add_argument(
        "--respawn-points",
        type=int,
        help="Number of respawn points on the map",
        default=1,
    )
    p.add_argument("domain", help="Name of resulting domain file")
    p.add_argument("problem", help="Name of resulting problem file")
    p.add_argument("points", help="Number of points to collect", type=int)
    args = p.parse_args()

    assert args.points > 0
    random.seed(args.seed)

    board = Board(args.map, args.ignore_apples)
    _distribute_apples(board, args.initial_apples)

    with open(args.domain, "w", encoding="ascii") as f:
        f.write(generate_domain(board, args.respawn_cost))
    with open(args.problem, "w", encoding="ascii") as f:
        f.write(generate_problem(board, args.seed, args.points, args.respawn_points))


if __name__ == "__main__":
    main()
