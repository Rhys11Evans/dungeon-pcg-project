"""
Cellular automata dungeon generator.

This module generates dungeon layouts using a rule-based
cellular automata approach. Random noise is gradually transformed
into structured cave-like spaces through repeated rule application.
"""

import random
from .grid import DungeonGrid, WALL, FLOOR


def _count_wall_neighbours(grid: DungeonGrid, x: int, y: int) -> int:
    """
    Count how many neighbouring cells around (x, y) are walls.

    Cells outside the grid are treated as walls to encourage
    enclosed dungeon shapes.
    """
    count = 0
    for dy in (-1, 0, 1):
        for dx in (-1, 0, 1):
            if dx == 0 and dy == 0:
                continue

            nx, ny = x + dx, y + dy
            if (not grid.in_bounds(nx, ny)) or grid.is_wall(nx, ny):
                count += 1
    return count


def generate_ca(
    w: int,
    h: int,
    fill_prob: float,
    steps: int,
    birth_limit: int,
    death_limit: int
) -> DungeonGrid:
    """
    Generate a dungeon grid using cellular automata rules.

    The process starts with a random grid and repeatedly applies
    smoothing rules to produce a more structured layout.
    """

    # Step 1: initialise a random grid (with a solid wall border)
    cells = []
    for y in range(h):
        row = []
        for x in range(w):
            if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                row.append(WALL)
            else:
                row.append(WALL if random.random() < fill_prob else FLOOR)
        cells.append(row)

    grid = DungeonGrid(w, h, cells)

    # Step 2: smoothing iterations
    for _ in range(steps):
        new_cells = []
        for y in range(h):
            new_row = []
            for x in range(w):
                if x == 0 or y == 0 or x == w - 1 or y == h - 1:
                    new_row.append(WALL)
                    continue

                wall_count = _count_wall_neighbours(grid, x, y)

                # These rules control how caves form:
                # - walls survive with enough neighbouring walls
                # - floors become walls if surrounded heavily
                if grid.get_cell(x, y) == WALL:
                    new_row.append(WALL if wall_count >= death_limit else FLOOR)
                else:
                    new_row.append(WALL if wall_count > birth_limit else FLOOR)

            new_cells.append(new_row)

        grid = DungeonGrid(w, h, new_cells)

    return grid