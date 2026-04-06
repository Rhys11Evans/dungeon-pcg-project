"""
grid.py

Defines the grid-based representation of a dungeon layout.

A dungeon is stored as a 2D list (rows then columns), where each cell is:
- WALL (1)  -> blocked tile
- FLOOR (0) -> walkable tile
- DOOR (2)  -> walkable connector tile

This class is shared by the generator, evaluator, and renderer.
"""

from dataclasses import dataclass
from typing import List, Tuple

# Cell type constants
WALL = 1
FLOOR = 0
DOOR = 2


@dataclass
class DungeonGrid:
    """
    Represents a dungeon as a simple grid.

    Attributes:
        w (int): width in cells
        h (int): height in cells
        cells (List[List[int]]): 2D grid: cells[y][x]
    """
    w: int
    h: int
    cells: List[List[int]]

    @property
    def width(self) -> int:
        return self.w

    @property
    def height(self) -> int:
        return self.h

    def in_bounds(self, x: int, y: int) -> bool:
        """True if (x, y) lies within the grid boundaries."""
        return 0 <= x < self.w and 0 <= y < self.h

    def get_cell(self, x: int, y: int) -> int:
        """Return the cell value (WALL/FLOOR/DOOR) at (x, y)."""
        return self.cells[y][x]

    def set_cell(self, x: int, y: int, value: int) -> None:
        """Set the cell at (x, y) to WALL/FLOOR/DOOR."""
        self.cells[y][x] = value

    def is_wall(self, x: int, y: int) -> bool:
        """Convenience method to check if a cell is a wall."""
        return self.get_cell(x, y) == WALL

    def count_type(self, cell_type: int) -> int:
        """Count how many cells match a given type (WALL/FLOOR/DOOR)."""
        return sum(
            1
            for y in range(self.h)
            for x in range(self.w)
            if self.get_cell(x, y) == cell_type
        )

    def as_tuple(self) -> Tuple[Tuple[int, ...], ...]:
        """Return an immutable representation of the grid."""
        return tuple(tuple(row) for row in self.cells)