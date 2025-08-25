# Py-Man Game by AI
# Version: 1.8 (Classic Overhaul)
# A single-file implementation of a Pac-Man-like game using Pygame.
# FIX #1: Implemented an authentic, classic Pac-Man maze layout.
# FIX #2: Corrected ghost spawning positions to match the original game (Blinky outside, others inside).
# FIX #3: Greatly improved the ghost release mechanism to ensure they leave the pen sequentially.

import pygame
import random
import math
from collections import deque

# --- Game Constants ---
SCREEN_WIDTH = 672  # 28 tiles * 24 px
SCREEN_HEIGHT = 768  # 32 tiles * 24 px
TILE_SIZE = 24
FPS = 60

# --- Colors ---
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
YELLOW = (255, 255, 0)
BLUE = (0, 0, 255)
RED = (255, 0, 0)
PINK = (255, 182, 193)
CYAN = (0, 255, 255)
ORANGE = (255, 165, 0)
FRIGHTENED_BLUE = (50, 50, 200)
FRIGHTENED_WHITE = (200, 200, 255)

# --- Game Settings ---
PLAYER_SPEED = 2.0
GHOST_SPEED = 2.0
FRIGHTEN_SPEED = 1.5
PLAYER_LIVES = 3
FRIGHTEN_DURATION = 6000  # 6 seconds
FRIGHTEN_FLASH_DURATION = 2000
GHOST_POINTS = [200, 400, 800, 1600]

# --- Ghost Mode Timers (in frames) ---
MODE_SWITCH_TIMES = [7 * FPS, 20 * FPS, 7 * FPS, 20 * FPS, 5 * FPS, 20 * FPS, 5 * FPS, -1]

# --- Maze Layout ---
# FIX #1: Replaced the entire maze with a classic, arcade-accurate layout.
# Key: #=Wall, .=Pellet, P=Power Pellet, S=Player Spawn, G=Ghost Return, I=Inky, C=Clyde, K=Pinky, -=Ghost Door
MAZE_LAYOUT = [
    "############################",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#P####.#####.##.#####.####.P#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "#.####.##.########.##.####.#",
    "#.####.##.########.##.####.#",
    "#......##....##....##......#",
    "######.##### ## #####.######",
    "     #.##### ## #####.#     ",
    "     #.##   -G-  ##.#     ",  # The door is now centered above the pen
    "######.## #K I C# ##.######",  # Ghost starting positions inside the pen
    "      .   #     #   .      ",
    "######.## ####### ##.######",
    "     #.## ####### ##.#     ",
    "     #.##    S    ##.#     ",
    "######.## ####### ##.######",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#P..##.#####.##.#####.##..P#",
    "#...##... .........##...#",
    "#.######.### ## ###.######.#",
    "#.######.### ## ###.######.#",
    "#............##............#",
    "#.####.#####.##.#####.####.#",
    "#.####.#####.##.#####.####.#",
    "#..........................#",
    "############################",
    "                           ",
    "                           ",
]


# --- Helper Functions ---
def draw_text(surface, text, size, x, y, color):
    font = pygame.font.Font(pygame.font.get_default_font(), size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect(midtop=(x, y))
    surface.blit(text_surface, text_rect)


def pos_to_tile(pos):
    return int(pos.x // TILE_SIZE), int(pos.y // TILE_SIZE)


def tile_to_pos(tile):
    return pygame.Vector2(tile[0] * TILE_SIZE + TILE_SIZE / 2, tile[1] * TILE_SIZE + TILE_SIZE / 2)


def distance(pos1, pos2):
    return math.sqrt((pos1[0] - pos2[0]) ** 2 + (pos1[1] - pos2[1]) ** 2)


# --- Game Classes ---
class Player(pygame.sprite.Sprite):
    def __init__(self, game, pos):
        super().__init__()
        self.game = game
        self.start_pos = pos
        self.image = pygame.Surface((TILE_SIZE - 2, TILE_SIZE - 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=tile_to_pos(pos))
        self.pos = pygame.Vector2(self.rect.center)
        self.direction = pygame.Vector2(0, 0)
        self.buffered_direction = pygame.Vector2(0, 0)
        self.speed = PLAYER_SPEED
        self.lives = PLAYER_LIVES
        self.mouth_angle = 0
        self.mouth_anim_speed = 10
        self.radius = TILE_SIZE // 3

    def update(self):
        self.get_input()
        self.move()
        self.animate()
        self.check_collisions()

    def get_input(self):
        keys = pygame.key.get_pressed()
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.buffered_direction = pygame.Vector2(0, -1)
        elif keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.buffered_direction = pygame.Vector2(0, 1)
        elif keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.buffered_direction = pygame.Vector2(-1, 0)
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.buffered_direction = pygame.Vector2(1, 0)

    def is_at_intersection(self):
        return abs(self.pos.x % TILE_SIZE - TILE_SIZE / 2) < self.speed and \
            abs(self.pos.y % TILE_SIZE - TILE_SIZE / 2) < self.speed

    def move(self):
        current_tile = pos_to_tile(self.pos)
        if self.is_at_intersection():
            self.pos = tile_to_pos(current_tile)
            next_tile_buffered = current_tile + self.buffered_direction
            if not self.game.maze.is_wall(next_tile_buffered, self):
                self.direction = self.buffered_direction
            else:
                next_tile_current = current_tile + self.direction
                if self.game.maze.is_wall(next_tile_current, self):
                    self.direction = pygame.Vector2(0, 0)

        self.pos += self.direction * self.speed
        self.rect.center = self.pos

        if self.pos.x < -TILE_SIZE / 2:
            self.pos.x = SCREEN_WIDTH + TILE_SIZE / 2
        elif self.pos.x > SCREEN_WIDTH + TILE_SIZE / 2:
            self.pos.x = -TILE_SIZE / 2

    def animate(self):
        if self.direction == (0, 0):
            self.image.fill((0, 0, 0, 0))
            pygame.draw.circle(self.image, YELLOW, (self.image.get_width() / 2, self.image.get_height() / 2),
                               TILE_SIZE / 2 - 1)
            return

        self.mouth_angle = (self.mouth_angle + self.mouth_anim_speed) % 90
        mouth_open = self.mouth_angle < 45
        self.image.fill((0, 0, 0, 0))
        pygame.draw.circle(self.image, YELLOW, (self.image.get_width() / 2, self.image.get_height() / 2),
                           TILE_SIZE / 2 - 1)
        if mouth_open:
            mouth_center = (self.image.get_width() / 2, self.image.get_height() / 2)
            angle = -self.direction.angle_to(pygame.Vector2(1, 0))
            p_left = pygame.Vector2(TILE_SIZE / 2, 0).rotate(angle + self.mouth_angle) + mouth_center
            p_right = pygame.Vector2(TILE_SIZE / 2, 0).rotate(angle - self.mouth_angle) + mouth_center
            pygame.draw.polygon(self.image, BLACK, [mouth_center, p_left, p_right])

    def check_collisions(self):
        if pygame.sprite.spritecollide(self, self.game.pellets_group, True, pygame.sprite.collide_circle):
            self.game.score += 10
        if pygame.sprite.spritecollide(self, self.game.power_pellets_group, True, pygame.sprite.collide_circle):
            self.game.score += 50
            self.game.start_frighten_mode()

        if len(self.game.pellets_group) == 0 and len(self.game.power_pellets_group) == 0:
            self.game.level_cleared()

        collided_ghosts = pygame.sprite.spritecollide(self, self.game.ghosts_group, False, pygame.sprite.collide_circle)
        for ghost in collided_ghosts:
            if ghost.state == "FRIGHTENED":
                self.game.eat_ghost(ghost)
            elif ghost.state not in ["EATEN", "IN_PEN"]:
                self.game.player_dies()

    def die(self):
        self.lives -= 1
        if self.lives <= 0: self.game.game_over()

    def reset(self):
        self.rect.center = tile_to_pos(self.start_pos)
        self.pos = pygame.Vector2(self.rect.center)
        self.direction = pygame.Vector2(0, 0)
        self.buffered_direction = pygame.Vector2(0, 0)


class Ghost(pygame.sprite.Sprite):
    def __init__(self, game, pos, color, scatter_target, start_state="IN_PEN"):
        super().__init__()
        self.game, self.start_pos, self.color = game, pos, color
        self.image = pygame.Surface((TILE_SIZE - 2, TILE_SIZE - 2), pygame.SRCALPHA)
        self.rect = self.image.get_rect(center=tile_to_pos(pos))
        self.pos = pygame.Vector2(self.rect.center)
        self.direction = pygame.Vector2(0, -1)
        self.speed, self.state = GHOST_SPEED, start_state
        self.scatter_target, self.target_tile = scatter_target, None
        self.frightened_timer = 0
        self.radius = TILE_SIZE // 3
        self.draw_body()

    def draw_body(self):
        self.image.fill((0, 0, 0, 0))
        body_color = self.color
        if self.state == "FRIGHTENED":
            is_flashing = self.frightened_timer - pygame.time.get_ticks() < FRIGHTEN_FLASH_DURATION
            if is_flashing and (pygame.time.get_ticks() // 250) % 2 == 0:
                body_color = FRIGHTENED_WHITE
            else:
                body_color = FRIGHTENED_BLUE
        elif self.state == "EATEN":
            body_color = (0, 0, 0, 0)

        center_x, center_y = (TILE_SIZE - 2) / 2, (TILE_SIZE - 2) / 4
        pygame.draw.rect(self.image, body_color, (0, center_y, TILE_SIZE - 2, (TILE_SIZE - 2) * 3 / 4))
        pygame.draw.circle(self.image, body_color, (center_x, center_y), TILE_SIZE / 2 - 1)

        eye_y, eye_x_offset = TILE_SIZE / 2 - 2, TILE_SIZE / 4
        pupil_offset = self.direction * 2 if self.state != "EATEN" else pygame.Vector2(0, 0)
        for i in [-1, 1]:
            eye_pos = (center_x + (eye_x_offset * i) - i, eye_y)
            pygame.draw.circle(self.image, WHITE, eye_pos, 4)
            pygame.draw.circle(self.image, BLACK, (eye_pos[0] + pupil_offset.x, eye_pos[1] + pupil_offset.y), 2)

    def update(self):
        if self.state == "FRIGHTENED":
            self.speed = FRIGHTEN_SPEED
            if pygame.time.get_ticks() > self.frightened_timer:
                self.game.end_frighten_mode_for_ghost(self)
        elif self.state == "EATEN":
            self.speed = GHOST_SPEED * 2
        else:
            self.speed = GHOST_SPEED
        self.set_target()
        self.move()
        self.draw_body()

    def is_at_intersection(self):
        return abs(self.pos.x % TILE_SIZE - TILE_SIZE / 2) < self.speed and \
            abs(self.pos.y % TILE_SIZE - TILE_SIZE / 2) < self.speed

    def move(self):
        if self.target_tile and self.is_at_intersection():
            current_tile = pos_to_tile(self.pos)
            self.pos = tile_to_pos(current_tile)

            all_dirs = [pygame.Vector2(0, -1), pygame.Vector2(-1, 0), pygame.Vector2(0, 1), pygame.Vector2(1, 0)]
            valid_dirs = [d for d in all_dirs if not self.game.maze.is_wall(current_tile + d, self)]

            forward_dirs = [d for d in valid_dirs if d != -self.direction]

            if self.state == "FRIGHTENED":
                if forward_dirs:
                    self.direction = random.choice(forward_dirs)
                else:
                    self.direction = random.choice(valid_dirs) if valid_dirs else -self.direction
            else:
                dirs_to_check = forward_dirs if forward_dirs else valid_dirs
                if dirs_to_check:
                    self.direction = min(dirs_to_check, key=lambda d: distance(current_tile + d, self.target_tile))

        self.pos += self.direction * self.speed
        self.rect.center = self.pos

        if self.pos.x < -TILE_SIZE / 2:
            self.pos.x = SCREEN_WIDTH + TILE_SIZE / 2
        elif self.pos.x > SCREEN_WIDTH + TILE_SIZE / 2:
            self.pos.x = -TILE_SIZE / 2

    def set_target(self):
        current_tile = pos_to_tile(self.pos)
        if self.state == "CHASE" or self.state == "SCATTER":
            self.target_tile = self.get_chase_target() if self.state == "CHASE" else self.scatter_target
        elif self.state == "EATEN":
            self.target_tile = self.game.maze.ghost_return_pos
            if current_tile == self.target_tile:
                self.state = "IN_PEN"
                # FIX #3: Center the ghost properly when it re-enters the pen
                self.pos = tile_to_pos(self.game.maze.ghost_return_pos)
                self.rect.center = self.pos
        elif self.state == "IN_PEN":
            self.target_tile = self.game.maze.ghost_exit_pos
        elif self.state == "LEAVING_PEN":
            self.target_tile = self.game.maze.ghost_exit_pos
            if current_tile == self.target_tile:
                self.state = self.game.current_ghost_mode

    def get_chase_target(self):
        return pos_to_tile(self.game.player.pos)

    def eaten(self):
        self.state = "EATEN"

    def frighten(self):
        if self.state != "EATEN":
            self.state = "FRIGHTENED"
            if self.state not in ["IN_PEN", "LEAVING_PEN"]:
                self.direction *= -1
            self.frightened_timer = pygame.time.get_ticks() + FRIGHTEN_DURATION

    def reset(self):
        self.rect.center = tile_to_pos(self.start_pos)
        self.pos = pygame.Vector2(self.rect.center)
        self.state = "IN_PEN" if not isinstance(self, Blinky) else "SCATTER"
        self.direction = pygame.Vector2(-1, 0) if isinstance(self, Blinky) else pygame.Vector2(0, -1)
        self.draw_body()


class Blinky(Ghost):
    def __init__(self, game, pos): super().__init__(game, pos, RED, (25, -2), start_state="SCATTER")


class Pinky(Ghost):
    def __init__(self, game, pos): super().__init__(game, pos, PINK, (2, -2))

    def get_chase_target(self):
        pt, pd = pos_to_tile(self.game.player.pos), self.game.player.direction
        if pd == (0, -1): return (pt[0] - 4, pt[1] - 4)
        return (pt[0] + pd.x * 4, pt[1] + pd.y * 4)


class Inky(Ghost):
    def __init__(self, game, pos): super().__init__(game, pos, CYAN, (27, 33))

    def get_chase_target(self):
        pt, pd = pos_to_tile(self.game.player.pos), self.game.player.direction
        blinky = next((g for g in self.game.ghosts_group if isinstance(g, Blinky)), None)
        if not blinky: return pt
        bt = pos_to_tile(blinky.pos)
        ot = (pt[0] + pd.x * 2, pt[1] + pd.y * 2)
        return (ot[0] + (ot[0] - bt[0]), ot[1] + (ot[1] - bt[1]))


class Clyde(Ghost):
    def __init__(self, game, pos): super().__init__(game, pos, ORANGE, (0, 33))

    def get_chase_target(self):
        pt, ct = pos_to_tile(self.game.player.pos), pos_to_tile(self.pos)
        return pt if distance(pt, ct) > 8 else self.scatter_target


class Wall(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE));
        self.image.fill(BLUE)
        self.rect = self.image.get_rect(topleft=(x, y))


class Pellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        pygame.draw.circle(self.image, WHITE, (TILE_SIZE / 2, TILE_SIZE / 2), 3)
        self.rect = self.image.get_rect(topleft=(x, y))
        self.radius = 3


class PowerPellet(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__();
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE), pygame.SRCALPHA)
        self.radius = TILE_SIZE // 3;
        self.rect = self.image.get_rect(topleft=(x, y))

    def update(self):
        self.image.fill((0, 0, 0, 0))
        if (pygame.time.get_ticks() // 250) % 2 != 0:
            pygame.draw.circle(self.image, WHITE, (TILE_SIZE // 2, TILE_SIZE // 2), self.radius)


class Maze:
    def __init__(self, layout):
        self.walls = pygame.sprite.Group();
        self.pellets = pygame.sprite.Group()
        self.power_pellets = pygame.sprite.Group();
        self.grid = []
        self.ghost_door = []
        # FIX #2: Added specific spawn locations for each ghost inside the pen
        self.ghost_spawns = {}
        self.ghost_return_pos = None

        for y, row in enumerate(layout):
            grid_row = []
            for x, char in enumerate(row):
                is_wall = (char == '#')
                grid_row.append(1 if is_wall else 0)
                if is_wall:
                    self.walls.add(Wall(x * TILE_SIZE, y * TILE_SIZE))
                elif char == '.':
                    self.pellets.add(Pellet(x * TILE_SIZE, y * TILE_SIZE))
                elif char == 'P':
                    self.power_pellets.add(PowerPellet(x * TILE_SIZE, y * TILE_SIZE))
                elif char == 'S':
                    self.player_spawn_pos = (x, y)
                elif char == '-':
                    self.ghost_door.append((x, y))
                elif char == 'G':  # Return point for eaten ghosts
                    self.ghost_return_pos = (x, y)
                # FIX #2: Store individual ghost start positions
                elif char in ['K', 'I', 'C']:
                    self.ghost_spawns[char] = (x, y)
            self.grid.append(grid_row)

        # FIX #1: Define the exit point for ghosts leaving the pen
        self.ghost_exit_pos = (13, 11)

    def is_wall(self, tile_pos, sprite=None):
        x, y = int(tile_pos[0]), int(tile_pos[1])
        if (x, y) in self.ghost_door:
            return not isinstance(sprite, Ghost)
        # Updated tunnel check for the new maze
        if y == 14 and (x <= -1 or x >= 28):
            return False
        if not (0 <= y < len(self.grid) and 0 <= x < len(self.grid[y])):
            return True
        return self.grid[y][x] == 1


class Game:
    def __init__(self):
        pygame.init();
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Py-Man");
        self.clock = pygame.time.Clock()
        self.running, self.state = True, "START_SCREEN"
        self.score, self.high_score, self.level = 0, self.load_high_score(), 1
        self.player_lives = PLAYER_LIVES

    def run(self):
        while self.running: self.events(); self.update(); self.draw()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT or (
                    event.type == pygame.KEYDOWN and event.key == pygame.K_ESCAPE): self.running = False
            if event.type == pygame.KEYDOWN:
                if self.state == "START_SCREEN" and event.key == pygame.K_RETURN:
                    self.new_level();
                    self.state = "LEVEL_START"
                elif self.state == "GAMEPLAY" and event.key == pygame.K_p:
                    self.state = "PAUSED"
                elif self.state == "PAUSED" and event.key == pygame.K_p:
                    self.state = "GAMEPLAY"
                elif self.state == "GAME_OVER" and event.key == pygame.K_RETURN:
                    self.reset_game()

    def update(self):
        if self.state == "GAMEPLAY":
            self.all_sprites.update()
            self.power_pellets_group.update()
            self.check_ghost_mode_switch()

            # FIX #3: Improved ghost release logic
            if self.ghost_release_timer > 0:
                self.ghost_release_timer -= 1
            elif self.ghosts_in_pen:
                ghost_to_release = self.ghosts_in_pen.pop(0)
                ghost_to_release.state = "LEAVING_PEN"
                self.ghost_release_timer = 4 * FPS  # Timer for next ghost

        elif self.state == "LEVEL_START":
            self.level_start_timer -= 1
            if self.level_start_timer <= 0: self.state = "GAMEPLAY"
        elif self.state == "PLAYER_DYING":
            self.player_dying_timer -= 1
            if self.player_dying_timer <= 0:
                self.player.die()
                if self.player.lives > 0:
                    self.reset_level_after_death()
                    self.state = "LEVEL_START"
                else:
                    self.game_over()

    def draw(self):
        self.screen.fill(BLACK)
        if self.state == "START_SCREEN":
            self.draw_start_screen()
        elif self.state == "GAME_OVER":
            self.draw_game_over_screen()
        else:
            self.maze.walls.draw(self.screen);
            self.pellets_group.draw(self.screen)
            self.power_pellets_group.draw(self.screen);
            self.all_sprites.draw(self.screen)
            self.draw_hud()
            if self.state == "LEVEL_START":
                draw_text(self.screen, "READY!", 40, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 48, YELLOW)
            elif self.state == "PAUSED":
                draw_text(self.screen, "PAUSED", 50, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2 - 48, WHITE)
        pygame.display.flip()
        self.clock.tick(FPS)

    def new_level(self):
        self.all_sprites = pygame.sprite.Group();
        self.pellets_group = pygame.sprite.Group()
        self.power_pellets_group = pygame.sprite.Group();
        self.ghosts_group = pygame.sprite.Group()
        self.maze = Maze(MAZE_LAYOUT)
        self.pellets_group.add(self.maze.pellets);
        self.power_pellets_group.add(self.maze.power_pellets)
        self.player = Player(self, self.maze.player_spawn_pos);
        self.player.lives = self.player_lives
        self.all_sprites.add(self.player)

        # FIX #2: Spawn ghosts in their classic starting positions
        blinky = Blinky(self, self.maze.ghost_exit_pos)  # Starts outside
        pinky = Pinky(self, self.maze.ghost_spawns['K'])
        inky = Inky(self, self.maze.ghost_spawns['I'])
        clyde = Clyde(self, self.maze.ghost_spawns['C'])
        self.ghosts = [blinky, pinky, inky, clyde]
        self.ghosts_group.add(self.ghosts)
        self.all_sprites.add(self.ghosts)

        # FIX #3: Set up the release queue correctly for ghosts starting in the pen
        self.ghosts_in_pen = [pinky, inky, clyde]
        self.ghost_release_timer = 2 * FPS

        self.ghost_points_multiplier, self.mode_change_timer, self.mode_index = 0, 0, 0
        self.previous_ghost_mode = "SCATTER"
        self.set_ghost_mode("SCATTER");
        self.level_start_timer = 3 * FPS

    def reset_level_after_death(self):
        self.player.reset();
        [ghost.reset() for ghost in self.ghosts]
        self.ghosts_in_pen = [g for g in self.ghosts if g.state == "IN_PEN"]
        self.ghosts_in_pen.sort(
            key=lambda g: isinstance(g, Pinky) and -1 or isinstance(g, Inky) and 0 or 1)  # Pinky, Inky, Clyde order
        self.ghost_release_timer = 3 * FPS
        self.mode_change_timer, self.mode_index = 0, 0;
        self.set_ghost_mode("SCATTER")
        self.level_start_timer = 3 * FPS

    def reset_game(self):
        self.score, self.level, self.player_lives = 0, 1, PLAYER_LIVES
        self.new_level();
        self.state = "LEVEL_START"

    def draw_start_screen(self):
        draw_text(self.screen, "PY-MAN", 64, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4, YELLOW)
        draw_text(self.screen, "Press ENTER to Start", 30, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, WHITE)
        draw_text(self.screen, f"High Score: {self.high_score}", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT * 3 / 4, WHITE)

    def draw_game_over_screen(self):
        draw_text(self.screen, "GAME OVER", 64, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 4, RED)
        draw_text(self.screen, f"Final Score: {self.score}", 30, SCREEN_WIDTH / 2, SCREEN_HEIGHT / 2, WHITE)
        if self.score > self.high_score: draw_text(self.screen, "NEW HIGH SCORE!", 25, SCREEN_WIDTH / 2,
                                                   SCREEN_HEIGHT / 2 + 40, YELLOW)
        draw_text(self.screen, "Press ENTER to Play Again", 22, SCREEN_WIDTH / 2, SCREEN_HEIGHT * 3 / 4, WHITE)

    def draw_hud(self):
        draw_text(self.screen, f"Score: {self.score}", 22, 100, 5, WHITE)
        draw_text(self.screen, f"High Score: {self.high_score}", 22, SCREEN_WIDTH - 120, 5, WHITE)
        for i in range(self.player.lives - 1):
            life_surf = pygame.Surface((TILE_SIZE - 2, TILE_SIZE - 2), pygame.SRCALPHA)
            pygame.draw.circle(life_surf, YELLOW, (life_surf.get_width() / 2, life_surf.get_height() / 2),
                               TILE_SIZE / 2 - 1)
            self.screen.blit(life_surf, (10 + i * (TILE_SIZE + 5), SCREEN_HEIGHT - TILE_SIZE - 5))

    def level_cleared(self):
        self.level += 1;
        self.player_lives = self.player.lives
        self.new_level();
        self.state = "LEVEL_START"

    def player_dies(self):
        self.state = "PLAYER_DYING";
        self.player_dying_timer = 2 * FPS

    def game_over(self):
        self.state = "GAME_OVER"
        if self.score > self.high_score: self.high_score = self.score; self.save_high_score()

    def start_frighten_mode(self):
        if self.current_ghost_mode != "FRIGHTENED":
            self.previous_ghost_mode = self.current_ghost_mode
        self.current_ghost_mode = "FRIGHTENED";
        [g.frighten() for g in self.ghosts]
        self.ghost_points_multiplier = 0
        self.mode_change_timer = 0

    def end_frighten_mode_for_ghost(self, ghost):
        if ghost.state == "FRIGHTENED":
            ghost.state = self.previous_ghost_mode
            ghost.draw_body()

    def eat_ghost(self, ghost):
        self.score += GHOST_POINTS[self.ghost_points_multiplier]
        self.ghost_points_multiplier = min(self.ghost_points_multiplier + 1, len(GHOST_POINTS) - 1)
        ghost.eaten()

    def set_ghost_mode(self, mode):
        self.current_ghost_mode = mode
        for ghost in self.ghosts:
            if ghost.state not in ["EATEN", "FRIGHTENED", "IN_PEN", "LEAVING_PEN"]:
                ghost.state = mode
                if ghost.is_at_intersection():
                    ghost.direction *= -1

    def check_ghost_mode_switch(self):
        if self.current_ghost_mode != "FRIGHTENED":
            self.mode_change_timer += 1
            if self.mode_index < len(MODE_SWITCH_TIMES) and MODE_SWITCH_TIMES[self.mode_index] != -1:
                if self.mode_change_timer >= MODE_SWITCH_TIMES[self.mode_index]:
                    self.mode_index += 1;
                    self.mode_change_timer = 0
                    self.set_ghost_mode("CHASE" if self.mode_index % 2 != 0 else "SCATTER")

    def load_high_score(self):
        try:
            with open("highscore.txt", "r") as f:
                return int(f.read())
        except (FileNotFoundError, ValueError):
            return 0

    def save_high_score(self):
        with open("highscore.txt", "w") as f: f.write(str(self.high_score))


if __name__ == "__main__":
    game = Game()
    game.run()
    pygame.quit()