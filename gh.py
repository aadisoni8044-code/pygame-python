# Infinite procedural world (chunk-based) platformer with bullets, effects, enemies
# चलाने से पहले: pip install pygame
import pygame
import sys
import random
import math

pygame.init()

# Screen
WIDTH, HEIGHT = 900, 500
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("aadi")

clock = pygame.time.Clock()
FONT = pygame.font.SysFont(None, 28)

# Colors
GREEN = (50, 205, 50)
BLUE = (30, 144, 255)
RED = (200, 30, 30)
SKY = (135, 206, 250)
SPIKE_COLOR = (255, 80, 80)
ENEMY_COLOR = (150, 0, 150)
BULLET_COLOR = (255, 255, 0)
SPARK_COLOR = (255, 215, 0)
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)

# Player (screen-space x, but world position = scroll_x + player.x)
player = pygame.Rect(100, 300, 40, 50)
player_vel_y = 0
gravity = 0.6
speed = 5
jump_power = -12
on_ground = False
health = 3

# Camera world offset (how much world has scrolled to the right)
scroll_x = 0
score = 0

# Bullets and effects store world coordinates (absolute)
bullets = []   # each: {"rect": pygame.Rect(world_x, world_y, w,h), "vx": 10}
sparks = []    # each: [world_x, world_y, lifetime]

# Bullet cooldown
bullet_cooldown = 250
last_shot_time = 0

# Chunk system
CHUNK_WIDTH = 1600   # px per chunk (adjustable)
ACTIVE_RADIUS = 3    # how many chunks to keep on each side
WORLD_SEED = 12345   # deterministic seed base (change for different worlds)

# Entities are stored in chunks as lists; world coordinate rectangles used
# Chunk data structure: { "platforms": [...], "moving_platforms":[...], "enemies":[...], "gems":[...], "spikes":[...] }

chunks = {}  # key = chunk_index (int), value = chunk dict

# helper: get player's world_x
def player_world_x():
    return scroll_x + player.x

# deterministic random generator per chunk
def chunk_rng(chunk_index):
    return random.Random(WORLD_SEED + chunk_index)

# generate a chunk (deterministic)
def generate_chunk(ci):
    rng = chunk_rng(ci)
    base_x = ci * CHUNK_WIDTH
    chunk = {"platforms": [], "moving_platforms": [], "enemies": [], "gems": [], "spikes": []}

    # ground platform (very wide)
    ground = pygame.Rect(base_x, 460, CHUNK_WIDTH, 40)
    chunk["platforms"].append(ground)

    # add some static platforms (num depends on rng)
    num_plats = rng.randint(2, 6)
    for i in range(num_plats):
        w = rng.randint(100, 220)
        h = 20
        px = base_x + rng.randint(50, CHUNK_WIDTH - 200)
        py = rng.randint(220, 380)
        chunk["platforms"].append(pygame.Rect(px, py, w, h))

    # add some moving platforms
    num_moving = rng.randint(0, 3)
    for i in range(num_moving):
        w = rng.randint(100, 160)
        px = base_x + rng.randint(50, CHUNK_WIDTH - 200)
        py = rng.randint(200, 360)
        dir = rng.choice([-1, 1])
        range_min = px - rng.randint(50, 150)
        range_max = px + rng.randint(50, 150)
        # store as dict with movement params
        mp = {"rect": pygame.Rect(px, py, w, 16), "dir": dir, "range": (range_min, range_max), "speed": rng.uniform(0.6, 1.8)}
        chunk["moving_platforms"].append(mp)

    # add spikes
    num_spikes = rng.randint(0, 3)
    for i in range(num_spikes):
        sx = base_x + rng.randint(50, CHUNK_WIDTH - 40)
        spike = pygame.Rect(sx, 440, 30, 20)
        chunk["spikes"].append(spike)

    # add gems
    num_gems = rng.randint(1, 5)
    for i in range(num_gems):
        gx = base_x + rng.randint(50, CHUNK_WIDTH - 30)
        gy = rng.randint(200, 420)
        chunk["gems"].append(pygame.Rect(gx, gy, 12, 12))

    # add enemies
    num_enemies = rng.randint(0, 4)
    for i in range(num_enemies):
        ex = base_x + rng.randint(100, CHUNK_WIDTH - 100)
        ey = 420
        speed_e = rng.choice([1.0, 1.5, 2.0])
        patrol_min = ex - rng.randint(80, 180)
        patrol_max = ex + rng.randint(80, 180)
        aggressive = rng.random() < 0.5
        enemy = {"rect": pygame.Rect(ex, ey, 36, 36), "speed": speed_e, "range": (patrol_min, patrol_max), "aggressive": aggressive, "hp": rng.randint(1, 3)}
        chunk["enemies"].append(enemy)

    return chunk

# ensure chunk exists
def ensure_chunks_around(player_world_x_val):
    ci = int(math.floor(player_world_x_val / CHUNK_WIDTH))
    for c in range(ci - ACTIVE_RADIUS, ci + ACTIVE_RADIUS + 1):
        if c not in chunks:
            chunks[c] = generate_chunk(c)
    # cull distant chunks
    to_remove = []
    for cidx in list(chunks.keys()):
        if abs(cidx - ci) > (ACTIVE_RADIUS + 1):
            to_remove.append(cidx)
    for c in to_remove:
        del chunks[c]

# helpers to iterate all entities across active chunks
def iter_platforms():
    for c in chunks.values():
        for p in c["platforms"]:
            yield p
        for mp in c["moving_platforms"]:
            yield mp["rect"]

def iter_moving_platforms():
    for c in chunks.values():
        for mp in c["moving_platforms"]:
            yield mp

def iter_spikes():
    for c in chunks.values():
        for s in c["spikes"]:
            yield s

def iter_gems():
    for c in chunks.values():
        for g in c["gems"]:
            yield g

def iter_enemies():
    for c in chunks.values():
        for e in c["enemies"]:
            yield e

# movement and updates for moving platforms (work in world coords)
def update_moving_platforms():
    for c in chunks.values():
        for mp in c["moving_platforms"]:
            mp["rect"].x += mp["dir"] * mp["speed"]
            if mp["rect"].x < mp["range"][0] or mp["rect"].x > mp["range"][1]:
                mp["dir"] *= -1

# enemy AI update (world coords)
def update_enemies():
    pwx = player_world_x()
    for c in chunks.values():
        for e in c["enemies"]:
            # aggressive: if within detection range, move towards player
            if e["aggressive"] and abs(pwx - e["rect"].x) < 220:
                if pwx > e["rect"].x:
                    e["rect"].x += e["speed"]
                else:
                    e["rect"].x -= e["speed"]
            else:
                e["rect"].x += e["speed"]
                if e["rect"].x < e["range"][0] or e["rect"].x > e["range"][1]:
                    e["speed"] *= -1

# gravity and platform collision (player is screen-space rect but collides against world rects moved into screen space)
def apply_gravity_and_collide():
    global player_vel_y, on_ground
    player_vel_y += gravity
    player.y += player_vel_y
    on_ground = False
    # test collisions with all platforms (including moving ones)
    for p in iter_platforms():
        shifted = p.move(-scroll_x, 0)
        if player.colliderect(shifted) and player_vel_y > 0:
            player.bottom = shifted.top
            player_vel_y = 0
            on_ground = True

# move_player (updates player.x screen-space and scroll_x world offset similar to earlier approach)
def move_player(keys):
    global scroll_x
    if keys[pygame.K_LEFT]:
        player.x -= speed
    if keys[pygame.K_RIGHT]:
        player.x += speed
    # camera scroll behavior (center zone)
    if player.x > WIDTH * 0.6:
        scroll_x += speed
        player.x -= speed
    if player.x < WIDTH * 0.3 and scroll_x > 0:
        scroll_x -= speed
        player.x += speed

def try_jump(keys):
    global player_vel_y
    if keys[pygame.K_SPACE] and on_ground:
        player_vel_y = jump_power

# shooting (bullets stored in world coords)
def shoot(keys):
    global last_shot_time
    now = pygame.time.get_ticks()
    if keys[pygame.K_f] and now - last_shot_time > bullet_cooldown:
        # spawn bullet at player's world position
        wx = player_world_x() + player.width
        wy = player.y + player.height // 2
        rect = pygame.Rect(wx, wy, 10, 5)
        bullets.append({"rect": rect, "vx": 12})
        last_shot_time = now

# update bullets (world coords) with trails (sparks)
def update_bullets():
    for b in bullets[:]:
        b["rect"].x += b["vx"]
        # add small trail spark (limit count)
        if len(sparks) < 400:
            sparks.append([b["rect"].x, b["rect"].y + 2, 7])
        # cull bullet if far from player (to avoid storing forever)
        if abs(b["rect"].x - player_world_x()) > (CHUNK_WIDTH * (ACTIVE_RADIUS + 2)):
            bullets.remove(b)

# check collisions: bullets vs enemies, player vs enemies/spikes/gems
def collisions_and_game_logic():
    global score, health
    # bullets vs enemies
    for b in bullets[:]:
        for e in list(iter_enemies()):  # returns reference to enemy dict
            if b["rect"].colliderect(e["rect"]):
                # explosion sparks
                for _ in range(12):
                    if len(sparks) < 800:
                        sx = e["rect"].centerx + random.randint(-12, 12)
                        sy = e["rect"].centery + random.randint(-12, 12)
                        sparks.append([sx, sy, random.randint(6, 15)])
                # damage enemy
                e["hp"] -= 1
                try:
                    bullets.remove(b)
                except ValueError:
                    pass
                if e["hp"] <= 0:
                    # remove enemy from its chunk list
                    # find the chunk that contains this enemy
                    remove_enemy_from_chunks(e)
                    score += 5
                break

    # player vs gems
    for g in list(iter_gems()):
        if player.colliderect(g.move(-scroll_x, 0)):
            remove_gem_from_chunks(g)
            score += 2

    # player vs spikes
    for s in list(iter_spikes()):
        if player.colliderect(s.move(-scroll_x, 0)):
            # hit: reduce health and respawn or reset entirely if health 0
            health -= 1
            if health <= 0:
                reset_all()
            else:
                # respawn player to starting position (but keep chunks)
                respawn_player()
            break

    # player vs enemies (contact)
    for e in list(iter_enemies()):
        if player.colliderect(e["rect"].move(-scroll_x, 0)):
            health -= 1
            if health <= 0:
                reset_all()
            else:
                respawn_player()
            break

# helpers to remove entity from chunks (since iter_enemies yields references from chunk lists, but removal is easier by scanning)
def remove_enemy_from_chunks(enemy_obj):
    for c in chunks.values():
        if enemy_obj in c["enemies"]:
            c["enemies"].remove(enemy_obj)
            return

def remove_gem_from_chunks(gem_obj):
    for c in chunks.values():
        if gem_obj in c["gems"]:
            c["gems"].remove(gem_obj)
            return

# respawn player (preserve chunks/score/health > 0)
def respawn_player():
    global scroll_x
    player.x, player.y = 100, 300
    scroll_x = max(0, player_world_x() - 100)  # try to keep non-negative scroll

# full reset (health->3, score->0, clear chunks near player to regenerate)
def reset_all():
    global health, score, bullets, sparks, chunks, scroll_x
    health = 3
    score = 0
    bullets.clear()
    sparks.clear()
    chunks.clear()
    scroll_x = 0
    player.x, player.y = 100, 300

# update sparks (particle lifetimes)
def update_sparks():
    for s in sparks[:]:
        s[2] -= 1
        if s[2] <= 0:
            sparks.remove(s)

# draw everything (convert world coords to screen via -scroll_x)
def draw_all():
    screen.fill(SKY)
    # draw platforms (static and moving)
    for p in iter_platforms():
        screen_rect = p.move(-scroll_x, 0)
        pygame.draw.rect(screen, GREEN, screen_rect)
    # draw moving platforms overlay (thin)
    for mp in iter_moving_platforms():
        screen_rect = mp["rect"].move(-scroll_x, 0)
        pygame.draw.rect(screen, (40,160,40), screen_rect)

    # gems
    for g in iter_gems():
        screen_rect = g.move(-scroll_x, 0)
        pygame.draw.rect(screen, RED, screen_rect)

    # spikes
    for s in iter_spikes():
        sp = s.move(-scroll_x, 0)
        pygame.draw.polygon(screen, SPIKE_COLOR, [
            (sp.x, sp.y + sp.height),
            (sp.x + sp.width // 2, sp.y),
            (sp.x + sp.width, sp.y + sp.height)
        ])

    # enemies
    for e in iter_enemies():
        er = e["rect"].move(-scroll_x, 0)
        pygame.draw.rect(screen, ENEMY_COLOR, er)
        # HP bar
        hp_w = int(er.width * (e["hp"] / 3.0))
        pygame.draw.rect(screen, BLACK, (er.x, er.y - 6, er.width, 4))
        pygame.draw.rect(screen, (255,0,0), (er.x, er.y - 6, hp_w, 4))

    # bullets (world -> screen)
    for b in bullets:
        br = b["rect"].move(-scroll_x, 0)
        pygame.draw.rect(screen, BULLET_COLOR, br)

    # sparks (as small circles)
    for s in sparks:
        sx = int(s[0] - scroll_x)
        sy = int(s[1])
        # size depends on lifetime
        r = max(1, min(5, s[2] // 2))
        if 0 <= sx <= WIDTH+50 and 0 <= sy <= HEIGHT+50:
            pygame.draw.circle(screen, SPARK_COLOR, (sx, sy), r)

    # player
    pygame.draw.rect(screen, BLUE, player)

    # HUD
    hud_score = FONT.render(f"Score: {score}", True, WHITE)
    hud_health = FONT.render(f"Health: {health}", True, WHITE)
    hud_pos = FONT.render(f"World X: {int(player_world_x())}", True, WHITE)
    screen.blit(hud_score, (10, 10))
    screen.blit(hud_health, (10, 36))
    screen.blit(hud_pos, (10, 62))

    pygame.display.update()

# initial chunk ensure
ensure_chunks_around(player_world_x())

# GAME LOOP
running = True
while running:
    dt = clock.tick(60)
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    move_player(keys)
    try_jump(keys)
    shoot(keys)

    # ensure chunks around player (generate as needed)
    ensure_chunks_around(player_world_x())

    # updates
    update_moving_platforms()
    update_enemies()
    apply_gravity_and_collide()
    update_bullets()
    collisions_and_game_logic()
    update_sparks()

    draw_all()

pygame.quit()
sys.exit()
