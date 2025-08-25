import pygame
import sys
import random

# Constants
TILE_SIZE = 20
MAZE = [
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 3, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 3, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 0, 1, 1, 0, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 1, 1, 1, 4, 4, 1, 1, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [0, 0, 0, 0, 0, 0, 2, 0, 0, 0, 1, 0, 0, 0, 0, 0, 1, 0, 0, 0, 0, 2, 0, 0, 0, 0, 0, 0],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 1, 0, 0, 0, 0, 0, 1, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 1, 1, 1, 1, 1, 1, 1, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 2, 1, 1, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 2, 1, 1, 1, 1, 2, 1],
    [1, 3, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 2, 0, 0, 2, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 3, 1],
    [1, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1],
    [1, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 2, 1, 1, 1],
    [1, 2, 2, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 1, 1, 2, 2, 2, 2, 2, 2, 1],
    [1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1],
    [1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1, 1, 2, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 2, 1],
    [1, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 2, 1],
    [1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1, 1],
]
WIDTH = len(MAZE[0]) * TILE_SIZE
HEIGHT = len(MAZE) * TILE_SIZE
FPS = 30
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
PINK = (255, 105, 180)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
PLAYER_SPEED = 4
GHOST_SPEED = 3
TUNNEL_ROW = 14
# Maze legend: 0 - empty, 1 - wall, 2 - dot, 3 - power pellet, 4 - ghost start

class Pacman:
    def __init__(self):
        self.row = 23
        self.col = 14
        self.x = float(self.col * TILE_SIZE + TILE_SIZE // 2)
        self.y = float(self.row * TILE_SIZE + TILE_SIZE // 2)
        self.radius = TILE_SIZE // 2 - 2
        self.direction = (0, 0)
        self.next_direction = (0, 0)
        self.power_up = False
        self.power_up_timer = 0
        self.speed = PLAYER_SPEED

    def update(self):
        score_add = 0
        if self.direction == (0, 0) and self.next_direction == (0, 0):
            return 0

        # Try to change direction if next is different and possible
        if self.next_direction != self.direction:
            vel_x = self.next_direction[0] * self.speed
            vel_y = self.next_direction[1] * self.speed
            new_x = self.x + vel_x
            new_y = self.y + vel_y
            new_col = int(new_x // TILE_SIZE)
            new_row = int(new_y // TILE_SIZE)
            if 0 <= new_col < len(MAZE[0]) and 0 <= new_row < len(MAZE) and MAZE[new_row][new_col] != 1:
                self.direction = self.next_direction

        # Move in current direction
        vel_x = self.direction[0] * self.speed
        vel_y = self.direction[1] * self.speed
        new_x = self.x + vel_x
        new_y = self.y + vel_y
        new_col = int(new_x // TILE_SIZE)
        new_row = int(new_y // TILE_SIZE)

        move_ok = False
        if 0 <= new_col < len(MAZE[0]) and 0 <= new_row < len(MAZE):
            if MAZE[new_row][new_col] != 1:
                move_ok = True
        else:
            # Out of bounds, allow if tunnel
            if new_row == TUNNEL_ROW:
                move_ok = True

        if move_ok:
            self.x = new_x
            self.y = new_y
            # Wrap around
            if self.x < 0:
                self.x += WIDTH
            elif self.x > WIDTH:
                self.x -= WIDTH

        # Update grid position
        self.col = int(self.x // TILE_SIZE)
        self.row = int(self.y // TILE_SIZE)

        # Eat if entered new tile with dot or pellet
        if hasattr(self, 'last_row') and hasattr(self, 'last_col'):
            if (self.row, self.col) != (self.last_row, self.last_col):
                if MAZE[self.row][self.col] == 2:
                    MAZE[self.row][self.col] = 0
                    score_add = 10
                elif MAZE[self.row][self.col] == 3:
                    MAZE[self.row][self.col] = 0
                    score_add = 50
                    self.power_up = True
                    self.power_up_timer = 300
        else:
            # Initial setup
            pass

        self.last_row = self.row
        self.last_col = self.col

        return score_add

    def draw(self, screen):
        pygame.draw.circle(screen, YELLOW, (int(self.x), int(self.y)), self.radius)

class Ghost:
    def __init__(self, color, start_row, start_col):
        self.start_row = start_row
        self.start_col = start_col
        self.row = start_row
        self.col = start_col
        self.x = float(self.col * TILE_SIZE + TILE_SIZE // 2)
        self.y = float(self.row * TILE_SIZE + TILE_SIZE // 2)
        self.radius = TILE_SIZE // 2 - 2
        self.color = color
        self.direction = (0, -1)  # Start moving up
        self.vulnerable = False
        self.speed = GHOST_SPEED

    def reset(self):
        self.row = self.start_row
        self.col = self.start_col
        self.x = float(self.col * TILE_SIZE + TILE_SIZE // 2)
        self.y = float(self.row * TILE_SIZE + TILE_SIZE // 2)
        self.direction = (0, -1)

    def is_in_house(self):
        return 10 <= self.row <= 17 and 10 <= self.col <= 17

    def update(self, pacman_row, pacman_col, power_up):
        self.vulnerable = power_up

        if self.is_in_house() and not self.vulnerable:
            target_row = 8.0
            target_col = 14.0
        else:
            target_row = pacman_row
            target_col = pacman_col

        directions = [(0, -1), (0, 1), (-1, 0), (1, 0)]
        valid_dirs = []
        for dx, dy in directions:
            new_x = self.x + dx * self.speed
            new_y = self.y + dy * self.speed
            new_col_i = int(new_x // TILE_SIZE)
            new_row_i = int(new_y // TILE_SIZE)
            valid = False
            if 0 <= new_col_i < len(MAZE[0]) and 0 <= new_row_i < len(MAZE):
                if MAZE[new_row_i][new_col_i] != 1:
                    valid = True
            else:
                if new_row_i == TUNNEL_ROW:
                    valid = True
            if valid:
                valid_dirs.append((dx, dy))

        if len(valid_dirs) == 0:
            return

        reverse = (-self.direction[0], -self.direction[1])

        possible_dirs = valid_dirs[:]
        if not self.vulnerable and len(valid_dirs) > 1 and reverse in possible_dirs:
            possible_dirs.remove(reverse)

        if self.vulnerable:
            best_dir = random.choice(possible_dirs)
        else:
            min_dist = float('inf')
            best_dir = possible_dirs[0]
            for dx, dy in possible_dirs:
                new_x = self.x + dx * self.speed
                new_y = self.y + dy * self.speed
                new_col = new_x / TILE_SIZE
                new_row = new_y / TILE_SIZE
                # Wrap col for dist
                col_dist = min(abs(new_col - target_col), len(MAZE[0]) - abs(new_col - target_col))
                row_dist = abs(new_row - target_row)
                dist = col_dist + row_dist
                if dist < min_dist:
                    min_dist = dist
                    best_dir = (dx, dy)

        self.direction = best_dir

        # Move
        vel_x = self.direction[0] * self.speed
        vel_y = self.direction[1] * self.speed
        new_x = self.x + vel_x
        new_y = self.y + vel_y
        new_col_i = int(new_x // TILE_SIZE)
        new_row_i = int(new_y // TILE_SIZE)

        move_ok = False
        if 0 <= new_col_i < len(MAZE[0]) and 0 <= new_row_i < len(MAZE):
            if MAZE[new_row_i][new_col_i] != 1:
                move_ok = True
        else:
            if new_row_i == TUNNEL_ROW:
                move_ok = True

        if move_ok:
            self.x = new_x
            self.y = new_y
            if self.x < 0:
                self.x += WIDTH
            elif self.x > WIDTH:
                self.x -= WIDTH

        self.col = int(self.x // TILE_SIZE)
        self.row = int(self.y // TILE_SIZE)

    def draw(self, screen):
        color = BLUE if self.vulnerable else self.color
        pygame.draw.circle(screen, color, (int(self.x), int(self.y)), self.radius)

def draw_maze(screen):
    for row in range(len(MAZE)):
        for col in range(len(MAZE[row])):
            if MAZE[row][col] == 1:
                pygame.draw.rect(screen, BLUE, (col * TILE_SIZE, row * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif MAZE[row][col] == 2:
                pygame.draw.circle(screen, WHITE, (col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2), 4)
            elif MAZE[row][col] == 3:
                pygame.draw.circle(screen, WHITE, (col * TILE_SIZE + TILE_SIZE // 2, row * TILE_SIZE + TILE_SIZE // 2), 8)

def check_collision(pacman, ghost):
    dist = ((pacman.x - ghost.x)**2 + (pacman.y - ghost.y)**2)**0.5
    return dist < pacman.radius + ghost.radius

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Pac-Man")
    clock = pygame.time.Clock()

    pacman = Pacman()
    ghosts = [
        Ghost(RED, 13, 13),
        Ghost(PINK, 13, 14),
        Ghost(CYAN, 13, 15),
        Ghost(ORANGE, 14, 14)
    ]
    score = 0
    lives = 3
    font = pygame.font.Font(None, 36)

    running = True
    while running:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            elif event.type == pygame.KEYDOWN:
                if event.key == pygame.K_LEFT:
                    pacman.next_direction = (-1, 0)
                elif event.key == pygame.K_RIGHT:
                    pacman.next_direction = (1, 0)
                elif event.key == pygame.K_UP:
                    pacman.next_direction = (0, -1)
                elif event.key == pygame.K_DOWN:
                    pacman.next_direction = (0, 1)

        score += pacman.update()

        if pacman.power_up_timer > 0:
            pacman.power_up_timer -= 1
        else:
            pacman.power_up = False

        pac_row = pacman.y / TILE_SIZE
        pac_col = pacman.x / TILE_SIZE

        for ghost in ghosts:
            ghost.update(pac_row, pac_col, pacman.power_up)
            if check_collision(pacman, ghost):
                if pacman.power_up:
                    score += 200
                    ghost.reset()
                else:
                    lives -= 1
                    if lives == 0:
                        running = False
                    # Reset positions
                    pacman.row = 23
                    pacman.col = 14
                    pacman.x = float(pacman.col * TILE_SIZE + TILE_SIZE // 2)
                    pacman.y = float(pacman.row * TILE_SIZE + TILE_SIZE // 2)
                    pacman.direction = (0, 0)
                    pacman.next_direction = (0, 0)
                    for g in ghosts:
                        g.reset()

        screen.fill(BLACK)
        draw_maze(screen)
        pacman.draw(screen)
        for ghost in ghosts:
            ghost.draw(screen)

        score_text = font.render(f"Score: {score}", True, WHITE)
        lives_text = font.render(f"Lives: {lives}", True, WHITE)
        screen.blit(score_text, (10, 10))
        screen.blit(lives_text, (WIDTH - 100, 10))

        pygame.display.flip()
        clock.tick(FPS)

    pygame.quit()
    sys.exit()

if __name__ == "__main__":
    main()