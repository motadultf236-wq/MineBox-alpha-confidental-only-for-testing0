import pygame
import subprocess
import sys
import os

pygame.init()

# Screen settings
WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
clock = pygame.time.Clock()
pygame.display.set_caption("MineBox - Launcher")

# Colors
BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
CYAN = (0, 255, 255)
HIGHLIGHT = (0, 200, 255)
DARK_GRAY = (40, 40, 40)
GREEN = (60, 150, 70)

# Fonts
font_title = pygame.font.Font(None, 48)
font_menu = pygame.font.Font(None, 32)
font_small = pygame.font.Font(None, 20)

# ASCII Art Logo
LOGO = [
    "███╗   ███╗██╗███╗   ██╗███████╗",
    "████╗ ████║██║████╗  ██║██╔════╝",
    "██╔████╔██║██║██╔██╗ ██║█████╗",
    "██║╚██╔╝██║██║██║╚██╗██║██╔══╝",
    "██║ ╚═╝ ██║██║██║ ╚████║███████╗",
    "╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝",
    "██████╗  ██████╗ ██╗  ██╗",
    "██╔══██╗██╔═══██╗╚██╗██╔╝",
    "██████╔╝██║   ██║ ╚███╔╝",
    "██╔══██╗██║   ██║ ██╔██╗",
    "██████╔╝╚██████╔╝██╔╝ ██╗",
    "╚═════╝  ╚═════╝ ╚═╝  ╚═╝"
]

# Menu options
menu_options = [
    {"name": "SINGLE-PLAYER (BETA)", "file": "minebox.py", "desc": "Solo experience with menu & music"},
    {"name": "MULTIPLAYER (FULL GAME)", "file": "minebox_backup.py", "desc": "Play with friends on LAN"},
    {"name": "QUIT", "file": None, "desc": "Exit launcher"}
]

selected_option = 0

def draw_launcher():
    screen.fill(BLACK)
    
    # Draw logo
    y_offset = 30
    font_logo = pygame.font.Font(None, 16)
    for line in LOGO:
        text_surf = font_logo.render(line, True, CYAN)
        text_rect = text_surf.get_rect(center=(WIDTH // 2, y_offset))
        screen.blit(text_surf, text_rect)
        y_offset += 14
    
    # Draw "LAUNCHER" subtitle
    subtitle = font_title.render("LAUNCHER", True, GREEN)
    subtitle_rect = subtitle.get_rect(center=(WIDTH // 2, y_offset + 10))
    screen.blit(subtitle, subtitle_rect)
    
    # Draw menu options
    menu_y_start = 280
    menu_spacing = 70
    
    for i, option in enumerate(menu_options):
        if i == selected_option:
            # Draw selection box background
            box_width = 500
            box_height = 55
            box_x = WIDTH // 2 - box_width // 2
            box_y = menu_y_start + i * menu_spacing - 5
            
            pygame.draw.rect(screen, HIGHLIGHT, (box_x, box_y, box_width, box_height), 3)
            
            color = HIGHLIGHT
            prefix = "▶ "
        else:
            color = WHITE
            prefix = "  "
        
        # Draw option name
        name_surf = font_menu.render(prefix + option["name"], True, color)
        name_rect = name_surf.get_rect(center=(WIDTH // 2, menu_y_start + i * menu_spacing))
        screen.blit(name_surf, name_rect)
        
        # Draw description
        desc_surf = font_small.render(option["desc"], True, (150, 150, 150))
        desc_rect = desc_surf.get_rect(center=(WIDTH // 2, menu_y_start + i * menu_spacing + 25))
        screen.blit(desc_surf, desc_rect)
    
    # Draw instructions
    instructions = font_small.render("Use UP/DOWN arrows to select, ENTER to launch", True, (100, 100, 100))
    instructions_rect = instructions.get_rect(center=(WIDTH // 2, HEIGHT - 30))
    screen.blit(instructions, instructions_rect)
    
    pygame.display.flip()

def launch_game(filename):
    """Launch a game file"""
    if filename is None:
        return False
    
    # Get the directory of the launcher script
    base_dir = os.path.dirname(os.path.abspath(__file__))
    game_path = os.path.join(base_dir, filename)
    
    if not os.path.exists(game_path):
        print(f"Error: {filename} not found!")
        return False
    
    try:
        # Launch the game in a new process
        subprocess.Popen([sys.executable, game_path])
        return True
    except Exception as e:
        print(f"Error launching game: {e}")
        return False

def launcher_loop():
    global selected_option
    
    running = True
    while running:
        clock.tick(60)
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False
            
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_UP:
                    selected_option = (selected_option - 1) % len(menu_options)
                
                if event.key == pygame.K_DOWN:
                    selected_option = (selected_option + 1) % len(menu_options)
                
                if event.key == pygame.K_RETURN:
                    selected_item = menu_options[selected_option]
                    
                    if selected_item["file"] is None:  # QUIT
                        return False
                    else:
                        # Launch the game
                        if launch_game(selected_item["file"]):
                            print(f"Launching {selected_item['name']}...")
                            return True
                        else:
                            print("Failed to launch game")
        
        draw_launcher()
    
    return False

if __name__ == "__main__":
    launcher_loop()
    pygame.quit()
