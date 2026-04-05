# -*- coding: utf-8 -*-
"""
Quant_Structure/FTMO/Dashboards/Main_Board/pages/Visual_Folder/Visual_Folder.py

Zweck:
- Visual Folder Explorer als Tkinter-Panel für das FTMO Main Board
- Links: interaktiver Folder Tree
- Rechts: sichtbarer ASCII-Tree als Nebenfenster
- One-click Copy
- One-click Export
- Hidden-Dateien optional
- Root frei wählbar

Einbettung im Main Board:
    panel_class_name="FolderExplorerPanel"

Standalone:
    python Quant_Structure/FTMO/Dashboards/Main_Board/pages/Visual_Folder/Visual_Folder.py
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

import tkinter as tk
from tkinter import ttk


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

DEFAULT_ROOT = FTMO_ROOT
DEFAULT_OUTPUT_PATH = FTMO_ROOT / "Dashboards" / "Main_Board" / "runtime" / "visible_tree.txt"
DEFAULT_OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)


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

BORDER = "#232A34"

FONT_TITLE = ("Segoe UI", 18, "bold")
FONT_TOP = ("Segoe UI", 10, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_LABEL = ("Segoe UI", 9)
FONT_TEXT = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)


# ============================================================
# MODEL
# ============================================================

@dataclass
class VisibleNode:
    name: str
    rel_posix: str
    kind: str  # "dir" | "file"
    children: Optional[List["VisibleNode"]] = None


def build_visible_tree(
    root: Path,
    rel: Path,
    expanded_paths: set[str],
    ignore_hidden: bool = True,
) -> VisibleNode:
    abs_path = (root / rel).resolve()
    if not abs_path.exists():
        raise FileNotFoundError(str(abs_path))
    if not abs_path.is_dir():
        raise NotADirectoryError(str(abs_path))

    entries = list(abs_path.iterdir())
    if ignore_hidden:
        entries = [e for e in entries if not e.name.startswith(".")]

    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))

    rel_posix = rel.as_posix()
    children: List[VisibleNode] = []

    for e in entries:
        child_rel = rel / e.name
        child_rel_posix = child_rel.as_posix()

        if e.is_dir():
            if child_rel_posix in expanded_paths:
                children.append(
                    build_visible_tree(
                        root=root,
                        rel=child_rel,
                        expanded_paths=expanded_paths,
                        ignore_hidden=ignore_hidden,
                    )
                )
            else:
                children.append(
                    VisibleNode(
                        name=e.name,
                        rel_posix=child_rel_posix,
                        kind="dir",
                        children=[],
                    )
                )
        else:
            children.append(
                VisibleNode(
                    name=e.name,
                    rel_posix=child_rel_posix,
                    kind="file",
                    children=None,
                )
            )

    node_name = "." if rel_posix == "." else rel.name
    return VisibleNode(name=node_name, rel_posix=rel_posix, kind="dir", children=children)


def render_ascii_tree(node: VisibleNode) -> str:
    lines: List[str] = []

    def rec(n: VisibleNode, prefix: str = "", is_last: bool = True, is_root: bool = False):
        if is_root:
            lines.append(".")
        else:
            connector = "└── " if is_last else "├── "
            lines.append(prefix + connector + n.name)

        kids = n.children or []
        if not kids:
            return

        next_prefix = prefix + ("    " if is_last else "│   ")
        for i, c in enumerate(kids):
            rec(c, next_prefix, i == (len(kids) - 1), is_root=False)

    rec(node, prefix="", is_last=True, is_root=True)
    return "\n".join(lines) + "\n"


# ============================================================
# HELPERS
# ============================================================

def make_iid(rel_path: str) -> str:
    return rel_path if rel_path else "."


def safe_rel(path: Path, root: Path) -> str:
    try:
        rel = path.resolve().relative_to(root.resolve())
        s = rel.as_posix()
        return s if s else "."
    except Exception:
        return "."


def list_dir(path: Path, ignore_hidden: bool) -> List[Path]:
    entries = list(path.iterdir())
    if ignore_hidden:
        entries = [e for e in entries if not e.name.startswith(".")]
    entries.sort(key=lambda p: (not p.is_dir(), p.name.lower()))
    return entries


# ============================================================
# PANEL
# ============================================================

class FolderExplorerPanel(tk.Frame):
    def __init__(self, parent):
        super().__init__(parent, bg=BG_MAIN)

        self.root_path = Path(DEFAULT_ROOT).resolve()
        self.output_path = Path(DEFAULT_OUTPUT_PATH).resolve()
        self.ignore_hidden = tk.BooleanVar(value=True)
        self.expanded_paths: set[str] = {"."}

        self._build_ui()
        self._load_tree()
        self._refresh_ascii_preview()

    # ========================================================
    # UI
    # ========================================================

    def _build_ui(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(2, weight=1)

        topbar = tk.Frame(self, bg=BG_TOPBAR, height=52, highlightbackground=BORDER, highlightthickness=1)
        topbar.grid(row=0, column=0, sticky="ew", padx=12, pady=(12, 10))
        topbar.grid_propagate(False)
        topbar.columnconfigure(1, weight=1)

        tk.Label(
            topbar,
            text="VISUAL FOLDER",
            font=FONT_TITLE,
            bg=BG_TOPBAR,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=14)

        self.top_info_var = tk.StringVar(value="")
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
        controls.columnconfigure(3, weight=1)

        tk.Label(controls, text="Root", font=FONT_LABEL, bg=BG_MAIN, fg=FG_MUTED).grid(row=0, column=0, sticky="w", padx=(0, 6))
        self.root_var = tk.StringVar(value=str(self.root_path))
        self.root_entry = tk.Entry(
            controls,
            textvariable=self.root_var,
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
        )
        self.root_entry.grid(row=0, column=1, sticky="ew", padx=(0, 10), ipady=5)

        tk.Label(controls, text="Output", font=FONT_LABEL, bg=BG_MAIN, fg=FG_MUTED).grid(row=0, column=2, sticky="w", padx=(0, 6))
        self.output_var = tk.StringVar(value=str(self.output_path))
        self.output_entry = tk.Entry(
            controls,
            textvariable=self.output_var,
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
        )
        self.output_entry.grid(row=0, column=3, sticky="ew", padx=(0, 10), ipady=5)

        btns = tk.Frame(controls, bg=BG_MAIN)
        btns.grid(row=0, column=4, sticky="e")

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
        self.hidden_btn.pack(side="left", padx=(0, 6))

        tk.Button(
            btns,
            text="Reload",
            command=self._reload_from_input,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btns,
            text="Expand All",
            command=self._expand_all,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btns,
            text="Collapse All",
            command=self._collapse_all,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btns,
            text="Copy",
            command=self._copy_ascii_to_clipboard,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 6))

        tk.Button(
            btns,
            text="Export",
            command=self._export_ascii,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_ACTIVE,
            activeforeground=FG_WHITE,
            relief="flat",
            padx=10,
            pady=6,
            bd=0,
        ).pack(side="left")

        content = tk.PanedWindow(self, orient="horizontal", sashwidth=6, bg=BG_MAIN)
        content.grid(row=2, column=0, sticky="nsew", padx=12, pady=(0, 12))

        left = tk.Frame(content, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        right = tk.Frame(content, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)

        content.add(left, minsize=420)
        content.add(right, minsize=520)

        self._build_tree_side(left)
        self._build_preview_side(right)

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
            text="Folder Tree",
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

        tree_scroll_y = ttk.Scrollbar(shell, orient="vertical", command=self.tree.yview)
        tree_scroll_y.grid(row=0, column=1, sticky="ns")
        self.tree.configure(yscrollcommand=tree_scroll_y.set)

        self.tree.bind("<<TreeviewOpen>>", self._on_tree_open)
        self.tree.bind("<<TreeviewClose>>", self._on_tree_close)
        self.tree.bind("<<TreeviewSelect>>", self._on_tree_select)

    def _build_preview_side(self, parent: tk.Frame):
        parent.rowconfigure(1, weight=1)
        parent.columnconfigure(0, weight=1)

        tk.Label(
            parent,
            text="Visible Tree Output",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_WHITE,
        ).grid(row=0, column=0, sticky="w", padx=10, pady=(10, 8))

        self.preview = tk.Text(
            parent,
            wrap="none",
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_MONO,
        )
        self.preview.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        self.preview.configure(state="disabled")

    # ========================================================
    # TREE LOGIC
    # ========================================================

    def _load_tree(self):
        self.tree.delete(*self.tree.get_children())

        root_iid = make_iid(".")
        self.tree.insert("", "end", iid=root_iid, text=".", open=True, values=())
        self._populate_tree_node(root_iid, Path("."))
        self.expanded_paths = {"."}
        self.top_info_var.set(str(self.root_path))
        self.status_var.set("Tree loaded.")

    def _populate_tree_node(self, parent_iid: str, rel_path: Path):
        abs_dir = (self.root_path / rel_path).resolve()
        if not abs_dir.exists() or not abs_dir.is_dir():
            return

        for child in self.tree.get_children(parent_iid):
            self.tree.delete(child)

        try:
            entries = list_dir(abs_dir, ignore_hidden=not self.ignore_hidden.get())
        except PermissionError:
            self.tree.insert(parent_iid, "end", text="⛔ Permission denied", iid=f"{parent_iid}::__denied__")
            return
        except Exception as e:
            self.tree.insert(parent_iid, "end", text=f"⛔ {e}", iid=f"{parent_iid}::__error__")
            return

        for entry in entries:
            child_rel = safe_rel(entry, self.root_path)
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

    def _on_tree_open(self, _event=None):
        sel = self.tree.focus()
        if not sel:
            return
        self._ensure_loaded(sel)
        if sel != ".":
            self.expanded_paths.add(sel)
        self._refresh_ascii_preview()

    def _on_tree_close(self, _event=None):
        sel = self.tree.focus()
        if not sel:
            return
        if sel != "." and sel in self.expanded_paths:
            self.expanded_paths.discard(sel)
        self._refresh_ascii_preview()

    def _on_tree_select(self, _event=None):
        pass

    def _collect_all_dirs(self, rel: Path = Path(".")) -> List[str]:
        abs_dir = (self.root_path / rel).resolve()
        out: List[str] = []
        if not abs_dir.exists() or not abs_dir.is_dir():
            return out

        try:
            entries = list_dir(abs_dir, ignore_hidden=not self.ignore_hidden.get())
        except Exception:
            return out

        for entry in entries:
            if entry.is_dir():
                child_rel = safe_rel(entry, self.root_path)
                out.append(child_rel)
                out.extend(self._collect_all_dirs(Path(child_rel)))
        return out

    def _expand_all(self):
        all_dirs = self._collect_all_dirs(Path("."))
        self.expanded_paths = {"."} | set(all_dirs)
        self._load_tree()

        for rel in sorted(self.expanded_paths, key=lambda x: x.count("/")):
            iid = make_iid(rel)
            if self.tree.exists(iid):
                self._ensure_loaded(iid)
                self.tree.item(iid, open=True)

        self._refresh_ascii_preview()
        self.status_var.set("All folders expanded.")

    def _collapse_all(self):
        self.expanded_paths = {"."}
        self._load_tree()
        self._refresh_ascii_preview()
        self.status_var.set("All folders collapsed.")

    # ========================================================
    # OUTPUT
    # ========================================================

    def _refresh_ascii_preview(self):
        try:
            visible = build_visible_tree(
                root=self.root_path,
                rel=Path("."),
                expanded_paths=set(self.expanded_paths),
                ignore_hidden=not self.ignore_hidden.get(),
            )
            txt = render_ascii_tree(visible)
        except Exception as e:
            txt = f"ERROR: {e}\n"

        self.preview.configure(state="normal")
        self.preview.delete("1.0", "end")
        self.preview.insert("1.0", txt)
        self.preview.configure(state="disabled")

    def _copy_ascii_to_clipboard(self):
        txt = self.preview.get("1.0", "end-1c")
        self.clipboard_clear()
        self.clipboard_append(txt)
        self.status_var.set("Visible tree copied to clipboard.")

    def _export_ascii(self):
        try:
            self.output_path = Path(self.output_var.get()).expanduser().resolve()
            self.output_path.parent.mkdir(parents=True, exist_ok=True)
            txt = self.preview.get("1.0", "end-1c") + "\n"
            self.output_path.write_text(txt, encoding="utf-8")
            self.status_var.set(f"Exported: {self.output_path}")
            self.top_info_var.set(str(self.root_path))
        except Exception as e:
            self.status_var.set(f"Export failed: {e}")

    # ========================================================
    # CONTROLS
    # ========================================================

    def _reload_from_input(self):
        try:
            new_root = Path(self.root_var.get()).expanduser().resolve()
            if not new_root.exists() or not new_root.is_dir():
                self.status_var.set(f"Invalid root: {new_root}")
                return

            self.root_path = new_root
            self.output_path = Path(self.output_var.get()).expanduser().resolve()
            self.output_path.parent.mkdir(parents=True, exist_ok=True)

            self._load_tree()
            self._refresh_ascii_preview()
            self.status_var.set(f"Reloaded: {self.root_path}")
        except Exception as e:
            self.status_var.set(f"Reload failed: {e}")

    def _toggle_hidden(self):
        self.ignore_hidden.set(not self.ignore_hidden.get())
        self.hidden_btn.configure(text="Hidden: ON" if self.ignore_hidden.get() else "Hidden: OFF")
        self._load_tree()
        self._refresh_ascii_preview()

    def destroy(self):
        super().destroy()


# ============================================================
# STANDALONE
# ============================================================

class FolderExplorerDashboard(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Visual Folder")
        self.geometry("1600x950")
        self.minsize(1200, 700)
        self.configure(bg=BG_MAIN)

        self.panel = FolderExplorerPanel(self)
        self.panel.pack(fill="both", expand=True)

        self.protocol("WM_DELETE_WINDOW", self._on_close)

    def _on_close(self):
        try:
            self.panel.destroy()
        except Exception:
            pass
        self.destroy()


def main():
    app = FolderExplorerDashboard()
    app.mainloop()


if __name__ == "__main__":
    main()