Version of Pacman based on an assignment at Uni Berkeley.

The current version simplifies things by ignoring pills, and assuming that all agents move
at the same velocity, and that ghosts behaviour does only depend on their current position
and direction.

In the original game, the objective is to maximize reward, with the following reward function:
 -1 for each step taken
 +10 for each food eaten
 -500 for getting killed by a ghost
 +500 for completing the level

We transform this into a cost-problem where the goal is to end the game, each move has a
cost of one, and upon getting killed by a ghost the penalty is 1000 + remaining_food*10.

Therefore, given a policy with expected cost of X in the PDDL version, this is the same as a policy obtaining reward 500 + 10*food_in_level - X.



Implemented by Alvaro Torralba