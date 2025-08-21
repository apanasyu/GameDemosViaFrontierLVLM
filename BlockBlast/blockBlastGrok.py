import pygame
import random
import os
import sys

# Constants
GRID_SIZE = 8
CELL_SIZE = 50
GRID_WIDTH = GRID_SIZE * CELL_SIZE
GRID_HEIGHT = GRID_SIZE * CELL_SIZE
TRAY_HEIGHT = 150
WIDTH = GRID_WIDTH
HEIGHT = GRID_HEIGHT + TRAY_HEIGHT + 100  # Extra space for HUD
FPS = 60

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRAY = (128, 128, 128)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)

BLOCK_COLORS = [RED, GREEN, BLUE, YELLOW, CYAN, MAGENTA, ORANGE]

# Block shapes (list of relative positions)
SHAPES = [
    # Single
    [(0, 0)],
    # 2 horizontal
    [(0, 0), (1, 0)],
    # 2 vertical
    [(0, 0), (0, 1)],
    # 3 horizontal
    [(0, 0), (1, 0), (2, 0)],
    # 3 vertical
    [(0, 0), (0, 1), (0, 2)],
    # Square 2x2
    [(0, 0), (1, 0), (0, 1), (1, 1)],
    # L shapes
    [(0, 0), (0, 1), (0, 2), (1, 2)],
    [(0, 0), (1, 0), (2, 0), (2, 1)],
    [(0, 0), (0, 1), (1, 0), (2, 0)],
    [(0, 0), (1, 0), (1, 1), (1, 2)],
    # T shape
    [(0, 0), (1, 0), (2, 0), (1, 1)],
    # Plus
    [(1, 0), (0, 1), (1, 1), (2, 1), (1, 2)],
    # More complex if needed, but keep simple
]

HIGH_SCORE_FILE = "high_score.txt"

def load_high_score():
    if os.path.exists(HIGH_SCORE_FILE):
        with open(HIGH_SCORE_FILE, "r") as f:
            return int(f.read().strip())
    return 0

def save_high_score(score):
    with open(HIGH_SCORE_FILE, "w") as f:
        f.write(str(score))

class Block:
    def __init__(self, shape, color):
        self.shape = shape
        self.color = color
        self.x = 0
        self.y = 0

    def draw(self, screen, offset_x=0, offset_y=0):
        for dx, dy in self.shape:
            rect = pygame.Rect(
                offset_x + self.x + dx * CELL_SIZE,
                offset_y + self.y + dy * CELL_SIZE,
                CELL_SIZE,
                CELL_SIZE
            )
            pygame.draw.rect(screen, self.color, rect)
            pygame.draw.rect(screen, BLACK, rect, 1)

class Game:
    def __init__(self):
        self.grid = [[None for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.score = 0
        self.high_score = load_high_score()
        self.blocks = self.generate_blocks()
        self.dragging = None
        self.drag_offset_x = 0
        self.drag_offset_y = 0
        self.game_over = False

    def generate_blocks(self):
        return [Block(random.choice(SHAPES), random.choice(BLOCK_COLORS)) for _ in range(3)]

    def draw_grid(self, screen):
        for i in range(GRID_SIZE):
            for j in range(GRID_SIZE):
                rect = pygame.Rect(j * CELL_SIZE, i * CELL_SIZE, CELL_SIZE, CELL_SIZE)
                if self.grid[i][j]:
                    pygame.draw.rect(screen, self.grid[i][j], rect)
                pygame.draw.rect(screen, GRAY, rect, 1)

    def draw_tray(self, screen):
        tray_y = GRID_HEIGHT + 50
        for idx, block in enumerate(self.blocks):
            block.x = idx * (GRID_WIDTH // 3) + (GRID_WIDTH // 6) - (len(block.shape) * CELL_SIZE // 2)
            block.y = 0
            block.draw(screen, 0, tray_y)

    def draw_hud(self, screen):
        font = pygame.font.SysFont(None, 36)
        score_text = font.render(f"Score: {self.score}", True, WHITE)
        high_text = font.render(f"High: {self.high_score}", True, WHITE)
        screen.blit(score_text, (10, GRID_HEIGHT + 10))
        screen.blit(high_text, (WIDTH - high_text.get_width() - 10, GRID_HEIGHT + 10))

    def draw_game_over(self, screen):
        font = pygame.font.SysFont(None, 48)
        over_text = font.render("Game Over", True, RED)
        final_text = font.render(f"Final Score: {self.score}", True, WHITE)
        best_text = font.render(f"Best Score: {self.high_score}", True, WHITE)
        restart_text = font.render("Press R to Restart", True, GREEN)
        menu_text = font.render("Press M for Main Menu", True, GREEN)

        screen.blit(over_text, (WIDTH // 2 - over_text.get_width() // 2, HEIGHT // 2 - 150))
        screen.blit(final_text, (WIDTH // 2 - final_text.get_width() // 2, HEIGHT // 2 - 50))
        screen.blit(best_text, (WIDTH // 2 - best_text.get_width() // 2, HEIGHT // 2))
        screen.blit(restart_text, (WIDTH // 2 - restart_text.get_width() // 2, HEIGHT // 2 + 100))
        screen.blit(menu_text, (WIDTH // 2 - menu_text.get_width() // 2, HEIGHT // 2 + 150))

    def can_place(self, block, grid_x, grid_y):
        for dx, dy in block.shape:
            x = grid_x + dx
            y = grid_y + dy
            if x < 0 or x >= GRID_SIZE or y < 0 or y >= GRID_SIZE or self.grid[y][x]:
                return False
        return True

    def place_block(self, block, grid_x, grid_y):
        for dx, dy in block.shape:
            x = grid_x + dx
            y = grid_y + dy
            self.grid[y][x] = block.color
        lines_cleared = self.clear_lines()
        self.score += lines_cleared * 10
        if lines_cleared > 1:
            self.score += (lines_cleared - 1) * 5  # Combo bonus
        if self.score > self.high_score:
            self.high_score = self.score
            save_high_score(self.high_score)

    def clear_lines(self):
        lines_cleared = 0
        # Clear rows
        for i in range(GRID_SIZE):
            if all(self.grid[i][j] for j in range(GRID_SIZE)):
                for j in range(GRID_SIZE):
                    self.grid[i][j] = None
                lines_cleared += 1
        # Clear columns
        for j in range(GRID_SIZE):
            if all(self.grid[i][j] for i in range(GRID_SIZE)):
                for i in range(GRID_SIZE):
                    self.grid[i][j] = None
                lines_cleared += 1
        return lines_cleared

    def check_game_over(self):
        for block in self.blocks:
            for i in range(GRID_SIZE):
                for j in range(GRID_SIZE):
                    if self.can_place(block, j, i):
                        return False
        return True

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Block Blast")
    clock = pygame.time.Clock()

    game = Game()

    while True:
        screen.fill(BLACK)

        if game.game_over:
            game.draw_grid(screen)
            game.draw_tray(screen)
            game.draw_hud(screen)
            game.draw_game_over(screen)
        else:
            game.draw_grid(screen)
            game.draw_tray(screen)
            game.draw_hud(screen)

            if game.dragging:
                mouse_x, mouse_y = pygame.mouse.get_pos()
                game.dragging.x = mouse_x - game.drag_offset_x
                game.dragging.y = mouse_y - game.drag_offset_y
                game.dragging.draw(screen)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if game.game_over:
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_r:
                        game = Game()
                    elif event.key == pygame.K_m:
                        # For now, just restart as main menu not implemented
                        game = Game()
            else:
                if event.type == pygame.MOUSEBUTTONDOWN:
                    mouse_x, mouse_y = event.pos
                    tray_y = GRID_HEIGHT + 50
                    for idx, block in enumerate(game.blocks):
                        block_rect = pygame.Rect(
                            idx * (GRID_WIDTH // 3),
                            tray_y,
                            GRID_WIDTH // 3,
                            TRAY_HEIGHT - 50
                        )
                        # Check if click inside block's bounding box
                        min_x = min(dx for dx, dy in block.shape) * CELL_SIZE + block.x
                        max_x = max(dx for dx, dy in block.shape) * CELL_SIZE + block.x
                        min_y = min(dy for dx, dy in block.shape) * CELL_SIZE + block.y + tray_y
                        max_y = max(dy for dx, dy in block.shape) * CELL_SIZE + block.y + tray_y
                        if min_x <= mouse_x <= max_x and min_y <= mouse_y <= max_y:
                            game.dragging = block
                            game.drag_offset_x = mouse_x - block.x
                            game.drag_offset_y = mouse_y - (block.y + tray_y)
                            game.blocks.remove(block)
                            break
                elif event.type == pygame.MOUSEBUTTONUP and game.dragging:
                    mouse_x, mouse_y = event.pos
                    grid_x = mouse_x // CELL_SIZE
                    grid_y = mouse_y // CELL_SIZE
                    if game.can_place(game.dragging, grid_x, grid_y):
                        game.place_block(game.dragging, grid_x, grid_y)
                        if not game.blocks:
                            game.blocks = game.generate_blocks()
                        if game.check_game_over():
                            game.game_over = True
                    else:
                        # Return to tray
                        game.blocks.append(game.dragging)
                    game.dragging = None

        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()