import pygame
import sys
import json
import random
from pathlib import Path

# --------------------------
# Config
# --------------------------
WINDOW_W, WINDOW_H = 540, 900  # portrait
FPS = 60

GRID_SIZE = 8
CELL = 54  # grid cell size in pixels
GRID_PAD = 10
GRID_W = GRID_SIZE * CELL
GRID_H = GRID_SIZE * CELL

# Grid placed centered horizontally, with space for HUD on top and tray at bottom
TOP_MARGIN = 120
GRID_LEFT = (WINDOW_W - GRID_W) // 2
GRID_TOP = TOP_MARGIN

BOTTOM_TRAY_H = 220

BG_COLOR = (28, 33, 41)
GRID_BG = (44, 50, 61)
GRID_LINE = (70, 77, 92)
TEXT_COLOR = (235, 240, 255)
GHOST_OK = (60, 180, 90, 120)
GHOST_BAD = (210, 70, 70, 120)
PIECE_COLORS = [
    (244, 67, 54),
    (33, 150, 243),
    (255, 193, 7),
    (76, 175, 80),
    (156, 39, 176),
    (255, 87, 34),
    (0, 188, 212),
    (121, 85, 72),
]

FLASH_COLOR = (255, 255, 255)
FLASH_MS = 220

HIGHSCORE_FILE = Path("block_blast_highscore.json")

# --------------------------
# Shapes (no rotation)
# Each shape is a list of coordinate tuples relative to (0,0)
# --------------------------
def shape_from_matrix(mat):
    cells = []
    for r, row in enumerate(mat):
        for c, v in enumerate(row):
            if v:
                cells.append((r, c))
    return norm_shape(cells)

def norm_shape(cells):
    # normalize so smallest r,c starts at (0,0)
    min_r = min(r for r, _ in cells)
    min_c = min(c for _, c in cells)
    return sorted([(r - min_r, c - min_c) for r, c in cells])

# A curated set (small to medium) to fit 8x8 well
SHAPES = [
    # singles / dominos
    shape_from_matrix([[1]]),
    shape_from_matrix([[1,1]]),
    shape_from_matrix([[1],[1]]),
    # tri-lines
    shape_from_matrix([[1,1,1]]),
    shape_from_matrix([[1],[1],[1]]),
    # 2x2 square
    shape_from_matrix([[1,1],[1,1]]),
    # L-2x3 variants
    shape_from_matrix([[1,0],[1,0],[1,1]]),
    shape_from_matrix([[0,1],[0,1],[1,1]]),
    shape_from_matrix([[1,1],[1,0],[1,0]]),
    shape_from_matrix([[1,1],[0,1],[0,1]]),
    # T shapes
    shape_from_matrix([[1,1,1],[0,1,0]]),
    shape_from_matrix([[0,1,0],[1,1,1]]),
    # 3-block corner
    shape_from_matrix([[1,1],[1,0]]),
    shape_from_matrix([[1,1],[0,1]]),
    # plus sign (3x3 light)
    shape_from_matrix([[0,1,0],[1,1,1],[0,1,0]]),
]

# --------------------------
# Utility
# --------------------------
def load_highscore():
    if HIGHSCORE_FILE.exists():
        try:
            return int(json.loads(HIGHSCORE_FILE.read_text()).get("highscore", 0))
        except Exception:
            return 0
    return 0

def save_highscore(v):
    try:
        HIGHSCORE_FILE.write_text(json.dumps({"highscore": int(v)}))
    except Exception:
        pass

def draw_text(surface, text, x, y, font, color=TEXT_COLOR, center=False):
    img = font.render(text, True, color)
    rect = img.get_rect()
    if center:
        rect.center = (x, y)
    else:
        rect.topleft = (x, y)
    surface.blit(img, rect)

# --------------------------
# Piece class for dragging
# --------------------------
class Piece:
    def __init__(self, cells, color, scale=CELL):
        # cells: list[(r,c)] relative
        self.cells = cells
        self.color = color
        self.scale = scale

        # visual bounding box in grid cells
        max_r = max(r for r, _ in cells)
        max_c = max(c for _, c in cells)
        self.h = max_r + 1
        self.w = max_c + 1

        # screen position (top-left in px)
        self.x = 0
        self.y = 0

        # dragging
        self.drag_offset = (0, 0)
        self.dragging = False

    def set_pos(self, x, y):
        self.x, self.y = x, y

    def rect(self):
        return pygame.Rect(self.x, self.y, self.w * self.scale, self.h * self.scale)

    def start_drag(self, mx, my):
        if self.rect().collidepoint(mx, my):
            self.dragging = True
            self.drag_offset = (mx - self.x, my - self.y)
            return True
        return False

    def drag(self, mx, my):
        if self.dragging:
            self.x = mx - self.drag_offset[0]
            self.y = my - self.drag_offset[1]

    def stop_drag(self):
        self.dragging = False

    def draw(self, surf):
        for r, c in self.cells:
            rx = self.x + c * self.scale
            ry = self.y + r * self.scale
            pygame.draw.rect(surf, self.color, (rx+2, ry+2, self.scale-4, self.scale-4), border_radius=8)

    def draw_ghost_on_grid(self, surf, grid_origin, cell_size, valid):
        # draw semi-transparent overlay at nearest snapped grid pos (handled by caller)
        color = GHOST_OK if valid else GHOST_BAD
        ghost = pygame.Surface((self.w * cell_size, self.h * cell_size), pygame.SRCALPHA)
        ghost.fill((0,0,0,0))
        for r, c in self.cells:
            rx = c * cell_size
            ry = r * cell_size
            cell = pygame.Surface((cell_size-3, cell_size-3), pygame.SRCALPHA)
            cell.fill(color)
            ghost.blit(cell, (rx+1, ry+1))
        surf.blit(ghost, grid_origin)

# --------------------------
# Board
# --------------------------
class Board:
    def __init__(self, rows, cols):
        self.r = rows
        self.c = cols
        self.cells = [[None for _ in range(cols)] for _ in range(rows)]  # store colors

        self.flash_timer = 0
        self.flash_coords = []  # list[(r,c)]

    def inside(self, rr, cc):
        return 0 <= rr < self.r and 0 <= cc < self.c

    def empty_at(self, rr, cc):
        return self.inside(rr, cc) and self.cells[rr][cc] is None

    def can_place(self, piece, top_r, left_c):
        for dr, dc in piece.cells:
            rr = top_r + dr
            cc = left_c + dc
            if not self.inside(rr, cc) or self.cells[rr][cc] is not None:
                return False
        return True

    def place(self, piece, top_r, left_c):
        for dr, dc in piece.cells:
            rr = top_r + dr
            cc = left_c + dc
            self.cells[rr][cc] = piece.color

    def find_full_lines(self):
        full_rows = [r for r in range(self.r) if all(self.cells[r][c] is not None for c in range(self.c))]
        full_cols = [c for c in range(self.c) if all(self.cells[r][c] is not None for r in range(self.r))]
        return full_rows, full_cols

    def clear_lines(self, rows, cols):
        coords = []
        for r in rows:
            for c in range(self.c):
                coords.append((r, c))
        for c in cols:
            for r in range(self.r):
                coords.append((r, c))

        # flash then clear
        self.flash_coords = coords
        self.flash_timer = FLASH_MS

        # do the actual clear after flash ends; handled in update()
        # so we mark them but defer erasing
        return len(set(coords))

    def commit_clears_if_due(self, dt_ms):
        if self.flash_timer > 0:
            self.flash_timer -= dt_ms
            if self.flash_timer <= 0:
                # time to clear
                for (r, c) in self.flash_coords:
                    self.cells[r][c] = None
                self.flash_coords = []

    def any_placement_possible(self, piece):
        for r in range(self.r):
            for c in range(self.c):
                if self.can_place(piece, r, c):
                    return True
        return False

    def draw(self, surf):
        # grid bg
        pygame.draw.rect(surf, GRID_BG, (GRID_LEFT, GRID_TOP, GRID_W, GRID_H), border_radius=10)
        # grid lines
        for i in range(self.r + 1):
            y = GRID_TOP + i * CELL
            pygame.draw.line(surf, GRID_LINE, (GRID_LEFT, y), (GRID_LEFT + GRID_W, y), 1)
        for j in range(self.c + 1):
            x = GRID_LEFT + j * CELL
            pygame.draw.line(surf, GRID_LINE, (x, GRID_TOP), (x, GRID_TOP + GRID_H), 1)
        # filled cells
        for r in range(self.r):
            for c in range(self.c):
                color = self.cells[r][c]
                if color:
                    x = GRID_LEFT + c * CELL
                    y = GRID_TOP + r * CELL
                    pygame.draw.rect(surf, color, (x+2, y+2, CELL-4, CELL-4), border_radius=8)

        # flash overlay
        if self.flash_timer > 0 and self.flash_coords:
            alpha = 180
            overlay = pygame.Surface((CELL-3, CELL-3))
            overlay.fill(FLASH_COLOR)
            overlay.set_alpha(alpha)
            for (r, c) in self.flash_coords:
                x = GRID_LEFT + c * CELL + 1
                y = GRID_TOP + r * CELL + 1
                surf.blit(overlay, (x, y))

# --------------------------
# Game States
# --------------------------
STATE_MENU = "menu"
STATE_PLAY = "play"
STATE_GAMEOVER = "gameover"

# --------------------------
# Helpers
# --------------------------
def random_piece():
    cells = random.choice(SHAPES)
    color = random.choice(PIECE_COLORS)
    return Piece(cells, color, CELL)

def new_tray_set():
    return [random_piece(), random_piece(), random_piece()]

def tray_layout_rects():
    # Three slots in bottom tray
    tray_top = GRID_TOP + GRID_H + 24
    slot_w = WINDOW_W // 3
    rects = []
    for i in range(3):
        x = i * slot_w + 14
        w = slot_w - 28
        rects.append(pygame.Rect(x, tray_top, w, BOTTOM_TRAY_H - 36))
    return rects

def center_piece_in_rect(piece, rect):
    px = rect.centerx - (piece.w * CELL) // 2
    py = rect.centery - (piece.h * CELL) // 2
    piece.set_pos(px, py)

def mouse_to_grid(mx, my):
    if GRID_LEFT <= mx < GRID_LEFT + GRID_W and GRID_TOP <= my < GRID_TOP + GRID_H:
        col = (mx - GRID_LEFT) // CELL
        row = (my - GRID_TOP) // CELL
        return row, col
    return None, None

def snapped_grid_origin_for_piece(piece, mx, my):
    # Snap piece top-left to nearest grid cell based on its (0,0) block location relative to mouse
    # We’ll snap the piece’s top-left so that its (0,0) aims at the hovered cell’s top-left.
    row, col = mouse_to_grid(mx, my)
    if row is None:
        return None, None, None, None
    # We want to align so the mouse sits somewhere over the piece; simplest: snap piece’s top-left
    # so that (row, col) corresponds to the piece's (0,0)
    top_r = row
    left_c = col
    px = GRID_LEFT + left_c * CELL
    py = GRID_TOP + top_r * CELL
    return px, py, top_r, left_c

def any_move_possible(board, tray_pieces):
    for p in tray_pieces:
        if p is None:  # already used
            continue
        if board.any_placement_possible(p):
            return True
    return False

# --------------------------
# Main Game
# --------------------------
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((WINDOW_W, WINDOW_H))
        pygame.display.set_caption("Block Blast")
        self.clock = pygame.time.Clock()

        self.font_title = pygame.font.SysFont("arialblack", 48)
        self.font_ui = pygame.font.SysFont("arial", 24)
        self.font_big = pygame.font.SysFont("arialblack", 36)

        self.state = STATE_MENU
        self.board = Board(GRID_SIZE, GRID_SIZE)
        self.tray = []
        self.score = 0
        self.highscore = load_highscore()

        self.drag_piece = None
        self.drag_index = -1  # which slot (0..2)
        self.pending_clear_points = 0
        self.just_cleared = False

        self.buttons = self.make_buttons()

    def make_buttons(self):
        # for menu & game over
        w = 260
        h = 56
        cx = WINDOW_W // 2
        buttons = {
            "menu_play": pygame.Rect(cx - w//2, GRID_TOP + 220, w, h),
            "menu_quit": pygame.Rect(cx - w//2, GRID_TOP + 290, w, h),
            "go_restart": pygame.Rect(cx - w//2, GRID_TOP + 220, w, h),
            "go_menu": pygame.Rect(cx - w//2, GRID_TOP + 290, w, h),
        }
        return buttons

    def reset_play(self):
        self.board = Board(GRID_SIZE, GRID_SIZE)
        self.tray = new_tray_set()
        # Lay pieces in tray slots
        for piece, rect in zip(self.tray, tray_layout_rects()):
            center_piece_in_rect(piece, rect)
        self.score = 0
        self.drag_piece = None
        self.drag_index = -1
        self.pending_clear_points = 0
        self.just_cleared = False

    # ------------- State Transitions -------------
    def goto_menu(self):
        self.state = STATE_MENU

    def start_game(self):
        self.reset_play()
        self.state = STATE_PLAY

    def end_game(self):
        if self.score > self.highscore:
            self.highscore = self.score
            save_highscore(self.highscore)
        self.state = STATE_GAMEOVER

    # ------------- Event Handling -------------
    def handle_events(self, dt):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                if self.score > self.highscore:
                    save_highscore(self.score)
                pygame.quit()
                sys.exit()

            if self.state == STATE_MENU:
                self.handle_menu_events(event)
            elif self.state == STATE_PLAY:
                self.handle_play_events(event)
            elif self.state == STATE_GAMEOVER:
                self.handle_gameover_events(event)

    def handle_menu_events(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.buttons["menu_play"].collidepoint(mx, my):
                self.start_game()
            elif self.buttons["menu_quit"].collidepoint(mx, my):
                pygame.quit()
                sys.exit()

    def handle_gameover_events(self, event):
        if event.type == pygame.KEYDOWN and event.key == pygame.K_r:
            self.start_game()
        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            if self.buttons["go_restart"].collidepoint(mx, my):
                self.start_game()
            elif self.buttons["go_menu"].collidepoint(mx, my):
                self.goto_menu()

    def handle_play_events(self, event):
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_r:
                self.start_game()

        if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
            mx, my = event.pos
            # start drag if clicked a tray piece
            if self.drag_piece is None:
                for i, piece in enumerate(self.tray):
                    if piece is None:
                        continue
                    if piece.start_drag(mx, my):
                        self.drag_piece = piece
                        self.drag_index = i
                        break

        elif event.type == pygame.MOUSEMOTION:
            if self.drag_piece:
                mx, my = event.pos
                self.drag_piece.drag(mx, my)

        elif event.type == pygame.MOUSEBUTTONUP and event.button == 1:
            if self.drag_piece:
                mx, my = event.pos
                # Try place on grid
                px, py, top_r, left_c = snapped_grid_origin_for_piece(self.drag_piece, mx, my)
                placed = False
                if px is not None:
                    if self.board.can_place(self.drag_piece, top_r, left_c):
                        self.board.place(self.drag_piece, top_r, left_c)
                        placed = True

                if placed:
                    # consume piece from tray
                    self.tray[self.drag_index] = None
                    self.drag_piece.stop_drag()
                    self.drag_piece = None
                    self.drag_index = -1

                    # line clears
                    rows, cols = self.board.find_full_lines()
                    n_lines = len(rows) + len(cols)
                    if n_lines > 0:
                        # Start flash and schedule points after flash ends (we still add score immediately for simplicity)
                        self.board.clear_lines(rows, cols)
                        base = 100 * n_lines
                        combo = 50 * max(0, (n_lines - 1))
                        gain = base + combo
                        self.score += gain
                        self.just_cleared = True
                    else:
                        self.just_cleared = False

                    # Refill tray when all three used
                    if all(p is None for p in self.tray):
                        self.tray = new_tray_set()
                        for piece, rect in zip(self.tray, tray_layout_rects()):
                            center_piece_in_rect(piece, rect)

                    # After placement, if no move possible -> game over
                    if not any_move_possible(self.board, self.tray):
                        self.end_game()
                else:
                    # snap back to tray slot
                    if self.drag_index != -1:
                        # send back to its slot rect
                        rects = tray_layout_rects()
                        center_piece_in_rect(self.drag_piece, rects[self.drag_index])
                    self.drag_piece.stop_drag()
                    self.drag_piece = None
                    self.drag_index = -1

    # ------------- Update -------------
    def update(self, dt):
        if self.state == STATE_PLAY:
            self.board.commit_clears_if_due(dt)

    # ------------- Draw -------------
    def draw_button(self, rect, label):
        pygame.draw.rect(self.screen, (60, 70, 85), rect, border_radius=10)
        pygame.draw.rect(self.screen, (90, 100, 120), rect, 2, border_radius=10)
        draw_text(self.screen, label, rect.centerx, rect.centery, self.font_ui, center=True)

    def draw_hud(self):
        draw_text(self.screen, f"Score: {self.score}", 20, 20, self.font_ui)
        draw_text(self.screen, f"Best: {self.highscore}", WINDOW_W - 20, 20, self.font_ui, center=False)
        # Title small
        draw_text(self.screen, "BLOCK BLAST", WINDOW_W // 2, 70, self.font_big, center=True)

    def draw_tray(self):
        # tray background
        y = GRID_TOP + GRID_H + 8
        h = WINDOW_H - y - 8
        pygame.draw.rect(self.screen, (36, 42, 52), (12, y, WINDOW_W-24, h), border_radius=14)
        pygame.draw.rect(self.screen, (70, 77, 92), (12, y, WINDOW_W-24, h), 2, border_radius=14)

        # slots
        for rect in tray_layout_rects():
            pygame.draw.rect(self.screen, (46, 52, 64), rect, border_radius=12)
            pygame.draw.rect(self.screen, (80, 88, 104), rect, 2, border_radius=12)

        # pieces
        for i, piece in enumerate(self.tray):
            if piece is None:
                continue
            # if dragging this one, skip (draw on top later)
            if piece is self.drag_piece:
                continue
            piece.draw(self.screen)

        # draw currently dragged on top
        if self.drag_piece:
            self.drag_piece.draw(self.screen)
            # draw ghost preview if inside grid
            mx, my = pygame.mouse.get_pos()
            px, py, top_r, left_c = snapped_grid_origin_for_piece(self.drag_piece, mx, my)
            if px is not None:
                valid = self.board.can_place(self.drag_piece, top_r, left_c)
                self.drag_piece.draw_ghost_on_grid(self.screen, (px, py), CELL, valid)

    def draw_menu(self):
        draw_text(self.screen, "BLOCK BLAST", WINDOW_W // 2, GRID_TOP + 90, self.font_title, center=True)
        draw_text(self.screen, "Drag pieces onto the 8×8 grid.\nFill lines to clear.\nNo rotations.",
                  WINDOW_W // 2, GRID_TOP + 150, self.font_ui, center=True)
        self.draw_button(self.buttons["menu_play"], "Play")
        self.draw_button(self.buttons["menu_quit"], "Quit")

    def draw_gameover(self):
        # dim
        dim = pygame.Surface((WINDOW_W, WINDOW_H))
        dim.set_alpha(160)
        dim.fill((0, 0, 0))
        self.screen.blit(dim, (0, 0))

        # modal
        mw, mh = 360, 260
        rect = pygame.Rect((WINDOW_W - mw)//2, (WINDOW_H - mh)//2 - 40, mw, mh)
        pygame.draw.rect(self.screen, (38, 46, 58), rect, border_radius=16)
        pygame.draw.rect(self.screen, (90, 100, 120), rect, 2, border_radius=16)

        draw_text(self.screen, "Game Over", rect.centerx, rect.top + 26, self.font_big, center=True)
        draw_text(self.screen, f"Final Score: {self.score}", rect.centerx, rect.top + 80, self.font_ui, center=True)
        draw_text(self.screen, f"Best Score:  {self.highscore}", rect.centerx, rect.top + 110, self.font_ui, center=True)
        draw_text(self.screen, "Press R to Restart", rect.centerx, rect.top + 140, self.font_ui, center=True)

        self.draw_button(self.buttons["go_restart"], "Restart")
        self.draw_button(self.buttons["go_menu"], "Main Menu")

    def render(self):
        self.screen.fill(BG_COLOR)
        if self.state == STATE_MENU:
            self.draw_menu()
        elif self.state == STATE_PLAY:
            self.draw_hud()
            self.board.draw(self.screen)
            self.draw_tray()
        elif self.state == STATE_GAMEOVER:
            self.draw_hud()
            self.board.draw(self.screen)
            self.draw_tray()
            self.draw_gameover()
        pygame.display.flip()

    # ------------- Loop -------------
    def run(self):
        while True:
            dt = self.clock.tick(FPS)
            self.handle_events(dt)
            self.update(dt)
            self.render()

def main():
    Game().run()

if __name__ == "__main__":
    main()
