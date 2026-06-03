import pygame
import math
import socket
import threading
import json
import uuid
import os
import random
import time

# Import account system
from account_system import load_character, save_character, update_character_stats

pygame.init()
pygame.mixer.init()

# Check if character is loaded
current_character = None
try:
    with open("current_character.json", "r") as f:
        current_character = json.load(f)
except:
    print("No character loaded! Run login_ui.py first")
    exit()

# Remove temp file
try:
    os.remove("current_character.json")
except:
    pass

# SCREEN
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption(f"MineBox Enhanced - {current_character['char_name']}")

# SETTINGS
FOV = math.pi / 3
RAYS = 120
MAX_DEPTH = 400
TILE = 64

# LAN
SERVER_IP = "127.0.0.1"
PORT = 5555

sock = None
players = {}
villagers = {}
zombies = {}
world = {}
items_on_ground = {}
particles = []
pid = str(uuid.uuid4())

# Player state (loaded from character)
px, py = float(current_character["x"]), float(current_character["y"])
pa = 0.0
speed = 3.0
health = current_character["health"]
max_health = 100
current_dimension = current_character["dimension"]
inventory = current_character["inventory"]
equipped_item = None
armor = current_character["armor"]
active_potions = {}
char_id = current_character["char_id"]
kills = current_character["kills"]
deaths = current_character["deaths"]
playtime_session = 0.0

# Textures
def create_advanced_textures():
    textures = {}
    
    grass_tex = pygame.Surface((64, 64))
    grass_tex.fill((60, 180, 60))
    pygame.draw.line(grass_tex, (80, 200, 80), (0, 20), (64, 20), 3)
    for x in range(0, 64, 8):
        pygame.draw.line(grass_tex, (50, 150, 50), (x, 25), (x + 4, 30), 1)
    textures["grass"] = grass_tex
    
    stone_tex = pygame.Surface((64, 64))
    stone_tex.fill((120, 120, 120))
    for x in range(0, 64, 16):
        for y in range(0, 64, 16):
            pygame.draw.rect(stone_tex, (100, 100, 100), (x, y, 14, 14), 1)
    textures["stone"] = stone_tex
    
    wood_tex = pygame.Surface((64, 64))
    wood_tex.fill((139, 90, 40))
    pygame.draw.circle(wood_tex, (160, 110, 50), (32, 32), 20)
    pygame.draw.circle(wood_tex, (120, 70, 30), (32, 32), 15)
    pygame.draw.circle(wood_tex, (160, 110, 50), (32, 32), 10)
    textures["wood"] = wood_tex
    
    dirt_tex = pygame.Surface((64, 64))
    dirt_tex.fill((139, 101, 60))
    for x in range(0, 64, 8):
        for y in range(0, 64, 8):
            if random.random() > 0.5:
                pygame.draw.rect(dirt_tex, (120, 85, 50), (x, y, 6, 6))
    textures["dirt"] = dirt_tex
    
    nether_tex = pygame.Surface((64, 64))
    nether_tex.fill((100, 30, 30))
    for x in range(0, 64, 12):
        for y in range(0, 64, 12):
            pygame.draw.rect(nether_tex, (150, 50, 50), (x, y, 8, 8))
    textures["nether"] = nether_tex
    
    end_tex = pygame.Surface((64, 64))
    end_tex.fill((80, 40, 120))
    for x in range(0, 64, 16):
        for y in range(0, 64, 16):
            pygame.draw.circle(end_tex, (120, 80, 160), (x + 8, y + 8), 4)
    textures["end"] = end_tex
    
    return textures

textures = create_advanced_textures()

# Sound Effects
def create_sound_effect(frequency, duration=0.1):
    sample_rate = 22050
    frames = int(sample_rate * duration)
    arr = pygame.sndarray.array("h", pygame.mixer.Sound(buffer=bytearray(frames * 2)))
    for i in range(frames):
        arr[i] = int(32767 * 0.3 * math.sin(2 * math.pi * frequency * i / sample_rate))
    return pygame.mixer.Sound(buffer=bytearray(arr))

try:
    sound_hit = create_sound_effect(400, 0.1)
    sound_mine = create_sound_effect(600, 0.15)
    sound_death = create_sound_effect(200, 0.3)
    sound_pickup = create_sound_effect(800, 0.08)
    sound_potion = create_sound_effect(1000, 0.2)
except:
    print("Sound disabled")

# Items
ITEMS = {
    "sword": {"damage": 15, "range": 80, "color": (200, 100, 50)},
    "bow": {"damage": 10, "range": 200, "color": (180, 100, 40)},
    "pickaxe": {"speed_boost": 1.5, "color": (150, 150, 150)},
    "food": {"heal": 20, "color": (255, 150, 100)},
    "health_potion": {"heal": 50, "color": (255, 50, 50), "type": "potion"},
    "speed_potion": {"duration": 10, "color": (100, 200, 255), "type": "potion"},
    "strength_potion": {"damage_boost": 5, "duration": 10, "color": (255, 100, 100), "type": "potion"},
    "leather_armor": {"defense": 5, "color": (160, 100, 50), "type": "armor"},
    "iron_armor": {"defense": 10, "color": (180, 180, 180), "type": "armor"},
    "diamond_armor": {"defense": 20, "color": (100, 200, 255), "type": "armor"},
    "wood": {"type": "block", "color": (139, 90, 40)},
    "stone": {"type": "block", "color": (180, 180, 180)},
    "grass": {"type": "block", "color": (80, 200, 80)},
}

# Particles
class Particle:
    def __init__(self, x, y, vx, vy, color, lifetime=1.0, particle_type="spark"):
        self.x = x
        self.y = y
        self.vx = vx
        self.vy = vy
        self.color = color
        self.lifetime = lifetime
        self.max_lifetime = lifetime
        self.particle_type = particle_type
    
    def update(self, dt):
        self.x += self.vx * dt
        self.y += self.vy * dt
        self.vy += 5 * dt
        self.lifetime -= dt
    
    def draw_2d(self, surface, player_x, player_y, screen_width, screen_height):
        screen_x = screen_width // 2 + (self.x - player_x)
        screen_y = screen_height // 2 + (self.y - player_y)
        
        if 0 < screen_x < screen_width and 0 < screen_y < screen_height:
            alpha = int(255 * (self.lifetime / self.max_lifetime))
            size = max(1, int(3 * (self.lifetime / self.max_lifetime)))
            pygame.draw.circle(surface, self.color, (int(screen_x), int(screen_y)), size)

def spawn_particles(x, y, particle_type="spark", color=(255, 255, 255), count=5):
    for _ in range(count):
        angle = random.random() * 2 * math.pi
        speed = random.uniform(50, 150)
        vx = math.cos(angle) * speed
        vy = math.sin(angle) * speed - 50
        
        lifetime = random.uniform(0.5, 1.5)
        particles.append(Particle(x, y, vx, vy, color, lifetime, particle_type))

def update_particles(dt):
    global particles
    for particle in particles[:]:
        particle.update(dt)
        if particle.lifetime <= 0:
            particles.remove(particle)

# LAN
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
        print("Could not connect to server!")

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
                "armor": armor,
                "action": action
            }
            sock.send(json.dumps(data).encode())
        except:
            pass

# World
def height(x, dim="overworld"):
    if dim == "nether":
        return int(4 + math.sin(x * 0.08) * 3)
    elif dim == "end":
        return int(8 + math.sin(x * 0.12) * 4)
    else:
        return int(6 + math.sin(x * 0.1) * 4)

def get_block(x, y, dim="overworld"):
    gx = int(x // TILE)
    gy = int(y // TILE)
    key = (gx, gy, dim)
    
    if key in world and world[key] == 0:
        return 0
    
    h = height(gx, dim)
    
    if gy < h:
        return 0
    elif gy == h:
        return 2
    else:
        return 1

# Mining
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
            
            try:
                sound_mine.play()
            except:
                pass
            
            spawn_particles(tx, ty, "dust", (150, 150, 150), 8)
            send(px, py, pa, {"type": "mine", "x": gx, "y": gy})
            break

# Combat
def attack():
    global health, kills
    dx = math.cos(pa)
    dy = math.sin(pa)
    
    damage = 5
    attack_range = 50
    
    if "strength_potion" in active_potions:
        damage += ITEMS["strength_potion"]["damage_boost"]
    
    if equipped_item == "sword":
        damage = 15
        attack_range = 80
    elif equipped_item == "bow":
        damage = 10
        attack_range = 200
    
    for vid, villager in villagers.items():
        vx, vy = villager["x"], villager["y"]
        
        if villager.get("dimension") != current_dimension:
            continue
        
        dist = math.sqrt((px - vx)**2 + (py - vy)**2)
        if dist < attack_range:
            try:
                sound_hit.play()
            except:
                pass
            spawn_particles(vx, vy, "blood", (255, 50, 50), 10)
            send(px, py, pa, {"type": "attack_villager", "id": vid, "damage": damage})
    
    for zid, zombie in zombies.items():
        zx, zy = zombie["x"], zombie["y"]
        
        if zombie.get("dimension") != current_dimension:
            continue
        
        dist = math.sqrt((px - zx)**2 + (py - zy)**2)
        if dist < attack_range:
            try:
                sound_hit.play()
            except:
                pass
            spawn_particles(zx, zy, "blood", (255, 50, 50), 12)
            kills += 1
            send(px, py, pa, {"type": "attack_zombie", "id": zid, "damage": damage})

# Items
def equip_item(item_type):
    global equipped_item, armor
    
    if item_type in inventory and inventory[item_type] > 0:
        if item_type.endswith("_armor"):
            armor = item_type
        else:
            equipped_item = item_type
        return True
    return False

def use_item():
    global health, inventory, equipped_item, active_potions
    
    if equipped_item == "food" and equipped_item in inventory:
        heal_amount = ITEMS["food"]["heal"]
        health = min(max_health, health + heal_amount)
        inventory["food"] -= 1
        if inventory["food"] <= 0:
            del inventory["food"]
            equipped_item = None
        try:
            sound_pickup.play()
        except:
            pass
        spawn_particles(px, py, "sparkle", (255, 200, 100), 8)
        send(px, py, pa, {"type": "use_item", "item": "food"})
        return True
    
    elif equipped_item and "potion" in ITEMS.get(equipped_item, {}).get("type", ""):
        potion_type = equipped_item
        if potion_type in inventory and inventory[potion_type] > 0:
            if potion_type == "health_potion":
                health = min(max_health, health + ITEMS[potion_type]["heal"])
            else:
                active_potions[potion_type] = ITEMS[potion_type]["duration"]
            
            inventory[potion_type] -= 1
            if inventory[potion_type] <= 0:
                del inventory[potion_type]
                equipped_item = None
            
            try:
                sound_potion.play()
            except:
                pass
            spawn_particles(px, py, "sparkle", ITEMS[potion_type]["color"], 12)
            send(px, py, pa, {"type": "use_item", "item": potion_type})
            return True
    
    return False

def pick_up_item():
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
            
            try:
                sound_pickup.play()
            except:
                pass
            spawn_particles(ix, iy, "sparkle", (255, 200, 100), 6)
            send(px, py, pa, {"type": "pickup_item", "item_id": item_id})
    
    for item_id in items_to_remove:
        del items_on_ground[item_id]

# Dimensions
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

# Rendering
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
    dx = entity_x - px
    dy = entity_y - py
    
    dist = math.sqrt(dx**2 + dy**2)
    angle = math.atan2(dy, dx)
    
    return angle, dist

def cast_rays():
    draw_sky()
    draw_floor()
    
    entities_to_draw = []
    
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
    
    entities_to_draw.sort(key=lambda e: e["distance"], reverse=True)
    
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
    
    for entity_data in entities_to_draw:
        angle_to_entity = entity_data["angle"]
        dist_to_entity = entity_data["distance"]
        
        if dist_to_entity < 10:
            dist_to_entity = 10
        
        angle_diff = angle_to_entity - pa
        
        while angle_diff > math.pi:
            angle_diff -= 2 * math.pi
        while angle_diff < -math.pi:
            angle_diff += 2 * math.pi
        
        if abs(angle_diff) > FOV / 2:
            continue
        
        screen_x = WIDTH / 2 + (angle_diff / (FOV / 2)) * (WIDTH / 2)
        entity_height = int(HEIGHT / (dist_to_entity * 0.02))
        
        if entity_height < 2:
            entity_height = 2
        
        screen_y = HEIGHT // 2 - entity_height // 2
        
        entity_type = entity_data["type"]
        entity = entity_data["entity"]
        
        if entity_type == "zombie":
            color = (180, 80, 80)
            pygame.draw.rect(screen, color, (int(screen_x) - entity_height // 2, int(screen_y), entity_height, entity_height))
            health_pct = entity.get("health", 20) / 20.0
            pygame.draw.line(screen, (255, 0, 0), (int(screen_x) - entity_height // 2, int(screen_y) - 5),
                           (int(screen_x) - entity_height // 2 + int(entity_height * health_pct), int(screen_y) - 5), 2)
        
        elif entity_type == "villager":
            color = (80, 200, 80)
            pygame.draw.rect(screen, color, (int(screen_x) - entity_height // 2, int(screen_y), entity_height, entity_height))
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
    
    for particle in particles:
        particle.draw_2d(screen, px, py, WIDTH, HEIGHT)

def draw_hud():
    font_small = pygame.font.Font(None, 18)
    font_large = pygame.font.Font(None, 24)
    
    health_text = font_large.render(f"Health: {health}/{max_health}", True, (255, 100, 100))
    screen.blit(health_text, (10, 10))
    
    armor_text = font_small.render(f"Armor: {armor.upper()}", True, (200, 200, 150))
    screen.blit(armor_text, (10, 35))
    
    char_text = font_small.render(f"Character: {current_character['char_name']}", True, (200, 200, 255))
    screen.blit(char_text, (10, 50))
    
    kills_text = font_small.render(f"Kills: {kills}", True, (255, 150, 100))
    screen.blit(kills_text, (10, 65))
    
    if active_potions:
        pot_text = font_small.render(f"Potions: {', '.join(active_potions.keys())}", True, (200, 100, 200))
        screen.blit(pot_text, (10, 80))
        y_offset = 95
    else:
        y_offset = 80
    
    equipped_text = f"Equipped: {equipped_item.upper() if equipped_item else 'NONE'}"
    equipped_display = font_small.render(equipped_text, True, (200, 200, 100))
    screen.blit(equipped_display, (10, y_offset))
    
    dim_text = font_small.render(f"Dimension: {current_dimension.upper()}", True, (100, 200, 255))
    screen.blit(dim_text, (10, y_offset + 15))
    
    inv_text = font_small.render("Inventory:", True, (200, 200, 200))
    screen.blit(inv_text, (10, y_offset + 35))
    
    y_inv = y_offset + 55
    if inventory:
        for item_type, count in sorted(inventory.items()):
            item_text = font_small.render(f"{item_type}: {count}x", True, (150, 200, 150))
            screen.blit(item_text, (10, y_inv))
            y_inv += 16
    else:
        empty_text = font_small.render("(empty)", True, (100, 100, 100))
        screen.blit(empty_text, (10, y_inv))

# Main loop
lan_start()

running = True
session_start = time.time()

while running:
    dt = clock.tick(60) / 1000.0
    playtime_session += dt
    
    keys = pygame.key.get_pressed()
    
    for potion in list(active_potions.keys()):
        active_potions[potion] -= dt
        if active_potions[potion] <= 0:
            del active_potions[potion]
    
    current_speed = speed
    if "speed_potion" in active_potions:
        current_speed = speed * 1.5
    
    update_particles(dt)
    
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
            if event.key == pygame.K_b:
                equip_item("bow")
            if event.key == pygame.K_a:
                equip_item("iron_armor")
            if event.key == pygame.K_h:
                equip_item("health_potion")
            if event.key == pygame.K_k:
                equip_item("speed_potion")
            if event.key == pygame.K_j:
                equip_item("strength_potion")
            if event.key == pygame.K_f:
                if equipped_item and "potion" in ITEMS.get(equipped_item, {}).get("type", ""):
                    use_item()
                elif equipped_item == "food":
                    use_item()
    
    mouse_x, mouse_y = pygame.mouse.get_rel()
    pa += mouse_x * 0.005
    
    move_x = math.cos(pa) * current_speed
    move_y = math.sin(pa) * current_speed
    
    if keys[pygame.K_w]:
        px += move_x
        py += move_y
    if keys[pygame.K_a]:
        px -= move_y
        py += move_x
    if keys[pygame.K_d]:
        px += move_y
        py -= move_x
    
    cast_rays()
    draw_hud()
    
    send(px, py, pa)
    
    pygame.display.flip()

# Save character before exit
total_playtime = current_character["playtime"] + int(playtime_session)
save_character(char_id, health, armor, inventory, px, py, current_dimension, kills, 0, total_playtime)

pygame.quit()
