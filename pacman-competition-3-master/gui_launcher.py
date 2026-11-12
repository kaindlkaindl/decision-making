"""
Pacman Capture the Flag - Premium Modern GUI Launcher
ApexPredators AI (Decision Making - HvA / UvA)
Authors: Matin & Gabriel
"""

import os
import sys
import threading
import subprocess
import tkinter as tk
from tkinter import ttk, messagebox

# Enable High DPI awareness on Windows for crystal clear fonts
try:
    import ctypes
    ctypes.windll.shcore.SetProcessDpiAwareness(1)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

# Resolve base paths
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
CAPTURE_SCRIPT = os.path.join(SCRIPT_DIR, "capture.py")
LAYOUTS_DIR = os.path.join(SCRIPT_DIR, "layouts")

# Collect available layouts
available_layouts = ["defaultCapture", "RANDOM"]
if os.path.isdir(LAYOUTS_DIR):
    for f in sorted(os.listdir(LAYOUTS_DIR)):
        if f.endswith(".lay"):
            name = f[:-4]
            if name not in available_layouts:
                available_layouts.append(name)

# Available teams
available_teams = [
    "ApexPredators.py",
    "baselineTeam.py",
    "simpleTeam.py",
    "heuristicTeam.py",
    "myTeam.py"
]


class ModernPacmanLauncher:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pacman Capture the Flag · ApexPredators Arena")
        self.root.geometry("1060x860")
        self.root.minsize(980, 780)

        # Process management
        self.current_process = None
        self.reader_thread = None

        # Modern Premium Dark Palette (GitHub Dark / Neon Cyber theme)
        self.c_bg = "#0d1117"             # Main background
        self.c_surface = "#161b22"        # Card surface
        self.c_surface_elevated = "#21262d" # Active/Elevated card surface
        self.c_border = "#30363d"         # Border stroke
        self.c_border_focus = "#58a6ff"   # Focus/Selected glowing border
        self.c_text_main = "#f0f6fc"      # Crisp bright text
        self.c_text_muted = "#8b949e"     # Subtle text
        self.c_accent_green = "#2ea043"   # Vibrant Launch Green
        self.c_accent_green_hover = "#3fb950"
        self.c_accent_red = "#da3633"     # Stop / Red team
        self.c_accent_red_hover = "#f85149"
        self.c_accent_blue = "#58a6ff"    # Blue team / Highlights
        self.c_accent_purple = "#bc8cff"  # FSM / Specialty
        self.c_accent_yellow = "#d29922"  # Amber / Warning
        self.c_accent_cyan = "#39c5cf"    # Speed / Turbo
        self.c_input_bg = "#090d13"       # Deep input background

        self.root.configure(bg=self.c_bg)
        self._setup_tk_styles()

        # Variables
        self.red_team_var = tk.StringVar(value="ApexPredators.py")
        self.blue_team_var = tk.StringVar(value="baselineTeam.py")
        self.layout_var = tk.StringVar(value="defaultCapture")
        self.delay_var = tk.DoubleVar(value=0.005)  # Fast by default
        self.moves_var = tk.StringVar(value="1200")
        self.zoom_var = tk.StringVar(value="1.5")
        self.keys0_var = tk.BooleanVar(value=False)
        self.catch_exc_var = tk.BooleanVar(value=True)
        self.custom_flags_var = tk.StringVar(value="")
        self.cmd_preview_var = tk.StringVar(value="")
        self.status_text_var = tk.StringVar(value="Klaar voor de start")
        self.live_score_var = tk.StringVar(value="Score: 0")
        self.selected_preset_index = 0

        # Speed buttons state
        self.speed_buttons = []
        self.preset_cards = []

        self._build_ui()
        self._set_speed_preset(0.005)  # Default Super Snel
        self._select_preset_card(0)
        self._update_command_preview()

    def _setup_tk_styles(self):
        style = ttk.Style()
        style.theme_use("clam")

        # Combobox styling
        self.root.option_add("*TCombobox*Listbox.background", self.c_surface)
        self.root.option_add("*TCombobox*Listbox.foreground", self.c_text_main)
        self.root.option_add("*TCombobox*Listbox.selectBackground", "#1f6feb")
        self.root.option_add("*TCombobox*Listbox.selectForeground", "#ffffff")
        self.root.option_add("*TCombobox*Listbox.font", ("Segoe UI", 9))

        style.configure("Dark.TCombobox",
                        fieldbackground=self.c_input_bg,
                        background=self.c_surface_elevated,
                        foreground=self.c_text_main,
                        darkcolor=self.c_border,
                        lightcolor=self.c_border,
                        bordercolor=self.c_border,
                        arrowcolor=self.c_accent_blue)
        style.map("Dark.TCombobox",
                  fieldbackground=[("readonly", self.c_input_bg)],
                  foreground=[("readonly", self.c_text_main)],
                  bordercolor=[("focus", self.c_border_focus)])

    def _build_ui(self):
        # Header Banner
        header = tk.Frame(self.root, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        header.pack(fill=tk.X, padx=16, pady=(12, 10))

        h_inner = tk.Frame(header, bg=self.c_surface)
        h_inner.pack(fill=tk.X, padx=16, pady=10)

        # Left title info
        t_frame = tk.Frame(h_inner, bg=self.c_surface)
        t_frame.pack(side=tk.LEFT)

        title_lbl = tk.Label(t_frame, text="👾 PACMAN CAPTURE THE FLAG ARENA",
                             font=("Segoe UI", 15, "bold"), bg=self.c_surface, fg=self.c_text_main)
        title_lbl.pack(anchor="w")

        sub_lbl = tk.Label(t_frame, text="Decision Making (Autonome Systemen) | ApexPredators.py",
                           font=("Segoe UI", 8), bg=self.c_surface, fg=self.c_text_muted)
        sub_lbl.pack(anchor="w", pady=(2, 0))

        # Right stats / quick pill
        stat_frame = tk.Frame(h_inner, bg=self.c_surface)
        stat_frame.pack(side=tk.RIGHT)

        self.score_badge = tk.Label(stat_frame, textvariable=self.live_score_var, font=("Segoe UI", 10, "bold"),
                                    bg="#1f6feb", fg="#ffffff", padx=12, pady=4)
        self.score_badge.pack(side=tk.RIGHT, padx=(8, 0))

        self.status_pill = tk.Label(stat_frame, textvariable=self.status_text_var, font=("Segoe UI", 9, "bold"),
                                    bg=self.c_surface_elevated, fg=self.c_accent_green, padx=10, pady=4)
        self.status_pill.pack(side=tk.RIGHT)

        # Main Body Container
        main_body = tk.Frame(self.root, bg=self.c_bg)
        main_body.pack(fill=tk.BOTH, expand=True, padx=16, pady=(0, 10))

        # =========================================================================
        # SECTION 1: PRESET CARDS
        # =========================================================================
        p_card_container = tk.Frame(main_body, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        p_card_container.pack(fill=tk.X, pady=(0, 10))

        p_head = tk.Frame(p_card_container, bg=self.c_surface)
        p_head.pack(fill=tk.X, padx=14, pady=(10, 6))

        tk.Label(p_head, text="⚡ WEDSTRIJD PRESETS", font=("Segoe UI", 10, "bold"),
                 bg=self.c_surface, fg=self.c_accent_blue).pack(side=tk.LEFT)
        tk.Label(p_head, text="Klik op een kaart om de .py teams direct in te stellen",
                 font=("Segoe UI", 8), bg=self.c_surface, fg=self.c_text_muted).pack(side=tk.LEFT, padx=10)

        # 5 Cards Grid
        grid_frame = tk.Frame(p_card_container, bg=self.c_surface)
        grid_frame.pack(fill=tk.X, padx=12, pady=(0, 12))

        self.presets_data = [
            {
                "icon": "⚡",
                "title": "ApexPredators.py vs baselineTeam.py",
                "red": "ApexPredators.py",
                "blue": "baselineTeam.py",
                "keys": False,
                "badge": "baselineTeam.py",
                "color": self.c_accent_green,
                "desc": "ApexPredators.py vs baselineTeam.py"
            },
            {
                "icon": "🧠",
                "title": "ApexPredators.py vs simpleTeam.py",
                "red": "ApexPredators.py",
                "blue": "simpleTeam.py",
                "keys": False,
                "badge": "simpleTeam.py",
                "color": self.c_accent_purple,
                "desc": "ApexPredators.py vs simpleTeam.py"
            },
            {
                "icon": "🎯",
                "title": "ApexPredators.py vs heuristicTeam.py",
                "red": "ApexPredators.py",
                "blue": "heuristicTeam.py",
                "keys": False,
                "badge": "heuristicTeam.py",
                "color": self.c_accent_yellow,
                "desc": "ApexPredators.py vs heuristicTeam.py"
            },
            {
                "icon": "⚔️",
                "title": "ApexPredators.py vs ApexPredators.py",
                "red": "ApexPredators.py",
                "blue": "ApexPredators.py",
                "keys": False,
                "badge": "ApexPredators.py",
                "color": self.c_accent_cyan,
                "desc": "ApexPredators.py vs ApexPredators.py"
            },
            {
                "icon": "🕹️",
                "title": "keyboardAgents.py vs ApexPredators.py",
                "red": "ApexPredators.py",
                "blue": "ApexPredators.py",
                "keys": True,
                "badge": "keyboardAgents.py",
                "color": self.c_accent_red,
                "desc": "keyboardAgents.py (--keys0)"
            }
        ]

        for idx, p in enumerate(self.presets_data):
            c_box = tk.Frame(grid_frame, bg=self.c_surface_elevated, highlightbackground=self.c_border,
                             highlightthickness=1, cursor="hand2", padx=8, pady=8)
            c_box.grid(row=0, column=idx, padx=4, pady=2, sticky="nsew")
            grid_frame.columnconfigure(idx, weight=1)

            # Icon + Title
            t_box = tk.Frame(c_box, bg=self.c_surface_elevated)
            t_box.pack(fill=tk.X, anchor="w")
            t_lbl = tk.Label(t_box, text=f"{p['icon']} {p['title']}", font=("Segoe UI", 8, "bold"),
                             bg=self.c_surface_elevated, fg=p["color"], wraplength=170, justify="left")
            t_lbl.pack(anchor="w")

            # Badge pill
            b_lbl = tk.Label(c_box, text=p["badge"], font=("Segoe UI", 7, "bold"),
                             bg=self.c_bg, fg=self.c_text_main, padx=6, pady=1)
            b_lbl.pack(anchor="w", pady=(4, 3))

            # Description
            d_lbl = tk.Label(c_box, text=p["desc"], font=("Segoe UI", 7),
                             bg=self.c_surface_elevated, fg=self.c_text_muted, wraplength=165, justify="left")
            d_lbl.pack(anchor="w", pady=(0, 2))

            # Store card for selection & hover
            self.preset_cards.append({
                "frame": c_box,
                "title_box": t_box,
                "title_lbl": t_lbl,
                "badge": b_lbl,
                "desc": d_lbl,
                "index": idx
            })

            # Bind click and double-click events
            for widget in (c_box, t_box, t_lbl, b_lbl, d_lbl):
                widget.bind("<Button-1>", lambda e, i=idx: self._select_preset_card(i))
                widget.bind("<Double-Button-1>", lambda e, i=idx: self._on_card_double_click(i))
                widget.bind("<Enter>", lambda e, i=idx: self._on_card_hover(i, True))
                widget.bind("<Leave>", lambda e, i=idx: self._on_card_hover(i, False))

        # =========================================================================
        # SECTION 2: TEAMS & MAP MATCHUP ARENA
        # =========================================================================
        arena_card = tk.Frame(main_body, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        arena_card.pack(fill=tk.X, pady=(0, 10))

        a_inner = tk.Frame(arena_card, bg=self.c_surface, padx=14, pady=10)
        a_inner.pack(fill=tk.X)

        # Red Team Box
        red_box = tk.Frame(a_inner, bg=self.c_surface)
        red_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(red_box, text="🔴 ROOD TEAM (-r)", font=("Segoe UI", 9, "bold"),
                 bg=self.c_surface, fg=self.c_accent_red).pack(anchor="w")
        self.red_combo = ttk.Combobox(red_box, values=available_teams, textvariable=self.red_team_var,
                                      style="Dark.TCombobox", state="readonly", width=18)
        self.red_combo.pack(anchor="w", pady=(4, 0))
        self.red_combo.bind("<<ComboboxSelected>>", lambda e: self._on_team_change())

        # VS Badge Center
        vs_box = tk.Frame(a_inner, bg=self.c_surface)
        vs_box.pack(side=tk.LEFT, padx=25)

        tk.Label(vs_box, text="⚔️", font=("Segoe UI", 16), bg=self.c_surface).pack()
        tk.Label(vs_box, text="VERSUS", font=("Segoe UI", 8, "bold"), bg=self.c_surface, fg=self.c_text_muted).pack()
        swap_btn = tk.Button(vs_box, text="🔄 Wissel", font=("Segoe UI", 7, "bold"),
                             bg=self.c_surface_elevated, fg=self.c_accent_cyan, activebackground=self.c_border,
                             activeforeground="#ffffff", relief="flat", bd=0, padx=6, pady=1, cursor="hand2",
                             command=self._swap_teams)
        swap_btn.pack(pady=(3, 0))

        # Blue Team Box
        blue_box = tk.Frame(a_inner, bg=self.c_surface)
        blue_box.pack(side=tk.LEFT, fill=tk.X, expand=True)

        tk.Label(blue_box, text="🔵 BLAUW TEAM (-b)", font=("Segoe UI", 9, "bold"),
                 bg=self.c_surface, fg=self.c_accent_blue).pack(anchor="w")
        self.blue_combo = ttk.Combobox(blue_box, values=available_teams, textvariable=self.blue_team_var,
                                       style="Dark.TCombobox", state="readonly", width=18)
        self.blue_combo.pack(anchor="w", pady=(4, 0))
        self.blue_combo.bind("<<ComboboxSelected>>", lambda e: self._on_team_change())

        # Map Selector Box
        map_box = tk.Frame(a_inner, bg=self.c_surface)
        map_box.pack(side=tk.RIGHT, padx=(20, 0))

        tk.Label(map_box, text="🗺️ DOOLHOF MAP (-l)", font=("Segoe UI", 9, "bold"),
                 bg=self.c_surface, fg=self.c_accent_yellow).pack(anchor="w")
        self.map_combo = ttk.Combobox(map_box, values=available_layouts, textvariable=self.layout_var,
                                      style="Dark.TCombobox", state="readonly", width=20)
        self.map_combo.pack(anchor="w", pady=(4, 0))
        self.map_combo.bind("<<ComboboxSelected>>", lambda e: self._update_command_preview())

        # =========================================================================
        # SECTION 3: DYNAMISCHE VLAGGEN & SNELHEID
        # =========================================================================
        flags_card = tk.Frame(main_body, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        flags_card.pack(fill=tk.X, pady=(0, 10))

        fl_inner = tk.Frame(flags_card, bg=self.c_surface, padx=14, pady=10)
        fl_inner.pack(fill=tk.X)

        # Speed Row
        speed_row = tk.Frame(fl_inner, bg=self.c_surface)
        speed_row.pack(fill=tk.X, pady=(0, 6))

        tk.Label(speed_row, text="⏩ SPEELTEMPO (--delay-step):", font=("Segoe UI", 9, "bold"),
                 bg=self.c_surface, fg=self.c_text_main, width=24, anchor="w").pack(side=tk.LEFT)

        speed_options = [
            ("🔥 Max Turbo (0s)", 0.0),
            ("⚡ Super Snel (0.005s)", 0.005),
            ("🚀 Vlot (0.015s)", 0.015),
            ("⏱️ Normaal (0.03s)", 0.03),
            ("🐢 Rustig (0.06s)", 0.06)
        ]

        for s_text, s_val in speed_options:
            s_btn = tk.Button(speed_row, text=s_text, font=("Segoe UI", 8, "bold"),
                              bg=self.c_surface_elevated, fg=self.c_text_main, activebackground=self.c_border,
                              activeforeground=self.c_accent_cyan, relief="flat", bd=0, padx=8, pady=3, cursor="hand2",
                              command=lambda v=s_val: self._set_speed_preset(v))
            s_btn.pack(side=tk.LEFT, padx=3)
            self.speed_buttons.append((s_btn, s_val))

        self.speed_lbl = tk.Label(speed_row, text="", font=("Segoe UI", 9, "bold"),
                                  bg=self.c_surface, fg=self.c_accent_cyan)
        self.speed_lbl.pack(side=tk.RIGHT)

        # Precise Slider Row
        slider_row = tk.Frame(fl_inner, bg=self.c_surface)
        slider_row.pack(fill=tk.X, pady=(0, 8))

        tk.Label(slider_row, text="   Nauwkeurige Slider:", font=("Segoe UI", 8),
                 bg=self.c_surface, fg=self.c_text_muted, width=24, anchor="w").pack(side=tk.LEFT)

        self.slider = tk.Scale(slider_row, from_=0.0, to=0.08, resolution=0.001, orient=tk.HORIZONTAL,
                               variable=self.delay_var, showvalue=False, bg=self.c_surface, fg=self.c_text_main,
                               troughcolor=self.c_input_bg, activebackground=self.c_accent_cyan,
                               highlightthickness=0, bd=0, command=self._on_slider_move)
        self.slider.pack(side=tk.LEFT, fill=tk.X, expand=True, padx=(0, 10))

        # Flags Grid Row (Moves, Zoom, Keys, Catch)
        opt_row = tk.Frame(fl_inner, bg=self.c_surface)
        opt_row.pack(fill=tk.X, pady=(2, 6))

        # Move Limit
        tk.Label(opt_row, text="⏱️ Stappen (-i):", font=("Segoe UI", 8, "bold"),
                 bg=self.c_surface, fg=self.c_text_main).pack(side=tk.LEFT, padx=(0, 4))
        moves_combo = ttk.Combobox(opt_row, values=["1200", "800", "600", "300", "150"], textvariable=self.moves_var,
                                   style="Dark.TCombobox", width=7)
        moves_combo.pack(side=tk.LEFT, padx=(0, 15))
        moves_combo.bind("<<ComboboxSelected>>", lambda e: self._update_command_preview())
        moves_combo.bind("<KeyRelease>", lambda e: self._update_command_preview())

        # Zoom
        tk.Label(opt_row, text="🔍 Zoom (-z):", font=("Segoe UI", 8, "bold"),
                 bg=self.c_surface, fg=self.c_text_main).pack(side=tk.LEFT, padx=(0, 4))
        zoom_combo = ttk.Combobox(opt_row, values=["1.5", "1.7", "2.0", "1.2", "1.0"], textvariable=self.zoom_var,
                                  style="Dark.TCombobox", state="readonly", width=6)
        zoom_combo.pack(side=tk.LEFT, padx=(0, 20))
        zoom_combo.bind("<<ComboboxSelected>>", lambda e: self._update_command_preview())

        # Checkbuttons
        k_chk = tk.Checkbutton(opt_row, text="Zelf spelen met pijltjestoetsen (--keys0)", variable=self.keys0_var,
                               font=("Segoe UI", 8, "bold"), bg=self.c_surface, fg=self.c_accent_red,
                               selectcolor=self.c_input_bg, activebackground=self.c_surface,
                               activeforeground=self.c_accent_red, command=self._on_keys_toggle)
        k_chk.pack(side=tk.LEFT, padx=(0, 15))

        c_chk = tk.Checkbutton(opt_row, text="Catch Exceptions (-c)", variable=self.catch_exc_var,
                               font=("Segoe UI", 8), bg=self.c_surface, fg=self.c_text_main,
                               selectcolor=self.c_input_bg, activebackground=self.c_surface,
                               activeforeground=self.c_accent_green, command=self._update_command_preview)
        c_chk.pack(side=tk.LEFT)

        # Free Custom Flags
        custom_row = tk.Frame(fl_inner, bg=self.c_surface)
        custom_row.pack(fill=tk.X, pady=(4, 0))

        tk.Label(custom_row, text="✏️ Vrije Vlaggen (Custom):", font=("Segoe UI", 8),
                 bg=self.c_surface, fg=self.c_text_muted, width=24, anchor="w").pack(side=tk.LEFT)
        custom_entry = tk.Entry(custom_row, textvariable=self.custom_flags_var, font=("Consolas", 9),
                                bg=self.c_input_bg, fg=self.c_text_main, insertbackground=self.c_text_main,
                                relief="flat", highlightbackground=self.c_border, highlightthickness=1)
        custom_entry.pack(side=tk.LEFT, fill=tk.X, expand=True)
        custom_entry.bind("<KeyRelease>", lambda e: self._update_command_preview())

        # =========================================================================
        # SECTION 4: COMMAND PREVIEW & ACTION BAR
        # =========================================================================
        action_card = tk.Frame(main_body, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        action_card.pack(fill=tk.X, pady=(0, 10))

        # Command Preview Chip
        cmd_box = tk.Frame(action_card, bg=self.c_input_bg, padx=12, pady=7)
        cmd_box.pack(fill=tk.X, padx=14, pady=(10, 8))

        tk.Label(cmd_box, text="COMMAND ▶", font=("Consolas", 8, "bold"),
                 bg=self.c_input_bg, fg=self.c_accent_blue).pack(side=tk.LEFT, padx=(0, 10))
        cmd_lbl = tk.Label(cmd_box, textvariable=self.cmd_preview_var, font=("Consolas", 9, "bold"),
                           bg=self.c_input_bg, fg=self.c_accent_green, anchor="w")
        cmd_lbl.pack(side=tk.LEFT, fill=tk.X, expand=True)

        copy_btn = tk.Button(cmd_box, text="📋 Kopieer", font=("Segoe UI", 8, "bold"),
                             bg=self.c_surface_elevated, fg=self.c_text_main, activebackground=self.c_border,
                             activeforeground=self.c_accent_blue, relief="flat", bd=0, padx=10, pady=2,
                             cursor="hand2", command=self._copy_command)
        copy_btn.pack(side=tk.RIGHT)

        # Big Action Buttons
        btn_bar = tk.Frame(action_card, bg=self.c_surface, padx=14)
        btn_bar.pack(fill=tk.X, pady=(0, 12))

        self.start_btn = tk.Button(btn_bar, text="▶  START WEDSTRIJD MET GUI", font=("Segoe UI", 11, "bold"),
                                   bg=self.c_accent_green, fg="#ffffff", activebackground=self.c_accent_green_hover,
                                   activeforeground="#ffffff", relief="flat", bd=0, padx=26, pady=8, cursor="hand2",
                                   command=self.start_game)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 12))

        self.stop_btn = tk.Button(btn_bar, text="⏹  STOP SPEL", font=("Segoe UI", 10, "bold"),
                                  bg=self.c_accent_red, fg="#ffffff", activebackground=self.c_accent_red_hover,
                                  activeforeground="#ffffff", relief="flat", bd=0, padx=18, pady=8, state=tk.DISABLED,
                                  cursor="hand2", command=self.stop_game)
        self.stop_btn.pack(side=tk.LEFT, padx=(0, 16))

        # Status text in action bar
        self.action_status_lbl = tk.Label(btn_bar, textvariable=self.status_text_var, font=("Segoe UI", 9, "italic"),
                                          bg=self.c_surface, fg=self.c_accent_yellow)
        self.action_status_lbl.pack(side=tk.LEFT)

        # =========================================================================
        # SECTION 5: LIVE CONSOLE OUTPUT & EVENT MONITOR
        # =========================================================================
        console_card = tk.Frame(main_body, bg=self.c_surface, highlightbackground=self.c_border, highlightthickness=1)
        console_card.pack(fill=tk.BOTH, expand=True)

        c_head = tk.Frame(console_card, bg=self.c_surface, padx=14)
        c_head.pack(fill=tk.X, pady=(8, 4))

        tk.Label(c_head, text="📊 LIVE WEDSTRIJD CONSOLE & STATS MONITOR", font=("Segoe UI", 8, "bold"),
                 bg=self.c_surface, fg=self.c_text_muted).pack(side=tk.LEFT)

        clear_btn = tk.Button(c_head, text="Console Wissen", font=("Segoe UI", 7),
                              bg=self.c_surface_elevated, fg=self.c_text_muted, activebackground=self.c_border,
                              activeforeground=self.c_text_main, relief="flat", bd=0, padx=6, pady=1,
                              cursor="hand2", command=self._clear_console)
        clear_btn.pack(side=tk.RIGHT)

        # Text Console Box
        c_box = tk.Frame(console_card, bg=self.c_input_bg)
        c_box.pack(fill=tk.BOTH, expand=True, padx=12, pady=(0, 10))

        scrollbar = tk.Scrollbar(c_box, bg=self.c_surface)
        scrollbar.pack(side=tk.RIGHT, fill=tk.Y)

        self.console_text = tk.Text(c_box, bg=self.c_input_bg, fg="#c9d1d9", insertbackground="#ffffff",
                                    font=("Consolas", 9), relief="flat", yscrollcommand=scrollbar.set, height=8)
        self.console_text.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        scrollbar.config(command=self.console_text.yview)

        # Syntax color tags
        self.console_text.tag_config("score", foreground="#7ee787", font=("Consolas", 9, "bold"))
        self.console_text.tag_config("win", foreground="#ffd700", font=("Consolas", 10, "bold"))
        self.console_text.tag_config("error", foreground="#ff7b72", font=("Consolas", 9, "bold"))
        self.console_text.tag_config("info", foreground="#79c0ff")

    # =========================================================================
    # EVENT HANDLERS & CARD LOGIC
    # =========================================================================
    def _on_card_double_click(self, idx: int):
        self._select_preset_card(idx)
        self.start_game()

    def _swap_teams(self):
        r = self.red_team_var.get()
        b = self.blue_team_var.get()
        self.red_team_var.set(b)
        self.blue_team_var.set(r)
        self._update_command_preview()
        self.status_text_var.set(f"Teams gewisseld: {b} (Rood) vs {r} (Blauw)")

    def _select_preset_card(self, idx: int):
        self.selected_preset_index = idx
        p = self.presets_data[idx]

        self.red_team_var.set(p["red"])
        self.blue_team_var.set(p["blue"])
        self.keys0_var.set(p["keys"])

        # Update card visuals
        for i, c in enumerate(self.preset_cards):
            is_active = (i == idx)
            bg_col = self.c_surface_elevated if not is_active else "#1c2333"
            border_col = self.presets_data[i]["color"] if is_active else self.c_border
            thickness = 2 if is_active else 1

            c["frame"].config(bg=bg_col, highlightbackground=border_col, highlightthickness=thickness)
            c["title_box"].config(bg=bg_col)
            c["title_lbl"].config(bg=bg_col)
            c["desc"].config(bg=bg_col)

        self._update_command_preview()
        self.status_text_var.set(f"Preset geselecteerd: {p['title']}")

    def _on_card_hover(self, idx: int, entering: bool):
        if idx == self.selected_preset_index:
            return
        c = self.preset_cards[idx]
        bg_col = "#252b36" if entering else self.c_surface_elevated
        c["frame"].config(bg=bg_col)
        c["title_box"].config(bg=bg_col)
        c["title_lbl"].config(bg=bg_col)
        c["desc"].config(bg=bg_col)

    def _set_speed_preset(self, val: float):
        self.delay_var.set(val)
        self._update_speed_label(val)
        self._update_speed_buttons(val)
        self._update_command_preview()

    def _on_slider_move(self, event=None):
        val = round(self.delay_var.get(), 4)
        self._update_speed_label(val)
        self._update_speed_buttons(val)
        self._update_command_preview()

    def _update_speed_label(self, val: float):
        if val <= 0.001:
            desc = "Max Turbo (0s vertraging)"
        elif val <= 0.008:
            desc = f"{val:.3f}s (Super Snel)"
        elif val <= 0.02:
            desc = f"{val:.3f}s (Vlot)"
        elif val <= 0.04:
            desc = f"{val:.3f}s (Normaal)"
        else:
            desc = f"{val:.3f}s (Rustig volgen)"
        self.speed_lbl.config(text=desc)

    def _update_speed_buttons(self, current_val: float):
        for btn, s_val in self.speed_buttons:
            if abs(current_val - s_val) < 0.002:
                btn.config(bg="#1f6feb", fg="#ffffff")
            else:
                btn.config(bg=self.c_surface_elevated, fg=self.c_text_main)

    def _on_team_change(self):
        self._update_command_preview()

    def _on_keys_toggle(self):
        if self.keys0_var.get():
            self.status_text_var.set("Pijltjestoetsen actief: Jij bent Agent 0")
        self._update_command_preview()

    def _build_command_list(self) -> list:
        cmd = [sys.executable, "capture.py"]

        if self.keys0_var.get():
            cmd.append("--keys0")
        else:
            cmd.extend(["-r", self.red_team_var.get()])

        cmd.extend(["-b", self.blue_team_var.get()])

        # Layout
        layout = self.layout_var.get()
        if layout and layout != "defaultCapture":
            cmd.extend(["-l", layout])

        # Delay step
        delay = round(self.delay_var.get(), 4)
        cmd.extend(["--delay-step", str(delay)])

        # Moves
        moves = self.moves_var.get().strip()
        if moves and moves != "1200":
            cmd.extend(["-i", moves])

        # Zoom
        zoom = self.zoom_var.get().strip()
        if zoom and zoom != "1.0":
            cmd.extend(["-z", zoom])

        # Catch exceptions
        if self.catch_exc_var.get():
            cmd.append("-c")

        # Custom flags
        custom = self.custom_flags_var.get().strip()
        if custom:
            cmd.extend(custom.split())

        return cmd

    def _update_command_preview(self):
        cmd = self._build_command_list()
        display_cmd = "python " + " ".join(cmd[1:])
        self.cmd_preview_var.set(display_cmd)

    def _copy_command(self):
        self.root.clipboard_clear()
        self.root.clipboard_append(self.cmd_preview_var.get())
        self.status_text_var.set("✅ Commando gekopieerd naar klembord!")

    def _clear_console(self):
        self.console_text.delete("1.0", tk.END)
        self.live_score_var.set("Score: 0")

    def _log(self, text: str, tag: str = None):
        self.console_text.insert(tk.END, text + "\n", tag)
        self.console_text.see(tk.END)

    # =========================================================================
    # GAME EXECUTION ENGINE
    # =========================================================================
    def start_game(self):
        if self.current_process is not None and self.current_process.poll() is None:
            messagebox.showinfo("Al actief", "Er draait al een wedstrijd! Stop deze eerst.")
            return

        cmd = self._build_command_list()
        self._log("\n" + "═" * 55, "info")
        self._log(f"▶ STARTEN: {' '.join(cmd[1:])}", "info")
        self._log("═" * 55, "info")

        self.start_btn.config(state=tk.DISABLED, bg="#30363d")
        self.stop_btn.config(state=tk.NORMAL)
        self.status_pill.config(text="● LIVE ACTIEF", fg=self.c_accent_green)
        self.status_text_var.set("🎮 Wedstrijd is actief...")

        def run_proc():
            try:
                self.current_process = subprocess.Popen(
                    cmd,
                    cwd=SCRIPT_DIR,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1
                )

                for line in self.current_process.stdout:
                    clean_line = line.rstrip()
                    if clean_line:
                        tag = None
                        if "Score:" in clean_line:
                            tag = "score"
                            try:
                                score_val = clean_line.split("Score:")[-1].strip()
                                self.root.after(0, self.live_score_var.set, f"Score: {score_val}")
                            except Exception:
                                pass
                        elif "wins by" in clean_line or "Tie game" in clean_line:
                            tag = "win"
                            self.root.after(0, self.status_text_var.set, clean_line)
                        elif "Exception" in clean_line or "Error" in clean_line:
                            tag = "error"
                        self.root.after(0, self._log, clean_line, tag)

                self.current_process.wait()
                rc = self.current_process.returncode
                self.root.after(0, self._on_game_finished, rc)
            except Exception as e:
                self.root.after(0, self._log, f"Fout bij starten: {e}", "error")
                self.root.after(0, self._on_game_finished, -1)

        self.reader_thread = threading.Thread(target=run_proc, daemon=True)
        self.reader_thread.start()

    def _on_game_finished(self, returncode: int):
        self.current_process = None
        self.start_btn.config(state=tk.NORMAL, bg=self.c_accent_green)
        self.stop_btn.config(state=tk.DISABLED)
        self.status_pill.config(text="○ STANDBY", fg=self.c_text_muted)

        if returncode == 0:
            self._log("🏁 Wedstrijd beëindigd.", "win")
        else:
            self.status_text_var.set(f"Beëindigd (code {returncode})")
            self._log(f"⚠️ Spel beëindigd (code {returncode})", "error")

    def stop_game(self):
        if self.current_process is not None and self.current_process.poll() is None:
            self.current_process.terminate()
            self.status_text_var.set("⏹ Wedstrijd handmatig gestopt.")
            self._log("⏹ Wedstrijd handmatig gestopt.", "error")


def main():
    root = tk.Tk()
    app = ModernPacmanLauncher(root)

    def on_closing():
        if app.current_process and app.current_process.poll() is None:
            app.current_process.terminate()
        root.destroy()

    root.protocol("WM_DELETE_WINDOW", on_closing)
    root.mainloop()


if __name__ == "__main__":
    main()
