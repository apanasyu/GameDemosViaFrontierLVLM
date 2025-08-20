import pygame
import random

# #############################################################################
# SECTION 1: CONSTANTS (from constants.py)
# #############################################################################

# --- Screen and Grid Dimensions ---
SCREEN_WIDTH = 800
SCREEN_HEIGHT = 700
PLAY_WIDTH = 300  # 10 blocks * 30 pixels/block
PLAY_HEIGHT = 600  # 20 blocks * 30 pixels/block
BLOCK_SIZE = 30

# Top-left corner of the playfield on the screen
TOP_LEFT_X = (SCREEN_WIDTH - PLAY_WIDTH) // 2
TOP_LEFT_Y = SCREEN_HEIGHT - PLAY_HEIGHT - 50

# --- Grid Dimensions ---
GRID_WIDTH = 10
GRID_HEIGHT = 20  # This is the visible grid height

# --- Tetrimino Shapes ---
# Shape formats are a list of mino positions relative to a pivot point
# Indexed by rotation state
S = [['.....',
      '.....',
      '..00.',
      '.00..',
      '.....'],
     ['.....',
      '..0.',
      '..00.',
      '...0.',
      '.....']]

Z = [['.....',
      '.....',
      '.00..',
      '..00.',
      '.....'],
     ['.....',
      '..0.',
      '.00.',
      '.0..',
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
      '.00..',
      '.00..',
      '.....',
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
      '.00.',
      '..0..',
      '.....'],
     ['.....',
      '.....',
      '.000.',
      '..0..',
      '.....'],
     ['.....',
      '..0..',
      '..00.',
      '..0..',
      '.....']]

# --- Data Structures for Pieces ---
SHAPES = [S, Z, I, O, J, L, T]
SHAPE_NAMES = ["S", "Z", "I", "O", "J", "L", "T"]

# Guideline colors (Section 1.1)
SHAPE_COLORS = {
    "S": (0, 255, 0),  # Green
    "Z": (255, 0, 0),  # Red
    "I": (0, 255, 255),  # Cyan
    "O": (255, 255, 0),  # Yellow
    "J": (0, 0, 255),  # Blue
    "L": (255, 128, 0),  # Orange
    "T": (128, 0, 128)  # Purple
}

# --- Gameplay Tuning (Section 6.2) ---
# All times are in milliseconds
LOCK_DELAY = 500  # 0.5 seconds
DAS_DELAY = 160  # Delayed Auto Shift
ARR_DELAY = 30  # Auto Repeat Rate


# #############################################################################
# SECTION 2: PIECE CLASS (from piece.py)
# #############################################################################

class Piece:
    def __init__(self, column, row, shape_name):
        self.x = column
        self.y = row
        self.shape_name = shape_name
        self.shape = SHAPES[SHAPE_NAMES.index(shape_name)]
        self.color = SHAPE_COLORS[shape_name]
        self.rotation = 0

    def get_formatted_shape(self):
        # Returns the current rotation of the shape
        return self.shape[self.rotation % len(self.shape)]

    def get_block_positions(self):
        # Returns the absolute grid coordinates of the piece's blocks
        positions = []
        shape_format = self.get_formatted_shape()
        for i, line in enumerate(shape_format):
            row = list(line)
            for j, column in enumerate(row):
                if column == '0':
                    positions.append((self.x + j, self.y + i))

        # Offset to account for the 5x5 grid representation
        for i, pos in enumerate(positions):
            positions[i] = (pos[0] - 2, pos[1] - 4)
        return positions

    def rotate(self, clockwise=True):
        if clockwise:
            self.rotation = (self.rotation + 1) % len(self.shape)
        else:
            self.rotation = (self.rotation - 1) % len(self.shape)


# #############################################################################
# SECTION 3: BOARD CLASS (from board.py)
# #############################################################################

class Board:
    def __init__(self):
        # The grid stores the color of locked pieces. 0 means empty.
        self.grid = [[0 for _ in range(GRID_WIDTH)] for _ in range(GRID_HEIGHT)]
        self.game_over = False

    def is_valid_position(self, piece):
        # Checks if a piece is in a valid position on the grid
        accepted_pos = [[(j, i) for j in range(GRID_WIDTH) if self.grid[i][j] == 0] for i in range(GRID_HEIGHT)]
        accepted_pos = [j for sub in accepted_pos for j in sub]  # Flatten list

        formatted = piece.get_block_positions()

        for pos in formatted:
            if pos not in accepted_pos:
                if pos[1] > -1:  # Allow pieces to be above the screen
                    return False
        return True

    def lock_piece(self, piece):
        for pos in piece.get_block_positions():
            if pos[1] >= 0:  # Only lock blocks that are on the visible grid
                self.grid[pos[1]][pos[0]] = piece.color

        cleared_lines = self.clear_lines()

        # Check for game over (Block Out)
        for pos in piece.get_block_positions():
            if pos[1] < 0:
                self.game_over = True
                return 0  # No lines cleared if game over

        return cleared_lines

    def clear_lines(self):
        lines_to_clear = []
        for i, row in enumerate(self.grid):
            if 0 not in row:
                lines_to_clear.append(i)

        if not lines_to_clear:
            return 0

        for line_index in lines_to_clear:
            # Remove the full row
            del self.grid[line_index]
            # Add a new empty row at the top
            self.grid.insert(0, [0 for _ in range(GRID_WIDTH)])

        return len(lines_to_clear)

    def draw(self, screen):
        # Draw the grid lines
        for i in range(GRID_HEIGHT + 1):
            pygame.draw.line(screen, (50, 50, 50), (TOP_LEFT_X, TOP_LEFT_Y + i * BLOCK_SIZE),
                             (TOP_LEFT_X + PLAY_WIDTH, TOP_LEFT_Y + i * BLOCK_SIZE))
        for j in range(GRID_WIDTH + 1):
            pygame.draw.line(screen, (50, 50, 50), (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y),
                             (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y + PLAY_HEIGHT))

        # Draw the locked pieces
        for i in range(len(self.grid)):
            for j in range(len(self.grid[i])):
                if self.grid[i][j] != 0:
                    pygame.draw.rect(screen, self.grid[i][j],
                                     (TOP_LEFT_X + j * BLOCK_SIZE, TOP_LEFT_Y + i * BLOCK_SIZE, BLOCK_SIZE, BLOCK_SIZE),
                                     0)

        # Draw the playfield border
        pygame.draw.rect(screen, (255, 255, 255), (TOP_LEFT_X, TOP_LEFT_Y, PLAY_WIDTH, PLAY_HEIGHT), 4)


# #############################################################################
# SECTION 4: GAME CLASS (from game.py)
# #############################################################################

class Game:
    def __init__(self, screen):
        self.screen = screen
        self.clock = pygame.time.Clock()
        self.board = Board()
        self.running = True

        # --- 7-Bag Randomizer (Section 2.6) ---
        self.bag = []
        self.fill_bag()

        # --- Piece Management ---
        self.current_piece = self.get_new_piece()
        self.next_pieces = [self.get_new_piece() for _ in range(5)]  # Next Queue (Section 2.3)
        self.held_piece = None  # Hold Queue (Section 2.2)
        self.can_hold = True

        # --- Timers ---
        self.fall_time = 0
        self.fall_speed = 500  # Milliseconds per step down
        self.soft_drop_speed = 50  # Speed for soft drop

        self.lock_delay_timer = 0
        self.is_on_ground = False

        # --- Input Handling (for DAS/ARR) ---
        self.move_left_pressed = False
        self.move_right_pressed = False
        self.move_timer = 0
        self.das_timer = 0

        # --- Scoring (Marathon Mode) ---
        self.score = 0
        self.level = 1
        self.lines_cleared = 0
        self.is_back_to_back = False

    def fill_bag(self):
        self.bag = list(SHAPE_NAMES)
        random.shuffle(self.bag)

    def get_new_piece(self):
        if not self.bag:
            self.fill_bag()
        shape_name = self.bag.pop()
        return Piece(GRID_WIDTH // 2 - 2, 0, shape_name)

    def update(self, delta_time):
        self.handle_movement(delta_time)
        self.handle_gravity(delta_time)

        if self.board.game_over:
            self.running = False

    def handle_gravity(self, delta_time):
        # Check if piece is on the ground to start lock delay
        self.current_piece.y += 1
        if not self.board.is_valid_position(self.current_piece):
            self.current_piece.y -= 1
            if not self.is_on_ground:
                self.is_on_ground = True
                self.lock_delay_timer = 0
        else:
            self.current_piece.y -= 1
            self.is_on_ground = False

        # Handle Lock Delay (Section 2.5)
        if self.is_on_ground:
            self.lock_delay_timer += delta_time
            if self.lock_delay_timer > LOCK_DELAY:
                self.lock_current_piece()
            return

        # Handle normal gravity fall
        current_fall_speed = self.soft_drop_speed if pygame.key.get_pressed()[pygame.K_DOWN] else self.fall_speed
        self.fall_time += delta_time
        if self.fall_time > current_fall_speed:
            self.fall_time = 0
            self.current_piece.y += 1
            if not self.board.is_valid_position(self.current_piece):
                self.current_piece.y -= 1
                # No lock here, wait for lock delay logic

    def handle_movement(self, delta_time):
        # This implements DAS and ARR for smoother movement
        keys = pygame.key.get_pressed()

        # Left Movement
        if keys[pygame.K_LEFT]:
            if not self.move_left_pressed:  # First press
                self.move_left()
                self.move_left_pressed = True
                self.das_timer = 0
            else:
                self.das_timer += delta_time
                if self.das_timer > DAS_DELAY:
                    self.move_timer += delta_time
                    if self.move_timer > ARR_DELAY:
                        self.move_timer = 0
                        self.move_left()
        else:
            self.move_left_pressed = False

        # Right Movement
        if keys[pygame.K_RIGHT]:
            if not self.move_right_pressed:  # First press
                self.move_right()
                self.move_right_pressed = True
                self.das_timer = 0
            else:
                self.das_timer += delta_time
                if self.das_timer > DAS_DELAY:
                    self.move_timer += delta_time
                    if self.move_timer > ARR_DELAY:
                        self.move_timer = 0
                        self.move_right()
        else:
            self.move_right_pressed = False

    def move_left(self):
        self.current_piece.x -= 1
        if not self.board.is_valid_position(self.current_piece):
            self.current_piece.x += 1
        else:
            self.reset_lock_delay()

    def move_right(self):
        self.current_piece.x += 1
        if not self.board.is_valid_position(self.current_piece):
            self.current_piece.x -= 1
        else:
            self.reset_lock_delay()

    def rotate_piece(self, clockwise=True):
        self.current_piece.rotate(clockwise)
        if not self.board.is_valid_position(self.current_piece):
            # Basic Wall Kick (Section 2.4)
            # Try moving left, then right
            self.current_piece.x -= 1
            if self.board.is_valid_position(self.current_piece):
                self.reset_lock_delay()
                return
            self.current_piece.x += 2
            if self.board.is_valid_position(self.current_piece):
                self.reset_lock_delay()
                return

            # Revert if all kicks fail
            self.current_piece.x -= 1
            self.current_piece.rotate(not clockwise)
        else:
            self.reset_lock_delay()

    def hard_drop(self):
        while self.board.is_valid_position(self.current_piece):
            self.current_piece.y += 1
        self.current_piece.y -= 1
        self.lock_current_piece()

    def hold(self):
        if not self.can_hold:
            return

        if self.held_piece is None:
            self.held_piece = self.current_piece.shape_name
            self.current_piece = self.next_pieces.pop(0)
            self.next_pieces.append(self.get_new_piece())
        else:
            held_shape_name = self.held_piece
            self.held_piece = self.current_piece.shape_name
            self.current_piece = Piece(GRID_WIDTH // 2 - 2, 0, held_shape_name)

        self.can_hold = False
        self.is_on_ground = False
        self.lock_delay_timer = 0

    def reset_lock_delay(self):
        # Infinity / Move Reset (Section 2.5)
        if self.is_on_ground:
            self.lock_delay_timer = 0

    def lock_current_piece(self):
        cleared_count = self.board.lock_piece(self.current_piece)
        if cleared_count > 0:
            self.update_score(cleared_count, self.current_piece.shape_name == "T")  # Basic T-spin check

        self.current_piece = self.next_pieces.pop(0)
        self.next_pieces.append(self.get_new_piece())
        self.can_hold = True
        self.is_on_ground = False
        self.fall_time = 0

        if not self.board.is_valid_position(self.current_piece):
            self.board.game_over = True

    def update_score(self, lines, is_tspin):
        # Basic scoring, can be expanded for T-Spins, etc.
        base_points = {1: 100, 2: 300, 3: 500, 4: 800}

        is_difficult = (lines == 4 or is_tspin)

        score_to_add = base_points.get(lines, 0) * self.level

        if is_difficult and self.is_back_to_back:
            score_to_add *= 1.5  # Back-to-Back Bonus (Section 1.4)

        self.score += int(score_to_add)
        self.lines_cleared += lines

        self.is_back_to_back = is_difficult

        # Level up every 10 lines (Marathon Mode)
        new_level = (self.lines_cleared // 10) + 1
        if new_level > self.level:
            self.level = new_level
            # Increase speed (max fall speed is ~1 frame)
            self.fall_speed = max(50, 500 - (self.level - 1) * 30)

    def draw(self):
        self.screen.fill((20, 20, 30))  # Dark blue background
        self.board.draw(self.screen)

        self.draw_ghost_piece()
        self.draw_current_piece()
        self.draw_ui()

        pygame.display.flip()

    def draw_piece(self, piece, offset_x=0, offset_y=0, alpha=255):
        shape_positions = piece.get_block_positions()

        # Center the piece for UI display
        if offset_x != 0 or offset_y != 0:
            min_x = min(p[0] for p in shape_positions)
            max_x = max(p[0] for p in shape_positions)
            min_y = min(p[1] for p in shape_positions)
            max_y = max(p[1] for p in shape_positions)

            shape_width = (max_x - min_x + 1) * BLOCK_SIZE
            shape_height = (max_y - min_y + 1) * BLOCK_SIZE

            # Adjust offsets to center the visual shape
            offset_x -= shape_width / 2
            offset_y -= shape_height / 2

        for pos in shape_positions:
            px, py = pos
            rect = pygame.Rect(
                TOP_LEFT_X + px * BLOCK_SIZE + offset_x,
                TOP_LEFT_Y + py * BLOCK_SIZE + offset_y,
                BLOCK_SIZE, BLOCK_SIZE
            )

            if alpha < 255:
                # Drawing with transparency
                surface = pygame.Surface((BLOCK_SIZE, BLOCK_SIZE), pygame.SRCALPHA)
                pygame.draw.rect(surface, (*piece.color, alpha), (0, 0, BLOCK_SIZE, BLOCK_SIZE), 0)
                self.screen.blit(surface, rect.topleft)
            else:
                pygame.draw.rect(self.screen, piece.color, rect)

    def draw_current_piece(self):
        self.draw_piece(self.current_piece)

    def draw_ghost_piece(self):  # Section 2.1
        ghost = Piece(self.current_piece.x, self.current_piece.y, self.current_piece.shape_name)
        ghost.rotation = self.current_piece.rotation
        while self.board.is_valid_position(ghost):
            ghost.y += 1
        ghost.y -= 1
        self.draw_piece(ghost, alpha=80)  # Semi-transparent

    def draw_ui(self):
        font_large = pygame.font.Font(None, 40)
        font_small = pygame.font.Font(None, 32)

        # --- Next Queue ---
        next_label = font_large.render("NEXT", True, (255, 255, 255))
        self.screen.blit(next_label, (TOP_LEFT_X + PLAY_WIDTH + 50, TOP_LEFT_Y))
        for i, piece_name in enumerate(self.next_pieces):
            piece = Piece(0, 0, piece_name.shape_name)
            self.draw_piece(piece, offset_x=PLAY_WIDTH + 190, offset_y=70 + i * 80)

        # --- Hold Queue ---
        hold_label = font_large.render("HOLD", True, (255, 255, 255))
        self.screen.blit(hold_label, (TOP_LEFT_X - 150, TOP_LEFT_Y))
        if self.held_piece:
            piece = Piece(0, 0, self.held_piece)
            self.draw_piece(piece, offset_x=-240, offset_y=70)

        # --- Score, Level, Lines ---
        score_text = font_small.render(f"Score: {self.score}", True, (255, 255, 255))
        level_text = font_small.render(f"Level: {self.level}", True, (255, 255, 255))
        lines_text = font_small.render(f"Lines: {self.lines_cleared}", True, (255, 255, 255))

        self.screen.blit(score_text, (TOP_LEFT_X + PLAY_WIDTH + 50, 500))
        self.screen.blit(level_text, (TOP_LEFT_X + PLAY_WIDTH + 50, 540))
        self.screen.blit(lines_text, (TOP_LEFT_X + PLAY_WIDTH + 50, 580))

        if self.board.game_over:
            # Semi-transparent overlay
            overlay = pygame.Surface((SCREEN_WIDTH, SCREEN_HEIGHT), pygame.SRCALPHA)
            overlay.fill((0, 0, 0, 180))
            self.screen.blit(overlay, (0, 0))

            font_game_over = pygame.font.Font(None, 72)
            game_over_text = font_game_over.render("GAME OVER", True, (255, 0, 0))
            text_rect = game_over_text.get_rect(center=(SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2))
            self.screen.blit(game_over_text, text_rect)

    def run(self):
        while self.running:
            delta_time = self.clock.tick(60)  # Cap FPS at 60

            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    self.running = False
                if event.type == pygame.KEYDOWN:
                    if self.board.game_over:  # Don't process game input if game is over
                        if event.key == pygame.K_ESCAPE:
                            self.running = False
                        continue

                    if event.key == pygame.K_ESCAPE:
                        self.running = False
                    if event.key == pygame.K_UP or event.key == pygame.K_x:
                        self.rotate_piece(clockwise=True)
                    if event.key == pygame.K_z or event.key == pygame.K_LCTRL:  # Counter-clockwise
                        self.rotate_piece(clockwise=False)
                    if event.key == pygame.K_SPACE:
                        self.hard_drop()
                    if event.key == pygame.K_c or event.key == pygame.K_LSHIFT:
                        self.hold()

            if not self.board.game_over:
                self.update(delta_time)

            self.draw()

        pygame.time.wait(2000)  # Wait 2 seconds before closing


# #############################################################################
# SECTION 5: MAIN FUNCTION AND EXECUTION (from main.py)
# #############################################################################

def main():
    pygame.init()
    # pygame.mixer.init() # Uncomment when you add sounds

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Professional Tetris")

    game = Game(screen)
    game.run()

    pygame.quit()


if __name__ == "__main__":
    main()