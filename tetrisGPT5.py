# tetris.py
# Pygame Tetris — Guideline-style core with SRS, 7-bag, Ghost, Hold, B2B, Combos, basic modes.
# Controls:
#   Left/Right  : Move piece (DAS/ARR implemented)
#   Down        : Soft drop
#   Z / UP      : Rotate CW (both for convenience); X : Rotate CCW ; A : 180° rotate (optional)
#   Space       : Hard drop
#   C / Shift   : Hold piece (once per drop)
#   P           : Pause
#   R           : Restart current mode
#   ESC         : Back to mode select
# Modes:
#   1 Marathon, 2 Sprint (40L), 3 Ultra (120s), 4 Zen
#
# Requires: pygame (pip install pygame)

import pygame
import random
import time
from collections import deque, defaultdict

# ----------------------------- Config ---------------------------------

CELL = 30
COLS, VISIBLE_ROWS = 10, 20
VANISH_ROWS = 20               # Extra hidden rows above the visible field
ROWS = VISIBLE_ROWS + VANISH_ROWS  # 40 high logical matrix
SCREEN_W = 640                 # Playfield + sidebars
SCREEN_H = CELL * VISIBLE_ROWS + 80
FPS = 60

# DAS/ARR handling (in milliseconds)
DAS = 150
ARR = 33

# Lock delay (ms)
LOCK_DELAY = 500

# Gravity timings (ms per cell). Simplified level curve.
LEVEL_SPEED_MS = [1000, 793, 618, 473, 355, 262, 190, 135, 94, 64, 43, 28, 18, 11, 7, 5, 3, 2, 1, 1]

# Colors (modern standard)
COLORS = {
    'I': (0, 255, 255),   # Cyan
    'O': (255, 255, 0),   # Yellow
    'T': (128, 0, 128),   # Purple
    'L': (255, 165, 0),   # Orange
    'J': (0, 0, 255),     # Blue
    'S': (0, 255, 0),     # Green
    'Z': (255, 0, 0),     # Red
    'G': (80, 80, 80),    # Garbage (unused in single)
}

BG = (10, 12, 16)
GRID = (30, 34, 44)
WELL_BG = (18, 20, 26)
TEXT = (230, 230, 238)
GHOST = (120, 120, 120)

# ------------------------- Tetromino Definitions -----------------------

# Shapes are lists of rotation states; each state is a list of (x,y) in a 4x4 box.
# States 0, R(1), 2, L(3) match SRS indexing.
SHAPES = {
    'I': [
        [(0, 1), (1, 1), (2, 1), (3, 1)],
        [(2, 0), (2, 1), (2, 2), (2, 3)],
        [(0, 2), (1, 2), (2, 2), (3, 2)],
        [(1, 0), (1, 1), (1, 2), (1, 3)],
    ],
    'O': [
        [(1, 1), (2, 1), (1, 2), (2, 2)],
        [(1, 1), (2, 1), (1, 2), (2, 2)],
        [(1, 1), (2, 1), (1, 2), (2, 2)],
        [(1, 1), (2, 1), (1, 2), (2, 2)],
    ],
    'T': [
        [(1, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (1, 2)],
        [(1, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'J': [
        [(0, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (2, 0), (1, 1), (1, 2)],
        [(0, 1), (1, 1), (2, 1), (2, 2)],
        [(1, 0), (1, 1), (0, 2), (1, 2)],
    ],
    'L': [
        [(2, 0), (0, 1), (1, 1), (2, 1)],
        [(1, 0), (1, 1), (1, 2), (2, 2)],
        [(0, 1), (1, 1), (2, 1), (0, 2)],
        [(0, 0), (1, 0), (1, 1), (1, 2)],
    ],
    'S': [
        [(1, 0), (2, 0), (0, 1), (1, 1)],
        [(1, 0), (1, 1), (2, 1), (2, 2)],
        [(1, 1), (2, 1), (0, 2), (1, 2)],
        [(0, 0), (0, 1), (1, 1), (1, 2)],
    ],
    'Z': [
        [(0, 0), (1, 0), (1, 1), (2, 1)],
        [(2, 0), (1, 1), (2, 1), (1, 2)],
        [(0, 1), (1, 1), (1, 2), (2, 2)],
        [(1, 0), (0, 1), (1, 1), (0, 2)],
    ]
}

# SRS kick tables: dict[(from, to)] = [(dx,dy), ...]
# JLSTZ & T
KICKS = defaultdict(list)
for (fr_to, tests) in [
    ((0, 1), [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)]),
    ((1, 0), [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)]),
    ((1, 2), [(0, 0), (+1, 0), (+1, -1), (0, +2), (+1, +2)]),
    ((2, 1), [(0, 0), (-1, 0), (-1, +1), (0, -2), (-1, -2)]),
    ((2, 3), [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)]),
    ((3, 2), [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)]),
    ((3, 0), [(0, 0), (-1, 0), (-1, -1), (0, +2), (-1, +2)]),
    ((0, 3), [(0, 0), (+1, 0), (+1, +1), (0, -2), (+1, -2)]),
]:
    a, b = fr_to
    KICKS[(a, b)] = tests

# I piece kicks
I_KICKS = {
    (0, 1): [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    (1, 0): [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    (1, 2): [(0, 0), (-1, 0), (+2, 0), (-1, +2), (+2, -1)],
    (2, 1): [(0, 0), (+1, 0), (-2, 0), (+1, -2), (-2, +1)],
    (2, 3): [(0, 0), (+2, 0), (-1, 0), (+2, +1), (-1, -2)],
    (3, 2): [(0, 0), (-2, 0), (+1, 0), (-2, -1), (+1, +2)],
    (3, 0): [(0, 0), (+1, 0), (-1, 0), (+1, -2), (-1, +2)],
    (0, 3): [(0, 0), (-1, 0), (+1, 0), (-1, +2), (+1, -2)],
}

# ----------------------------- Helpers --------------------------------

def clamp(n, a, b):
    return max(a, min(b, n))

def new_matrix():
    return [[None for _ in range(COLS)] for _ in range(ROWS)]

def copy_matrix(mat):
    return [row[:] for row in mat]

def bag7():
    items = list("IJLOSTZ")
    random.shuffle(items)
    return deque(items)

# ------------------------------ Piece ---------------------------------

class Piece:
    def __init__(self, kind, x, y, rot=0):
        self.kind = kind
        self.x = x
        self.y = y
        self.rot = rot % 4
        self.last_action_rotate = False
        self.last_kick_used = False

    def cells(self, rot=None, offset=(0, 0)):
        r = self.rot if rot is None else rot % 4
        ox, oy = offset
        shape = SHAPES[self.kind][r]
        for (px, py) in shape:
            yield (self.x + px + ox, self.y + py + oy)

    def clone(self):
        p = Piece(self.kind, self.x, self.y, self.rot)
        p.last_action_rotate = self.last_action_rotate
        p.last_kick_used = self.last_kick_used
        return p

# ------------------------------ Game ----------------------------------

class Game:
    MODE_MARATHON = "Marathon"
    MODE_SPRINT = "Sprint 40L"
    MODE_ULTRA = "Ultra 120s"
    MODE_ZEN = "Zen"

    def __init__(self, mode):
        self.mode = mode
        self.reset()

    def reset(self):
        self.board = new_matrix()
        self.score = 0
        self.lines = 0
        self.level = 0
        self.pieces_placed = 0
        self.start_time = time.time()
        self.elapsed = 0.0
        self.combo = -1
        self.b2b = False
        self.apm_attacks = 0  # For future; single player not used
        self.held = None
        self.hold_used = False
        self.nextq = deque()
        self.bag = deque()
        while len(self.nextq) < 5:
            self.refill_bag()
        self.active = None
        self.spawn_new()
        self.gravity_ms = LEVEL_SPEED_MS[self.level]
        self.gravity_accum = 0.0
        self.soft_drop = False
        self.paused = False
        self.game_over = False
        self.lock_timer = 0
        self.grounded = False
        # movement repeat
        self.left_down = False
        self.right_down = False
        self.left_timer = 0
        self.right_timer = 0
        self.left_repeat = False
        self.right_repeat = False
        # Sprint/Ultra targets
        self.sprint_target = 40
        self.ultra_secs = 120

    def refill_bag(self):
        if not self.bag:
            self.bag = bag7()
        while self.bag:
            self.nextq.append(self.bag.popleft())

    def spawn_new(self, from_hold=False, kind_override=None):
        if kind_override is not None:
            kind = kind_override
        else:
            if not self.nextq:
                self.refill_bag()
            kind = self.nextq.popleft()
            if len(self.nextq) < 5:
                self.refill_bag()

        # Spawn near center; SRS spawn for 10-wide center x=3
        p = Piece(kind, 3, VANISH_ROWS - 2, rot=0)
        if not self.valid(p):
            # Block out: game over unless Zen mode chooses to ignore
            self.game_over = (self.mode != self.MODE_ZEN)
            if self.mode == self.MODE_ZEN:
                # In Zen, clear top two lines to make space (simple approach)
                for _ in range(2):
                    self.board.pop(0)
                    self.board.append([None for _ in range(COLS)])
                if not self.valid(p):
                    self.game_over = True
        self.active = p
        self.hold_used = False if not from_hold else True  # after a hold-swap, you've used hold this drop
        self.lock_timer = 0
        self.grounded = False

    # -------------------- Collision & Placement ------------------------

    def valid(self, piece):
        for (x, y) in piece.cells():
            if x < 0 or x >= COLS or y < 0 or y >= ROWS:
                return False
            if self.board[y][x] is not None:
                return False
        return True

    def move(self, dx, dy):
        if self.game_over or self.paused: return False
        p = self.active.clone()
        p.x += dx
        p.y += dy
        if self.valid(p):
            self.active = p
            self.reset_lock_if_needed(moved=True)
            return True
        return False

    def softdrop_step(self):
        # Move down by 1 if possible; score 1 per cell soft dropped
        if self.move(0, 1):
            self.score += 1
            return True
        return False

    def harddrop(self):
        if self.game_over or self.paused: return
        dist = 0
        while self.move(0, 1):
            dist += 1
        self.score += 2 * dist
        self.lock_down(force=True)

    def rotate(self, dir_):
        # dir_: +1 = CW, -1 = CCW, 2 = 180
        if self.game_over or self.paused: return
        if self.active.kind == 'O' and dir_ in (1, -1):  # O has no kicks but allow rotation as no-op
            self.active.last_action_rotate = True
            self.active.last_kick_used = False
            self.reset_lock_if_needed(rotated=True)
            return

        if dir_ == 2:
            # 180: try two CWs with simple kicks sequence
            if not self._rotate_once(1):
                return
            self._rotate_once(1)
            return

        self._rotate_once(dir_)

    def _rotate_once(self, dir_):
        p = self.active
        fr = p.rot
        to = (p.rot + (1 if dir_ == 1 else -1)) % 4
        if p.kind == 'I':
            test_offsets = I_KICKS[(fr, to)]
        else:
            test_offsets = KICKS[(fr, to)]

        base = p.clone()
        base.rot = to
        # Try kicks
        for (dx, dy) in test_offsets:
            cand = base.clone()
            cand.x += dx
            cand.y += dy
            if self.valid(cand):
                cand.last_action_rotate = True
                cand.last_kick_used = (dx, dy) != (0, 0)
                self.active = cand
                self.reset_lock_if_needed(rotated=True)
                return True
        return False

    def reset_lock_if_needed(self, moved=False, rotated=False):
        # If piece is touching ground, moving/rotating resets lock timer (Infinity)
        if self.is_grounded(self.active):
            self.lock_timer = 0
            self.grounded = True
        else:
            self.grounded = False
        if rotated:
            self.active.last_action_rotate = True

    def is_grounded(self, piece):
        # grounded if cannot move down
        test = piece.clone()
        test.y += 1
        return not self.valid(test)

    def lock_down(self, force=False):
        # Place piece into board, clear lines, score, spawn next
        p = self.active
        # If force is False and piece isn't grounded, ignore
        if not force and not self.is_grounded(p):
            return
        for (x, y) in p.cells():
            if 0 <= y < ROWS:
                self.board[y][x] = p.kind
        self.pieces_placed += 1

        # Check lines cleared
        full_rows = [y for y in range(ROWS) if all(self.board[y][x] is not None for x in range(COLS))]
        # T-Spin detection (simplified, "3-corner" rule)
        tspin_type = self.detect_tspin(p, full_rows)

        cleared = len(full_rows)
        if cleared > 0:
            self.clear_lines(full_rows)

        self.apply_scoring(cleared, tspin_type)

        # Level progress (Marathon)
        if self.mode == self.MODE_MARATHON:
            self.level = min(19, self.lines // 10)
            self.gravity_ms = LEVEL_SPEED_MS[self.level]

        # Sprint win
        if self.mode == self.MODE_SPRINT and self.lines >= self.sprint_target:
            self.game_over = True

        # Spawn next
        self.spawn_new()

    def detect_tspin(self, p, full_rows):
        # Only T piece can T-Spin and only if last action was a rotation
        if p.kind != 'T' or not p.last_action_rotate:
            return "none"
        # T pivot is at (x+1, y+1) in our 4x4 representation
        pivot = (p.x + 1, p.y + 1)
        corners = [(pivot[0]-1, pivot[1]-1),
                   (pivot[0]+1, pivot[1]-1),
                   (pivot[0]-1, pivot[1]+1),
                   (pivot[0]+1, pivot[1]+1)]
        filled = 0
        for (cx, cy) in corners:
            if cx < 0 or cx >= COLS or cy < 0 or cy >= ROWS:
                filled += 1
            elif self.board[cy][cx] is not None:
                filled += 1
        if filled >= 3:
            return "tspin"
        return "none"

    def clear_lines(self, rows):
        # Remove rows from top to bottom
        rows = sorted(rows)
        for idx in rows:
            del self.board[idx]
            self.board.insert(0, [None for _ in range(COLS)])
        self.lines += len(rows)

    def apply_scoring(self, cleared, tspin_type):
        difficult = False
        base = 0
        if tspin_type == "tspin":
            if cleared == 1:
                base = 800
            elif cleared == 2:
                base = 1200
            elif cleared == 3:
                base = 1600
            difficult = cleared >= 1
        else:
            if cleared == 1:
                base = 100
            elif cleared == 2:
                base = 300
            elif cleared == 3:
                base = 500
            elif cleared == 4:
                base = 800
                difficult = True

        # Back-to-Back
        if difficult:
            if self.b2b:
                base = int(base * 1.5)
            self.b2b = True
        elif cleared > 0:
            self.b2b = False

        # Combo
        if cleared > 0:
            self.combo += 1
            base += 50 * max(0, self.combo)  # 0, 50, 100, ...
        else:
            self.combo = -1

        # Level multiplier (Marathon/Zen)
        mult = (self.level + 1) if self.mode in (self.MODE_MARATHON, self.MODE_ZEN) else 1
        self.score += base * mult

        # Reset rotation flag for next piece scoring
        self.active.last_action_rotate = False
        self.active.last_kick_used = False

    # ------------------------------ Hold --------------------------------

    def hold(self):
        if self.game_over or self.paused: return
        if self.hold_used:
            return
        cur_kind = self.active.kind
        if self.held is None:
            # Store current, get next from queue
            self.held = cur_kind
            self.spawn_new()
        else:
            # Swap: spawn the previously held piece
            temp = self.held
            self.held = cur_kind
            self.spawn_new(from_hold=True, kind_override=temp)
        self.hold_used = True

    # ------------------------- Update & Input ---------------------------

    def update(self, dt_ms, keys):
        if self.game_over or self.paused:
            return

        # Sprint / Ultra timer tracking
        now = time.time()
        self.elapsed = now - self.start_time

        if self.mode == self.MODE_ULTRA and self.elapsed >= self.ultra_secs:
            self.game_over = True
            return

        # DAS/ARR handling
        self.handle_horizontal_repeat(dt_ms, keys)

        # Soft drop state
        self.soft_drop = keys[pygame.K_DOWN]

        # Gravity
        step_ms = max(1, self.gravity_ms // (8 if self.soft_drop else 1))
        self.gravity_accum += dt_ms
        while self.gravity_accum >= step_ms:
            self.gravity_accum -= step_ms
            if not self.move(0, 1):
                # On contact: start/advance lock timer
                self.grounded = True
                self.lock_timer += step_ms
                if self.lock_timer >= LOCK_DELAY:
                    self.lock_down(force=True)
                    break
            else:
                self.grounded = False
                self.lock_timer = 0

    def handle_horizontal_repeat(self, dt_ms, keys):
        # Held-repeat logic (DAS/ARR). Immediate moves are in the event loop.
        if self.left_down:
            self.left_timer += dt_ms
            if (not self.left_repeat and self.left_timer >= DAS) or (self.left_repeat and self.left_timer >= ARR):
                self.move(-1, 0)
                self.left_repeat = True
                self.left_timer = 0
        if self.right_down:
            self.right_timer += dt_ms
            if (not self.right_repeat and self.right_timer >= DAS) or (self.right_repeat and self.right_timer >= ARR):
                self.move(+1, 0)
                self.right_repeat = True
                self.right_timer = 0

    # ----------------------------- Render -------------------------------

    def draw(self, surf, font_small, font_big):
        surf.fill(BG)
        # Playfield rect
        well_x = 40
        well_y = 40
        well_w = COLS * CELL
        well_h = VISIBLE_ROWS * CELL
        pygame.draw.rect(surf, WELL_BG, (well_x-2, well_y-2, well_w+4, well_h+4), border_radius=8)

        # Grid lines
        for r in range(VISIBLE_ROWS + 1):
            y = well_y + r * CELL
            pygame.draw.line(surf, GRID, (well_x, y), (well_x + well_w, y))
        for c in range(COLS + 1):
            x = well_x + c * CELL
            pygame.draw.line(surf, GRID, (x, well_y), (x, well_y + well_h))

        # Draw locked blocks (only visible rows)
        for y in range(VANISH_ROWS, ROWS):
            for x in range(COLS):
                k = self.board[y][x]
                if k:
                    self.draw_cell(surf, well_x, well_y, x, y - VANISH_ROWS, COLORS[k])

        # Ghost piece
        if not self.game_over and self.active:
            gy = self.ghost_drop_y()
            for (x, y) in self.active.cells(offset=(0, gy - self.active.y)):
                if y >= VANISH_ROWS:
                    self.draw_cell(surf, well_x, well_y, x, y - VANISH_ROWS, GHOST, hollow=True)

        # Active piece
        if self.active and not self.game_over:
            for (x, y) in self.active.cells():
                if y >= VANISH_ROWS:
                    self.draw_cell(surf, well_x, well_y, x, y - VANISH_ROWS, COLORS[self.active.kind])

        # HUD (right sidebar)
        sidebar_x = well_x + well_w + 30
        self.text(surf, font_big, f"{self.mode}", sidebar_x, 30)
        self.text(surf, font_small, f"Score: {self.score}", sidebar_x, 80)
        self.text(surf, font_small, f"Level: {self.level}", sidebar_x, 110)
        self.text(surf, font_small, f"Lines: {self.lines}", sidebar_x, 140)
        self.text(surf, font_small, f"PPS: {self.pps():.2f}", sidebar_x, 170)

        time_y = 200
        if self.mode == self.MODE_SPRINT:
            self.text(surf, font_small, f"Target: {self.sprint_target}L", sidebar_x, time_y)
            self.text(surf, font_small, f"Time: {self.elapsed:.2f}s", sidebar_x, time_y + 30)
        elif self.mode == self.MODE_ULTRA:
            remain = max(0, self.ultra_secs - self.elapsed)
            self.text(surf, font_small, f"Time Left: {remain:.2f}s", sidebar_x, time_y)
        else:
            self.text(surf, font_small, f"Time: {self.elapsed:.2f}s", sidebar_x, time_y)

        # --- RELOCATED UI: Hold & Next (only 1 next) ---
        box_w = CELL * 4 + 8
        hold_y = 260
        self.text(surf, font_small, "HOLD", sidebar_x, hold_y - 24)
        self.draw_preview_box(surf, sidebar_x, hold_y, self.held)

        next_y = hold_y + box_w + 20  # stack below hold box
        next_kind = (list(self.nextq)[0] if len(self.nextq) > 0 else None)
        self.text(surf, font_small, "NEXT", sidebar_x, next_y - 24)
        self.draw_preview_box(surf, sidebar_x, next_y, next_kind)

        if self.paused:
            self.overlay(surf, "PAUSED (P to resume)", font_big)
        if self.game_over:
            msg = "Game Over"
            if self.mode == self.MODE_SPRINT and self.lines >= self.sprint_target:
                msg = f"SPRINT DONE! {self.elapsed:.2f}s"
            elif self.mode == self.MODE_ULTRA and self.elapsed >= self.ultra_secs:
                msg = f"ULTRA DONE! Score: {self.score}"
            self.overlay(surf, f"{msg}\nR: Restart   ESC: Menu", font_big)

    def pps(self):
        # Pieces per second (based on placed pieces)
        if self.elapsed <= 0: return 0.0
        return self.pieces_placed / self.elapsed

    def overlay(self, surf, msg, font_big):
        s = pygame.Surface((SCREEN_W, SCREEN_H), pygame.SRCALPHA)
        s.fill((0, 0, 0, 150))
        surf.blit(s, (0, 0))
        lines = msg.split("\n")
        y = SCREEN_H // 2 - 40
        for line in lines:
            t = font_big.render(line, True, TEXT)
            surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, y))
            y += t.get_height() + 10

    def draw_preview_box(self, surf, x, y, kind):
        box_w = CELL * 4 + 8
        box_h = CELL * 4 + 8
        pygame.draw.rect(surf, WELL_BG, (x, y, box_w, box_h), border_radius=6)
        if kind:
            self.draw_mini_piece(surf, x + 4, y + 4, kind)

    def draw_next_list(self, surf, x, y, kinds):
        # (Unused now; kept for reference)
        for i, kind in enumerate(kinds):
            self.draw_mini_piece(surf, x, y + i * (CELL * 2 + 10), kind, scale=0.5)

    def draw_mini_piece(self, surf, x, y, kind, scale=1.0):
        shape = SHAPES[kind][0]
        for (px, py) in shape:
            cx = int(x + px * CELL * scale)
            cy = int(y + py * CELL * scale)
            size = int(CELL * scale)
            pygame.draw.rect(surf, COLORS[kind], (cx, cy, size, size))
            pygame.draw.rect(surf, (0, 0, 0), (cx, cy, size, size), 2)

    def draw_cell(self, surf, wx, wy, x, y, color, hollow=False):
        rx = wx + x * CELL
        ry = wy + y * CELL
        if hollow:
            pygame.draw.rect(surf, color, (rx+2, ry+2, CELL-4, CELL-4), 2, border_radius=4)
        else:
            pygame.draw.rect(surf, color, (rx+1, ry+1, CELL-2, CELL-2), border_radius=6)
            pygame.draw.rect(surf, (0, 0, 0), (rx+1, ry+1, CELL-2, CELL-2), 2, border_radius=6)

    def text(self, surf, font, s, x, y):
        surf.blit(font.render(s, True, TEXT), (x, y))

    def ghost_drop_y(self):
        test = self.active.clone()
        while self.valid(test):
            test.y += 1
        return test.y - 1

# ---------------------------- Menu & Main ------------------------------

def draw_menu(surf, font_big, font_small):
    surf.fill(BG)
    title = font_big.render("TETRIS — Pygame", True, TEXT)
    surf.blit(title, (SCREEN_W // 2 - title.get_width() // 2, 80))

    lines = [
        "1 — Marathon",
        "2 — Sprint (40 Lines)",
        "3 — Ultra (120s)",
        "4 — Zen",
        "",
        "Controls:",
        "←/→ move, ↓ soft drop, Space hard drop",
        "Z/↑ rotate CW, X rotate CCW, A rotate 180",
        "C/Shift hold, P pause, R restart, ESC menu",
    ]
    y = 180
    for ln in lines:
        t = font_small.render(ln, True, TEXT)
        surf.blit(t, (SCREEN_W // 2 - t.get_width() // 2, y))
        y += 28

def main():
    pygame.init()
    pygame.display.set_caption("Tetris — Pygame (SRS, Ghost, Hold, 7-Bag)")
    screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
    clock = pygame.time.Clock()
    font_small = pygame.font.SysFont("consolas", 20)
    font_big = pygame.font.SysFont("consolas", 28, bold=True)

    running = True
    game = None
    on_menu = True

    while running:
        dt = clock.tick(FPS)
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            # Menu handling
            if on_menu:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_1:
                        game = Game(Game.MODE_MARATHON); on_menu = False
                    elif event.key == pygame.K_2:
                        game = Game(Game.MODE_SPRINT); on_menu = False
                    elif event.key == pygame.K_3:
                        game = Game(Game.MODE_ULTRA); on_menu = False
                    elif event.key == pygame.K_4:
                        game = Game(Game.MODE_ZEN); on_menu = False
                continue

            # In-game events
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    on_menu = True
                    game = None
                    continue
                if event.key == pygame.K_p:
                    if game and not game.game_over:
                        game.paused = not game.paused
                if event.key == pygame.K_r:
                    if game:
                        mode = game.mode
                        game = Game(mode)
                if not game or game.paused or game.game_over:
                    continue
                # Immediate moves for snappy feel
                if event.key == pygame.K_LEFT:
                    game.left_down = True
                    game.left_timer = 0
                    game.left_repeat = False
                    game.move(-1, 0)
                elif event.key == pygame.K_RIGHT:
                    game.right_down = True
                    game.right_timer = 0
                    game.right_repeat = False
                    game.move(+1, 0)
                elif event.key in (pygame.K_UP, pygame.K_z):
                    game.rotate(+1)  # CW
                elif event.key == pygame.K_x:
                    game.rotate(-1)  # CCW
                elif event.key == pygame.K_a:
                    game.rotate(2)   # 180
                elif event.key == pygame.K_SPACE:
                    game.harddrop()
                elif event.key in (pygame.K_c, pygame.K_LSHIFT, pygame.K_RSHIFT):
                    game.hold()

            if event.type == pygame.KEYUP and game:
                if event.key == pygame.K_LEFT:
                    game.left_down = False
                elif event.key == pygame.K_RIGHT:
                    game.right_down = False

        # Update
        if game and not on_menu:
            keys = pygame.key.get_pressed()
            game.update(dt, keys)

        # Draw
        if on_menu:
            draw_menu(screen, font_big, font_small)
        else:
            game.draw(screen, font_small, font_big)
        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
