import pygame
import sys
from account_system import (
    register_user, login_user, create_character, 
    get_user_characters, load_character, get_leaderboard,
    get_player_profile
)

pygame.init()

WIDTH, HEIGHT = 900, 600
screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("MineBox Enhanced - Login")
clock = pygame.time.Clock()

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
DARK_GRAY = (40, 40, 40)
LIGHT_GRAY = (100, 100, 100)
BLUE = (70, 140, 220)
GREEN = (60, 180, 60)
RED = (255, 100, 100)
GOLD = (255, 200, 50)

# Button class
class Button:
    def __init__(self, x, y, width, height, text, color=BLUE):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = text
        self.color = color
        self.hover = False
    
    def draw(self, surface):
        color = tuple(min(255, c + 50) for c in self.color) if self.hover else self.color
        pygame.draw.rect(surface, color, self.rect)
        pygame.draw.rect(surface, WHITE, self.rect, 2)
        
        font = pygame.font.Font(None, 24)
        text_surf = font.render(self.text, True, WHITE)
        text_rect = text_surf.get_rect(center=self.rect.center)
        surface.blit(text_surf, text_rect)
    
    def is_clicked(self, pos):
        return self.rect.collidepoint(pos)
    
    def update_hover(self, pos):
        self.hover = self.rect.collidepoint(pos)

# Text input class
class TextInput:
    def __init__(self, x, y, width, height, placeholder=""):
        self.rect = pygame.Rect(x, y, width, height)
        self.text = ""
        self.placeholder = placeholder
        self.active = False
    
    def draw(self, surface):
        color = BLUE if self.active else LIGHT_GRAY
        pygame.draw.rect(surface, DARK_GRAY, self.rect)
        pygame.draw.rect(surface, color, self.rect, 2)
        
        font = pygame.font.Font(None, 20)
        display_text = self.text if self.text else self.placeholder
        text_color = WHITE if self.text else LIGHT_GRAY
        text_surf = font.render(display_text, True, text_color)
        surface.blit(text_surf, (self.rect.x + 10, self.rect.y + 10))
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.active = self.rect.collidepoint(event.pos)
        elif event.type == pygame.KEYDOWN and self.active:
            if event.key == pygame.K_BACKSPACE:
                self.text = self.text[:-1]
            elif event.unicode.isprintable():
                self.text += event.unicode

# Screen classes
class LoginScreen:
    def __init__(self):
        self.username_input = TextInput(200, 150, 500, 40, "Username")
        self.password_input = TextInput(200, 220, 500, 40, "Password")
        self.login_btn = Button(250, 300, 150, 50, "LOGIN", GREEN)
        self.register_btn = Button(500, 300, 150, 50, "REGISTER", BLUE)
        self.message = ""
        self.message_time = 0
    
    def draw(self):
        screen.fill(DARK_GRAY)
        
        font_large = pygame.font.Font(None, 48)
        title = font_large.render("MineBox Enhanced", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 50))
        
        self.username_input.draw(screen)
        self.password_input.draw(screen)
        
        self.login_btn.draw(screen)
        self.register_btn.draw(screen)
        
        if self.message and self.message_time > 0:
            font_small = pygame.font.Font(None, 20)
            msg_surf = font_small.render(self.message, True, GREEN if "success" in self.message.lower() else RED)
            screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, 380))
    
    def update(self, dt):
        self.message_time -= dt
    
    def handle_event(self, event):
        self.username_input.handle_event(event)
        self.password_input.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.login_btn.update_hover(event.pos)
            self.register_btn.update_hover(event.pos)
            
            if self.login_btn.is_clicked(event.pos):
                if self.username_input.text and self.password_input.text:
                    success, user_id, msg = login_user(self.username_input.text, self.password_input.text)
                    if success:
                        return "character_select", user_id
                    else:
                        self.message = msg
                        self.message_time = 3
            
            if self.register_btn.is_clicked(event.pos):
                return "register", None
        
        if event.type == pygame.MOUSEMOTION:
            self.login_btn.update_hover(event.pos)
            self.register_btn.update_hover(event.pos)
        
        return None, None

class RegisterScreen:
    def __init__(self):
        self.username_input = TextInput(200, 120, 500, 40, "Username")
        self.password_input = TextInput(200, 180, 500, 40, "Password")
        self.email_input = TextInput(200, 240, 500, 40, "Email (optional)")
        self.register_btn = Button(250, 320, 150, 50, "CREATE", GREEN)
        self.back_btn = Button(500, 320, 150, 50, "BACK", BLUE)
        self.message = ""
        self.message_time = 0
    
    def draw(self):
        screen.fill(DARK_GRAY)
        
        font_large = pygame.font.Font(None, 48)
        title = font_large.render("Create Account", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 30))
        
        self.username_input.draw(screen)
        self.password_input.draw(screen)
        self.email_input.draw(screen)
        
        self.register_btn.draw(screen)
        self.back_btn.draw(screen)
        
        if self.message and self.message_time > 0:
            font_small = pygame.font.Font(None, 20)
            msg_surf = font_small.render(self.message, True, GREEN if "success" in self.message.lower() else RED)
            screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, 400))
    
    def update(self, dt):
        self.message_time -= dt
    
    def handle_event(self, event):
        self.username_input.handle_event(event)
        self.password_input.handle_event(event)
        self.email_input.handle_event(event)
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.register_btn.update_hover(event.pos)
            self.back_btn.update_hover(event.pos)
            
            if self.register_btn.is_clicked(event.pos):
                if self.username_input.text and self.password_input.text:
                    success, user_id, msg = register_user(
                        self.username_input.text,
                        self.password_input.text,
                        self.email_input.text
                    )
                    if success:
                        self.message = "Account created! Redirecting..."
                        self.message_time = 2
                        return "login", None
                    else:
                        self.message = msg
                        self.message_time = 3
            
            if self.back_btn.is_clicked(event.pos):
                return "login", None
        
        if event.type == pygame.MOUSEMOTION:
            self.register_btn.update_hover(event.pos)
            self.back_btn.update_hover(event.pos)
        
        return None, None

class CharacterSelectScreen:
    def __init__(self, user_id):
        self.user_id = user_id
        self.characters = get_user_characters(user_id)
        self.character_buttons = []
        self.new_char_btn = Button(300, 450, 300, 50, "CREATE NEW CHARACTER", GREEN)
        self.new_char_input = None
        self.creating_char = False
        self.message = ""
        self.message_time = 0
        
        self.update_buttons()
    
    def update_buttons(self):
        self.character_buttons = []
        for i, char in enumerate(self.characters):
            y = 100 + i * 80
            btn = Button(100, y, 700, 70, 
                        f"{char['char_name']} | Level {char['level']} | Kills: {char['kills']}", 
                        BLUE)
            self.character_buttons.append((btn, char))
    
    def draw(self):
        screen.fill(DARK_GRAY)
        
        font_large = pygame.font.Font(None, 48)
        title = font_large.render("Select Character", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        
        for btn, _ in self.character_buttons:
            btn.draw(screen)
        
        self.new_char_btn.draw(screen)
        
        if self.creating_char and self.new_char_input:
            self.new_char_input.draw(screen)
        
        if self.message and self.message_time > 0:
            font_small = pygame.font.Font(None, 20)
            msg_surf = font_small.render(self.message, True, GREEN if "success" in self.message.lower() else RED)
            screen.blit(msg_surf, (WIDTH//2 - msg_surf.get_width()//2, 520))
    
    def update(self, dt):
        self.message_time -= dt
    
    def handle_event(self, event):
        if self.creating_char and self.new_char_input:
            self.new_char_input.handle_event(event)
            
            if event.type == pygame.KEYDOWN and event.key == pygame.K_RETURN:
                if self.new_char_input.text:
                    success, char_id, msg = create_character(self.user_id, self.new_char_input.text)
                    if success:
                        self.message = msg
                        self.characters = get_user_characters(self.user_id)
                        self.update_buttons()
                        self.creating_char = False
                    else:
                        self.message = msg
                        self.message_time = 3
            return None, None
        
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.new_char_btn.update_hover(event.pos)
            
            if self.new_char_btn.is_clicked(event.pos):
                self.creating_char = True
                self.new_char_input = TextInput(200, 400, 500, 40, "Character Name")
            
            for btn, char in self.character_buttons:
                btn.update_hover(event.pos)
                if btn.is_clicked(event.pos):
                    return "game", char["char_id"]
        
        if event.type == pygame.MOUSEMOTION:
            self.new_char_btn.update_hover(event.pos)
            for btn, _ in self.character_buttons:
                btn.update_hover(event.pos)
        
        return None, None

class LeaderboardScreen:
    def __init__(self):
        self.leaderboard = get_leaderboard(10)
        self.back_btn = Button(300, 500, 300, 50, "BACK TO LOGIN", BLUE)
    
    def draw(self):
        screen.fill(DARK_GRAY)
        
        font_large = pygame.font.Font(None, 48)
        title = font_large.render("Leaderboard - Top Killers", True, GOLD)
        screen.blit(title, (WIDTH//2 - title.get_width()//2, 20))
        
        font_small = pygame.font.Font(None, 18)
        y = 80
        
        header = "RANK | PLAYER | CHARACTER | KILLS | DEATHS | LEVEL"
        header_surf = font_small.render(header, True, GOLD)
        screen.blit(header_surf, (50, y))
        y += 30
        
        for entry in self.leaderboard:
            text = f"{entry['rank']:2d}. | {entry['username']:15s} | {entry['character']:15s} | {entry['kills']:4d} | {entry['deaths']:4d} | {entry['level']:2d}"
            text_surf = font_small.render(text, True, WHITE)
            screen.blit(text_surf, (50, y))
            y += 25
        
        self.back_btn.draw(screen)
    
    def handle_event(self, event):
        if event.type == pygame.MOUSEBUTTONDOWN:
            self.back_btn.update_hover(event.pos)
            if self.back_btn.is_clicked(event.pos):
                return "login", None
        
        if event.type == pygame.MOUSEMOTION:
            self.back_btn.update_hover(event.pos)
        
        return None, None

# Main loop
def main():
    screen_state = "login"
    user_id = None
    char_id = None
    
    screens = {
        "login": LoginScreen(),
        "register": RegisterScreen(),
        "character_select": None,
        "leaderboard": LeaderboardScreen()
    }
    
    running = True
    
    while running:
        dt = clock.tick(60) / 1000.0
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            
            if screen_state == "login":
                next_state, data = screens["login"].handle_event(event)
                if next_state == "character_select":
                    user_id = data
                    screens["character_select"] = CharacterSelectScreen(user_id)
                    screen_state = "character_select"
                elif next_state == "register":
                    screen_state = "register"
            
            elif screen_state == "register":
                next_state, _ = screens["register"].handle_event(event)
                if next_state:
                    screen_state = next_state
            
            elif screen_state == "character_select":
                next_state, data = screens["character_select"].handle_event(event)
                if next_state == "game":
                    char_id = data
                    import subprocess
                    import json
                    
                    char_data = load_character(char_id)
                    if char_data:
                        with open("current_character.json", "w") as f:
                            json.dump(char_data, f)
                        
                        subprocess.Popen([sys.executable, "minebox_enhanced.py"])
                        running = False
        
        if screen_state == "login":
            screens["login"].update(dt)
            screens["login"].draw()
        elif screen_state == "register":
            screens["register"].update(dt)
            screens["register"].draw()
        elif screen_state == "character_select":
            screens["character_select"].update(dt)
            screens["character_select"].draw()
        elif screen_state == "leaderboard":
            screens["leaderboard"].draw()
        
        pygame.display.flip()
    
    pygame.quit()

if __name__ == "__main__":
    main()
