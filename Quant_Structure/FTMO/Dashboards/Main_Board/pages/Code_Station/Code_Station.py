# -*- coding: utf-8 -*-
"""
Quant_Structure/FTMO/Dashboards/Main_Board/pages/Code_Station/Code_Station.py

Zweck:
- Interne Code Station für das FTMO Main Board
- Links: File Explorer
- Mitte: Code Editor
- Rechts: Datei-Informationen + vorhandene Code-Dateien im Workspace
- Unten: Console / Run Output
- Save / Reload / New File / New Folder / Delete / Copy Path
- Python-Dateien direkt ausführbar
- Zusätzlicher Code-Index mit Suche und Doppelklick zum Öffnen

Einbettung im Main Board:
    panel_class_name="CodeStationPanel"

Standalone:
    python Quant_Structure/FTMO/Dashboards/Main_Board/pages/Code_Station/Code_Station.py
"""

from __future__ import annotations

from pathlib import Path
from typing import Optional, List
import shutil
import subprocess
import sys
import threading
import tkinter as tk
from tkinter import ttk, messagebox, simpledialog


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
DEFAULT_WORKSPACE_ROOT = FTMO_ROOT


# ============================================================
# STYLE
# ============================================================

BG_MAIN = "#0A0C10"
BG_PANEL = "#11151B"
BG_PANEL_2 = "#151A21"
BG_HEADER = "#171C24"
BG_TOPBAR = "#0E1319"
BG_BUTTON = "#1A2029"
BG_ACTIVE = "#1E232B"

FG_MAIN = "#E6EAF0"
FG_MUTED = "#9BA6B2"
FG_WHITE = "#FFFFFF"
FG_ACCENT = "#6EA8FE"
FG_WARN = "#F5C451"
FG_OK = "#22C55E"
FG_NEG = "#EF4444"

BORDER = "#232A34"

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_TOP = ("Segoe UI", 10, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_LABEL = ("Segoe UI", 9)
FONT_TEXT = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)


# ============================================================
# HELPERS
# ============================================================

TEXT_FILE_EXTENSIONS = {
    ".py", ".txt", ".md", ".json", ".yaml", ".yml", ".csv", ".ini", ".cfg",
    ".toml", ".sql", ".js", ".ts", ".html", ".css", ".xml", ".log", ".env",
    ".mq5", ".mqh", ".bat", ".ps1", ".r", ".cpp", ".c", ".h", ".java"
}

CODE_INDEX_EXTENSIONS = {
    ".py", ".mq5", ".mqh", ".json", ".yaml", ".yml", ".sql", ".js", ".ts",
    ".html", ".css", ".xml", ".ini", ".cfg", ".toml", ".txt", ".md", ".csv"
}


def is_text_file(path: Path) -> bool:
    return path.suffix.lower() in TEXT_FILE_EXTENSIONS or path.name.lower() in {
        "dockerfile", ".gitignore", ".env"
    }


def is_code_index_file(path: Path) -> bool:
    return path.is_file() and (path.suffix.lower() in CODE_INDEX_EXTENSIONS or path.name.lower() in {
        "dockerfile", ".gitignore", ".env"
    })


def safe_rel(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
        s = rel.as_posix()
        return s if s else "."
    except Exception:
        return "."


def make_iid(rel_path: str) -> str:
    return rel_path if rel_path else "."


def within_root(path: Path, root: Path) -> bool:
    try:
        path.resolve().relative_to(root.resolve())
        return True
    except Exception:
        return False


def list_dir(path: Path, ignore_hidden: bool = True):
    entries = list(path.iterdir())
    if ignore_hidden:
        entries = [e for e in entries if not e.name.startswith(".")]
    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    return entries


# ============================================================
# PANEL
# ============================================================

class CodeStationPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)

        self.workspace_root = DEFAULT_WORKSPACE_ROOT.resolve()
        self.current_file: Optional[Path] = None
        self.editor_dirty = False
        self.ignore_hidden = tk.BooleanVar(value=True)

        self.process: Optional[subprocess.Popen] = None
        self.process_thread: Optional[threading.Thread] = None

        self.code_index_files: List[Path] = []

        self._build_ui()
        self._load_tree()
        self._rebuild_code_index()
        self._update_status("READY")

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):
        self.rowconfigure(2, weight=1)
        self.columnconfigure(0, weight=1)

        topbar = tk.Frame(self, bg=BG_TOPBAR, height=52, highlightbackground=BORDER, highlightthickness=1)
        topbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
        topbar.grid_propagate(False)
        topbar.columnconfigure(1, weight=1)

        tk.Label(
            topbar,
            text="CODE STATION",
            font=FONT_TITLE,
            bg=BG_TOPBAR,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=14)

        self.top_info_var = tk.StringVar(value=str(self.workspace_root))
        tk.Label(
            topbar,
            textvariable=self.top_info_var,
            font=FONT_TOP,
            bg=BG_TOPBAR,
            fg=FG_MUTED,
        ).grid(row=0, column=1, sticky="e", padx=14)

        controls = tk.Frame(self, bg=BG_MAIN)
        controls.grid(row=1, column=0, sticky="ew", padx=12, pady=(0, 10))
        controls.columnconfigure(1, weight=1)

        tk.Label(controls, text="Workspace", font=FONT_LABEL, bg=BG_MAIN, fg=FG_MUTED).grid(row=0, column=0, sticky="w", padx=(0, 6))

        self.workspace_var = tk.StringVar(value=str(self.workspace_root))
        self.workspace_entry = tk.Entry(
            controls,
            textvariable=self.workspace_var,
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
        )
        self.workspace_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), ipady=5)

        btns = tk.Frame(controls, bg=BG_MAIN)
        btns.grid(row=0, column=2, sticky="e")

        def mkbtn(text, cmd):
            return tk.Button(
                btns,
                text=text,
                command=cmd,
                bg=BG_BUTTON,
                fg=FG_MAIN,
                activebackground=BG_ACTIVE,
                activeforeground=FG_WHITE,
                relief="flat",
                padx=10,
                pady=6,
                bd=0,
            )

        mkbtn("Reload", self._reload_workspace).pack(side="left", padx=(0, 6))
        mkbtn("Save", self._save_current_file).pack(side="left", padx=(0, 6))
        mkbtn("Run", self._run_current_file).pack(side="left", padx=(0, 6))
        mkbtn("Stop", self._stop_process).pack(side="left", padx=(0, 6))
        mkbtn("New File", self._new_file).pack(side="left", padx=(0, 6))
        mkbtn("New Folder", self._new_folder).pack(side="left", padx=(0, 6))
        mkbtn("Delete", self._delete_selected).pack(side="left", padx=(0, 6))
        mkbtn("Copy Path", self._copy_current_path).pack(side="left", padx=(0, 6))
        mkbtn("Refresh Index", self._rebuild_code_index).pack(side="left", padx=(0, 6))
        mkbtn("Clear Console", self._clear_console).pack(side="left", padx=(0, 6))

        self.hidden_btn = tk.Button(
            btns,
            text="Hidden: OFF",
            command=self._toggle_hidden,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        )
        self.hidden_btn.pack(side="left")

        vertical = tk.PanedWindow(self, orient="vertical", sashwidth=6, bg=BG_MAIN)
        vertical.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        top_content = tk.PanedWindow(vertical, orient="horizontal", sashwidth=6, bg=BG_MAIN)
        vertical.add(top_content, minsize=500)

        left = tk.Frame(top_content, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        center = tk.Frame(top_content, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        right = tk.Frame(top_content, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)

        top_content.add(left, minsize=320)
        top_content.add(center, minsize=750)
        top_content.add(right, minsize=380)

        console_frame = tk.Frame(vertical, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        vertical.add(console_frame, minsize=180)

        self._build_tree_side(left)
        self._build_editor_side(center)
        self._build_right_side(right)
        self._build_console_side(console_frame)

        footer = tk.Frame(self, bg=BG_TOPBAR, height=32, highlightbackground=BORDER, highlightthickness=1)
        footer.grid(row=3, column=0, sticky="ew", padx=12, pady=(0, 12))
        footer.grid_propagate(False)

        self.status_var = tk.StringVar(value="READY")
        tk.Label(
            footer,
            textvariable=self.status_var,
            font=FONT_LABEL,
            bg=BG_TOPBAR,
            fg=FG_MUTED,
        ).pack(side="left", padx=10)

    def _build_tree_side(self, parent: tk.Frame):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        tk.Label(
            parent,
            text="Workspace Explorer",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 8))

        shell = tk.Frame(parent, bg=BG_PANEL)
        shell.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(shell, show="tree")
        self.tree.grid(row=0, column=0, sticky="nsew")

        scrollbar_y = ttk.Scrollbar(shell, orient="vertical", command=self.tree.yview)
        scrollbar_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=scrollbar_y.set)

        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)
        self.tree.bind("<Double-1>", self._on_tree_double_click)

    def _build_editor_side(self, parent: tk.Frame):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        self.editor_title_var = tk.StringVar(value="Editor")
        tk.Label(
            parent,
            textvariable=self.editor_title_var,
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 8))

        shell = tk.Frame(parent, bg=BG_PANEL)
        shell.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        self.editor = tk.Text(
            shell,
            wrap="none",
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_MONO,
            undo=True,
        )
        self.editor.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(shell, orient="vertical", command=self.editor.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.editor.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(shell, orient="horizontal", command=self.editor.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.editor.configure(xscrollcommand=scroll_x.set)

        self.editor.bind("<<Modified>>", self._on_editor_modified)

    def _build_right_side(self, parent: tk.Frame):
        parent.rowconfigure(3, weight=1)
        parent.columnconfigure(0, weight=1)

        tk.Label(
            parent,
            text="File Info",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 8))

        self.info_text = tk.Text(
            parent,
            wrap="word",
            height=10,
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_TEXT,
        )
        self.info_text.grid(row=1, column=0, sticky="ew", padx=10, pady=(0, 10))
        self.info_text.configure(state="disabled")

        search_row = tk.Frame(parent, bg=BG_PANEL)
        search_row.grid(row=2, column=0, sticky="ew", padx=10, pady=(0, 8))
        search_row.columnconfigure(1, weight=1)

        tk.Label(
            search_row,
            text="Code Search",
            font=FONT_LABEL,
            bg=BG_PANEL,
            fg=FG_MUTED,
        ).grid(row=0, column=0, sticky="w", padx=(0, 8))

        self.code_search_var = tk.StringVar(value="")
        self.code_search_entry = tk.Entry(
            search_row,
            textvariable=self.code_search_var,
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
        )
        self.code_search_entry.grid(row=0, column=1, sticky="ew", ipady=4)
        self.code_search_entry.bind("<KeyRelease>", self._on_code_search_change)

        tk.Label(
            parent,
            text="Existing Code Files",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=3, column=0, sticky="nw", padx=10, pady=(0, 8))

        list_shell = tk.Frame(parent, bg=BG_PANEL)
        list_shell.grid(row=4, column=0, sticky="nsew", padx=10, pady=(0, 10))
        list_shell.rowconfigure(0, weight=1)
        list_shell.columnconfigure(0, weight=1)

        self.code_list = ttk.Treeview(
            list_shell,
            columns=("relpath",),
            show="headings",
            height=18,
        )
        self.code_list.grid(row=0, column=0, sticky="nsew")

        self.code_list.heading("relpath", text="relative_path")
        self.code_list.column("relpath", anchor="w", width=320)

        code_scroll_y = ttk.Scrollbar(list_shell, orient="vertical", command=self.code_list.yview)
        code_scroll_y.grid(row=0, column=1, sticky="ns")
        self.code_list.configure(yscrollcommand=code_scroll_y.set)

        self.code_list.bind("<Double-1>", self._on_code_list_double_click)

    def _build_console_side(self, parent: tk.Frame):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        tk.Label(
            parent,
            text="Console",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 8))

        shell = tk.Frame(parent, bg=BG_PANEL)
        shell.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        shell.rowconfigure(0, weight=1)
        shell.columnconfigure(0, weight=1)

        self.console = tk.Text(
            shell,
            wrap="none",
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_MONO,
        )
        self.console.grid(row=0, column=0, sticky="nsew")

        scroll_y = ttk.Scrollbar(shell, orient="vertical", command=self.console.yview)
        scroll_y.grid(row=0, column=1, sticky="ns")
        self.console.configure(yscrollcommand=scroll_y.set)

        scroll_x = ttk.Scrollbar(shell, orient="horizontal", command=self.console.xview)
        scroll_x.grid(row=1, column=0, sticky="ew")
        self.console.configure(xscrollcommand=scroll_x.set)

        self.console.configure(state="disabled")

    # ========================================================
    # STATUS / CONSOLE
    # ========================================================

    def _update_status(self, msg: str):
        self.status_var.set(msg)
        self.top_info_var.set(str(self.workspace_root))

    def _append_console(self, text: str):
        self.console.configure(state="normal")
        self.console.insert("end", text)
        self.console.see("end")
        self.console.configure(state="disabled")

    def _clear_console(self):
        self.console.configure(state="normal")
        self.console.delete("1.0", "end")
        self.console.configure(state="disabled")
        self._update_status("Console cleared.")

    # ========================================================
    # TREE
    # ========================================================

    def _load_tree(self):
        self.tree.delete(*self.tree.get_children())
        self.tree.insert("", "end", iid=".", text=".", open=True)
        self._populate_tree_node(".", Path("."))

    def _populate_tree_node(self, parent_iid: str, rel_path: Path):
        abs_dir = (self.workspace_root / rel_path).resolve()
        if not abs_dir.exists() or not abs_dir.is_dir():
            return

        for child in self.tree.get_children(parent_iid):
            self.tree.delete(child)

        try:
            entries = list_dir(abs_dir, ignore_hidden=not self.ignore_hidden.get())
        except Exception as e:
            self.tree.insert(parent_iid, "end", text=f"ERROR: {e}", iid=f"{parent_iid}::__error__")
            return

        for entry in entries:
            child_rel = safe_rel(entry, self.workspace_root)
            iid = make_iid(child_rel)

            if entry.is_dir():
                self.tree.insert(parent_iid, "end", iid=iid, text=entry.name, open=False)
                self.tree.insert(iid, "end", iid=f"{iid}::__placeholder__", text="...")
            else:
                self.tree.insert(parent_iid, "end", iid=iid, text=entry.name)

    def _ensure_loaded(self, iid: str):
        children = self.tree.get_children(iid)
        if len(children) == 1 and children[0].endswith("::__placeholder__"):
            rel = Path("." if iid == "." else iid)
            self._populate_tree_node(iid, rel)

    def _selected_path(self) -> Optional[Path]:
        sel = self.tree.selection()
        if not sel:
            return None
        iid = sel[0]
        if "::__" in iid:
            return None
        rel = Path("." if iid == "." else iid)
        p = (self.workspace_root / rel).resolve()
        if not within_root(p, self.workspace_root):
            return None
        return p

    def _on_tree_open(self, _event=None):
        iid = self.tree.focus()
        if iid:
            self._ensure_loaded(iid)

    def _on_tree_select(self, _event=None):
        self._refresh_info_panel()

    def _on_tree_double_click(self, _event=None):
        path = self._selected_path()
        if path and path.is_file():
            self._open_file(path)

    # ========================================================
    # CODE INDEX
    # ========================================================

    def _iter_code_files(self, root: Path) -> List[Path]:
        out: List[Path] = []
        try:
            for p in root.rglob("*"):
                try:
                    if self.ignore_hidden.get():
                        if any(part.startswith(".") for part in p.parts):
                            continue
                    if is_code_index_file(p):
                        out.append(p)
                except Exception:
                    continue
        except Exception:
            pass

        out.sort(key=lambda x: safe_rel(x, root).lower())
        return out

    def _rebuild_code_index(self):
        self.code_index_files = self._iter_code_files(self.workspace_root)
        self._load_code_list()
        self._update_status(f"Code index rebuilt: {len(self.code_index_files)} files")

    def _load_code_list(self):
        self.code_list.delete(*self.code_list.get_children())

        needle = self.code_search_var.get().strip().lower()

        for p in self.code_index_files:
            rel = safe_rel(p, self.workspace_root)
            if needle and needle not in rel.lower() and needle not in p.name.lower():
                continue
            self.code_list.insert("", "end", iid=rel, values=(rel,))

    def _on_code_search_change(self, _event=None):
        self._load_code_list()

    def _on_code_list_double_click(self, _event=None):
        sel = self.code_list.selection()
        if not sel:
            return

        rel = sel[0]
        path = (self.workspace_root / rel).resolve()
        if path.exists() and path.is_file():
            self._open_file(path)

    # ========================================================
    # FILE INFO
    # ========================================================

    def _refresh_info_panel(self):
        path = self._selected_path()

        lines = []
        if path is None:
            lines.append("No selection.")
        else:
            lines.append(f"path      : {path}")
            lines.append(f"relative  : {safe_rel(path, self.workspace_root)}")
            lines.append(f"type      : {'dir' if path.is_dir() else 'file'}")

            if path.exists():
                try:
                    stat = path.stat()
                    lines.append(f"size      : {stat.st_size} bytes")
                except Exception:
                    lines.append("size      : -")

            if path.is_file():
                lines.append(f"suffix    : {path.suffix}")
                lines.append(f"text_file : {is_text_file(path)}")
                lines.append(f"runnable  : {path.suffix.lower() == '.py'}")

        lines.append("")
        lines.append(f"workspace_root : {self.workspace_root}")
        lines.append(f"indexed_files  : {len(self.code_index_files)}")

        self.info_text.configure(state="normal")
        self.info_text.delete("1.0", "end")
        self.info_text.insert("1.0", "\n".join(lines))
        self.info_text.configure(state="disabled")

    # ========================================================
    # EDITOR
    # ========================================================

    def _open_file(self, path: Path):
        if not within_root(path, self.workspace_root):
            self._update_status("Open blocked: path outside workspace.")
            return

        if not path.exists() or not path.is_file():
            self._update_status(f"File not found: {path}")
            return

        if not is_text_file(path):
            self._update_status(f"Unsupported file type: {path.name}")
            return

        if self.editor_dirty and self.current_file is not None:
            answer = messagebox.askyesnocancel(
                "Unsaved Changes",
                "Aktuelle Datei hat ungespeicherte Änderungen. Erst speichern?",
            )
            if answer is None:
                return
            if answer is True:
                if not self._save_current_file():
                    return

        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            try:
                text = path.read_text(encoding="latin-1")
            except Exception as e:
                self._update_status(f"Open failed: {e}")
                return
        except Exception as e:
            self._update_status(f"Open failed: {e}")
            return

        self.editor.delete("1.0", "end")
        self.editor.insert("1.0", text)
        self.editor.edit_modified(False)

        self.current_file = path
        self.editor_dirty = False
        self._refresh_editor_title()
        self._refresh_info_panel()
        self._highlight_code_list_for_path(path)
        self._update_status(f"Opened: {path.name}")

    def _highlight_code_list_for_path(self, path: Path):
        rel = safe_rel(path, self.workspace_root)
        if self.code_list.exists(rel):
            self.code_list.selection_set(rel)
            self.code_list.focus(rel)
            self.code_list.see(rel)

    def _refresh_editor_title(self):
        if self.current_file is None:
            self.editor_title_var.set("Editor")
            return

        mark = "*" if self.editor_dirty else ""
        self.editor_title_var.set(f"Editor | {self.current_file.name}{mark}")

    def _on_editor_modified(self, _event=None):
        try:
            modified = self.editor.edit_modified()
        except Exception:
            modified = False

        if modified:
            self.editor_dirty = True
            self._refresh_editor_title()
            self.editor.edit_modified(False)

    def _save_current_file(self) -> bool:
        if self.current_file is None:
            self._update_status("No file open.")
            return False

        if not within_root(self.current_file, self.workspace_root):
            self._update_status("Save blocked: file outside workspace.")
            return False

        try:
            text = self.editor.get("1.0", "end-1c")
            self.current_file.write_text(text, encoding="utf-8")
            self.editor_dirty = False
            self._refresh_editor_title()
            self._refresh_info_panel()
            self._rebuild_code_index()
            self._highlight_code_list_for_path(self.current_file)
            self._update_status(f"Saved: {self.current_file.name}")
            return True
        except Exception as e:
            self._update_status(f"Save failed: {e}")
            return False

    # ========================================================
    # RUN / STOP
    # ========================================================

    def _run_current_file(self):
        if self.current_file is None:
            self._update_status("No file open.")
            return

        if self.current_file.suffix.lower() != ".py":
            self._update_status("Run currently only supports .py files.")
            return

        if self.process is not None and self.process.poll() is None:
            self._update_status("A process is already running.")
            return

        if self.editor_dirty:
            ok = messagebox.askyesno(
                "Unsaved Changes",
                "Datei hat ungespeicherte Änderungen. Vor Ausführung speichern?",
            )
            if ok:
                if not self._save_current_file():
                    return

        self._clear_console()
        self._append_console(f"> RUN {self.current_file}\n\n")

        try:
            self.process = subprocess.Popen(
                [sys.executable, str(self.current_file)],
                cwd=str(self.current_file.parent),
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
            )
        except Exception as e:
            self._append_console(f"START FAILED: {e}\n")
            self._update_status(f"Run failed: {e}")
            self.process = None
            return

        self._update_status(f"Running: {self.current_file.name}")

        def reader():
            proc = self.process
            if proc is None or proc.stdout is None:
                return

            try:
                for line in proc.stdout:
                    self.after(0, lambda ln=line: self._append_console(ln))
            except Exception as e:
                self.after(0, lambda: self._append_console(f"\nREAD ERROR: {e}\n"))
            finally:
                try:
                    return_code = proc.wait(timeout=1)
                except Exception:
                    return_code = None

                def done():
                    if return_code is None:
                        self._append_console("\nPROCESS FINISHED\n")
                        self._update_status("Process finished.")
                    elif return_code == 0:
                        self._append_console(f"\nPROCESS EXITED WITH CODE {return_code}\n")
                        self._update_status("Process finished successfully.")
                    else:
                        self._append_console(f"\nPROCESS EXITED WITH CODE {return_code}\n")
                        self._update_status(f"Process failed with code {return_code}.")

                    self.process = None

                self.after(0, done)

        self.process_thread = threading.Thread(target=reader, daemon=True)
        self.process_thread.start()

    def _stop_process(self):
        if self.process is None or self.process.poll() is not None:
            self._update_status("No running process.")
            return

        try:
            self.process.terminate()
            self._append_console("\n> STOP REQUESTED\n")
            self._update_status("Stop requested.")
        except Exception as e:
            self._append_console(f"\nSTOP FAILED: {e}\n")
            self._update_status(f"Stop failed: {e}")

    # ========================================================
    # ACTIONS
    # ========================================================

    def _reload_workspace(self):
        new_root = Path(self.workspace_var.get()).expanduser().resolve()
        if not new_root.exists() or not new_root.is_dir():
            self._update_status(f"Invalid workspace: {new_root}")
            return

        if not within_root(new_root, FTMO_ROOT) and new_root != FTMO_ROOT:
            self._update_status("Workspace blocked: outside FTMO root.")
            return

        self.workspace_root = new_root
        self.current_file = None
        self.editor_dirty = False
        self.editor.delete("1.0", "end")
        self._refresh_editor_title()
        self._load_tree()
        self._rebuild_code_index()
        self._refresh_info_panel()
        self._update_status(f"Workspace loaded: {self.workspace_root}")

    def _toggle_hidden(self):
        self.ignore_hidden.set(not self.ignore_hidden.get())
        self.hidden_btn.configure(text="Hidden: ON" if self.ignore_hidden.get() else "Hidden: OFF")
        self._load_tree()
        self._rebuild_code_index()
        self._update_status("Explorer and index reloaded.")

    def _new_file(self):
        base = self._selected_path()
        if base is None:
            base = self.workspace_root
        if base.is_file():
            base = base.parent

        name = simpledialog.askstring("New File", "Dateiname:")
        if not name:
            return

        target = (base / name).resolve()
        if not within_root(target, self.workspace_root):
            self._update_status("Create blocked: outside workspace.")
            return

        if target.exists():
            self._update_status("File already exists.")
            return

        try:
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_text("", encoding="utf-8")
            self._load_tree()
            self._rebuild_code_index()
            self._update_status(f"File created: {target.name}")
        except Exception as e:
            self._update_status(f"Create file failed: {e}")

    def _new_folder(self):
        base = self._selected_path()
        if base is None:
            base = self.workspace_root
        if base.is_file():
            base = base.parent

        name = simpledialog.askstring("New Folder", "Ordnername:")
        if not name:
            return

        target = (base / name).resolve()
        if not within_root(target, self.workspace_root):
            self._update_status("Create blocked: outside workspace.")
            return

        if target.exists():
            self._update_status("Folder already exists.")
            return

        try:
            target.mkdir(parents=True, exist_ok=True)
            self._load_tree()
            self._rebuild_code_index()
            self._update_status(f"Folder created: {target.name}")
        except Exception as e:
            self._update_status(f"Create folder failed: {e}")

    def _delete_selected(self):
        path = self._selected_path()
        if path is None or path == self.workspace_root:
            self._update_status("Nothing deletable selected.")
            return

        if not within_root(path, self.workspace_root):
            self._update_status("Delete blocked: outside workspace.")
            return

        ok = messagebox.askyesno("Delete", f"Wirklich löschen?\n\n{path}")
        if not ok:
            return

        try:
            if path.is_dir():
                shutil.rmtree(path)
            else:
                path.unlink()

            if self.current_file is not None and self.current_file == path:
                self.current_file = None
                self.editor_dirty = False
                self.editor.delete("1.0", "end")
                self._refresh_editor_title()

            self._load_tree()
            self._rebuild_code_index()
            self._refresh_info_panel()
            self._update_status(f"Deleted: {path.name}")
        except Exception as e:
            self._update_status(f"Delete failed: {e}")

    def _copy_current_path(self):
        path = self.current_file or self._selected_path()
        if path is None:
            self._update_status("No path available.")
            return

        self.clipboard_clear()
        self.clipboard_append(str(path))
        self._update_status(f"Copied path: {path}")

    def destroy(self):
        try:
            if self.process is not None and self.process.poll() is None:
                self.process.terminate()
        except Exception:
            pass
        super().destroy()


# ============================================================
# STANDALONE
# ============================================================

class CodeStationDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Code Station")
        self.geometry("1850x1100")
        self.minsize(1350, 850)
        self.configure(bg=BG_MAIN)

        self.panel = CodeStationPanel(self)
        self.panel.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            self.panel.destroy()
        except Exception:
            pass
        self.destroy()


def main():
    app = CodeStationDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()