# -*- coding: utf-8 -*-
"""
Quant_Structure/FTMO/Dashboards/Main_Board/main_board.py

Launcher-Version:
- Main Board als leichte Home-Zentrale
- Module werden erst beim Klick geöffnet
- Jedes Modul öffnet in eigenem Toplevel-Fenster
- Keine permanente Einbettung aller Dashboards im Hauptfenster
- Deutlich besser skalierbar bei vielen Pages

Start:
    python Quant_Structure/FTMO/Dashboards/Main_Board/main_board.py
"""

from __future__ import annotations

import importlib.util
import sys
import tkinter as tk
from dataclasses import dataclass
from pathlib import Path
from tkinter import messagebox
from typing import Callable, Dict, Optional, Tuple


# ============================================================
# PATHS
# ============================================================

def find_ftmo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "Data_Center").exists() and (p / "Dashboards").exists():
            return p
    raise RuntimeError(
        f"FTMO-Root nicht gefunden. Erwartet Root mit 'Data_Center' und 'Dashboards'. Start={start}"
    )


SCRIPT_PATH = Path(__file__).resolve()
FTMO_ROOT = find_ftmo_root(SCRIPT_PATH)

DASHBOARDS_ROOT = FTMO_ROOT / "Dashboards"
MAIN_BOARD_DIR = DASHBOARDS_ROOT / "Main_Board"
PAGES_DIR = MAIN_BOARD_DIR / "pages"
RUNTIME_DIR = MAIN_BOARD_DIR / "runtime"

STRATEGY_DASHBOARD_PATH = PAGES_DIR / "Strategy" / "strategy_dashboard.py"
LOOP_DASHBOARD_PATH = PAGES_DIR / "Loop_Management" / "loop_management_board.py"
MARKET_DASHBOARD_PATH = PAGES_DIR / "Market" / "market_watch_dashboard.py"
VISUAL_FOLDER_DASHBOARD_PATH = PAGES_DIR / "Visual_Folder" / "Visual_Folder.py"
CODE_STATION_DASHBOARD_PATH = PAGES_DIR / "Code_Station" / "Code_Station.py"


# ============================================================
# THEME
# ============================================================

BG_MAIN = "#0B0F14"
BG_SIDEBAR = "#0F141B"
BG_TOPBAR = "#0E141C"
BG_PANEL = "#111823"
BG_PANEL_2 = "#151E29"
BG_CARD = "#161F2B"
BG_CARD_SOFT = "#131B25"
BG_ACTIVE = "#1C2A3A"
BG_HOVER = "#182330"
BG_BUTTON = "#1A2430"

FG_MAIN = "#E8EDF3"
FG_MUTED = "#95A1AE"
FG_SUBTLE = "#7D8894"
FG_WHITE = "#FFFFFF"
FG_ACCENT = "#6EA8FE"
FG_POS = "#21C77A"
FG_NEG = "#FF5C6A"
FG_WARN = "#F5C451"

DIVIDER = "#1A2430"
BORDER_SOFT = "#1C2530"

FONT_TITLE = ("Segoe UI", 19, "bold")
FONT_TOP = ("Segoe UI", 10)
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_LABEL = ("Segoe UI", 9)
FONT_TEXT = ("Segoe UI", 10)
FONT_SMALL = ("Segoe UI", 8)
FONT_CARD_TITLE = ("Segoe UI", 10, "bold")
FONT_CARD_VALUE = ("Segoe UI", 18, "bold")
FONT_MONO = ("Consolas", 10)


# ============================================================
# HELPERS
# ============================================================

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def shorten_path(s: str, max_len: int = 100) -> str:
    if len(s) <= max_len:
        return s
    return "..." + s[-(max_len - 3):]


def load_module_from_path(module_name: str, file_path: Path):
    if not file_path.exists():
        raise FileNotFoundError(f"Datei nicht gefunden: {file_path}")

    spec = importlib.util.spec_from_file_location(module_name, str(file_path))
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Modul konnte nicht geladen werden: {file_path}")

    module = importlib.util.module_from_spec(spec)
    sys.modules[module_name] = module
    spec.loader.exec_module(module)
    return module


def make_divider(parent, pady=(0, 0)):
    tk.Frame(parent, bg=DIVIDER, height=1).pack(fill="x", pady=pady)


# ============================================================
# MODULE SPEC
# ============================================================

@dataclass
class ModuleSpec:
    key: str
    title: str
    subtitle: str
    description: str
    icon: str
    path: Optional[Path]
    panel_class_name: Optional[str]
    module_name_for_import: Optional[str]
    geometry: str = "1500x900"
    minsize: Tuple[int, int] = (1100, 700)
    placeholder: bool = False


# ============================================================
# BASE COMPONENTS
# ============================================================

class SoftPanel(tk.Frame):
    def __init__(self, parent, bg=BG_PANEL, padx=16, pady=16):
        super().__init__(parent, bg=bg, bd=0, highlightthickness=0)
        self.inner = tk.Frame(self, bg=bg)
        self.inner.pack(fill="both", expand=True, padx=padx, pady=pady)


class MetricRow(tk.Frame):
    def __init__(self, parent, key_text: str, value_text: str = "-", value_color: str = FG_MAIN):
        super().__init__(parent, bg=BG_PANEL)
        self.columnconfigure(0, weight=0)
        self.columnconfigure(1, weight=1)

        tk.Label(
            self,
            text=key_text,
            font=FONT_LABEL,
            bg=BG_PANEL,
            fg=FG_MUTED,
            anchor="w",
            width=24,
        ).grid(row=0, column=0, sticky="w")

        self.value_var = tk.StringVar(value=value_text)
        self.value_label = tk.Label(
            self,
            textvariable=self.value_var,
            font=FONT_TEXT,
            bg=BG_PANEL,
            fg=value_color,
            anchor="w",
        )
        self.value_label.grid(row=0, column=1, sticky="w")

    def set(self, value: str, color: Optional[str] = None):
        self.value_var.set(value)
        if color is not None:
            self.value_label.configure(fg=color)


class SectionHeader(tk.Frame):
    def __init__(self, parent, title: str, right_text: str = ""):
        super().__init__(parent, bg=BG_PANEL)
        tk.Label(
            self,
            text=title,
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).pack(side="left")

        if right_text:
            tk.Label(
                self,
                text=right_text,
                font=FONT_LABEL,
                bg=BG_PANEL,
                fg=FG_SUBTLE,
            ).pack(side="right")


class SidebarNavButton(tk.Frame):
    def __init__(self, parent, icon: str, text: str, command: Callable[[], None]):
        super().__init__(parent, bg=BG_SIDEBAR, bd=0, highlightthickness=0)
        self.command = command
        self.active = False

        self.btn = tk.Frame(self, bg=BG_SIDEBAR, cursor="hand2")
        self.btn.pack(fill="x", padx=10, pady=4)

        self.icon_label = tk.Label(
            self.btn,
            text=icon,
            font=("Segoe UI Symbol", 15),
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
            width=2,
            cursor="hand2",
        )
        self.icon_label.pack(side="left", padx=(10, 8), pady=10)

        self.text_label = tk.Label(
            self.btn,
            text=text,
            font=("Segoe UI", 9, "bold"),
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
            anchor="w",
            cursor="hand2",
        )
        self.text_label.pack(side="left", fill="x", expand=True, padx=(0, 10))

        for w in (self, self.btn, self.icon_label, self.text_label):
            w.bind("<Button-1>", lambda _e: self.command())
            w.bind("<Enter>", self._on_enter)
            w.bind("<Leave>", self._on_leave)

    def _apply_style(self):
        if self.active:
            bg = BG_ACTIVE
            fg = FG_WHITE
        else:
            bg = BG_SIDEBAR
            fg = FG_MUTED

        self.btn.configure(bg=bg)
        self.icon_label.configure(bg=bg, fg=fg)
        self.text_label.configure(bg=bg, fg=fg)

    def _on_enter(self, _event=None):
        if not self.active:
            self.btn.configure(bg=BG_HOVER)
            self.icon_label.configure(bg=BG_HOVER, fg=FG_MAIN)
            self.text_label.configure(bg=BG_HOVER, fg=FG_MAIN)

    def _on_leave(self, _event=None):
        if not self.active:
            self._apply_style()

    def set_active(self, active: bool):
        self.active = active
        self._apply_style()


class ModuleCard(tk.Frame):
    def __init__(
        self,
        parent,
        title: str,
        subtitle: str,
        description: str,
        icon: str,
        open_command: Callable[[], None],
        status_getter: Callable[[], Tuple[str, str]],
    ):
        super().__init__(parent, bg=BG_CARD, bd=0, highlightthickness=1, highlightbackground=BORDER_SOFT)
        self.open_command = open_command
        self.status_getter = status_getter

        self.columnconfigure(0, weight=1)

        top = tk.Frame(self, bg=BG_CARD)
        top.grid(row=0, column=0, sticky="ew", padx=14, pady=(14, 8))
        top.columnconfigure(1, weight=1)

        self.icon_label = tk.Label(
            top,
            text=icon,
            font=("Segoe UI Symbol", 18),
            bg=BG_CARD,
            fg=FG_ACCENT,
            width=2,
        )
        self.icon_label.grid(row=0, column=0, sticky="nw", padx=(0, 8))

        title_wrap = tk.Frame(top, bg=BG_CARD)
        title_wrap.grid(row=0, column=1, sticky="ew")

        tk.Label(
            title_wrap,
            text=title,
            font=FONT_CARD_TITLE,
            bg=BG_CARD,
            fg=FG_WHITE,
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            title_wrap,
            text=subtitle,
            font=FONT_SMALL,
            bg=BG_CARD,
            fg=FG_SUBTLE,
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        self.status_var = tk.StringVar(value="-")
        self.status_label = tk.Label(
            self,
            textvariable=self.status_var,
            font=FONT_CARD_VALUE,
            bg=BG_CARD,
            fg=FG_MUTED,
            anchor="w",
        )
        self.status_label.grid(row=1, column=0, sticky="w", padx=14)

        tk.Label(
            self,
            text=description,
            font=FONT_LABEL,
            bg=BG_CARD,
            fg=FG_MUTED,
            justify="left",
            wraplength=260,
            anchor="w",
        ).grid(row=2, column=0, sticky="ew", padx=14, pady=(8, 12))

        btn_row = tk.Frame(self, bg=BG_CARD)
        btn_row.grid(row=3, column=0, sticky="ew", padx=14, pady=(0, 14))

        tk.Button(
            btn_row,
            text="Open",
            command=self.open_command,
            bg=BG_ACTIVE,
            fg=FG_WHITE,
            activebackground=BG_HOVER,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=12,
            pady=7,
            bd=0,
        ).pack(side="left")

        tk.Button(
            btn_row,
            text="Focus",
            command=self.open_command,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_HOVER,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=12,
            pady=7,
            bd=0,
        ).pack(side="left", padx=(8, 0))

        for widget in (self, top, title_wrap, self.icon_label, self.status_label):
            widget.bind("<Double-1>", lambda _e: self.open_command())

    def refresh_status(self):
        text, color = self.status_getter()
        self.status_var.set(text)
        self.status_label.configure(fg=color)


# ============================================================
# MODULE WINDOW
# ============================================================

class ModuleWindow(tk.Toplevel):
    def __init__(self, app: "FTMOMainBoard", spec: ModuleSpec):
        super().__init__(app)
        self.app = app
        self.spec = spec
        self.loaded_ok = False
        self.load_error: Optional[str] = None
        self.panel = None

        self.title(spec.title)
        self.geometry(spec.geometry)
        self.minsize(*spec.minsize)
        self.configure(bg=BG_MAIN)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

        self._build_shell()
        self._build_content()

    def _build_shell(self):
        topbar = tk.Frame(self, bg=BG_TOPBAR, height=52, highlightbackground=DIVIDER, highlightthickness=1)
        topbar.pack(fill="x", padx=12, pady=(12, 10))
        topbar.pack_propagate(False)
        topbar.columnconfigure(1, weight=1)

        tk.Label(
            topbar,
            text=self.spec.title.upper(),
            font=FONT_TITLE,
            bg=BG_TOPBAR,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=14)

        self.info_var = tk.StringVar(value="")
        tk.Label(
            topbar,
            textvariable=self.info_var,
            font=FONT_TOP,
            bg=BG_TOPBAR,
            fg=FG_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=14)

        self.content = tk.Frame(self, bg=BG_MAIN)
        self.content.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        footer = tk.Frame(self, bg=BG_TOPBAR, height=30, highlightbackground=DIVIDER, highlightthickness=1)
        footer.pack(fill="x", padx=12, pady=(0, 12))
        footer.pack_propagate(False)

        self.status_var = tk.StringVar(value="READY")
        tk.Label(
            footer,
            textvariable=self.status_var,
            font=FONT_LABEL,
            bg=BG_TOPBAR,
            fg=FG_MUTED,
        ).pack(side="left", padx=10)

    def _build_placeholder(self, desc: str):
        body = SoftPanel(self.content, bg=BG_PANEL, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        SectionHeader(body.inner, self.spec.title).pack(fill="x")
        make_divider(body.inner, pady=(10, 14))

        tk.Label(
            body.inner,
            text=desc,
            justify="left",
            wraplength=1200,
            font=FONT_TEXT,
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).pack(anchor="w")

    def _build_error(self, err: str):
        body = SoftPanel(self.content, bg=BG_PANEL, padx=20, pady=20)
        body.pack(fill="both", expand=True)

        SectionHeader(body.inner, "Modul konnte nicht geladen werden").pack(fill="x")
        make_divider(body.inner, pady=(10, 14))

        txt = tk.Text(
            body.inner,
            wrap="word",
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=FONT_TEXT,
        )
        txt.pack(fill="both", expand=True)
        txt.insert(
            "1.0",
            "\n".join(
                [
                    f"Title      : {self.spec.title}",
                    f"Path       : {self.spec.path}",
                    f"PanelClass : {self.spec.panel_class_name}",
                    "",
                    "Fehler:",
                    err,
                ]
            ),
        )
        txt.configure(state="disabled")

    def _build_content(self):
        for child in self.content.winfo_children():
            child.destroy()

        if self.spec.placeholder:
            self.loaded_ok = True
            self.info_var.set("Placeholder")
            self.status_var.set("PLACEHOLDER")
            self._build_placeholder(self.spec.description)
            return

        try:
            assert self.spec.path is not None
            assert self.spec.panel_class_name is not None
            assert self.spec.module_name_for_import is not None

            module = load_module_from_path(self.spec.module_name_for_import, self.spec.path)

            if not hasattr(module, self.spec.panel_class_name):
                raise AttributeError(
                    f"Klasse '{self.spec.panel_class_name}' nicht gefunden in {self.spec.path.name}"
                )

            panel_cls = getattr(module, self.spec.panel_class_name)

            host = tk.Frame(self.content, bg=BG_MAIN)
            host.pack(fill="both", expand=True)

            if self.spec.panel_class_name == "StrategyDashboardPanel":
                repo_cls = getattr(module, "StrategyProfileRepository")
                root_path = getattr(module, "STRATEGY_PROFILE_ROOT")
                repo = repo_cls(root_path)
                self.panel = panel_cls(host, repo=repo)
            else:
                self.panel = panel_cls(host)

            self.panel.pack(fill="both", expand=True)
            self.loaded_ok = True
            self.info_var.set(shorten_path(str(self.spec.path), 120))
            self.status_var.set("READY")

        except Exception as e:
            self.loaded_ok = False
            self.load_error = str(e)
            self.info_var.set("LOAD ERROR")
            self.status_var.set("ERROR")
            self._build_error(str(e))

    def _on_close(self):
        try:
            if self.panel is not None and hasattr(self.panel, "destroy"):
                self.panel.destroy()
        except Exception:
            pass

        self.app.unregister_window(self.spec.key)
        self.destroy()


# ============================================================
# HOME PAGE
# ============================================================

class HomePage(tk.Frame):
    def __init__(self, parent, app: "FTMOMainBoard"):
        super().__init__(parent, bg=BG_MAIN)
        self.app = app
        self.cards: Dict[str, ModuleCard] = {}
        self.overview_rows: Dict[str, MetricRow] = {}

        self.columnconfigure(0, weight=3)
        self.columnconfigure(1, weight=2)
        self.rowconfigure(2, weight=1)

        self._build_ui()

    def _build_ui(self):
        top = tk.Frame(self, bg=BG_MAIN)
        top.grid(row=0, column=0, columnspan=2, sticky="ew", pady=(0, 18))

        tk.Label(
            top,
            text="FTMO MAIN BOARD",
            font=FONT_TITLE,
            bg=BG_MAIN,
            fg=FG_WHITE,
        ).pack(side="left")

        self.header_info_var = tk.StringVar(value="-")
        tk.Label(
            top,
            textvariable=self.header_info_var,
            font=FONT_TOP,
            bg=BG_MAIN,
            fg=FG_SUBTLE,
        ).pack(side="right")

        left = SoftPanel(self, bg=BG_PANEL, padx=18, pady=18)
        left.grid(row=1, column=0, rowspan=2, sticky="nsew", padx=(0, 10))

        SectionHeader(left.inner, "Module Launcher").pack(fill="x")
        make_divider(left.inner, pady=(10, 14))

        grid = tk.Frame(left.inner, bg=BG_PANEL)
        grid.pack(fill="both", expand=True)
        for c in range(2):
            grid.columnconfigure(c, weight=1)

        ordered_keys = [
            "strategy",
            "market",
            "loop_management",
            "visual_folder",
            "code_station",
            "performance",
            "spread",
        ]

        for idx, key in enumerate(ordered_keys):
            spec = self.app.module_specs[key]
            card = ModuleCard(
                grid,
                title=spec.title,
                subtitle=spec.subtitle,
                description=spec.description,
                icon=spec.icon,
                open_command=lambda k=key: self.app.open_module(k),
                status_getter=lambda k=key: self.app.get_module_status(k),
            )
            r, c = divmod(idx, 2)
            card.grid(row=r, column=c, sticky="nsew", padx=6, pady=6, ipadx=4, ipady=4)
            self.cards[key] = card

        right_top = SoftPanel(self, bg=BG_PANEL, padx=18, pady=18)
        right_top.grid(row=1, column=1, sticky="nsew", padx=(10, 0), pady=(0, 10))

        SectionHeader(right_top.inner, "System Overview").pack(fill="x")
        make_divider(right_top.inner, pady=(10, 14))

        overview_items = [
            ("FTMO Root", "-"),
            ("Strategy File", "-"),
            ("Loop File", "-"),
            ("Market File", "-"),
            ("Visual Folder File", "-"),
            ("Code Station File", "-"),
            ("Open Windows", "-"),
            ("Mode", "Launcher + Popup Windows"),
        ]
        for key_text, default_value in overview_items:
            row = MetricRow(right_top.inner, key_text, default_value)
            row.pack(fill="x", pady=4)
            self.overview_rows[key_text] = row

        right_bottom = SoftPanel(self, bg=BG_PANEL, padx=18, pady=18)
        right_bottom.grid(row=2, column=1, sticky="nsew", padx=(10, 0))

        SectionHeader(right_bottom.inner, "Current Structure").pack(fill="x")
        make_divider(right_bottom.inner, pady=(10, 14))

        self.structure_text = tk.Text(
            right_bottom.inner,
            wrap="none",
            bg=BG_PANEL,
            fg=FG_ACCENT,
            insertbackground=FG_ACCENT,
            relief="flat",
            bd=0,
            highlightthickness=0,
            font=FONT_MONO,
            height=24,
        )
        self.structure_text.pack(fill="both", expand=True)
        self.structure_text.configure(state="disabled")

    def refresh(self):
        self.header_info_var.set(shorten_path(str(FTMO_ROOT), 110))

        self.overview_rows["FTMO Root"].set(shorten_path(str(FTMO_ROOT), 70), FG_MAIN)
        self.overview_rows["Strategy File"].set(str(STRATEGY_DASHBOARD_PATH.exists()), FG_MAIN)
        self.overview_rows["Loop File"].set(str(LOOP_DASHBOARD_PATH.exists()), FG_MAIN)
        self.overview_rows["Market File"].set(str(MARKET_DASHBOARD_PATH.exists()), FG_MAIN)
        self.overview_rows["Visual Folder File"].set(str(VISUAL_FOLDER_DASHBOARD_PATH.exists()), FG_MAIN)
        self.overview_rows["Code Station File"].set(str(CODE_STATION_DASHBOARD_PATH.exists()), FG_MAIN)
        self.overview_rows["Open Windows"].set(str(len(self.app.module_windows)), FG_MAIN)

        for card in self.cards.values():
            card.refresh_status()

        structure_lines = [
            "Quant_Structure/FTMO/",
            "├── Analyse_Center",
            "├── Dashboards",
            "│   └── Main_Board",
            "│       ├── pages",
            "│       │   ├── Code_Station",
            "│       │   │   └── Code_Station.py",
            "│       │   ├── Loop_Management",
            "│       │   │   └── loop_management_board.py",
            "│       │   ├── Market",
            "│       │   │   └── market_watch_dashboard.py",
            "│       │   ├── Performance",
            "│       │   ├── Spread",
            "│       │   ├── Strategy",
            "│       │   │   └── strategy_dashboard.py",
            "│       │   └── Visual_Folder",
            "│       │       └── Visual_Folder.py",
            "│       ├── runtime",
            "│       ├── services",
            "│       └── main_board.py",
            "└── Data_Center",
        ]

        self.structure_text.configure(state="normal")
        self.structure_text.delete("1.0", "end")
        self.structure_text.insert("1.0", "\n".join(structure_lines))
        self.structure_text.configure(state="disabled")


# ============================================================
# MAIN APP
# ============================================================

class FTMOMainBoard(tk.Tk):
    REFRESH_MS = 5000

    def __init__(self):
        super().__init__()

        ensure_dir(RUNTIME_DIR)

        self.title("FTMO Main Board")
        self.geometry("1680x980")
        self.minsize(1380, 860)
        self.configure(bg=BG_MAIN)

        self.nav_buttons: Dict[str, SidebarNavButton] = {}
        self.module_windows: Dict[str, ModuleWindow] = {}

        self.module_specs: Dict[str, ModuleSpec] = self._build_module_specs()

        self._build_ui()
        self.home_page.refresh()
        self.after(self.REFRESH_MS, self._tick)

    def _build_module_specs(self) -> Dict[str, ModuleSpec]:
        return {
            "strategy": ModuleSpec(
                key="strategy",
                title="Strategy",
                subtitle="Research / Profile / Selection",
                description="Öffnet das Strategy Dashboard als separates Arbeitsfenster.",
                icon="◫",
                path=STRATEGY_DASHBOARD_PATH,
                panel_class_name="StrategyDashboardPanel",
                module_name_for_import="ftmo_strategy_dashboard_module",
                geometry="1860x1080",
                minsize=(1400, 900),
            ),
            "loop_management": ModuleSpec(
                key="loop_management",
                title="Loop Management",
                subtitle="Runtime / Monitoring",
                description="Öffnet das Loop Management Dashboard als separates Fenster.",
                icon="↻",
                path=LOOP_DASHBOARD_PATH,
                panel_class_name="LoopManagementPanel",
                module_name_for_import="ftmo_loop_management_module",
                geometry="1600x980",
                minsize=(1200, 800),
            ),
            "market": ModuleSpec(
                key="market",
                title="Market",
                subtitle="Market Watch / Session Moves",
                description="Öffnet das Market Dashboard als separates Monitor-Fenster.",
                icon="◌",
                path=MARKET_DASHBOARD_PATH,
                panel_class_name="MarketWatchPanel",
                module_name_for_import="ftmo_market_watch_module",
                geometry="1540x940",
                minsize=(1200, 760),
            ),
            "visual_folder": ModuleSpec(
                key="visual_folder",
                title="Visual Folder",
                subtitle="Structure / Export",
                description="Öffnet den Folder Explorer mit ASCII-Export und Copy-Funktion.",
                icon="☷",
                path=VISUAL_FOLDER_DASHBOARD_PATH,
                panel_class_name="FolderExplorerPanel",
                module_name_for_import="ftmo_visual_folder_module",
                geometry="1650x960",
                minsize=(1250, 760),
            ),
            "code_station": ModuleSpec(
                key="code_station",
                title="Code Station",
                subtitle="Editor / Run / Console",
                description="Öffnet die interne Code Station mit Explorer, Editor und Console.",
                icon="⌘",
                path=CODE_STATION_DASHBOARD_PATH,
                panel_class_name="CodeStationPanel",
                module_name_for_import="ftmo_code_station_module",
                geometry="1820x1050",
                minsize=(1350, 860),
            ),
            "performance": ModuleSpec(
                key="performance",
                title="Performance",
                subtitle="Placeholder",
                description="Reserviert für Performance-Metriken, Equity Curves und Attribution.",
                icon="◴",
                path=None,
                panel_class_name=None,
                module_name_for_import=None,
                geometry="1200x760",
                minsize=(900, 600),
                placeholder=True,
            ),
            "spread": ModuleSpec(
                key="spread",
                title="Spread",
                subtitle="Placeholder",
                description="Reserviert für Spread Monitoring, Kostenvergleich und Broker Analytics.",
                icon="⇄",
                path=None,
                panel_class_name=None,
                module_name_for_import=None,
                geometry="1200x760",
                minsize=(900, 600),
                placeholder=True,
            ),
        }

    def _build_topbar(self, parent):
        topbar = tk.Frame(parent, bg=BG_TOPBAR, height=54)
        topbar.pack(fill="x", side="top")
        topbar.pack_propagate(False)

        left = tk.Frame(topbar, bg=BG_TOPBAR)
        left.pack(side="left", fill="y", padx=18)

        tk.Label(
            left,
            text="FTMO / MAIN SOFTWARE",
            font=("Segoe UI", 11, "bold"),
            bg=BG_TOPBAR,
            fg=FG_WHITE,
        ).pack(side="left")

        right = tk.Frame(topbar, bg=BG_TOPBAR)
        right.pack(side="right", fill="y", padx=18)

        self.topbar_status_var = tk.StringVar(value="HOME READY")
        tk.Label(
            right,
            textvariable=self.topbar_status_var,
            font=FONT_TOP,
            bg=BG_TOPBAR,
            fg=FG_ACCENT,
        ).pack(side="right")

        tk.Frame(parent, bg=DIVIDER, height=1).pack(fill="x", side="top")

    def _build_ui(self):
        root = tk.Frame(self, bg=BG_MAIN)
        root.pack(fill="both", expand=True)

        sidebar = tk.Frame(root, bg=BG_SIDEBAR, width=230)
        sidebar.pack(side="left", fill="y")
        sidebar.pack_propagate(False)

        content_shell = tk.Frame(root, bg=BG_MAIN)
        content_shell.pack(side="left", fill="both", expand=True)

        self._build_topbar(content_shell)

        content = tk.Frame(content_shell, bg=BG_MAIN)
        content.pack(fill="both", expand=True)

        brand = tk.Frame(sidebar, bg=BG_SIDEBAR)
        brand.pack(fill="x", padx=16, pady=(18, 16))

        tk.Label(
            brand,
            text="FTMO",
            font=("Segoe UI", 18, "bold"),
            bg=BG_SIDEBAR,
            fg=FG_WHITE,
        ).pack(anchor="w")

        tk.Label(
            brand,
            text="Launcher / Control Hub",
            font=("Segoe UI", 9),
            bg=BG_SIDEBAR,
            fg=FG_SUBTLE,
        ).pack(anchor="w", pady=(2, 0))

        make_divider(sidebar, pady=(0, 12))

        nav = tk.Frame(sidebar, bg=BG_SIDEBAR)
        nav.pack(fill="x", padx=6)

        self.nav_buttons["home"] = SidebarNavButton(nav, icon="⌂", text="Home", command=self.focus_home)
        self.nav_buttons["home"].pack(fill="x")
        self.nav_buttons["home"].set_active(True)

        for key in ("strategy", "market", "loop_management", "visual_folder", "code_station"):
            spec = self.module_specs[key]
            btn = SidebarNavButton(nav, icon=spec.icon, text=spec.title, command=lambda k=key: self.open_module(k))
            btn.pack(fill="x")
            self.nav_buttons[key] = btn

        bottom_sidebar = tk.Frame(sidebar, bg=BG_SIDEBAR)
        bottom_sidebar.pack(side="bottom", fill="x", padx=16, pady=18)

        tk.Label(
            bottom_sidebar,
            text="ROOT",
            font=FONT_LABEL,
            bg=BG_SIDEBAR,
            fg=FG_SUBTLE,
        ).pack(anchor="w")

        self.sidebar_info_var = tk.StringVar(value=shorten_path(str(FTMO_ROOT), 42))
        tk.Label(
            bottom_sidebar,
            textvariable=self.sidebar_info_var,
            justify="left",
            wraplength=190,
            font=FONT_LABEL,
            bg=BG_SIDEBAR,
            fg=FG_MUTED,
        ).pack(anchor="w", pady=(4, 0))

        self.page_container = tk.Frame(content, bg=BG_MAIN)
        self.page_container.pack(fill="both", expand=True, padx=18, pady=18)

        self.home_page = HomePage(self.page_container, self)
        self.home_page.place(relx=0, rely=0, relwidth=1, relheight=1)

    def get_module_status(self, key: str) -> Tuple[str, str]:
        win = self.module_windows.get(key)
        if win is None or not win.winfo_exists():
            return ("CLOSED", FG_MUTED)
        if win.loaded_ok:
            return ("OPEN", FG_POS)
        return ("ERROR", FG_WARN)

    def unregister_window(self, key: str):
        if key in self.module_windows:
            self.module_windows.pop(key, None)
        self._refresh_status_text()
        self.home_page.refresh()

    def open_module(self, key: str):
        spec = self.module_specs[key]

        existing = self.module_windows.get(key)
        if existing is not None and existing.winfo_exists():
            try:
                existing.deiconify()
                existing.lift()
                existing.focus_force()
            except Exception:
                pass
            self._refresh_status_text()
            self.home_page.refresh()
            return

        try:
            win = ModuleWindow(self, spec)
            self.module_windows[key] = win
            self._refresh_status_text()
            self.home_page.refresh()
        except Exception as e:
            messagebox.showerror("Modulfehler", f"{spec.title} konnte nicht geöffnet werden.\n\n{e}")

    def focus_home(self):
        self.lift()
        self.focus_force()
        self.home_page.refresh()
        self._refresh_status_text()

    def _refresh_status_text(self):
        open_count = sum(1 for w in self.module_windows.values() if w.winfo_exists())
        self.topbar_status_var.set(f"HOME READY  |  OPEN WINDOWS: {open_count}")

    def _tick(self):
        try:
            dead_keys = []
            for key, win in self.module_windows.items():
                if not win.winfo_exists():
                    dead_keys.append(key)

            for key in dead_keys:
                self.module_windows.pop(key, None)

            self._refresh_status_text()
            self.home_page.refresh()
        finally:
            self.after(self.REFRESH_MS, self._tick)


# ============================================================
# MAIN
# ============================================================

def main() -> None:
    app = FTMOMainBoard()
    app.mainloop()


if __name__ == "__main__":
    main()