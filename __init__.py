# autoreward — reward layer for autonomous optimization loops
# MIT licensed — https://github.com/michaelhunley/autoreward
from autoreward.reward_vector import RewardVector, compute_reward_vector
from autoreward.optimizer import (
    Node,
    run,
    best_by_maximin,
    best_by_mean,
    pareto_front,
)
from autoreward.descent import (
    Knob,
    descent,
    bisect_search,
    gauss_newton,
)

__all__ = [
    "RewardVector",
    "compute_reward_vector",
    "Node",
    "run",
    "best_by_maximin",
    "best_by_mean",
    "pareto_front",
    # descent driver (bisection + joint Gauss-Newton) -- see DESCENT.md
    "Knob",
    "descent",
    "bisect_search",
    "gauss_newton",
]
