import tkinter as tk
from tkinter import font
import subprocess
import sys
import os

class MineBoxLauncher:
    def __init__(self, root):
        self.root = root
        self.root.title("MineBox - Launcher")
        self.root.geometry("900x600")
        self.root.configure(bg="#141928")
        self.root.resizable(False, False)
        
        # Center window on screen
        self.root.update_idletasks()
        x = (self.root.winfo_screenwidth() // 2) - (450)
        y = (self.root.winfo_screenheight() // 2) - (300)
        self.root.geometry(f"+{x}+{y}")
        
        self.selected_option = 0
        self.menu_options = [
            {"name": "SINGLE-PLAYER (BETA)", "file": "minebox.py", "desc": "Solo experience with menu & music"},
            {"name": "MULTIPLAYER (FULL GAME)", "file": "minebox_backup.py", "desc": "Play with friends on LAN"},
            {"name": "QUIT", "file": None, "desc": "Exit launcher"}
        ]
        
        self.setup_ui()
        self.bind_keys()
        self.update_display()
    
    def setup_ui(self):
        # Main frame
        main_frame = tk.Frame(self.root, bg="#141928")
        main_frame.pack(fill=tk.BOTH, expand=True)
        
        # Logo frame
        logo_frame = tk.Frame(main_frame, bg="#141928")
        logo_frame.pack(pady=20)
        
        # ASCII Logo
        logo_text = """███╗   ███╗██╗███╗   ██╗███████╗
████╗ ████║██║████╗  ██║██╔════╝
██╔████╔██║██║██╔██╗ ██║█████╗
██║╚██╔╝██║██║██║╚██╗██║██╔══╝
██║ ╚═╝ ██║██║██║ ╚████║███████╗
╚═╝     ╚═╝╚═╝╚═╝  ╚═══╝╚══════╝

██████╗  ██████╗ ██╗  ██╗
██╔══██╗██╔═══██╗╚██╗██╔╝
██████╔╝██║   ██║ ╚███╔╝
██╔══██╗██║   ██║ ██╔██╗
██████╔╝╚██████╔╝██╔╝ ██╗
╚═════╝  ╚═════╝ ╚═╝  ╚═╝"""
        
        logo_font = font.Font(family="Courier", size=8)
        logo_label = tk.Label(logo_frame, text=logo_text, font=logo_font, fg="#00FFFF", bg="#141928")
        logo_label.pack()
        
        # Launcher title
        title_font = font.Font(family="Courier", size=24, weight="bold")
        title_label = tk.Label(main_frame, text="LAUNCHER", font=title_font, fg="#3C9646", bg="#141928")
        title_label.pack(pady=10)
        
        # Menu frame
        self.menu_frame = tk.Frame(main_frame, bg="#141928")
        self.menu_frame.pack(pady=20, expand=True)
        
        # Create menu buttons
        self.menu_labels = []
        for i in range(len(self.menu_options)):
            label = tk.Label(
                self.menu_frame,
                text="",
                font=font.Font(family="Courier", size=12),
                bg="#141928",
                fg="white",
                padx=20,
                pady=10
            )
            label.pack(pady=10)
            self.menu_labels.append(label)
        
        # Instructions frame
        inst_frame = tk.Frame(main_frame, bg="#141928")
        inst_frame.pack(side=tk.BOTTOM, pady=20)
        
        inst_font = font.Font(family="Courier", size=9)
        instructions = tk.Label(
            inst_frame,
            text="Use UP/DOWN arrows to select, ENTER to launch",
            font=inst_font,
            fg="#646464",
            bg="#141928"
        )
        instructions.pack()
    
    def bind_keys(self):
        self.root.bind("<Up>", lambda e: self.move_selection(-1))
        self.root.bind("<Down>", lambda e: self.move_selection(1))
        self.root.bind("<Return>", lambda e: self.launch_selected())
    
    def move_selection(self, direction):
        self.selected_option = (self.selected_option + direction) % len(self.menu_options)
        self.update_display()
    
    def update_display(self):
        for i, label in enumerate(self.menu_labels):
            option = self.menu_options[i]
            
            if i == self.selected_option:
                # Highlighted option
                label.configure(
                    text=f"▶ {option['name']}\n  {option['desc']}",
                    fg="#00C8FF",
                    bg="#141928"
                )
                label.config(relief=tk.SOLID, borderwidth=2, bd=2)
            else:
                # Normal option
                label.configure(
                    text=f"  {option['name']}\n  {option['desc']}",
                    fg="white",
                    bg="#141928"
                )
                label.config(relief=tk.FLAT, borderwidth=0)
    
    def launch_selected(self):
        selected_item = self.menu_options[self.selected_option]
        
        if selected_item["file"] is None:  # QUIT
            self.root.quit()
            return
        
        # Launch the game
        self.launch_game(selected_item["file"], selected_item["name"])
    
    def launch_game(self, filename, name):
        base_dir = os.path.dirname(os.path.abspath(__file__))
        game_path = os.path.join(base_dir, filename)
        
        if not os.path.exists(game_path):
            print(f"Error: {filename} not found!")
            return
        
        try:
            print(f"Launching {name}...")
            subprocess.Popen([sys.executable, game_path])
        except Exception as e:
            print(f"Error launching game: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    launcher = MineBoxLauncher(root)
    root.mainloop()
