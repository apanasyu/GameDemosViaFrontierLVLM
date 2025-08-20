import pygame
import random
import json
import os
from collections import deque

# ------------------------------
# Config
# ------------------------------
CELL = 30
COLS, ROWS = 10, 20
HIDDEN_ROWS = 4  # spawn buffer
MATRIX_H = ROWS + HIDDEN_ROWS

FPS = 60
START_LEVEL = 1
LINES_PER_LEVEL = 10
LOCK_DELAY_MS = 500  # 0.5s

# Layout: playfield centered-left, HUD on sides
BORDER = 12
GRID_W = COLS * CELL
GRID_H = ROWS * CELL
LEFT_PANEL_W = 160
RIGHT_PANEL_W = 160
WIN_W = LEFT_PANEL_W + BORDER + GRID_W + BORDER + RIGHT_PANEL_W
WIN_H = BORDER + GRID_H + BORDER

# Colors
BG = (16, 18, 24)
GRID_BG = (24, 26, 34)
GRID_LINE = (38, 42, 55)
WHITE = (240, 240, 245)
MUTED = (170, 170, 180)
ACCENT = (90, 200, 250)

# Tetrimino colors (modern standard)
COLORS = {
    'I': (0, 255, 255),     # Cyan
    'O': (255, 255, 0),     # Yellow
    'T': (128, 0, 128),     # Purple
    'S': (0, 255, 0),       # Green
    'Z': (255, 0, 0),       # Red
    'J': (0, 0, 255),       # Blue
    'L': (255, 165, 0),     # Orange
    'GHOST': (255, 255, 255)  # used with alpha
}

# Gravity speeds (frames/step or seconds/row); we’ll use seconds/row (approx Guideline)
# Using a simple decreasing scale per level
def gravity_seconds_for_level(level: int) -> float:
    # Tetris Guideline uses a complex table; here a smooth curve
    base = 0.8 - (level - 1) * 0.007
    return max(0.02, base ** (level - 1))

# Piece definitions: rotation states as lists of (x,y) in a 4x4 grid
# Using SRS rotation origin semantics (we handle kicks separately)
PIECES = {
    'I': [
        [(0,2),(1,2),(2,2),(3,2)],
        [(2,0),(2,1),(2,2),(2,3)],
        [(0,1),(1,1),(2,1),(3,1)],
        [(1,0),(1,1),(1,2),(1,3)],
    ],
    'O': [
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
        [(1,1),(2,1),(1,2),(2,2)],
    ],
    'T': [
        [(1,1),(0,2),(1,2),(2,2)],
        [(1,1),(1,2),(2,1),(1,0)],
        [(0,1),(1,1),(2,1),(1,2)],
        [(1,2),(1,1),(0,1),(1,0)],
    ],
    'S': [
        [(1,1),(2,1),(0,2),(1,2)],
        [(1,0),(1,1),(2,1),(2,2)],
        [(1,1),(2,1),(0,2),(1,2)],
        [(1,0),(1,1),(2,1),(2,2)],
    ],
    'Z': [
        [(0,1),(1,1),(1,2),(2,2)],
        [(2,0),(1,1),(2,1),(1,2)],
        [(0,1),(1,1),(1,2),(2,2)],
        [(2,0),(1,1),(2,1),(1,2)],
    ],
    'J': [
        [(0,1),(0,2),(1,2),(2,2)],
        [(1,0),(2,0),(1,1),(1,2)],
        [(0,1),(1,1),(2,1),(2,2)],
        [(1,0),(1,1),(0,2),(1,2)],
    ],
    'L': [
        [(2,1),(0,2),(1,2),(2,2)],
        [(1,0),(1,1),(1,2),(2,2)],
        [(0,1),(1,1),(2,1),(0,2)],
        [(0,0),(1,0),(1,1),(1,2)],
    ],
}

# SRS kick data (from Tetris Guideline)
# For non-I pieces
JLSTZ_KICKS = {
    (0,1): [(0,0),(-1,0),(-1,1),(0,-2),(-1,-2)],
    (1,0): [(0,0),(1,0),(1,-1),(0,2),(1,2)],
    (1,2): [(0,0),(1,0),(1,-1),(0,2),(1,2)],
    (2,1): [(0,0),(-1,0),(-1,1),(0,-2),(-1,-2)],
    (2,3): [(0,0),(1,0),(1,1),(0,-2),(1,-2)],
    (3,2): [(0,0),(-1,0),(-1,-1),(0,2),(-1,2)],
    (3,0): [(0,0),(-1,0),(-1,-1),(0,2),(-1,2)],
    (0,3): [(0,0),(1,0),(1,1),(0,-2),(1,-2)],
}
# For I piece
I_KICKS = {
    (0,1): [(0,0),(-2,0),(1,0),(-2,-1),(1,2)],
    (1,0): [(0,0),(2,0),(-1,0),(2,1),(-1,-2)],
    (1,2): [(0,0),(-1,0),(2,0),(-1,2),(2,-1)],
    (2,1): [(0,0),(1,0),(-2,0),(1,-2),(-2,1)],
    (2,3): [(0,0),(2,0),(-1,0),(2,1),(-1,-2)],
    (3,2): [(0,0),(-2,0),(1,0),(-2,-1),(1,2)],
    (3,0): [(0,0),(1,0),(-2,0),(1,-2),(-2,1)],
    (0,3): [(0,0),(-1,0),(2,0),(-1,2),(2,-1)],
}

# Scoring
SCORE_CLEAR = {1: 100, 2: 300, 3: 500, 4: 800}
B2B_BONUS = 1200  # × level for consecutive Tetrises

# High score file
HS_FILE = "tetris_highscores.json"
MAX_HS = 10

# ------------------------------
# Utilities
# ------------------------------
def load_highscores():
    if os.path.exists(HS_FILE):
        try:
            with open(HS_FILE, "r") as f:
                return json.load(f)
        except:
            return []
    return []

def save_highscores(entries):
    try:
        with open(HS_FILE, "w") as f:
            json.dump(entries[:MAX_HS], f)
    except:
        pass

def add_highscore(name, score):
    entries = load_highscores()
    entries.append({"name": name[:3].upper(), "score": score})
    entries.sort(key=lambda e: e["score"], reverse=True)
    save_highscores(entries)

# ------------------------------
# Core classes
# ------------------------------
class Bag7:
    def __init__(self):
        self.bag = []
        self.refill()
    def refill(self):
        self.bag = list(PIECES.keys())
        random.shuffle(self.bag)
    def pop(self):
        if not self.bag:
            self.refill()
        return self.bag.pop()

class Piece:
    def __init__(self, kind):
        self.kind = kind
        self.rot = 0
        # spawn in center over hidden area
        self.x = (COLS // 2) - 2
        self.y = -(HIDDEN_ROWS)  # top off-screen
        self.used_hold = False  # managed at board level
    @property
    def cells(self):
        return PIECES[self.kind][self.rot]
    def blocks(self, ox=None, oy=None, rot=None):
        r = self.rot if rot is None else rot
        x = self.x if ox is None else ox
        y = self.y if oy is None else oy
        for cx, cy in PIECES[self.kind][r]:
            yield (x + cx, y + cy)
    def rotated(self, dir=1):
        # dir = +1 clockwise, -1 ccw
        return (self.rot + dir) % 4

class Board:
    def __init__(self):
        self.grid = [[None for _ in range(COLS)] for _ in range(MATRIX_H)]
        self.bag = Bag7()
        self.active = Piece(self.bag.pop())
        self.hold = None
        self.can_hold = True
        self.queue = deque([self.bag.pop()])  # show only 1 next
        self.score = 0
        self.lines = 0
        self.level = START_LEVEL
        self.gravity_timer = 0.0
        self.lock_timer_ms = None
        self.last_clear_was_tetris = False
        self.game_over = False

    # ---- Collision & placement ----
    def in_bounds(self, x, y):
        if x < 0 or x >= COLS: return False
        if y >= MATRIX_H: return False
        return True
    def is_occupied(self, x, y):
        if y < 0:  # hidden rows above are not occupied unless we placed there
            return False
        return self.grid[y][x] is not None
    def can_place(self, piece: Piece, ox=None, oy=None, rot=None):
        for x, y in piece.blocks(ox, oy, rot):
            if not self.in_bounds(x, y): return False
            if self.is_occupied(x, y): return False
        return True

    # ---- Movement ----
    def try_move(self, dx, dy):
        p = self.active
        if self.can_place(p, p.x + dx, p.y + dy, p.rot):
            p.x += dx
            p.y += dy
            self.reset_lock_delay_if_landed_changed()
            return True
        return False

    # ---- Rotation with SRS ----
    def try_rotate(self, dir=1):
        p = self.active
        from_r = p.rot
        to_r = p.rotated(dir)
        kicks = None
        key = (from_r, to_r)
        if p.kind == 'O':
            # O has no kicks; just try in place
            if self.can_place(p, p.x, p.y, to_r):
                p.rot = to_r
                self.reset_lock_delay_if_landed_changed()
                return True
            return False
        elif p.kind == 'I':
            kicks = I_KICKS.get(key, [(0,0)])
        else:
            kicks = JLSTZ_KICKS.get(key, [(0,0)])
        for ox, oy in kicks:
            nx, ny = p.x + ox, p.y + oy
            if self.can_place(p, nx, ny, to_r):
                p.x, p.y, p.rot = nx, ny, to_r
                self.reset_lock_delay_if_landed_changed()
                return True
        return False

    # ---- Gravity / Locking ----
    def step_gravity(self, seconds, current_ms):
        if self.game_over:
            return
        self.gravity_timer += seconds
        fall_s = gravity_seconds_for_level(self.level)
        while self.gravity_timer >= fall_s:
            self.gravity_timer -= fall_s
            if not self.try_move(0, 1):
                # land -> start/continue lock delay
                if self.lock_timer_ms is None:
                    self.lock_timer_ms = current_ms
                else:
                    if current_ms - self.lock_timer_ms >= LOCK_DELAY_MS:
                        self.lock_piece()
                break

    def is_landed(self):
        # cannot move down
        return not self.can_place(self.active, self.active.x, self.active.y + 1, self.active.rot)

    def reset_lock_delay_if_landed_changed(self):
        # Called on movement/rotation; per “infinity placement” lock delay resets when player moves/rotates
        if self.is_landed():
            self.lock_timer_ms = 0  # will be set to now at next gravity touch
        else:
            self.lock_timer_ms = None

    def hard_drop(self):
        rows = 0
        while self.try_move(0, 1):
            rows += 1
        # score hard drop rows * 2
        self.score += rows * 2
        # lock immediately
        self.lock_piece()

    def soft_drop(self):
        if self.try_move(0, 1):
            self.score += 1  # per row
            return True
        return False

    def lock_piece(self):
        p = self.active
        for x, y in p.blocks():
            if y < 0:
                self.game_over = True
                return
            self.grid[y][x] = COLORS[p.kind]
        cleared = self.clear_lines()
        # scoring
        if cleared:
            if cleared == 4:
                pts = SCORE_CLEAR[4] * self.level
                # Back-to-back tetris
                if self.last_clear_was_tetris:
                    pts = B2B_BONUS * self.level
                self.last_clear_was_tetris = True
                self.score += pts
            else:
                self.last_clear_was_tetris = False
                self.score += SCORE_CLEAR[cleared] * self.level
            self.lines += cleared
            self.level = START_LEVEL + (self.lines // LINES_PER_LEVEL)
        else:
            self.last_clear_was_tetris = False

        # Next piece
        self.spawn_next()
        self.lock_timer_ms = None
        self.can_hold = True

    def clear_lines(self):
        full_rows = [y for y in range(MATRIX_H) if all(self.grid[y][x] is not None for x in range(COLS))]
        # Only visible rows count toward scoring/level; but clearing hidden is rare—keep simple
        cleared = 0
        for y in reversed(full_rows):
            del self.grid[y]
            self.grid.insert(0, [None for _ in range(COLS)])
            cleared += 1
        return cleared

    def spawn_next(self):
        kind = self.queue.popleft()
        self.queue.append(self.bag.pop())
        self.active = Piece(kind)
        if not self.can_place(self.active, self.active.x, self.active.y, self.active.rot):
            self.game_over = True

    def hold_piece(self):
        if not self.can_hold:
            return
        kind = self.active.kind
        if self.hold is None:
            self.hold = kind
            self.active = Piece(self.queue.popleft())
            self.queue.append(self.bag.pop())
        else:
            self.hold, kind = kind, self.hold
            self.active = Piece(kind)
        self.can_hold = False
        # If spawn is blocked, game over
        if not self.can_place(self.active, self.active.x, self.active.y, self.active.rot):
            self.game_over = True

    # ---- Ghost ----
    def ghost_y(self):
        p = self.active
        gy = p.y
        while self.can_place(p, p.x, gy + 1, p.rot):
            gy += 1
        return gy

# ------------------------------
# Drawing
# ------------------------------
def draw_text(surf, text, size, x, y, color=WHITE, align="topleft"):
    font = pygame.font.SysFont("arial", size, bold=True)
    img = font.render(text, True, color)
    r = img.get_rect()
    setattr(r, align, (x, y))
    surf.blit(img, r)

def draw_board(surf, board: Board):
    # Panels rects
    left_x = BORDER
    grid_x = LEFT_PANEL_W + BORDER
    right_x = LEFT_PANEL_W + BORDER + GRID_W + BORDER

    # Backgrounds
    surf.fill(BG)
    # Playfield bg
    pygame.draw.rect(surf, GRID_BG, (grid_x, BORDER, GRID_W, GRID_H), border_radius=8)

    # Grid lines
    for c in range(COLS + 1):
        x = grid_x + c * CELL
        pygame.draw.line(surf, GRID_LINE, (x, BORDER), (x, BORDER + GRID_H))
    for r in range(ROWS + 1):
        y = BORDER + r * CELL
        pygame.draw.line(surf, GRID_LINE, (grid_x, y), (grid_x + GRID_W, y))

    # Locked blocks
    for y in range(ROWS):  # only visible rows
        gy = y + HIDDEN_ROWS
        for x in range(COLS):
            col = board.grid[gy][x]
            if col:
                rx = grid_x + x * CELL
                ry = BORDER + y * CELL
                pygame.draw.rect(surf, col, (rx+1, ry+1, CELL-2, CELL-2), border_radius=4)

    # Ghost
    gy = board.ghost_y()
    p = board.active
    ghost_alpha = 80
    ghost_surf = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    for x, y in p.blocks(oy=gy):
        if y >= HIDDEN_ROWS:
            rx = grid_x + x * CELL
            ry = BORDER + (y - HIDDEN_ROWS) * CELL
            pygame.draw.rect(ghost_surf, (*COLORS['GHOST'], ghost_alpha),
                             (rx+1, ry+1, CELL-2, CELL-2), border_radius=4, width=2)
    surf.blit(ghost_surf, (0,0))

    # Active piece
    for x, y in p.blocks():
        if y >= HIDDEN_ROWS:
            rx = grid_x + x * CELL
            ry = BORDER + (y - HIDDEN_ROWS) * CELL
            pygame.draw.rect(surf, COLORS[p.kind], (rx+1, ry+1, CELL-2, CELL-2), border_radius=4)

    # Left Panel (HOLD)
    panel = pygame.Rect(left_x, BORDER, LEFT_PANEL_W, GRID_H)
    pygame.draw.rect(surf, (28, 30, 40), panel, border_radius=10)
    draw_text(surf, "HOLD", 20, panel.centerx, panel.y + 12, MUTED, align="midtop")
    draw_mini_piece(surf, board.hold, panel, offset_y=40)

    # Right Panel (NEXT + stats)
    rpanel = pygame.Rect(right_x, BORDER, RIGHT_PANEL_W, GRID_H)
    pygame.draw.rect(surf, (28, 30, 40), rpanel, border_radius=10)
    draw_text(surf, "NEXT", 20, rpanel.centerx, rpanel.y + 12, MUTED, align="midtop")
    next_kind = board.queue[0]
    draw_mini_piece(surf, next_kind, rpanel, offset_y=40)

    # Stats
    draw_text(surf, f"SCORE", 18, rpanel.centerx, rpanel.y + 140, MUTED, "midtop")
    draw_text(surf, f"{board.score}", 28, rpanel.centerx, rpanel.y + 162, WHITE, "midtop")
    draw_text(surf, f"LEVEL", 18, rpanel.centerx, rpanel.y + 210, MUTED, "midtop")
    draw_text(surf, f"{board.level}", 28, rpanel.centerx, rpanel.y + 232, WHITE, "midtop")
    draw_text(surf, f"LINES", 18, rpanel.centerx, rpanel.y + 280, MUTED, "midtop")
    draw_text(surf, f"{board.lines}", 28, rpanel.centerx, rpanel.y + 302, WHITE, "midtop")

def draw_mini_piece(surf, kind, panel_rect, offset_y=40):
    if not kind:
        # empty box
        box = pygame.Rect(panel_rect.x + 20, panel_rect.y + offset_y, panel_rect.w - 40, 100)
        pygame.draw.rect(surf, (22,24,32), box, border_radius=8)
        pygame.draw.rect(surf, (40,44,58), box, width=2, border_radius=8)
        return
    box = pygame.Rect(panel_rect.x + 20, panel_rect.y + offset_y, panel_rect.w - 40, 100)
    pygame.draw.rect(surf, (22,24,32), box, border_radius=8)
    pygame.draw.rect(surf, (40,44,58), box, width=2, border_radius=8)
    # draw centered using 4x4 grid
    size = 20
    # compute bounding box of blocks for centering
    cells = PIECES[kind][0]
    minx = min(c[0] for c in cells)
    maxx = max(c[0] for c in cells)
    miny = min(c[1] for c in cells)
    maxy = max(c[1] for c in cells)
    w = (maxx - minx + 1) * size
    h = (maxy - miny + 1) * size
    ox = box.x + (box.w - w)//2
    oy = box.y + (box.h - h)//2
    for cx, cy in cells:
        rx = ox + (cx - minx) * size
        ry = oy + (cy - miny) * size
        pygame.draw.rect(surf, COLORS[kind], (rx+1, ry+1, size-2, size-2), border_radius=4)

def draw_pause_overlay(surf):
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    overlay.fill((0,0,0,140))
    surf.blit(overlay, (0,0))
    draw_text(surf, "PAUSED", 48, WIN_W//2, WIN_H//2 - 24, ACCENT, "center")
    draw_text(surf, "Press P to resume", 20, WIN_W//2, WIN_H//2 + 20, WHITE, "center")

def draw_menu(surf, selected=0):
    surf.fill(BG)
    title = "TETRIS CLASSIC"
    draw_text(surf, title, 56, WIN_W//2, 80, WHITE, "center")
    items = ["START GAME", "HIGH SCORES", "QUIT"]
    for i, it in enumerate(items):
        c = ACCENT if i == selected else WHITE
        draw_text(surf, it, 28, WIN_W//2, 200 + i*56, c, "center")
    draw_text(surf, "Use ↑/↓ and Enter", 18, WIN_W//2, WIN_H-56, MUTED, "center")

def draw_gameover(surf, score, selected=0, entering_name=False, name=""):
    overlay = pygame.Surface((WIN_W, WIN_H), pygame.SRCALPHA)
    overlay.fill((0,0,0,140))
    surf.blit(overlay, (0,0))
    draw_text(surf, "GAME OVER", 56, WIN_W//2, 100, WHITE, "center")
    draw_text(surf, f"Score: {score}", 28, WIN_W//2, 180, WHITE, "center")
    if entering_name:
        draw_text(surf, "NEW HIGH SCORE! Enter initials:", 22, WIN_W//2, 230, MUTED, "center")
        draw_text(surf, name or "_", 40, WIN_W//2, 262, ACCENT, "center")
    items = ["PLAY AGAIN", "MAIN MENU"]
    for i, it in enumerate(items):
        c = ACCENT if i == selected else WHITE
        draw_text(surf, it, 28, WIN_W//2, 330 + i*52, c, "center")
    draw_text(surf, "Press R to restart", 18, WIN_W//2, WIN_H-56, MUTED, "center")

def draw_highscores(surf, selected=0):
    surf.fill(BG)
    draw_text(surf, "HIGH SCORES", 48, WIN_W//2, 60, WHITE, "center")
    hs = load_highscores()[:MAX_HS]
    if not hs:
        draw_text(surf, "No scores yet.", 24, WIN_W//2, 140, MUTED, "center")
    else:
        y = 140
        for i, e in enumerate(hs):
            rank = f"{i+1:>2}."
            line = f"{rank}  {e['name']:<3}   {e['score']}"
            draw_text(surf, line, 26, WIN_W//2, y, WHITE, "center")
            y += 36
    items = ["BACK"]
    c = ACCENT if selected == 0 else WHITE
    draw_text(surf, items[0], 28, WIN_W//2, WIN_H-100, c, "center")

# ------------------------------
# Main game loop / states
# ------------------------------
def main():
    pygame.init()
    pygame.display.set_caption("Tetris Classic")
    screen = pygame.display.set_mode((WIN_W, WIN_H))
    clock = pygame.time.Clock()

    state = "menu"
    menu_sel = 0
    hs_sel = 0

    board = None
    paused = False

    go_sel = 0
    entering_name = False
    name_buf = ""

    running = True
    while running:
        dt = clock.tick(FPS) / 1000.0
        now_ms = pygame.time.get_ticks()

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False

            if state == "menu":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_UP, pygame.K_w):
                        menu_sel = (menu_sel - 1) % 3
                    elif event.key in (pygame.K_DOWN, pygame.K_s):
                        menu_sel = (menu_sel + 1) % 3
                    elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                        if menu_sel == 0:
                            board = Board()
                            state = "playing"
                        elif menu_sel == 1:
                            state = "highscores"
                            hs_sel = 0
                        elif menu_sel == 2:
                            running = False
                    elif event.key == pygame.K_ESCAPE:
                        running = False

            elif state == "highscores":
                if event.type == pygame.KEYDOWN:
                    if event.key in (pygame.K_RETURN, pygame.K_KP_ENTER, pygame.K_ESCAPE):
                        state = "menu"

            elif state == "playing":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        state = "menu"
                    elif event.key == pygame.K_p:
                        paused = not paused
                    if not paused and not board.game_over:
                        if event.key == pygame.K_LEFT:
                            board.try_move(-1, 0)
                        elif event.key == pygame.K_RIGHT:
                            board.try_move(1, 0)
                        elif event.key == pygame.K_DOWN:
                            board.soft_drop()
                        elif event.key == pygame.K_SPACE:
                            board.hard_drop()
                        elif event.key in (pygame.K_UP, pygame.K_x):
                            board.try_rotate(+1)
                        elif event.key in (pygame.K_z,):
                            board.try_rotate(-1)
                        elif event.key in (pygame.K_c, pygame.K_LSHIFT):
                            board.hold_piece()

            elif state == "gameover":
                if entering_name:
                    if event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_RETURN:
                            add_highscore(name_buf or "AAA", board.score)
                            entering_name = False
                        elif event.key == pygame.K_BACKSPACE:
                            name_buf = name_buf[:-1]
                        else:
                            ch = event.unicode
                            if ch and ch.isalnum() and len(name_buf) < 3:
                                name_buf += ch.upper()
                else:
                    if event.type == pygame.KEYDOWN:
                        if event.key in (pygame.K_UP, pygame.K_w, pygame.K_DOWN, pygame.K_s):
                            go_sel = 1 - go_sel
                        elif event.key == pygame.K_r:
                            board = Board()
                            state = "playing"
                        elif event.key in (pygame.K_RETURN, pygame.K_KP_ENTER):
                            if go_sel == 0:
                                board = Board()
                                state = "playing"
                            else:
                                state = "menu"
                        elif event.key == pygame.K_ESCAPE:
                            state = "menu"

        # Update
        if state == "playing":
            if not paused and not board.game_over:
                board.step_gravity(dt, now_ms)
                # Delayed lock when landed (without waiting for next gravity tick)
                if board.is_landed():
                    if board.lock_timer_ms is None:
                        board.lock_timer_ms = now_ms
                    elif now_ms - board.lock_timer_ms >= LOCK_DELAY_MS:
                        board.lock_piece()
            if board and board.game_over:
                # Check HS
                entries = load_highscores()
                if len(entries) < MAX_HS or board.score > min([e["score"] for e in entries] + [0]):
                    entering_name = True
                    name_buf = ""
                else:
                    entering_name = False
                state = "gameover"
                go_sel = 0

        # Draw
        if state == "menu":
            draw_menu(screen, menu_sel)
        elif state == "highscores":
            draw_highscores(screen, hs_sel)
        elif state == "playing":
            draw_board(screen, board)
            if paused:
                draw_pause_overlay(screen)
        elif state == "gameover":
            draw_board(screen, board)
            draw_gameover(screen, board.score, go_sel, entering_name, name_buf)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
