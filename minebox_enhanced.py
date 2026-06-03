import pygame
import math
import socket
import threading
import json
import uuid
import os
import random

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

# ---------------- LAN ----------------
SERVER_IP = "127.0.0.1"
PORT = 5555

sock = None
players = {}
villagers = {}
zombies = {}
world = {}
items_on_ground = {}
pid = str(uuid.uuid4())

# Player state
px, py = 100.0, 100.0
pa = 0.0
speed = 3.0
health = 100
max_health = 100
current_dimension = "overworld"
inventory = {}
equipped_item = None  # sword, pickaxe, food
selected_block = 0

# ============ TEXTURES ============
def create_textures():
    """Create simple block textures"""
    textures = {}
    
    # Grass block
    grass_tex = pygame.Surface((64, 64))
    grass_tex.fill((60, 180, 60))
    pygame.draw.line(grass_tex, (80, 200, 80), (0, 32), (64, 32), 2)
    textures["grass"] = grass_tex
    
    # Stone block
    stone_tex = pygame.Surface((64, 64))
    stone_tex.fill((120, 120, 120))
    for x in range(0, 64, 16):
        for y in range(0, 64, 16):
            pygame.draw.rect(stone_tex, (100, 100, 100), (x, y, 14, 14))
    textures["stone"] = stone_tex
    
    # Wood block
    wood_tex = pygame.Surface((64, 64))
    wood_tex.fill((139, 90, 40))
    pygame.draw.rect(wood_tex, (160, 110, 50), (10, 10, 44, 44), 2)
    textures["wood"] = wood_tex
    
    # Dirt block
    dirt_tex = pygame.Surface((64, 64))
    dirt_tex.fill((139, 101, 60))
    textures["dirt"] = dirt_tex
    
    return textures

textures = create_textures()

# ============ ITEMS ============
ITEMS = {
    "sword": {"damage": 15, "range": 80, "speed": 0.5, "color": (200, 100, 50)},
    "pickaxe": {"damage": 5, "speed_boost": 1.5, "color": (150, 150, 150)},
    "food": {"heal": 20, "color": (255, 150, 100)},
    "wood": {"type": "block", "color": (139, 90, 40)},
    "stone": {"type": "block", "color": (120, 120, 120)},
    "grass": {"type": "block", "color": (60, 180, 60)},
}

def lan_start():
    global sock
    try:
        sock = socket.socket()
        sock.connect((SERVER_IP, PORT))
        sock.settimeout(1.0)

        def recv():
            global players, villagers, zombies, world, items_on_ground, health
            while True:
                try:
                    data = sock.recv(4096).decode()
                    if data:
                        msg = json.loads(data)
                        players = msg.get("players", {})
                        villagers = msg.get("villagers", {})
                        zombies = msg.get("zombies", {})
                        world = msg.get("world", {})
                        items_on_ground = msg.get("items", {})
                except socket.timeout:
                    pass
                except:
                    break

        threading.Thread(target=recv, daemon=True).start()
    except:
        print("Could not connect to server. Make sure server_enhanced.py is running!")

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
                "equipped": equipped_item,
                "action": action
            }
            sock.send(json.dumps(data).encode())
        except:
            pass

# ============ WORLD GENERATION ============
def height(x, dim="overworld"):
    if dim == "nether":
        return int(4 + math.sin(x * 0.08) * 3)
    elif dim == "end":
        return int(8 + math.sin(x * 0.12) * 4)
    else:
        return int(6 + math.sin(x * 0.1) * 4)

def get_block(x, y, dim="overworld"):
    """Get block type at position"""
    gx = int(x // TILE)
    gy = int(y // TILE)
    key = (gx, gy, dim)
    
    if key in world and world[key] == 0:
        return 0
    
    h = height(gx, dim)
    
    if gy < h:
        return 0
    elif gy == h:
        return 2  # Grass
    else:
        return 1  # Stone

# ============ MINING ============
def mine():
    global inventory
    dx = math.cos(pa)
    dy = math.sin(pa)
    
    speed_mult = 1.0
    if equipped_item == "pickaxe":
        speed_mult = 1.5
    
    for dist in range(1, int(100 * speed_mult)):
        tx = px + dx * dist
        ty = py + dy * dist
        
        block = get_block(tx, ty, current_dimension)
        if block != 0:
            gx = int(tx // TILE)
            gy = int(ty // TILE)
            key = (gx, gy, current_dimension)
            
            world[key] = 0
            
            block_name = "stone" if block == 1 else "grass"
            inventory[block_name] = inventory.get(block_name, 0) + 1
            
            send(px, py, pa, {"type": "mine", "x": gx, "y": gy})
            break

# ============ COMBAT ============
def attack():
    global health, inventory
    dx = math.cos(pa)
    dy = math.sin(pa)
    
    damage = 5
    attack_range = 50
    
    if equipped_item == "sword":
        damage = 15
        attack_range = 80
    
    # Attack villagers
    for vid, villager in villagers.items():
        vx, vy = villager["x"], villager["y"]
        
        if villager.get("dimension") != current_dimension:
            continue
        
        dist = math.sqrt((px - vx)**2 + (py - vy)**2)
        if dist < attack_range:
            send(px, py, pa, {"type": "attack_villager", "id": vid, "damage": damage})
    
    # Attack zombies
    for zid, zombie in zombies.items():
        zx, zy = zombie["x"], zombie["y"]
        
        if zombie.get("dimension") != current_dimension:
            continue
        
        dist = math.sqrt((px - zx)**2 + (py - zy)**2)
        if dist < attack_range:
            send(px, py, pa, {"type": "attack_zombie", "id": zid, "damage": damage})

# ============ ITEM MANAGEMENT ============
def equip_item(item_type):
    global equipped_item
    if item_type in inventory and inventory[item_type] > 0:
        equipped_item = item_type
        return True
    return False

def use_item():
    global health, inventory, equipped_item
    
    if equipped_item == "food" and equipped_item in inventory:
        heal_amount = ITEMS["food"]["heal"]
        health = min(max_health, health + heal_amount)
        inventory["food"] -= 1
        if inventory["food"] <= 0:
            del inventory["food"]
            equipped_item = None
        send(px, py, pa, {"type": "use_item", "item": "food"})
        return True
    
    return False

def pick_up_item():
    """Pick up items on the ground"""
    global inventory
    
    pickup_range = 50
    items_to_remove = []
    
    for item_id, item in items_on_ground.items():
        ix, iy = item["x"], item["y"]
        
        if item.get("dimension") != current_dimension:
            continue
        
        dist = math.sqrt((px - ix)**2 + (py - iy)**2)
        if dist < pickup_range:
            item_type = item["type"]
            inventory[item_type] = inventory.get(item_type, 0) + item.get("amount", 1)
            items_to_remove.append(item_id)
            send(px, py, pa, {"type": "pickup_item", "item_id": item_id})
    
    for item_id in items_to_remove:
        del items_on_ground[item_id]

# ============ DIMENSION TRAVEL ============
def change_dimension(new_dim):
    global current_dimension, px, py
    current_dimension = new_dim
    
    if new_dim == "nether":
        px, py = 200.0, 200.0
    elif new_dim == "end":
        px, py = 300.0, 100.0
    else:
        px, py = 100.0, 100.0
    
    send(px, py, pa, {"type": "dimension_change", "dimension": new_dim})

# ============ RENDERING ============
def draw_sky():
    if current_dimension == "overworld":
        color_top = (70, 140, 220)
        color_bot = (120, 200, 220)
    elif current_dimension == "nether":
        color_top = (100, 30, 30)
        color_bot = (150, 50, 50)
    else:
        color_top = (10, 10, 30)
        color_bot = (30, 30, 50)
    
    for y in range(HEIGHT // 2):
        t = y / (HEIGHT // 2)
        r = int(color_top[0] + (color_bot[0] - color_top[0]) * t)
        g = int(color_top[1] + (color_bot[1] - color_top[1]) * t)
        b = int(color_top[2] + (color_bot[2] - color_top[2]) * t)
        pygame.draw.line(screen, (r, g, b), (0, y), (WIDTH, y))

def draw_floor():
    if current_dimension == "overworld":
        color = (40, 120, 40)
    elif current_dimension == "nether":
        color = (80, 20, 20)
    else:
        color = (20, 20, 40)
    
    for y in range(HEIGHT // 2, HEIGHT):
        pygame.draw.line(screen, color, (0, y), (WIDTH, y))

def cast_rays():
    """Raycasting engine"""
    draw_sky()
    draw_floor()
    
    start_angle = pa - FOV / 2
    angle_step = FOV / RAYS
    
    for ray_idx in range(RAYS):
        current_angle = start_angle + ray_idx * angle_step
        
        cos_a = math.cos(current_angle)
        sin_a = math.sin(current_angle)
        
        for distance in range(1, MAX_DEPTH):
            target_x = px + cos_a * distance
            target_y = py + sin_a * distance
            
            block_type = get_block(target_x, target_y, current_dimension)
            
            if block_type != 0:
                corrected_dist = distance * math.cos(pa - current_angle)
                
                if corrected_dist < 0.1:
                    corrected_dist = 0.1
                
                wall_height = int(HEIGHT / (corrected_dist * 0.02))
                
                if block_type == 2:
                    base_color = (60, 180, 60)
                else:
                    base_color = (120, 120, 120)
                
                shade = max(0.3, 1.0 - (corrected_dist / 800.0))
                final_color = (
                    int(base_color[0] * shade),
                    int(base_color[1] * shade),
                    int(base_color[2] * shade)
                )
                
                x_pos = ray_idx * (WIDTH // RAYS)
                y_pos = HEIGHT // 2 - wall_height // 2
                
                pygame.draw.rect(
                    screen,
                    final_color,
                    (x_pos, y_pos, WIDTH // RAYS + 1, wall_height)
                )
                break

def draw_hud():
    font_small = pygame.font.Font(None, 18)
    font_large = pygame.font.Font(None, 24)
    
    # Health bar
    health_text = font_large.render(f"Health: {health}/{max_health}", True, (255, 100, 100))
    screen.blit(health_text, (10, 10))
    
    # Equipped item
    equipped_text = f"Equipped: {equipped_item.upper() if equipped_item else 'NONE'}"
    equipped_display = font_small.render(equipped_text, True, (200, 200, 100))
    screen.blit(equipped_display, (10, 35))
    
    # Dimension
    dim_text = font_small.render(f"Dimension: {current_dimension.upper()}", True, (100, 200, 255))
    screen.blit(dim_text, (10, 55))
    
    # Inventory header
    inv_text = font_small.render("Inventory:", True, (200, 200, 200))
    screen.blit(inv_text, (10, 75))
    
    # Inventory items
    y_offset = 95
    if inventory:
        for item_type, count in sorted(inventory.items()):
            item_text = font_small.render(f"{item_type}: {count}x", True, (150, 200, 150))
            screen.blit(item_text, (10, y_offset))
            y_offset += 18
    else:
        empty_text = font_small.render("(empty)", True, (100, 100, 100))
        screen.blit(empty_text, (10, y_offset))
    
    # Instructions
    inst_y = HEIGHT - 120
    instructions = [
        "SPACE: Mine | E: Attack | F: Use Item",
        "1-3: Dimensions | Q: Drop | P: Pick Up",
        "S/P/F: Equip Sword/Pickaxe/Food"
    ]
    for inst in instructions:
        inst_text = font_small.render(inst, True, (150, 150, 150))
        screen.blit(inst_text, (WIDTH - len(inst) * 7 - 10, inst_y))
        inst_y += 18

# ============ START ============
lan_start()

running = True
while running:
    clock.tick(60)
    
    keys = pygame.key.get_pressed()
    
    # Input
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False
        
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                mine()
            if event.key == pygame.K_e:
                attack()
            if event.key == pygame.K_f:
                use_item()
            if event.key == pygame.K_1:
                change_dimension("overworld")
            if event.key == pygame.K_2:
                change_dimension("nether")
            if event.key == pygame.K_3:
                change_dimension("end")
            if event.key == pygame.K_q:
                if inventory:
                    last_item = list(inventory.keys())[-1]
                    inventory[last_item] -= 1
                    if inventory[last_item] <= 0:
                        del inventory[last_item]
            if event.key == pygame.K_p:
                pick_up_item()
            if event.key == pygame.K_s:
                equip_item("sword")
            if event.key == pygame.K_SHIFT:
                equip_item("pickaxe")
            if event.key == pygame.K_f:
                equip_item("food")
    
    # Movement
    mouse_x, mouse_y = pygame.mouse.get_rel()
    pa += mouse_x * 0.005
    
    move_x = math.cos(pa) * speed
    move_y = math.sin(pa) * speed
    
    if keys[pygame.K_w]:
        px += move_x
        py += move_y
    if keys[pygame.K_s]:
        px -= move_x
        py -= move_y
    if keys[pygame.K_a]:
        px -= move_y
        py += move_x
    if keys[pygame.K_d]:
        px += move_y
        py -= move_x
    
    # Rendering
    cast_rays()
    
    # Draw items on ground
    for item_id, item in items_on_ground.items():
        if item.get("dimension") != current_dimension:
            continue
        
        ix, iy = item["x"], item["y"]
        screen_x = WIDTH // 2 + (ix - px)
        screen_y = HEIGHT // 2 + (iy - py)
        
        if 0 < screen_x < WIDTH and 0 < screen_y < HEIGHT:
            item_color = ITEMS.get(item["type"], {}).get("color", (200, 200, 200))
            pygame.draw.rect(screen, item_color, (int(screen_x) - 3, int(screen_y) - 3, 6, 6))
    
    # Draw players
    for pid_other, player in players.items():
        if pid_other == pid:
            continue
        if player.get("dimension") != current_dimension:
            continue
        
        other_x = player["x"]
        other_y = player["y"]
        
        screen_x = WIDTH // 2 + (other_x - px)
        screen_y = HEIGHT // 2 + (other_y - py)
        
        if 0 < screen_x < WIDTH and 0 < screen_y < HEIGHT:
            pygame.draw.circle(screen, (0, 100, 255), (int(screen_x), int(screen_y)), 6)
    
    # Draw villagers
    for vid, villager in villagers.items():
        if villager.get("dimension") != current_dimension:
            continue
        
        vx = villager["x"]
        vy = villager["y"]
        
        screen_x = WIDTH // 2 + (vx - px)
        screen_y = HEIGHT // 2 + (vy - py)
        
        if 0 < screen_x < WIDTH and 0 < screen_y < HEIGHT:
            pygame.draw.circle(screen, (100, 200, 100), (int(screen_x), int(screen_y)), 8)
            # Health bar
            pygame.draw.line(screen, (255, 0, 0), (int(screen_x) - 8, int(screen_y) - 12), (int(screen_x) + 8, int(screen_y) - 12), 2)
    
    # Draw zombies
    for zid, zombie in zombies.items():
        if zombie.get("dimension") != current_dimension:
            continue
        
        zx = zombie["x"]
        zy = zombie["y"]
        
        screen_x = WIDTH // 2 + (zx - px)
        screen_y = HEIGHT // 2 + (zy - py)
        
        if 0 < screen_x < WIDTH and 0 < screen_y < HEIGHT:
            pygame.draw.circle(screen, (150, 100, 100), (int(screen_x), int(screen_y)), 10)
            # Health bar
            health_pct = zombie.get("health", 20) / 20.0
            pygame.draw.line(screen, (255, 0, 0), (int(screen_x) - 10, int(screen_y) - 14), (int(screen_x) - 10 + int(20 * health_pct), int(screen_y) - 14), 3)
    
    # Draw HUD
    draw_hud()
    
    # Send state
    send(px, py, pa)
    
    pygame.display.flip()

pygame.quit()
