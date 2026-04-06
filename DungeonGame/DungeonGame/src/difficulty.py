"""
difficulty.py

Centralised difficulty presets (academic + explainable).
Each preset controls:
- CA generation parameters
- evaluation thresholds
- gameplay density knobs
- selection (generate-and-test) attempt counts
"""

from dataclasses import dataclass
from typing import Dict


@dataclass(frozen=True)
class DifficultyConfig:
    # CA parameters
    fill_prob: float
    steps: int
    birth_limit: int
    death_limit: int

    # Post-processing knobs
    target_wall_density: float

    # Generate-and-test selection
    num_candidates: int

    # Evaluation thresholds
    min_path_length: int
    min_component_ratio: float
    max_dead_end_ratio: float
    min_openness: float

    # Scoring targets
    target_path_len: int
    ideal_wall_density: float
    wall_density_tolerance: float

    # Scoring weights
    w_path: float
    w_component: float
    w_density: float
    w_dead_ends: float
    w_openness: float

    # Gameplay densities / caps
    enemy_density: float
    trap_density: float
    torch_density: float
    max_enemies: int
    max_traps: int
    max_torches: int

    # Fairness constraints
    min_spawn_dist_from_start: int


DIFFICULTIES: Dict[str, DifficultyConfig] = {
    "easy": DifficultyConfig(
        fill_prob=0.40, steps=4, birth_limit=4, death_limit=3,
        target_wall_density=0.34,
        num_candidates=18,

        min_path_length=40,
        min_component_ratio=0.78,
        max_dead_end_ratio=0.18,
        min_openness=0.20,

        target_path_len=90,
        ideal_wall_density=0.34,
        wall_density_tolerance=0.18,

        w_path=0.40, w_component=0.25, w_density=0.15, w_dead_ends=0.10, w_openness=0.10,

        enemy_density=1 / 290.0,
        trap_density=1 / 250.0,
        torch_density=1 / 22.0,
        max_enemies=14,
        max_traps=20,
        max_torches=65,

        min_spawn_dist_from_start=6,
    ),
    "medium": DifficultyConfig(
        fill_prob=0.43, steps=5, birth_limit=4, death_limit=3,
        target_wall_density=0.36,
        num_candidates=24,

        min_path_length=50,
        min_component_ratio=0.82,
        max_dead_end_ratio=0.16,
        min_openness=0.18,

        target_path_len=110,
        ideal_wall_density=0.36,
        wall_density_tolerance=0.16,

        w_path=0.40, w_component=0.25, w_density=0.15, w_dead_ends=0.12, w_openness=0.08,

        enemy_density=1 / 260.0,
        trap_density=1 / 220.0,
        torch_density=1 / 24.0,
        max_enemies=18,
        max_traps=24,
        max_torches=60,

        min_spawn_dist_from_start=6,
    ),
    "hard": DifficultyConfig(
        fill_prob=0.46, steps=6, birth_limit=4, death_limit=3,
        target_wall_density=0.38,
        num_candidates=30,

        min_path_length=60,
        min_component_ratio=0.86,
        max_dead_end_ratio=0.14,
        min_openness=0.16,

        target_path_len=130,
        ideal_wall_density=0.38,
        wall_density_tolerance=0.14,

        w_path=0.40, w_component=0.25, w_density=0.15, w_dead_ends=0.15, w_openness=0.05,

        enemy_density=1 / 230.0,
        trap_density=1 / 200.0,
        torch_density=1 / 28.0,
        max_enemies=22,
        max_traps=28,
        max_torches=55,

        min_spawn_dist_from_start=7,
    ),
}