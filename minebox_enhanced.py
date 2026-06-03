import pygame
import math
import socket
import threading
import json
import uuid
import os

pygame.init()

# ---------------- SCREEN ----------------
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("MineBox Enhanced - Multiplayer")

# ---------------- SETTINGS ----------------
FOV = math.pi / 3
RAYS = 120
MAX_DEPTH = 400
TILE = 64

# ---------------- PATH ----------------
BASE = os.path.dirname(__file__)

def load_tex(name, fallback):
    try:
        path = os.path.join(BASE, "assets", name)
        img = pygame.image.load(path).convert_alpha()
        return pygame.transform.scale(img, (64, 64))
    except:
        surf = pygame.Surface((64, 64))
        surf.fill(fallback)
        return surf

# ---------------- TEXTURES ----------------
wall_tex = load_tex("wall.png", (120,120,120))
grass_tex = load_tex("grass.png", (80,200,90))
wood_tex = load_tex("wood.png", (139,90,40))

# ---------------- LAN ----------------
SERVER_IP = "127.0.0.1"
PORT = 5555

sock = None
players = {}
villagers = {}
world = {}
pid = str(uuid.uuid4())

# Player state
px, py = 100, 100
pa = 0
speed = 3
health = 100
max_health = 100
current_dimension = "overworld"  # overworld, nether, end
inventory = {}  # {block_type: count}
selected_block = 0

def lan_start():
    global sock
    sock = socket.socket()
    sock.connect((SERVER_IP, PORT))

    def recv():
        global players, villagers, world, health
        while True:
            try:
                data = sock.recv(4096).decode()
                if data:
                    msg = json.loads(data)
                    players = msg.get("players", {})
                    villagers = msg.get("villagers", {})
                    world = msg.get("world", {})
                    if "damage" in msg:
                        health -= msg["damage"]
            except:
                break

    threading.Thread(target=recv, daemon=True).start()

def send(x, y, a, action=None):
    if sock:
        try:
            data = {
                "id": pid,
                "x": x,
                "y": y,
                "a": a,
                "dimension": current_dimension,
                "inventory": inventory,
                "health": health,
                "action": action
            }
            sock.send(json.dumps(data).encode())
        except:
            pass

# ---------------- WORLD ----------------
def height(x):
    return int(6 + math.sin(x*0.1)*4)

def get_block(x, y, dim="overworld"):
    key = (int(x//TILE), int(y//TILE), dim)
    if key in world:
        return world[key]

    if dim == "nether":
        h = height(x) - 5
        color = 1
    elif dim == "end":
        h = height(x) + 5
        color = 2
    else:  # overworld
        h = height(x)
        color = 2

    if y < h:
        return 0
    if y == h:
        return color
    return 1

# ---------------- MINING ----------------
def mine():
    global inventory, world
    gx = int(px // TILE)
    gy = int(py // TILE)
    key = (gx, gy, current_dimension)
    
    block = get_block(px, py, current_dimension)
    if block:
        world[key] = 0
        inventory[str(block)] = inventory.get(str(block), 0) + 1
        send(px, py, pa, {"type": "mine", "x": gx, "y": gy})

# ---------------- COMBAT ----------------
def attack():
    global health
    # Check if attacking any villagers
    attack_range = 50
    for vid, villager in villagers.items():
        vx, vy = villager["x"], villager["y"]
        dist = math.sqrt((px - vx)**2 + (py - vy)**2)
        if dist < attack_range:
            send(px, py, pa, {"type": "attack_villager", "id": vid})

# ---------------- DIMENSION TRAVEL ----------------
def change_dimension(new_dim):
    global current_dimension, px, py
    current_dimension = new_dim
    # Respawn at dimension-specific coordinates
    if new_dim == "nether":
        px, py = 200, 200
    elif new_dim == "end":
        px, py = 300, 100
    else:
        px, py = 100, 100
    send(px, py, pa, {"type": "dimension_change", "dimension": new_dim})

# ---------------- SKY ----------------
def draw_sky():
    if current_dimension == "overworld":
        color_top = (70, 140, 220)
        color_bot = (120, 200, 220)
    elif current_dimension == "nether":
        color_top = (100, 30, 30)
        color_bot = (150, 50, 50)
    else:  # end
        color_top = (10, 10, 30)
        color_bot = (30, 30, 50)
    
    for y in range(HEIGHT//2):
        t = y/(HEIGHT//2)
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

# ---------------- FLOOR ----------------
def draw_floor():
    if current_dimension == "overworld":
        color = (40, 120, 40)
    elif current_dimension == "nether":
        color = (80, 20, 20)
    else:  # end
        color = (20, 20, 40)
    
    for y in range(HEIGHT//2, HEIGHT):
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))

# ---------------- TEXTURE ----------------
def get_tex(b):
    if b == 1: return wall_tex
    if b == 2: return wood_tex
    return grass_tex

# ---------------- RAYCAST ----------------
def cast():
    draw_sky()
    draw_floor()

    start = pa - FOV/2
    step = FOV/RAYS

    for r in range(RAYS):
        a = start + r*step

        sin_a = math.sin(a)
        cos_a = math.cos(a)

        for d in range(1, MAX_DEPTH):
            tx = px + cos_a*d
            ty = py + sin_a*d

            b = get_block(tx, ty, current_dimension)

            if b:
                dist = d * math.cos(pa - a)
                if dist < 0.0001:
                    dist = 0.0001

                h = HEIGHT / (dist * 0.02)

                tex = get_tex(b)

                hit = int((tx % TILE) / TILE * 63)
                hit = max(0, min(63, hit))

                col = tex.subsurface((hit,0,1,64))
                col = pygame.transform.scale(col,(WIDTH//RAYS,int(h)))

                shade = max(0.35, 1 - dist/900)
                col.fill((shade*255,shade*255,shade*255),
                         special_flags=pygame.BLEND_MULT)

                screen.blit(col,(r*(WIDTH//RAYS),HEIGHT//2 - h//2))
                break

# ---------------- HUD ----------------
def draw_hud():
    font = pygame.font.Font(None, 24)
    
    # Health bar
    health_text = font.render(f"Health: {health}/{max_health}", True, (255, 0, 0))
    screen.blit(health_text, (10, 10))
    
    # Dimension display
    dim_text = font.render(f"Dimension: {current_dimension.upper()}", True, (100, 200, 255))
    screen.blit(dim_text, (10, 40))
    
    # Inventory display
    inv_text = font.render("Inventory:", True, (255, 255, 255))
    screen.blit(inv_text, (10, 70))
    
    y_offset = 100
    for block_type, count in inventory.items():
        item_text = font.render(f"Block {block_type}: {count}", True, (200, 200, 200))
        screen.blit(item_text, (10, y_offset))
        y_offset += 25
    
    # Instructions
    instructions = [
        "SPACE: Mine",
        "E: Attack",
        "1-3: Change Dimension",
        "Q: Drop Item"
    ]
    y_offset = HEIGHT - 120
    for inst in instructions:
        inst_text = font.render(inst, True, (150, 150, 150))
        screen.blit(inst_text, (WIDTH - 200, y_offset))
        y_offset += 25

# START LAN
lan_start()

# MAIN LOOP
run = True
while run:
    clock.tick(60)

    keys = pygame.key.get_pressed()

    for e in pygame.event.get():
        if e.type == pygame.QUIT:
            run = False
        if e.type == pygame.KEYDOWN:
            if e.key == pygame.K_SPACE:
                mine()
            if e.key == pygame.K_e:
                attack()
            if e.key == pygame.K_1:
                change_dimension("overworld")
            if e.key == pygame.K_2:
                change_dimension("nether")
            if e.key == pygame.K_3:
                change_dimension("end")
            if e.key == pygame.K_q:
                if inventory:
                    last_item = list(inventory.keys())[-1]
                    inventory[last_item] -= 1
                    if inventory[last_item] == 0:
                        del inventory[last_item]

    mx, my = pygame.mouse.get_rel()
    pa += mx * 0.002

    dx = math.cos(pa) * speed
    dy = math.sin(pa) * speed

    if keys[pygame.K_w]:
        px += dx
        py += dy
    if keys[pygame.K_s]:
        px -= dx
        py -= dy
    if keys[pygame.K_a]:
        px -= dy
        py += dx
    if keys[pygame.K_d]:
        px += dy
        py -= dx

    cast()
    draw_hud()
    send(px, py, pa)

    # Draw other players
    for i, p in players.items():
        if i == pid:
            continue
        if p.get("dimension") != current_dimension:
            continue
        sx = int(p["x"] - px + WIDTH//2)
        sy = int(p["y"] - py + HEIGHT//2)
        pygame.draw.circle(screen, (0, 0, 255), (sx, sy), 6)

    # Draw villagers
    for vid, v in villagers.items():
        if v.get("dimension") != current_dimension:
            continue
        sx = int(v["x"] - px + WIDTH//2)
        sy = int(v["y"] - py + HEIGHT//2)
        pygame.draw.circle(screen, (100, 200, 100), (sx, sy), 8)

    pygame.display.flip()

pygame.quit()
