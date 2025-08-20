import pygame
import random
import sys

# --- Constants ---
# Screen dimensions
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700

# Playfield dimensions (10x20 grid)
PLAY_WIDTH = 300  # 10 blocks * 30 pixels each
PLAY_HEIGHT = 600  # 20 blocks * 30 pixels each
BLOCK_SIZE = 30

# Top-left corner of the playfield on the screen
TOP_LEFT_X = (SCREEN_WIDTH - PLAY_WIDTH) // 2
TOP_LEFT_Y = SCREEN_HEIGHT - PLAY_HEIGHT - 50

# --- Tetrimino Shapes & Colors ---
# Shape formats for each Tetrimino
S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '.0...',
      '.....']]

I = [['..0..',
      '..0..',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '0000.',
      '.....',
      '.....',
      '.....']]

O = [['.....',
      '.....',
      '.00..',
      '.00..',
      '.....']]

J = [['.....',
      '.0...',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..00.',
      '..0..',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '...0.',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '.00..',
      '.....']]

L = [['.....',
      '...0.',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..0..',
      '..00.',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '.0...',
      '.....'],
     ['.....',
      '.00..',
      '..0..',
      '..0..',
      '.....']]

T = [['.....',
      '..0..',
      '.000.',
      '.....',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '.00..',
      '..0..',
      '.....']]

# Dictionary to hold all shapes and their corresponding colors
SHAPES = [S, Z, I, O, J, L, T]
SHAPE_COLORS = [
    (0, 255, 0),  # S - Green
    (255, 0, 0),  # Z - Red
    (0, 255, 255),  # I - Cyan
    (255, 255, 0),  # O - Yellow
    (0, 0, 255),  # J - Blue
    (255, 165, 0),  # L - Orange
    (128, 0, 128)  # T - Purple
]


# --- Game Classes ---

class Piece:
    """Represents a single Tetrimino piece."""

    def __init__(self, column, row, shape_index):
        self.x = column
        self.y = row
        self.shape_index = shape_index
        self.shape = SHAPES[shape_index]
        self.color = SHAPE_COLORS[shape_index]
        self.rotation = 0

    def get_formatted_shape(self):
        """Returns the current rotation of the shape as a list of (x, y) coordinates."""
        positions = []
        shape_format = self.shape[self.rotation % len(self.shape)]
        for i, line in enumerate(shape_format):
            row = list(line)
            for j, column in enumerate(row):
                if column == '0':
                    positions.append((self.x + j, self.y + i))

        # Offset for the 5x5 grid
        for i, pos in enumerate(positions):
            positions[i] = (pos[0] - 2, pos[1] - 4)
        return positions


class TetrisGame:
    """The main class that orchestrates the game."""

    def __init__(self):
        pygame.init()
        pygame.font.init()

        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Project Tetris Classic")

        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont('Arial', 30)
        self.small_font = pygame.font.SysFont('Arial', 24)

        self.reset_game()

    def reset_game(self):
        """Initializes or resets all game state variables."""
        self.locked_positions = {}  # (x, y): (r, g, b)
        self.grid = self.create_grid()

        self.change_piece = False
        self.run_game = True
        self.game_over = False

        self.current_piece = self.get_new_piece()
        self.next_piece_shapes = [self.get_new_piece() for _ in range(5)]

        self.fall_time = 0
        self.fall_speed = 0.27  # Seconds per step down
        self.level_time = 0

        # Lock Delay
        self.lock_delay = 500  # milliseconds
        self.lock_timer = None

        # Scoring
        self.score = 0
        self.level = 1
        self.lines_cleared = 0

        # Hold piece
        self.held_piece_shape_index = None
        self.hold_used = False

    def get_new_piece(self):
        """Implements the 7-Bag Randomizer to get a new piece."""
        if not hasattr(self, 'bag') or not self.bag:
            self.bag = list(range(len(SHAPES)))
            random.shuffle(self.bag)

        shape_index = self.bag.pop()
        # Spawn at middle-top (col 3 of 10, row 0)
        return Piece(3, 0, shape_index)

    def create_grid(self):
        """Creates an empty 10x20 grid and populates it with locked pieces."""
        grid = [[(0, 0, 0) for _ in range(10)] for _ in range(20)]
        for y in range(len(grid)):
            for x in range(len(grid[y])):
                if (x, y) in self.locked_positions:
                    grid[y][x] = self.locked_positions[(x, y)]
        return grid

    def is_valid_space(self, piece):
        """Checks if the piece's current position is valid."""
        accepted_pos = [[(j, i) for j in range(10) if self.grid[i][j] == (0, 0, 0)] for i in range(20)]
        accepted_pos = [j for sub in accepted_pos for j in sub]

        formatted_shape = piece.get_formatted_shape()

        for pos in formatted_shape:
            if pos not in accepted_pos:
                if pos[1] > -1:  # Allow pieces to be above the visible grid
                    return False
        return True

    def check_lost(self):
        """Checks if any locked piece is above the visible playfield."""
        for pos in self.locked_positions:
            x, y = pos
            if y < 1:
                return True
        return False

    def clear_lines(self):
        """Checks for and clears completed lines, returns number of lines cleared."""
        lines_to_clear = 0

        # Iterate from bottom to top
        for y in range(19, -1, -1):
            row_full = True
            for x in range(10):
                if self.grid[y][x] == (0, 0, 0):
                    row_full = False
                    break

            if row_full:
                lines_to_clear += 1
                # TODO: Play line clear sound
                # Shift every row above this one down
                for y_above in range(y, 0, -1):
                    for x_inner in range(10):
                        self.grid[y_above][x_inner] = self.grid[y_above - 1][x_inner]
                for x_inner in range(10):
                    self.grid[0][x_inner] = (0, 0, 0)

        # Update locked_positions from the modified grid
        new_locked = {}
        for y_new in range(len(self.grid)):
            for x_new in range(len(self.grid[y_new])):
                if self.grid[y_new][x_new] != (0, 0, 0):
                    new_locked[(x_new, y_new)] = self.grid[y_new][x_new]
        self.locked_positions = new_locked

        return lines_to_clear

    def update_score(self, num_lines):
        """Updates score, lines, and level based on lines cleared."""
        if num_lines == 1:
            self.score += 100 * self.level
        elif num_lines == 2:
            self.score += 300 * self.level
        elif num_lines == 3:
            self.score += 500 * self.level
        elif num_lines == 4:
            self.score += 800 * self.level  # Tetris!
            # TODO: Play Tetris clear sound

        self.lines_cleared += num_lines

        # Level up every 10 lines
        if self.lines_cleared >= self.level * 10:
            self.level += 1
            self.fall_speed = max(0.1, 0.27 - (self.level * 0.02))
            # TODO: Play level up sound

    def hard_drop(self):
        """Instantly drops the piece to the lowest possible position."""
        while self.is_valid_space(self.current_piece):
            self.current_piece.y += 1
        self.current_piece.y -= 1
        # Hard drop locks immediately, bypassing lock delay
        self.lock_piece()
        # TODO: Play hard drop sound

    def lock_piece(self):
        """Locks the current piece to the grid."""
        for pos in self.current_piece.get_formatted_shape():
            p = (pos[0], pos[1])
            self.locked_positions[p] = self.current_piece.color

        self.change_piece = True
        self.grid = self.create_grid()
        lines_cleared = self.clear_lines()
        if lines_cleared > 0:
            self.update_score(lines_cleared)

        if self.check_lost():
            self.game_over = True
            # TODO: Play game over sound
        self.hold_used = False  # Allow hold to be used again
        # TODO: Play lock piece sound

    def handle_input(self):
        """Processes all player input from the event queue."""
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.run_game = False
                pygame.quit()
                sys.exit()

            if event.type == pygame.KEYDOWN:
                if self.game_over:
                    if event.key == pygame.K_RETURN:
                        self.reset_game()
                    return

                # Move Left
                if event.key == pygame.K_LEFT:
                    self.current_piece.x -= 1
                    if not self.is_valid_space(self.current_piece):
                        self.current_piece.x += 1
                    else:
                        self.reset_lock_timer()
                        # TODO: Play move sound

                # Move Right
                elif event.key == pygame.K_RIGHT:
                    self.current_piece.x += 1
                    if not self.is_valid_space(self.current_piece):
                        self.current_piece.x -= 1
                    else:
                        self.reset_lock_timer()
                        # TODO: Play move sound

                # Soft Drop
                elif event.key == pygame.K_DOWN:
                    self.current_piece.y += 1
                    if not self.is_valid_space(self.current_piece):
                        self.current_piece.y -= 1
                    else:
                        # Soft dropping adds points
                        self.score += 1
                        # TODO: Play soft drop tick sound

                # Rotate (Clockwise)
                elif event.key == pygame.K_UP:
                    self.current_piece.rotation += 1
                    if not self.is_valid_space(self.current_piece):
                        self.current_piece.rotation -= 1  # Revert if invalid
                    else:
                        self.reset_lock_timer()
                        # TODO: Play rotate sound

                # Hard Drop
                elif event.key == pygame.K_SPACE:
                    self.hard_drop()

                # Hold Piece
                elif event.key == pygame.K_c:
                    self.hold_piece()

    def hold_piece(self):
        """Swaps the current piece with the held piece."""
        if self.hold_used:
            return

        if self.held_piece_shape_index is None:
            # First time holding, current piece goes to hold, next piece becomes current
            self.held_piece_shape_index = self.current_piece.shape_index
            self.current_piece = self.next_piece_shapes.pop(0)
            self.next_piece_shapes.append(self.get_new_piece())
        else:
            # Swap current with held
            current_shape_index = self.current_piece.shape_index
            self.current_piece = Piece(3, 0, self.held_piece_shape_index)
            self.held_piece_shape_index = current_shape_index

        self.hold_used = True
        self.lock_timer = None  # Reset lock timer after hold

    def reset_lock_timer(self):
        """Resets the lock timer if the piece is touching the ground."""
        self.current_piece.y += 1
        is_on_ground = not self.is_valid_space(self.current_piece)
        self.current_piece.y -= 1

        if is_on_ground:
            self.lock_timer = pygame.time.get_ticks()

    def draw_grid_lines(self):
        """Draws the grid lines for the playfield."""
        for i in range(21):
            pygame.draw.line(self.screen, (128, 128, 128), (TOP_LEFT_X, TOP_LEFT_Y + i * BLOCK_SIZE),
                             (TOP_LEFT_X + PLAY_WIDTH, TOP_LEFT_Y + i * BLOCK_SIZE))
        for j in range(11):
            pygame.draw.line(self.screen, (128, 128, 128), (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y),
                             (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y + PLAY_HEIGHT))

    def draw_window(self):
        """Draws everything to the screen."""
        self.screen.fill((20, 20, 30))  # Dark blue background

        # Draw Title
        title_text = self.font.render("Tetris Classic", True, (255, 255, 255))
        self.screen.blit(title_text, (TOP_LEFT_X + PLAY_WIDTH / 2 - title_text.get_width() / 2, 15))

        # Draw HUD: Score, Level, Lines
        score_label = self.font.render(f"Score: {self.score}", True, (255, 255, 255))
        level_label = self.font.render(f"Level: {self.level}", True, (255, 255, 255))
        lines_label = self.font.render(f"Lines: {self.lines_cleared}", True, (255, 255, 255))

        self.screen.blit(score_label, (TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y + 200))
        self.screen.blit(level_label, (TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y + 250))
        self.screen.blit(lines_label, (TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y + 300))

        # Draw "NEXT" queue
        next_label = self.font.render("NEXT", True, (255, 255, 255))
        self.screen.blit(next_label, (TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y))
        for i, piece in enumerate(self.next_piece_shapes[:3]):
            self.draw_small_piece(piece, TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y + 50 + i * 80)

        # Draw "HOLD" queue
        hold_label = self.font.render("HOLD", True, (255, 255, 255))
        self.screen.blit(hold_label, (TOP_LEFT_X - 150, TOP_LEFT_Y))
        if self.held_piece_shape_index is not None:
            held_piece = Piece(0, 0, self.held_piece_shape_index)
            self.draw_small_piece(held_piece, TOP_LEFT_X - 150, TOP_LEFT_Y + 50)

        # Draw the playfield border and grid lines
        pygame.draw.rect(self.screen, (150, 150, 150), (TOP_LEFT_X, TOP_LEFT_Y, PLAY_WIDTH, PLAY_HEIGHT), 2)
        self.draw_grid_lines()

        # Draw the locked blocks
        for y in range(len(self.grid)):
            for x in range(len(self.grid[y])):
                if self.grid[y][x] != (0, 0, 0):
                    pygame.draw.rect(self.screen, self.grid[y][x],
                                     (TOP_LEFT_X + x * BLOCK_SIZE, TOP_LEFT_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                                     0)

        # Draw Ghost Piece
        self.draw_ghost_piece()

        # Draw the current falling piece
        piece_positions = self.current_piece.get_formatted_shape()
        for pos in piece_positions:
            x, y = pos
            if y > -1:
                pygame.draw.rect(self.screen, self.current_piece.color,
                                 (TOP_LEFT_X + x * BLOCK_SIZE, TOP_LEFT_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 0)

        # Game Over Screen
        if self.game_over:
            self.draw_game_over()

        pygame.display.update()

    def draw_small_piece(self, piece, x_start, y_start):
        """Draws a smaller version of a piece for the Next/Hold queue."""
        shape_format = piece.shape[0]
        for i, line in enumerate(shape_format):
            row = list(line)
            for j, column in enumerate(row):
                if column == '0':
                    pygame.draw.rect(self.screen, piece.color,
                                     (x_start + j * 20, y_start + i * 20, 18, 18), 0)

    def draw_ghost_piece(self):
        """Draws a wireframe of where the current piece will land."""
        ghost = Piece(self.current_piece.x, self.current_piece.y, self.current_piece.shape_index)
        ghost.rotation = self.current_piece.rotation
        ghost.color = (128, 128, 128)  # Grey color for ghost

        # Find hard drop position
        while self.is_valid_space(ghost):
            ghost.y += 1
        ghost.y -= 1

        # Draw the ghost
        piece_positions = ghost.get_formatted_shape()
        for pos in piece_positions:
            x, y = pos
            if y > -1:
                pygame.draw.rect(self.screen, ghost.color,
                                 (TOP_LEFT_X + x * BLOCK_SIZE, TOP_LEFT_Y + y * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE), 2)

    def draw_start_screen(self):
        self.screen.fill((20, 20, 30))
        title = self.font.render('Project Tetris Classic', True, (255, 255, 255))
        prompt = self.small_font.render('Press Any Key To Start', True, (255, 255, 255))
        self.screen.blit(title, (SCREEN_WIDTH / 2 - title.get_width() / 2, SCREEN_HEIGHT / 2 - 50))
        self.screen.blit(prompt, (SCREEN_WIDTH / 2 - prompt.get_width() / 2, SCREEN_HEIGHT / 2 + 20))
        pygame.display.update()

        waiting = True
        while waiting:
            self.clock.tick(60)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                if event.type == pygame.KEYDOWN:
                    waiting = False

    def draw_game_over(self):
        overlay = pygame.Surface((PLAY_WIDTH, PLAY_HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 180))  # Semi-transparent black
        self.screen.blit(overlay, (TOP_LEFT_X, TOP_LEFT_Y))

        game_over_text = self.font.render("GAME OVER", True, (255, 0, 0))
        prompt_text = self.small_font.render("Press Enter to Play Again", True, (255, 255, 255))

        self.screen.blit(game_over_text,
                         (TOP_LEFT_X + PLAY_WIDTH / 2 - game_over_text.get_width() / 2, TOP_LEFT_Y + 200))
        self.screen.blit(prompt_text, (TOP_LEFT_X + PLAY_WIDTH / 2 - prompt_text.get_width() / 2, TOP_LEFT_Y + 250))

    def run(self):
        """The main game loop."""
        self.draw_start_screen()

        while self.run_game:
            self.grid = self.create_grid()
            self.fall_time += self.clock.get_rawtime()
            self.clock.tick()

            # --- Game Logic ---
            if not self.game_over:
                # Piece Gravity
                if self.fall_time / 1000 >= self.fall_speed:
                    self.fall_time = 0
                    self.current_piece.y += 1
                    if not self.is_valid_space(self.current_piece):
                        self.current_piece.y -= 1
                        # If lock timer isn't set, start it.
                        if self.lock_timer is None:
                            self.lock_timer = pygame.time.get_ticks()

                # Lock Delay Check
                if self.lock_timer is not None:
                    if pygame.time.get_ticks() - self.lock_timer > self.lock_delay:
                        self.lock_piece()

                # Change Piece
                if self.change_piece:
                    self.current_piece = self.next_piece_shapes.pop(0)
                    self.next_piece_shapes.append(self.get_new_piece())
                    self.change_piece = False
                    self.lock_timer = None  # Reset lock timer for new piece

                    # If the new piece is immediately invalid, game over
                    if not self.is_valid_space(self.current_piece):
                        self.game_over = True
                        # TODO: Play game over sound

            # --- Input and Drawing ---
            self.handle_input()
            self.draw_window()


def main():
    """Main function to run the game."""
    game = TetrisGame()
    game.run()


if __name__ == "__main__":
    main()
