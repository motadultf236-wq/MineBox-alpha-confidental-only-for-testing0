# MineBox Alpha

A 3D raycasting game engine with LAN multiplayer support, inspired by classic first-person shooters like Wolfenstein 3D.

## Features

- **3D Raycasting Rendering** - Fast software-based 3D graphics
- **Procedurally Generated World** - Infinite terrain with sine-wave height variation
- **Texture Mapping** - Real textures on walls, grass, and wood blocks
- **Distance-Based Lighting** - Dynamic shading for depth perception
- **LAN Multiplayer** - Real-time player synchronization via local network
- **Mining System** - Break blocks in the world
- **Smooth Controls** - WASD movement + mouse look

## Requirements

- Python 3.7+
- pygame
- socket (standard library)
- threading (standard library)
- json (standard library)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/motadultf236-wq/MineBox-alpha-confidental-only-for-testing0.git
cd MineBox-alpha-confidental-only-for-testing0
```

2. Install dependencies:
```bash
pip install pygame
```

3. Create an `assets` folder and add textures (or use built-in fallbacks):
```bash
mkdir assets
```

## Running the Game

### Start the Server (Host)

```bash
python server.py
```

The server will start on `127.0.0.1:5555` and listen for client connections.

### Start the Client (Players)

```bash
python minebox_backup.py
```

Multiple clients can connect to the same server to play together.

## Controls

| Key | Action |
|-----|--------|
| **W** | Move Forward |
| **S** | Move Backward |
| **A** | Strafe Left |
| **D** | Strafe Right |
| **Mouse** | Look Around |
| **Space** | Mine Block |

## Configuration

Edit the following variables in `minebox_backup.py` to customize:

```python
WIDTH, HEIGHT = 900, 600          # Screen resolution
FOV = math.pi / 3                 # Field of view (radians)
RAYS = 120                        # Number of raycasts per frame
MAX_DEPTH = 400                   # Maximum render distance
TILE = 64                         # Block size in pixels
SERVER_IP = "127.0.0.1"           # Server address
PORT = 5555                       # Server port
```

## Game Mechanics

- **Mining** - Press SPACE to break blocks in front of you
- **World Generation** - Terrain height is procedurally generated with grass tops and wood walls
- **Multiplayer** - See other players as blue circles in real-time
- **Collision** - Move freely through the world (collision detection coming soon)

## Architecture

- **minebox_backup.py** - Client-side game engine with raycasting renderer
- **server.py** - Multiplayer server for player synchronization

## Future Improvements

- [ ] Block placement system
- [ ] Collision detection
- [ ] Inventory system
- [ ] Different block types
- [ ] Better networking optimization
- [ ] Sprinting mechanics
- [ ] Ceiling/floor textures
- [ ] Chat system
- [ ] Performance optimizations

## Troubleshooting

**"Connection refused" error**
- Make sure the server is running before starting clients
- Check that `SERVER_IP` and `PORT` match in both files

**Low FPS**
- Reduce `RAYS` for faster rendering
- Lower `MAX_DEPTH` to render less distance
- Increase `TILE` size for larger blocks

**Missing textures**
- Place PNG files in the `assets/` folder: `wall.png`, `grass.png`, `wood.png`
- Each texture should be at least 64x64 pixels
- Without assets, the game uses fallback colors

## License

Alpha testing only - confidential

## Author

motadultf236-wq
