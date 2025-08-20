import pygame
from pygame.locals import *
import random
import sys

# Constants
CELL_SIZE = 30
WIDTH = 10
HEIGHT = 22
VISIBLE_HEIGHT = 20
SCREEN_WIDTH = 500
SCREEN_HEIGHT = 620
FPS = 60
GRAVITY_BASE = 60.0  # frames per drop at level 1
SOFT_DROP_SPEED = 2  # frames per drop for soft drop

COLORS = {
    'I': (0, 255, 255),
    'O': (255, 255, 0),
    'T': (128, 0, 128),
    'S': (0, 255, 0),
    'Z': (255, 0, 0),
    'J': (0, 0, 255),
    'L': (255, 165, 0)
}

SHAPES = {
    'I': [
        [(-1, 0), (0, 0), (1, 0), (2, 0)],  # 0
        [(0, 1), (0, 0), (0, -1), (0, -2)],  # R
        [(-1, 0), (0, 0), (1, 0), (2, 0)],  # 2
        [(0, 1), (0, 0), (0, -1), (0, -2)]   # L
    ],
    'O': [
        [(0, 0), (1, 0), (0, -1), (1, -1)],  # same
        [(0, 0), (1, 0), (0, -1), (1, -1)],
        [(0, 0), (1, 0), (0, -1), (1, -1)],
        [(0, 0), (1, 0), (0, -1), (1, -1)]
    ],
    'T': [
        [(-1, 0), (0, 0), (1, 0), (0, -1)],  # 0
        [(0, 0), (-1, 0), (0, -1), (1, 0)],  # R
        [(-1, 0), (0, 0), (1, 0), (0, 1)],  # 2
        [(0, 0), (-1, 0), (0, 1), (1, 0)]   # L
    ],
    'S': [
        [(-1, 0), (0, 0), (0, -1), (1, -1)],  # 0
        [(0, 0), (0, 1), (1, 0), (1, -1)],  # R
        [(-1, 1), (0, 1), (0, 0), (1, 0)],  # 2
        [(-1, 1), (-1, 0), (0, 0), (0, -1)]   # L
    ],
    'Z': [
        [(-1, -1), (0, -1), (0, 0), (1, 0)],  # 0
        [(0, -1), (0, 0), (1, 1), (1, 0)],  # R
        [(-1, 0), (0, 0), (0, 1), (1, 1)],  # 2
        [(-1, 0), (-1, 1), (0, 0), (0, -1)]   # L
    ],
    'J': [
        [(-1, 0), (0, 0), (1, 0), (-1, -1)],  # 0
        [(0, 0), (0, -1), (0, 1), (-1, 1)],  # R
        [(-1, 0), (0, 0), (1, 0), (1, -1)],  # 2
        [(0, 0), (0, -1), (0, 1), (1, 1)]   # L
    ],
    'L': [
        [(-1, 0), (0, 0), (1, 0), (1, -1)],  # 0
        [(0, 0), (0, -1), (0, 1), (1, 1)],  # R
        [(-1, 0), (0, 0), (1, 0), (-1, -1)],  # 2
        [(0, 0), (0, -1), (0, 1), (-1, 1)]   # L
    ]
}

KICK_DATA = {
    'common': {
        (0, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        (1, 0): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        (1, 2): [(0, 0), (1, 0), (1, -1), (0, 2), (1, 2)],
        (2, 1): [(0, 0), (-1, 0), (-1, 1), (0, -2), (-1, -2)],
        (2, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)],
        (3, 2): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        (3, 0): [(0, 0), (-1, 0), (-1, -1), (0, 2), (-1, 2)],
        (0, 3): [(0, 0), (1, 0), (1, 1), (0, -2), (1, -2)]
    },
    'I': {
        (0, 1): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        (1, 0): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        (1, 2): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)],
        (2, 1): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        (2, 3): [(0, 0), (2, 0), (-1, 0), (2, 1), (-1, -2)],
        (3, 2): [(0, 0), (-2, 0), (1, 0), (-2, -1), (1, 2)],
        (3, 0): [(0, 0), (1, 0), (-2, 0), (1, -2), (-2, 1)],
        (0, 3): [(0, 0), (-1, 0), (2, 0), (-1, 2), (2, -1)]
    }
}

class Tetrimino:
    def __init__(self, piece_type):
        self.type = piece_type
        self.rotation = 0
        self.x = 4 if self.type in 'IO' else 3
        self.y = 0  # pivot row at top
        self.last_move = None
        self.last_kick = -1

    def get_blocks(self):
        return [(self.x + dx, self.y - dy) for dx, dy in SHAPES[self.type][self.rotation]]

    def move(self, dx, dy):
        self.x += dx
        self.y += dy

    def rotate(self, direction):
        old_rot = self.rotation
        new_rot = (self.rotation + direction) % 4
        if self.type == 'O':
            return False
        kicks = KICK_DATA['I' if self.type == 'I' else 'common'][(old_rot, new_rot)]
        for i, (kx, ky) in enumerate(kicks):
            new_x = self.x + kx
            new_y = self.y - ky  # adjust for y up
            self.x = new_x
            self.y = new_y
            self.rotation = new_rot
            if not game.collision(self):
                self.last_move = 'rotate'
                self.last_kick = i
                return True
            # revert
        self.rotation = old_rot
        self.x -= kx  # last one
        self.y += ky
        return False

class Tetris:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tetris")
        self.clock = pygame.time.Clock()
        self.grid = [[0] * WIDTH for _ in range(HEIGHT)]
        self.bag = []
        self.current_piece = self.generate_piece()
        self.hold_piece = None
        self.can_hold = True
        self.next_pieces = [self.generate_piece() for _ in range(5)]
        self.score = 0
        self.lines = 0
        self.level = 1
        self.game_over = False
        self.last_clear = None
        self.back_to_back = False
        self.drop_timer = 0
        self.lock_timer = 0
        self.move_resets = 0
        self.soft_dropping = False
        self.combo = 0
        self.vanish_zone = 2  # hidden top rows

    def generate_piece(self):
        if not self.bag:
            self.bag = list('IJLTOSZ')
            random.shuffle(self.bag)
        piece_type = self.bag.pop(0)
        return Tetrimino(piece_type)

    def next_piece(self):
        piece = self.next_pieces.pop(0)
        self.next_pieces.append(self.generate_piece())
        self.can_hold = True
        self.move_resets = 0
        self.last_move = None
        return piece

    def hold(self):
        if not self.can_hold:
            return
        if self.hold_piece is None:
            self.hold_piece = self.current_piece
            self.current_piece = self.next_piece()
        else:
            self.current_piece, self.hold_piece = self.hold_piece, self.current_piece
        self.current_piece.rotation = 0
        self.current_piece.x = 4 if self.current_piece.type in 'IO' else 3
        self.current_piece.y = 0
        self.can_hold = False

    def collision(self, piece):
        for bx, by in piece.get_blocks():
            if not (0 <= bx < WIDTH and 0 <= by < HEIGHT) or self.grid[by][bx] != 0:
                return True
        return False

    def drop(self):
        self.current_piece.move(0, 1)
        if self.collision(self.current_piece):
            self.current_piece.move(0, -1)
            return True
        return False

    def hard_drop(self):
        while not self.drop():
            self.score += 2  # score for hard drop
        self.lock()

    def lock(self):
        blocks = self.current_piece.get_blocks()
        is_tspin = self.is_tspin()
        for bx, by in blocks:
            self.grid[by][bx] = self.current_piece.type
        lines_cleared = self.clear_lines()
        self.update_score(lines_cleared, is_tspin)
        if all(by < self.vanish_zone for _, by in blocks):
            self.game_over = True
        self.current_piece = self.next_piece()
        if self.collision(self.current_piece):
            self.game_over = True

    def is_tspin(self):
        if self.current_piece.type != 'T' or self.last_move != 'rotate':
            return 0
        px, py = self.current_piece.x, self.current_piece.y
        corners = [
            (px - 1, py - 1),
            (px - 1, py + 1),
            (px + 1, py - 1),
            (px + 1, py + 1)
        ]
        occupied = 0
        for cx, cy in corners:
            if 0 <= cx < WIDTH and 0 <= cy < HEIGHT:
                if self.grid[cy][cx] != 0:
                    occupied += 1
            else:
                occupied += 1  # out of bounds count as occupied
        if occupied >= 3:
            return 1  # assume regular for now
        return 0

    def clear_lines(self):
        lines = []
        for r in range(HEIGHT):
            if all(self.grid[r]):
                lines.append(r)
        for r in reversed(lines):
            del self.grid[r]
            self.grid.insert(0, [0] * WIDTH)
        return len(lines)

    def update_score(self, lines, is_tspin):
        if lines == 0:
            self.back_to_back = False
            self.combo = 0
            return
        base = [0, 100, 300, 500, 800]
        if is_tspin:
            base = [0, 800, 1200, 1600, 0]  # no tspin quad
            if self.back_to_back:
                base[lines] = int(base[lines] * 1.5)
            self.back_to_back = True
        else:
            if lines == 4:
                if self.back_to_back:
                    base[lines] = int(base[lines] * 1.5)
                self.back_to_back = True
            else:
                self.back_to_back = False
        self.score += base[lines] * self.level
        self.combo += 1
        self.score += 50 * self.combo * self.level
        self.lines += lines
        self.level = self.lines // 10 + 1

    def get_ghost(self):
        ghost = Tetrimino(self.current_piece.type)
        ghost.rotation = self.current_piece.rotation
        ghost.x = self.current_piece.x
        ghost.y = self.current_piece.y
        while not self.collision(ghost):
            ghost.y += 1
        ghost.y -= 1
        return ghost

    def draw_grid(self):
        for y in range(self.vanish_zone, HEIGHT):
            for x in range(WIDTH):
                if self.grid[y][x]:
                    pygame.draw.rect(self.screen, COLORS[self.grid[y][x]],
                                     (x * CELL_SIZE + 100, (y - self.vanish_zone) * CELL_SIZE, CELL_SIZE, CELL_SIZE))
                pygame.draw.rect(self.screen, (50, 50, 50),
                                 (x * CELL_SIZE + 100, (y - self.vanish_zone) * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

    def draw_piece(self, piece, alpha=255, offset_y=0):
        color = COLORS[piece.type]
        for bx, by in piece.get_blocks():
            if by >= offset_y:
                surf = pygame.Surface((CELL_SIZE, CELL_SIZE))
                surf.fill(color)
                surf.set_alpha(alpha)
                self.screen.blit(surf, (bx * CELL_SIZE + 100, (by - offset_y) * CELL_SIZE))
                pygame.draw.rect(self.screen, (255, 255, 255),
                                 (bx * CELL_SIZE + 100, (by - offset_y) * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

    def draw_hold(self):
        if self.hold_piece:
            piece = Tetrimino(self.hold_piece.type)
            piece.x = 0
            piece.y = 3
            self.draw_piece(piece, offset_y=0)

    def draw_next(self):
        for i, p in enumerate(self.next_pieces):
            piece = Tetrimino(p.type)
            piece.x = 12
            piece.y = 3 + i * 4
            self.draw_piece(piece, offset_y=0)

    def run(self):
        while not self.game_over:
            self.screen.fill((0, 0, 0))
            self.drop_timer += 1
            gravity = GRAVITY_BASE / self.level
            if self.soft_dropping:
                gravity = SOFT_DROP_SPEED
            if self.drop_timer >= gravity:
                self.drop_timer = 0
                landed = self.drop()
                if not landed and self.soft_dropping:
                    self.score += 1
                if landed:
                    self.lock_timer += 1
                    if self.lock_timer >= 30:  # example lock delay in frames
                        self.lock()
                        self.lock_timer = 0
                else:
                    self.lock_timer = 0
                    self.move_resets = 0
            ghost = self.get_ghost()
            self.draw_piece(ghost, 100, offset_y=self.vanish_zone)  # semi transparent
            self.draw_grid()
            self.draw_piece(self.current_piece, offset_y=self.vanish_zone)
            self.draw_hold()
            self.draw_next()
            # draw score, level, etc.
            font = pygame.font.Font(None, 36)
            text = font.render(f"Score: {self.score}", True, (255,255,255))
            self.screen.blit(text, (10, 10))
            text = font.render(f"Level: {self.level}", True, (255,255,255))
            self.screen.blit(text, (10, 50))
            text = font.render(f"Lines: {self.lines}", True, (255,255,255))
            self.screen.blit(text, (10, 90))
            pygame.display.flip()
            self.clock.tick(FPS)
            for event in pygame.event.get():
                if event.type == QUIT:
                    sys.exit()
                if event.type == KEYDOWN:
                    if event.key == K_LEFT:
                        self.current_piece.move(-1, 0)
                        if self.collision(self.current_piece):
                            self.current_piece.move(1, 0)
                        else:
                            self.last_move = 'move'
                        if self.lock_timer > 0:
                            self.lock_timer = 0
                            self.move_resets += 1
                            if self.move_resets > 15:
                                self.lock()
                    if event.key == K_RIGHT:
                        self.current_piece.move(1, 0)
                        if self.collision(self.current_piece):
                            self.current_piece.move(-1, 0)
                        else:
                            self.last_move = 'move'
                        if self.lock_timer > 0:
                            self.lock_timer = 0
                            self.move_resets += 1
                            if self.move_resets > 15:
                                self.lock()
                    if event.key == K_DOWN:
                        self.soft_dropping = True
                    if event.key == K_UP:
                        self.current_piece.rotate(1)  # CW as alternative
                        if self.lock_timer > 0:
                            self.lock_timer = 0
                            self.move_resets += 1
                            if self.move_resets > 15:
                                self.lock()
                    if event.key == K_z:
                        self.current_piece.rotate(-1)  # CCW
                        if self.lock_timer > 0:
                            self.lock_timer = 0
                            self.move_resets += 1
                            if self.move_resets > 15:
                                self.lock()
                    if event.key == K_x:
                        self.current_piece.rotate(1)  # CW
                        if self.lock_timer > 0:
                            self.lock_timer = 0
                            self.move_resets += 1
                            if self.move_resets > 15:
                                self.lock()
                    if event.key == K_c:
                        self.hold()
                    if event.key == K_SPACE:
                        self.hard_drop()
                if event.type == KEYUP:
                    if event.key == K_DOWN:
                        self.soft_dropping = False

def main():
    global game
    game = Tetris()
    game.run()
    pygame.quit()

if __name__ == "__main__":
    main()