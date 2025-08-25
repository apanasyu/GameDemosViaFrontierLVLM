import pygame
import sys
import random
import math

# --- Constants ---
# Screen dimensions
SCREEN_WIDTH = 560
SCREEN_HEIGHT = 620
# Grid dimensions
GRID_WIDTH = 28
GRID_HEIGHT = 31
TILE_SIZE = SCREEN_WIDTH // GRID_WIDTH

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
PINK = (255, 184, 222)
CYAN = (0, 255, 255)
ORANGE = (255, 184, 82)
GHOST_BLUE = (33, 33, 255)
GHOST_WHITE = (222, 222, 222)

# Game settings
FPS = 60
PACMAN_SPEED = 2
GHOST_SPEED = 1.8
FRIGHTENED_DURATION = 7 * FPS  # 7 seconds

# Maze layout (1=wall, 0=pellet, 2=power pellet, 3=empty, 4=ghost spawn, P=player)
# *** CORRECTED PLAYER AND GHOST STARTING POSITIONS ***
LEVEL = [
    "1111111111111111111111111111",
    "1000000000000110000000000001",
    "1011110111110110111110111101",
    "1211110111110110111110111121",
    "1011110111110110111110111101",
    "1000000000000000000000000001",
    "1011110110111111110110111101",
    "1000000110000110000110000001",
    "1111110111113113111110111111",
    "1111110113333333333110111111",
    "1111110113111331113110111111",
    "1111110113144444413110111111",
    "1111110333144444413330111111",
    "3333330113144444413110333333",  # Tunnel row
    "1111110333144444413330111111",
    "1111110113111111113110111111",
    "1111110113333333333110111111",
    "1111110113111111113110111111",
    "1000000000000110000000000001",
    "1011110111110110111110111101",
    "1000110000000000000000110001",
    "1201100111110110111110011021",
    "1000000110000110000110000001",
    "101111111111P110111111111101",  # Pac-Man's new, safe starting position
    "1000000000000000000000000001",
    "1111111111111111111111111111",
]


# --- Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self, x, y, walls):
        super().__init__()
        self.start_pos = (x, y)
        self.image = pygame.Surface([TILE_SIZE - 4, TILE_SIZE - 4], pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.walls = walls
        self.direction = pygame.Vector2(0, 0)
        self.next_direction = pygame.Vector2(0, 0)
        self.speed = PACMAN_SPEED
        self.mouth_open = 0
        self.angle = 0

    def update(self):
        # Try to execute a queued turn
        if self.next_direction != (0, 0):
            can_turn_now = False

            # Case 1: Standing still - can always try to turn.
            if self.direction.x == 0 and self.direction.y == 0:
                can_turn_now = True
            # Case 2: Moving horizontally, trying to turn vertically
            elif self.next_direction.y != 0:
                # Check if Pac-Man is aligned with the grid to make a turn
                if (self.rect.centery - TILE_SIZE // 2) % TILE_SIZE == 0:
                    # Snap to grid to prevent getting stuck on corners
                    self.rect.centerx = round(self.rect.centerx / TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                    can_turn_now = True
            # Case 3: Moving vertically, trying to turn horizontally
            elif self.next_direction.x != 0:
                if (self.rect.centerx - TILE_SIZE // 2) % TILE_SIZE == 0:
                    self.rect.centery = round(self.rect.centery / TILE_SIZE) * TILE_SIZE + TILE_SIZE // 2
                    can_turn_now = True

            if can_turn_now:
                # Check if the new path is clear
                test_rect = self.rect.copy()
                test_rect.center += self.next_direction * self.speed
                if not any(wall.rect.colliderect(test_rect) for wall in self.walls):
                    self.direction = self.next_direction
                    self.next_direction = pygame.Vector2(0, 0)

        # Move the player
        self.rect.center += self.direction * self.speed

        # Wall collision
        hit_walls = pygame.sprite.spritecollide(self, self.walls, False)
        if hit_walls and self.direction != (0, 0):
            self.rect.center -= self.direction * self.speed
            self.direction = pygame.Vector2(0, 0)

        # Screen wrapping (tunnel)
        if self.rect.centerx < -TILE_SIZE / 2: self.rect.centerx = SCREEN_WIDTH + TILE_SIZE / 2
        if self.rect.centerx > SCREEN_WIDTH + TILE_SIZE / 2: self.rect.centerx = -TILE_SIZE / 2

        # Animate mouth
        self.mouth_open = (self.mouth_open + 1) % 20
        self._update_image()

    def _update_image(self):
        self.image.fill((0, 0, 0, 0))  # Transparent background

        # Determine angle for arc based on direction
        if self.direction == (1, 0):
            self.angle = 0
        elif self.direction == (-1, 0):
            self.angle = 180
        elif self.direction == (0, 1):
            self.angle = 270
        elif self.direction == (0, -1):
            self.angle = 90

        if self.direction == (0, 0):  # If not moving, show closed mouth
            pygame.draw.circle(self.image, YELLOW, (self.image.get_width() // 2, self.image.get_height() // 2),
                               (TILE_SIZE - 4) // 2)
        else:
            # Calculate mouth opening for chomping animation
            arc_start = math.radians(self.angle + 35 * (1 + math.sin(self.mouth_open * math.pi / 10)))
            arc_end = math.radians(self.angle + 360 - 35 * (1 + math.sin(self.mouth_open * math.pi / 10)))
            pygame.draw.arc(self.image, YELLOW, (0, 0, TILE_SIZE - 4, TILE_SIZE - 4), arc_start, arc_end,
                            TILE_SIZE // 2)

    def set_direction(self, direction):
        if self.direction == -direction:
            self.direction = direction
            self.next_direction = pygame.Vector2(0, 0)
        else:
            self.next_direction = direction

    def reset(self):
        self.rect.center = self.start_pos
        self.direction = pygame.Vector2(0, 0)
        self.next_direction = pygame.Vector2(0, 0)


class Ghost(pygame.sprite.Sprite):
    def __init__(self, x, y, color, walls):
        super().__init__()
        self.start_pos = (x, y)
        self.image = pygame.Surface([TILE_SIZE, TILE_SIZE], pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=(x, y))
        self.color = color
        self.walls = walls
        self.direction = random.choice(
            [pygame.Vector2(1, 0), pygame.Vector2(-1, 0), pygame.Vector2(0, 1), pygame.Vector2(0, -1)])
        self.speed = GHOST_SPEED
        self.state = 'chase'
        self.frightened_timer = 0
        self._draw_image()

    def _draw_image(self):
        self.image.fill((0, 0, 0, 0))

        body_color = GHOST_BLUE if self.state == 'frightened' else self.color
        eye_color = GHOST_WHITE if self.state == 'frightened' else WHITE
        pupil_color = BLACK if self.state != 'frightened' else GHOST_BLUE

        # Body
        pygame.draw.rect(self.image, body_color, (0, TILE_SIZE // 2, TILE_SIZE, TILE_SIZE // 2))
        pygame.draw.circle(self.image, body_color, (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2)
        # Jagged bottom
        for i in range(3):
            pygame.draw.polygon(self.image, body_color, [
                (i * TILE_SIZE / 3, TILE_SIZE),
                ((i + 0.5) * TILE_SIZE / 3, TILE_SIZE - 4),
                ((i + 1) * TILE_SIZE / 3, TILE_SIZE)
            ])

        # Eyes
        eye_y = TILE_SIZE // 2 - 2
        eye_l_x, eye_r_x = TILE_SIZE // 3, 2 * TILE_SIZE // 3
        pygame.draw.circle(self.image, eye_color, (eye_l_x, eye_y), TILE_SIZE // 6)
        pygame.draw.circle(self.image, eye_color, (eye_r_x, eye_y), TILE_SIZE // 6)

        # Pupils (look in direction of movement)
        pupil_offset_x = self.direction.x * TILE_SIZE / 12
        pupil_offset_y = self.direction.y * TILE_SIZE / 12
        pygame.draw.circle(self.image, pupil_color, (eye_l_x + pupil_offset_x, eye_y + pupil_offset_y), TILE_SIZE // 12)
        pygame.draw.circle(self.image, pupil_color, (eye_r_x + pupil_offset_x, eye_y + pupil_offset_y), TILE_SIZE // 12)

    def update(self):
        if self.state == 'frightened':
            self.frightened_timer -= 1
            if self.frightened_timer <= 0:
                self.state = 'chase'
                self.speed = GHOST_SPEED

        self._draw_image()
        self.move()

    def move(self):
        # Simplified AI: At an intersection, choose a new valid direction randomly (but don't reverse)
        if (self.rect.centerx - TILE_SIZE // 2) % TILE_SIZE == 0 and \
                (self.rect.centery - TILE_SIZE // 2) % TILE_SIZE == 0:

            possible_directions = []
            valid_turns = [pygame.Vector2(1, 0), pygame.Vector2(-1, 0), pygame.Vector2(0, 1), pygame.Vector2(0, -1)]

            # Don't let ghosts turn back unless it's a dead end
            if len(valid_turns) > 1 and -self.direction in valid_turns:
                valid_turns.remove(-self.direction)

            for d in valid_turns:
                test_rect = self.rect.copy()
                test_rect.center += d * self.speed
                if not any(wall.rect.colliderect(test_rect) for wall in self.walls):
                    possible_directions.append(d)

            if possible_directions:
                self.direction = random.choice(possible_directions)
            else:  # If stuck, reverse direction
                self.direction = -self.direction

        self.rect.center += self.direction * self.speed

        # Screen wrapping (tunnel)
        if self.rect.centerx < -TILE_SIZE / 2: self.rect.centerx = SCREEN_WIDTH + TILE_SIZE / 2
        if self.rect.centerx > SCREEN_WIDTH + TILE_SIZE / 2: self.rect.centerx = -TILE_SIZE / 2

    def frighten(self):
        self.state = 'frightened'
        self.frightened_timer = FRIGHTENED_DURATION
        self.speed = PACMAN_SPEED * 0.75  # Slower when frightened
        if (self.rect.centerx - TILE_SIZE // 2) % TILE_SIZE == 0 and \
                (self.rect.centery - TILE_SIZE // 2) % TILE_SIZE == 0:
            self.direction *= -1  # Reverse direction if at an intersection

    def reset(self):
        self.rect.center = self.start_pos
        self.state = 'chase'
        self.speed = GHOST_SPEED
        self.direction = random.choice([pygame.Vector2(0, -1), pygame.Vector2(0, 1)])


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([TILE_SIZE, TILE_SIZE])
        self.image.fill(BLUE)
        self.rect = self.image.get_rect(topleft=(x, y))


class Pellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([TILE_SIZE // 4, TILE_SIZE // 4])
        self.image.fill(WHITE)
        self.rect = self.image.get_rect(center=(x, y))


class PowerPellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface([TILE_SIZE, TILE_SIZE], pygame.SRCALPHA)
        pygame.draw.circle(self.image, WHITE, (TILE_SIZE // 2, TILE_SIZE // 2), TILE_SIZE // 2.5)
        self.rect = self.image.get_rect(center=(x, y))
        self.flash_timer = 0

    def update(self):
        # Flashing effect
        self.flash_timer = (self.flash_timer + 1) % 40
        self.image.set_alpha(255 if self.flash_timer < 20 else 0)


class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.Font(None, 36)
        self.small_font = pygame.font.Font(None, 28)
        self.state = 'start'
        self.score = 0
        self.lives = 3
        self.ghost_score_multiplier = 1

    def _create_level(self):
        self.all_sprites = pygame.sprite.Group()
        self.walls = pygame.sprite.Group()
        self.pellets = pygame.sprite.Group()
        self.power_pellets = pygame.sprite.Group()
        self.ghosts = pygame.sprite.Group()

        player_pos = None
        ghost_positions = []

        for row_idx, row in enumerate(LEVEL):
            for col_idx, char in enumerate(row):
                x, y = col_idx * TILE_SIZE, row_idx * TILE_SIZE
                if char == '1':
                    self.walls.add(Wall(x, y))
                elif char == '0':
                    self.pellets.add(Pellet(x + TILE_SIZE // 2, y + TILE_SIZE // 2))
                elif char == '2':
                    pp = PowerPellet(x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                    self.power_pellets.add(pp)
                    self.all_sprites.add(pp)
                elif char == 'P':
                    player_pos = (x + TILE_SIZE // 2, y + TILE_SIZE // 2)
                elif char == '4':
                    ghost_positions.append((x + TILE_SIZE // 2, y + TILE_SIZE // 2))

        # Player
        self.player = Player(player_pos[0], player_pos[1], self.walls)
        self.all_sprites.add(self.player)

        # Ghosts
        ghost_colors = [RED, PINK, CYAN, ORANGE]
        # To prevent ghosts from spawning on top of each other, we iterate through unique positions
        unique_ghost_positions = list(dict.fromkeys(ghost_positions))
        for i, pos in enumerate(unique_ghost_positions):
            if i < len(ghost_colors):
                ghost = Ghost(pos[0], pos[1], ghost_colors[i], self.walls)
                self.ghosts.add(ghost)
                self.all_sprites.add(ghost)

    def _handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if self.state == 'playing':
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_LEFT:
                        self.player.set_direction(pygame.Vector2(-1, 0))
                    elif event.key == pygame.K_RIGHT:
                        self.player.set_direction(pygame.Vector2(1, 0))
                    elif event.key == pygame.K_UP:
                        self.player.set_direction(pygame.Vector2(0, -1))
                    elif event.key == pygame.K_DOWN:
                        self.player.set_direction(pygame.Vector2(0, 1))
            elif self.state in ['start', 'game_over', 'win']:
                if event.type == pygame.KEYDOWN or event.type == pygame.MOUSEBUTTONDOWN:
                    self._reset_game()
                    self.state = 'playing'

    def _update(self):
        if self.state != 'playing':
            if self.state in ['start', 'win', 'game_over']:
                self.power_pellets.update()  # Keep power pellets flashing on menus
            return

        self.all_sprites.update()

        # Pellet collisions
        eaten_pellets = pygame.sprite.spritecollide(self.player, self.pellets, True)
        self.score += len(eaten_pellets) * 10

        # Power pellet collisions
        if pygame.sprite.spritecollide(self.player, self.power_pellets, True):
            self.score += 50
            self.ghost_score_multiplier = 1
            for ghost in self.ghosts:
                ghost.frighten()

        # Ghost collisions
        hit_ghosts = pygame.sprite.spritecollide(self.player, self.ghosts, False)
        for ghost in hit_ghosts:
            if ghost.state == 'frightened':
                self.score += 200 * self.ghost_score_multiplier
                self.ghost_score_multiplier *= 2
                ghost.reset()
            else:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = 'game_over'
                else:
                    self._reset_level()

        # Check win condition
        if not self.pellets and not self.power_pellets:
            self.state = 'win'

    def _draw(self):
        self.screen.fill(BLACK)
        if self.state == 'start':
            self._draw_text("PAC-MAN", self.font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
            self._draw_text("Press any key to start", self.small_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 20)
        elif self.state == 'game_over':
            self._draw_text("GAME OVER", self.font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
            self._draw_text(f"Final Score: {self.score}", self.small_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self._draw_text("Press any key to play again", self.small_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
        elif self.state == 'win':
            self._draw_text("YOU WIN!", self.font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50)
            self._draw_text(f"Final Score: {self.score}", self.small_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2)
            self._draw_text("Press any key to play again", self.small_font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 50)
        else:  # 'playing' state
            for wall in self.walls:
                pygame.draw.rect(self.screen, BLUE, wall.rect, 2)
            self.pellets.draw(self.screen)
            self.all_sprites.draw(self.screen)

            # Draw UI
            score_text = self.font.render(f"Score: {self.score}", True, WHITE)
            self.screen.blit(score_text, (10, SCREEN_HEIGHT - 45))

            lives_text = self.font.render("Lives:", True, WHITE)
            self.screen.blit(lives_text, (SCREEN_WIDTH - 150, SCREEN_HEIGHT - 45))
            for i in range(self.lives - 1):
                pygame.draw.circle(self.screen, YELLOW, (SCREEN_WIDTH - 70 + i * 30, SCREEN_HEIGHT - 30), 10)

        pygame.display.flip()

    def _draw_text(self, text, font, x, y, color=WHITE):
        text_surface = font.render(text, True, color)
        text_rect = text_surface.get_rect(center=(x, y))
        self.screen.blit(text_surface, text_rect)

    def _reset_level(self):
        # Brief pause to show the capture
        self._draw()
        pygame.time.wait(1000)

        # Reset positions
        self.player.reset()
        for ghost in self.ghosts:
            ghost.reset()

        # Another brief pause before play resumes
        self.screen.fill(BLACK)
        self._draw_text("GET READY!", self.font, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2, YELLOW)
        pygame.display.flip()
        pygame.time.wait(2000)

    def _reset_game(self):
        self.score = 0
        self.lives = 3
        self._create_level()

    def run(self):
        self.running = True
        self._create_level()
        while self.running:
            self.clock.tick(FPS)
            self._handle_events()
            self._update()
            self._draw()
        pygame.quit()
        sys.exit()


def main():
    game = Game()
    game.run()


if __name__ == "__main__":
    main()