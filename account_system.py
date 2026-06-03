import sqlite3
import hashlib
import json
import os
from datetime import datetime

# Database setup
DB_FILE = "minebox_accounts.db"

def init_database():
    """Initialize the database"""
    conn = sqlite3.connect(DB_FILE)
    c = conn.cursor()
    
    # Users table
    c.execute('''CREATE TABLE IF NOT EXISTS users (
        user_id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        email TEXT,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_login TIMESTAMP
    )''')
    
    # Characters table
    c.execute('''CREATE TABLE IF NOT EXISTS characters (
        char_id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        char_name TEXT NOT NULL,
        level INTEGER DEFAULT 1,
        experience INTEGER DEFAULT 0,
        kills INTEGER DEFAULT 0,
        deaths INTEGER DEFAULT 0,
        playtime INTEGER DEFAULT 0,
        dimension TEXT DEFAULT 'overworld',
        x REAL DEFAULT 100.0,
        y REAL DEFAULT 100.0,
        health INTEGER DEFAULT 100,
        armor TEXT DEFAULT 'none',
        inventory TEXT DEFAULT '{}',
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        last_played TIMESTAMP,
        FOREIGN KEY(user_id) REFERENCES users(user_id)
    )''')
    
    # Stats table
    c.execute('''CREATE TABLE IF NOT EXISTS stats (
        stat_id INTEGER PRIMARY KEY AUTOINCREMENT,
        char_id INTEGER NOT NULL,
        total_blocks_mined INTEGER DEFAULT 0,
        total_distance_traveled REAL DEFAULT 0.0,
        total_damage_dealt INTEGER DEFAULT 0,
        total_damage_taken INTEGER DEFAULT 0,
        villagers_killed INTEGER DEFAULT 0,
        zombies_killed INTEGER DEFAULT 0,
        potions_used INTEGER DEFAULT 0,
        FOREIGN KEY(char_id) REFERENCES characters(char_id)
    )''')
    
    conn.commit()
    conn.close()

def hash_password(password):
    """Hash password with salt"""
    return hashlib.sha256(password.encode()).hexdigest()

def register_user(username, password, email=""):
    """Register a new user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        password_hash = hash_password(password)
        c.execute("INSERT INTO users (username, password_hash, email) VALUES (?, ?, ?)",
                 (username, password_hash, email))
        conn.commit()
        user_id = c.lastrowid
        conn.close()
        
        return True, user_id, "Account created successfully!"
    except sqlite3.IntegrityError:
        return False, None, "Username already exists!"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def login_user(username, password):
    """Login a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        password_hash = hash_password(password)
        c.execute("SELECT user_id FROM users WHERE username = ? AND password_hash = ?",
                 (username, password_hash))
        result = c.fetchone()
        
        if result:
            user_id = result[0]
            c.execute("UPDATE users SET last_login = CURRENT_TIMESTAMP WHERE user_id = ?", (user_id,))
            conn.commit()
            conn.close()
            return True, user_id, "Login successful!"
        else:
            conn.close()
            return False, None, "Invalid username or password!"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def create_character(user_id, char_name):
    """Create a new character for a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("SELECT char_id FROM characters WHERE user_id = ? AND char_name = ?",
                 (user_id, char_name))
        if c.fetchone():
            return False, None, "Character name already exists!"
        
        c.execute("""INSERT INTO characters 
                    (user_id, char_name, inventory) 
                    VALUES (?, ?, ?)""",
                 (user_id, char_name, json.dumps({})))
        
        char_id = c.lastrowid
        c.execute("INSERT INTO stats (char_id) VALUES (?)", (char_id,))
        
        conn.commit()
        conn.close()
        
        return True, char_id, f"Character '{char_name}' created!"
    except Exception as e:
        return False, None, f"Error: {str(e)}"

def get_user_characters(user_id):
    """Get all characters for a user"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""SELECT char_id, char_name, level, kills, deaths, playtime, last_played 
                    FROM characters WHERE user_id = ?""", (user_id,))
        characters = c.fetchall()
        conn.close()
        
        char_list = []
        for char in characters:
            char_list.append({
                "char_id": char[0],
                "char_name": char[1],
                "level": char[2],
                "kills": char[3],
                "deaths": char[4],
                "playtime": char[5],
                "last_played": char[6]
            })
        
        return char_list
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def load_character(char_id):
    """Load character data"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""SELECT char_name, level, health, armor, inventory, 
                            x, y, dimension, kills, deaths, playtime
                    FROM characters WHERE char_id = ?""", (char_id,))
        result = c.fetchone()
        conn.close()
        
        if result:
            return {
                "char_id": char_id,
                "char_name": result[0],
                "level": result[1],
                "health": result[2],
                "armor": result[3],
                "inventory": json.loads(result[4]),
                "x": result[5],
                "y": result[6],
                "dimension": result[7],
                "kills": result[8],
                "deaths": result[9],
                "playtime": result[10]
            }
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def save_character(char_id, health, armor, inventory, x, y, dimension, kills, deaths, playtime):
    """Save character data"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""UPDATE characters 
                    SET health = ?, armor = ?, inventory = ?, 
                        x = ?, y = ?, dimension = ?, 
                        kills = ?, deaths = ?, playtime = ?,
                        last_played = CURRENT_TIMESTAMP
                    WHERE char_id = ?""",
                 (health, armor, json.dumps(inventory), x, y, dimension, 
                  kills, deaths, playtime, char_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error saving character: {str(e)}")
        return False

def get_leaderboard(limit=10):
    """Get top players by kills"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""SELECT u.username, c.char_name, c.kills, c.deaths, c.level, c.playtime
                    FROM characters c
                    JOIN users u ON c.user_id = u.user_id
                    ORDER BY c.kills DESC
                    LIMIT ?""", (limit,))
        
        results = c.fetchall()
        conn.close()
        
        leaderboard = []
        for i, row in enumerate(results, 1):
            leaderboard.append({
                "rank": i,
                "username": row[0],
                "character": row[1],
                "kills": row[2],
                "deaths": row[3],
                "level": row[4],
                "playtime": row[5]
            })
        
        return leaderboard
    except Exception as e:
        print(f"Error: {str(e)}")
        return []

def get_player_profile(username):
    """Get player profile"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""SELECT u.user_id, u.created_at, 
                           COUNT(c.char_id) as total_chars,
                           SUM(c.kills) as total_kills,
                           SUM(c.playtime) as total_playtime
                    FROM users u
                    LEFT JOIN characters c ON u.user_id = c.user_id
                    WHERE u.username = ?
                    GROUP BY u.user_id""", (username,))
        
        result = c.fetchone()
        
        if result:
            profile = {
                "username": username,
                "created_at": result[1],
                "total_characters": result[2] or 0,
                "total_kills": result[3] or 0,
                "total_playtime": result[4] or 0,
                "characters": []
            }
            
            c.execute("""SELECT char_name, level, kills, deaths, playtime
                        FROM characters WHERE user_id = ?""", (result[0],))
            
            for char in c.fetchall():
                profile["characters"].append({
                    "name": char[0],
                    "level": char[1],
                    "kills": char[2],
                    "deaths": char[3],
                    "playtime": char[4]
                })
            
            conn.close()
            return profile
        
        conn.close()
        return None
    except Exception as e:
        print(f"Error: {str(e)}")
        return None

def update_character_stats(char_id, kills=0, deaths=0, playtime=0):
    """Update character stats"""
    try:
        conn = sqlite3.connect(DB_FILE)
        c = conn.cursor()
        
        c.execute("""UPDATE characters 
                    SET kills = kills + ?,
                        deaths = deaths + ?,
                        playtime = playtime + ?
                    WHERE char_id = ?""",
                 (kills, deaths, playtime, char_id))
        
        conn.commit()
        conn.close()
        return True
    except Exception as e:
        print(f"Error: {str(e)}")
        return False

# Initialize database on import
if not os.path.exists(DB_FILE):
    init_database()
