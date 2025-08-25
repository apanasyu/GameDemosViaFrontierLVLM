import pygame
import sys
import random
from collections import deque

# --- 1. Constants and Configuration ---
# Screen and Grid
CELL_SIZE = 64
GRID_COLS = 12
GRID_ROWS = 7
HUD_HEIGHT = 64
SCREEN_WIDTH = CELL_SIZE * GRID_COLS
SCREEN_HEIGHT = CELL_SIZE * GRID_ROWS + HUD_HEIGHT
FPS = 60

# Colors
COLOR_BG = (240, 240, 240)
COLOR_GRID = (220, 220, 220)
COLOR_FRAME = (40, 40, 40)
COLOR_BLOCK = (60, 60, 60)
COLOR_PLAYER = (50, 205, 50)  # LimeGreen
COLOR_AI = (255, 165, 0)  # Orange
COLOR_BULLET = (30, 30, 30)
COLOR_TEXT = (20, 20, 20)
COLOR_HIT_OVERLAY = (255, 0, 0, 128)  # Red with alpha for transparency
COLOR_MODAL_BG = (255, 255, 255, 220)

# Tank Properties
TANK_SPEED = 3
AI_SPEED_MODIFIER = 0.9
TANK_SIZE = int(CELL_SIZE * 0.75)
FIRE_COOLDOWN = 500  # Milliseconds

# AI Properties
AI_PATHFIND_INTERVAL = 1000  # Recalculate path every second
AI_FIRE_COOLDOWN = 700


# --- 2. Helper Functions ---
def world_to_grid(pos):
    return int((pos[1] - HUD_HEIGHT) // CELL_SIZE), int(pos[0] // CELL_SIZE)


def grid_to_world_center(cell):
    x = cell[1] * CELL_SIZE + CELL_SIZE // 2
    y = cell[0] * CELL_SIZE + CELL_SIZE // 2 + HUD_HEIGHT  # Adjust for HUD
    return x, y


def draw_text(surface, text, size, x, y, color, align="center"):
    font = pygame.font.Font(None, size)
    text_surface = font.render(text, True, color)
    text_rect = text_surface.get_rect()
    if align == "center":
        text_rect.center = (x, y)
    elif align == "topleft":
        text_rect.topleft = (x, y)
    elif align == "midtop":
        text_rect.midtop = (x, y)
    surface.blit(text_surface, text_rect)


def bfs(grid, start_cell, end_cell):
    queue = deque([[start_cell]])
    visited = {start_cell}

    if start_cell == end_cell:
        return [start_cell]

    while queue:
        path = queue.popleft()
        row, col = path[-1]

        if (row, col) == end_cell:
            return path

        for dr, dc in [(0, 1), (0, -1), (1, 0), (-1, 0)]:
            next_row, next_col = row + dr, col + dc
            if (0 <= next_row < len(grid) and 0 <= next_col < len(grid[0]) and
                    grid[next_row][next_col] == 0 and (next_row, next_col) not in visited):
                visited.add((next_row, next_col))
                new_path = list(path)
                new_path.append((next_row, next_col))
                queue.append(new_path)
    return None


# --- 3. Game Object Classes (Sprites) ---
class Tank(pygame.sprite.Sprite):
    def __init__(self, color, pos, direction):
        super().__init__()
        self.image = pygame.Surface([TANK_SIZE, TANK_SIZE])
        self.image.fill(color)
        self.image.set_colorkey((0, 0, 0))  # For transparency if needed later
        self.original_image = self.image.copy()  # Store for when hit overlay is removed
        self.rect = self.image.get_rect(center=pos)
        self.color = color

        self.pos = pygame.math.Vector2(pos)
        self.vel = pygame.math.Vector2(0, 0)
        self.speed = TANK_SPEED
        self.direction = direction

        self.last_shot_time = 0
        self.is_destroyed = False

    def fire(self, bullets_group, all_sprites_group):
        now = pygame.time.get_ticks()
        if now - self.last_shot_time > FIRE_COOLDOWN:
            self.last_shot_time = now

            # <<< FIX 1: CALCULATE BULLET SPAWN POSITION >>>
            # Spawn the bullet in front of the tank, not inside it.
            spawn_pos = self.rect.center
            offset_dist = TANK_SIZE // 2 + 5  # Just outside the tank's body
            if self.direction == 'up':
                spawn_pos = (self.rect.centerx, self.rect.centery - offset_dist)
            elif self.direction == 'down':
                spawn_pos = (self.rect.centerx, self.rect.centery + offset_dist)
            elif self.direction == 'left':
                spawn_pos = (self.rect.centerx - offset_dist, self.rect.centery)
            elif self.direction == 'right':
                spawn_pos = (self.rect.centerx + offset_dist, self.rect.centery)

            bullet = Bullet(spawn_pos, self.direction)
            bullets_group.add(bullet)
            all_sprites_group.add(bullet)

    def update(self, blocks, arena_rect):
        self.pos += self.vel
        self.rect.centerx = round(self.pos.x)
        self.rect.centery = round(self.pos.y)

        # Collision detection
        # X-axis collision
        collided_blocks = pygame.sprite.spritecollide(self, blocks, False)
        if collided_blocks:
            if self.vel.x > 0: self.rect.right = collided_blocks[0].rect.left
            if self.vel.x < 0: self.rect.left = collided_blocks[0].rect.right
            self.pos.x = self.rect.centerx

        # Y-axis collision
        self.rect.centery = round(self.pos.y)  # Re-apply y position before checking y-axis
        collided_blocks = pygame.sprite.spritecollide(self, blocks, False)
        if collided_blocks:
            if self.vel.y > 0: self.rect.bottom = collided_blocks[0].rect.top
            if self.vel.y < 0: self.rect.top = collided_blocks[0].rect.bottom
            self.pos.y = self.rect.centery

        # Arena bounds collision
        if self.rect.left < arena_rect.left: self.rect.left = arena_rect.left
        if self.rect.right > arena_rect.right: self.rect.right = arena_rect.right
        if self.rect.top < arena_rect.top: self.rect.top = arena_rect.top
        if self.rect.bottom > arena_rect.bottom: self.rect.bottom = arena_rect.bottom
        self.pos.x, self.pos.y = self.rect.centerx, self.rect.centery

    def draw_barrel(self, surface):
        if self.is_destroyed: return  # Don't draw barrel if destroyed
        barrel_length = TANK_SIZE // 2
        barrel_end = list(self.rect.center)
        if self.direction == 'up':
            barrel_end[1] -= barrel_length
        elif self.direction == 'down':
            barrel_end[1] += barrel_length
        elif self.direction == 'left':
            barrel_end[0] -= barrel_length
        elif self.direction == 'right':
            barrel_end[0] += barrel_length
        pygame.draw.line(surface, COLOR_BLOCK, self.rect.center, barrel_end, 4)

    def destroy(self):
        self.is_destroyed = True
        self.image = self.original_image.copy()  # Start with a clean slate
        hit_overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
        hit_overlay.fill(COLOR_HIT_OVERLAY)
        self.image.blit(hit_overlay, (0, 0))


class Player(Tank):
    def __init__(self, pos):
        super().__init__(COLOR_PLAYER, pos, 'up')

    def handle_input(self):
        keys = pygame.key.get_pressed()
        self.vel.x, self.vel.y = 0, 0

        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.vel.x = -self.speed
            self.direction = 'left'
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.vel.x = self.speed
            self.direction = 'right'
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            self.vel.y = -self.speed
            self.direction = 'up'
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            self.vel.y = self.speed
            self.direction = 'down'

        # Normalize diagonal movement
        if self.vel.x != 0 and self.vel.y != 0:
            self.vel.x /= 1.414
            self.vel.y /= 1.414


class AI(Tank):
    def __init__(self, pos, player, blocks):
        super().__init__(COLOR_AI, pos, 'down')
        self.speed = TANK_SPEED * AI_SPEED_MODIFIER
        self.player = player
        self.all_blocks = blocks
        self.path = []
        self.last_path_time = 0
        self.last_shot_time = 0

    def update(self, blocks, arena_rect):
        now = pygame.time.get_ticks()

        if self.is_destroyed:
            self.vel.x, self.vel.y = 0, 0
            super().update(blocks, arena_rect)
            return

        if self.has_line_of_sight():
            self.vel.x, self.vel.y = 0, 0
            self.aim_at_player()
        else:
            if not self.path or now - self.last_path_time > AI_PATHFIND_INTERVAL:
                self.last_path_time = now
                self.find_path()

            if self.path:
                self.move_along_path()
            else:
                self.vel.x, self.vel.y = 0, 0

        super().update(blocks, arena_rect)

    def has_line_of_sight(self):
        start_pos = pygame.math.Vector2(self.rect.center)
        end_pos = pygame.math.Vector2(self.player.rect.center)

        # Check if tanks are roughly aligned horizontally or vertically
        aligned_h = abs(start_pos.y - end_pos.y) < TANK_SIZE / 2
        aligned_v = abs(start_pos.x - end_pos.x) < TANK_SIZE / 2
        if not (aligned_h or aligned_v):
            return False

        # Raycast for blocks
        direction = (end_pos - start_pos).normalize() if (end_pos - start_pos).length() > 0 else pygame.math.Vector2(0,
                                                                                                                     0)
        distance = start_pos.distance_to(end_pos)

        for i in range(0, int(distance), CELL_SIZE // 4):
            check_pos = start_pos + direction * i
            for block in self.all_blocks:
                if block.rect.collidepoint(check_pos):
                    return False
        return True

    def aim_at_player(self):
        dx = self.player.rect.centerx - self.rect.centerx
        dy = self.player.rect.centery - self.rect.centery
        if abs(dx) > abs(dy):
            self.direction = 'right' if dx > 0 else 'left'
        else:
            self.direction = 'down' if dy > 0 else 'up'

    def find_path(self):
        grid_map = [[0 for _ in range(GRID_COLS)] for _ in range(GRID_ROWS)]
        for block in self.all_blocks:
            row, col = world_to_grid(block.rect.topleft)
            if 0 <= row < GRID_ROWS and 0 <= col < GRID_COLS:
                grid_map[row][col] = 1

        start_cell = world_to_grid(self.rect.center)
        end_cell = world_to_grid(self.player.rect.center)

        if not (0 <= start_cell[0] < GRID_ROWS and 0 <= start_cell[1] < GRID_COLS): return
        if not (0 <= end_cell[0] < GRID_ROWS and 0 <= end_cell[1] < GRID_COLS): return

        path_cells = bfs(grid_map, start_cell, end_cell)
        if path_cells and len(path_cells) > 1:
            self.path = path_cells[1:]
        else:
            self.path = []

    def move_along_path(self):
        if not self.path:
            self.vel.x, self.vel.y = 0, 0
            return

        target_cell = self.path[0]
        target_pos = grid_to_world_center(target_cell)

        if pygame.math.Vector2(self.rect.center).distance_to(target_pos) < self.speed:
            self.path.pop(0)
            if not self.path:
                self.vel.x, self.vel.y = 0, 0
                return

        # Recalculate direction to target
        if self.path:
            target_pos = grid_to_world_center(self.path[0])
            direction_vec = pygame.math.Vector2(target_pos) - self.pos
            if direction_vec.length() > 0:
                direction_vec.normalize_ip()
                self.vel = direction_vec * self.speed
                if abs(self.vel.x) > abs(self.vel.y):
                    self.direction = 'right' if self.vel.x > 0 else 'left'
                else:
                    self.direction = 'down' if self.vel.y > 0 else 'up'
            else:
                self.vel.x, self.vel.y = 0, 0


class Block(pygame.sprite.Sprite):
    def __init__(self, pos):
        super().__init__()
        self.image = pygame.Surface([CELL_SIZE, CELL_SIZE], pygame.SRCALPHA)
        pygame.draw.rect(self.image, COLOR_BLOCK, (0, 0, CELL_SIZE, CELL_SIZE), border_radius=8)
        self.rect = self.image.get_rect(topleft=pos)


class Bullet(pygame.sprite.Sprite):
    def __init__(self, pos, direction):
        super().__init__()
        self.image = pygame.Surface([8, 8])
        pygame.draw.circle(self.image, COLOR_BULLET, (4, 4), 4)
        self.image.set_colorkey((0, 0, 0))
        self.rect = self.image.get_rect(center=pos)
        self.speed = 10
        self.vel = pygame.math.Vector2(0, 0)

        if direction == 'up':
            self.vel.y = -self.speed
        elif direction == 'down':
            self.vel.y = self.speed
        elif direction == 'left':
            self.vel.x = -self.speed
        elif direction == 'right':
            self.vel.x = self.speed

    def update(self, arena_rect):
        self.rect.move_ip(self.vel)
        if not arena_rect.contains(self.rect):
            self.kill()


# --- 4. Main Game Class ---
class Game:
    def __init__(self):
        pygame.init()
        self.screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
        pygame.display.set_caption("Tank Duel")
        self.clock = pygame.time.Clock()
        self.running = True
        self.game_over = False
        self.winner = None

        self.arena_rect = pygame.Rect(0, HUD_HEIGHT, SCREEN_WIDTH, SCREEN_HEIGHT - HUD_HEIGHT)
        self.new_game_button = pygame.Rect(SCREEN_WIDTH // 2 - 75, 12, 150, 40)

    def new_round(self):
        self.game_over = False
        self.winner = None

        self.all_sprites = pygame.sprite.Group()
        self.blocks = pygame.sprite.Group()
        self.bullets = pygame.sprite.Group()
        self.tanks = pygame.sprite.Group()

        # <<< FIX 2: CREATE SAFE ZONES FOR SPAWNING >>>
        # Define cells where blocks cannot be placed to ensure corridors are clear.
        player_spawn_cell = (GRID_ROWS - 1, 0)
        ai_spawn_cell = (0, GRID_COLS - 1)
        safe_zones = {
            player_spawn_cell, (player_spawn_cell[0], 1), (player_spawn_cell[0] - 1, 0),
            ai_spawn_cell, (ai_spawn_cell[0], ai_spawn_cell[1] - 1), (ai_spawn_cell[0] + 1, ai_spawn_cell[1])
        }

        # Create blocks, avoiding safe zones
        for r in range(GRID_ROWS):
            for c in range(GRID_COLS):
                # Don't spawn on the outermost border cells, only inner cells
                if r == 0 or r == GRID_ROWS - 1 or c == 0 or c == GRID_COLS - 1:
                    continue
                if (r, c) in safe_zones:
                    continue
                if random.random() < 0.6:
                    block = Block((c * CELL_SIZE, r * CELL_SIZE + HUD_HEIGHT))
                    self.blocks.add(block)
                    self.all_sprites.add(block)

        player_start_pos = grid_to_world_center(player_spawn_cell)
        self.player = Player(player_start_pos)

        ai_start_pos = grid_to_world_center(ai_spawn_cell)
        self.ai = AI(ai_start_pos, self.player, self.blocks)

        self.tanks.add(self.player, self.ai)
        self.all_sprites.add(self.player, self.ai)

    def run(self):
        while self.running:
            self.dt = self.clock.tick(FPS)
            self.events()
            self.update()
            self.draw()

    def events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.running = False
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.running = False
                if event.key == pygame.K_SPACE and not self.game_over:
                    self.player.fire(self.bullets, self.all_sprites)
                if event.key == pygame.K_n and self.game_over:
                    self.new_round()
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                if self.new_game_button.collidepoint(event.pos):
                    self.new_round()

        if not self.game_over:
            self.player.handle_input()

    def update(self):
        if self.game_over: return

        self.bullets.update(self.arena_rect)

        # AI Logic: Firing
        if self.ai.has_line_of_sight():
            now = pygame.time.get_ticks()
            if now - self.ai.last_shot_time > AI_FIRE_COOLDOWN:
                self.ai.aim_at_player()
                self.ai.fire(self.bullets, self.all_sprites)

        self.tanks.update(self.blocks, self.arena_rect)

        # Collision Checks
        pygame.sprite.groupcollide(self.bullets, self.blocks, True, True)

        bullet_hits = pygame.sprite.groupcollide(self.bullets, self.tanks, True, False)
        for bullet, hit_tanks in bullet_hits.items():
            for tank in hit_tanks:
                if not tank.is_destroyed:
                    tank.destroy()
                    self.game_over = True
                    self.winner = "ai" if tank == self.player else "player"

    def draw(self):
        self.screen.fill(COLOR_BG)

        pygame.draw.rect(self.screen, (220, 220, 220), (0, 0, SCREEN_WIDTH, HUD_HEIGHT))
        pygame.draw.rect(self.screen, COLOR_BLOCK, self.new_game_button, border_radius=8)
        draw_text(self.screen, "New Game", 30, self.new_game_button.centerx, self.new_game_button.centery,
                  (255, 255, 255))
        pygame.draw.line(self.screen, COLOR_FRAME, (0, HUD_HEIGHT), (SCREEN_WIDTH, HUD_HEIGHT), 2)

        pygame.draw.rect(self.screen, COLOR_FRAME, self.arena_rect, 2)

        self.all_sprites.draw(self.screen)

        for tank in self.tanks:
            tank.draw_barrel(self.screen)

        if self.game_over:
            modal_surf = pygame.Surface(self.screen.get_size(), pygame.SRCALPHA)
            modal_surf.fill(COLOR_MODAL_BG)
            outcome_text = "You Win!" if self.winner == "player" else "You Were Hit!"
            draw_text(modal_surf, "GAME OVER", 80, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 - 50, COLOR_TEXT)
            draw_text(modal_surf, outcome_text, 50, SCREEN_WIDTH // 2, SCREEN_HEIGHT // 2 + 10, COLOR_TEXT)
            draw_text(modal_surf, "Press 'N' or click New Game to restart", 28, SCREEN_WIDTH // 2,
                      SCREEN_HEIGHT // 2 + 70, COLOR_TEXT)
            self.screen.blit(modal_surf, (0, 0))

        pygame.display.flip()


# --- 5. Main Execution Block ---
def main():
    game = Game()
    game.new_round()
    game.run()
    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()