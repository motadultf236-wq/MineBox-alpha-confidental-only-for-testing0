import socket
import threading
import json
import uuid
import math
import random
import time

# Server settings
HOST = "0.0.0.0"
PORT = 5555

# Game state
players = {}
villagers = {}
zombies = {}
world = {}
items_on_ground = {}
player_lock = threading.Lock()

# Spawn settings
VILLAGER_SPAWN_RATE = 8
VILLAGER_COUNT = 8
ZOMBIE_SPAWN_RATE = 5
ZOMBIE_COUNT = 12

def spawn_villagers():
    """Spawn villagers in the world"""
    global villagers
    
    while True:
        time.sleep(VILLAGER_SPAWN_RATE)
        
        with player_lock:
            if len(villagers) < VILLAGER_COUNT:
                vid = str(uuid.uuid4())
                dimension = random.choice(["overworld", "nether", "end"])
                
                villagers[vid] = {
                    "id": vid,
                    "x": random.randint(0, 500),
                    "y": random.randint(0, 300),
                    "dimension": dimension,
                    "health": 20,
                    "vx": random.uniform(-0.5, 0.5),
                    "vy": random.uniform(-0.5, 0.5),
                    "type": "villager",
                    "state": "wander"  # wander, fleeing
                }

def spawn_zombies():
    """Spawn zombies in the world"""
    global zombies
    
    while True:
        time.sleep(ZOMBIE_SPAWN_RATE)
        
        with player_lock:
            if len(zombies) < ZOMBIE_COUNT:
                zid = str(uuid.uuid4())
                dimension = random.choice(["overworld", "nether", "end"])
                
                zombies[zid] = {
                    "id": zid,
                    "x": random.randint(0, 500),
                    "y": random.randint(0, 300),
                    "dimension": dimension,
                    "health": 20,
                    "vx": random.uniform(-1, 1),
                    "vy": random.uniform(-1, 1),
                    "type": "zombie",
                    "target": None,
                    "hunt_cooldown": 0
                }

def move_entities():
    """Move villagers and zombies with smart AI"""
    global villagers, zombies, items_on_ground
    
    while True:
        time.sleep(0.1)
        
        with player_lock:
            # Move and AI for villagers
            dead_villagers = []
            for vid, v in villagers.items():
                # Fleeing from zombies
                closest_zombie = None
                closest_dist = 150
                
                for zid, z in zombies.items():
                    if z.get("dimension") == v.get("dimension"):
                        dist = math.sqrt((v["x"] - z["x"])**2 + (v["y"] - z["y"])**2)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_zombie = z
                
                if closest_zombie:
                    # Flee from zombie
                    v["state"] = "fleeing"
                    dx = v["x"] - closest_zombie["x"]
                    dy = v["y"] - closest_zombie["y"]
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0:
                        v["vx"] = (dx / dist) * 1.2
                        v["vy"] = (dy / dist) * 1.2
                else:
                    v["state"] = "wander"
                    if random.random() < 0.05:
                        v["vx"] = random.uniform(-0.5, 0.5)
                        v["vy"] = random.uniform(-0.5, 0.5)
                
                # Move
                v["x"] += v["vx"]
                v["y"] += v["vy"]
                
                # Bounce
                if v["x"] < 0 or v["x"] > 1000:
                    v["vx"] *= -1
                if v["y"] < 0 or v["y"] > 600:
                    v["vy"] *= -1
                
                if v["health"] <= 0:
                    dead_villagers.append(vid)
                    # Drop loot
                    items_on_ground[str(uuid.uuid4())] = {
                        "type": random.choice(["stone", "wood", "food", "health_potion"]),
                        "x": v["x"],
                        "y": v["y"],
                        "dimension": v["dimension"],
                        "amount": random.randint(1, 3)
                    }
            
            for vid in dead_villagers:
                del villagers[vid]
            
            # Move and AI for zombies
            dead_zombies = []
            for zid, z in zombies.items():
                z["hunt_cooldown"] -= 0.1
                
                # Find closest player
                closest_player = None
                closest_dist = 300
                
                for pid, p in players.items():
                    if p.get("dimension") == z["dimension"]:
                        dist = math.sqrt((p["x"] - z["x"])**2 + (p["y"] - z["y"])**2)
                        if dist < closest_dist:
                            closest_dist = dist
                            closest_player = p
                
                # Smart hunting behavior
                if closest_player and closest_dist < 250:
                    if z["hunt_cooldown"] <= 0:
                        z["hunt_cooldown"] = random.uniform(1, 3)
                    
                    # Chase player
                    dx = closest_player["x"] - z["x"]
                    dy = closest_player["y"] - z["y"]
                    dist = math.sqrt(dx**2 + dy**2)
                    if dist > 0:
                        z["vx"] = (dx / dist) * 2.0
                        z["vy"] = (dy / dist) * 2.0
                else:
                    # Random wandering
                    if random.random() < 0.02:
                        z["vx"] = random.uniform(-1.5, 1.5)
                        z["vy"] = random.uniform(-1.5, 1.5)
                
                # Move
                z["x"] += z["vx"]
                z["y"] += z["vy"]
                
                # Bounce
                if z["x"] < 0 or z["x"] > 1000:
                    z["vx"] *= -1
                if z["y"] < 0 or z["y"] > 600:
                    z["vy"] *= -1
                
                if z["health"] <= 0:
                    dead_zombies.append(zid)
                    # Drop loot - better loot
                    loot_type = random.choice(["food", "food", "stone", "wood", "strength_potion"])
                    items_on_ground[str(uuid.uuid4())] = {
                        "type": loot_type,
                        "x": z["x"],
                        "y": z["y"],
                        "dimension": z["dimension"],
                        "amount": random.randint(2, 5)
                    }
            
            for zid in dead_zombies:
                del zombies[zid]

def handle_player(conn, addr):
    """Handle individual player connection"""
    player_id = str(uuid.uuid4())
    
    players[player_id] = {
        "id": player_id,
        "x": 100,
        "y": 100,
        "a": 0,
        "dimension": "overworld",
        "inventory": {},
        "health": 100,
        "equipped": None,
        "armor": "none",
        "addr": addr
    }
    
    print(f"Player {player_id} connected from {addr}")
    
    try:
        while True:
            data = conn.recv(4096).decode()
            
            if not data:
                break
            
            try:
                msg = json.loads(data)
                
                with player_lock:
                    # Update player position
                    if "id" in msg and msg["id"] in players:
                        players[msg["id"]]["x"] = msg.get("x", 100)
                        players[msg["id"]]["y"] = msg.get("y", 100)
                        players[msg["id"]]["a"] = msg.get("a", 0)
                        players[msg["id"]]["dimension"] = msg.get("dimension", "overworld")
                        players[msg["id"]]["inventory"] = msg.get("inventory", {})
                        players[msg["id"]]["health"] = msg.get("health", 100)
                        players[msg["id"]]["equipped"] = msg.get("equipped")
                        players[msg["id"]]["armor"] = msg.get("armor", "none")
                    
                    # Handle actions
                    if "action" in msg:
                        action = msg["action"]
                        
                        # Mining
                        if action.get("type") == "mine":
                            x = action.get("x")
                            y = action.get("y")
                            dim = msg.get("dimension", "overworld")
                            key = (x, y, dim)
                            world[key] = 0
                        
                        # Attack villager
                        elif action.get("type") == "attack_villager":
                            vid = action.get("id")
                            damage = action.get("damage", 5)
                            if vid in villagers:
                                villagers[vid]["health"] -= damage
                        
                        # Attack zombie
                        elif action.get("type") == "attack_zombie":
                            zid = action.get("id")
                            damage = action.get("damage", 5)
                            if zid in zombies:
                                zombies[zid]["health"] -= damage
                        
                        # Pickup item
                        elif action.get("type") == "pickup_item":
                            item_id = action.get("item_id")
                            if item_id in items_on_ground:
                                del items_on_ground[item_id]
                        
                        # Dimension change
                        elif action.get("type") == "dimension_change":
                            new_dim = action.get("dimension")
                            players[msg["id"]]["dimension"] = new_dim
                    
                    # Broadcast state
                    state = {
                        "players": players,
                        "villagers": villagers,
                        "zombies": zombies,
                        "world": world,
                        "items": items_on_ground
                    }
                
                # Send game state back
                conn.send(json.dumps(state).encode())
            
            except json.JSONDecodeError:
                pass
    
    except Exception as e:
        print(f"Error handling player {player_id}: {e}")
    
    finally:
        with player_lock:
            if player_id in players:
                del players[player_id]
        conn.close()
        print(f"Player {player_id} disconnected")

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    
    print(f"MineBox Enhanced Server started on {HOST}:{PORT}")
    
    # Start background threads
    threading.Thread(target=spawn_villagers, daemon=True).start()
    threading.Thread(target=spawn_zombies, daemon=True).start()
    threading.Thread(target=move_entities, daemon=True).start()
    
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_player, args=(conn, addr), daemon=True).start()
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        server.close()

if __name__ == "__main__":
    main()
