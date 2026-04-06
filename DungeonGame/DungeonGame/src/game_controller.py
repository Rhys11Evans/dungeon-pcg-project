import random
from collections import deque
from typing import List, Set, Tuple, Optional, Dict

from .dungeon.generator_ca import generate_ca
from .dungeon.grid import FLOOR, WALL, DungeonGrid
from .dungeon.evaluator import evaluate_level, bfs_distances
from .render.renderer_pygame import run_renderer


# --- CA settings (tune these) ---
CA_FILL_PROB = 0.40
CA_STEPS = 4
CA_BIRTH_LIMIT = 4
CA_DEATH_LIMIT = 3

TARGET_WALL_DENSITY = 0.34

CORNER_RADIUS = 8
CORNER_CARVE_RADIUS = 4

BREACH_RADIUS = 3
MAX_CONNECTIONS = 8

MIN_PATH_LENGTH = 45
MAX_ATTEMPTS = 250

# --- Gameplay placement knobs ---
ENEMY_DENSITY = 1 / 260.0
TRAP_DENSITY = 1 / 220.0
TORCH_DENSITY = 1 / 24.0

# ✅ NEW: Health pickups
HEAL_DENSITY = 1 / 520.0
MAX_HEALS = 10

MAX_ENEMIES = 18
MAX_TRAPS = 24
MAX_TORCHES = 60


def _opposite_corner(corner: str) -> str:
    return {"tl": "br", "br": "tl", "tr": "bl", "bl": "tr"}[corner]


def _neighbors4(x: int, y: int) -> List[Tuple[int, int]]:
    return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]


def _wall_density(grid: DungeonGrid) -> float:
    total = grid.w * grid.h
    if total <= 0:
        return 1.0
    walls = 0
    for y in range(grid.h):
        for x in range(grid.w):
            if grid.get_cell(x, y) == WALL:
                walls += 1
    return walls / total


def _corner_region(grid: DungeonGrid, corner: str, radius: int) -> List[Tuple[int, int]]:
    if corner == "tl":
        xs = range(0, min(grid.w, radius))
        ys = range(0, min(grid.h, radius))
    elif corner == "tr":
        xs = range(max(0, grid.w - radius), grid.w)
        ys = range(0, min(grid.h, radius))
    elif corner == "bl":
        xs = range(0, min(grid.w, radius))
        ys = range(max(0, grid.h - radius), grid.h)
    else:  # br
        xs = range(max(0, grid.w - radius), grid.w)
        ys = range(max(0, grid.h - radius), grid.h)

    return [(x, y) for y in ys for x in xs]


def _random_floor_in_region(grid: DungeonGrid, region: List[Tuple[int, int]]) -> Optional[Tuple[int, int]]:
    floors = [(x, y) for (x, y) in region if grid.in_bounds(x, y) and grid.get_cell(x, y) == FLOOR]
    return random.choice(floors) if floors else None


def _dig_blob(grid: DungeonGrid, cx: int, cy: int, radius: int) -> None:
    for y in range(cy - radius, cy + radius + 1):
        for x in range(cx - radius, cx + radius + 1):
            if not grid.in_bounds(x, y):
                continue
            if (x - cx) * (x - cx) + (y - cy) * (y - cy) <= radius * radius:
                grid.set_cell(x, y, FLOOR)


def _ensure_corner_has_floor(grid: DungeonGrid, corner: str, carve_radius: int) -> None:
    region = _corner_region(grid, corner, CORNER_RADIUS)
    if _random_floor_in_region(grid, region) is not None:
        return

    if corner == "tl":
        cx, cy = 2, 2
    elif corner == "tr":
        cx, cy = grid.w - 3, 2
    elif corner == "bl":
        cx, cy = 2, grid.h - 3
    else:
        cx, cy = grid.w - 3, grid.h - 3

    _dig_blob(grid, cx, cy, carve_radius)


def _open_up_to_density(grid: DungeonGrid, target_wall_density: float) -> None:
    max_ops = grid.w * grid.h * 3
    ops = 0

    while _wall_density(grid) > target_wall_density and ops < max_ops:
        ops += 1

        candidates = []
        for y in range(1, grid.h - 1):
            for x in range(1, grid.w - 1):
                if grid.get_cell(x, y) != WALL:
                    continue
                if any(grid.get_cell(nx, ny) == FLOOR for nx, ny in _neighbors4(x, y)):
                    candidates.append((x, y))

        if not candidates:
            break

        x, y = random.choice(candidates)
        grid.set_cell(x, y, FLOOR)


def _get_floor_components(grid: DungeonGrid) -> List[Set[Tuple[int, int]]]:
    remaining = {
        (x, y)
        for y in range(grid.h)
        for x in range(grid.w)
        if grid.get_cell(x, y) == FLOOR
    }

    comps: List[Set[Tuple[int, int]]] = []
    while remaining:
        start = next(iter(remaining))
        q = deque([start])
        comp = {start}
        remaining.remove(start)

        while q:
            x, y = q.popleft()
            for nx, ny in _neighbors4(x, y):
                if (nx, ny) in remaining:
                    remaining.remove((nx, ny))
                    comp.add((nx, ny))
                    q.append((nx, ny))

        comps.append(comp)

    return comps


def _dig_jitter_path(grid: DungeonGrid, a: Tuple[int, int], b: Tuple[int, int], blob_radius: int) -> None:
    x, y = a
    bx, by = b
    _dig_blob(grid, x, y, blob_radius)

    while (x, y) != (bx, by):
        dx = 1 if bx > x else -1 if bx < x else 0
        dy = 1 if by > y else -1 if by < y else 0

        if dx != 0 and dy != 0:
            if random.random() < 0.5:
                x += dx
            else:
                y += dy
        elif dx != 0:
            x += dx
        elif dy != 0:
            y += dy

        _dig_blob(grid, x, y, blob_radius)


def _connect_components_chunky(grid: DungeonGrid) -> None:
    comps = _get_floor_components(grid)
    if len(comps) <= 1:
        return

    comps.sort(key=len, reverse=True)
    main = comps[0]
    connections = 0

    for comp in comps[1:]:
        if connections >= MAX_CONNECTIONS:
            break

        best_pair = None
        best_dist = 10**9

        for (x1, y1) in comp:
            for (x2, y2) in main:
                d = abs(x1 - x2) + abs(y1 - y2)
                if d < best_dist:
                    best_dist = d
                    best_pair = ((x1, y1), (x2, y2))

        if best_pair:
            a, b = best_pair
            _dig_jitter_path(grid, a, b, BREACH_RADIUS)
            main = main.union(comp)
            connections += 1


def _choose_goal_in_opposite_corner_or_farthest(
    grid: DungeonGrid, start: Tuple[int, int], goal_corner: str
) -> Tuple[int, int]:
    dist_map = bfs_distances(grid, start)
    if not dist_map:
        return start

    region = set(_corner_region(grid, goal_corner, CORNER_RADIUS))
    in_corner = [(pos, d) for pos, d in dist_map.items() if pos in region]

    if in_corner:
        max_d = max(d for _, d in in_corner)
        candidates = [pos for pos, d in in_corner if d == max_d]
        return random.choice(candidates)

    max_d = max(dist_map.values())
    candidates = [pos for pos, d in dist_map.items() if d == max_d]
    return random.choice(candidates) if candidates else start


def _place_enemies_traps_torches_heals(
    grid: DungeonGrid,
    start: Tuple[int, int],
    goal: Tuple[int, int],
) -> Tuple[Set[Tuple[int, int]], Set[Tuple[int, int]], Set[Tuple[int, int]], Set[Tuple[int, int]]]:
    dist_map: Dict[Tuple[int, int], int] = bfs_distances(grid, start)
    reachable = set(dist_map.keys())

    # only place on reachable floors (and not too close to start)
    floor_candidates = [p for p in reachable if p != start and p != goal]
    floor_candidates = [p for p in floor_candidates if dist_map.get(p, 999) >= 6]
    random.shuffle(floor_candidates)

    total_tiles = grid.w * grid.h
    n_enemies = min(MAX_ENEMIES, max(3, int(total_tiles * ENEMY_DENSITY)))
    n_traps = min(MAX_TRAPS, max(4, int(total_tiles * TRAP_DENSITY)))

    # ✅ heals count (simple + explainable)
    n_heals = min(MAX_HEALS, max(2, int(total_tiles * HEAL_DENSITY)))

    enemies: Set[Tuple[int, int]] = set()
    traps: Set[Tuple[int, int]] = set()
    heals: Set[Tuple[int, int]] = set()

    for p in floor_candidates:
        if len(enemies) >= n_enemies:
            break
        enemies.add(p)

    for p in floor_candidates:
        if len(traps) >= n_traps:
            break
        if p in enemies:
            continue
        traps.add(p)

    # ✅ place heals avoiding enemies/traps
    for p in floor_candidates:
        if len(heals) >= n_heals:
            break
        if p in enemies or p in traps:
            continue
        heals.add(p)

    # torches sit on WALLs adjacent to reachable floor tiles
    torch_candidates: List[Tuple[int, int]] = []
    for (fx, fy) in reachable:
        for wx, wy in _neighbors4(fx, fy):
            if grid.in_bounds(wx, wy) and grid.get_cell(wx, wy) == WALL:
                torch_candidates.append((wx, wy))

    torch_candidates = list(set(torch_candidates))
    random.shuffle(torch_candidates)

    n_torches = min(MAX_TORCHES, max(8, int(len(torch_candidates) * TORCH_DENSITY)))
    torches = set(torch_candidates[:n_torches])

    return enemies, traps, torches, heals


def generate_valid_level(width: int = 40, height: int = 25):
    last_metrics = {}

    for _ in range(MAX_ATTEMPTS):
        grid = generate_ca(
            w=width,
            h=height,
            fill_prob=CA_FILL_PROB,
            steps=CA_STEPS,
            birth_limit=CA_BIRTH_LIMIT,
            death_limit=CA_DEATH_LIMIT,
        )

        _open_up_to_density(grid, TARGET_WALL_DENSITY)

        start_corner = random.choice(["tl", "tr", "bl", "br"])
        goal_corner = _opposite_corner(start_corner)

        _ensure_corner_has_floor(grid, start_corner, CORNER_CARVE_RADIUS)
        _ensure_corner_has_floor(grid, goal_corner, CORNER_CARVE_RADIUS)

        _connect_components_chunky(grid)

        start = _random_floor_in_region(grid, _corner_region(grid, start_corner, CORNER_RADIUS))
        if start is None:
            continue

        goal = _choose_goal_in_opposite_corner_or_farthest(grid, start, goal_corner)
        if start == goal:
            continue

        metrics = evaluate_level(grid, start, goal)
        last_metrics = metrics

        if not metrics.get("solvable", False):
            continue

        path_len = metrics.get("path_length")
        if path_len is None or path_len < MIN_PATH_LENGTH:
            continue

        enemies, traps, torches, heals = _place_enemies_traps_torches_heals(grid, start, goal)
        return grid, start, goal, metrics, enemies, traps, torches, heals

    # fallback
    enemies, traps, torches, heals = _place_enemies_traps_torches_heals(grid, start, goal)
    return grid, start, goal, last_metrics, enemies, traps, torches, heals


def run(width: int = 40, height: int = 25) -> None:
    """
    IMPORTANT:
    - Renderer returns action strings like "regen" or "quit".
    - If action == "regen", we loop again and generate a NEW map.
    - Any other action exits the loop and ends the program.
    """
    difficulty: Optional[str] = None

    while True:
        grid, start, goal, metrics, enemies, traps, torches, heals = generate_valid_level(width, height)

        action, difficulty = run_renderer(
            grid,
            start,
            goal,
            enemies=enemies,
            traps=traps,
            torches=torches,
            heals=heals,  # ✅ NEW
            difficulty=difficulty,
            metrics=metrics,
        )

        # ✅ Accept multiple restart labels just in case an older renderer is still returning them
        if action in ("regen", "restart", "regen_new"):
            continue

        break