import pygame
from pygame.locals import *
import sys
import random
import math

TILE_SIZE = 20
MAZE_WIDTH = 28
MAZE_HEIGHT = 31
SCREEN_WIDTH = MAZE_WIDTH * TILE_SIZE
SCREEN_HEIGHT = MAZE_HEIGHT * TILE_SIZE
COLOR_WALL = (0, 0, 255)
COLOR_PELLET = (255, 255, 255)
COLOR_POWER = (255, 255, 255)  # flashing
COLOR_PYMAN = (255, 255, 0)
COLOR_GHOST = {
    'blinky': (255, 0, 0),
    'pinky': (255, 192, 203),
    'inky': (0, 255, 255),
    'clyde': (255, 165, 0)
}
COLOR_FRIGHT = (0, 0, 139)
COLOR_EYES = (255, 255, 255)
COLOR_GATE = (255, 105, 180)
FPS = 30  # slower for simple

maze_str = """
############################
#............##............#
#.####.#####.##.#####.####.#
#.####.#####.##.#####.####.#
#.####.#####.##.#####.####.#
#..........................#
#.####.##.########.##.####.#
#.####.##.########.##.####.#
#......##....##....##......#
######.#####.##.#####.######
     #.#####.##.#####.#     
     #.##..........##.#     
     #.##.########.##.#     
######.##.#      #.##.######
         #        #         
######.##.#      #.##.######
     #.##.########.##.#     
     #.##..........##.#     
     #.##.########.##.#     
######.##.########.##.######
#............##............#
#.####.#####.##.#####.####.#
#.####.#####.##.#####.####.#
#...##................##...#
###.##.##.########.##.##.###
###.##.##.########.##.##.###
#......##....##....##......#
#.##########.##.##########.#
#.##########.##.##########.#
#..........................#
############################
""".strip()
lines = maze_str.split('\n')
maze = [list(line) for line in lines]

# Set power pellets
maze[1][1] = 'O'
maze[1][26] = 'O'
maze[26][1] = 'O'
maze[26][26] = 'O'

# Clear pen pellets
for y in range(10, 19):
    for x in range(8, 19):
        if maze[y][x] == '.':
            maze[y][x] = ' '

class Vector2:
    def __init__(self, x, y):
        self.x = float(x)
        self.y = float(y)

    def __add__(self, other):
        return Vector2(self.x + other.x, self.y + other.y)

    def __sub__(self, other):
        return Vector2(self.x - other.x, self.y - other.y)

    def __mul__(self, scalar):
        return Vector2(self.x * scalar, self.y * scalar)

    def __eq__(self, other):
        return self.x == other.x and self.y == other.y

    def __str__(self):
        return f"({self.x}, {self.y})"

    def clone(self):
        return Vector2(self.x, self.y)

directions = {
    'left': Vector2(-1, 0),
    'right': Vector2(1, 0),
    'up': Vector2(0, -1),
    'down': Vector2(0, 1)
}

priority = {
    'up': 0,
    'left': 1,
    'down': 2,
    'right': 3
}

def get_dir_name(d):
    for name, dd in directions.items():
        if dd.x == d.x and dd.y == d.y:
            return name

def get_tile(pos):
    return Vector2(int(pos.x // TILE_SIZE), int(pos.y // TILE_SIZE))

def get_pos(tile):
    return Vector2(tile.x * TILE_SIZE + TILE_SIZE // 2, tile.y * TILE_SIZE + TILE_SIZE // 2)

def is_intersection(tile):
    count = 0
    for d in directions.values():
        nt = tile + d
        if 0 <= nt.x < MAZE_WIDTH and 0 <= nt.y < MAZE_HEIGHT and maze[int(nt.y)][int(nt.x)] != '#':
            count += 1
    return count > 2

def get_possible_dirs(tile, current_dir, is_eaten=False):
    possible = []
    reverse = current_dir * -1
    for d in directions.values():
        if d == reverse:
            continue
        nt = tile + d
        if 0 <= nt.x < MAZE_WIDTH and 0 <= nt.y < MAZE_HEIGHT and maze[int(nt.y)][int(nt.x)] != '#' and not (not is_eaten and tile.y == 10 and tile.x in (13,14) and d.y > 0):
            possible.append(d)
    return possible

def distance(a, b):
    dx = a.x - b.x
    dy = a.y - b.y
    return (dx * dx + dy * dy) ** 0.5

class Player:
    def __init__(self):
        self.pos = get_pos(Vector2(14, 23))
        self.dir = Vector2(-1, 0)  # left
        self.next_dir = None
        self.speed = 3
        self.score = 0
        self.power = False
        self.power_timer = 0

    def update(self):
        if self.next_dir:
            tile = get_tile(self.pos)
            nt = tile + self.next_dir
            if maze[int(nt.y)][int(nt.x)] != '#' and not (int(nt.y) == 10 and int(nt.x) in (13,14)):
                self.dir = self.next_dir
                self.next_dir = None
        next_pos = self.pos + self.dir * self.speed
        next_tile = get_tile(next_pos)
        if maze[int(next_tile.y)][int(next_tile.x)] == '#' or (int(next_tile.y) == 10 and int(next_tile.x) in (13,14)):
            self.pos = get_pos(get_tile(self.pos))
        else:
            self.pos = next_pos
        if self.pos.x < 0:
            self.pos.x = SCREEN_WIDTH
        if self.pos.x > SCREEN_WIDTH:
            self.pos.x = 0
        tile = get_tile(self.pos)
        if maze[int(tile.y)][int(tile.x)] in ('.', 'O'):
            if maze[int(tile.y)][int(tile.x)] == 'O':
                self.score += 50
                self.power = True
                self.power_timer = 300
                global eaten_multiplier
                eaten_multiplier = 1
                for ghost in ghosts:
                    if ghost.mode != 'eaten':
                        ghost.previous_mode = ghost.mode
                        ghost.mode = 'frightened'
                        ghost.speed = 1.5
            else:
                self.score += 10
            maze[int(tile.y)][int(tile.x)] = ' '
            all_eaten = True
            for row in maze:
                if '.' in row or 'O' in row:
                    all_eaten = False
            if all_eaten:
                global state
                state = 'cleared'
        if self.power:
            self.power_timer -= 1
            if self.power_timer <= 0:
                self.power = False
                for ghost in ghosts:
                    if ghost.mode == 'frightened':
                        ghost.mode = ghost.previous_mode
                        ghost.speed = 2

    def draw(self, screen):
        radius = TILE_SIZE // 2
        mouth_open = (pygame.time.get_ticks() % 400) < 200
        angle = 60 if mouth_open else 20
        if self.dir.x == 1:  # right
            start_angle = -angle / 2
            end_angle = angle / 2 + 360
        elif self.dir.x == -1:  # left
            start_angle = 180 - angle / 2
            end_angle = 180 + angle / 2
        elif self.dir.y == -1:  # up
            start_angle = 90 - angle / 2
            end_angle = 90 + angle / 2
        elif self.dir.y == 1:  # down
            start_angle = 270 - angle / 2
            end_angle = 270 + angle / 2
        center = (int(self.pos.x) - radius, int(self.pos.y) - radius, radius * 2, radius * 2)
        pygame.draw.arc(screen, COLOR_PYMAN, center, math.radians(start_angle), math.radians(end_angle), width=radius)

class Ghost:
    def __init__(self, name, scatter_target):
        self.name = name
        self.color = COLOR_GHOST[name]
        self.pos = get_pos(Vector2(14, 11) if name == 'blinky' else Vector2(12, 14) if name == 'pinky' else Vector2(14, 14) if name == 'inky' else Vector2(16, 14))
        self.dir = Vector2(-1, 0) if name == 'blinky' else Vector2(0, -1)
        self.speed = 2
        self.mode = 'scatter' if name == 'blinky' else 'pen'
        self.previous_mode = None
        self.scatter_target = scatter_target
        self.target = Vector2(0, 0)
        self.release_timer = 0 if name == 'blinky' else 90 if name == 'pinky' else 180 if name == 'inky' else 270 if name == 'clyde' else 360

    def update(self):
        if self.mode == 'eaten':
            pen = Vector2(14, 10)
            if distance(self.pos, get_pos(pen)) < self.speed:
                self.pos = get_pos(Vector2(14, 14))
                self.mode = 'pen'
                self.release_timer = 0
                self.dir = Vector2(0, -1)
            else:
                direction = get_pos(pen) - self.pos
                length = distance(Vector2(0, 0), direction)
                if length > 0:
                    direction = direction * (1 / length)
                self.pos += direction * self.speed * 2
            return
        if self.mode == 'pen':
            self.release_timer -= 1
            if self.release_timer <= 0:
                self.target = Vector2(14, 11)
                if int(self.pos.x) % TILE_SIZE == TILE_SIZE // 2 and int(self.pos.y) % TILE_SIZE == TILE_SIZE // 2:
                    tile = get_tile(self.pos)
                    possible = get_possible_dirs(tile, self.dir, False)
                    if possible:
                        sorted_dirs = sorted(possible, key=lambda d: (distance(tile + d, self.target), priority[get_dir_name(d)]))
                        self.dir = sorted_dirs[0]
            else:
                next_pos = self.pos + self.dir * self.speed
                next_tile = get_tile(next_pos)
                if not (0 <= next_tile.x < MAZE_WIDTH and 0 <= next_tile.y < MAZE_HEIGHT) or maze[int(next_tile.y)][int(next_tile.x)] == '#' or (next_tile.y == 10 and next_tile.x in (13,14) and self.dir.y < 0):
                    self.dir = self.dir * -1
                    self.pos = get_pos(get_tile(self.pos))
                else:
                    self.pos = next_pos
            if distance(self.pos, get_pos(self.target)) < self.speed:
                self.mode = global_current_mode
                self.dir = Vector2(-1, 0)
            return
        p_tile = get_tile(player.pos)
        if self.mode == 'scatter':
            self.target = self.scatter_target
        elif self.mode == 'chase':
            if self.name == 'blinky':
                self.target = p_tile
            elif self.name == 'pinky':
                p_dir = player.dir
                self.target = p_tile + p_dir * 4
            elif self.name == 'inky':
                p_ahead = p_tile + player.dir * 2
                b_pos = get_tile(ghosts[0].pos)
                vect = p_ahead - b_pos
                self.target = b_pos + vect * 2
            elif self.name == 'clyde':
                dist = distance(get_tile(self.pos), p_tile)
                if dist < 8:
                    self.target = self.scatter_target
                else:
                    self.target = p_tile
        if int(self.pos.x) % TILE_SIZE == TILE_SIZE // 2 and int(self.pos.y) % TILE_SIZE == TILE_SIZE // 2:
            tile = get_tile(self.pos)
            if is_intersection(tile) or self.mode == 'frightened':
                possible = get_possible_dirs(tile, self.dir, self.mode == 'eaten')
                if possible:
                    if self.mode == 'frightened':
                        self.dir = random.choice(possible)
                    else:
                        sorted_dirs = sorted(possible, key=lambda d: (distance(tile + d, self.target), priority[get_dir_name(d)]))
                        self.dir = sorted_dirs[0]
        next_pos = self.pos + self.dir * self.speed
        next_tile = get_tile(next_pos)
        if maze[int(next_tile.y)][int(next_tile.x)] == '#' or (int(next_tile.y) == 10 and int(next_tile.x) in (13,14) and self.dir.y > 0 and self.mode != 'eaten'):
            self.pos = get_pos(get_tile(self.pos))
        else:
            self.pos = next_pos
        if self.pos.x < 0:
            self.pos.x = SCREEN_WIDTH
        if self.pos.x > SCREEN_WIDTH:
            self.pos.x = 0

    def draw(self, screen):
        if self.mode == 'frightened':
            if player.power_timer < 60 and player.power_timer % 20 < 10:
                color = (255, 255, 255)
            else:
                color = COLOR_FRIGHT
        elif self.mode == 'eaten':
            color = (0, 0, 0)
        else:
            color = self.color
        radius = TILE_SIZE // 2
        if self.mode != 'eaten':
            pygame.draw.circle(screen, color, (int(self.pos.x), int(self.pos.y)), radius)
        eye_radius = TILE_SIZE // 8
        pupil_radius = eye_radius // 2
        eye_offset = Vector2(TILE_SIZE // 4, TILE_SIZE // 4)
        left_eye = (int(self.pos.x) - eye_offset.x, int(self.pos.y) - eye_offset.y)
        right_eye = (int(self.pos.x) + eye_offset.x, int(self.pos.y) - eye_offset.y)
        pygame.draw.circle(screen, COLOR_EYES, left_eye, eye_radius)
        pygame.draw.circle(screen, COLOR_EYES, right_eye, eye_radius)
        pupil_offset = self.dir * (eye_radius - pupil_radius)
        left_pupil = (left_eye[0] + pupil_offset.x, left_eye[1] + pupil_offset.y)
        right_pupil = (right_eye[0] + pupil_offset.x, right_eye[1] + pupil_offset.y)
        pygame.draw.circle(screen, (0, 0, 0), left_pupil, pupil_radius)
        pygame.draw.circle(screen, (0, 0, 0), right_pupil, pupil_radius)

def draw_maze(screen):
    for y in range(MAZE_HEIGHT):
        for x in range(MAZE_WIDTH):
            if maze[y][x] == '#':
                pygame.draw.rect(screen, COLOR_WALL, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            elif maze[y][x] == '.':
                pygame.draw.circle(screen, COLOR_PELLET, (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2), 2)
            elif maze[y][x] == 'O':
                radius = 5 if pygame.time.get_ticks() % 500 < 250 else 4
                pygame.draw.circle(screen, COLOR_POWER, (x * TILE_SIZE + TILE_SIZE // 2, y * TILE_SIZE + TILE_SIZE // 2), radius)
    pygame.draw.line(screen, COLOR_GATE, (13 * TILE_SIZE, 10 * TILE_SIZE), (15 * TILE_SIZE, 10 * TILE_SIZE), 3)

def draw_hud(screen, score, high_score, lives, level):
    font = pygame.font.Font(None, 30)
    text = font.render(f"Score: {score}", True, (255, 255, 255))
    screen.blit(text, (10, 10))
    text = font.render(f"High: {high_score}", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH // 2 - 50, 10))
    text = font.render(f"Level: {level}", True, (255, 255, 255))
    screen.blit(text, (SCREEN_WIDTH - 100, 10))
    for i in range(lives):
        pygame.draw.circle(screen, COLOR_PYMAN, (30 + i * 30, SCREEN_HEIGHT - 20), TILE_SIZE // 2)

def reset_maze():
    global maze
    maze = [list(line) for line in lines]
    maze[1][1] = 'O'
    maze[1][26] = 'O'
    maze[26][1] = 'O'
    maze[26][26] = 'O'
    for y in range(10, 19):
        for x in range(8, 19):
            if maze[y][x] == '.':
                maze[y][x] = ' '
    maze[10][13] = ' '
    maze[10][14] = ' '
    # Make sides of gate walls to prevent invalid exits
    maze[10][12] = '#'
    maze[10][15] = '#'

def reset_positions():
    player.pos = get_pos(Vector2(14, 23))
    player.dir = Vector2(-1, 0)
    player.next_dir = None
    player.power = False
    player.power_timer = 0
    ghosts[0].pos = get_pos(Vector2(14, 11))
    ghosts[0].dir = Vector2(-1, 0)
    ghosts[0].mode = 'scatter'
    ghosts[0].release_timer = 0
    ghosts[1].pos = get_pos(Vector2(12, 14))
    ghosts[1].dir = Vector2(0, -1)
    ghosts[1].mode = 'pen'
    ghosts[1].release_timer = 90
    ghosts[2].pos = get_pos(Vector2(14, 14))
    ghosts[2].dir = Vector2(0, -1)
    ghosts[2].mode = 'pen'
    ghosts[2].release_timer = 180
    ghosts[3].pos = get_pos(Vector2(16, 14))
    ghosts[3].dir = Vector2(0, -1)
    ghosts[3].mode = 'pen'
    ghosts[3].release_timer = 270
    for g in ghosts:
        g.previous_mode = None
        g.speed = 2

def reset_level(preserve_pellets=False):
    if not preserve_pellets:
        reset_maze()
    reset_positions()

def main():
    pygame.init()
    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    clock = pygame.time.Clock()
    global player, ghosts, state, eaten_multiplier, global_current_mode
    player = Player()
    ghosts = [
        Ghost('blinky', Vector2(27, 0)),
        Ghost('pinky', Vector2(0, 0)),
        Ghost('inky', Vector2(27, 30)),
        Ghost('clyde', Vector2(0, 30))
    ]
    global_current_mode = 'scatter'
    reset_maze()
    reset_positions()
    state = 'start_screen'
    score = 0
    high_score = 0
    lives = 3
    level = 1
    pause = False
    timer = 0
    eaten_multiplier = 1
    game_timer = 0
    chase_scatter = [7, 20, 7, 20, 5, 20, 5, -1]  # seconds, -1 infinite
    cs_index = 0
    cs_timer = chase_scatter[0] * FPS
    while True:
        screen.fill((0, 0, 0))
        for event in pygame.event.get():
            if event.type == QUIT:
                sys.exit()
            if event.type == KEYDOWN:
                if event.key == K_ESCAPE:
                    sys.exit()
                if event.key == K_p:
                    pause = not pause
                if state == 'start_screen':
                    if event.key == K_RETURN:
                        reset_level(False)
                        state = 'level_start'
                        timer = 120
                if state == 'game_over':
                    if event.key == K_RETURN:
                        score = 0
                        lives = 3
                        level = 1
                        cs_index = 0
                        cs_timer = chase_scatter[0] * FPS
                        global_current_mode = 'scatter'
                        reset_level(False)
                        state = 'level_start'
                        timer = 120
                if event.key in (K_LEFT, K_a):
                    player.next_dir = directions['left']
                if event.key in (K_RIGHT, K_d):
                    player.next_dir = directions['right']
                if event.key in (K_UP, K_w):
                    player.next_dir = directions['up']
                if event.key in (K_DOWN, K_s):
                    player.next_dir = directions['down']
        if pause:
            pygame.display.flip()
            continue
        if state == 'start_screen':
            font = pygame.font.Font(None, 50)
            text = font.render("Py-Man", True, (255, 255, 0))
            screen.blit(text, (SCREEN_WIDTH // 2 - 100, SCREEN_HEIGHT // 2 - 100))
            text = font.render("Press Enter to Start", True, (255, 255, 255))
            screen.blit(text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2))
        elif state == 'level_start':
            timer -= 1
            if timer <= 0:
                state = 'gameplay'
            font = pygame.font.Font(None, 50)
            text = font.render("READY!", True, (255, 255, 0))
            screen.blit(text, (SCREEN_WIDTH // 2 - 80, SCREEN_HEIGHT // 2))
            draw_maze(screen)
            player.draw(screen)
            for g in ghosts:
                g.draw(screen)
            draw_hud(screen, score, high_score, lives, level)
        elif state == 'gameplay':
            game_timer += 1
            cs_timer -= 1
            if cs_timer <= 0:
                cs_index += 1
                if cs_index < len(chase_scatter):
                    cs_timer = chase_scatter[cs_index] * FPS if chase_scatter[cs_index] > 0 else 999999
                mode = 'scatter' if cs_index % 2 == 0 else 'chase'
                global_current_mode = mode
                for g in ghosts:
                    if g.mode not in ('frightened', 'eaten', 'pen'):
                        g.mode = global_current_mode
            player.update()
            for g in ghosts:
                g.update()
            for g in ghosts:
                if distance(player.pos, g.pos) < TILE_SIZE // 2:
                    if g.mode == 'frightened':
                        g.mode = 'eaten'
                        score += 200 * eaten_multiplier
                        eaten_multiplier *= 2
                    elif g.mode != 'eaten':
                        state = 'dying'
                        timer = 60
                        lives -= 1
                        break
            if not player.power:
                eaten_multiplier = 1
            draw_maze(screen)
            player.draw(screen)
            for g in ghosts:
                g.draw(screen)
            draw_hud(screen, score, high_score, lives, level)
        elif state == 'dying':
            timer -= 1
            if timer <= 0:
                if lives > 0:
                    reset_level(True)
                    state = 'level_start'
                    timer = 120
                else:
                    state = 'game_over'
            draw_maze(screen)
            for g in ghosts:
                g.draw(screen)
            draw_hud(screen, score, high_score, lives, level)
        elif state == 'cleared':
            timer += 1
            if timer % 30 < 15:
                wall_color = (255, 255, 255)
            else:
                wall_color = COLOR_WALL
            for y in range(MAZE_HEIGHT):
                for x in range(MAZE_WIDTH):
                    if maze[y][x] == '#':
                        pygame.draw.rect(screen, wall_color, (x * TILE_SIZE, y * TILE_SIZE, TILE_SIZE, TILE_SIZE))
            pygame.draw.line(screen, wall_color if wall_color == COLOR_WALL else (255, 255, 255), (13 * TILE_SIZE, 10 * TILE_SIZE), (15 * TILE_SIZE, 10 * TILE_SIZE), 3)
            if timer > 120:
                level += 1
                cs_index = 0
                cs_timer = chase_scatter[0] * FPS
                global_current_mode = 'scatter'
                reset_level(False)
                state = 'level_start'
                timer = 120
            draw_hud(screen, score, high_score, lives, level)
        elif state == 'game_over':
            font = pygame.font.Font(None, 50)
            text = font.render("GAME OVER", True, (255, 0, 0))
            screen.blit(text, (SCREEN_WIDTH // 2 - 150, SCREEN_HEIGHT // 2 - 50))
            text = font.render("Press Enter to Restart", True, (255, 255, 255))
            screen.blit(text, (SCREEN_WIDTH // 2 - 200, SCREEN_HEIGHT // 2))
            draw_hud(screen, score, high_score, lives, level)
        if score > high_score:
            high_score = score
        pygame.display.flip()
        clock.tick(FPS)

if __name__ == "__main__":
    main()