#!/usr/bin/env python

import argparse
import random
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
        (BORDER_ADJACENT ?x ?y - loc)
    )

    (:action exit
        :parameters (?head ?newHead - loc)
        :precondition (and
            (headSnake ?head)
            (BORDER_ADJACENT ?head ?newHead)
            (not (blocked ?newHead))
        )
        :effect (and 
            (increase (total-cost) {exit_cost})
            (not (headSnake ?head))
            (headSnake ?newHead)
            (tailSnake ?head)
            (nextSnake ?newHead ?head)
            (blocked ?head)
            (blocked ?newHead)
{exit_effect}
        )
    )

    (:action move
    :parameters (?head ?newHead ?tail ?newTail - loc)
    :precondition (and
        (headSnake ?head)
        (ADJACENT ?head ?newHead)
        (tailSnake ?tail)
        (nextSnake ?newTail ?tail)
        (not (blocked ?newHead))
        (not (isPoint ?newHead))
        )
    :effect (and
        (blocked ?newHead)
        (headSnake ?newHead)
        (nextSnake ?newHead ?head)
        (not (headSnake ?head))
        (not (blocked ?tail))
        (not (tailSnake ?tail))
        (not (nextSnake ?newTail ?tail))
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
        (nextSnake ?newHead ?head)
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
(define (problem snake-{dim0}-{dim1}-{seed})
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
    (blocked grid-{x1}-{y1})
    (headSnake grid-{x0}-{y0})
    (tailSnake grid-{x1}-{y1})
    (nextSnake grid-{x0}-{y0} grid-{x1}-{y1})
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

    def __init__(self, path: str):
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
                    elif c == Board.APPLE:
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
        return "\n".join(
            [
                12 * " " + self._get_not_blocked([]),
                12 * " " + self._get_not_tail(),
                12 * " " + self._get_not_snake(),
            ]
        )

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


def generate_problem(board: Board, seed: int, numPoints: int) -> str:
    random.seed(seed)
    while True:
        x0 = random.randint(0, board.dim0 - 1)
        y0 = random.randint(0, board.dim1 - 1)
        if board.board[x0][y0] != Board.WALL:
            sat = False
            for x1, y1 in board._adj(x0, y0):
                if board.board[x1][y1] != Board.WALL:
                    sat = True
                    break
            if sat:
                break
    apples = [(x, y) for x, y in board._dim() if board.board[x][y] == Board.APPLE]
    while len(apples) == 0:
        x = random.randint(0, board.dim0 - 1)
        y = random.randint(0, board.dim1 - 1)
        if board.board[x][y] != Board.WALL:
            apples.append((x, y))
    return PROBLEM.format(
        dim0=board.dim0,
        dim1=board.dim1,
        seed=seed,
        num=" ".join((f"n{i}" for i in range(numPoints + 1))),
        nexxt=board.get_next(numPoints + 1),
        adjac=board.get_adjacent(),
        border=board.get_border(),
        blocked=board.get_blocked(),
        apples=board.get_apples(apples),
        x0=x0,
        y0=y0,
        x1=x1,
        y1=y1,
        points=numPoints,
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--map", help="Path to map file")
    p.add_argument("--seed", type=int, default=1734, help="Seed")
    p.add_argument(
        "--exit-cost", type=int, default=10, help="Cost of exit/reset action"
    )
    p.add_argument("domain", help="Name of resulting domain file")
    p.add_argument("problem", help="Name of resulting problem file")
    p.add_argument("points", help="Number of points to collect", type=int)
    args = p.parse_args()
    assert args.points > 0
    board = Board(args.map)

    with open(args.domain, "w", encoding="ascii") as f:
        f.write(generate_domain(board, args.exit_cost))
    with open(args.problem, "w", encoding="ascii") as f:
        f.write(generate_problem(board, args.seed, args.points))


if __name__ == "__main__":
    main()
