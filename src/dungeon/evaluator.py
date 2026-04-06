from collections import deque
from typing import Dict, Optional, Tuple, List, Set

from .grid import FLOOR, DOOR, WALL, DungeonGrid


def _is_walkable(cell: int) -> bool:
    return cell in (FLOOR, DOOR)


def bfs_shortest_path_length(
    grid: DungeonGrid,
    start: Tuple[int, int],
    goal: Tuple[int, int]
) -> Optional[int]:
    if start == goal:
        return 0

    sx, sy = start
    gx, gy = goal

    if not grid.in_bounds(sx, sy) or not grid.in_bounds(gx, gy):
        return None
    if not _is_walkable(grid.get_cell(sx, sy)) or not _is_walkable(grid.get_cell(gx, gy)):
        return None

    q = deque([(sx, sy)])
    dist = {(sx, sy): 0}

    while q:
        x, y = q.popleft()
        d = dist[(x, y)]

        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not grid.in_bounds(nx, ny):
                continue
            if not _is_walkable(grid.get_cell(nx, ny)):
                continue
            if (nx, ny) in dist:
                continue

            dist[(nx, ny)] = d + 1
            if (nx, ny) == (gx, gy):
                return d + 1
            q.append((nx, ny))

    return None


def bfs_distances(grid: DungeonGrid, start: Tuple[int, int]) -> Dict[Tuple[int, int], int]:
    sx, sy = start
    if not grid.in_bounds(sx, sy) or not _is_walkable(grid.get_cell(sx, sy)):
        return {}

    q = deque([(sx, sy)])
    dist: Dict[Tuple[int, int], int] = {(sx, sy): 0}

    while q:
        x, y = q.popleft()
        d = dist[(x, y)]

        for nx, ny in ((x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)):
            if not grid.in_bounds(nx, ny):
                continue
            if not _is_walkable(grid.get_cell(nx, ny)):
                continue
            if (nx, ny) in dist:
                continue

            dist[(nx, ny)] = d + 1
            q.append((nx, ny))

    return dist


def _neighbors4(x: int, y: int) -> List[Tuple[int, int]]:
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def connected_component_sizes(grid: DungeonGrid) -> List[int]:
    visited: Set[Tuple[int, int]] = set()
    sizes: List[int] = []

    for y in range(grid.h):
        for x in range(grid.w):
            if (x, y) in visited:
                continue
            if not _is_walkable(grid.get_cell(x, y)):
                continue

            q = deque([(x, y)])
            visited.add((x, y))
            size = 0

            while q:
                cx, cy = q.popleft()
                size += 1
                for nx, ny in _neighbors4(cx, cy):
                    if not grid.in_bounds(nx, ny):
                        continue
                    if (nx, ny) in visited:
                        continue
                    if not _is_walkable(grid.get_cell(nx, ny)):
                        continue
                    visited.add((nx, ny))
                    q.append((nx, ny))

            sizes.append(size)

    return sizes


def dead_end_ratio(grid: DungeonGrid) -> float:
    floors = 0
    dead_ends = 0

    for y in range(grid.h):
        for x in range(grid.w):
            if not _is_walkable(grid.get_cell(x, y)):
                continue
            floors += 1
            walkable_neigh = 0
            for nx, ny in _neighbors4(x, y):
                if grid.in_bounds(nx, ny) and _is_walkable(grid.get_cell(nx, ny)):
                    walkable_neigh += 1
            if walkable_neigh == 1:
                dead_ends += 1

    return (dead_ends / floors) if floors > 0 else 1.0


def openness_proxy(grid: DungeonGrid, window_radius: int = 2) -> float:
    window_size = (2 * window_radius + 1) ** 2
    if window_size <= 0:
        return 0.0

    total_samples = 0
    total_density = 0.0

    for y in range(grid.h):
        for x in range(grid.w):
            if not _is_walkable(grid.get_cell(x, y)):
                continue

            floors_in_window = 0
            total_samples += 1

            for wy in range(y - window_radius, y + window_radius + 1):
                for wx in range(x - window_radius, x + window_radius + 1):
                    if grid.in_bounds(wx, wy) and _is_walkable(grid.get_cell(wx, wy)):
                        floors_in_window += 1

            total_density += floors_in_window / window_size

    return (total_density / total_samples) if total_samples > 0 else 0.0


def _clamp01(v: float) -> float:
    return 0.0 if v < 0.0 else 1.0 if v > 1.0 else v


def evaluate_level(grid: DungeonGrid, start: Tuple[int, int], goal: Tuple[int, int], cfg=None) -> dict:
    total_cells = grid.width * grid.height
    wall_count = 0

    for y in range(grid.height):
        for x in range(grid.width):
            if grid.get_cell(x, y) == WALL:
                wall_count += 1

    wall_density = wall_count / total_cells if total_cells > 0 else 0.0
    path_length = bfs_shortest_path_length(grid, start, goal)
    solvable = path_length is not None

    comp_sizes = connected_component_sizes(grid)
    total_walkable = sum(comp_sizes) if comp_sizes else 0
    largest_comp = max(comp_sizes) if comp_sizes else 0
    largest_component_ratio = (largest_comp / total_walkable) if total_walkable > 0 else 0.0

    de_ratio = dead_end_ratio(grid)
    open_score = openness_proxy(grid, window_radius=2)

    score = 0.0
    if solvable and cfg is not None and path_length is not None:
        path_score = _clamp01(path_length / max(1, cfg.target_path_len))

        deviation = abs(wall_density - cfg.ideal_wall_density)
        density_score = 1.0 - (deviation / max(1e-6, cfg.wall_density_tolerance))
        density_score = _clamp01(density_score)

        dead_end_score = _clamp01(1.0 - de_ratio)
        openness_norm = _clamp01(open_score)

        score = (
            cfg.w_path * path_score +
            cfg.w_component * _clamp01(largest_component_ratio) +
            cfg.w_density * density_score +
            cfg.w_dead_ends * dead_end_score +
            cfg.w_openness * openness_norm
        )

    return {
        "solvable": solvable,
        "wall_density": wall_density,
        "path_length": path_length,
        "largest_component_ratio": largest_component_ratio,
        "dead_end_ratio": de_ratio,
        "openness": open_score,
        "score": score,
    }


def passes_thresholds(metrics: dict, cfg) -> bool:
    if not metrics.get("solvable", False):
        return False
    pl = metrics.get("path_length")
    if pl is None or pl < cfg.min_path_length:
        return False
    if metrics.get("largest_component_ratio", 0.0) < cfg.min_component_ratio:
        return False
    if metrics.get("dead_end_ratio", 1.0) > cfg.max_dead_end_ratio:
        return False
    if metrics.get("openness", 0.0) < cfg.min_openness:
        return False
    return True