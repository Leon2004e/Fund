# -*- coding: utf-8 -*-
"""
Quant_Structure/FTMO/Dashboards/Main_Board/pages/Loop_Management/loop_management_board.py

Zweck:
- Eingebettetes Loop Management Panel für das Main Board
- Kann zusätzlich weiterhin standalone gestartet werden
- Bloomberg-inspirierter Dark-Ops Stil
- Robuste Script-Auflösung
- Echter Auto-Restart
- Verwendet deine aktuelle Struktur unter:
    Quant_Structure/FTMO/
        ├── Dashboards
        │   └── Main_Board
        │       ├── pages
        │       │   └── Loop_Management
        │       │       ├── runtime
        │       │       └── loop_management_board.py
        └── Data_Center

Wichtig:
- Für Einbettung im Main Board existiert jetzt:
    class LoopManagementPanel(tk.Frame)
- Für Standalone existiert zusätzlich:
    class LoopManagementBoardApp(tk.Tk)
"""

from __future__ import annotations

import json
import os
import signal
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk, messagebox


# ============================================================
# PATH HELPERS
# ============================================================

def find_ftmo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "Data_Center").exists() and (p / "Dashboards").exists():
            return p
    raise RuntimeError(
        f"FTMO-Root nicht gefunden. Erwartet FTMO-Root mit 'Data_Center' und 'Dashboards'. Start={start}"
    )


SCRIPT_PATH = Path(__file__).resolve()
FTMO_ROOT = find_ftmo_root(SCRIPT_PATH)

DASHBOARDS_DIR = FTMO_ROOT / "Dashboards"
LOOP_MGMT_DIR = SCRIPT_PATH.parent
RUNTIME_DIR = LOOP_MGMT_DIR / "runtime"
STATE_FILE = RUNTIME_DIR / "loop_state.json"
LOG_DIR = RUNTIME_DIR / "logs"


# ============================================================
# HELPERS
# ============================================================

def ensure_dir(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)


def find_script_by_name(project_root: Path, filename: str) -> Optional[Path]:
    hits = list(project_root.rglob(filename))
    if not hits:
        return None

    hits_sorted = sorted(
        hits,
        key=lambda p: (
            "Data_Center" not in str(p),
            "Data_Operations" not in str(p),
            len(str(p)),
        ),
    )
    return hits_sorted[0]


def resolve_script_path(loop_cfg: Dict[str, Any]) -> Path:
    raw_script_path = loop_cfg.get("script_path")
    if raw_script_path:
        p = Path(raw_script_path)
        if not p.is_absolute():
            p = FTMO_ROOT / p
        if p.exists():
            return p.resolve()

    for candidate in loop_cfg.get("script_candidates", []) or []:
        p = Path(candidate)
        if not p.is_absolute():
            p = FTMO_ROOT / p
        if p.exists():
            return p.resolve()

    script_name = str(loop_cfg.get("script_name", "")).strip()
    if script_name:
        found = find_script_by_name(FTMO_ROOT, script_name)
        if found is not None and found.exists():
            return found.resolve()

    raise FileNotFoundError(
        f"Script nicht gefunden für loop_id={loop_cfg.get('id')} | "
        f"script_path={raw_script_path} | "
        f"script_name={loop_cfg.get('script_name')}"
    )


def shorten_path(s: str, max_len: int = 72) -> str:
    if len(s) <= max_len:
        return s
    return "..." + s[-(max_len - 3):]


# ============================================================
# LOOP CONFIG
# ============================================================

LOOP_DEFINITIONS: List[Dict[str, object]] = [
    {
        "id": "spread_logger",
        "label": "Spread Logger",
        "script_name": "Spread_Data_Management.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Market/Spread_Logger_Loop/Spread_Data_Management.py",
            "Data_Center/Data_Operations/Market/Spread_Logger/Spread_Data_Management.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "ohlc_loader",
        "label": "OHLC Loader",
        "script_name": "Ohcl_Loader.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Market/Ohcl_Logger_Loop/Ohcl_Loader.py",
            "Data_Center/Data_Operations/Market/Ohcl_Generator_Loop/Ohcl_Loader.py",
            "Data_Center/Data_Operations/Market/Ohcl_Loader.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "strategy_performance_loop",
        "label": "Strategy Perf",
        "script_name": "Strategy_Performance_Loop.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Strategy_Performance_Loop/Strategy_Performance_Loop.py",
            "Data_Center/Data_Operations/Strategy_Performance_Loop/Strategy_Performance_Loop.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trades_combiner",
        "label": "Trades Combiner",
        "script_name": "Trades_Combiner.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trades_Combiner/Trades_Combiner.py",
            "Data_Center/Data_Operations/Trades_Combiner/Trades_Combiner.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_live_530164208",
        "label": "LIVE 530164208",
        "script_name": "Trade_Logger_FTMO_LIVE_530164208.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_LIVE_530164208.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_live_540130486",
        "label": "LIVE 540130486",
        "script_name": "Trade_Logger_FTMO_LIVE_540130486.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_LIVE_540130486.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_live_540136817",
        "label": "LIVE 540136817",
        "script_name": "Trade_Logger_FTMO_LIVE_540136817.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_LIVE_540136817.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_live_540136824",
        "label": "LIVE 540136824",
        "script_name": "Trade_Logger_FTMO_LIVE_540136824.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_LIVE_540136824.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_demo_1",
        "label": "DEMO 1",
        "script_name": "Trade_Logger_FTMO_DEMO_1.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_DEMO_1.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
    {
        "id": "trade_logger_demo_2",
        "label": "DEMO 2",
        "script_name": "Trade_Logger_FTMO_DEMO_2.py",
        "script_candidates": [
            "Data_Center/Data_Operations/Trades/Trade_Logger_Loop/Trade_Logger_FTMO_DEMO_2.py",
        ],
        "cwd": None,
        "env": {},
        "auto_restart": False,
    },
]


# ============================================================
# DATA MODELS
# ============================================================

@dataclass
class LoopState:
    loop_id: str
    pid: Optional[int] = None
    running: bool = False
    started_at_epoch: Optional[float] = None
    last_exit_code: Optional[int] = None
    auto_restart: bool = False
    log_file: Optional[str] = None
    script_path: Optional[str] = None


# ============================================================
# FS / JSON
# ============================================================

def load_state() -> Dict[str, LoopState]:
    ensure_dir(RUNTIME_DIR)
    ensure_dir(LOG_DIR)

    if not STATE_FILE.exists():
        return {}

    try:
        raw = json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}

    out: Dict[str, LoopState] = {}
    for loop_id, payload in raw.items():
        try:
            out[loop_id] = LoopState(**payload)
        except Exception:
            out[loop_id] = LoopState(loop_id=loop_id)
    return out


def save_state(state: Dict[str, LoopState]) -> None:
    ensure_dir(RUNTIME_DIR)
    payload = {k: asdict(v) for k, v in state.items()}
    tmp = STATE_FILE.with_suffix(".tmp")
    tmp.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    tmp.replace(STATE_FILE)


# ============================================================
# PROCESS HELPERS
# ============================================================

def is_pid_running(pid: Optional[int]) -> bool:
    if pid is None or pid <= 0:
        return False

    try:
        if os.name == "nt":
            import ctypes

            kernel32 = ctypes.windll.kernel32
            PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
            handle = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
            if not handle:
                return False
            try:
                code = ctypes.c_ulong()
                kernel32.GetExitCodeProcess(handle, ctypes.byref(code))
                STILL_ACTIVE = 259
                return code.value == STILL_ACTIVE
            finally:
                kernel32.CloseHandle(handle)
        else:
            os.kill(pid, 0)
            return True
    except Exception:
        return False


def build_log_file(loop_id: str) -> Path:
    ensure_dir(LOG_DIR)
    ts = time.strftime("%Y%m%d_%H%M%S")
    return LOG_DIR / f"{loop_id}_{ts}.log"


def start_loop_process(loop_cfg: Dict[str, object], existing_state: LoopState) -> LoopState:
    script_path = resolve_script_path(loop_cfg)

    if existing_state.pid and is_pid_running(existing_state.pid):
        raise RuntimeError(f"Loop läuft bereits mit PID {existing_state.pid}")

    env = os.environ.copy()
    env.update({str(k): str(v) for k, v in dict(loop_cfg.get("env", {})).items()})

    cwd = loop_cfg.get("cwd")
    cwd_path = Path(cwd) if cwd else script_path.parent

    log_file = build_log_file(str(loop_cfg["id"]))

    creationflags = 0
    if os.name == "nt":
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP

    log_handle = open(log_file, "a", encoding="utf-8", buffering=1)

    try:
        proc = subprocess.Popen(
            [sys.executable, str(script_path)],
            cwd=str(cwd_path),
            env=env,
            stdout=log_handle,
            stderr=subprocess.STDOUT,
            stdin=subprocess.DEVNULL,
            creationflags=creationflags,
        )
    finally:
        try:
            log_handle.close()
        except Exception:
            pass

    return LoopState(
        loop_id=str(loop_cfg["id"]),
        pid=int(proc.pid),
        running=True,
        started_at_epoch=time.time(),
        last_exit_code=None,
        auto_restart=bool(loop_cfg.get("auto_restart", False)),
        log_file=str(log_file),
        script_path=str(script_path),
    )


def stop_pid(pid: int, timeout_sec: float = 8.0) -> Optional[int]:
    if not is_pid_running(pid):
        return 0

    if os.name == "nt":
        try:
            os.kill(pid, signal.CTRL_BREAK_EVENT)
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass

    t0 = time.time()
    while time.time() - t0 < timeout_sec:
        if not is_pid_running(pid):
            return 0
        time.sleep(0.25)

    if os.name == "nt":
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=False,
            )
        except Exception:
            pass
    else:
        try:
            os.kill(pid, signal.SIGKILL)
        except Exception:
            pass

    time.sleep(0.5)
    return 0 if not is_pid_running(pid) else None


# ============================================================
# MANAGER
# ============================================================

class LoopManager:
    def __init__(self, loop_definitions: List[Dict[str, object]]):
        self.loop_definitions = {str(x["id"]): x for x in loop_definitions}
        self.state: Dict[str, LoopState] = load_state()
        self._bootstrap_missing_state()
        self.refresh_runtime_state(save=True)

    def _bootstrap_missing_state(self) -> None:
        for loop_id, cfg in self.loop_definitions.items():
            if loop_id not in self.state:
                script_path_str = ""
                try:
                    script_path_str = str(resolve_script_path(cfg))
                except Exception:
                    script_path_str = str(cfg.get("script_name", ""))

                self.state[loop_id] = LoopState(
                    loop_id=loop_id,
                    pid=None,
                    running=False,
                    started_at_epoch=None,
                    last_exit_code=None,
                    auto_restart=bool(cfg.get("auto_restart", False)),
                    script_path=script_path_str,
                )

    def refresh_runtime_state(self, save: bool = False) -> None:
        changed = False

        for loop_id, st in self.state.items():
            alive = is_pid_running(st.pid)

            if st.running and not alive:
                st.running = False
                st.pid = None
                if st.last_exit_code is None:
                    st.last_exit_code = 0
                changed = True

                if st.auto_restart:
                    try:
                        new_state = start_loop_process(self.loop_definitions[loop_id], st)
                        self.state[loop_id] = new_state
                        changed = True
                    except Exception as e:
                        print(f"[WARN] auto_restart failed for {loop_id}: {e}")

            elif alive and not st.running:
                st.running = True
                changed = True

        if save or changed:
            save_state(self.state)

    def start_loop(self, loop_id: str) -> None:
        cfg = self.loop_definitions[loop_id]
        new_state = start_loop_process(cfg, self.state[loop_id])
        self.state[loop_id] = new_state
        save_state(self.state)

    def stop_loop(self, loop_id: str) -> None:
        st = self.state[loop_id]
        if not st.pid:
            st.running = False
            save_state(self.state)
            return

        stop_pid(st.pid)
        st.running = False
        st.pid = None
        st.last_exit_code = 0
        save_state(self.state)

    def restart_loop(self, loop_id: str) -> None:
        self.stop_loop(loop_id)
        time.sleep(0.5)
        self.start_loop(loop_id)

    def start_all(self) -> None:
        for loop_id in self.loop_definitions:
            try:
                self.refresh_runtime_state(save=False)
                if not self.state[loop_id].running:
                    self.start_loop(loop_id)
            except Exception as e:
                print(f"[WARN] start_all {loop_id} failed: {e}")

    def stop_all(self) -> None:
        for loop_id in self.loop_definitions:
            try:
                if self.state[loop_id].running:
                    self.stop_loop(loop_id)
            except Exception as e:
                print(f"[WARN] stop_all {loop_id} failed: {e}")

    def set_auto_restart(self, loop_id: str, value: bool) -> None:
        self.state[loop_id].auto_restart = bool(value)
        save_state(self.state)

    def get_summary(self) -> Dict[str, int]:
        self.refresh_runtime_state(save=False)
        total = len(self.loop_definitions)
        running = sum(1 for st in self.state.values() if st.running)
        stopped = total - running
        return {"total": total, "running": running, "stopped": stopped}

    def get_rows(self) -> List[Dict[str, str]]:
        self.refresh_runtime_state(save=False)
        rows: List[Dict[str, str]] = []

        for loop_id, cfg in self.loop_definitions.items():
            st = self.state[loop_id]

            started_at = ""
            uptime = ""
            if st.started_at_epoch and st.running:
                started_at = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime(st.started_at_epoch))
                elapsed = max(0, int(time.time() - st.started_at_epoch))
                hh = elapsed // 3600
                mm = (elapsed % 3600) // 60
                ss = elapsed % 60
                uptime = f"{hh:02d}:{mm:02d}:{ss:02d}"

            try:
                resolved_script = str(resolve_script_path(cfg))
            except Exception:
                resolved_script = str(st.script_path or cfg.get("script_name", ""))

            rows.append(
                {
                    "id": loop_id,
                    "label": str(cfg.get("label", loop_id)),
                    "status": "RUNNING" if st.running else "STOPPED",
                    "pid": str(st.pid or ""),
                    "started_at": started_at,
                    "uptime": uptime,
                    "auto_restart": "ON" if st.auto_restart else "OFF",
                    "script_path": resolved_script,
                    "log_file": str(st.log_file or ""),
                }
            )
        return rows


# ============================================================
# EMBEDDED PANEL
# ============================================================

class LoopManagementPanel(tk.Frame):
    REFRESH_MS = 1500

    def __init__(self, parent, manager: Optional[LoopManager] = None):
        super().__init__(parent, bg="#0f0f10")
        self.manager = manager or LoopManager(LOOP_DEFINITIONS)
        self.selected_loop_id: Optional[str] = None
        self.compact_mode = tk.BooleanVar(value=True)
        self._refresh_job: Optional[str] = None

        self._setup_style()
        self._build_ui()
        self._refresh_table()
        self._schedule_refresh()

    def _setup_style(self) -> None:
        style = ttk.Style(self)
        try:
            style.theme_use("clam")
        except Exception:
            pass

        bg = "#0f0f10"
        panel = "#17181a"
        panel_2 = "#1d1f22"
        header = "#111214"
        border = "#33363a"
        text = "#f3f4f6"
        muted = "#a1a1aa"
        amber = "#ff9f1a"
        amber_soft = "#ffb84d"
        green = "#00c853"
        red = "#ff5252"
        blue = "#4da3ff"

        style.configure(".", background=bg, foreground=text, font=("Segoe UI", 9))
        style.configure("TFrame", background=bg)
        style.configure("Panel.TFrame", background=panel)
        style.configure("Panel2.TFrame", background=panel_2)
        style.configure("TLabel", background=bg, foreground=text, font=("Segoe UI", 9))
        style.configure("Panel.TLabel", background=panel, foreground=text, font=("Segoe UI", 9))
        style.configure("Muted.TLabel", background=bg, foreground=muted, font=("Segoe UI", 9))
        style.configure("Header.TLabel", background=bg, foreground=amber, font=("Segoe UI", 16, "bold"))
        style.configure("SubHeader.TLabel", background=bg, foreground=amber_soft, font=("Segoe UI", 9))
        style.configure("KPI.TLabel", background=panel, foreground=amber, font=("Segoe UI", 10, "bold"))

        style.configure(
            "Bloom.TButton",
            background=panel_2,
            foreground=text,
            bordercolor=border,
            lightcolor=panel_2,
            darkcolor=panel_2,
            padding=(10, 5),
            font=("Segoe UI", 9),
        )
        style.map(
            "Bloom.TButton",
            background=[("active", amber), ("pressed", amber)],
            foreground=[("active", "#000000"), ("pressed", "#000000")],
        )

        style.configure(
            "TCheckbutton",
            background=bg,
            foreground=text,
            font=("Segoe UI", 9),
        )
        style.map(
            "TCheckbutton",
            foreground=[("active", amber)],
            background=[("active", bg)],
        )

        style.configure(
            "TLabelframe",
            background=bg,
            bordercolor=border,
            relief="solid",
        )
        style.configure(
            "TLabelframe.Label",
            background=bg,
            foreground=amber,
            font=("Segoe UI", 9, "bold"),
        )

        style.configure(
            "Treeview",
            background=panel,
            fieldbackground=panel,
            foreground=text,
            bordercolor=border,
            rowheight=22,
            font=("Segoe UI", 9),
        )
        style.configure(
            "Treeview.Heading",
            background=header,
            foreground=amber,
            bordercolor=border,
            relief="flat",
            font=("Segoe UI", 9, "bold"),
            padding=(6, 5),
        )
        style.map(
            "Treeview",
            background=[("selected", "#3a2a10")],
            foreground=[("selected", amber_soft)],
        )

        self._colors = {
            "bg": bg,
            "panel": panel,
            "panel_2": panel_2,
            "header": header,
            "border": border,
            "text": text,
            "muted": muted,
            "amber": amber,
            "amber_soft": amber_soft,
            "green": green,
            "red": red,
            "blue": blue,
        }

    def _build_ui(self) -> None:
        root = ttk.Frame(self, padding=10)
        root.pack(fill="both", expand=True)

        header = ttk.Frame(root)
        header.pack(fill="x", pady=(0, 8))

        ttk.Label(header, text="LOOP MANAGEMENT BOARD", style="Header.TLabel").pack(side="left")
        ttk.Label(header, text="OPS / BLOOMBERG STYLE", style="SubHeader.TLabel").pack(side="left", padx=(10, 0))

        toolbar = ttk.Frame(header)
        toolbar.pack(side="right")

        ttk.Checkbutton(
            toolbar,
            text="Compact",
            variable=self.compact_mode,
            command=self._apply_compact_mode,
        ).pack(side="left", padx=(0, 8))

        ttk.Button(toolbar, text="Refresh", style="Bloom.TButton", command=self._refresh_table).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Start All", style="Bloom.TButton", command=self._start_all).pack(side="left", padx=3)
        ttk.Button(toolbar, text="Stop All", style="Bloom.TButton", command=self._stop_all).pack(side="left", padx=3)

        kpi_wrap = ttk.Frame(root, style="Panel.TFrame")
        kpi_wrap.pack(fill="x", pady=(0, 8))

        self.kpi_total = ttk.Label(kpi_wrap, text="TOTAL 0", style="KPI.TLabel")
        self.kpi_running = ttk.Label(kpi_wrap, text="RUNNING 0", style="KPI.TLabel")
        self.kpi_stopped = ttk.Label(kpi_wrap, text="STOPPED 0", style="KPI.TLabel")
        self.kpi_root = ttk.Label(kpi_wrap, text=shorten_path(str(FTMO_ROOT), 96), style="Panel.TLabel")

        self.kpi_total.pack(side="left", padx=(10, 18), pady=8)
        self.kpi_running.pack(side="left", padx=(0, 18), pady=8)
        self.kpi_stopped.pack(side="left", padx=(0, 18), pady=8)
        self.kpi_root.pack(side="right", padx=10, pady=8)

        body = ttk.Panedwindow(root, orient="vertical")
        body.pack(fill="both", expand=True)

        top = ttk.Frame(body)
        bottom = ttk.Frame(body)

        body.add(top, weight=5)
        body.add(bottom, weight=2)

        columns = ("label", "status", "pid", "uptime", "auto_restart")

        self.tree = ttk.Treeview(top, columns=columns, show="headings", height=16)
        self.tree.pack(side="left", fill="both", expand=True)
        self.tree.bind("<<TreeviewSelect>>", self._on_select)

        specs = [
            ("label", 270, "LOOP"),
            ("status", 110, "STATUS"),
            ("pid", 90, "PID"),
            ("uptime", 100, "UPTIME"),
            ("auto_restart", 120, "AUTO RST"),
        ]
        for col, width, title in specs:
            self.tree.heading(col, text=title)
            self.tree.column(col, width=width, anchor="w", stretch=(col == "label"))

        yscroll = ttk.Scrollbar(top, orient="vertical", command=self.tree.yview)
        yscroll.pack(side="right", fill="y")
        self.tree.configure(yscrollcommand=yscroll.set)

        detail_frame = ttk.LabelFrame(bottom, text="DETAILS", padding=8)
        detail_frame.pack(fill="both", expand=True)

        self.detail_text = tk.Text(
            detail_frame,
            height=8,
            wrap="word",
            relief="flat",
            borderwidth=0,
            font=("Consolas", 9),
            bg=self._colors["panel"],
            fg=self._colors["amber_soft"],
            insertbackground=self._colors["amber_soft"],
            selectbackground="#3a2a10",
            selectforeground=self._colors["amber_soft"],
        )
        self.detail_text.pack(fill="both", expand=True)

        action_row = ttk.Frame(bottom)
        action_row.pack(fill="x", pady=(8, 0))

        ttk.Button(action_row, text="Start", style="Bloom.TButton", command=self._start_selected).pack(side="left", padx=3)
        ttk.Button(action_row, text="Stop", style="Bloom.TButton", command=self._stop_selected).pack(side="left", padx=3)
        ttk.Button(action_row, text="Restart", style="Bloom.TButton", command=self._restart_selected).pack(side="left", padx=3)
        ttk.Button(action_row, text="Logs", style="Bloom.TButton", command=self._open_log_folder).pack(side="left", padx=3)

        self.auto_restart_var = tk.BooleanVar(value=False)
        ttk.Checkbutton(
            action_row,
            text="Auto Restart",
            variable=self.auto_restart_var,
            command=self._toggle_auto_restart_selected,
        ).pack(side="left", padx=12)

        self._apply_compact_mode()

    def _apply_compact_mode(self) -> None:
        style = ttk.Style(self)
        if self.compact_mode.get():
            style.configure("Treeview", rowheight=22, font=("Segoe UI", 9))
            style.configure("Treeview.Heading", font=("Segoe UI", 9, "bold"), padding=(6, 5))
        else:
            style.configure("Treeview", rowheight=28, font=("Segoe UI", 10))
            style.configure("Treeview.Heading", font=("Segoe UI", 10, "bold"), padding=(8, 7))

    def _schedule_refresh(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
        self._refresh_job = self.after(self.REFRESH_MS, self._periodic_refresh)

    def _periodic_refresh(self) -> None:
        self._refresh_table()
        self._schedule_refresh()

    def _refresh_kpis(self) -> None:
        s = self.manager.get_summary()
        self.kpi_total.config(text=f"TOTAL {s['total']}")
        self.kpi_running.config(text=f"RUNNING {s['running']}")
        self.kpi_stopped.config(text=f"STOPPED {s['stopped']}")

    def _refresh_table(self) -> None:
        self._refresh_kpis()

        rows = self.manager.get_rows()
        current_selection = self.selected_loop_id
        self.tree.delete(*self.tree.get_children())

        for row in rows:
            status = row["status"]
            tags = ("running",) if status == "RUNNING" else ("stopped",)

            self.tree.insert(
                "",
                "end",
                iid=row["id"],
                values=(
                    row["label"],
                    row["status"],
                    row["pid"],
                    row["uptime"],
                    row["auto_restart"],
                ),
                tags=tags,
            )

        self.tree.tag_configure("running", foreground=self._colors["green"])
        self.tree.tag_configure("stopped", foreground=self._colors["red"])

        if current_selection and current_selection in self.tree.get_children():
            self.tree.selection_set(current_selection)
            self.tree.focus(current_selection)
            self._render_details(current_selection)

    def _on_select(self, _event=None) -> None:
        selected = self.tree.selection()
        if not selected:
            self.selected_loop_id = None
            return
        self.selected_loop_id = selected[0]
        self._render_details(self.selected_loop_id)

    def _render_details(self, loop_id: str) -> None:
        cfg = self.manager.loop_definitions[loop_id]
        st = self.manager.state[loop_id]

        self.auto_restart_var.set(bool(st.auto_restart))

        try:
            resolved_script = resolve_script_path(cfg)
        except Exception:
            resolved_script = Path(str(st.script_path or cfg.get("script_name", "")))

        cwd = cfg.get("cwd", "") or resolved_script.parent

        lines = [
            f"LOOP_ID      : {loop_id}",
            f"LABEL        : {cfg.get('label', '')}",
            f"STATUS       : {'RUNNING' if st.running else 'STOPPED'}",
            f"PID          : {st.pid}",
            f"AUTO_RESTART : {st.auto_restart}",
            f"STARTED_AT   : {st.started_at_epoch}",
            f"LAST_EXIT    : {st.last_exit_code}",
            "",
            f"SCRIPT_PATH  : {resolved_script}",
            f"CWD          : {cwd}",
            f"LOG_FILE     : {st.log_file or ''}",
            f"ENV          : {cfg.get('env', {})}",
        ]

        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", "\n".join(lines))

    def _run_action(self, action, success_msg: Optional[str] = None) -> None:
        def worker():
            try:
                action()
                self.after(0, self._refresh_table)
                if success_msg:
                    self.after(0, lambda: self._set_detail_message(success_msg))
            except Exception as e:
                err_msg = str(e)
                self.after(0, lambda msg=err_msg: messagebox.showerror("Fehler", msg))

        threading.Thread(target=worker, daemon=True).start()

    def _set_detail_message(self, msg: str) -> None:
        self.detail_text.delete("1.0", "end")
        self.detail_text.insert("1.0", msg)

    def _require_selection(self) -> str:
        if not self.selected_loop_id:
            raise RuntimeError("Kein Loop ausgewählt")
        return self.selected_loop_id

    def _start_selected(self) -> None:
        loop_id = self._require_selection()
        self._run_action(lambda: self.manager.start_loop(loop_id), f"GESTARTET: {loop_id}")

    def _stop_selected(self) -> None:
        loop_id = self._require_selection()
        self._run_action(lambda: self.manager.stop_loop(loop_id), f"GESTOPPT: {loop_id}")

    def _restart_selected(self) -> None:
        loop_id = self._require_selection()
        self._run_action(lambda: self.manager.restart_loop(loop_id), f"NEU GESTARTET: {loop_id}")

    def _toggle_auto_restart_selected(self) -> None:
        loop_id = self._require_selection()
        value = self.auto_restart_var.get()
        self.manager.set_auto_restart(loop_id, value)
        self._refresh_table()
        self._render_details(loop_id)

    def _start_all(self) -> None:
        self._run_action(self.manager.start_all, "ALLE LOOPS GESTARTET")

    def _stop_all(self) -> None:
        self._run_action(self.manager.stop_all, "ALLE LOOPS GESTOPPT")

    def _open_log_folder(self) -> None:
        ensure_dir(LOG_DIR)
        try:
            os.startfile(str(LOG_DIR))  # type: ignore[attr-defined]
        except Exception as e:
            messagebox.showerror("Fehler", f"Log-Folder konnte nicht geöffnet werden: {e}")

    def destroy(self) -> None:
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None
        super().destroy()


# ============================================================
# STANDALONE APP WRAPPER
# ============================================================

class LoopManagementBoardApp(tk.Tk):
    def __init__(self, manager: Optional[LoopManager] = None):
        super().__init__()
        self.title("Loop Management Board")
        self.geometry("1160x650")
        self.minsize(980, 540)
        self.configure(bg="#0f0f10")

        self.panel = LoopManagementPanel(self, manager=manager)
        self.panel.pack(fill="both", expand=True)

    def destroy(self) -> None:
        try:
            self.panel.destroy()
        except Exception:
            pass
        super().destroy()


# ============================================================
# MAIN
# ============================================================

def validate_loop_definitions() -> None:
    seen = set()
    for cfg in LOOP_DEFINITIONS:
        loop_id = str(cfg["id"])
        if loop_id in seen:
            raise RuntimeError(f"Doppelte loop id: {loop_id}")
        seen.add(loop_id)

        try:
            script_path = resolve_script_path(cfg)
            print(f"[OK] {loop_id} -> {script_path}")
        except Exception as e:
            print(f"[WARN] Script existiert noch nicht / nicht gefunden: {loop_id} | {e}")


def main() -> None:
    ensure_dir(RUNTIME_DIR)
    ensure_dir(LOG_DIR)
    validate_loop_definitions()

    manager = LoopManager(LOOP_DEFINITIONS)
    app = LoopManagementBoardApp(manager=manager)
    app.mainloop()


if __name__ == "__main__":
    main()