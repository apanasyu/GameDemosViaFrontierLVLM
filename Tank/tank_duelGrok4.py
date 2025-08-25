import pygame
from pygame.locals import *
import random
import queue
import math

# Constants
CELL_SIZE = 64
ROWS = 7
COLS = 12
WIDTH = COLS * CELL_SIZE
HEIGHT = ROWS * CELL_SIZE

# Colors
GREEN = (0, 255, 0)
ORANGE = (255, 165, 0)
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
RED = (255, 0, 0)
GRAY = (200, 200, 200)
DARK_GRAY = (50, 50, 50)

# Directions
DIRECTIONS = {
    'up': (0, -1),
    'down': (0, 1),
    'left': (-1, 0),
    'right': (1, 0)
}

class Tank:
    def __init__(self, color, pos, facing='right', is_ai=False):
        self.rect = pygame.Rect(pos[0] - 16, pos[1] - 16, 32, 32)  # Smaller tanks
        self.color = color
        self.facing = facing
        self.cooldown = 0
        self.alive = True
        self.is_ai = is_ai
        self.speed = 150 if is_ai else 200
        # For AI
        self.path = None
        self.path_timer = 0

    def update(self, dt, keys, block_rects):
        if not self.alive:
            return None

        self.cooldown -= dt

        dx = 0
        dy = 0
        if keys[K_UP] or keys[K_w]:
            dy -= self.speed * dt
            self.facing = 'up'
        if keys[K_DOWN] or keys[K_s]:
            dy += self.speed * dt
            self.facing = 'down'
        if keys[K_LEFT] or keys[K_a]:
            dx -= self.speed * dt
            self.facing = 'left'
        if keys[K_RIGHT] or keys[K_d]:
            dx += self.speed * dt
            self.facing = 'right'

        # Normalize diagonal movement
        if dx != 0 and dy != 0:
            dist = math.sqrt(dx**2 + dy**2)
            dx = (dx / dist) * self.speed * dt
            dy = (dy / dist) * self.speed * dt

        # Move X
        temp = self.rect.copy()
        temp.x += dx
        if temp.left < 0:
            temp.left = 0
        if temp.right > WIDTH:
            temp.right = WIDTH
        collided = False
        for br in block_rects:
            if temp.colliderect(br):
                collided = True
                if dx > 0:
                    temp.right = br.left
                elif dx < 0:
                    temp.left = br.right
        if not collided or True:  # Apply adjusted position
            self.rect.x = temp.x

        # Move Y
        temp = self.rect.copy()
        temp.y += dy
        if temp.top < 0:
            temp.top = 0
        if temp.bottom > HEIGHT:
            temp.bottom = HEIGHT
        collided = False
        for br in block_rects:
            if temp.colliderect(br):
                collided = True
                if dy > 0:
                    temp.bottom = br.top
                elif dy < 0:
                    temp.top = br.bottom
        if not collided or True:
            self.rect.y = temp.y

        # Fire
        bullet = None
        if keys[K_SPACE] and self.cooldown <= 0:
            dir_vec = DIRECTIONS[self.facing]
            bullet = Bullet(self.rect.center, dir_vec)
            self.cooldown = 0.5

        return bullet

    def update_ai(self, dt, player, block_positions, block_rects):
        if not self.alive:
            return None

        self.cooldown -= dt
        self.path_timer -= dt

        bullet = None

        # Check LOS
        if check_los(self.rect.center, player.rect.center, block_positions):
            # Aim facing
            dx = player.rect.centerx - self.rect.centerx
            dy = player.rect.centery - self.rect.centery
            if abs(dx) > abs(dy):
                self.facing = 'right' if dx > 0 else 'left'
            else:
                self.facing = 'down' if dy > 0 else 'up'
            if self.cooldown <= 0:
                dir_vec = DIRECTIONS[self.facing]
                bullet = Bullet(self.rect.center, dir_vec)
                self.cooldown = 0.5
        else:
            # Pathfind
            if self.path_timer <= 0:
                start = (self.rect.centery // CELL_SIZE, self.rect.centerx // CELL_SIZE)
                goal = (player.rect.centery // CELL_SIZE, player.rect.centerx // CELL_SIZE)
                self.path = bfs(start, goal, block_positions)
                self.path_timer = 1.0

            if self.path and len(self.path) > 1:
                next_cell = self.path[1]
                target_x = next_cell[1] * CELL_SIZE + CELL_SIZE / 2
                target_y = next_cell[0] * CELL_SIZE + CELL_SIZE / 2
                dx = target_x - self.rect.centerx
                dy = target_y - self.rect.centery
                dist = max(math.sqrt(dx**2 + dy**2), 1e-5)
                vx = (dx / dist) * self.speed
                vy = (dy / dist) * self.speed
                move_x = vx * dt
                move_y = vy * dt

                # Move X
                temp = self.rect.copy()
                temp.x += move_x
                if temp.left < 0:
                    temp.left = 0
                if temp.right > WIDTH:
                    temp.right = WIDTH
                for br in block_rects:
                    if temp.colliderect(br):
                        if move_x > 0:
                            temp.right = br.left
                        elif move_x < 0:
                            temp.left = br.right
                self.rect.x = temp.x

                # Move Y
                temp = self.rect.copy()
                temp.y += move_y
                if temp.top < 0:
                    temp.top = 0
                if temp.bottom > HEIGHT:
                    temp.bottom = HEIGHT
                for br in block_rects:
                    if temp.colliderect(br):
                        if move_y > 0:
                            temp.bottom = br.top
                        elif move_y < 0:
                            temp.top = br.bottom
                self.rect.y = temp.y

                # Update facing
                if abs(dx) > abs(dy):
                    self.facing = 'right' if dx > 0 else 'left'
                else:
                    self.facing = 'down' if dy > 0 else 'up'

                # Check if reached
                if dist < self.speed * dt:
                    self.path = self.path[1:]
            else:
                # Wander
                if random.random() < 0.01:
                    self.facing = random.choice(list(DIRECTIONS.keys()))
                dir_vec = DIRECTIONS[self.facing]
                move_x = dir_vec[0] * self.speed * dt
                move_y = dir_vec[1] * self.speed * dt

                # Move X
                temp = self.rect.copy()
                temp.x += move_x
                if temp.left < 0:
                    temp.left = 0
                if temp.right > WIDTH:
                    temp.right = WIDTH
                for br in block_rects:
                    if temp.colliderect(br):
                        if move_x > 0:
                            temp.right = br.left
                        elif move_x < 0:
                            temp.left = br.right
                self.rect.x = temp.x

                # Move Y
                temp = self.rect.copy()
                temp.y += move_y
                if temp.top < 0:
                    temp.top = 0
                if temp.bottom > HEIGHT:
                    temp.bottom = HEIGHT
                for br in block_rects:
                    if temp.colliderect(br):
                        if move_y > 0:
                            temp.bottom = br.top
                        elif move_y < 0:
                            temp.top = br.bottom
                self.rect.y = temp.y

        return bullet

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # Barrel
        cx, cy = self.rect.center
        dir_vec = DIRECTIONS[self.facing]
        end = (cx + dir_vec[0] * 20, cy + dir_vec[1] * 20)
        pygame.draw.line(screen, BLACK, (cx, cy), end, 5)
        if not self.alive:
            surf = pygame.Surface((32, 32), SRCALPHA)
            surf.fill((255, 0, 0, 128))
            screen.blit(surf, self.rect.topleft)

class Bullet:
    def __init__(self, pos, dir_vec, speed=500):
        offset = 25  # Start outside the tank
        start_x = pos[0] + dir_vec[0] * offset
        start_y = pos[1] + dir_vec[1] * offset
        self.pos = [start_x, start_y]
        self.dir = dir_vec
        self.speed = speed

    def update(self, dt):
        self.pos[0] += self.dir[0] * self.speed * dt
        self.pos[1] += self.dir[1] * self.speed * dt

    def draw(self, screen):
        pygame.draw.circle(screen, BLACK, (int(self.pos[0]), int(self.pos[1])), 5)

def bfs(start, goal, block_positions):
    grid = [[True] * COLS for _ in range(ROWS)]
    for r, c in block_positions:
        grid[r][c] = False
    q = queue.Queue()
    q.put([start])
    visited = set([start])
    while not q.empty():
        path = q.get()
        cur = path[-1]
        if cur == goal:
            return path
        for dr, dc in [(-1, 0), (1, 0), (0, -1), (0, 1)]:
            nr, nc = cur[0] + dr, cur[1] + dc
            if 0 <= nr < ROWS and 0 <= nc < COLS and grid[nr][nc] and (nr, nc) not in visited:
                visited.add((nr, nc))
                new_path = path + [(nr, nc)]
                q.put(new_path)
    return None

def check_los(p1, p2, block_positions):
    x0, y0 = p1
    x1, y1 = p2
    cells = get_line_cells(x0, y0, x1, y1)
    for row, col in cells:
        if (row, col) in block_positions:
            return False
    return True

def get_line_cells(x0, y0, x1, y1):
    cells = set()
    dx = abs(x1 - x0)
    dy = abs(y1 - y0)
    sx = 1 if x0 < x1 else -1
    sy = 1 if y0 < y1 else -1
    err = dx - dy
    while True:
        col = int(x0 // CELL_SIZE)
        row = int(y0 // CELL_SIZE)
        cells.add((row, col))
        if int(x0) == int(x1) and int(y0) == int(y1):
            break
        e2 = 2 * err
        if e2 > -dy:
            err -= dy
            x0 += sx
        if e2 < dx:
            err += dx
            y0 += sy
    return cells

def generate_blocks():
    block_positions = set()
    for r in range(ROWS):
        for c in range(COLS):
            if random.random() < 0.4:  # Less dense
                block_positions.add((r, c))
    # Clear spawn areas roughly
    block_positions.discard((ROWS - 1, 0))
    block_positions.discard((0, COLS - 1))
    return block_positions

def get_block_rect(bl):
    r, c = bl
    return pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tank Duel")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 48)
    small_font = pygame.font.SysFont(None, 24)

    level = 1
    player = None
    enemies = []
    block_positions = None
    bullets = []
    game_over = False
    winner = None

    def new_game(advance=False):
        nonlocal level, player, enemies, block_positions, bullets, game_over, winner
        if advance:
            level += 1
        block_positions = generate_blocks()
        player_pos = (CELL_SIZE / 2, HEIGHT - CELL_SIZE / 2)
        player = Tank(GREEN, player_pos, 'right')
        enemies = []
        num_enemies = 2 ** (level - 1)
        for _ in range(num_enemies):
            while True:
                ex = random.randint(1, COLS - 2) * CELL_SIZE + CELL_SIZE / 2
                ey = random.randint(0, ROWS // 2) * CELL_SIZE + CELL_SIZE / 2
                erect = pygame.Rect(ex - 16, ey - 16, 32, 32)
                collides = False
                for bl in block_positions:
                    if erect.colliderect(get_block_rect(bl)):
                        collides = True
                        break
                if not collides:
                    break
            enemies.append(Tank(ORANGE, (ex, ey), 'left', is_ai=True))
        bullets = []
        game_over = False
        winner = None

    new_game()

    running = True
    while running:
        dt = clock.tick(60) / 1000.0
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                if game_over and event.key == K_n:
                    new_game(advance=winner == 'player')
            if event.type == MOUSEBUTTONDOWN:
                if new_game_rect.collidepoint(event.pos):
                    level = 1
                    new_game()
                elif game_over and restart_rect.collidepoint(event.pos):
                    new_game(advance=winner == 'player')

        keys = pygame.key.get_pressed()

        if not game_over:
            block_rects = [get_block_rect(bl) for bl in block_positions]

            # Update player
            p_bullet = player.update(dt, keys, block_rects)
            if p_bullet:
                bullets.append(p_bullet)

            # Update enemies
            e_bullets = []
            for enemy in enemies:
                e_bullet = enemy.update_ai(dt, player, block_positions, block_rects)
                if e_bullet:
                    e_bullets.append(e_bullet)
            bullets.extend(e_bullets)

            # Update bullets
            for bullet in bullets[:]:
                bullet.update(dt)
                if not (0 < bullet.pos[0] < WIDTH and 0 < bullet.pos[1] < HEIGHT):
                    bullets.remove(bullet)
                    continue

                # Check blocks
                hit_block = False
                for bl in list(block_positions):
                    brect = get_block_rect(bl)
                    if brect.collidepoint(bullet.pos):
                        block_positions.remove(bl)
                        hit_block = True
                        break
                if hit_block:
                    bullets.remove(bullet)
                    continue

                # Check player
                if player.alive and player.rect.collidepoint(bullet.pos):
                    player.alive = False
                    bullets.remove(bullet)
                    game_over = True
                    winner = 'ai'
                    continue

                # Check enemies
                hit_enemy = False
                for enemy in enemies:
                    if enemy.alive and enemy.rect.collidepoint(bullet.pos):
                        enemy.alive = False
                        bullets.remove(bullet)
                        hit_enemy = True
                        if all(not e.alive for e in enemies):
                            game_over = True
                            winner = 'player'
                        break
                if hit_enemy:
                    continue

        # Draw
        screen.fill(GRAY)
        pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, HEIGHT), 2)

        # Blocks
        for bl in block_positions:
            rect = get_block_rect(bl)
            pygame.draw.rect(screen, DARK_GRAY, rect)

        # Tanks
        player.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)

        # Bullets
        for bullet in bullets:
            bullet.draw(screen)

        # HUD New Game button
        new_game_text = small_font.render("New Game", True, BLACK)
        new_game_rect = new_game_text.get_rect(center=(WIDTH / 2, 20))
        screen.blit(new_game_text, new_game_rect)

        if game_over:
            modal_surf = pygame.Surface((400, 200), SRCALPHA)
            modal_surf.fill((255, 255, 255, 200))
            title_text = font.render("GAME OVER", True, BLACK)
            modal_surf.blit(title_text, (100, 20))
            outcome = "You Win!" if winner == 'player' else "You Were Hit!"
            outcome_text = font.render(outcome, True, BLACK)
            modal_surf.blit(outcome_text, (100, 70))
            hint_text = small_font.render("Press N or click below to continue", True, BLACK)
            modal_surf.blit(hint_text, (100, 120))
            restart_text = small_font.render("Restart", True, BLACK)
            restart_rect_modal = restart_text.get_rect(center=(200, 160))
            modal_surf.blit(restart_text, restart_rect_modal)
            modal_pos = ((WIDTH - 400) / 2, (HEIGHT - 200) / 2)
            screen.blit(modal_surf, modal_pos)
            # Global restart rect for click
            restart_rect = restart_rect_modal.copy()
            restart_rect.topleft = (modal_pos[0] + restart_rect_modal.left, modal_pos[1] + restart_rect_modal.top)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()