import pygame
import random
from collections import deque
from math import copysign

# -----------------------------
# Config / Constants
# -----------------------------
CELL = 64
ROWS, COLS = 7, 12
ARENA_W, ARENA_H = COLS * CELL, ROWS * CELL
HUD_H = 56
SCREEN_W, SCREEN_H = ARENA_W, ARENA_H + HUD_H
FPS = 60

# Colors
BG = (238, 238, 238)
INK = (40, 40, 40)
FRAME = (30, 30, 30)
GREEN = (41, 167, 69)
ORANGE = (245, 130, 32)
RED = (220, 40, 40)
WHITE = (255, 255, 255)

# Gameplay
PLAYER_SPEED = 3.0
AI_SPEED = 2.6
TANK_SIZE = int(CELL * 0.66)  # square body
BARREL_LEN = int(TANK_SIZE * 0.65)
BULLET_SPEED = 8
BULLET_RADIUS = 6
FIRE_COOLDOWN_MS = 420
AI_FIRE_COOLDOWN_MS = 520
AI_PATHFIND_MS = 250
AI_WANDER_MS = 600
BLOCK_PROB = 0.28  # chance a cell becomes a block
SEED_NONE = None  # set int to get reproducible maps


# -----------------------------
# Helpers
# -----------------------------
def grid_to_px(cell):
    r, c = cell
    return c * CELL, HUD_H + r * CELL


def px_to_grid(px):
    """Return (row, col) as INTS, already clamped to grid."""
    x, y = px
    y -= HUD_H
    r = int(y // CELL)
    c = int(x // CELL)
    if r < 0: r = 0
    if c < 0: c = 0
    if r >= ROWS: r = ROWS - 1
    if c >= COLS: c = COLS - 1
    return r, c


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


def rect_from_cell(r, c):
    x, y = grid_to_px((r, c))
    return pygame.Rect(x, y, CELL, CELL)


def los_clear_same_row_or_col(a_center, b_center, blocks):
    """Cardinal LOS only: True if same row/col and no blocks in between."""
    ar, ac = px_to_grid(a_center)
    br, bc = px_to_grid(b_center)
    if ar == br:
        cmin, cmax = sorted((ac, bc))
        for c in range(cmin + 1, cmax):
            if blocks[ar][c]:
                return False
        return True
    if ac == bc:
        rmin, rmax = sorted((ar, br))
        for r in range(rmin + 1, rmax):
            if blocks[r][ac]:
                return False
        return True
    return False


def build_solid_rects(blocks):
    rects = []
    for r in range(ROWS):
        for c in range(COLS):
            if blocks[r][c]:
                rects.append(rect_from_cell(r, c))
    # Outer frame walls
    rects.append(pygame.Rect(0, HUD_H, ARENA_W, 2))  # top
    rects.append(pygame.Rect(0, HUD_H + ARENA_H - 2, ARENA_W, 2))  # bottom
    rects.append(pygame.Rect(0, HUD_H, 2, ARENA_H))  # left
    rects.append(pygame.Rect(ARENA_W - 2, HUD_H, 2, ARENA_H))  # right
    return rects


def aabb_move_and_collide(rect, dx, dy, solids):
    """Move rect by dx, dy, collide against solids (axis separated)."""
    rect.x += dx
    for s in solids:
        if rect.colliderect(s):
            if dx > 0:
                rect.right = s.left
            elif dx < 0:
                rect.left = s.right
    rect.y += dy
    for s in solids:
        if rect.colliderect(s):
            if dy > 0:
                rect.bottom = s.top
            elif dy < 0:
                rect.top = s.bottom
    return rect


def bfs_path(blocks, start_cell, goal_cell):
    """BFS on grid of free cells; returns list of cells start->goal (inclusive)."""
    if start_cell == goal_cell:
        return [start_cell]
    def free(r, c):
        return 0 <= r < ROWS and 0 <= c < COLS and not blocks[r][c]
    q = deque([start_cell])
    parent = {start_cell: None}
    while q:
        r, c = q.popleft()
        for dr, dc in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            nr, nc = r + dr, c + dc
            if free(nr, nc) and (nr, nc) not in parent:
                parent[(nr, nc)] = (r, c)
                if (nr, nc) == goal_cell:
                    path = [(nr, nc)]
                    cur = (nr, nc)
                    while parent[cur] is not None:
                        cur = parent[cur]
                        path.append(cur)
                    path.reverse()
                    return path
                q.append((nr, nc))
    return []


# -----------------------------
# Entities
# -----------------------------
class Bullet:
    def __init__(self, x, y, dir_vec):
        self.pos = pygame.Vector2(x, y)
        self.dir = pygame.Vector2(dir_vec).normalize()
        self.alive = True

    def update(self, dt, blocks, tanks):
        if not self.alive:
            return
        step = self.dir * BULLET_SPEED
        self.pos.x += step.x
        self.pos.y += step.y

        # Out of arena?
        if not (0 <= self.pos.x <= ARENA_W) or not (HUD_H <= self.pos.y <= HUD_H + ARENA_H):
            self.alive = False
            return

        # Hit a block?
        r, c = px_to_grid(self.pos)  # already ints & clamped
        if blocks[r][c]:
            blocks[r][c] = 0  # destroy block
            self.alive = False
            return

        # Hit a tank?
        for t in tanks:
            if t.alive and t.rect.inflate(-8, -8).collidepoint(self.pos.x, self.pos.y):
                t.alive = False
                self.alive = False
                return

    def draw(self, surf):
        if self.alive:
            pygame.draw.circle(surf, INK, (int(self.pos.x), int(self.pos.y)), BULLET_RADIUS)


class Tank:
    def __init__(self, x, y, color, speed):
        self.color = color
        self.rect = pygame.Rect(0, 0, TANK_SIZE, TANK_SIZE)
        self.rect.center = (x, y)
        self.speed = speed
        self.facing = pygame.Vector2(1, 0)  # right by default
        self.alive = True
        self.last_fire = 0

    def can_fire(self, now, cooldown_ms):
        return now - self.last_fire >= cooldown_ms and self.alive

    def fire(self, now):
        self.last_fire = now
        cx, cy = self.rect.center
        tip = pygame.Vector2(cx, cy) + self.facing * (TANK_SIZE // 2 + 10)
        return Bullet(tip.x, tip.y, self.facing)

    def draw(self, surf, destroyed_overlay=False):
        pygame.draw.rect(surf, self.color, self.rect, border_radius=10)
        cx, cy = self.rect.center
        end = (int(cx + self.facing.x * BARREL_LEN), int(cy + self.facing.y * BARREL_LEN))
        pygame.draw.line(surf, INK, (cx, cy), end, 6)
        if destroyed_overlay:
            overlay = pygame.Surface(self.rect.size, pygame.SRCALPHA)
            overlay.fill((*RED, 120))
            surf.blit(overlay, self.rect.topleft)


# -----------------------------
# Game
# -----------------------------
class Game:
    def __init__(self):
        self.screen = pygame.display.set_mode((SCREEN_W, SCREEN_H))
        pygame.display.set_caption("Tank Duel")
        self.clock = pygame.time.Clock()
        self.font = pygame.font.SysFont("arial", 20)
        self.big = pygame.font.SysFont("arial", 42, bold=True)
        self.state = "RUNNING"  # or "GAME_OVER"
        self.outcome = ""       # "You Win!" or "You Were Hit!"
        self.seed = SEED_NONE
        self.new_game_button = pygame.Rect(SCREEN_W // 2 - 70, 10, 140, HUD_H - 20)
        self._init_round()

        # AI helpers
        self.ai_path = []
        self.ai_next_path_time = 0
        self.ai_wander_until = 0

    # ----- Setup -----
    def _init_round(self):
        if self.seed is None:
            random.seed()
        else:
            random.seed(self.seed)

        # Blocks
        self.blocks = [[0 for _ in range(COLS)] for _ in range(ROWS)]
        for r in range(ROWS):
            for c in range(COLS):
                if random.random() < BLOCK_PROB:
                    self.blocks[r][c] = 1

        # Clear spawn corridors (bottom-left & top-right)
        for r in range(ROWS - 2, ROWS):
            for c in range(0, 2):
                self.blocks[r][c] = 0
        for r in range(0, 2):
            for c in range(COLS - 2, COLS):
                self.blocks[r][c] = 0

        # Tanks
        p_spawn = rect_from_cell(ROWS - 1, 0).center
        a_spawn = rect_from_cell(0, COLS - 1).center
        self.player = Tank(*p_spawn, GREEN, PLAYER_SPEED)
        self.ai = Tank(*a_spawn, ORANGE, AI_SPEED)
        self.player.facing = pygame.Vector2(1, 0)
        self.ai.facing = pygame.Vector2(-1, 0)

        # Bullets
        self.bullets = []

        # State
        self.state = "RUNNING"
        self.outcome = ""

    # ----- Input -----
    def handle_inputs(self):
        keys = pygame.key.get_pressed()
        move = pygame.Vector2(0, 0)
        # Player movement
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            move.x -= 1
            self.player.facing = pygame.Vector2(-1, 0)
        if keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            move.x += 1
            self.player.facing = pygame.Vector2(1, 0)
        if keys[pygame.K_UP] or keys[pygame.K_w]:
            move.y -= 1
            self.player.facing = pygame.Vector2(0, -1)
        if keys[pygame.K_DOWN] or keys[pygame.K_s]:
            move.y += 1
            self.player.facing = pygame.Vector2(0, 1)

        if move.length_squared() > 0:
            move = move.normalize() * self.player.speed
        solids = build_solid_rects(self.blocks)
        self.player.rect = aabb_move_and_collide(self.player.rect, move.x, move.y, solids)

    # ----- Update -----
    def update(self, dt):
        now = pygame.time.get_ticks()
        solids = build_solid_rects(self.blocks)

        # Player fire
        pressed = pygame.key.get_pressed()
        if pressed[pygame.K_SPACE] and self.player.can_fire(now, FIRE_COOLDOWN_MS):
            self.bullets.append(self.player.fire(now))

        # AI logic
        if self.ai.alive and self.player.alive:
            self.ai_logic(now, solids)

        # Bullets update
        for b in self.bullets:
            b.update(dt, self.blocks, [self.player, self.ai])
        self.bullets = [b for b in self.bullets if b.alive]

        # Check end conditions
        if self.state == "RUNNING":
            if not self.player.alive and not self.ai.alive:
                self.state = "GAME_OVER"
                self.outcome = "Trade! Both tanks destroyed."
            elif not self.player.alive:
                self.state = "GAME_OVER"
                self.outcome = "You Were Hit!"
            elif not self.ai.alive:
                self.state = "GAME_OVER"
                self.outcome = "You Win!"

    def ai_logic(self, now, solids):
        # Update AI facing toward player (axis preference toward the larger delta)
        pc = pygame.Vector2(self.player.rect.center)
        ac = pygame.Vector2(self.ai.rect.center)
        delta = pc - ac
        if abs(delta.x) > abs(delta.y):
            self.ai.facing = pygame.Vector2(copysign(1, delta.x), 0)
        else:
            self.ai.facing = pygame.Vector2(0, copysign(1, delta.y))

        # If cardinal LOS is clear and aligned, shoot with cooldown
        pr, pcg = px_to_grid(pc)
        ar, acg = px_to_grid(ac)
        aligned_cardinal = (pr == ar) or (pcg == acg)
        if aligned_cardinal and los_clear_same_row_or_col(self.ai.rect.center, self.player.rect.center, self.blocks):
            if self.ai.can_fire(now, AI_FIRE_COOLDOWN_MS):
                # Face exactly toward the axis of fire
                if ar == pr:
                    self.ai.facing = pygame.Vector2(1 if pcg > acg else -1, 0)
                else:
                    self.ai.facing = pygame.Vector2(0, 1 if pr > ar else -1)
                self.bullets.append(self.ai.fire(now))
            move_vec = pygame.Vector2(0, 0)  # hold position to take shot
        else:
            # Need to navigate using BFS toward player's cell
            if now >= self.ai_next_path_time:
                start = px_to_grid(self.ai.rect.center)
                goal = px_to_grid(self.player.rect.center)
                self.ai_path = bfs_path(self.blocks, start, goal)
                self.ai_next_path_time = now + AI_PATHFIND_MS

            move_vec = pygame.Vector2(0, 0)
            if len(self.ai_path) >= 2:
                # move toward the next cell center
                _, nxt = self.ai_path[0], self.ai_path[1]
                nx, ny = rect_from_cell(*nxt).center
                aim = pygame.Vector2(nx, ny) - pygame.Vector2(self.ai.rect.center)
                if aim.length_squared() > 0:
                    move_vec = aim.normalize() * self.ai.speed
            else:
                # wander a bit if no path
                if now > self.ai_wander_until:
                    dirs = [pygame.Vector2(1, 0), pygame.Vector2(-1, 0),
                            pygame.Vector2(0, 1), pygame.Vector2(0, -1)]
                    self.ai.facing = random.choice(dirs)
                    self.ai_wander_until = now + AI_WANDER_MS
                move_vec = self.ai.facing * (self.ai.speed * 0.75)

        # Move AI with collisions
        self.ai.rect = aabb_move_and_collide(self.ai.rect, move_vec.x, move_vec.y, solids)

    # ----- Draw -----
    def draw(self):
        self.screen.fill(BG)
        # HUD
        pygame.draw.rect(self.screen, WHITE, (0, 0, SCREEN_W, HUD_H))
        pygame.draw.rect(self.screen, FRAME, self.new_game_button, width=2, border_radius=10)
        label = self.font.render("New Game", True, FRAME)
        self.screen.blit(label, (self.new_game_button.centerx - label.get_width() // 2,
                                 self.new_game_button.centery - label.get_height() // 2))

        # Arena frame
        pygame.draw.rect(self.screen, FRAME, (0, HUD_H, ARENA_W, ARENA_H), width=2)

        # Grid blocks
        for r in range(ROWS):
            for c in range(COLS):
                if self.blocks[r][c]:
                    cell_rect = rect_from_cell(r, c).inflate(-8, -8)
                    pygame.draw.rect(self.screen, INK, cell_rect, border_radius=6)

        # Bullets
        for b in self.bullets:
            b.draw(self.screen)

        # Tanks
        self.player.draw(self.screen, destroyed_overlay=not self.player.alive)
        self.ai.draw(self.screen, destroyed_overlay=not self.ai.alive)

        # Modal on game over
        if self.state == "GAME_OVER":
            self.draw_modal()

        pygame.display.flip()

    def draw_modal(self):
        w, h = 520, 220
        rx = (SCREEN_W - w) // 2
        ry = HUD_H + (ARENA_H - h) // 2
        # panel
        pygame.draw.rect(self.screen, WHITE, (rx, ry, w, h), border_radius=12)
        pygame.draw.rect(self.screen, FRAME, (rx, ry, w, h), width=2, border_radius=12)

        title = self.big.render("GAME OVER", True, FRAME)
        self.screen.blit(title, (rx + (w - title.get_width()) // 2, ry + 18))

        outcome = self.font.render(self.outcome, True, FRAME)
        self.screen.blit(outcome, (rx + (w - outcome.get_width()) // 2, ry + 90))

        hint = self.font.render("Press N or click New Game to restart", True, FRAME)
        self.screen.blit(hint, (rx + (w - hint.get_width()) // 2, ry + 130))

    # ----- Events -----
    def handle_event(self, e):
        if e.type == pygame.MOUSEBUTTONDOWN and e.button == 1:
            if self.new_game_button.collidepoint(e.pos):
                self._init_round()
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_n:
                self._init_round()
            if e.key == pygame.K_ESCAPE:
                pygame.event.post(pygame.event.Event(pygame.QUIT))

    # ----- Loop -----
    def run(self):
        running = True
        while running:
            dt = self.clock.tick(FPS)
            for e in pygame.event.get():
                if e.type == pygame.QUIT:
                    running = False
                else:
                    self.handle_event(e)

            if self.state == "RUNNING":
                self.handle_inputs()
                self.update(dt)

            self.draw()


def main():
    pygame.init()
    try:
        Game().run()
    finally:
        pygame.quit()


if __name__ == "__main__":
    main()
