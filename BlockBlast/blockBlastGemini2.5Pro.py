import pygame
import sys
import random
import os

# --- Constants ---
# Screen dimensions (portrait orientation)
SCREEN_WIDTH = 480
SCREEN_HEIGHT = 800

# Grid settings
GRID_SIZE = 8
CELL_SIZE = 50
GRID_WIDTH = GRID_SIZE * CELL_SIZE
GRID_HEIGHT = GRID_SIZE * CELL_SIZE

# Grid position (centered horizontally, placed vertically)
GRID_X = (SCREEN_WIDTH - GRID_WIDTH) // 2
GRID_Y = 150

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
GRAY = (40, 40, 40)
LIGHT_GRAY = (180, 180, 180)
GRID_COLOR = (60, 60, 60)
RED = (255, 50, 50)
GREEN = (50, 255, 50)

# Block colors - vibrant and distinct
BLOCK_COLORS = [
    (255, 105, 180),  # Hot Pink
    (135, 206, 235),  # Sky Blue
    (255, 215, 0),    # Gold
    (50, 205, 50),    # Lime Green
    (255, 165, 0),    # Orange
    (147, 112, 219),  # Medium Purple
]

# Block Shapes (relative coordinates from an anchor point)
# These shapes cannot be rotated
SHAPES = [
    # 1x1
    [[[0, 0]]],
    # 1x2 / 2x1
    [[[0, 0], [0, 1]]],
    [[[0, 0], [1, 0]]],
    # 1x3 / 3x1
    [[[0, 0], [0, 1], [0, 2]]],
    [[[0, 0], [1, 0], [2, 0]]],
    # 1x4 / 4x1
    [[[0, 0], [0, 1], [0, 2], [0, 3]]],
    [[[0, 0], [1, 0], [2, 0], [3, 0]]],
    # 2x2 Square
    [[[0, 0], [1, 0], [0, 1], [1, 1]]],
    # L-shapes
    [[[0, 0], [0, 1], [0, 2], [1, 2]]],
    [[[0, 0], [1, 0], [2, 0], [2, 1]]],
    [[[0, 0], [1, 0], [1, 1], [1, 2]]],
    [[[0, 1], [1, 1], [2, 1], [2, 0]]],
    # Plus Shape
    [[[1, 0], [0, 1], [1, 1], [2, 1], [1, 2]]],
]

# High score file
HIGH_SCORE_FILE = "highscore.txt"

# --- Game Classes ---

class Block:
    """Represents a single block piece with its shape, color, and position."""
    def __init__(self, shape, color_index):
        self.shape = shape
        self.color_index = color_index
        self.color = BLOCK_COLORS[color_index]
        self.screen_pos = [0, 0]

    def draw(self, screen, pos, cell_size, alpha=255):
        """Draws the block on the screen."""
        for r_off, c_off in self.shape:
            # Create a surface for transparency
            surface = pygame.Surface((cell_size, cell_size), pygame.SRCALPHA)
            surface.fill((*self.color, alpha))
            screen.blit(surface, (pos[0] + c_off * cell_size, pos[1] + r_off * cell_size))

class Game:
    """Manages the main game state and logic."""
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Block Blast")
        self.clock = pygame.time.Clock()
        self.font_large = pygame.font.Font(None, 64)
        self.font_medium = pygame.font.Font(None, 48)
        self.font_small = pygame.font.Font(None, 36)

        self.high_score = self.load_high_score()
        self.reset_game()

    def reset_game(self):
        """Initializes or resets the game state."""
        self.grid = [[0 for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]
        self.score = 0
        self.available_blocks = []
        self.generate_new_blocks()

        self.dragging_block = None
        self.dragging_offset = (0, 0)

        self.game_over = False

    def load_high_score(self):
        """Loads the high score from a file."""
        if os.path.exists(HIGH_SCORE_FILE):
            try:
                with open(HIGH_SCORE_FILE, 'r') as f:
                    return int(f.read())
            except ValueError:
                return 0
        return 0

    def save_high_score(self):
        """Saves the high score to a file."""
        with open(HIGH_SCORE_FILE, 'w') as f:
            f.write(str(self.high_score))

    def generate_new_blocks(self):
        """Generates a new set of three blocks for the player to choose from."""
        self.available_blocks = []
        for i in range(3):
            shape = random.choice(random.choice(SHAPES))
            color_index = random.randint(0, len(BLOCK_COLORS) - 1)
            block = Block(shape, color_index)
            # Position them in the bottom tray
            # *** THE FIX IS HERE: Use integer division // instead of float division / ***
            block.screen_pos = [SCREEN_WIDTH // 4 * (i + 1) - CELL_SIZE, GRID_Y + GRID_HEIGHT + 60]
            self.available_blocks.append(block)

    def run(self):
        """The main game loop."""
        running = True
        while running:

            if self.game_over:
                self.show_game_over_screen()
                # A new game starts after the game over screen
                self.reset_game()

            # Event Handling
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False

                if not self.game_over:
                    self.handle_mouse_events(event)

            # Drawing
            self.draw()
            pygame.display.flip()
            self.clock.tick(60)

        pygame.quit()
        sys.exit()

    def handle_mouse_events(self, event):
        mouse_pos = pygame.mouse.get_pos()

        if event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:  # Left click
                for i, block in enumerate(self.available_blocks):
                    # Check if click is on a block
                    block_rects = [pygame.Rect(block.screen_pos[0] + c_off * CELL_SIZE,
                                               block.screen_pos[1] + r_off * CELL_SIZE,
                                               CELL_SIZE, CELL_SIZE)
                                   for r_off, c_off in block.shape]

                    for rect in block_rects:
                        if rect.collidepoint(mouse_pos):
                            self.dragging_block = self.available_blocks.pop(i)
                            self.dragging_offset = (mouse_pos[0] - block.screen_pos[0],
                                                    mouse_pos[1] - block.screen_pos[1])
                            return # Exit after finding the first block

        elif event.type == pygame.MOUSEBUTTONUP:
            if self.dragging_block and event.button == 1:
                self.place_block() # No longer need to pass mouse_pos
                self.dragging_block = None

        elif event.type == pygame.MOUSEMOTION:
            if self.dragging_block:
                self.dragging_block.screen_pos = [mouse_pos[0] - self.dragging_offset[0],
                                                   mouse_pos[1] - self.dragging_offset[1]]

    def place_block(self):
        """Attempts to place the currently dragged block on the grid."""
        # Calculate grid position based on the block's anchor and mouse offset
        block_center_x = self.dragging_block.screen_pos[0] + self.dragging_offset[0]
        block_center_y = self.dragging_block.screen_pos[1] + self.dragging_offset[1]

        grid_col = (block_center_x - GRID_X) // CELL_SIZE
        grid_row = (block_center_y - GRID_Y) // CELL_SIZE

        if self.is_valid_placement(self.dragging_block, grid_row, grid_col):
            # Place the block
            for r_off, c_off in self.dragging_block.shape:
                self.grid[grid_row + r_off][grid_col + c_off] = self.dragging_block.color_index + 1

            # Score for placing block (e.g., 1 point per square)
            self.score += len(self.dragging_block.shape)

            # Clear lines and score
            self.clear_lines()

            # Replenish blocks if tray is empty
            if not self.available_blocks:
                self.generate_new_blocks()

            # Check for game over
            if self.check_game_over():
                self.game_over = True
                if self.score > self.high_score:
                    self.high_score = self.score
                    self.save_high_score()

    def is_valid_placement(self, block, grid_row, grid_col):
        """Checks if a block can be placed at a specific grid location."""
        for r_off, c_off in block.shape:
            r, c = grid_row + r_off, grid_col + c_off
            if not (0 <= r < GRID_SIZE and 0 <= c < GRID_SIZE and self.grid[r][c] == 0):
                return False
        return True

    def clear_lines(self):
        """Checks for and clears completed horizontal and vertical lines."""
        full_rows = [r for r in range(GRID_SIZE) if all(self.grid[r])]
        full_cols = [c for c in range(GRID_SIZE) if all(self.grid[r][c] for r in range(GRID_SIZE))]

        lines_cleared = len(full_rows) + len(full_cols)

        # Scoring: Simple combo system
        if lines_cleared == 1: self.score += 100
        elif lines_cleared == 2: self.score += 300 # Combo
        elif lines_cleared == 3: self.score += 600
        elif lines_cleared >= 4: self.score += 1000

        # Clear rows
        for r in full_rows:
            for c in range(GRID_SIZE):
                self.grid[r][c] = 0

        # Clear columns
        for c in full_cols:
            for r in range(GRID_SIZE):
                self.grid[r][c] = 0

        # After clearing, make blocks fall
        if full_rows or full_cols:
            # A simple gravity effect would be complex with static blocks.
            # The classic game this is based on does not have gravity after line clears.
            # So, we will just clear them and leave the space empty, which is also a valid design choice.
            pass


    def check_game_over(self):
        """Checks if any of the available blocks can be placed on the grid."""
        for block in self.available_blocks:
            for r in range(GRID_SIZE):
                for c in range(GRID_SIZE):
                    if self.is_valid_placement(block, r, c):
                        return False # Found a valid move
        return True # No valid moves for any available block

    def draw(self):
        """Draws all game elements to the screen."""
        self.screen.fill(BLACK)
        self.draw_hud()
        self.draw_grid()
        self.draw_placed_blocks()

        # Draw blocks in the tray
        for block in self.available_blocks:
            block.draw(self.screen, block.screen_pos, CELL_SIZE)

        # Draw dragging block and ghost preview
        if self.dragging_block:
            # Ghost preview
            mouse_pos = pygame.mouse.get_pos()
            grid_col = (mouse_pos[0] - GRID_X) // CELL_SIZE
            grid_row = (mouse_pos[1] - GRID_Y) // CELL_SIZE

            is_valid = self.is_valid_placement(self.dragging_block, grid_row, grid_col)
            ghost_color = (*GREEN, 100) if is_valid else (*RED, 100)

            ghost_pos = (GRID_X + grid_col * CELL_SIZE, GRID_Y + grid_row * CELL_SIZE)

            # Draw individual cells for transparency
            for r_off, c_off in self.dragging_block.shape:
                surface = pygame.Surface((CELL_SIZE, CELL_SIZE), pygame.SRCALPHA)
                surface.fill(ghost_color)
                self.screen.blit(surface, (ghost_pos[0] + c_off * CELL_SIZE, ghost_pos[1] + r_off * CELL_SIZE))

            # Draw the actual block being dragged on top
            self.dragging_block.draw(self.screen, self.dragging_block.screen_pos, CELL_SIZE)

    def draw_grid(self):
        """Draws the 8x8 grid lines."""
        for r in range(GRID_SIZE + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (GRID_X, GRID_Y + r * CELL_SIZE),
                             (GRID_X + GRID_WIDTH, GRID_Y + r * CELL_SIZE))
        for c in range(GRID_SIZE + 1):
            pygame.draw.line(self.screen, GRID_COLOR, (GRID_X + c * CELL_SIZE, GRID_Y),
                             (GRID_X + c * CELL_SIZE, GRID_Y + GRID_HEIGHT))

    def draw_placed_blocks(self):
        """Draws the blocks that are already on the grid."""
        for r in range(GRID_SIZE):
            for c in range(GRID_SIZE):
                if self.grid[r][c] != 0:
                    color = BLOCK_COLORS[self.grid[r][c] - 1]
                    pygame.draw.rect(self.screen, color,
                                     (GRID_X + c * CELL_SIZE + 1, GRID_Y + r * CELL_SIZE + 1,
                                      CELL_SIZE - 2, CELL_SIZE - 2))

    def draw_hud(self):
        """Draws the score and high score."""
        # Score
        score_text = self.font_medium.render("SCORE", True, WHITE)
        score_val = self.font_large.render(str(self.score), True, WHITE)
        self.screen.blit(score_text, (GRID_X, 50))
        self.screen.blit(score_val, (GRID_X, 80))

        # High Score
        high_score_text = self.font_medium.render("BEST", True, WHITE)
        high_score_val = self.font_large.render(str(self.high_score), True, WHITE)
        self.screen.blit(high_score_text, (SCREEN_WIDTH - GRID_X - high_score_text.get_width(), 50))
        self.screen.blit(high_score_val, (SCREEN_WIDTH - GRID_X - high_score_val.get_width(), 80))

    def show_game_over_screen(self):
        """Displays the game over modal and waits for player action."""
        # Create a semi-transparent overlay
        overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))
        self.screen.blit(overlay, (0, 0))

        # Game Over text
        game_over_text = self.font_large.render("GAME OVER", True, WHITE)
        self.screen.blit(game_over_text, game_over_text.get_rect(center=(SCREEN_WIDTH/2, 250)))

        # Final Score
        final_score_text = self.font_medium.render(f"Final Score: {self.score}", True, WHITE)
        self.screen.blit(final_score_text, final_score_text.get_rect(center=(SCREEN_WIDTH/2, 350)))

        # Best Score
        best_score_text = self.font_small.render(f"Best Score: {self.high_score}", True, LIGHT_GRAY)
        self.screen.blit(best_score_text, best_score_text.get_rect(center=(SCREEN_WIDTH/2, 400)))

        # Restart Button
        restart_button = pygame.Rect(0, 0, 200, 60)
        restart_button.center = (SCREEN_WIDTH / 2, 500)
        pygame.draw.rect(self.screen, GREEN, restart_button, border_radius=10)
        restart_text = self.font_medium.render("Restart", True, BLACK)
        self.screen.blit(restart_text, restart_text.get_rect(center=restart_button.center))

        pygame.display.flip()

        # Wait for player to click restart
        waiting_for_input = True
        while waiting_for_input:
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.MOUSEBUTTONDOWN:
                    if restart_button.collidepoint(event.pos):
                        waiting_for_input = False # Exit this loop to restart

def main():
    """Main function to run the game."""
    game = Game()
    game.run()

if __name__ == "__main__":
    main()