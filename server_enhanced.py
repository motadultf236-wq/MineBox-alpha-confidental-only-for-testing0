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
world = {}
player_lock = threading.Lock()

# Villager spawn settings
VILLAGER_SPAWN_RATE = 5  # Spawn every 5 seconds
VILLAGER_COUNT = 10

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
                    "vx": random.uniform(-1, 1),
                    "vy": random.uniform(-1, 1)
                }

def move_villagers():
    """Move villagers around the world"""
    global villagers
    
    while True:
        time.sleep(0.1)
        
        with player_lock:
            dead_villagers = []
            
            for vid, v in villagers.items():
                # Simple movement
                v["x"] += v["vx"]
                v["y"] += v["vy"]
                
                # Bounce off edges
                if v["x"] < 0 or v["x"] > 1000:
                    v["vx"] *= -1
                if v["y"] < 0 or v["y"] > 600:
                    v["vy"] *= -1
                
                # Remove if dead
                if v["health"] <= 0:
                    dead_villagers.append(vid)
            
            for vid in dead_villagers:
                del villagers[vid]

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
                    
                    # Handle actions
                    if "action" in msg:
                        action = msg["action"]
                        
                        # Mining action
                        if action.get("type") == "mine":
                            x = action.get("x")
                            y = action.get("y")
                            dim = msg.get("dimension", "overworld")
                            key = (x, y, dim)
                            
                            if key in world:
                                world[key] = 0
                        
                        # Attack villager
                        elif action.get("type") == "attack_villager":
                            vid = action.get("id")
                            if vid in villagers:
                                villagers[vid]["health"] -= 10
                        
                        # Dimension change
                        elif action.get("type") == "dimension_change":
                            new_dim = action.get("dimension")
                            players[msg["id"]]["dimension"] = new_dim
                    
                    # Broadcast state to all players
                    state = {
                        "players": players,
                        "villagers": villagers,
                        "world": world
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

def broadcast_state():
    """Periodically broadcast game state to all players"""
    while True:
        time.sleep(0.05)
        
        with player_lock:
            state = {
                "players": players,
                "villagers": villagers,
                "world": world
            }
            state_json = json.dumps(state).encode()
            
            for pid, player in list(players.items()):
                try:
                    # Note: This is simplified. In production, maintain persistent connections
                    pass
                except:
                    pass

def main():
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(5)
    
    print(f"MineBox Enhanced Server started on {HOST}:{PORT}")
    
    # Start background threads
    threading.Thread(target=spawn_villagers, daemon=True).start()
    threading.Thread(target=move_villagers, daemon=True).start()
    threading.Thread(target=broadcast_state, daemon=True).start()
    
    try:
        while True:
            conn, addr = server.accept()
            threading.Thread(target=handle_player, args=(conn, addr), daemon=True).start()
    
    except KeyboardInterrupt:
        print("\nServer shutting down...")
        server.close()

if __name__ == "__main__":
    main()
