import math
import random
import time
from collections import deque
import pygame

# ---------------------------------
# Pac-Man — Tile-perfect movement
# ---------------------------------
# Controls:
#   Arrows / WASD  -> move
#   Enter          -> start / restart
#   P              -> pause
#   Esc            -> quit

# ------------------------------------------------
# Window, grid, timing
# ------------------------------------------------
WIDTH, HEIGHT = 800, 840
GRID_W, GRID_H = 28, 31
TILE = 24
MAZE_OFFSET_X = (WIDTH - GRID_W * TILE) // 2
MAZE_OFFSET_Y = 60
TITLE = "Pac-Man (tile-perfect)"

RENDER_FPS = 120
SIM_HZ = 240
DT = 1.0 / SIM_HZ

# ------------------------------------------------
# Gameplay parameters (close to classic feel)
# ------------------------------------------------
# Speeds are in tiles/second (cleaner for grid stepping)
PAC_SPEED_TPS = 7.5          # Pac-Man default speed (≈ 7.5 tiles/s)
GHOST_SPEED_TPS = 7.0        # normal ghost speed
FRIGHT_SPEED_TPS = 5.5       # frightened ghosts slower
EYES_SPEED_TPS = 12.0        # eyes go fast back to house

FRIGHTENED_TIME = 6.0
RELEASE_INTERVAL = 3.0

PELLET_SCORE = 10
POWER_SCORE = 50
GHOST_EAT_SCORES = [200, 400, 800, 1600]

TUNNEL_ROW = 15

# Scatter/Chase schedule (simplified classic)
MODE_SCHEDULE = [
    ("scatter", 7),
    ("chase", 20),
    ("scatter", 7),
    ("chase", 20),
    ("scatter", 5),
    ("chase", 9999),
]

# ------------------------------------------------
# Colors
# ------------------------------------------------
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
WALL_BLUE = (0, 55, 200)
YELLOW = (255, 210, 0)
RED = (255, 0, 0)
PINK = (255, 105, 180)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
FRIGHT_BLUE = (50, 90, 255)

# ------------------------------------------------
# Maze
# ------------------------------------------------
MAZE_LAYOUT = [
"############################",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#o####.#####.##.#####.####o#",
"#.####.#####.##.#####.####.#",
"#..........................#",
"#.####.##.########.##.####.#",
"#.####.##.########.##.####.#",
"#......##....##....##......#",
"######.#####.##.#####.######",
"######.##..........##.######",
"######.##.###==###.##.######",
"######.##.#      #.##.######",
"######.##.# GGGG #.##.######",
"######.##.#      #.##.######",
"............    ............",
"######.##.###  ###.##.######",
"######.##.....P....##.######",
"######.##.########.##.######",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#o####.#####.##.#####.####o#",
"#...##................##...#",
"###.##.##.########.##.##.###",
"#......##....##....##......#",
"#.##########.##.##########.#",
"#..........................#",
"#.####.#####.##.#####.####.#",
"#o####.#####.##.#####.####o#",
"#............##............#",
"############################",
]

# ------------------------------------------------
# Helpers
# ------------------------------------------------
DIRS = {
    "left":  pygame.Vector2(-1, 0),
    "right": pygame.Vector2(1, 0),
    "up":    pygame.Vector2(0, -1),
    "down":  pygame.Vector2(0, 1),
}
ORDERED_DIRS = ["up", "left", "down", "right"]
OPPOSITE = {"left": "right", "right": "left", "up": "down", "down": "up"}

def in_bounds(c, r):
    return 0 <= c < GRID_W and 0 <= r < GRID_H

def tile_center_px(c, r):
    return (
        MAZE_OFFSET_X + c * TILE + TILE // 2,
        MAZE_OFFSET_Y + r * TILE + TILE // 2,
    )

def px_to_tile(x, y):
    c = int((x - MAZE_OFFSET_X) // TILE)
    r = int((y - MAZE_OFFSET_Y) // TILE)
    return c, r

def manhattan(a, b):
    (ax, ay), (bx, by) = a, b
    return abs(ax - bx) + abs(ay - by)

# ------------------------------------------------
# Maze class (walls, pellets, gate)
# ------------------------------------------------
class Maze:
    def __init__(self, layout):
        self.raw = [list(r) for r in layout]
        self.walls = set()
        self.gate = set()
        self.pellets = set()
        self.power = set()
        self.ghost_starts = []
        self.pac_start = None
        self.parse()

    def parse(self):
        for r in range(GRID_H):
            for c in range(GRID_W):
                ch = self.raw[r][c]
                if ch == "#":
                    self.walls.add((c, r))
                elif ch == "=":
                    self.gate.add((c, r))
                elif ch == ".":
                    self.pellets.add((c, r))
                    self.raw[r][c] = " "
                elif ch == "o":
                    self.power.add((c, r))
                    self.raw[r][c] = " "
                elif ch == "G":
                    self.ghost_starts.append((c, r))
                    self.raw[r][c] = " "
                elif ch == "P":
                    self.pac_start = (c, r)
                    self.raw[r][c] = " "

    def passable_for_pac(self, c, r):
        if not in_bounds(c, r):
            return r == TUNNEL_ROW
        return (c, r) not in self.walls and (c, r) not in self.gate

    def passable_for_ghost(self, c, r, can_use_gate=False):
        if not in_bounds(c, r):
            return r == TUNNEL_ROW
        if (c, r) in self.walls:
            return False
        if (c, r) in self.gate and not can_use_gate:
            return False
        return True

    def draw(self, surf):
        # walls
        for (c, r) in self.walls:
            x = MAZE_OFFSET_X + c * TILE
            y = MAZE_OFFSET_Y + r * TILE
            pygame.draw.rect(surf, WALL_BLUE, (x, y, TILE, TILE))
        # gate
        for (c, r) in self.gate:
            x, y = tile_center_px(c, r)
            pygame.draw.line(surf, WHITE, (x - TILE//2 + 4, y), (x + TILE//2 - 4, y), 2)
        # pellets
        for (c, r) in self.pellets:
            x, y = tile_center_px(c, r)
            pygame.draw.circle(surf, WHITE, (x, y), 3)
        # power
        for (c, r) in self.power:
            x, y = tile_center_px(c, r)
            pygame.draw.circle(surf, WHITE, (x, y), 6)

# ------------------------------------------------
# TileStepper: the key to arcade-accurate motion
# ------------------------------------------------
class TileStepper:
    """
    Moves exactly along the grid:
    - Keeps a current tile (c,r) and a facing direction.
    - Has a sub-tile progress 't' in pixels toward the next tile center.
    - At each tile CENTER, it may accept a buffered turn if that next tile is free.
    - If forward blocked, it stops at center; no corner cutting.
    """
    def __init__(self, maze, c, r, dir_name=None, speed_tps=7.5):
        self.maze = maze
        self.c, self.r = c, r
        self.dir_name = dir_name          # 'left'/'right'/'up'/'down' or None
        self.next_buffer = None           # buffered desired dir from input/AI
        self.speed_px = speed_tps * TILE  # pixels/sec
        self.progress_px = 0.0            # progress from center toward next center (0..TILE)
        self.pos = pygame.Vector2(*tile_center_px(c, r))

    def set_speed_tps(self, tps):
        self.speed_px = tps * TILE

    def set_buffer(self, dir_name):
        self.next_buffer = dir_name

    def can_enter(self, c, r, for_ghost=False, can_use_gate=False):
        if for_ghost:
            return self.maze.passable_for_ghost(c, r, can_use_gate=can_use_gate)
        return self.maze.passable_for_pac(c, r)

    def at_center(self):
        cx, cy = tile_center_px(self.c, self.r)
        return abs(self.pos.x - cx) < 0.5 and abs(self.pos.y - cy) < 0.5

    def _try_commit_turn_at_center(self, for_ghost=False, can_use_gate=False):
        if not self.next_buffer:
            return False
        dc, dr = int(DIRS[self.next_buffer].x), int(DIRS[self.next_buffer].y)
        nc, nr = self.c + dc, self.r + dr
        # tunnel wrap preview
        if nr == TUNNEL_ROW and not in_bounds(nc, nr):
            if nc < 0: nc = GRID_W - 1
            if nc >= GRID_W: nc = 0
        if self.can_enter(nc, nr, for_ghost=for_ghost, can_use_gate=can_use_gate):
            self.dir_name = self.next_buffer
            self.next_buffer = None
            return True
        return False

    def _forward_target_tile(self):
        if not self.dir_name:
            return self.c, self.r
        dc, dr = int(DIRS[self.dir_name].x), int(DIRS[self.dir_name].y)
        nc, nr = self.c + dc, self.r + dr
        # tunnel wrap
        if nr == TUNNEL_ROW and not in_bounds(nc, nr):
            if nc < 0: nc = GRID_W - 1
            if nc >= GRID_W: nc = 0
        return nc, nr

    def tick(self, dt, for_ghost=False, can_use_gate=False):
        # If sitting at center, first try to take buffered turn.
        if self.at_center():
            cx, cy = tile_center_px(self.c, self.r)
            self.pos.update(cx, cy)
            if self._try_commit_turn_at_center(for_ghost=for_ghost, can_use_gate=can_use_gate):
                pass  # committed the turn
            # If no current dir, try to set from buffer straight ahead
            if not self.dir_name and self.next_buffer:
                self._try_commit_turn_at_center(for_ghost=for_ghost, can_use_gate=can_use_gate)

        # Decide forward tile and whether movement is possible
        target_c, target_r = self._forward_target_tile()
        can_go = self.dir_name and self.can_enter(target_c, target_r, for_ghost=for_ghost, can_use_gate=can_use_gate)

        # Move along the center-to-center line
        if can_go:
            move_px = self.speed_px * dt
            self.progress_px += move_px
            # advance whole tiles if accumulated
            while self.progress_px >= TILE:
                # arrive exactly at next tile center
                self.c, self.r = target_c, target_r
                self.pos.update(*tile_center_px(self.c, self.r))
                self.progress_px -= TILE
                # tunnel wrap already applied in _forward_target_tile
                target_c, target_r = self._forward_target_tile()
                can_go = self.dir_name and self.can_enter(target_c, target_r, for_ghost=for_ghost, can_use_gate=can_use_gate)
                if not can_go:
                    self.progress_px = 0.0
                    break

            # move partially toward next center if still traveling
            if can_go and self.progress_px > 0:
                # set position between centers along dir
                cx, cy = tile_center_px(self.c, self.r)
                dx, dy = DIRS[self.dir_name].x, DIRS[self.dir_name].y
                self.pos.x = cx + dx * self.progress_px
                self.pos.y = cy + dy * self.progress_px
        else:
            # Stop at center; no corner cutting.
            cx, cy = tile_center_px(self.c, self.r)
            self.pos.update(cx, cy)
            self.progress_px = 0.0

        # Handle out-of-bounds x wrap (visual continuity) when on tunnel row
        if self.r == TUNNEL_ROW:
            left_lim = MAZE_OFFSET_X - TILE * 0.75
            right_lim = MAZE_OFFSET_X + GRID_W * TILE + TILE * 0.75
            if self.pos.x < left_lim:
                self.pos.x = MAZE_OFFSET_X + GRID_W * TILE + TILE * 0.5
            elif self.pos.x > right_lim:
                self.pos.x = MAZE_OFFSET_X - TILE * 0.5

        return int(self.pos.x), int(self.pos.y)

# ------------------------------------------------
# Entities
# ------------------------------------------------
class Pacman:
    def __init__(self, maze, level=1):
        self.maze = maze
        c, r = maze.pac_start
        self.stepper = TileStepper(maze, c, r, dir_name=None, speed_tps=PAC_SPEED_TPS + 0.25*(level-1))
        self.radius = 10
        self.mouth_phase = 0.0
        self.dir_name = None  # cached for draw

    def reset(self, level=1):
        c, r = self.maze.pac_start
        self.stepper = TileStepper(self.maze, c, r, dir_name=None, speed_tps=PAC_SPEED_TPS + 0.25*(level-1))
        self.radius = 10
        self.mouth_phase = 0.0
        self.dir_name = None

    def handle_input(self, keys):
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.stepper.set_buffer("left")
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.stepper.set_buffer("right")
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            self.stepper.set_buffer("up")
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.stepper.set_buffer("down")

    def update(self, dt):
        x, y = self.stepper.tick(dt, for_ghost=False)
        self.dir_name = self.stepper.dir_name
        self.mouth_phase += 6.0 * dt
        return x, y

    @property
    def tile(self):
        return self.stepper.c, self.stepper.r

    @property
    def pos(self):
        return pygame.Vector2(*tile_center_px(self.stepper.c, self.stepper.r)) if self.stepper.at_center() else self.stepper.pos

    def draw(self, surf):
        x, y = int(self.stepper.pos.x), int(self.stepper.pos.y)
        # mouth animation + facing
        angle = (math.sin(self.mouth_phase) * 0.4 + 0.6) * math.pi / 4
        if self.dir_name == "left":
            start, end = math.pi + angle, math.pi - angle
        elif self.dir_name == "right":
            start, end = -angle, angle
        elif self.dir_name == "up":
            start, end = -math.pi/2 - angle, -math.pi/2 + angle
        elif self.dir_name == "down":
            start, end = math.pi/2 - angle, math.pi/2 + angle
        else:
            start, end = 0, 2 * math.pi

        pygame.draw.circle(surf, YELLOW, (x, y), self.radius)
        if self.dir_name:
            pygame.draw.polygon(
                surf, BLACK,
                [(x, y),
                 (x + int(self.radius * math.cos(start)), y + int(self.radius * math.sin(start))),
                 (x + int(self.radius * math.cos(end)),   y + int(self.radius * math.sin(end)))],
            )

class Ghost:
    def __init__(self, maze, name, color, start_tile, house_tiles, level=1, start_outside=False, gate_tiles=None):
        self.maze = maze
        self.name = name
        self.color = color
        self.house = set(house_tiles)
        self.gate_tiles = set(gate_tiles or [])
        self.state = "chase" if start_outside else "in_house"
        self.leaving = start_outside
        self.fright_timer = 0.0
        self.respawn_timer = 0.0

        c, r = start_tile
        dir0 = random.choice(["left", "right", "up", "down"]) if start_outside else None
        self.stepper = TileStepper(maze, c, r, dir_name=dir0, speed_tps=GHOST_SPEED_TPS + 0.2*(level-1))
        self.fr_speed = FRIGHT_SPEED_TPS + 0.2*(level-1)
        self.eyes_speed = EYES_SPEED_TPS
        self.radius = 10

        self.scatter_targets = {
            "blinky": (GRID_W - 2, 1),
            "pinky": (1, 1),
            "inky": (GRID_W - 2, GRID_H - 2),
            "clyde": (1, GRID_H - 2),
        }

    def can_use_gate(self):
        return self.state in ("leaving", "eyes")

    def cur_speed_tps(self):
        if self.state == "eyes":
            return self.eyes_speed
        elif self.state == "frightened":
            return self.fr_speed
        else:
            return GHOST_SPEED_TPS

    @property
    def tile(self):
        return self.stepper.c, self.stepper.r

    def at_center(self):
        return self.stepper.at_center()

    def update_state_timers(self, dt):
        if self.state == "frightened":
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                self.state = "chase"

        if self.state in ("in_house",) and self.respawn_timer > 0:
            self.respawn_timer -= dt

    def choose_dir(self, target_tile):
        # Greedy at intersections (arcade orders tie by Up, Left, Down, Right)
        if not self.at_center():
            return
        # snap to center
        cx, cy = tile_center_px(self.stepper.c, self.stepper.r)
        self.stepper.pos.update(cx, cy)

        # frightened => random valid (no reverse bias)
        if self.state == "frightened":
            moves = []
            for d in ORDERED_DIRS:
                if self.stepper.dir_name and d == OPPOSITE[self.stepper.dir_name]:
                    continue
                dc, dr = int(DIRS[d].x), int(DIRS[d].y)
                nc, nr = self.stepper.c + dc, self.stepper.r + dr
                if nr == TUNNEL_ROW and not in_bounds(nc, nr):
                    if nc < 0: nc = GRID_W - 1
                    if nc >= GRID_W: nc = 0
                if self.maze.passable_for_ghost(nc, nr, can_use_gate=self.can_use_gate()):
                    moves.append(d)
            if not moves and self.stepper.dir_name:
                moves = [OPPOSITE[self.stepper.dir_name]]
            if moves:
                self.stepper.dir_name = random.choice(moves)
            return

        # chase/scatter
        best_d, best_h = None, 10**9
        for d in ORDERED_DIRS:
            if self.stepper.dir_name and d == OPPOSITE[self.stepper.dir_name]:
                continue
            dc, dr = int(DIRS[d].x), int(DIRS[d].y)
            nc, nr = self.stepper.c + dc, self.stepper.r + dr
            if nr == TUNNEL_ROW and not in_bounds(nc, nr):
                if nc < 0: nc = GRID_W - 1
                if nc >= GRID_W: nc = 0
            if not self.maze.passable_for_ghost(nc, nr, can_use_gate=self.can_use_gate()):
                continue
            h = manhattan((nc, nr), target_tile)
            if h < best_h:
                best_h, best_d = h, d
        if best_d is None and self.stepper.dir_name:
            best_d = OPPOSITE[self.stepper.dir_name]
        self.stepper.dir_name = best_d

    def update(self, dt, target_tile):
        self.stepper.set_speed_tps(self.cur_speed_tps())
        self.choose_dir(target_tile)
        x, y = self.stepper.tick(dt, for_ghost=True, can_use_gate=self.can_use_gate())
        return x, y

    def draw(self, surf, blink=False):
        x, y = int(self.stepper.pos.x), int(self.stepper.pos.y)
        if self.state == "eyes":
            pygame.draw.circle(surf, WHITE, (x - 4, y - 2), 5)
            pygame.draw.circle(surf, WHITE, (x + 4, y - 2), 5)
            pygame.draw.circle(surf, (33,33,255), (x - 4, y - 2), 2)
            pygame.draw.circle(surf, (33,33,255), (x + 4, y - 2), 2)
            return
        body_col = WHITE if (self.state == "frightened" and blink) else (FRIGHT_BLUE if self.state == "frightened" else self.color)
        pygame.draw.circle(surf, body_col, (x, y), self.radius)
        for i in range(-2, 3):
            pygame.draw.circle(surf, body_col, (x + i * 4, y + self.radius - 2), 4)
        pygame.draw.circle(surf, BLACK, (x - 4, y - 3), 3)
        pygame.draw.circle(surf, BLACK, (x + 4, y - 3), 3)

# ------------------------------------------------
# Game
# ------------------------------------------------
class Game:
    def __init__(self, screen, font, smallfont):
        self.screen = screen
        self.font = font
        self.smallfont = smallfont
        self.maze = Maze(MAZE_LAYOUT)

        # house and gate tiles
        self.gate_tiles = list(self.maze.gate)
        self.house_tiles = self._compute_house_tiles()

        self.level = 1
        self.score = 0
        self.lives = 3

        # mode schedule
        self.mode_idx = 0
        self.mode_timer = MODE_SCHEDULE[0][1]
        self.mode = MODE_SCHEDULE[0][0]

        # entities
        self.player = Pacman(self.maze, level=self.level)
        self.ghosts = self._spawn_ghosts()

        # frightened chain
        self.chain = 0
        self.fright_blink_time = 2.0
        self._blink_phase = 0.0

        # releases
        self.release_queue = [g for g in self.ghosts if g.state == "in_house"]
        self.release_timer = RELEASE_INTERVAL

        self.started = False
        self.paused = False
        self.game_over = False

    def _compute_house_tiles(self):
        if not self.maze.ghost_starts:
            return set()
        cols = [c for (c, r) in self.maze.ghost_starts]
        rows = [r for (c, r) in self.maze.ghost_starts]
        cmin, cmax = min(cols) - 1, max(cols) + 1
        rmin, rmax = min(rows) - 1, max(rows) + 1
        tiles = set()
        for r in range(rmin, rmax + 1):
            for c in range(cmin, cmax + 1):
                if in_bounds(c, r) and (c, r) not in self.maze.walls:
                    tiles.add((c, r))
        return tiles

    def _spawn_ghosts(self):
        inside = list(self.maze.ghost_starts) if self.maze.ghost_starts else [(13, 14), (14, 14), (12, 14), (15, 14)]
        # outside spawn just above the gate midpoint
        if self.gate_tiles:
            gate_cols = [c for (c, r) in self.gate_tiles]
            gate_row = list(self.gate_tiles)[0][1]
            out_col = sum(gate_cols) // len(gate_cols)
            outside = (out_col, gate_row - 1)
        else:
            outside = (13, 11)

        blinky = Ghost(self.maze, "blinky", RED, outside, self.house_tiles, level=self.level, start_outside=True, gate_tiles=self.gate_tiles)
        names = ["pinky", "inky", "clyde"]
        cols = [PINK, CYAN, ORANGE]
        others = []
        for i in range(3):
            start = inside[i] if i < len(inside) else (13 + i, 14)
            g = Ghost(self.maze, names[i], cols[i], start, self.house_tiles, level=self.level, start_outside=False, gate_tiles=self.gate_tiles)
            others.append(g)
        return [blinky] + others

    def start_level(self, keep_score=True):
        if not keep_score:
            self.score = 0
            self.lives = 3
            self.level = 1
        # rebuild collectibles from layout
        self.maze = Maze(MAZE_LAYOUT)
        self.gate_tiles = list(self.maze.gate)
        self.house_tiles = self._compute_house_tiles()

        self.player = Pacman(self.maze, level=self.level)
        self.ghosts = self._spawn_ghosts()

        self.mode_idx = 0
        self.mode_timer = MODE_SCHEDULE[0][1]
        self.mode = MODE_SCHEDULE[0][0]
        self.chain = 0
        self.release_queue = [g for g in self.ghosts if g.state == "in_house"]
        self.release_timer = RELEASE_INTERVAL
        self.game_over = False

    def next_level(self):
        self.level += 1
        self.start_level(keep_score=True)

    def update_mode(self, dt):
        self.mode_timer -= dt
        if self.mode_timer <= 0:
            self.mode_idx = min(self.mode_idx + 1, len(MODE_SCHEDULE) - 1)
            self.mode, dur = MODE_SCHEDULE[self.mode_idx]
            self.mode_timer = dur

    def release_tick(self, dt):
        if not self.release_queue:
            return
        self.release_timer -= dt
        if self.release_timer <= 0:
            g = self.release_queue.pop(0)
            g.state = "leaving"
            self.release_timer = RELEASE_INTERVAL

    def frightened_all(self):
        self.chain = 0
        for g in self.ghosts:
            if g.state == "eyes":
                continue
            g.state = "frightened"
            g.fright_timer = FRIGHTENED_TIME

    def reset_after_death(self):
        self.player.reset(level=self.level)
        self.ghosts = self._spawn_ghosts()
        self.release_queue = [g for g in self.ghosts if g.state == "in_house"]
        self.release_timer = RELEASE_INTERVAL
        self.mode_idx = 0
        self.mode_timer = MODE_SCHEDULE[0][1]
        self.mode = MODE_SCHEDULE[0][0]
        self.chain = 0

    def update(self, dt, keys):
        if self.paused or not self.started or self.game_over:
            return

        self.update_mode(dt)
        self.release_tick(dt)

        self.player.handle_input(keys)
        self.player.update(dt)

        pc, pr = self.player.tile
        # pellets
        if (pc, pr) in self.maze.pellets:
            self.maze.pellets.remove((pc, pr))
            self.score += PELLET_SCORE
        elif (pc, pr) in self.maze.power:
            self.maze.power.remove((pc, pr))
            self.score += POWER_SCORE
            self.frightened_all()

        pac_tile = (pc, pr)

        # ghost state timers first
        for g in self.ghosts:
            g.update_state_timers(dt)

        self._blink_phase += dt * 6

        # choose targets and move
        for g in self.ghosts:
            if g.state == "eyes":
                # go to house (nearest house tile)
                target = min(self.house_tiles, key=lambda t: manhattan(t, g.tile)) if self.house_tiles else (13, 14)
            elif g.state == "leaving":
                # once above gate row, switch to chase
                if self.gate_tiles:
                    gate_row = list(self.gate_tiles)[0][1]
                    if g.tile[1] < gate_row:
                        g.state = "chase"
                target = pac_tile
            elif g.state == "in_house":
                # pace left/right inside house
                if g.at_center():
                    for d in ("left", "right"):
                        dc, dr = int(DIRS[d].x), int(DIRS[d].y)
                        nc, nr = g.tile[0] + dc, g.tile[1] + dr
                        if (nc, nr) in self.house_tiles and self.maze.passable_for_ghost(nc, nr, can_use_gate=True):
                            g.stepper.dir_name = d
                            break
                target = g.tile
            else:
                # scatter/chase
                target = g.scatter_targets.get(g.name, pac_tile) if self.mode == "scatter" else pac_tile

            g.update(dt, target)

        # handle eyes reaching house (respawn)
        for g in self.ghosts:
            if g.state == "eyes" and g.tile in self.house_tiles:
                g.state = "in_house"
                g.leaving = False
                g.respawn_timer = 1.5
                if g not in self.release_queue:
                    self.release_queue.append(g)

        # collisions
        ppos = self.player.pos
        for g in self.ghosts:
            gpos = g.stepper.pos
            if (ppos - gpos).length_squared() <= (self.player.radius + g.radius) ** 2:
                if g.state == "frightened":
                    points = GHOST_EAT_SCORES[min(self.chain, len(GHOST_EAT_SCORES)-1)]
                    self.score += points
                    self.chain += 1
                    g.state = "eyes"
                    g.respawn_timer = 0
                elif g.state not in ("eyes",):
                    self.lives -= 1
                    if self.lives <= 0:
                        self.game_over = True
                        self.started = False
                    else:
                        self.reset_after_death()
                    return

        # level complete
        if not self.maze.pellets and not self.maze.power:
            self.next_level()

    def draw_hud(self):
        pygame.draw.rect(self.screen, BLACK, (0, 0, WIDTH, MAZE_OFFSET_Y))
        score_s = self.smallfont.render(f"Score: {self.score}", True, WHITE)
        level_s = self.smallfont.render(f"Level: {self.level}", True, WHITE)
        self.screen.blit(score_s, (MAZE_OFFSET_X, 18))
        self.screen.blit(level_s, (MAZE_OFFSET_X + 220, 18))
        for i in range(self.lives):
            x = WIDTH - MAZE_OFFSET_X - 30 * (self.lives - i)
            y = 28
            pygame.draw.circle(self.screen, YELLOW, (x, y), 8)

    def draw(self):
        self.screen.fill(BLACK)
        self.maze.draw(self.screen)
        blink = any(g.state == "frightened" and g.fright_timer <= self.fright_blink_time for g in self.ghosts)
        for g in self.ghosts:
            g.draw(self.screen, blink=blink)
        self.player.draw(self.screen)
        self.draw_hud()

        if not self.started and not self.game_over:
            title = self.font.render("PAC-MAN", True, YELLOW)
            self.screen.blit(title, (WIDTH//2 - title.get_width()//2, 140))
            msg = self.smallfont.render("Press Enter (or Arrow/WASD) to Start", True, WHITE)
            self.screen.blit(msg, (WIDTH//2 - msg.get_width()//2, 210))
        if self.paused:
            pmsg = self.font.render("PAUSED", True, WHITE)
            self.screen.blit(pmsg, (WIDTH//2 - pmsg.get_width()//2, HEIGHT//2 - 20))
        if self.game_over:
            gom = self.font.render("GAME OVER", True, (255, 80, 80))
            self.screen.blit(gom, (WIDTH//2 - gom.get_width()//2, 160))
            rmsg = self.smallfont.render("Press Enter to Restart", True, WHITE)
            self.screen.blit(rmsg, (WIDTH//2 - rmsg.get_width()//2, 220))

# ------------------------------------------------
# Main loop (fixed-timestep)
# ------------------------------------------------
def main():
    pygame.init()
    flags = pygame.SCALED | pygame.DOUBLEBUF
    try:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags, vsync=1)
    except TypeError:
        screen = pygame.display.set_mode((WIDTH, HEIGHT), flags)
    pygame.display.set_caption(TITLE)
    clock = pygame.time.Clock()
    font = pygame.font.SysFont("arial", 48, bold=True)
    smallfont = pygame.font.SysFont("arial", 22)

    game = Game(screen, font, smallfont)
    running = True
    accum = 0.0
    prev = time.perf_counter()
    MAX_FRAME_DT = 0.25
    MAX_STEPS = 8

    while running:
        now = time.perf_counter()
        frame_dt = now - prev
        prev = now
        frame_dt = max(0.0, min(frame_dt, MAX_FRAME_DT))
        accum += frame_dt

        # events
        for e in pygame.event.get():
            if e.type == pygame.QUIT:
                running = False
            elif e.type == pygame.KEYDOWN:
                if e.key == pygame.K_ESCAPE:
                    running = False
                elif e.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                    if game.game_over:
                        game = Game(screen, font, smallfont)
                        game.started = True
                    else:
                        game.started = True
                elif e.key == pygame.K_p:
                    if game.started and not game.game_over:
                        game.paused = not game.paused
                elif e.key in (pygame.K_LEFT, pygame.K_RIGHT, pygame.K_UP, pygame.K_DOWN,
                               pygame.K_a, pygame.K_d, pygame.K_w, pygame.K_s):
                    if not game.started and not game.game_over:
                        game.started = True

        keys = pygame.key.get_pressed()

        steps = 0
        while accum >= DT and steps < MAX_STEPS:
            game.update(DT, keys)
            accum -= DT
            steps += 1

        game.draw()
        pygame.display.flip()
        clock.tick(RENDER_FPS)

    pygame.quit()

if __name__ == "__main__":
    main()
