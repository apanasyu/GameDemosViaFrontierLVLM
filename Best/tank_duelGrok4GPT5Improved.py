import pygame
from pygame.locals import *
import random
import queue
import math

# ---------------- Config ----------------
CELL_SIZE = 24           # smaller cell so 50x50 fits on most screens (1200x1200)
ROWS = 24
COLS = 24
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

# Gameplay tuning
PLAYER_SPEED = 220
ENEMY_SPEED = 120
AI_STANDOFF_DIST = 180        # enemies close in until this distance
AI_REPATH_TIME = 0.35
AI_FIRE_COOLDOWN = 1.0
PLAYER_FIRE_COOLDOWN = 0.12    # guard for key-repeat fire
BULLET_SPEED = 540

# Explosions
PLAYER_WEAPON_RADII = [10, 40, 150]  # two weapon options (toggle)
ENEMY_EXPLOSION_RADIUS = 5
EXPLOSION_DURATION = 0.45         # seconds, visual effect length
EXPLOSION_DAMAGE_APPLY_AT = 0.15  # seconds (apply damage early)

# --------------------------------------------------------
def clamp(v, a, b):
    return a if v < a else b if v > b else v

def dist(a, b):
    return math.hypot(a[0]-b[0], a[1]-b[1])

def circle_rect_overlap(cx, cy, radius, rect: pygame.Rect):
    nx = clamp(cx, rect.left, rect.right)
    ny = clamp(cy, rect.top, rect.bottom)
    dx = cx - nx
    dy = cy - ny
    return (dx*dx + dy*dy) <= (radius * radius)

def cell_from_pos(x, y):
    """Return (row, col) from pixel position, or None if out of bounds."""
    if 0 <= x < WIDTH and 0 <= y < HEIGHT:
        return int(y // CELL_SIZE), int(x // CELL_SIZE)
    return None

def cell_center(row, col):
    return (col * CELL_SIZE + CELL_SIZE * 0.5, row * CELL_SIZE + CELL_SIZE * 0.5)

class Tank:
    def __init__(self, color, pos, facing='right', is_ai=False):
        size = max(16, int(CELL_SIZE * 0.8))   # scale tank to cell size
        self.rect = pygame.Rect(0, 0, size, size)
        self.rect.center = (pos[0], pos[1])
        self.color = color
        self.facing = facing
        self.cooldown = 0
        self.alive = True
        self.is_ai = is_ai
        self.speed = ENEMY_SPEED if is_ai else PLAYER_SPEED
        self.path = None
        self.path_timer = 0

    @property
    def center(self):
        return (self.rect.centerx, self.rect.centery)

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
        # Normalize diagonal
        if dx != 0 and dy != 0:
            inv = 1.0 / math.hypot(dx, dy)
            dx *= inv * self.speed * dt
            dy *= inv * self.speed * dt

        # Move X
        temp = self.rect.copy()
        temp.x += dx
        temp.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        for br in block_rects:
            if temp.colliderect(br):
                if dx > 0: temp.right = br.left
                elif dx < 0: temp.left = br.right
        self.rect.x = temp.x

        # Move Y
        temp = self.rect.copy()
        temp.y += dy
        temp.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
        for br in block_rects:
            if temp.colliderect(br):
                if dy > 0: temp.bottom = br.top
                elif dy < 0: temp.top = br.bottom
        self.rect.y = temp.y

    def update_ai(self, dt, player, block_positions, block_rects):
        if not self.alive:
            return None
        self.cooldown -= dt
        self.path_timer -= dt

        my = self.center
        target = player.center
        d = dist(my, target)
        has_los = check_los(my, target, block_positions)

        # Face toward player
        dx = target[0] - my[0]
        dy = target[1] - my[1]
        if abs(dx) > abs(dy):
            self.facing = 'right' if dx > 0 else 'left'
        else:
            self.facing = 'down' if dy > 0 else 'up'

        # Move strategy
        want_advance = (d > AI_STANDOFF_DIST) or (not has_los)
        speed = self.speed
        move_x = 0
        move_y = 0

        if want_advance:
            if self.path_timer <= 0:
                start = (self.rect.centery // CELL_SIZE, self.rect.centerx // CELL_SIZE)
                goal = (player.rect.centery // CELL_SIZE, player.rect.centerx // CELL_SIZE)
                self.path = bfs(start, goal, block_positions)
                self.path_timer = AI_REPATH_TIME

            if self.path and len(self.path) > 1:
                next_cell = self.path[1]
                tx, ty = cell_center(next_cell[0], next_cell[1])
                vx = tx - my[0]
                vy = ty - my[1]
                mag = math.hypot(vx, vy)
                if mag > 1e-5:
                    vx /= mag
                    vy /= mag
                    move_x = vx * speed * dt
                    move_y = vy * speed * dt
                    if abs(vx) > abs(vy):
                        self.facing = 'right' if vx > 0 else 'left'
                    else:
                        self.facing = 'down' if vy > 0 else 'up'
                if mag < speed * dt * 1.2:
                    self.path = self.path[1:]
            else:
                mag = math.hypot(dx, dy)
                if mag > 1e-5:
                    move_x = (dx / mag) * speed * dt
                    move_y = (dy / mag) * speed * dt
        else:
            # light strafe
            if random.random() < 0.04:
                if abs(dx) + abs(dy) > 0:
                    sx, sy = -dy, dx
                    mag = math.hypot(sx, sy)
                    sx, sy = (sx / mag, sy / mag) if mag > 1e-5 else (0, 0)
                    self._strafe = (sx, sy, random.uniform(0.2, 0.5))
                else:
                    self._strafe = (0, 0, 0)
            if hasattr(self, "_strafe"):
                sx, sy, t = self._strafe
                move_x = sx * speed * 0.6 * dt
                move_y = sy * speed * 0.6 * dt
                self._strafe = (sx, sy, max(0.0, t - dt))
                if self._strafe[2] <= 0:
                    delattr(self, "_strafe")

        # Apply movement with collision
        if move_x or move_y:
            temp = self.rect.copy()
            temp.x += move_x
            temp.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            for br in block_rects:
                if temp.colliderect(br):
                    if move_x > 0: temp.right = br.left
                    elif move_x < 0: temp.left = br.right
            self.rect.x = temp.x

            temp = self.rect.copy()
            temp.y += move_y
            temp.clamp_ip(pygame.Rect(0, 0, WIDTH, HEIGHT))
            for br in block_rects:
                if temp.colliderect(br):
                    if move_y > 0: temp.bottom = br.top
                    elif move_y < 0: temp.top = br.bottom
            self.rect.y = temp.y

        # Fire logic
        bullet = None
        fire_ok = has_los or (random.random() < 0.15 and d < AI_STANDOFF_DIST * 1.2)
        if fire_ok and self.cooldown <= 0:
            dir_vec = DIRECTIONS[self.facing]
            bullet = Bullet(self.center, dir_vec, BULLET_SPEED, owner='ai')
            self.cooldown = AI_FIRE_COOLDOWN
        return bullet

    def draw(self, screen):
        pygame.draw.rect(screen, self.color, self.rect)
        # Barrel
        cx, cy = self.rect.center
        dir_vec = DIRECTIONS[self.facing]
        end = (cx + dir_vec[0] * int(CELL_SIZE * 0.6), cy + dir_vec[1] * int(CELL_SIZE * 0.6))
        pygame.draw.line(screen, BLACK, (cx, cy), end, max(2, CELL_SIZE // 12))
        if not self.alive:
            surf = pygame.Surface(self.rect.size, SRCALPHA)
            surf.fill((255, 0, 0, 128))
            screen.blit(surf, self.rect.topleft)

class Bullet:
    def __init__(self, pos, dir_vec, speed=BULLET_SPEED, owner='player'):
        offset = CELL_SIZE * 0.7
        start_x = pos[0] + dir_vec[0] * offset
        start_y = pos[1] + dir_vec[1] * offset
        self.pos = [start_x, start_y]
        self.dir = dir_vec
        self.speed = speed
        self.owner = owner

    def update(self, dt):
        self.pos[0] += self.dir[0] * self.speed * dt
        self.pos[1] += self.dir[1] * self.speed * dt

    def draw(self, screen):
        pygame.draw.circle(screen, BLACK, (int(self.pos[0]), int(self.pos[1])), max(3, CELL_SIZE // 8))

class Explosion:
    def __init__(self, pos, radius, duration=EXPLOSION_DURATION):
        self.pos = pos
        self.radius = radius
        self.duration = duration
        self.age = 0.0
        self.applied_damage = False
        self.spark_angles = [random.uniform(0, math.tau) for _ in range(18)]

    def update(self, dt):
        self.age += dt

    @property
    def done(self):
        return self.age >= self.duration

    def should_apply_damage(self):
        return (not self.applied_damage) and (self.age >= EXPLOSION_DAMAGE_APPLY_AT)

    def draw(self, screen):
        t = clamp(self.age / self.duration, 0.0, 1.0)
        R = int(self.radius * (0.6 + 0.6 * t))
        alpha = int(220 * (1.0 - t))
        surf = pygame.Surface((R*2+4, R*2+4), SRCALPHA)
        pygame.draw.circle(surf, (255, 200, 60, alpha), (R+2, R+2), int(R*0.7))
        pygame.draw.circle(surf, (255, 120, 20, alpha), (R+2, R+2), int(R*0.4))
        screen.blit(surf, (self.pos[0]-R-2, self.pos[1]-R-2))
        # rings
        for i in range(3):
            rr = int(self.radius * (0.35 + 0.25 * i + 0.4*t))
            pygame.draw.circle(screen, (255, 180, 40), (int(self.pos[0]), int(self.pos[1])), rr, 2)
        # sparks
        for ang in self.spark_angles:
            L = int(self.radius * (0.3 + 0.7 * t))
            x2 = int(self.pos[0] + math.cos(ang) * L)
            y2 = int(self.pos[1] + math.sin(ang) * L)
            pygame.draw.line(screen, (255, 230, 120), (int(self.pos[0]), int(self.pos[1])), (x2, y2), 2)

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
                q.put(path + [(nr, nc)])
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
        if 0 <= row < ROWS and 0 <= col < COLS:
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
    # lower density for big map so it doesn't choke paths
    density = 0.18
    for r in range(ROWS):
        for c in range(COLS):
            if random.random() < density:
                block_positions.add((r, c))
    # Clear spawn-ish areas (bottom-left, top-right)
    for rc in [(ROWS-1,0),(ROWS-2,0),(ROWS-1,1),(0,COLS-1),(1,COLS-1)]:
        block_positions.discard(rc)
    return block_positions

def get_block_rect(bl):
    r, c = bl
    return pygame.Rect(c * CELL_SIZE, r * CELL_SIZE, CELL_SIZE, CELL_SIZE)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Tank Duel — 50x50 + Click-to-Build")
    clock = pygame.time.Clock()
    font = pygame.font.SysFont(None, 44)
    small_font = pygame.font.SysFont(None, 22)

    level = 1
    player = None
    enemies = []
    block_positions = None
    bullets = []
    explosions = []
    game_over = False
    winner = None
    last_player_fire = 0.0
    player_weapon_idx = 0  # 0 => 88px, 1 => 188px

    def new_game(advance=False):
        nonlocal level, player, enemies, block_positions, bullets, explosions, game_over, winner, last_player_fire
        if advance:
            level += 1
        block_positions = generate_blocks()
        # spawn player bottom-left corner cell center
        player_pos = cell_center(ROWS - 1, 0)
        player = Tank(GREEN, player_pos, 'right')
        enemies = []
        num_enemies = 2 ** (level - 1)
        # cap enemies a bit for giant map sanity
        num_enemies = num_enemies = 2 ** (level - 1)
        for _ in range(num_enemies):
            while True:
                er = random.randint(0, ROWS // 2)
                ec = random.randint(COLS // 2, COLS - 1)
                ex, ey = cell_center(er, ec)
                erect = pygame.Rect(0, 0, int(CELL_SIZE*0.8), int(CELL_SIZE*0.8))
                erect.center = (ex, ey)
                collides = False
                for bl in block_positions:
                    if erect.colliderect(get_block_rect(bl)):
                        collides = True
                        break
                if not collides:
                    break
            t = Tank(ORANGE, (ex, ey), 'left', is_ai=True)
            t.speed = ENEMY_SPEED
            enemies.append(t)
        bullets = []
        explosions = []
        game_over = False
        winner = None
        last_player_fire = -999.0
        return player, enemies, block_positions, bullets, explosions, game_over, winner

    player, enemies, block_positions, bullets, explosions, game_over, winner = new_game()

    # Pre-created HUD rects
    new_game_rect = pygame.Rect(WIDTH // 2 - 60, 6, 120, 24)
    weapon_rect = pygame.Rect(WIDTH // 2 + 120, 6, 180, 24)
    restart_rect = pygame.Rect(0, 0, 1, 1)

    running = True
    while running:
        dt_ms = clock.tick(60)
        dt = dt_ms / 1000.0
        for event in pygame.event.get():
            if event.type == QUIT:
                running = False
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    running = False
                if event.key == K_SPACE and not game_over and player.alive:
                    # Fire (guard repeat)
                    now = pygame.time.get_ticks() / 1000.0
                    if now - last_player_fire >= PLAYER_FIRE_COOLDOWN:
                        dir_vec = DIRECTIONS[player.facing]
                        bullets.append(Bullet(player.center, dir_vec, BULLET_SPEED, owner='player'))
                        last_player_fire = now
                if event.key == K_t:
                    player_weapon_idx = (player_weapon_idx + 1) % len(PLAYER_WEAPON_RADII)
                if game_over and event.key == K_n:
                    player, enemies, block_positions, bullets, explosions, game_over, winner = new_game(advance=(winner == 'player'))

            if event.type == MOUSEBUTTONDOWN and event.button == 1:
                mx, my = event.pos
                # HUD clicks
                if new_game_rect.collidepoint(event.pos):
                    level = 1
                    player, enemies, block_positions, bullets, explosions, game_over, winner = new_game()
                    continue
                if weapon_rect.collidepoint(event.pos):
                    player_weapon_idx = 1 - player_weapon_idx
                    continue
                if game_over and restart_rect.collidepoint(event.pos):
                    player, enemies, block_positions, bullets, explosions, game_over, winner = new_game(advance=(winner == 'player'))
                    continue

                # --- NEW: click-to-build block ---
                cell = cell_from_pos(mx, my)
                if cell:
                    r, c = cell
                    # Only if space empty (no block) and no tank occupies that cell
                    if (r, c) not in block_positions:
                        cell_rect = get_block_rect((r, c))
                        occupied = False
                        if player.rect.colliderect(cell_rect):
                            occupied = True
                        else:
                            for e in enemies:
                                if e.rect.colliderect(cell_rect):
                                    occupied = True
                                    break
                        if not occupied:
                            block_positions.add((r, c))
                # ----------------------------------

        keys = pygame.key.get_pressed()

        if not game_over:
            block_rects = [get_block_rect(bl) for bl in block_positions]

            # Player movement
            player.update(dt, keys, block_rects)

            # Enemy AI
            e_bullets = []
            for enemy in enemies:
                e_bullet = enemy.update_ai(dt, player, block_positions, block_rects)
                if e_bullet:
                    e_bullets.append(e_bullet)
            bullets.extend(e_bullets)

            # Bullets -> explosions
            for bullet in bullets[:]:
                bullet.update(dt)
                x, y = bullet.pos
                out = not (0 < x < WIDTH and 0 < y < HEIGHT)

                exploded = False
                # Hit block?
                if not exploded:
                    for bl in list(block_positions):
                        if get_block_rect(bl).collidepoint(bullet.pos):
                            radius = PLAYER_WEAPON_RADII[player_weapon_idx] if bullet.owner == 'player' else ENEMY_EXPLOSION_RADIUS
                            explosions.append(Explosion((x, y), radius))
                            exploded = True
                            break
                # Hit player?
                if not exploded and player.alive and player.rect.collidepoint(bullet.pos) and bullet.owner == 'ai':
                    explosions.append(Explosion((x, y), ENEMY_EXPLOSION_RADIUS))
                    exploded = True

                # Hit enemy?
                if not exploded and bullet.owner == 'player':
                    for enemy in enemies:
                        if enemy.alive and enemy.rect.collidepoint(bullet.pos):
                            explosions.append(Explosion((x, y), PLAYER_WEAPON_RADII[player_weapon_idx]))
                            exploded = True
                            break

                # Out of bounds -> explode
                if out and not exploded:
                    radius = PLAYER_WEAPON_RADII[player_weapon_idx] if bullet.owner == 'player' else ENEMY_EXPLOSION_RADIUS
                    explosions.append(Explosion((x, y), radius))
                    exploded = True

                if exploded:
                    bullets.remove(bullet)

            # Explosions effects
            for ex in explosions[:]:
                ex.update(dt)
                if ex.should_apply_damage():
                    # destroy blocks in radius
                    for bl in list(block_positions):
                        if circle_rect_overlap(ex.pos[0], ex.pos[1], ex.radius, get_block_rect(bl)):
                            block_positions.remove(bl)
                    # damage player
                    if player.alive and circle_rect_overlap(ex.pos[0], ex.pos[1], ex.radius, player.rect):
                        player.alive = False
                        game_over = True
                        winner = 'ai'
                    # damage enemies
                    for enemy in enemies:
                        if enemy.alive and circle_rect_overlap(ex.pos[0], ex.pos[1], ex.radius, enemy.rect):
                            enemy.alive = False
                    # win check
                    if not game_over and all(not e.alive for e in enemies):
                        game_over = True
                        winner = 'player'
                    ex.applied_damage = True
                if ex.done:
                    explosions.remove(ex)

        # ---------------- Draw ----------------
        screen.fill(GRAY)
        pygame.draw.rect(screen, BLACK, (0, 0, WIDTH, HEIGHT), 2)

        # Blocks
        for bl in block_positions:
            pygame.draw.rect(screen, DARK_GRAY, get_block_rect(bl))

        # Tanks
        player.draw(screen)
        for enemy in enemies:
            enemy.draw(screen)

        # Bullets
        for bullet in bullets:
            bullet.draw(screen)

        # Explosions
        for ex in explosions:
            ex.draw(screen)

        # HUD: New Game
        new_game_text = small_font.render("New Game", True, BLACK)
        new_game_rect = new_game_text.get_rect(center=(WIDTH / 2, 14))
        pygame.draw.rect(screen, WHITE, new_game_rect.inflate(16, 6))
        pygame.draw.rect(screen, BLACK, new_game_rect.inflate(16, 6), 2)
        screen.blit(new_game_text, new_game_rect)

        # HUD: Weapon toggle
        weapon_label = f"Weapon: {PLAYER_WEAPON_RADII[player_weapon_idx]}px (T)"
        weapon_text = small_font.render(weapon_label, True, BLACK)
        weapon_rect = weapon_text.get_rect(midleft=(new_game_rect.right + 60, 14))
        bg = weapon_rect.inflate(16, 6)
        pygame.draw.rect(screen, WHITE, bg)
        pygame.draw.rect(screen, BLACK, bg, 2)
        screen.blit(weapon_text, weapon_rect)

        if game_over:
            modal_w, modal_h = 420, 220
            modal_surf = pygame.Surface((modal_w, modal_h), SRCALPHA)
            modal_surf.fill((255, 255, 255, 220))
            title_text = font.render("GAME OVER", True, BLACK)
            modal_surf.blit(title_text, (110, 20))
            outcome = "You Win!" if winner == 'player' else "You Were Hit!"
            outcome_text = pygame.font.SysFont(None, 32).render(outcome, True, BLACK)
            modal_surf.blit(outcome_text, (110, 80))
            hint_text = small_font.render("Press N or click below to continue", True, BLACK)
            modal_surf.blit(hint_text, (70, 120))
            restart_text = small_font.render("Restart", True, BLACK)
            restart_rect_modal = restart_text.get_rect(center=(modal_w // 2, 170))
            modal_surf.blit(restart_text, restart_rect_modal)
            modal_pos = ((WIDTH - modal_w) / 2, (HEIGHT - modal_h) / 2)
            screen.blit(modal_surf, modal_pos)
            # Global restart rect for click
            restart_rect = restart_rect_modal.copy()
            restart_rect.topleft = (modal_pos[0] + restart_rect_modal.left, modal_pos[1] + restart_rect_modal.top)

        pygame.display.flip()

    pygame.quit()

if __name__ == "__main__":
    main()
