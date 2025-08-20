import pygame
import random
import sys
import time
import os

# Constants
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 600
GRID_SIZE = 25
PLAYFIELD_WIDTH = 10
PLAYFIELD_HEIGHT = 20
BUFFER_ROWS = 4
TOTAL_HEIGHT = PLAYFIELD_HEIGHT + BUFFER_ROWS

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
DARK_GRAY = (64, 64, 64)
CYAN = (0, 255, 255)    # I
YELLOW = (255, 255, 0)  # O
PURPLE = (128, 0, 128)  # T
ORANGE = (255, 165, 0)  # L
BLUE = (0, 0, 255)      # J
GREEN = (0, 255, 0)     # S
RED = (255, 0, 0)       # Z

TETRIMINO_COLORS = {
    'I': CYAN,
    'O': YELLOW,
    'T': PURPLE,
    'L': ORANGE,
    'J': BLUE,
    'S': GREEN,
    'Z': RED
}

# Tetrimino shapes (0: spawn state)
TETRIMINO_SHAPES = {
    'I': [
        [[0, 0, 0, 0],
         [1, 1, 1, 1],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 1, 0]],
        [[0, 0, 0, 0],
         [0, 0, 0, 0],
         [1, 1, 1, 1],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0]]
    ],
    'O': [
        [[0, 1, 1, 0],
         [0, 1, 1, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]]
    ] * 4,  # O doesn't rotate
    'T': [
        [[0, 1, 0, 0],
         [1, 1, 1, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 1, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 0, 0],
         [1, 1, 1, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [1, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]]
    ],
    'L': [
        [[0, 0, 1, 0],
         [1, 1, 1, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 1, 0],
         [0, 0, 0, 0]],
        [[0, 0, 0, 0],
         [1, 1, 1, 0],
         [1, 0, 0, 0],
         [0, 0, 0, 0]],
        [[1, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]]
    ],
    'J': [
        [[1, 0, 0, 0],
         [1, 1, 1, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 1, 1, 0],
         [0, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 0, 0],
         [1, 1, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 0, 0],
         [1, 1, 0, 0],
         [0, 0, 0, 0]]
    ],
    'S': [
        [[0, 1, 1, 0],
         [1, 1, 0, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [0, 1, 1, 0],
         [0, 0, 1, 0],
         [0, 0, 0, 0]],
        [[0, 0, 0, 0],
         [0, 1, 1, 0],
         [1, 1, 0, 0],
         [0, 0, 0, 0]],
        [[1, 0, 0, 0],
         [1, 1, 0, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]]
    ],
    'Z': [
        [[1, 1, 0, 0],
         [0, 1, 1, 0],
         [0, 0, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 1, 0],
         [0, 1, 1, 0],
         [0, 1, 0, 0],
         [0, 0, 0, 0]],
        [[0, 0, 0, 0],
         [1, 1, 0, 0],
         [0, 1, 1, 0],
         [0, 0, 0, 0]],
        [[0, 1, 0, 0],
         [1, 1, 0, 0],
         [1, 0, 0, 0],
         [0, 0, 0, 0]]
    ]
}

# SRS Wall Kick Data (for non-I pieces)
WALL_KICKS = {
    (0, 1): [(-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (1, 0): [(1, 0), (1, -1), (0, 2), (1, 2)],
    (1, 2): [(1, 0), (1, -1), (0, 2), (1, 2)],
    (2, 1): [(-1, 0), (-1, 1), (0, -2), (-1, -2)],
    (2, 3): [(1, 0), (1, 1), (0, -2), (1, -2)],
    (3, 2): [(-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (3, 0): [(-1, 0), (-1, -1), (0, 2), (-1, 2)],
    (0, 3): [(1, 0), (1, 1), (0, -2), (1, -2)]
}

# SRS for I piece
WALL_KICKS_I = {
    (0, 1): [(-2, 0), (1, 0), (-2, -1), (1, 2)],
    (1, 0): [(2, 0), (-1, 0), (2, 1), (-1, -2)],
    (1, 2): [(-1, 0), (2, 0), (-1, 2), (2, -1)],
    (2, 1): [(1, 0), (-2, 0), (1, -2), (-2, 1)],
    (2, 3): [(2, 0), (-1, 0), (2, 1), (-1, -2)],
    (3, 2): [(-2, 0), (1, 0), (-2, -1), (1, 2)],
    (3, 0): [(1, 0), (-2, 0), (1, -2), (-2, 1)],
    (0, 3): [(-1, 0), (2, 0), (-1, 2), (2, -1)]
}

class Tetrimino:
    def __init__(self, type):
        self.type = type
        self.color = TETRIMINO_COLORS[type]
        self.rotation = 0
        self.shape = TETRIMINO_SHAPES[type][self.rotation]
        self.x = PLAYFIELD_WIDTH // 2 - len(self.shape[0]) // 2
        self.y = 0  # Spawn at top

    def rotate(self, direction=1):
        old_rotation = self.rotation
        self.rotation = (self.rotation + direction) % len(TETRIMINO_SHAPES[self.type])
        self.shape = TETRIMINO_SHAPES[self.type][self.rotation]
        return old_rotation

class Board:
    def __init__(self):
        self.grid = [[None for _ in range(PLAYFIELD_WIDTH)] for _ in range(TOTAL_HEIGHT)]
        self.lock_delay = 0.5
        self.lock_timer = 0
        self.move_reset_count = 0
        self.max_resets = 15  # For infinity rule, limit resets

    def add_piece(self, piece):
        for dy in range(len(piece.shape)):
            for dx in range(len(piece.shape[dy])):
                if piece.shape[dy][dx]:
                    self.grid[piece.y + dy][piece.x + dx] = piece.color

    def check_collision(self, piece, dx=0, dy=0):
        for y in range(len(piece.shape)):
            for x in range(len(piece.shape[y])):
                if piece.shape[y][x]:
                    nx, ny = piece.x + x + dx, piece.y + y + dy
                    if nx < 0 or nx >= PLAYFIELD_WIDTH or ny >= TOTAL_HEIGHT or (ny >= 0 and self.grid[ny][nx]):
                        return True
        return False

    def clear_lines(self):
        lines_cleared = 0
        for y in range(TOTAL_HEIGHT - 1, -1, -1):
            if all(self.grid[y]):
                del self.grid[y]
                self.grid.insert(0, [None] * PLAYFIELD_WIDTH)
                lines_cleared += 1
        return lines_cleared

    def is_game_over(self, piece):
        return self.check_collision(piece, 0, 0)

class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris Classic")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("Arial", 24)
        self.small_font = pygame.font.SysFont("Arial", 18)

        self.board = Board()
        self.bag = []
        self.next_pieces = [self.get_next_piece() for _ in range(5)]
        self.current_piece = self.get_next_piece()
        self.hold_piece = None
        self.can_hold = True
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.last_clear_was_tetris = False
        self.drop_speed = self.get_drop_speed()
        self.drop_timer = 0
        self.soft_drop = False
        self.game_state = "menu"  # menu, playing, paused, game_over
        self.high_scores = self.load_high_scores()
        self.paused = False
        self.last_move_time = time.time()

        # Audio placeholders (add your own sound files)
        # self.sfx_move = pygame.mixer.Sound('move.wav')
        # etc.

    def get_drop_speed(self):
        return max(0.05, 1.0 - (self.level - 1) * 0.05)  # Decrease time per level

    def get_next_piece(self):
        if not self.bag:
            self.bag = list('IOTLJSZ')
            random.shuffle(self.bag)
        type = self.bag.pop(0)
        piece = Tetrimino(type)
        piece.y = 0  # Adjust for buffer
        return piece

    def hold(self):
        if not self.can_hold:
            return
        if self.hold_piece:
            self.current_piece, self.hold_piece = self.hold_piece, self.current_piece
            self.current_piece.x = PLAYFIELD_WIDTH // 2 - len(self.current_piece.shape[0]) // 2
            self.current_piece.y = 0
            self.current_piece.rotation = 0
            self.current_piece.shape = TETRIMINO_SHAPES[self.current_piece.type][0]
        else:
            self.hold_piece = self.current_piece
            self.current_piece = self.next_pieces.pop(0)
            self.next_pieces.append(self.get_next_piece())
        self.can_hold = False
        self.board.lock_timer = 0
        self.board.move_reset_count = 0

    def move(self, dx):
        if not self.board.check_collision(self.current_piece, dx, 0):
            self.current_piece.x += dx
            self.reset_lock_timer(True)
            return True
        return False

    def drop(self, soft=False):
        if not self.board.check_collision(self.current_piece, 0, 1):
            self.current_piece.y += 1
            if soft:
                self.score += 1
            self.reset_lock_timer(soft)
            return True
        return False

    def hard_drop(self):
        rows_dropped = 0
        while self.drop(False):
            rows_dropped += 1
        self.score += 2 * rows_dropped
        self.lock_piece()

    def rotate(self, direction=1):
        old_rotation = self.current_piece.rotate(direction)
        if self.board.check_collision(self.current_piece, 0, 0):
            kicks = WALL_KICKS_I if self.current_piece.type == 'I' else WALL_KICKS
            key = (old_rotation, self.current_piece.rotation)
            for dx, dy in kicks.get(key, []):
                if not self.board.check_collision(self.current_piece, dx, dy):
                    self.current_piece.x += dx
                    self.current_piece.y += dy
                    self.reset_lock_timer(True)
                    return True
            # Revert if no kick works
            self.current_piece.rotate(-direction)
            return False
        self.reset_lock_timer(True)
        return True

    def reset_lock_timer(self, moved):
        if moved:
            self.board.lock_timer = time.time() + self.board.lock_delay
            self.board.move_reset_count += 1
            if self.board.move_reset_count > self.board.max_resets:
                self.lock_piece()

    def lock_piece(self):
        self.board.add_piece(self.current_piece)
        lines = self.board.clear_lines()
        self.lines_cleared += lines
        self.calculate_score(lines)
        if self.lines_cleared // 10 >= self.level:
            self.level += 1
            self.drop_speed = self.get_drop_speed()
        self.current_piece = self.next_pieces.pop(0)
        self.next_pieces.append(self.get_next_piece())
        self.can_hold = True
        self.board.lock_timer = 0
        self.board.move_reset_count = 0
        if self.board.is_game_over(self.current_piece):
            self.game_state = "game_over"
            self.update_high_scores()

    def calculate_score(self, lines):
        if lines == 0:
            self.last_clear_was_tetris = False
            return
        base = [0, 100, 300, 500, 800][lines]
        if lines == 4:
            if self.last_clear_was_tetris:
                base = 1200
            self.last_clear_was_tetris = True
        else:
            self.last_clear_was_tetris = False
        self.score += base * self.level

    def update(self, dt):
        if self.game_state != "playing":
            return

        self.drop_timer += dt
        if self.soft_drop:
            if self.drop_timer >= 0.05:  # Faster for soft drop
                if not self.drop(True):
                    self.board.lock_timer = time.time() + self.board.lock_delay if self.board.lock_timer == 0 else self.board.lock_timer
                self.drop_timer = 0
        else:
            if self.drop_timer >= self.drop_speed:
                if not self.drop():
                    self.board.lock_timer = time.time() + self.board.lock_delay if self.board.lock_timer == 0 else self.board.lock_timer
                self.drop_timer = 0

        if self.board.lock_timer and time.time() > self.board.lock_timer:
            self.lock_piece()

    def draw_grid(self, surface, x, y, width, height, buffer=False):
        for dy in range(height if buffer else PLAYFIELD_HEIGHT):
            for dx in range(width):
                color = self.board.grid[dy + (BUFFER_ROWS if not buffer else 0)][dx]
                if color:
                    pygame.draw.rect(surface, color, (x + dx * GRID_SIZE, y + dy * GRID_SIZE, GRID_SIZE, GRID_SIZE))
                pygame.draw.rect(surface, GRAY, (x + dx * GRID_SIZE, y + dy * GRID_SIZE, GRID_SIZE, GRID_SIZE), 1)

    def draw_piece(self, surface, piece, ox, oy, ghost=False):
        color = GRAY if ghost else piece.color
        alpha = 128 if ghost else 255
        temp_surface = pygame.Surface((GRID_SIZE * 4, GRID_SIZE * 4), pygame.SRCALPHA)
        temp_surface.set_alpha(alpha)
        for dy in range(len(piece.shape)):
            for dx in range(len(piece.shape[dy])):
                if piece.shape[dy][dx]:
                    pygame.draw.rect(temp_surface, color, (dx * GRID_SIZE, dy * GRID_SIZE, GRID_SIZE, GRID_SIZE))
        surface.blit(temp_surface, (ox + piece.x * GRID_SIZE, oy + (piece.y - BUFFER_ROWS) * GRID_SIZE))

    def draw_ghost(self, surface, ox, oy):
        ghost = Tetrimino(self.current_piece.type)
        ghost.rotation = self.current_piece.rotation
        ghost.shape = self.current_piece.shape
        ghost.x = self.current_piece.x
        ghost.y = self.current_piece.y
        while not self.board.check_collision(ghost, 0, 1):
            ghost.y += 1
        self.draw_piece(surface, ghost, ox, oy, True)

    def draw_hold(self, surface, x, y):
        if self.hold_piece:
            self.draw_mini_piece(surface, self.hold_piece, x, y)

    def draw_next(self, surface, x, y):
        for i, piece in enumerate(self.next_pieces):
            self.draw_mini_piece(surface, piece, x, y + i * 100)

    def draw_mini_piece(self, surface, piece, x, y):
        scale = 0.75
        for dy in range(len(piece.shape)):
            for dx in range(len(piece.shape[dy])):
                if piece.shape[dy][dx]:
                    pygame.draw.rect(surface, piece.color, (x + dx * GRID_SIZE * scale, y + dy * GRID_SIZE * scale, GRID_SIZE * scale, GRID_SIZE * scale))

    def draw_hud(self):
        # Left: Hold
        hold_x = 50
        hold_y = 100
        pygame.draw.rect(self.screen, DARK_GRAY, (hold_x - 10, hold_y - 30, 120, 120))
        self.screen.blit(self.small_font.render("HOLD", True, WHITE), (hold_x, hold_y - 25))
        self.draw_hold(self.screen, hold_x, hold_y)

        # Center: Playfield
        play_x = 200
        play_y = 50
        self.draw_grid(self.screen, play_x, play_y, PLAYFIELD_WIDTH, PLAYFIELD_HEIGHT)
        self.draw_ghost(self.screen, play_x, play_y)
        self.draw_piece(self.screen, self.current_piece, play_x, play_y)

        # Right: Next, Score, etc.
        next_x = 500
        next_y = 100
        pygame.draw.rect(self.screen, DARK_GRAY, (next_x - 10, next_y - 30, 120, 420))
        self.screen.blit(self.small_font.render("NEXT", True, WHITE), (next_x, next_y - 25))
        self.draw_next(self.screen, next_x, next_y)

        info_y = next_y + 400
        self.screen.blit(self.font.render(f"SCORE: {self.score}", True, WHITE), (next_x, info_y))
        self.screen.blit(self.font.render(f"LEVEL: {self.level}", True, WHITE), (next_x, info_y + 30))
        self.screen.blit(self.font.render(f"LINES: {self.lines_cleared}", True, WHITE), (next_x, info_y + 60))

    def draw_menu(self):
        self.screen.fill(BLACK)
        title = self.font.render("Tetris Classic", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        buttons = ["START GAME", "HIGH SCORES", "SETTINGS", "QUIT"]
        for i, text in enumerate(buttons):
            btn = self.font.render(text, True, WHITE)
            self.screen.blit(btn, (SCREEN_WIDTH // 2 - btn.get_width() // 2, 200 + i * 50))

    def draw_paused(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        paused = self.font.render("PAUSED", True, WHITE)
        self.screen.blit(paused, (SCREEN_WIDTH // 2 - paused.get_width() // 2, 200))

        buttons = ["RESUME", "RESTART", "QUIT TO MENU"]
        for i, text in enumerate(buttons):
            btn = self.font.render(text, True, WHITE)
            self.screen.blit(btn, (SCREEN_WIDTH // 2 - btn.get_width() // 2, 300 + i * 50))

    def draw_game_over(self):
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT))
        overlay.set_alpha(128)
        overlay.fill(BLACK)
        self.screen.blit(overlay, (0, 0))
        game_over = self.font.render("GAME OVER", True, WHITE)
        self.screen.blit(game_over, (SCREEN_WIDTH // 2 - game_over.get_width() // 2, 100))

        self.screen.blit(self.font.render(f"SCORE: {self.score}", True, WHITE), (SCREEN_WIDTH // 2 - 100, 200))
        self.screen.blit(self.font.render(f"LEVEL: {self.level}", True, WHITE), (SCREEN_WIDTH // 2 - 100, 230))
        self.screen.blit(self.font.render(f"LINES: {self.lines_cleared}", True, WHITE), (SCREEN_WIDTH // 2 - 100, 260))

        buttons = ["PLAY AGAIN", "MAIN MENU"]
        for i, text in enumerate(buttons):
            btn = self.font.render(text, True, WHITE)
            self.screen.blit(btn, (SCREEN_WIDTH // 2 - btn.get_width() // 2, 350 + i * 50))

        # High score entry if applicable
        if any(self.score > s[1] for s in self.high_scores):
            # Implement text input here, but for simplicity, assume "AAA"
            pass

    def draw_high_scores(self):
        self.screen.fill(BLACK)
        title = self.font.render("HIGH SCORES", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        for i, (name, score) in enumerate(self.high_scores):
            text = self.font.render(f"{i+1}. {name} - {score}", True, WHITE)
            self.screen.blit(text, (SCREEN_WIDTH // 2 - text.get_width() // 2, 200 + i * 30))

        back = self.font.render("BACK", True, WHITE)
        self.screen.blit(back, (SCREEN_WIDTH // 2 - back.get_width() // 2, 500))

    def draw_settings(self):
        self.screen.fill(BLACK)
        title = self.font.render("SETTINGS", True, WHITE)
        self.screen.blit(title, (SCREEN_WIDTH // 2 - title.get_width() // 2, 100))

        # Placeholder for controls, audio
        back = self.font.render("BACK", True, WHITE)
        self.screen.blit(back, (SCREEN_WIDTH // 2 - back.get_width() // 2, 500))

    def load_high_scores(self):
        if os.path.exists("high_scores.txt"):
            with open("high_scores.txt", "r") as f:
                lines = f.readlines()
                scores = []
                for line in lines:
                    parts = line.strip().split(":")
                    if len(parts) == 2:
                        name, score_str = parts
                        try:
                            score = int(score_str)
                            scores.append((name, score))
                        except ValueError:
                            pass  # Skip invalid lines
                return scores
        return [("AAA", 0)] * 5

    def save_high_scores(self):
        with open("high_scores.txt", "w") as f:
            for name, score in self.high_scores:
                f.write(f"{name}:{score}\n")

    def update_high_scores(self):
        self.high_scores.append(("AAA", self.score))  # Placeholder name
        self.high_scores = sorted(self.high_scores, key=lambda x: x[1], reverse=True)[:5]
        self.save_high_scores()

    def handle_menu_click(self, pos):
        x, y = pos
        if 200 < y < 250 and SCREEN_WIDTH // 2 - 100 < x < SCREEN_WIDTH // 2 + 100:
            self.start_game()
        elif 250 < y < 300:
            self.game_state = "high_scores"
        elif 300 < y < 350:
            self.game_state = "settings"
        elif 350 < y < 400:
            sys.exit()

    def handle_paused_click(self, pos):
        x, y = pos
        if 300 < y < 350:
            self.game_state = "playing"
        elif 350 < y < 400:
            self.__init__()
            self.game_state = "playing"
        elif 400 < y < 450:
            self.game_state = "menu"

    def handle_game_over_click(self, pos):
        x, y = pos
        if 350 < y < 400:
            self.__init__()
            self.game_state = "playing"
        elif 400 < y < 450:
            self.game_state = "menu"

    def handle_high_scores_click(self, pos):
        if 500 < pos[1] < 550:
            self.game_state = "menu"

    def handle_settings_click(self, pos):
        if 500 < pos[1] < 550:
            self.game_state = "menu"

    def run(self):
        while True:
            dt = self.clock.tick(60) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    if self.game_state == "playing":
                        if event.key == pygame.K_LEFT:
                            self.move(-1)
                        elif event.key == pygame.K_RIGHT:
                            self.move(1)
                        elif event.key == pygame.K_DOWN:
                            self.soft_drop = True
                        elif event.key == pygame.K_UP:
                            self.rotate(1)
                        elif event.key == pygame.K_x:
                            self.rotate(-1)
                        elif event.key == pygame.K_SPACE:
                            self.hard_drop()
                        elif event.key == pygame.K_c:
                            self.hold()
                        elif event.key == pygame.K_ESCAPE:
                            self.game_state = "paused"
                if event.type == pygame.KEYUP:
                    if event.key == pygame.K_DOWN:
                        self.soft_drop = False
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if self.game_state == "menu":
                        self.handle_menu_click(event.pos)
                    elif self.game_state == "paused":
                        self.handle_paused_click(event.pos)
                    elif self.game_state == "game_over":
                        self.handle_game_over_click(event.pos)
                    elif self.game_state == "high_scores":
                        self.handle_high_scores_click(event.pos)
                    elif self.game_state == "settings":
                        self.handle_settings_click(event.pos)

            self.update(dt)

            self.screen.fill(BLACK)
            if self.game_state == "playing":
                self.draw_hud()
            elif self.game_state == "menu":
                self.draw_menu()
            elif self.game_state == "paused":
                self.draw_hud()
                self.draw_paused()
            elif self.game_state == "game_over":
                self.draw_hud()
                self.draw_game_over()
            elif self.game_state == "high_scores":
                self.draw_high_scores()
            elif self.game_state == "settings":
                self.draw_settings()

            pygame.display.flip()

    def start_game(self):
        self.__init__()
        self.game_state = "playing"

def main():
    game = Game()
    game.run()

if __name__ == "__main__":
    main()