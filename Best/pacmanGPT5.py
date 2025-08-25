import math
import os
import random
import sys
from collections import deque

import pygame

# -----------------------------
# Py-Man — Single-file Pygame
# -----------------------------
# Controls: Arrows / WASD to move, Enter (or keypad Enter) to start, P to pause, Esc to quit

WIDTH, HEIGHT = 800, 800
FPS = 120
FONT_NAME = "arial"
TITLE = "Py-Man"

GRID_W, GRID_H = 28, 31
TILE = 24
MAZE_OFFSET_X = (WIDTH - GRID_W * TILE) // 2
MAZE_OFFSET_Y = 60

PELLET_SCORE = 10
POWER_SCORE = 50
GHOST_EAT_SCORES = [200, 400, 800, 1600]

PLAYER_SPEED = 7.0
GHOST_SPEED = 6.5
FRIGHT_SPEED = 4.0
EYES_SPEED = 10.0

SCATTER_CHASE_CYCLE = [
    ("scatter", 7.0), ("chase", 20.0),
    ("scatter", 7.0), ("chase", 20.0),
    ("scatter", 5.0), ("chase", 20.0),
    ("scatter", 5.0), ("chase", 999.0),
]

FRIGHT_TIME = 6.0
FRIGHT_FLASH_TIME = 2.0  # last seconds of frightened flash white/blue

LIVES_START = 3

BLACK = (0, 0, 0)
WALL_BLUE = (33, 33, 222)
PELLET_COLOR = (255, 184, 151)
POWER_COLOR = (255, 255, 255)
TEXT_YELLOW = (255, 255, 0)
HUD_WHITE = (240, 240, 240)
READY_YELLOW = (255, 255, 0)
GAMEOVER_RED = (255, 64, 64)

BLINKY_RED = (255, 0, 0)
PINKY_PINK = (255, 184, 255)
INKY_CYAN = (0, 255, 255)
CLYDE_ORANGE = (255, 184, 82)
FRIGHT_BLUE = (5, 5, 255)
FRIGHT_FLASH = (255, 255, 255)

# Maze legend:
# '#' wall  '.' pellet  'o' power pellet  '-' gate (only eyes or exiting ghost may pass)
# 'P' player spawn  'R' blinky  'I' inky  'K' pinky  'C' clyde  '=' pen floor
DEFAULT_LEVEL = [
"############################",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#o####.#####.##.#####.####o#",
"#.####.#####.##.#####.####.#",
"#..........................#",
"#.####.##.########.##.####.#",
"#.####.##.########.##.####.#",
"#......##....##....##......#",
"######.##### ## #####.######",
"     #.##### ## #####.#     ",
"     #.##          ##.#     ",
"     #.## ###--### ##.#     ",
"######.## #======# ##.######",
"      .   #=RIKC=#   .      ",
"######.## #======# ##.######",
"     #.## ######## ##.#     ",
"     #.##          ##.#     ",
"     #.## ######## ##.#     ",
"######.## ######## ##.######",
"#............##............#",
"#.####.#####.##.#####.####.#",
"#.####.#####.##.#####.####.#",
"#o..##................##..o#",
"###.##.##.########.##.##.###",
"###.##.##.########.##.##.###",
"#......##....##....##......#",
"#.##########.##.##########.#",
"#.##########.##.##########.#",
"#..........................#",
"############################",
]

DIR_LIST = [(-1,0),(1,0),(0,-1),(0,1)]
def opposite(v): return (-v[0], -v[1])

def grid_to_px(col, row):
    return MAZE_OFFSET_X + col * TILE + TILE // 2, MAZE_OFFSET_Y + row * TILE + TILE // 2

def px_to_grid(x, y):
    col = int((x - MAZE_OFFSET_X) // TILE)
    row = int((y - MAZE_OFFSET_Y) // TILE)
    return col, row

# -----------------------------
# Level
# -----------------------------
class Level:
    def __init__(self, lines):
        self.w = len(lines[0])
        self.h = len(lines)
        self.grid = [list(row) for row in lines]
        self.pellet_count = 0
        self.spawn_player = None
        self.spawn_ghosts = {}
        self.pen_tiles = set()
        self.gate_positions = set()
        self._scan()

    @staticmethod
    def from_file_or_default(path="level1.txt"):
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                lines = [line.rstrip("\n") for line in f if line.strip("\n")]
            width = max(len(r) for r in lines)
            lines = [r.ljust(width, " ") for r in lines]
            return Level(lines)
        else:
            return Level(DEFAULT_LEVEL)

    def _scan(self):
        self.pellet_count = 0
        self.spawn_player = None
        self.spawn_ghosts = {}
        self.pen_tiles.clear()
        self.gate_positions.clear()
        for r in range(self.h):
            for c in range(self.w):
                ch = self.grid[r][c]
                if ch == '.':
                    self.pellet_count += 1
                elif ch == 'o':
                    self.pellet_count += 1
                elif ch == 'P':
                    self.spawn_player = (c, r)
                    self.grid[r][c] = ' '
                elif ch in ('R','I','K','C'):
                    self.spawn_ghosts[ch] = (c, r)
                    self.grid[r][c] = '='
                    self.pen_tiles.add((c, r))
                elif ch == '=':
                    self.pen_tiles.add((c, r))
                elif ch == '-':
                    self.gate_positions.add((c, r))

    def is_walkable(self, c, r, *, for_eyes=False, allow_gate=False):
        if not (0 <= c < self.w and 0 <= r < self.h):
            return False
        ch = self.grid[r][c]
        if ch == '#':
            return False
        if ch == '-' and not (for_eyes or allow_gate):
            return False
        return True

    def eat_at(self, c, r):
        ch = self.grid[r][c]
        if ch == '.':
            self.grid[r][c] = ' '
            self.pellet_count -= 1
            return "pellet"
        elif ch == 'o':
            self.grid[r][c] = ' '
            self.pellet_count -= 1
            return "power"
        return None

# -----------------------------
# BFS pathfinding
# -----------------------------
def bfs_next_dir(level, start, goal, *, for_eyes=False, allow_gate=False, forbid=None):
    """Return a direction (dx,dy) for the first step on a shortest path from start->goal.
       If goal unreachable, step toward the visited tile nearest to goal."""
    if start == goal:
        return (0, 0)
    visited = set([start])
    parent = {}
    q = deque([start])

    def neighbors(tile):
        c, r = tile
        order = [v for v in DIR_LIST if v != forbid] + ([forbid] if forbid else [])
        for v in order:
            nc, nr = c + v[0], r + v[1]

            # --- allow stepping "outward" from extreme edge so wrap can occur in movement ---
            if v[0] < 0 and c == 0:
                yield (nc, nr)  # movement code will wrap
                continue
            if v[0] > 0 and c == level.w - 1:
                yield (nc, nr)
                continue
            # -------------------------------------------------------------------------------

            if (nc, nr) in visited:
                continue
            if level.is_walkable(nc, nr, for_eyes=for_eyes, allow_gate=allow_gate):
                yield (nc, nr)

    while q:
        cur = q.popleft()
        if cur == goal:
            break
        for nxt in neighbors(cur):
            if nxt in visited:
                continue
            visited.add(nxt)
            parent[nxt] = cur
            q.append(nxt)

    end = goal if goal in visited else min(visited, key=lambda t: (t[0]-goal[0])**2 + (t[1]-goal[1])**2)
    step = end
    while step in parent and parent[step] != start:
        step = parent[step]
    return (step[0] - start[0], step[1] - start[1])

# -----------------------------
# Entity base (with classic left↔right wrap)
# -----------------------------
class Entity:
    def __init__(self, level, col, row, speed_tiles_per_s):
        self.level = level
        self.x, self.y = grid_to_px(col, row)  # center px
        self.dir = (0, 0)
        self.desired_dir = (0, 0)
        self.speed = speed_tiles_per_s * TILE

    def pos_grid(self):
        return px_to_grid(self.x, self.y)

    def tile_center_px(self, c=None, r=None):
        if c is None or r is None:
            c, r = self.pos_grid()
        return grid_to_px(c, r)

    def at_center_of_tile(self, eps=1.2):
        cx, cy = self.tile_center_px()
        return abs(self.x - cx) < eps and abs(self.y - cy) < eps

    def can_enter_next_tile(self, vec, *, for_eyes=False, allow_gate=False):
        if vec == (0, 0):
            return False
        c, r = self.pos_grid()
        nx, ny = c + vec[0], r + vec[1]

        # permit stepping "off-grid" horizontally so wrap can happen
        if vec[0] < 0 and c == 0:
            return True
        if vec[0] > 0 and c == self.level.w - 1:
            return True

        return self.level.is_walkable(nx, ny, for_eyes=for_eyes, allow_gate=allow_gate)

    # *** THIS METHOD MUST BE INSIDE Entity (indentation!) ***
    def try_apply_desired(self, *, for_eyes=False, allow_gate=False):
        if self.desired_dir and self.can_enter_next_tile(self.desired_dir, for_eyes=for_eyes, allow_gate=allow_gate):
            self.dir = self.desired_dir
            return True
        return False

    def _wrap_horizontal(self, cur_r, moving_right):
        new_c = 0 if moving_right else self.level.w - 1
        self.x, self.y = self.tile_center_px(new_c, cur_r)
        self.dir = (1, 0) if moving_right else (-1, 0)
        self.desired_dir = self.dir

    def move_with_collision(self, dt, *, for_eyes=False, allow_gate=False):
        if self.at_center_of_tile():
            if not self.try_apply_desired(for_eyes=for_eyes, allow_gate=allow_gate):
                if not self.can_enter_next_tile(self.dir, for_eyes=for_eyes, allow_gate=allow_gate):
                    cx, cy = self.tile_center_px()
                    self.x, self.y = cx, cy
                    self.dir = (0, 0)

        if self.dir != (0, 0):
            dx = self.dir[0] * self.speed * dt
            dy = self.dir[1] * self.speed * dt
            nx, ny = self.x + dx, self.y + dy

            c, r = self.pos_grid()
            cx, cy = self.tile_center_px(c, r)

            if self.dir[0] != 0:
                boundary_x = cx + (TILE // 2) * (1 if self.dir[0] > 0 else -1)
                crossing = (self.dir[0] > 0 and nx > boundary_x) or (self.dir[0] < 0 and nx < boundary_x)
                if crossing:
                    next_c = c + self.dir[0]
                    if next_c < 0:
                        self._wrap_horizontal(r, moving_right=False); return
                    if next_c >= self.level.w:
                        self._wrap_horizontal(r, moving_right=True); return
                    if self.level.is_walkable(next_c, r, for_eyes=for_eyes, allow_gate=allow_gate):
                        remainder = abs(nx - boundary_x)
                        self.x = boundary_x + (1 if self.dir[0] > 0 else -1) * remainder
                    else:
                        self.x = boundary_x
                        self.dir = (0, 0); return
                else:
                    self.x = nx
            else:
                if self.dir[1] != 0:
                    boundary_y = cy + (TILE // 2) * (1 if self.dir[1] > 0 else -1)
                    if (self.dir[1] > 0 and ny > boundary_y) or (self.dir[1] < 0 and ny < boundary_y):
                        next_r = r + self.dir[1]
                        if self.level.is_walkable(c, next_r, for_eyes=for_eyes, allow_gate=allow_gate):
                            remainder = abs(ny - boundary_y)
                            self.y = boundary_y + (1 if self.dir[1] > 0 else -1) * remainder
                        else:
                            self.y = boundary_y
                            self.dir = (0, 0); return
                    else:
                        self.y = ny

# -----------------------------
# Player
# -----------------------------
class Player(Entity):
    def __init__(self, level, col, row, speed_tiles_per_s):
        super().__init__(level, col, row, speed_tiles_per_s)
        self.mouth_phase = 0.0

    def update(self, dt, keys):
        desired = self.desired_dir
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            desired = (-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            desired = (1, 0)
        elif keys[pygame.K_UP] or keys[pygame.K_w]:
            desired = (0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            desired = (0, 1)
        self.desired_dir = desired
        self.move_with_collision(dt, for_eyes=False, allow_gate=False)
        self.mouth_phase = (self.mouth_phase + dt * 6.0) % 1.0

    def draw(self, surf):
        cx, cy = int(self.x), int(self.y)
        radius = TILE // 2 - 2
        open_frac = 0.25 * (1 - math.cos(self.mouth_phase * math.tau))
        mouth = max(0.1, min(0.45, open_frac))
        angle = 0
        if self.dir == (1, 0): angle = 0
        elif self.dir == (-1, 0): angle = 180
        elif self.dir == (0, -1): angle = 90
        elif self.dir == (0, 1): angle = 270
        start_angle = math.radians(angle) + math.radians(mouth * 90)
        end_angle = math.radians(angle) - math.radians(mouth * 90)
        pygame.draw.circle(surf, TEXT_YELLOW, (cx, cy), radius)
        points = [(cx, cy)]
        for a in (start_angle, end_angle):
            points.append((cx + radius * math.cos(a), cy - radius * math.sin(a)))
        pygame.draw.polygon(surf, BLACK, points)

# -----------------------------
# Ghost
# -----------------------------
class Ghost(Entity):
    def __init__(self, level, col, row, name, color, scatter_target):
        super().__init__(level, col, row, GHOST_SPEED)
        self.name = name
        self.base_color = color
        self.scatter_target = scatter_target
        self.state = "scatter"  # scatter | chase | frightened | eyes | eyes_wait
        self.fright_timer = 0.0
        self.recover_timer = 0.0  # non-lethal window after frightened ends
        self.revive_timer = 0.0   # delay inside the pen before reviving from eyes
        self.dir = (0, 0)
        self.inside_pen = True
        self.spawn_tile = (col, row)
        self.exit_phase = "queued"  # queued → exiting → active

    def set_state(self, state, frightened_time=0.0):
        self.state = state
        if state == "frightened":
            self.fright_timer = frightened_time

    def speed_for_state(self):
        if self.state == "frightened": return FRIGHT_SPEED * TILE
        if self.state in ("eyes", "eyes_wait"): return EYES_SPEED * TILE
        return GHOST_SPEED * TILE

    def choose_dir_to(self, target_tile, *, for_eyes=False, allow_gate=False):
        cur = self.pos_grid()
        forbid = opposite(self.dir) if (self.state != "frightened" and not for_eyes and not allow_gate) else None
        step = bfs_next_dir(self.level, cur, target_tile, for_eyes=for_eyes, allow_gate=allow_gate, forbid=forbid)
        if step != (0, 0):
            self.desired_dir = step
            if self.at_center_of_tile():
                self.dir = step

    def update(self, dt, player, blinky_pos, global_mode, gate_row, gate_target_tile):
        self.speed = self.speed_for_state()
        for_eyes = (self.state in ("eyes", "eyes_wait"))
        allow_gate = (self.exit_phase == "exiting") or for_eyes

        if self.recover_timer > 0:
            self.recover_timer = max(0.0, self.recover_timer - dt)

        # Handle revive timer: when eyes are parked in pen ("eyes_wait")
        if self.revive_timer > 0:
            self.revive_timer = max(0.0, self.revive_timer - dt)
            if self.revive_timer == 0 and self.state == "eyes_wait":
                # Revive to body INSIDE pen and wait in the normal release queue
                self.state = global_mode
                self.inside_pen = True
                self.exit_phase = "queued"
                self.dir = (0, 0)
                self.desired_dir = (0, 0)

        if self.state == "frightened":
            self.fright_timer -= dt
            if self.fright_timer <= 0:
                self.state = global_mode
                self.recover_timer = 0.30
                self.dir = opposite(self.dir)
                self.desired_dir = self.dir

        if self.at_center_of_tile():
            c, r = self.pos_grid()

            # When eyes reach their spawn tile, convert to "eyes_wait" and start the revive delay
            if self.state == "eyes" and (c, r) == self.spawn_tile:
                self.state = "eyes_wait"
                self.revive_timer = 2.0  # <-- "stay a little bit" in the box
                self.dir = (0, 0)
                self.desired_dir = (0, 0)

            if self.state == "frightened":
                options = []
                for v in DIR_LIST:
                    if v == opposite(self.dir): continue
                    nc, nr = c + v[0], r + v[1]
                    if self.level.is_walkable(nc, nr, for_eyes=False, allow_gate=allow_gate):
                        options.append(v)
                if not options: options = DIR_LIST[:]
                self.desired_dir = random.choice(options)

            elif self.exit_phase == "exiting":
                self.choose_dir_to(gate_target_tile, for_eyes=False, allow_gate=True)
                _, gr = self.pos_grid()
                if gr < gate_row:
                    self.inside_pen = False
                    self.exit_phase = "active"

            else:
                if self.inside_pen and self.exit_phase == "queued":
                    # idle in place while queued (do NOT exit until Game schedules us)
                    self.desired_dir = (0, 0)
                    self.dir = (0, 0)
                else:
                    if self.state in ("scatter", "chase"):
                        self.choose_dir_to(self.scatter_target if self.state == "scatter"
                                           else self.chase_target(player, blinky_pos),
                                           for_eyes=False, allow_gate=False)
                    elif self.state == "eyes":
                        self.choose_dir_to(self.spawn_tile, for_eyes=True, allow_gate=True)
                    elif self.state == "eyes_wait":
                        self.desired_dir = (0, 0); self.dir = (0, 0)

        self.move_with_collision(dt, for_eyes=for_eyes, allow_gate=allow_gate)

    def chase_target(self, player, blinky_pos):
        pc, pr = player.pos_grid()
        pd = player.dir
        if self.name == "blinky":
            return (pc, pr)
        elif self.name == "pinky":
            return (pc + 4 * pd[0], pr + 4 * pd[1])
        elif self.name == "inky":
            two_ahead = (pc + 2 * pd[0], pr + 2 * pd[1])
            bx, by = blinky_pos
            vx, vy = two_ahead[0] - bx, two_ahead[1] - by
            return (bx + 2 * vx, by + 2 * vy)
        elif self.name == "clyde":
            gx, gy = self.pos_grid()
            if (pc - gx) ** 2 + (pr - gy) ** 2 <= 8 * 8:
                return self.scatter_target
            return (pc, pr)
        return (pc, pr)

    def draw(self, surf, flashing=False):
        cx, cy = int(self.x), int(self.y)
        radius = TILE // 2 - 3
        color = self.base_color
        eyes_only = False
        if self.state == "frightened":
            color = FRIGHT_FLASH if (flashing and (pygame.time.get_ticks()//120)%2==0) else FRIGHT_BLUE
        elif self.state in ("eyes", "eyes_wait"):
            eyes_only = True

        if eyes_only:
            pygame.draw.circle(surf, (255, 255, 255), (cx - 4, cy - 2), 4)
            pygame.draw.circle(surf, (255, 255, 255), (cx + 4, cy - 2), 4)
            dx, dy = self.dir
            pygame.draw.circle(surf, (0, 0, 255), (cx - 4 + 2*dx, cy - 2 + 2*dy), 2)
            pygame.draw.circle(surf, (0, 0, 255), (cx + 4 + 2*dx, cy - 2 + 2*dy), 2)
        else:
            pygame.draw.circle(surf, color, (cx, cy), radius)
            pygame.draw.circle(surf, (255,255,255), (cx-4, cy-2), 4)
            pygame.draw.circle(surf, (255,255,255), (cx+4, cy-2), 4)
            dx, dy = self.dir
            pygame.draw.circle(surf, (0,0,255), (cx-4 + 2*dx, cy-2 + 2*dy), 2)
            pygame.draw.circle(surf, (0,0,255), (cx+4 + 2*dx, cy-2 + 2*dy), 2)
            for i in range(-2,3):
                pygame.draw.circle(surf, color, (cx + i*4, cy + radius-2), 3)

# -----------------------------
# Helpers
# -----------------------------
def stable_gate_geometry(level):
    gate_row = min((r for (_, r) in level.gate_positions), default=14)
    gate_cols = sorted([c for (c, r) in level.gate_positions if r == gate_row])
    gate_col = gate_cols[len(gate_cols)//2] if gate_cols else level.w // 2
    gate_target_tile = (gate_col, gate_row - 1)
    return gate_row, gate_col, gate_target_tile

# -----------------------------
# Game
# -----------------------------
class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption(TITLE)
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_small = pygame.font.SysFont(FONT_NAME, 18)
        self.font = pygame.font.SysFont(FONT_NAME, 24, bold=True)
        self.font_big = pygame.font.SysFont(FONT_NAME, 40, bold=True)

        self.level_num = 1
        self.score = 0
        self.high_score = 0
        self.lives = LIVES_START
        self.state = "start"
        self.global_mode = "scatter"
        self.mode_index = 0
        self.mode_timer = SCATTER_CHASE_CYCLE[0][1]
        self.fright_chain = 0
        self.level = Level.from_file_or_default()
        self.flash_timer = 0.0
        self.post_eat_grace = 0.0
        self.power_grace = 0.0

        self.gate_row, self.gate_col, self.gate_target_tile = stable_gate_geometry(self.level)
        self.release_order_names = ["blinky", "pinky", "inky", "clyde"]
        self.release_spacing = 1.0
        self.release_cooldown = 0.0

        self.reset_positions(full_reset=True)

    def get_ghost_by_name(self, name):
        mapping = {"blinky": self.blinky, "pinky": self.pinky, "inky": self.inky, "clyde": self.clyde}
        return mapping[name]

    def reset_positions(self, full_reset=False):
        sp = self.level.spawn_player or (13, 23)
        self.player = Player(self.level, sp[0], sp[1], PLAYER_SPEED)

        corners = {
            "blinky": (self.level.w-2, 0),
            "pinky": (1, 0),
            "inky": (self.level.w-2, self.level.h-1),
            "clyde": (1, self.level.h-1),
        }
        gsp = self.level.spawn_ghosts
        self.blinky = Ghost(self.level, *(gsp.get('R', (14, 14))), "blinky", BLINKY_RED, corners["blinky"])
        self.pinky  = Ghost(self.level, *(gsp.get('K', (13, 14))), "pinky", PINKY_PINK, corners["pinky"])
        self.inky   = Ghost(self.level, *(gsp.get('I', (15, 14))), "inky", INKY_CYAN, corners["inky"])
        self.clyde  = Ghost(self.level, *(gsp.get('C', (12, 14))), "clyde", CLYDE_ORANGE, corners["clyde"])
        self.ghosts = [self.blinky, self.pinky, self.inky, self.clyde]
        for g in self.ghosts:
            g.state = "scatter"
            g.dir = (0, 0)
            g.inside_pen = True
            g.exit_phase = "queued"
            g.fright_timer = 0.0
            g.recover_timer = 0.0
            g.revive_timer = 0.0

        self.global_mode = "scatter"
        self.mode_index = 0
        self.mode_timer = SCATTER_CHASE_CYCLE[0][1]
        self.fright_chain = 0
        self.release_cooldown = 0.0
        self.post_eat_grace = 0.0
        self.power_grace = 0.0

        if full_reset:
            self.score = 0
            self.lives = LIVES_START
            self.state = "start"

    def start_level(self):
        self.state = "ready"
        self.ready_timer = 1.6
        self.player.speed = (PLAYER_SPEED + (self.level_num-1)*0.25) * TILE
        for g in self.ghosts:
            g.speed = (GHOST_SPEED + (self.level_num-1)*0.2) * TILE

    def begin_play(self):
        self.state = "playing"
        self.get_ghost_by_name("blinky").exit_phase = "exiting"
        self.release_order_names = ["pinky", "inky", "clyde"]
        self.release_cooldown = self.release_spacing

    def handle_ghost_release(self, dt):
        if self.release_cooldown > 0:
            self.release_cooldown -= dt; return
        if any(g.exit_phase == "exiting" for g in self.ghosts):
            return
        if self.release_order_names:
            name = self.release_order_names.pop(0)
            self.get_ghost_by_name(name).exit_phase = "exiting"
            self.release_cooldown = self.release_spacing

    def lose_life(self):
        self.lives -= 1
        if self.lives < 0:
            self.state = "game_over"
        else:
            self.state = "dying"
            self.death_timer = 1.2

    def next_level(self):
        self.state = "level_clear"
        self.flash_timer = 1.6

    def handle_keydown(self, key):
        if key == pygame.K_ESCAPE:
            pygame.quit(); sys.exit(0)
        if key in (pygame.K_RETURN, pygame.K_KP_ENTER):
            if self.state == "start":
                self.start_level()
            elif self.state == "ready":
                self.begin_play()
            elif self.state == "game_over":
                self.level_num = 1
                self.level = Level.from_file_or_default()
                self.gate_row, self.gate_col, self.gate_target_tile = stable_gate_geometry(self.level)
                self.reset_positions(full_reset=True)
                self.start_level()
        if key == pygame.K_p and self.state == "playing":
            self.state = "paused"
        elif key == pygame.K_p and self.state == "paused":
            self.state = "playing"

    def update(self, dt, keys):
        if self.state == "ready":
            self.ready_timer -= dt
            if self.ready_timer <= 0:
                self.begin_play()

        elif self.state == "dying":
            self.death_timer -= dt
            if self.death_timer <= 0:
                self.reset_positions(full_reset=False)
                self.start_level()

        elif self.state == "level_clear":
            self.flash_timer -= dt
            if self.flash_timer <= 0:
                self.level_num += 1
                self.level = Level.from_file_or_default()
                self.gate_row, self.gate_col, self.gate_target_tile = stable_gate_geometry(self.level)
                self.reset_positions(full_reset=False)
                self.start_level()

        elif self.state == "playing":
            self.handle_ghost_release(dt)
            if self.post_eat_grace > 0: self.post_eat_grace = max(0.0, self.post_eat_grace - dt)
            if self.power_grace > 0: self.power_grace = max(0.0, self.power_grace - dt)

            if not any(g.state == "frightened" for g in self.ghosts):
                self.mode_timer -= dt
                if self.mode_timer <= 0:
                    self.mode_index = min(self.mode_index + 1, len(SCATTER_CHASE_CYCLE)-1)
                    new_mode = SCATTER_CHASE_CYCLE[self.mode_index][0]
                    self.mode_timer = SCATTER_CHASE_CYCLE[self.mode_index][1]
                    self.global_mode = new_mode
                    for g in self.ghosts:
                        if g.state in ("scatter", "chase"):
                            g.state = new_mode
                            g.dir = opposite(g.dir)
                            g.desired_dir = g.dir

            self.player.update(dt, keys)
            blinky_pos = self.blinky.pos_grid()

            pc, pr = self.player.pos_grid()
            ate = self.level.eat_at(pc, pr)
            if ate == "pellet":
                self.score += PELLET_SCORE
            elif ate == "power":
                self.score += POWER_SCORE
                self.fright_chain = 0
                self.power_grace = 0.30
                for g in self.ghosts:
                    if g.state not in ("eyes", "eyes_wait"):
                        g.set_state("frightened", FRIGHT_TIME)
                        g.dir = opposite(g.dir)
                        g.desired_dir = g.dir

            for g in self.ghosts:
                g.update(dt, self.player, blinky_pos, self.global_mode, self.gate_row, self.gate_target_tile)

            # Re-queue any ghosts that have revived to body in the pen
            for g in self.ghosts:
                if g.inside_pen and g.exit_phase == "queued" and g.state in ("scatter", "chase"):
                    if g.name not in self.release_order_names and not any(gg.exit_phase == "exiting" and gg.name == g.name for gg in self.ghosts):
                        self.release_order_names.append(g.name)

            hit_radius = TILE * 0.6
            colliding = [g for g in self.ghosts if math.hypot(self.player.x - g.x, self.player.y - g.y) < hit_radius]
            fright_hits = [g for g in colliding if g.state == "frightened"]
            lethal_hits = [
                g for g in colliding
                if g.state not in ("frightened", "eyes", "eyes_wait") and g.recover_timer <= 0.0
            ]

            if fright_hits:
                for g in fright_hits:
                    pts = GHOST_EAT_SCORES[min(self.fright_chain, len(GHOST_EAT_SCORES)-1)]
                    self.score += pts
                    self.fright_chain += 1
                    g.state = "eyes"
                    g.inside_pen = False
                    g.exit_phase = "exiting"
                    g.dir = opposite(g.dir)
                    g.desired_dir = g.dir
                self.post_eat_grace = 0.25
            elif self.post_eat_grace <= 0.0 and self.power_grace <= 0.0 and lethal_hits:
                self.lose_life()

            if self.level.pellet_count <= 0:
                self.next_level()

        self.high_score = max(self.high_score, self.score)

    def draw(self):
        self.screen.fill(BLACK)
        self.draw_hud()

        if self.state in ("start", "game_over", "paused"):
            self.draw_maze(flash=False)
        elif self.state == "level_clear":
            flash = (int(pygame.time.get_ticks() / 150) % 2) == 0
            self.draw_maze(flash=flash)
        else:
            self.draw_maze(flash=False)

        if self.state in ("ready", "playing", "dying", "level_clear", "paused"):
            if self.state != "level_clear":
                self.draw_pellets()
            flashing = any(g.state == "frightened" and g.fright_timer <= FRIGHT_FLASH_TIME for g in self.ghosts)
            for g in self.ghosts:
                g.draw(self.screen, flashing=flashing)
            self.player.draw(self.screen)

        if self.state == "start":
            self.draw_center_text("PY-MAN", self.font_big, TEXT_YELLOW, dy=-40)
            self.draw_center_text("Press ENTER to start", self.font, HUD_WHITE, dy=10)
            self.draw_center_text("Arrows/WASD • P pause • Esc quit", self.font_small, HUD_WHITE, dy=40)

        if self.state == "ready":
            self.draw_center_text("READY!", self.font_big, READY_YELLOW, dy=0)

        if self.state == "paused":
            self.draw_center_text("PAUSED", self.font_big, HUD_WHITE, dy=0)
            self.draw_center_text("Press P to resume", self.font, HUD_WHITE, dy=40)

        if self.state == "dying":
            self.draw_center_text("Ouch!", self.font_big, GAMEOVER_RED, dy=0)

        if self.state == "game_over":
            self.draw_center_text("GAME OVER", self.font_big, GAMEOVER_RED, dy=0)
            self.draw_center_text("Press ENTER to restart", self.font, HUD_WHITE, dy=40)

        pygame.display.flip()

    def draw_hud(self):
        s = f"SCORE {self.score:06d}    HIGH {self.high_score:06d}    LVL {self.level_num}"
        txt = self.font.render(s, True, HUD_WHITE)
        self.screen.blit(txt, (MAZE_OFFSET_X, 18))
        for i in range(max(0, self.lives)):
            x = MAZE_OFFSET_X + i * 28
            y = MAZE_OFFSET_Y + GRID_H * TILE + 10
            pygame.draw.circle(self.screen, TEXT_YELLOW, (x + 14, y + 14), 10)
            pygame.draw.polygon(self.screen, BLACK, [(x+14, y+14), (x+24, y+10), (x+24, y+18)])

    def draw_maze(self, flash=False):
        wall_color = (255, 255, 255) if flash else WALL_BLUE
        for r in range(self.level.h):
            for c in range(self.level.w):
                ch = self.level.grid[r][c]
                if ch == '#':
                    x = MAZE_OFFSET_X + c * TILE
                    y = MAZE_OFFSET_Y + r * TILE
                    pygame.draw.rect(self.screen, wall_color, (x, y, TILE, TILE), border_radius=4)
                elif ch == '-':
                    x = MAZE_OFFSET_X + c * TILE
                    y = MAZE_OFFSET_Y + r * TILE + TILE//2 - 2
                    pygame.draw.rect(self.screen, (200, 200, 255), (x+4, y, TILE-8, 4), border_radius=2)

    def draw_pellets(self):
        t = pygame.time.get_ticks()
        power_flash = (t // 300) % 2 == 0
        for r in range(self.level.h):
            for c in range(self.level.w):
                ch = self.level.grid[r][c]
                cx, cy = grid_to_px(c, r)
                if ch == '.':
                    pygame.draw.circle(self.screen, PELLET_COLOR, (cx, cy), 3)
                elif ch == 'o':
                    pygame.draw.circle(self.screen, POWER_COLOR if power_flash else (180,180,180), (cx, cy), 6)

    def draw_center_text(self, s, font, color, dy=0):
        txt = font.render(s, True, color)
        rect = txt.get_rect(center=(WIDTH//2, MAZE_OFFSET_Y + GRID_H*TILE//2 + dy))
        self.screen.blit(txt, rect)

# -----------------------------
# Main loop
# -----------------------------
def main():
    pygame.init()
    game = Game()
    running = True
    while running:
        dt = game.clock.tick(FPS) / 1000.0
        keys = pygame.key.get_pressed()
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                game.handle_keydown(event.key)

        game.update(dt, keys)
        game.draw()

    pygame.quit()

if __name__ == "__main__":
    main()
