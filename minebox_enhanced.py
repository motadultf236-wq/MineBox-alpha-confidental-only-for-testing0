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
equipped_item = None
selected_block = 0

# ============ ENTITY SPRITES ============
def create_entity_sprite(color, size=32):
    """Create a simple sprite for an entity"""
    surf = pygame.Surface((size, size), pygame.SRCALPHA)
    pygame.draw.circle(surf, color, (size//2, size//2), size//2)
    return surf

# Create sprites
zombie_sprite = create_entity_sprite((180, 80, 80), 32)
villager_sprite = create_entity_sprite((80, 200, 80), 32)
player_sprite = create_entity_sprite((100, 150, 255), 28)

# ============ ITEMS ============
ITEMS = {
    "sword": {"damage": 15, "range": 80, "speed": 0.5, "color": (200, 100, 50)},
    "pickaxe": {"damage": 5, "speed_boost": 1.5, "color": (150, 150, 150)},
    "food": {"heal": 20, "color": (255, 150, 100)},
    "wood": {"type": "block", "color": (139, 90, 40)},
    "stone": {"type": "block", "color": (180, 180, 180)},
    "grass": {"type": "block", "color": (80, 200, 80)},
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
    
    pickup_range = 100
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

def get_entity_angle_and_distance(entity_x, entity_y):
    """Calculate angle and distance to entity from player"""
    dx = entity_x - px
    dy = entity_y - py
    
    dist = math.sqrt(dx**2 + dy**2)
    angle = math.atan2(dy, dx)
    
    return angle, dist

def cast_rays():
    """Raycasting engine with entity rendering"""
    draw_sky()
    draw_floor()
    
    # Collect all entities with their distances
    entities_to_draw = []
    
    # Collect zombies
    for zid, zombie in zombies.items():
        if zombie.get("dimension") != current_dimension:
            continue
        angle, dist = get_entity_angle_and_distance(zombie["x"], zombie["y"])
        entities_to_draw.append({
            "type": "zombie",
            "angle": angle,
            "distance": dist,
            "entity": zombie,
            "id": zid
        })
    
    # Collect villagers
    for vid, villager in villagers.items():
        if villager.get("dimension") != current_dimension:
            continue
        angle, dist = get_entity_angle_and_distance(villager["x"], villager["y"])
        entities_to_draw.append({
            "type": "villager",
            "angle": angle,
            "distance": dist,
            "entity": villager,
            "id": vid
        })
    
    # Collect items
    for item_id, item in items_on_ground.items():
        if item.get("dimension") != current_dimension:
            continue
        angle, dist = get_entity_angle_and_distance(item["x"], item["y"])
        entities_to_draw.append({
            "type": "item",
            "angle": angle,
            "distance": dist,
            "entity": item,
            "id": item_id
        })
    
    # Collect other players
    for pid_other, player in players.items():
        if pid_other == pid:
            continue
        if player.get("dimension") != current_dimension:
            continue
        angle, dist = get_entity_angle_and_distance(player["x"], player["y"])
        entities_to_draw.append({
            "type": "player",
            "angle": angle,
            "distance": dist,
            "entity": player,
            "id": pid_other
        })
    
    # Sort by distance (draw far entities first)
    entities_to_draw.sort(key=lambda e: e["distance"], reverse=True)
    
    # Draw walls first
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
    
    # Draw entities
    for entity_data in entities_to_draw:
        angle_to_entity = entity_data["angle"]
        dist_to_entity = entity_data["distance"]
        
        if dist_to_entity < 10:
            dist_to_entity = 10
        
        # Calculate screen position
        angle_diff = angle_to_entity - pa
        
        # Normalize angle
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        # Only draw if in FOV
        if abs(angle_diff) > FOV / 2:
            continue
        
        # Calculate screen X based on angle
        screen_x = WIDTH / 2 + (angle_diff / (FOV / 2)) * (WIDTH / 2)
        
        # Calculate height/size based on distance
        entity_height = int(HEIGHT / (dist_to_entity * 0.02))
        
        if entity_height < 2:
            entity_height = 2
        
        # Calculate screen Y
        screen_y = HEIGHT // 2 - entity_height // 2
        
        # Draw based on entity type
        entity_type = entity_data["type"]
        entity = entity_data["entity"]
        
        if entity_type == "zombie":
            color = (180, 80, 80)
            pygame.draw.rect(screen, color, (int(screen_x) - entity_height // 2, int(screen_y), entity_height, entity_height))
            # Health bar
            health_pct = entity.get("health", 20) / 20.0
            pygame.draw.line(screen, (255, 0, 0), (int(screen_x) - entity_height // 2, int(screen_y) - 5), 
                           (int(screen_x) - entity_height // 2 + int(entity_height * health_pct), int(screen_y) - 5), 2)
        
        elif entity_type == "villager":
            color = (80, 200, 80)
            pygame.draw.rect(screen, color, (int(screen_x) - entity_height // 2, int(screen_y), entity_height, entity_height))
            # Health bar
            health_pct = entity.get("health", 20) / 20.0
            pygame.draw.line(screen, (255, 0, 0), (int(screen_x) - entity_height // 2, int(screen_y) - 5),
                           (int(screen_x) - entity_height // 2 + int(entity_height * health_pct), int(screen_y) - 5), 2)
        
        elif entity_type == "player":
            color = (100, 150, 255)
            pygame.draw.rect(screen, color, (int(screen_x) - entity_height // 2, int(screen_y), entity_height, entity_height))
        
        elif entity_type == "item":
            item_type = entity.get("type", "stone")
            color = ITEMS.get(item_type, {}).get("color", (200, 200, 200))
            pygame.draw.rect(screen, color, (int(screen_x) - 4, int(screen_y), 8, 8))

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
        "S/Shift/F: Equip Sword/Pickaxe/Food"
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
            if event.key == pygame.K_LSHIFT or event.key == pygame.K_RSHIFT:
                equip_item("pickaxe")
            if event.key == pygame.K_f:
                if equipped_item != "food":
                    equip_item("food")
                else:
                    use_item()
    
    # Movement
    mouse_x, mouse_y = pygame.mouse.get_rel()
    pa += mouse_x * 0.005
    
    move_x = math.cos(pa) * speed
    move_y = math.sin(pa) * speed
    
    if keys[pygame.K_w]:
        px += move_x
        py += move_y
    if keys[pygame.K_a]:
        px -= move_y
        py += move_x
    if keys[pygame.K_d]:
        px += move_y
        py -= move_x
    
    # Rendering
    cast_rays()
    draw_hud()
    
    # Send state
    send(px, py, pa)
    
    pygame.display.flip()

pygame.quit()
