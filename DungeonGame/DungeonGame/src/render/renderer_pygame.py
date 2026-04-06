import math
import random
import pygame
from pathlib import Path
from typing import Tuple, Optional, Set, List, Dict

from ..dungeon.grid import FLOOR, DungeonGrid


def run_renderer(
    grid: DungeonGrid,
    start_pos: Tuple[int, int],
    goal_pos: Tuple[int, int],
    tile_size: int = 32,
    fps: int = 60,
    enemies: Optional[Set[Tuple[int, int]]] = None,
    traps: Optional[Set[Tuple[int, int]]] = None,
    torches: Optional[Set[Tuple[int, int]]] = None,
    heals: Optional[Set[Tuple[int, int]]] = None,
    difficulty: Optional[str] = None,  # "easy" | "medium" | "hard" | None
    seed: Optional[int] = None,
    metrics: Optional[dict] = None,
) -> Tuple[str, str]:
    pygame.init()

    enemies = set(enemies or set())
    traps = set(traps or set())
    torches = set(torches or set())
    heals = set(heals or set())
    metrics = metrics or {}

    width_px = grid.w * tile_size
    height_px = grid.h * tile_size
    screen = pygame.display.set_mode((width_px, height_px))
    pygame.display.set_caption("Cave Escape")

    clock = pygame.time.Clock()

    # --- Asset paths ---
    project_root = Path(__file__).resolve().parents[2]
    assets_dir = project_root / "assets"

    tiles_dir = assets_dir / "tiles"
    player_dir = assets_dir / "player"
    enemies_dir = assets_dir / "enemies"
    traps_dir = assets_dir / "traps"
    props_dir = assets_dir / "props"
    weapons_dir = assets_dir / "weapons"

    def load_sprite(path: Path) -> Optional[pygame.Surface]:
        try:
            img = pygame.image.load(str(path)).convert_alpha()
            return pygame.transform.scale(img, (tile_size, tile_size))
        except Exception:
            return None

    # Tiles
    floor_img = load_sprite(tiles_dir / "floor.png")
    floor_alt_img = load_sprite(tiles_dir / "floor_alt.png")  # optional
    wall_border_img = load_sprite(tiles_dir / "wall_border.png")
    exit_img = load_sprite(tiles_dir / "exit.png")

    # Entities
    player_img = load_sprite(player_dir / "player.png")
    skeleton_img = load_sprite(enemies_dir / "skeleton.png")
    spike_img = load_sprite(traps_dir / "spike_trap.png")
    torch_img = load_sprite(props_dir / "torch.png")
    sword_img = load_sprite(weapons_dir / "sword.png")

    # Heal sprite (green bottle)
    heal_img = load_sprite(props_dir / "green_bottle.png")

    font = pygame.font.SysFont(None, 56)
    ui_font = pygame.font.SysFont(None, 24)
    banner_font = pygame.font.SysFont(None, 42)
    rules_font = pygame.font.SysFont(None, 28)

    red_flash = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
    fog = pygame.Surface((width_px, height_px), pygame.SRCALPHA)

    # -----------------------------
    # Menu UI helpers
    # -----------------------------
    def draw_vertical_gradient_bg() -> None:
        top = (14, 14, 22)
        bot = (7, 7, 12)
        for y in range(height_px):
            t = y / max(1, height_px - 1)
            r = int(top[0] * (1 - t) + bot[0] * t)
            g = int(top[1] * (1 - t) + bot[1] * t)
            b = int(top[2] * (1 - t) + bot[2] * t)
            pygame.draw.line(screen, (r, g, b), (0, y), (width_px, y))

        vign = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
        vign.fill((0, 0, 0, 0))
        pygame.draw.rect(vign, (0, 0, 0, 85), vign.get_rect())
        screen.blit(vign, (0, 0))

    def draw_card(rect: pygame.Rect) -> None:
        shadow = pygame.Surface((rect.w + 18, rect.h + 18), pygame.SRCALPHA)
        pygame.draw.rect(shadow, (0, 0, 0, 110), shadow.get_rect(), border_radius=18)
        screen.blit(shadow, (rect.x - 9, rect.y - 6))

        panel = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)
        pygame.draw.rect(panel, (18, 18, 26, 235), panel.get_rect(), border_radius=16)
        pygame.draw.rect(panel, (255, 255, 255, 40), panel.get_rect(), width=2, border_radius=16)
        screen.blit(panel, rect.topleft)

    def draw_button(rect: pygame.Rect, label: str, is_hover: bool, is_selected: bool) -> None:
        btn = pygame.Surface((rect.w, rect.h), pygame.SRCALPHA)

        base = (32, 32, 46, 230)
        hover = (44, 44, 64, 235)
        sel = (70, 70, 110, 245)

        col = sel if is_selected else hover if is_hover else base
        pygame.draw.rect(btn, col, btn.get_rect(), border_radius=14)
        pygame.draw.rect(
            btn,
            (255, 255, 255, 60 if (is_hover or is_selected) else 35),
            btn.get_rect(),
            width=2,
            border_radius=14,
        )

        if is_selected:
            pygame.draw.rect(btn, (255, 255, 255, 70), pygame.Rect(10, 8, rect.w - 20, 2), border_radius=2)

        text = ui_font.render(label, True, (245, 245, 245))
        btn.blit(text, text.get_rect(center=(rect.w // 2, rect.h // 2)))
        screen.blit(btn, rect.topleft)

    def blit_icon(sprite: Optional[pygame.Surface], x: int, y: int, size: int = 26) -> None:
        if not sprite:
            return
        icon = pygame.transform.smoothscale(sprite, (size, size))
        screen.blit(icon, (x, y))

    # -----------------------------
    # Fog difficulty settings
    # -----------------------------
    DIFF: Dict[str, Dict[str, int]] = {
        "easy": {"radius_tiles": 10, "inner_dim_alpha": 55, "steps": 18},
        "medium": {"radius_tiles": 8, "inner_dim_alpha": 75, "steps": 16},
        "hard": {"radius_tiles": 6, "inner_dim_alpha": 95, "steps": 14},
    }

    def pick_difficulty() -> str:
        selected = difficulty if difficulty in ("easy", "medium", "hard") else "medium"

        card_w = min(600, width_px - 80)
        card_h = min(420, height_px - 80)
        card = pygame.Rect(0, 0, card_w, card_h)
        card.center = (width_px // 2, height_px // 2)

        top_pad = 120
        bottom_pad = 72
        gap = 12

        available_h = card_h - top_pad - bottom_pad
        btn_h = max(46, min(62, (available_h - 2 * gap) // 3))
        btn_w = card_w - 80
        bx = card.x + 40
        by = card.y + top_pad

        buttons = [
            ("easy", pygame.Rect(bx, by + 0 * (btn_h + gap), btn_w, btn_h), "Easy  •  More visibility"),
            ("medium", pygame.Rect(bx, by + 1 * (btn_h + gap), btn_w, btn_h), "Medium  •  Balanced"),
            ("hard", pygame.Rect(bx, by + 2 * (btn_h + gap), btn_w, btn_h), "Hard  •  Less visibility"),
        ]

        while True:
            clock.tick(60)
            mx, my = pygame.mouse.get_pos()

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return "easy"

                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return "easy"
                    if event.key == pygame.K_1:
                        return "easy"
                    if event.key == pygame.K_2:
                        return "medium"
                    if event.key == pygame.K_3:
                        return "hard"
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return selected

                    if event.key in (pygame.K_UP, pygame.K_w):
                        selected = "easy" if selected == "medium" else "medium" if selected == "hard" else "easy"
                    if event.key in (pygame.K_DOWN, pygame.K_s):
                        selected = "hard" if selected == "medium" else "medium" if selected == "easy" else "hard"

                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    for key, r, _ in buttons:
                        if r.collidepoint(mx, my):
                            selected = key
                            return selected

            draw_vertical_gradient_bg()
            draw_card(card)

            title = font.render("CAVE ESCAPE", True, (255, 255, 255))
            subtitle = ui_font.render("Cellular Automata Dungeon • Choose difficulty", True, (210, 210, 210))
            screen.blit(title, title.get_rect(center=(card.centerx, card.y + 50)))
            screen.blit(subtitle, subtitle.get_rect(center=(card.centerx, card.y + 86)))

            hint = ui_font.render("1/2/3 • ENTER • Click a button • ESC quits", True, (180, 180, 180))
            screen.blit(hint, hint.get_rect(center=(card.centerx, card.bottom - 28)))

            for key, r, label in buttons:
                hover = r.collidepoint(mx, my)
                draw_button(r, label, hover, key == selected)

            pygame.display.flip()

    difficulty_chosen = pick_difficulty()
    fog_cfg = DIFF.get(difficulty_chosen, DIFF["medium"])
    radius_px = fog_cfg["radius_tiles"] * tile_size
    inner_dim_alpha = fog_cfg["inner_dim_alpha"]
    steps = fog_cfg["steps"]

    # --- Combat tuning by difficulty ---
    ENEMY_MAX_HP = {"easy": 2, "medium": 3, "hard": 4}.get(difficulty_chosen, 3)
    ENEMY_MIN_HP = 2

    # --- Game state ---
    player_x, player_y = start_pos
    won = False
    dead = False

    player_max_hp = 3
    hp = player_max_hp

    last_dir = (0, 1)

    attack_timer = 0
    attack_dir = (0, 1)
    ATTACK_FRAMES = 8

    stamina_max = 2
    stamina = stamina_max

    spike_cooldown_moves = 0
    SPIKE_COOLDOWN = 2

    enemy_hit_cooldown_moves = 0
    ENEMY_HIT_COOLDOWN = 1

    hurt_timer = 0
    screen_flash_timer = 0
    HURT_FRAMES = 18
    FLASH_FRAMES = 10

    floating_texts: List[Tuple[int, int, int, str, Tuple[int, int, int]]] = []

    # --- Hold-to-move settings ---
    MOVE_INITIAL_DELAY_MS = 170
    MOVE_REPEAT_MS = 85
    held_dir: Optional[Tuple[int, int]] = None
    next_move_time_ms = 0

    hold_paused_by_threat = False

    # --- Endless waves ---
    wave = 1
    WAVE_BASE = 4
    WAVE_GROWTH = 1
    WAVE_MAX = 18
    RESPAWN_MIN_DIST = 8

    wave_warning_frames = 0
    pending_wave_spawn = False

    # Enemy HP maps
    enemy_hp: Dict[Tuple[int, int], int] = {}
    enemy_max_hp: Dict[Tuple[int, int], int] = {}
    for p in enemies:
        mhp = random.randint(ENEMY_MIN_HP, ENEMY_MAX_HP)
        enemy_hp[p] = mhp
        enemy_max_hp[p] = mhp

    SHUFFLE_CHANCE = 0.35
    TIE_JITTER = True

    # -----------------------------
    # Core helpers
    # -----------------------------
    def is_floor(x: int, y: int) -> bool:
        return grid.in_bounds(x, y) and grid.get_cell(x, y) == FLOOR

    def neighbors4(x: int, y: int) -> List[Tuple[int, int]]:
        return [(x + 1, y), (x - 1, y), (x, y + 1), (x, y - 1)]

    def any_enemy_adjacent() -> bool:
        for nx, ny in neighbors4(player_x, player_y):
            if (nx, ny) in enemies:
                return True
        return False

    def get_adjacent_enemies() -> List[Tuple[int, int]]:
        adj = []
        for nx, ny in neighbors4(player_x, player_y):
            if (nx, ny) in enemies:
                adj.append((nx, ny))
        return adj

    def show_text_world(tile_x: int, tile_y: int, text: str, color: Tuple[int, int, int]) -> None:
        px = tile_x * tile_size + tile_size // 2
        py = tile_y * tile_size - 6
        floating_texts.append((px, py, 28, text, color))

    def show_damage_feedback_player(amount: int) -> None:
        nonlocal hurt_timer, screen_flash_timer
        hurt_timer = HURT_FRAMES
        screen_flash_timer = FLASH_FRAMES
        show_text_world(player_x, player_y, f"-{amount}", (255, 80, 80))

    def try_damage_player(amount: int) -> None:
        nonlocal hp, dead
        hp -= amount
        show_damage_feedback_player(amount)
        if hp <= 0:
            dead = True

    def try_heal_player(amount: int) -> None:
        nonlocal hp
        if hp <= 0:
            return
        before = hp
        hp = min(player_max_hp, hp + amount)
        gained = hp - before
        if gained > 0:
            show_text_world(player_x, player_y, f"+{gained}", (80, 255, 120))

    def aim_dir_from_mouse(mx: int, my: int) -> Tuple[int, int]:
        tile_mx = mx // tile_size
        tile_my = my // tile_size
        dx_tile = tile_mx - player_x
        dy_tile = tile_my - player_y
        if abs(dx_tile) + abs(dy_tile) == 1 and (tile_mx, tile_my) in enemies:
            return (dx_tile, dy_tile)

        pcx = player_x * tile_size + tile_size // 2
        pcy = player_y * tile_size + tile_size // 2
        dx = mx - pcx
        dy = my - pcy
        if dx == 0 and dy == 0:
            return last_dir
        if abs(dx) >= abs(dy):
            return (1, 0) if dx > 0 else (-1, 0)
        return (0, 1) if dy > 0 else (0, -1)

    def rotated_sword(dir_xy: Tuple[int, int]) -> Optional[pygame.Surface]:
        if not sword_img:
            return None
        dx, dy = dir_xy
        if (dx, dy) == (0, -1):
            return sword_img
        if (dx, dy) == (0, 1):
            return pygame.transform.rotate(sword_img, 180)
        if (dx, dy) == (-1, 0):
            return pygame.transform.rotate(sword_img, 90)
        if (dx, dy) == (1, 0):
            return pygame.transform.rotate(sword_img, -90)
        return sword_img

    # -----------------------------
    # Rules screen
    # -----------------------------
    def show_rules_screen() -> None:
        card_w = min(820, width_px - 80)
        card_h = min(560, height_px - 80)
        card = pygame.Rect(0, 0, card_w, card_h)
        card.center = (width_px // 2, height_px // 2)

        pulse = 0.0
        icon_size = 28

        small_mode = card_h < 520 or card_w < 760
        line_gap = 24 if small_mode else 26
        section_gap = 10 if small_mode else 12

        while True:
            clock.tick(60)
            pulse += 0.08

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    return
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        pygame.quit()
                        return
                    if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                        return
                if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    return

            draw_vertical_gradient_bg()
            draw_card(card)

            title = font.render("How To Play", True, (255, 255, 255))
            sub = ui_font.render(
                f"Difficulty: {difficulty_chosen.upper()}  •  Turn-based  •  Fog-of-war",
                True,
                (210, 210, 210),
            )
            screen.blit(title, title.get_rect(center=(card.centerx, card.y + 48)))
            screen.blit(sub, sub.get_rect(center=(card.centerx, card.y + 84)))

            ix = card.x + 40
            iy = card.y + 108
            blit_icon(player_img, ix + 0 * 44, iy, icon_size)
            blit_icon(sword_img, ix + 1 * 44, iy, icon_size)
            blit_icon(torch_img, ix + 2 * 44, iy, icon_size)
            blit_icon(spike_img, ix + 3 * 44, iy, icon_size)
            blit_icon(skeleton_img, ix + 4 * 44, iy, icon_size)
            blit_icon(exit_img, ix + 5 * 44, iy, icon_size)
            blit_icon(heal_img, ix + 6 * 44, iy, icon_size)

            content_top = card.y + 150
            footer_h = 58
            content_bottom = card.bottom - footer_h

            x_left = card.x + 40
            y = content_top

            def heading(text: str) -> None:
                nonlocal y
                if y + line_gap > content_bottom:
                    return
                h = rules_font.render(text, True, (255, 255, 255))
                screen.blit(h, (x_left, y))
                y += line_gap

            def bullet(text: str) -> None:
                nonlocal y
                if y + line_gap > content_bottom:
                    return
                b = rules_font.render("• " + text, True, (230, 230, 230))
                screen.blit(b, (x_left + 10, y))
                y += line_gap

            heading("Objective")
            bullet("Reach the EXIT tile to escape.")

            y += section_gap
            heading("Turn System")
            bullet("Each MOVE or ATTACK ends your turn.")
            bullet("Then all enemies act.")
            bullet("Retreat Strike: moving away while adjacent deals 1 damage.")

            y += section_gap
            heading("Controls")
            bullet("Move: Hold WASD / Arrow Keys")
            bullet("Attack: Left Click (toward mouse) or SPACE")
            bullet("Restart: Press R")

            y += section_gap
            heading("Health")
            bullet("Green bottles restore 1 HP when stepped on.")

            y += section_gap
            heading("Stamina")
            bullet("Attacks reduce stamina, then it regenerates over turns.")
            bullet("You can ALWAYS attack (even at 0 stamina).")

            alpha = 150 + int(70 * (0.5 + 0.5 * math.sin(pulse)))
            footer = ui_font.render("Press ENTER / SPACE or Left Click to start", True, (255, 255, 255))
            footer_surf = pygame.Surface((footer.get_width() + 24, footer.get_height() + 16), pygame.SRCALPHA)
            footer_surf.fill((0, 0, 0, alpha))
            pygame.draw.rect(footer_surf, (255, 255, 255, 45), footer_surf.get_rect(), width=2, border_radius=12)

            fx = card.centerx - footer_surf.get_width() // 2
            fy = card.bottom - footer_h + 10
            screen.blit(footer_surf, (fx, fy))
            screen.blit(footer, (fx + 12, fy + 8))

            pygame.display.flip()

    show_rules_screen()

    # -----------------------------
    # Wave control
    # -----------------------------
    def schedule_next_wave() -> None:
        nonlocal pending_wave_spawn, wave_warning_frames
        if dead or won:
            return
        if len(enemies) > 0:
            return
        if pending_wave_spawn:
            return
        pending_wave_spawn = True
        wave_warning_frames = fps

    def spawn_enemy_wave_now() -> None:
        nonlocal wave, pending_wave_spawn
        if dead or won:
            pending_wave_spawn = False
            return

        start = (player_x, player_y)
        q = [(player_x, player_y)]
        dist = {start: 0}
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            d = dist[(x, y)]
            for nx, ny in neighbors4(x, y):
                if not is_floor(nx, ny):
                    continue
                if (nx, ny) in dist:
                    continue
                dist[(nx, ny)] = d + 1
                q.append((nx, ny))

        candidates = [
            p for p, dd in dist.items()
            if p != (player_x, player_y) and p != goal_pos and p not in traps and dd >= RESPAWN_MIN_DIST
        ]
        if not candidates:
            candidates = [p for p in dist.keys() if p != (player_x, player_y) and p != goal_pos and p not in traps]
        if not candidates:
            pending_wave_spawn = False
            return

        random.shuffle(candidates)
        n_to_spawn = min(WAVE_MAX, WAVE_BASE + (wave - 1) * WAVE_GROWTH)

        spawned = 0
        for p in candidates:
            if spawned >= n_to_spawn:
                break
            if p in enemies:
                continue
            enemies.add(p)
            mhp = random.randint(ENEMY_MIN_HP, ENEMY_MAX_HP)
            enemy_hp[p] = mhp
            enemy_max_hp[p] = mhp
            spawned += 1

        wave += 1
        pending_wave_spawn = False

    # -----------------------------
    # Enemy movement/pathfinding
    # -----------------------------
    def _enemy_walkable(x: int, y: int) -> bool:
        return is_floor(x, y) and ((x, y) not in traps)

    def enemy_turn() -> None:
        nonlocal enemy_hit_cooldown_moves, stamina
        if dead or won:
            return

        start = (player_x, player_y)
        q = [(player_x, player_y)]
        dist: Dict[Tuple[int, int], int] = {start: 0}
        head = 0
        while head < len(q):
            x, y = q[head]
            head += 1
            d = dist[(x, y)]
            for nx, ny in neighbors4(x, y):
                if not _enemy_walkable(nx, ny):
                    continue
                if (nx, ny) in dist:
                    continue
                dist[(nx, ny)] = d + 1
                q.append((nx, ny))

        occupied = set(enemies)
        new_positions: Set[Tuple[int, int]] = set()
        new_hp: Dict[Tuple[int, int], int] = {}
        new_max: Dict[Tuple[int, int], int] = {}

        enemy_list = list(enemies)
        t = pygame.time.get_ticks()
        enemy_list.sort(key=lambda p: ((p[0] * 73856093) ^ (p[1] * 19349663) ^ t))

        for (ex, ey) in enemy_list:
            hp_val = enemy_hp.get((ex, ey), ENEMY_MAX_HP)
            max_val = enemy_max_hp.get((ex, ey), ENEMY_MAX_HP)
            occupied.remove((ex, ey))

            if abs(ex - player_x) + abs(ey - player_y) == 1:
                if enemy_hit_cooldown_moves == 0 and not dead:
                    try_damage_player(1)
                    enemy_hit_cooldown_moves = ENEMY_HIT_COOLDOWN
                new_positions.add((ex, ey))
                new_hp[(ex, ey)] = hp_val
                new_max[(ex, ey)] = max_val
                occupied.add((ex, ey))
                continue

            if (ex, ey) not in dist:
                candidates = [(ex, ey)]
                for nx, ny in neighbors4(ex, ey):
                    if not _enemy_walkable(nx, ny):
                        continue
                    if (nx, ny) in occupied:
                        continue
                    if (nx, ny) == goal_pos:
                        continue
                    candidates.append((nx, ny))
                chosen = candidates[(t + ex * 7 + ey * 13) % len(candidates)]
                new_positions.add(chosen)
                new_hp[chosen] = hp_val
                new_max[chosen] = max_val
                occupied.add(chosen)
                continue

            candidates: List[Tuple[int, int]] = [(ex, ey)]
            for nx, ny in neighbors4(ex, ey):
                if not _enemy_walkable(nx, ny):
                    continue
                if (nx, ny) in occupied:
                    continue
                if (nx, ny) == goal_pos:
                    continue
                if (nx, ny) not in dist:
                    continue
                candidates.append((nx, ny))

            current_d = dist.get((ex, ey), 10**9)
            best_d = min(dist.get(p, 10**9) for p in candidates)

            if best_d < current_d:
                best_moves = [p for p in candidates if dist.get(p, 10**9) == best_d]
                chosen = random.choice(best_moves) if TIE_JITTER else best_moves[0]
            else:
                equal_moves = [p for p in candidates if dist.get(p, 10**9) == current_d and p != (ex, ey)]
                if equal_moves and random.random() < SHUFFLE_CHANCE:
                    chosen = random.choice(equal_moves)
                else:
                    chosen = (ex, ey)

            new_positions.add(chosen)
            new_hp[chosen] = hp_val
            new_max[chosen] = max_val
            occupied.add(chosen)

        enemies.clear()
        enemies.update(new_positions)
        enemy_hp.clear()
        enemy_hp.update(new_hp)
        enemy_max_hp.clear()
        enemy_max_hp.update(new_max)

        if len(enemies) == 0:
            schedule_next_wave()

        stamina = min(stamina_max, stamina + 1)

    # -----------------------------
    # Fog-of-war
    # -----------------------------
    def apply_fog_gradient() -> None:
        fog.fill((0, 0, 0, 255))
        cx = player_x * tile_size + tile_size // 2
        cy = player_y * tile_size + tile_size // 2
        for i in range(steps, 0, -1):
            r = int(radius_px * (i / steps))
            tt = i / steps
            alpha = int(inner_dim_alpha + (255 - inner_dim_alpha) * tt)
            pygame.draw.circle(fog, (0, 0, 0, alpha), (cx, cy), r)
        screen.blit(fog, (0, 0))

    # -----------------------------
    # Combat helper
    # -----------------------------
    def damage_enemy_at(pos: Tuple[int, int], amount: int = 1) -> None:
        tx, ty = pos
        if (tx, ty) not in enemies:
            return
        hp_val = enemy_hp.get((tx, ty), ENEMY_MAX_HP) - amount
        show_text_world(tx, ty, f"-{amount}", (255, 120, 120))
        if hp_val <= 0:
            enemies.remove((tx, ty))
            enemy_hp.pop((tx, ty), None)
            enemy_max_hp.pop((tx, ty), None)
            show_text_world(tx, ty, "X", (255, 200, 200))
        else:
            enemy_hp[(tx, ty)] = hp_val

    # -----------------------------
    # Player actions (turn-based)
    # -----------------------------
    def do_player_move(dx: int, dy: int) -> None:
        nonlocal player_x, player_y, last_dir, spike_cooldown_moves, enemy_hit_cooldown_moves, stamina
        if dead or won:
            return

        nx, ny = player_x + dx, player_y + dy

        if (nx, ny) in enemies:
            last_dir = (dx, dy)
            return

        if not is_floor(nx, ny):
            return

        # Retreat strike before moving (if adjacent enemies)
        adj_enemies = get_adjacent_enemies()
        if adj_enemies:
            behind = (player_x - dx, player_y - dy)
            target = behind if behind in enemies else adj_enemies[0]
            if stamina <= 0:
                show_text_world(player_x, player_y, "TIRED", (220, 220, 220))
            stamina = max(0, stamina - 1)
            damage_enemy_at(target, 1)

        player_x, player_y = nx, ny
        last_dir = (dx, dy)

        stamina = min(stamina_max, stamina + 1)

        if spike_cooldown_moves > 0:
            spike_cooldown_moves -= 1
        if enemy_hit_cooldown_moves > 0:
            enemy_hit_cooldown_moves -= 1

        # Heal pickup
        if (player_x, player_y) in heals:
            heals.remove((player_x, player_y))
            try_heal_player(1)

        if (player_x, player_y) in traps and spike_cooldown_moves == 0 and not dead:
            try_damage_player(1)
            spike_cooldown_moves = SPIKE_COOLDOWN

        enemy_turn()

    def do_player_attack(dir_xy: Tuple[int, int]) -> None:
        nonlocal attack_timer, attack_dir, last_dir, stamina
        if dead or won:
            return

        dx, dy = dir_xy
        if dx == 0 and dy == 0:
            return

        last_dir = (dx, dy)
        attack_timer = ATTACK_FRAMES
        attack_dir = (dx, dy)

        tx, ty = player_x + dx, player_y + dy

        if stamina <= 0:
            show_text_world(player_x, player_y, "TIRED", (220, 220, 220))
        stamina = max(0, stamina - 1)

        if (tx, ty) in enemies:
            damage_enemy_at((tx, ty), 1)

        enemy_turn()

    # -----------------------------
    # Drawing helpers (HP bars)
    # -----------------------------
    def draw_enemy_hp_bar(ex: int, ey: int) -> None:
        hp_val = enemy_hp.get((ex, ey), ENEMY_MAX_HP)
        max_val = enemy_max_hp.get((ex, ey), ENEMY_MAX_HP)
        if max_val <= 0:
            return
        bar_w = tile_size - 6
        bar_h = 6
        x = ex * tile_size + 3
        y = ey * tile_size + 2
        pygame.draw.rect(screen, (0, 0, 0), (x, y, bar_w, bar_h))
        fill_w = int(bar_w * (hp_val / max_val))
        fill_w = max(0, min(bar_w, fill_w))
        pygame.draw.rect(screen, (220, 60, 60), (x, y, fill_w, bar_h))
        pygame.draw.rect(screen, (240, 240, 240), (x, y, bar_w, bar_h), 1)

    def draw_player_world_hp_bar() -> None:
        bar_w = tile_size - 6
        bar_h = 6
        x = player_x * tile_size + 3
        y = player_y * tile_size - 6
        if y < 2:
            y = 2
        pygame.draw.rect(screen, (0, 0, 0), (x, y, bar_w, bar_h))
        frac = hp / max(1, player_max_hp)
        fill_w = int(bar_w * frac)
        fill_w = max(0, min(bar_w, fill_w))
        pygame.draw.rect(screen, (60, 200, 80), (x, y, fill_w, bar_h))
        pygame.draw.rect(screen, (240, 240, 240), (x, y, bar_w, bar_h), 1)

    # -----------------------------
    # Scene rendering
    # -----------------------------
    def draw_scene() -> None:
        for y in range(grid.h):
            for x in range(grid.w):
                rect = pygame.Rect(x * tile_size, y * tile_size, tile_size, tile_size)
                if grid.get_cell(x, y) == FLOOR:
                    use_alt = floor_alt_img is not None and ((x * 73856093) ^ (y * 19349663)) % 11 == 0
                    if use_alt and floor_alt_img:
                        screen.blit(floor_alt_img, rect)
                    elif floor_img:
                        screen.blit(floor_img, rect)
                    else:
                        pygame.draw.rect(screen, (190, 160, 120), rect)
                else:
                    if wall_border_img:
                        screen.blit(wall_border_img, rect)
                    else:
                        pygame.draw.rect(screen, (45, 45, 60), rect)

        for (tx, ty) in torches:
            if torch_img:
                screen.blit(torch_img, (tx * tile_size, ty * tile_size))

        for (tx, ty) in traps:
            if spike_img:
                screen.blit(spike_img, (tx * tile_size, ty * tile_size))

        for (hx, hy) in heals:
            if heal_img:
                screen.blit(heal_img, (hx * tile_size, hy * tile_size))
            else:
                pygame.draw.rect(
                    screen,
                    (60, 200, 80),
                    pygame.Rect(hx * tile_size + 10, hy * tile_size + 10, tile_size - 20, tile_size - 20),
                    border_radius=6,
                )

        if exit_img:
            gx, gy = goal_pos
            screen.blit(exit_img, (gx * tile_size, gy * tile_size))

        for (ex, ey) in enemies:
            if skeleton_img:
                screen.blit(skeleton_img, (ex * tile_size, ey * tile_size))
            draw_enemy_hp_bar(ex, ey)

        blink_off = (hurt_timer > 0) and ((hurt_timer // 3) % 2 == 0)
        if not blink_off and player_img:
            if hurt_timer > 0:
                tinted = player_img.copy()
                tint = pygame.Surface((tile_size, tile_size), pygame.SRCALPHA)
                tint.fill((255, 60, 60, 120))
                tinted.blit(tint, (0, 0), special_flags=pygame.BLEND_RGBA_ADD)
                screen.blit(tinted, (player_x * tile_size, player_y * tile_size))
            else:
                screen.blit(player_img, (player_x * tile_size, player_y * tile_size))

        if not dead and not won:
            draw_player_world_hp_bar()

        if attack_timer > 0 and sword_img:
            dx, dy = attack_dir
            offset_x = dx * (tile_size // 3)
            offset_y = dy * (tile_size // 3)
            sword_surface = rotated_sword((dx, dy))
            screen.blit(sword_surface, (player_x * tile_size + offset_x, player_y * tile_size + offset_y))

        for (px, py, _, text, color) in floating_texts:
            t_surf = ui_font.render(text, True, color)
            screen.blit(t_surf, t_surf.get_rect(center=(px, py)))

        pygame.draw.rect(screen, (20, 20, 30), screen.get_rect(), 4)

        if screen_flash_timer > 0:
            alpha = int(120 * (screen_flash_timer / FLASH_FRAMES))
            red_flash.fill((255, 0, 0, alpha))
            screen.blit(red_flash, (0, 0))

        if wave_warning_frames > 0 and pending_wave_spawn:
            banner = banner_font.render(f"WAVE {wave} INCOMING...", True, (255, 255, 255))
            back = pygame.Surface((banner.get_width() + 30, banner.get_height() + 18), pygame.SRCALPHA)
            back.fill((0, 0, 0, 170))
            bx = (width_px - back.get_width()) // 2
            by = 10
            screen.blit(back, (bx, by))
            screen.blit(banner, (bx + 15, by + 9))

    def draw_win_overlay() -> None:
        overlay = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        screen.blit(overlay, (0, 0))
        text = font.render("You escaped!", True, (255, 255, 255))
        hint = ui_font.render("Press R to restart, ESC to quit", True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=(width_px // 2, height_px // 2 - 10)))
        screen.blit(hint, hint.get_rect(center=(width_px // 2, height_px // 2 + 35)))

    def draw_dead_overlay() -> None:
        overlay = pygame.Surface((width_px, height_px), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 190))
        screen.blit(overlay, (0, 0))
        text = font.render("You died!", True, (255, 255, 255))
        hint = ui_font.render("Press R to restart, ESC to quit", True, (255, 255, 255))
        screen.blit(text, text.get_rect(center=(width_px // 2, height_px // 2 - 10)))
        screen.blit(hint, hint.get_rect(center=(width_px // 2, height_px // 2 + 35)))

    # -----------------------------
    # Main loop
    # -----------------------------
    running = True
    action = "quit"

    if len(enemies) == 0:
        schedule_next_wave()

    while running:
        now_ms = pygame.time.get_ticks()
        clock.tick(fps)

        if wave_warning_frames > 0:
            wave_warning_frames -= 1
            if wave_warning_frames == 0 and pending_wave_spawn:
                spawn_enemy_wave_now()

        if hurt_timer > 0:
            hurt_timer -= 1
        if screen_flash_timer > 0:
            screen_flash_timer -= 1

        new_texts: List[Tuple[int, int, int, str, Tuple[int, int, int]]] = []
        for (px, py, frames, text, color) in floating_texts:
            frames -= 1
            py -= 1
            if frames > 0:
                new_texts.append((px, py, frames, text, color))
        floating_texts = new_texts

        if attack_timer > 0:
            attack_timer -= 1

        if any_enemy_adjacent():
            if held_dir is not None:
                held_dir = None
            hold_paused_by_threat = True

        acted_this_frame = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
                action = "quit"

            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    running = False
                    action = "quit"
                    continue

                if event.key == pygame.K_r:
                    running = False
                    action = "regen"
                    continue

                if dead:
                    continue

                if event.key == pygame.K_SPACE and not won and not acted_this_frame:
                    do_player_attack(last_dir)
                    acted_this_frame = True
                    continue

                dx, dy = 0, 0
                if event.key in (pygame.K_w, pygame.K_UP):
                    dy = -1
                elif event.key in (pygame.K_s, pygame.K_DOWN):
                    dy = 1
                elif event.key in (pygame.K_a, pygame.K_LEFT):
                    dx = -1
                elif event.key in (pygame.K_d, pygame.K_RIGHT):
                    dx = 1

                if (dx or dy) and (not won) and (not acted_this_frame):
                    do_player_move(dx, dy)
                    acted_this_frame = True

                    if not any_enemy_adjacent():
                        held_dir = (dx, dy)
                        next_move_time_ms = now_ms + MOVE_INITIAL_DELAY_MS
                    else:
                        held_dir = None

            elif event.type == pygame.KEYUP:
                if held_dir is None:
                    continue

                k = event.key
                release_dir = None
                if k in (pygame.K_w, pygame.K_UP):
                    release_dir = (0, -1)
                elif k in (pygame.K_s, pygame.K_DOWN):
                    release_dir = (0, 1)
                elif k in (pygame.K_a, pygame.K_LEFT):
                    release_dir = (-1, 0)
                elif k in (pygame.K_d, pygame.K_RIGHT):
                    release_dir = (1, 0)

                if release_dir == held_dir:
                    held_dir = None

            elif event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1 and not dead and not won and not acted_this_frame:
                    do_player_attack(aim_dir_from_mouse(*event.pos))
                    acted_this_frame = True

        if (not acted_this_frame) and (not dead) and (not won):
            if any_enemy_adjacent():
                held_dir = None
                hold_paused_by_threat = True
            else:
                if (not hold_paused_by_threat) and held_dir is not None and now_ms >= next_move_time_ms:
                    do_player_move(held_dir[0], held_dir[1])
                    next_move_time_ms = now_ms + MOVE_REPEAT_MS

        if not dead and not won and len(enemies) == 0:
            schedule_next_wave()

        if not dead and not won and (player_x, player_y) == goal_pos:
            won = True

        screen.fill((0, 0, 0))
        draw_scene()
        apply_fog_gradient()

        if won:
            draw_win_overlay()
        elif dead:
            draw_dead_overlay()

        pygame.display.flip()

    pygame.quit()
    return action, difficulty_chosen