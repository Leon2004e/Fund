# -*- coding: utf-8 -*-
"""
Dashboards/Strategy/strategy_dashboard.py

Strategy Dashboard
- standalone nutzbar
- auch als eingebettetes Panel nutzbar
- liest Strategy_Profile JSON-Dateien
- dunkler Corporate-Stil
- Filter, KPI, Summary, Pivot, Chart, Detailfenster
- Excel-artigere Tabellenarbeit:
    - Sortieren per Spaltenkopf
    - Filterzeile direkt über der Tabelle

Wichtig:
- Für Standalone:
    python Quant_Structure/FTMO/Dashboards/Strategy/strategy_dashboard.py

- Für Integration ins Main Dashboard:
    from strategy_dashboard import (
        StrategyDashboardPanel,
        StrategyProfileRepository,
        STRATEGY_PROFILE_ROOT,
    )
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Dict, List, Optional

import tkinter as tk
from tkinter import ttk

import pandas as pd
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure


# ============================================================
# PATHS
# ============================================================

def find_ftmo_root(start: Path) -> Path:
    cur = start.resolve()
    for p in [cur] + list(cur.parents):
        if (p / "Data_Center").exists() and (p / "Dashboards").exists():
            return p
    raise RuntimeError(
        f"FTMO-Root nicht gefunden. Erwartet Root mit "
        f"'Data_Center' und 'Dashboards'. Start={start}"
    )


SCRIPT_PATH = Path(__file__).resolve()
FTMO_ROOT = find_ftmo_root(SCRIPT_PATH)

STRATEGY_PROFILE_ROOT = (
    FTMO_ROOT
    / "Data_Center"
    / "Data"
    / "Strategy"
    / "Strategy_Profile"
)


# ============================================================
# CONFIG
# ============================================================

APP_TITLE = "Strategy Dashboard"
AUTO_REFRESH_MS = 5000
AUTO_REFRESH_DEFAULT = True
TABLE_ROW_LIMIT = 5000
SUMMARY_ROW_LIMIT = 500
PIVOT_ROW_LIMIT = 500
CHART_MAX_SYMBOLS = 12


# ============================================================
# STYLE
# ============================================================

BG_MAIN = "#0A0C10"
BG_PANEL = "#11151B"
BG_PANEL_2 = "#151A21"
BG_HEADER = "#171C24"
BG_CARD = "#11151B"
BG_BUTTON = "#1A2029"

FG_MAIN = "#E6EAF0"
FG_MUTED = "#9BA6B2"
FG_POS = "#26D07C"
FG_NEG = "#FF5A67"
FG_WARN = "#FFC857"

BORDER = "#232A34"

FONT_TITLE = ("Segoe UI", 17, "bold")
FONT_SECTION = ("Segoe UI", 11, "bold")
FONT_LABEL = ("Segoe UI", 9)
FONT_VALUE = ("Segoe UI", 12, "bold")
FONT_TEXT = ("Segoe UI", 9)
FONT_MONO = ("Consolas", 10)

CHART_COLORS = {
    "BUY": "#26D07C",
    "SELL": "#FF5A67",
    "BOTH": "#9BA6B2",
    "UNKNOWN": "#6C7683",
}


# ============================================================
# HELPERS
# ============================================================

def safe_text(x: object) -> str:
    if x is None:
        return ""
    try:
        if pd.isna(x):
            return ""
    except Exception:
        pass
    return str(x).strip()


def fmt_int(x) -> str:
    try:
        return f"{int(x):,}"
    except Exception:
        return "-"


def unique_sorted(values: List[str], with_all: bool = True) -> List[str]:
    cleaned = sorted({safe_text(v) for v in values if safe_text(v)})
    return (["ALL"] + cleaned) if with_all else cleaned


def get_nested(d: Dict[str, Any], path: str, default=None):
    cur = d
    for key in path.split("."):
        if not isinstance(cur, dict) or key not in cur:
            return default
        cur = cur[key]
    return cur


def as_bool_label(v: Any) -> str:
    if v is True:
        return "YES"
    if v is False:
        return "NO"
    return "UNKNOWN"


def safe_read_json(path: Path) -> Dict[str, Any]:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception:
        return {}


def make_tree_iid(prefix: str, row_index: int, key: str = "") -> str:
    clean_key = (
        safe_text(key)
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
        .replace(":", "_")
    )
    return f"{prefix}__{row_index}__{clean_key}"


# ============================================================
# REPOSITORY
# ============================================================

class StrategyProfileRepository:
    def __init__(self, root: Path):
        self.root = root

    def scan(self) -> pd.DataFrame:
        if not self.root.exists():
            return pd.DataFrame()

        rows: List[Dict[str, Any]] = []

        for json_path in sorted(self.root.rglob("*.json")):
            profile = safe_read_json(json_path)
            if not profile:
                continue

            identity = profile.get("identity", {})
            naming = profile.get("profile_naming", {})
            classification = profile.get("classification", {})
            risk_model = profile.get("risk_model", {})
            fixed = get_nested(profile, "trade_parameters.fixed", {})
            dynamic = get_nested(profile, "trade_parameters.dynamic_coef", {})
            mm = profile.get("money_management", {})
            filters = profile.get("filters", {})
            checks = profile.get("checks", {})
            signal_family = classification.get("signal_family", [])

            if isinstance(signal_family, list):
                signal_family_label = "_".join(
                    [safe_text(x) for x in signal_family if safe_text(x)]
                ) or "UNKNOWN"
            else:
                signal_family_label = safe_text(signal_family) or "UNKNOWN"

            symbol = safe_text(identity.get("symbol", "unknown")).upper() or "UNKNOWN"
            variant_number = identity.get("variant_number")
            strategy_id = safe_text(identity.get("strategy_id", "unknown")) or "UNKNOWN"
            side = safe_text(identity.get("side", "unknown")).upper() or "UNKNOWN"
            timeframe = safe_text(identity.get("timeframe", "unknown")).upper() or "UNKNOWN"

            profile_file = json_path.name
            profile_relative_path = str(json_path.relative_to(self.root))

            row = {
                "profile_file": profile_file,
                "profile_path": str(json_path.resolve()),
                "profile_relative_path": profile_relative_path,
                "symbol_folder": json_path.parent.name,

                "schema_version": safe_text(profile.get("schema_version")),
                "ea_file": safe_text(get_nested(profile, "source.ea_file")),
                "ea_path": safe_text(get_nested(profile, "source.ea_path")),

                "symbol": symbol,
                "variant_number": variant_number,
                "strategy_id": strategy_id,
                "side": side,
                "timeframe": timeframe,

                "base_name": safe_text(naming.get("base_name")),
                "exit_label": safe_text(naming.get("exit_label")),
                "signal_label": safe_text(naming.get("signal_label")),
                "time_label": safe_text(naming.get("time_label")),
                "display_name": safe_text(naming.get("display_name")),
                "extended_display_name": safe_text(naming.get("extended_display_name")),

                "sl_type": safe_text(classification.get("sl_type")),
                "tp_type": safe_text(classification.get("tp_type")),
                "trailing_type": safe_text(classification.get("trailing_type")),
                "exit_profile": safe_text(classification.get("exit_profile")),
                "signal_family": signal_family_label,
                "overlap_key": safe_text(classification.get("overlap_key")),

                "risk_model_type": safe_text(risk_model.get("type")),
                "fixed_sl": fixed.get("stop_loss_pips"),
                "fixed_tp": fixed.get("take_profit_pips"),
                "sl_coef": dynamic.get("stop_loss_coef"),
                "tp_coef": dynamic.get("take_profit_coef"),
                "trailing_coef": dynamic.get("trailing_stop_coef"),

                "mm_enabled": as_bool_label(mm.get("enabled")),
                "risk_percent": mm.get("risk_percent"),
                "fixed_lot": mm.get("fixed_lot"),
                "initial_capital": mm.get("initial_capital"),

                "limit_time_range": as_bool_label(get_nested(filters, "limit_time_range.enabled")),
                "time_from": safe_text(get_nested(filters, "limit_time_range.from")),
                "time_to": safe_text(get_nested(filters, "limit_time_range.to")),
                "eod_exit": as_bool_label(get_nested(filters, "exit_at_end_of_day.enabled")),
                "friday_exit": as_bool_label(get_nested(filters, "exit_on_friday.enabled")),
                "weekend_protection": as_bool_label(get_nested(filters, "dont_trade_on_weekends.enabled")),
                "max_trades_per_day": filters.get("max_trades_per_day"),

                "has_defined_stop_loss": as_bool_label(checks.get("has_defined_stop_loss")),
                "has_defined_take_profit_or_exit": as_bool_label(checks.get("has_defined_take_profit_or_exit")),
                "uses_aggressive_mm": as_bool_label(checks.get("uses_aggressive_mm")),
                "has_parser_uncertainty": as_bool_label(checks.get("has_parser_uncertainty")),
                "has_tight_stop": as_bool_label(checks.get("has_tight_stop")),
            }

            row["strategy_uid"] = (
                f"{symbol}__{variant_number}__{strategy_id}__{side}__{timeframe}"
            )
            row["row_key"] = f"{profile_relative_path}__{profile_file}"

            rows.append(row)

        if not rows:
            return pd.DataFrame()

        df = pd.DataFrame(rows)
        df["variant_sort"] = pd.to_numeric(df["variant_number"], errors="coerce")
        df["risk_percent_sort"] = pd.to_numeric(df["risk_percent"], errors="coerce")
        df["fixed_sl_sort"] = pd.to_numeric(df["fixed_sl"], errors="coerce")
        df["fixed_tp_sort"] = pd.to_numeric(df["fixed_tp"], errors="coerce")

        df = df.sort_values(
            by=["symbol", "variant_sort", "strategy_id", "side", "timeframe", "profile_file"],
            na_position="last",
        ).reset_index(drop=True)

        return df


# ============================================================
# AGGREGATIONS
# ============================================================

def build_symbol_summary(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["symbol", "count", "buy", "sell", "both", "timeframes"])

    out = (
        df.groupby("symbol", dropna=False)
        .agg(
            count=("row_key", "size"),
            buy=("side", lambda s: int((s == "BUY").sum())),
            sell=("side", lambda s: int((s == "SELL").sum())),
            both=("side", lambda s: int((s == "BOTH").sum())),
            timeframes=("timeframe", lambda s: ", ".join(sorted({str(x) for x in s if str(x).strip()}))),
        )
        .reset_index()
        .sort_values(["count", "symbol"], ascending=[False, True])
        .reset_index(drop=True)
    )
    return out


def build_symbol_side_pivot(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        return pd.DataFrame(columns=["symbol", "BUY", "SELL", "BOTH", "UNKNOWN", "TOTAL"])

    work = df.copy()
    work["side_norm"] = work["side"].where(
        work["side"].isin(["BUY", "SELL", "BOTH"]),
        "UNKNOWN",
    )

    pivot = pd.pivot_table(
        work,
        index="symbol",
        columns="side_norm",
        values="row_key",
        aggfunc="count",
        fill_value=0,
    )

    for col in ["BUY", "SELL", "BOTH", "UNKNOWN"]:
        if col not in pivot.columns:
            pivot[col] = 0

    pivot = pivot[["BUY", "SELL", "BOTH", "UNKNOWN"]].copy()
    pivot["TOTAL"] = pivot.sum(axis=1)
    pivot = pivot.sort_values(["TOTAL", "symbol"], ascending=[False, True]).reset_index()
    return pivot


# ============================================================
# UI WIDGETS
# ============================================================

class KpiCard(tk.Frame):
    def __init__(self, parent, title: str):
        super().__init__(parent, bg=BG_CARD, highlightbackground=BORDER, highlightthickness=1)
        self.configure(height=72)
        self.pack_propagate(False)

        tk.Label(
            self,
            text=title,
            font=FONT_LABEL,
            bg=BG_CARD,
            fg=FG_MUTED,
        ).pack(anchor="w", padx=10, pady=(8, 2))

        self.value_var = tk.StringVar(value="-")
        self.value_label = tk.Label(
            self,
            textvariable=self.value_var,
            font=FONT_VALUE,
            bg=BG_CARD,
            fg=FG_MAIN,
        )
        self.value_label.pack(anchor="w", padx=10)

    def set_value(self, value: str, color: Optional[str] = None):
        self.value_var.set(value)
        self.value_label.configure(fg=color or FG_MAIN)


# ============================================================
# PANEL
# ============================================================

class StrategyDashboardPanel(tk.Frame):
    def __init__(self, parent, repo: StrategyProfileRepository):
        super().__init__(parent, bg=BG_MAIN)

        self.repo = repo

        self.raw_df = pd.DataFrame()
        self.filtered_df = pd.DataFrame()
        self.summary_df = pd.DataFrame()
        self.pivot_df = pd.DataFrame()

        self.auto_refresh_enabled = tk.BooleanVar(value=AUTO_REFRESH_DEFAULT)
        self._refresh_job: Optional[str] = None
        self.last_refresh_ts: Optional[pd.Timestamp] = None

        self.search_var = tk.StringVar(value="")
        self.symbol_var = tk.StringVar(value="ALL")
        self.side_var = tk.StringVar(value="ALL")
        self.timeframe_var = tk.StringVar(value="ALL")
        self.exit_profile_var = tk.StringVar(value="ALL")
        self.signal_family_var = tk.StringVar(value="ALL")
        self.risk_model_var = tk.StringVar(value="ALL")

        self.col_filter_symbol = tk.StringVar(value="")
        self.col_filter_variant = tk.StringVar(value="")
        self.col_filter_strategy_id = tk.StringVar(value="")
        self.col_filter_side = tk.StringVar(value="")
        self.col_filter_timeframe = tk.StringVar(value="")
        self.col_filter_exit = tk.StringVar(value="")

        self._sort_state: Dict[str, bool] = {}

        self.figure: Optional[Figure] = None
        self.ax = None
        self.chart_canvas: Optional[FigureCanvasTkAgg] = None

        self._configure_ttk_style()
        self._build_ui()
        self._refresh_all(live=False)
        self._schedule_auto_refresh()

    # ========================================================
    # STYLE
    # ========================================================

    def _configure_ttk_style(self):
        style = ttk.Style(self)

        try:
            style.theme_use("clam")
        except Exception:
            pass

        style.configure(
            "TNotebook",
            background=BG_PANEL,
            borderwidth=0,
        )
        style.configure(
            "TNotebook.Tab",
            background=BG_PANEL_2,
            foreground=FG_MAIN,
            padding=(10, 5),
            borderwidth=0,
        )
        style.map(
            "TNotebook.Tab",
            background=[("selected", BG_HEADER)],
            foreground=[("selected", FG_MAIN)],
        )

        style.configure(
            "Treeview",
            background="#F4F6F8",
            fieldbackground="#F4F6F8",
            foreground="#111111",
            rowheight=24,
            bordercolor=BORDER,
            borderwidth=0,
            font=FONT_TEXT,
        )
        style.configure(
            "Treeview.Heading",
            background="#E8ECEF",
            foreground="#111111",
            relief="flat",
            font=("Segoe UI", 9, "bold"),
        )
        style.map(
            "Treeview",
            background=[("selected", "#D6E4F0")],
            foreground=[("selected", "#111111")],
        )
        style.map(
            "Treeview.Heading",
            background=[("active", "#DDE3E8")],
        )

        style.configure(
            "TCombobox",
            fieldbackground="#FFFFFF",
            background="#FFFFFF",
            foreground="#111111",
            arrowsize=14,
        )

    # ========================================================
    # BUILD UI
    # ========================================================

    def _build_ui(self):
        root = tk.Frame(self, bg=BG_MAIN)
        root.pack(fill="both", expand=True, padx=12, pady=12)

        topbar = tk.Frame(root, bg=BG_HEADER, height=54, highlightbackground=BORDER, highlightthickness=1)
        topbar.pack(fill="x", pady=(0, 12))
        topbar.pack_propagate(False)

        tk.Label(
            topbar,
            text="STRATEGY DASHBOARD",
            font=FONT_TITLE,
            bg=BG_HEADER,
            fg=FG_MAIN,
        ).pack(side="left", padx=14)

        self.live_status_var = tk.StringVar(value="READY")
        tk.Label(
            topbar,
            textvariable=self.live_status_var,
            font=("Segoe UI", 9),
            bg=BG_HEADER,
            fg=FG_MUTED,
        ).pack(side="right", padx=(0, 14))

        self.info_var = tk.StringVar(value=str(STRATEGY_PROFILE_ROOT))
        tk.Label(
            topbar,
            textvariable=self.info_var,
            font=("Segoe UI", 9),
            bg=BG_HEADER,
            fg=FG_MUTED,
        ).pack(side="right", padx=14)

        controls = tk.Frame(root, bg=BG_MAIN)
        controls.pack(fill="x", pady=(0, 12))

        tk.Label(controls, text="Search", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        search_entry = tk.Entry(
            controls,
            textvariable=self.search_var,
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            width=24,
        )
        search_entry.pack(side="left", padx=(0, 10), ipady=5)
        search_entry.bind("<KeyRelease>", self._on_filter_change)

        tk.Label(controls, text="Symbol", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.symbol_combo = ttk.Combobox(controls, state="readonly", width=12, textvariable=self.symbol_var)
        self.symbol_combo.pack(side="left", padx=(0, 10))
        self.symbol_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(controls, text="Side", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.side_combo = ttk.Combobox(controls, state="readonly", width=10, textvariable=self.side_var)
        self.side_combo.pack(side="left", padx=(0, 10))
        self.side_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(controls, text="TF", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.timeframe_combo = ttk.Combobox(controls, state="readonly", width=10, textvariable=self.timeframe_var)
        self.timeframe_combo.pack(side="left", padx=(0, 10))
        self.timeframe_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(controls, text="Exit", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.exit_profile_combo = ttk.Combobox(controls, state="readonly", width=24, textvariable=self.exit_profile_var)
        self.exit_profile_combo.pack(side="left", padx=(0, 10))
        self.exit_profile_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(controls, text="Signal", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.signal_family_combo = ttk.Combobox(controls, state="readonly", width=16, textvariable=self.signal_family_var)
        self.signal_family_combo.pack(side="left", padx=(0, 10))
        self.signal_family_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Label(controls, text="Risk", bg=BG_MAIN, fg=FG_MUTED, font=FONT_LABEL).pack(side="left", padx=(0, 6))
        self.risk_model_combo = ttk.Combobox(controls, state="readonly", width=16, textvariable=self.risk_model_var)
        self.risk_model_combo.pack(side="left", padx=(0, 10))
        self.risk_model_combo.bind("<<ComboboxSelected>>", self._on_filter_change)

        tk.Button(
            controls,
            text="Refresh",
            command=lambda: self._refresh_all(live=False),
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_PANEL_2,
            activeforeground=FG_MAIN,
            relief="flat",
            padx=12,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 10))

        tk.Button(
            controls,
            text="Clear Column Filters",
            command=self._clear_column_filters,
            bg=BG_BUTTON,
            fg=FG_MAIN,
            activebackground=BG_PANEL_2,
            activeforeground=FG_MAIN,
            relief="flat",
            padx=12,
            pady=6,
            bd=0,
        ).pack(side="left", padx=(0, 10))

        tk.Checkbutton(
            controls,
            text="Auto Refresh",
            variable=self.auto_refresh_enabled,
            command=self._on_toggle_auto_refresh,
            bg=BG_MAIN,
            fg=FG_MAIN,
            activebackground=BG_MAIN,
            activeforeground=FG_MAIN,
            selectcolor=BG_PANEL_2,
            relief="flat",
        ).pack(side="left")

        kpi_row = tk.Frame(root, bg=BG_MAIN)
        kpi_row.pack(fill="x", pady=(0, 12))

        self.card_total = KpiCard(kpi_row, "Total Strategies")
        self.card_total.pack(side="left", fill="x", expand=True, padx=4)

        self.card_symbols = KpiCard(kpi_row, "Symbols")
        self.card_symbols.pack(side="left", fill="x", expand=True, padx=4)

        self.card_aggr = KpiCard(kpi_row, "Aggressive MM")
        self.card_aggr.pack(side="left", fill="x", expand=True, padx=4)

        self.card_uncertain = KpiCard(kpi_row, "Parser Uncertainty")
        self.card_uncertain.pack(side="left", fill="x", expand=True, padx=4)

        self.card_stops = KpiCard(kpi_row, "Defined Stop Loss")
        self.card_stops.pack(side="left", fill="x", expand=True, padx=4)

        self.card_selected = KpiCard(kpi_row, "Filtered Rows")
        self.card_selected.pack(side="left", fill="x", expand=True, padx=4)

        main = tk.PanedWindow(root, orient="horizontal", bg=BG_MAIN, sashwidth=6)
        main.pack(fill="both", expand=True)

        left = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        right = tk.Frame(main, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)

        main.add(left, minsize=430)
        main.add(right, minsize=1100)

        self._build_left_panel(left)
        self._build_right_panel(right)

    def _build_left_panel(self, parent: tk.Frame):
        tk.Label(
            parent,
            text="Symbol Summary",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(10, 8))

        cols = ("symbol", "count", "buy", "sell", "both", "timeframes")
        self.summary_tree = ttk.Treeview(parent, columns=cols, show="headings", height=14)
        self.summary_tree.pack(fill="both", expand=True, padx=10, pady=(0, 10))
        self.summary_tree.bind("<<TreeviewSelect>>", self._on_summary_select)

        widths = {"symbol": 110, "count": 70, "buy": 60, "sell": 60, "both": 60, "timeframes": 130}
        for col in cols:
            self.summary_tree.heading(col, text=col)
            self.summary_tree.column(col, width=widths[col], anchor="w")

        info_box = tk.Frame(parent, bg=BG_PANEL_2, highlightbackground=BORDER, highlightthickness=1)
        info_box.pack(fill="both", expand=False, padx=10, pady=(0, 10))

        tk.Label(
            info_box,
            text="Selection Info",
            font=FONT_SECTION,
            bg=BG_PANEL_2,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(8, 6))

        self.selection_text = tk.Text(
            info_box,
            height=14,
            wrap="word",
            bg=BG_PANEL_2,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_TEXT,
        )
        self.selection_text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

    def _build_right_panel(self, parent: tk.Frame):
        notebook = ttk.Notebook(parent)
        notebook.pack(fill="both", expand=True, padx=10, pady=10)

        tab_table = tk.Frame(notebook, bg=BG_PANEL)
        tab_pivot = tk.Frame(notebook, bg=BG_PANEL)

        notebook.add(tab_table, text="Strategy Table")
        notebook.add(tab_pivot, text="Pivot + Chart")

        self._build_table_tab(tab_table)
        self._build_pivot_tab(tab_pivot)

    def _build_table_tab(self, parent: tk.Frame):
        tk.Label(
            parent,
            text="Strategy Profile Table",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(10, 8))

        filter_bar = tk.Frame(parent, bg=BG_PANEL)
        filter_bar.pack(fill="x", padx=10, pady=(0, 8))

        def make_filter_entry(parent_, label, var, width):
            box = tk.Frame(parent_, bg=BG_PANEL)
            box.pack(side="left", padx=(0, 8))
            tk.Label(box, text=label, bg=BG_PANEL, fg=FG_MUTED, font=FONT_LABEL).pack(anchor="w")
            e = tk.Entry(
                box,
                textvariable=var,
                bg=BG_PANEL_2,
                fg=FG_MAIN,
                insertbackground=FG_MAIN,
                relief="flat",
                width=width,
            )
            e.pack(ipady=4)
            e.bind("<KeyRelease>", self._on_filter_change)

        make_filter_entry(filter_bar, "symbol", self.col_filter_symbol, 10)
        make_filter_entry(filter_bar, "variant", self.col_filter_variant, 10)
        make_filter_entry(filter_bar, "strategy_id", self.col_filter_strategy_id, 12)
        make_filter_entry(filter_bar, "side", self.col_filter_side, 8)
        make_filter_entry(filter_bar, "timeframe", self.col_filter_timeframe, 10)
        make_filter_entry(filter_bar, "exit_profile", self.col_filter_exit, 18)

        table_shell = tk.Frame(parent, bg=BG_PANEL)
        table_shell.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        cols = (
            "symbol",
            "variant_number",
            "strategy_id",
            "side",
            "timeframe",
            "exit_profile",
            "signal_family",
            "risk_model_type",
            "risk_percent",
            "fixed_sl",
            "fixed_tp",
            "time_label",
            "display_name",
        )

        self.table = ttk.Treeview(table_shell, columns=cols, show="headings", height=24)
        self.table.pack(side="left", fill="both", expand=True)
        self.table.bind("<Double-1>", self._on_row_double_click)

        scrollbar_y = ttk.Scrollbar(table_shell, orient="vertical", command=self.table.yview)
        scrollbar_y.pack(side="right", fill="y")
        self.table.configure(yscrollcommand=scrollbar_y.set)

        widths = {
            "symbol": 90,
            "variant_number": 80,
            "strategy_id": 100,
            "side": 80,
            "timeframe": 80,
            "exit_profile": 190,
            "signal_family": 130,
            "risk_model_type": 130,
            "risk_percent": 90,
            "fixed_sl": 80,
            "fixed_tp": 80,
            "time_label": 120,
            "display_name": 360,
        }

        for col in cols:
            self.table.heading(
                col,
                text=col,
                command=lambda c=col: self._sort_main_table_by(c),
            )
            self.table.column(col, width=widths[col], anchor="w")

    def _build_pivot_tab(self, parent: tk.Frame):
        top = tk.Frame(parent, bg=BG_PANEL)
        top.pack(fill="both", expand=True)

        pivot_frame = tk.Frame(top, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        pivot_frame.pack(fill="x", padx=10, pady=(10, 10))

        tk.Label(
            pivot_frame,
            text="Pivot Table | Symbol x Side",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(10, 8))

        pivot_shell = tk.Frame(pivot_frame, bg=BG_PANEL)
        pivot_shell.pack(fill="x", padx=10, pady=(0, 10))

        cols = ("symbol", "BUY", "SELL", "BOTH", "UNKNOWN", "TOTAL")
        self.pivot_tree = ttk.Treeview(pivot_shell, columns=cols, show="headings", height=10)
        self.pivot_tree.pack(side="left", fill="x", expand=True)
        self.pivot_tree.bind("<<TreeviewSelect>>", self._on_pivot_select)

        pivot_scroll = ttk.Scrollbar(pivot_shell, orient="vertical", command=self.pivot_tree.yview)
        pivot_scroll.pack(side="right", fill="y")
        self.pivot_tree.configure(yscrollcommand=pivot_scroll.set)

        widths = {"symbol": 110, "BUY": 70, "SELL": 70, "BOTH": 70, "UNKNOWN": 80, "TOTAL": 70}
        for col in cols:
            self.pivot_tree.heading(col, text=col)
            self.pivot_tree.column(col, width=widths[col], anchor="center" if col != "symbol" else "w")

        chart_frame = tk.Frame(top, bg=BG_PANEL_2, highlightbackground=BORDER, highlightthickness=1)
        chart_frame.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(
            chart_frame,
            text="Chart | Strategies per Symbol",
            font=FONT_SECTION,
            bg=BG_PANEL_2,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(10, 8))

        self.figure = Figure(figsize=(10, 5), dpi=100, facecolor=BG_PANEL_2)
        self.ax = self.figure.add_subplot(111)
        self.chart_canvas = FigureCanvasTkAgg(self.figure, master=chart_frame)
        self.chart_canvas.draw()
        self.chart_canvas.get_tk_widget().pack(fill="both", expand=True, padx=10, pady=(0, 10))

    # ========================================================
    # DATA FLOW
    # ========================================================

    def _refresh_all(self, live: bool = False):
        try:
            self.raw_df = self.repo.scan()
            self._reload_filter_options()
            self._apply_filters()

            self.last_refresh_ts = pd.Timestamp.now(tz="UTC")
            mode = "LIVE" if live else "MANUAL"
            self.live_status_var.set(
                f"{mode} | last refresh {self.last_refresh_ts.strftime('%Y-%m-%d %H:%M:%S UTC')}"
            )
        except Exception as e:
            self.live_status_var.set(f"ERROR | {e}")

    def _reload_filter_options(self):
        df = self.raw_df.copy()

        symbols = unique_sorted(df["symbol"].astype(str).tolist()) if not df.empty and "symbol" in df.columns else ["ALL"]
        sides = unique_sorted(df["side"].astype(str).tolist()) if not df.empty and "side" in df.columns else ["ALL"]
        timeframes = unique_sorted(df["timeframe"].astype(str).tolist()) if not df.empty and "timeframe" in df.columns else ["ALL"]
        exits = unique_sorted(df["exit_profile"].astype(str).tolist()) if not df.empty and "exit_profile" in df.columns else ["ALL"]
        signals = unique_sorted(df["signal_family"].astype(str).tolist()) if not df.empty and "signal_family" in df.columns else ["ALL"]
        risks = unique_sorted(df["risk_model_type"].astype(str).tolist()) if not df.empty and "risk_model_type" in df.columns else ["ALL"]

        def keep_or_all(var: tk.StringVar, values: List[str]):
            cur = var.get() or "ALL"
            var.set(cur if cur in values else "ALL")

        self.symbol_combo["values"] = symbols
        self.side_combo["values"] = sides
        self.timeframe_combo["values"] = timeframes
        self.exit_profile_combo["values"] = exits
        self.signal_family_combo["values"] = signals
        self.risk_model_combo["values"] = risks

        keep_or_all(self.symbol_var, symbols)
        keep_or_all(self.side_var, sides)
        keep_or_all(self.timeframe_var, timeframes)
        keep_or_all(self.exit_profile_var, exits)
        keep_or_all(self.signal_family_var, signals)
        keep_or_all(self.risk_model_var, risks)

    def _apply_filters(self):
        df = self.raw_df.copy()

        if not df.empty:
            search = safe_text(self.search_var.get()).lower()
            symbol = safe_text(self.symbol_var.get())
            side = safe_text(self.side_var.get())
            timeframe = safe_text(self.timeframe_var.get())
            exit_profile = safe_text(self.exit_profile_var.get())
            signal_family = safe_text(self.signal_family_var.get())
            risk_model = safe_text(self.risk_model_var.get())

            if symbol and symbol != "ALL":
                df = df[df["symbol"] == symbol].copy()
            if side and side != "ALL":
                df = df[df["side"] == side].copy()
            if timeframe and timeframe != "ALL":
                df = df[df["timeframe"] == timeframe].copy()
            if exit_profile and exit_profile != "ALL":
                df = df[df["exit_profile"] == exit_profile].copy()
            if signal_family and signal_family != "ALL":
                df = df[df["signal_family"] == signal_family].copy()
            if risk_model and risk_model != "ALL":
                df = df[df["risk_model_type"] == risk_model].copy()

            if search:
                mask = pd.Series(False, index=df.index)
                for col in [
                    "symbol",
                    "strategy_id",
                    "side",
                    "timeframe",
                    "exit_profile",
                    "signal_family",
                    "risk_model_type",
                    "display_name",
                    "extended_display_name",
                    "profile_file",
                ]:
                    if col in df.columns:
                        mask = mask | df[col].astype(str).str.lower().str.contains(search, na=False)
                df = df[mask].copy()

            col_symbol = safe_text(self.col_filter_symbol.get()).lower()
            col_variant = safe_text(self.col_filter_variant.get()).lower()
            col_strategy_id = safe_text(self.col_filter_strategy_id.get()).lower()
            col_side = safe_text(self.col_filter_side.get()).lower()
            col_timeframe = safe_text(self.col_filter_timeframe.get()).lower()
            col_exit = safe_text(self.col_filter_exit.get()).lower()

            if col_symbol:
                df = df[df["symbol"].astype(str).str.lower().str.contains(col_symbol, na=False)].copy()

            if col_variant:
                df = df[df["variant_number"].astype(str).str.lower().str.contains(col_variant, na=False)].copy()

            if col_strategy_id:
                df = df[df["strategy_id"].astype(str).str.lower().str.contains(col_strategy_id, na=False)].copy()

            if col_side:
                df = df[df["side"].astype(str).str.lower().str.contains(col_side, na=False)].copy()

            if col_timeframe:
                df = df[df["timeframe"].astype(str).str.lower().str.contains(col_timeframe, na=False)].copy()

            if col_exit:
                df = df[df["exit_profile"].astype(str).str.lower().str.contains(col_exit, na=False)].copy()

        self.filtered_df = df.reset_index(drop=True)
        self.summary_df = build_symbol_summary(self.filtered_df)
        self.pivot_df = build_symbol_side_pivot(self.filtered_df)

        self._update_kpis()
        self._load_summary_table()
        self._load_main_table()
        self._update_selection_info()
        self._load_pivot_table()
        self._render_pivot_chart()

    # ========================================================
    # KPI / TABLES
    # ========================================================

    def _update_kpis(self):
        raw = self.raw_df.copy()
        flt = self.filtered_df.copy()

        total = len(raw)
        symbols = raw["symbol"].nunique() if not raw.empty else 0
        aggressive = int((raw["uses_aggressive_mm"] == "YES").sum()) if not raw.empty else 0
        uncertain = int((raw["has_parser_uncertainty"] == "YES").sum()) if not raw.empty else 0
        stop_loss = int((raw["has_defined_stop_loss"] == "YES").sum()) if not raw.empty else 0
        filtered = len(flt)

        self.card_total.set_value(fmt_int(total))
        self.card_symbols.set_value(fmt_int(symbols))
        self.card_aggr.set_value(fmt_int(aggressive), color=FG_NEG if aggressive > 0 else FG_MAIN)
        self.card_uncertain.set_value(fmt_int(uncertain), color=FG_WARN if uncertain > 0 else FG_MAIN)
        self.card_stops.set_value(fmt_int(stop_loss), color=FG_POS if stop_loss > 0 else FG_MAIN)
        self.card_selected.set_value(fmt_int(filtered), color=FG_POS if filtered > 0 else FG_NEG)

    def _load_summary_table(self):
        self.summary_tree.delete(*self.summary_tree.get_children())
        if self.summary_df.empty:
            return

        for idx, row in self.summary_df.head(SUMMARY_ROW_LIMIT).iterrows():
            iid = make_tree_iid("summary", idx, safe_text(row.get("symbol")))
            self.summary_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("symbol", ""),
                    row.get("count", ""),
                    row.get("buy", ""),
                    row.get("sell", ""),
                    row.get("both", ""),
                    row.get("timeframes", ""),
                ),
            )

    def _load_pivot_table(self):
        self.pivot_tree.delete(*self.pivot_tree.get_children())
        if self.pivot_df.empty:
            return

        total_buy = int(self.pivot_df["BUY"].sum()) if "BUY" in self.pivot_df.columns else 0
        total_sell = int(self.pivot_df["SELL"].sum()) if "SELL" in self.pivot_df.columns else 0
        total_both = int(self.pivot_df["BOTH"].sum()) if "BOTH" in self.pivot_df.columns else 0
        total_unknown = int(self.pivot_df["UNKNOWN"].sum()) if "UNKNOWN" in self.pivot_df.columns else 0
        total_total = int(self.pivot_df["TOTAL"].sum()) if "TOTAL" in self.pivot_df.columns else 0

        for idx, row in self.pivot_df.head(PIVOT_ROW_LIMIT).iterrows():
            iid = make_tree_iid("pivot", idx, safe_text(row.get("symbol")))
            self.pivot_tree.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("symbol", ""),
                    row.get("BUY", 0),
                    row.get("SELL", 0),
                    row.get("BOTH", 0),
                    row.get("UNKNOWN", 0),
                    row.get("TOTAL", 0),
                ),
            )

        self.pivot_tree.insert(
            "",
            "end",
            iid="pivot__total",
            values=("Gesamtergebnis", total_buy, total_sell, total_both, total_unknown, total_total),
        )

    def _update_selection_info(self):
        self.selection_text.delete("1.0", "end")
        raw = self.raw_df.copy()
        flt = self.filtered_df.copy()

        duplicates = 0
        if not raw.empty and "strategy_uid" in raw.columns:
            duplicates = int(raw["strategy_uid"].duplicated().sum())

        lines = [
            f"Root                : {STRATEGY_PROFILE_ROOT}",
            f"Total Profiles      : {len(raw)}",
            f"Filtered Profiles   : {len(flt)}",
            f"Duplicate UID Rows  : {duplicates}",
            f"Selected Symbol     : {safe_text(self.symbol_var.get()) or 'ALL'}",
            f"Selected Side       : {safe_text(self.side_var.get()) or 'ALL'}",
            f"Selected Timeframe  : {safe_text(self.timeframe_var.get()) or 'ALL'}",
            f"Selected Exit       : {safe_text(self.exit_profile_var.get()) or 'ALL'}",
            f"Selected Signal     : {safe_text(self.signal_family_var.get()) or 'ALL'}",
            f"Selected Risk       : {safe_text(self.risk_model_var.get()) or 'ALL'}",
            f"Search              : {safe_text(self.search_var.get()) or '-'}",
            f"Column Symbol       : {safe_text(self.col_filter_symbol.get()) or '-'}",
            f"Column Variant      : {safe_text(self.col_filter_variant.get()) or '-'}",
            f"Column Strategy ID  : {safe_text(self.col_filter_strategy_id.get()) or '-'}",
            f"Column Side         : {safe_text(self.col_filter_side.get()) or '-'}",
            f"Column Timeframe    : {safe_text(self.col_filter_timeframe.get()) or '-'}",
            f"Column Exit         : {safe_text(self.col_filter_exit.get()) or '-'}",
            "",
        ]

        if flt.empty:
            lines.append("Keine Strategien im aktuellen Filter.")
        else:
            lines.extend([
                f"Symbols in Filter   : {flt['symbol'].nunique() if 'symbol' in flt.columns else 0}",
                f"Sides in Filter     : {flt['side'].nunique() if 'side' in flt.columns else 0}",
                f"Exit Profiles       : {flt['exit_profile'].nunique() if 'exit_profile' in flt.columns else 0}",
                f"Signal Families     : {flt['signal_family'].nunique() if 'signal_family' in flt.columns else 0}",
                "",
                "Top Symbols:",
            ])
            for sym, cnt in flt["symbol"].value_counts().head(10).items():
                lines.append(f"  {sym:<12} {cnt}")

        self.selection_text.insert("1.0", "\n".join(lines))

    def _load_main_table(self):
        self.table.delete(*self.table.get_children())
        df = self.filtered_df.copy()
        if df.empty:
            return

        for idx, row in df.head(TABLE_ROW_LIMIT).iterrows():
            iid = make_tree_iid("table", idx, safe_text(row.get("row_key")))
            self.table.insert(
                "",
                "end",
                iid=iid,
                values=(
                    row.get("symbol", ""),
                    row.get("variant_number", ""),
                    row.get("strategy_id", ""),
                    row.get("side", ""),
                    row.get("timeframe", ""),
                    row.get("exit_profile", ""),
                    row.get("signal_family", ""),
                    row.get("risk_model_type", ""),
                    row.get("risk_percent", ""),
                    row.get("fixed_sl", ""),
                    row.get("fixed_tp", ""),
                    row.get("time_label", ""),
                    row.get("display_name", ""),
                ),
            )

    def _sort_main_table_by(self, col: str):
        if self.filtered_df.empty or col not in self.filtered_df.columns:
            return

        ascending = self._sort_state.get(col, True)
        df = self.filtered_df.copy()

        try:
            numeric_series = pd.to_numeric(df[col], errors="coerce")
            if numeric_series.notna().any():
                df = df.assign(_sort_col=numeric_series).sort_values(
                    by="_sort_col",
                    ascending=ascending,
                    na_position="last",
                ).drop(columns=["_sort_col"])
            else:
                df = df.sort_values(
                    by=col,
                    ascending=ascending,
                    na_position="last",
                    key=lambda s: s.astype(str).str.lower(),
                )
        except Exception:
            df = df.sort_values(
                by=col,
                ascending=ascending,
                na_position="last",
            )

        self.filtered_df = df.reset_index(drop=True)
        self._sort_state[col] = not ascending
        self._load_main_table()

    def _clear_column_filters(self):
        self.col_filter_symbol.set("")
        self.col_filter_variant.set("")
        self.col_filter_strategy_id.set("")
        self.col_filter_side.set("")
        self.col_filter_timeframe.set("")
        self.col_filter_exit.set("")
        self._apply_filters()

    # ========================================================
    # CHART
    # ========================================================

    def _render_pivot_chart(self):
        if self.ax is None or self.figure is None or self.chart_canvas is None:
            return

        self.ax.clear()
        self.figure.patch.set_facecolor(BG_PANEL_2)
        self.ax.set_facecolor(BG_PANEL_2)
        self.ax.tick_params(colors=FG_MUTED, labelsize=9)
        for spine in self.ax.spines.values():
            spine.set_color(BORDER)
        self.ax.grid(True, axis="y", alpha=0.18)

        df = self.pivot_df.copy()
        if df.empty:
            self.ax.text(
                0.5,
                0.5,
                "No data",
                color=FG_MUTED,
                ha="center",
                va="center",
                transform=self.ax.transAxes,
            )
            self.chart_canvas.draw_idle()
            return

        df = df.head(CHART_MAX_SYMBOLS).copy()
        x = list(range(len(df)))
        width = 0.24

        buy_vals = df["BUY"].tolist() if "BUY" in df.columns else [0] * len(df)
        sell_vals = df["SELL"].tolist() if "SELL" in df.columns else [0] * len(df)
        both_vals = df["BOTH"].tolist() if "BOTH" in df.columns else [0] * len(df)
        labels = df["symbol"].tolist()

        self.ax.bar(
            [i - width for i in x],
            buy_vals,
            width=width,
            label="BUY",
            color=CHART_COLORS["BUY"],
        )
        self.ax.bar(
            x,
            sell_vals,
            width=width,
            label="SELL",
            color=CHART_COLORS["SELL"],
        )
        self.ax.bar(
            [i + width for i in x],
            both_vals,
            width=width,
            label="BOTH",
            color=CHART_COLORS["BOTH"],
        )

        self.ax.set_title("Strategy Distribution by Symbol", color=FG_MAIN, fontsize=12)
        self.ax.set_ylabel("Count", color=FG_MUTED)
        self.ax.set_xticks(x)
        self.ax.set_xticklabels(labels, rotation=45, ha="right", color=FG_MUTED)

        legend = self.ax.legend(facecolor=BG_PANEL_2, edgecolor=BORDER)
        for text in legend.get_texts():
            text.set_color(FG_MAIN)

        self.figure.tight_layout()
        self.chart_canvas.draw_idle()

    # ========================================================
    # EVENTS
    # ========================================================

    def _on_filter_change(self, _event=None):
        self._apply_filters()

    def _on_summary_select(self, _event=None):
        selected = self.summary_tree.selection()
        if not selected:
            return

        values = self.summary_tree.item(selected[0], "values")
        if not values:
            return

        symbol = safe_text(values[0])
        if symbol in list(self.symbol_combo["values"]):
            self.symbol_var.set(symbol)
            self._apply_filters()

    def _on_pivot_select(self, _event=None):
        selected = self.pivot_tree.selection()
        if not selected:
            return

        values = self.pivot_tree.item(selected[0], "values")
        if not values:
            return

        symbol = safe_text(values[0])
        if symbol == "Gesamtergebnis":
            return

        if symbol in list(self.symbol_combo["values"]):
            self.symbol_var.set(symbol)
            self._apply_filters()

    def _on_row_double_click(self, _event=None):
        selected = self.table.selection()
        if not selected:
            return

        item_values = self.table.item(selected[0], "values")
        if not item_values or len(item_values) < 13:
            return

        symbol = safe_text(item_values[0])
        variant_number = safe_text(item_values[1])
        strategy_id = safe_text(item_values[2])
        side = safe_text(item_values[3])
        timeframe = safe_text(item_values[4])
        display_name = safe_text(item_values[12])

        df = self.filtered_df.copy()
        match = df[
            (df["symbol"].astype(str) == symbol)
            & (df["variant_number"].astype(str) == variant_number)
            & (df["strategy_id"].astype(str) == strategy_id)
            & (df["side"].astype(str) == side)
            & (df["timeframe"].astype(str) == timeframe)
            & (df["display_name"].astype(str) == display_name)
        ].copy()

        if match.empty:
            return

        row = match.iloc[0].to_dict()
        self._open_detail_window(row)

    # ========================================================
    # DETAIL WINDOW
    # ========================================================

    def _open_detail_window(self, row: Dict[str, Any]):
        win = tk.Toplevel(self)
        win.title(f"Strategy Detail | {safe_text(row.get('strategy_uid'))}")
        win.geometry("1180x780")
        win.minsize(980, 680)
        win.configure(bg=BG_MAIN)

        header = tk.Frame(win, bg=BG_HEADER, highlightbackground=BORDER, highlightthickness=1, height=52)
        header.pack(fill="x", padx=10, pady=10)
        header.pack_propagate(False)

        tk.Label(
            header,
            text="STRATEGY PROFILE DETAIL",
            font=FONT_TITLE,
            bg=BG_HEADER,
            fg=FG_MAIN,
        ).pack(side="left", padx=12)

        tk.Label(
            header,
            text=safe_text(row.get("profile_file")),
            font=("Segoe UI", 9),
            bg=BG_HEADER,
            fg=FG_MUTED,
        ).pack(side="right", padx=12)

        kpi_row = tk.Frame(win, bg=BG_MAIN)
        kpi_row.pack(fill="x", padx=10, pady=(0, 10))

        for title, key in [
            ("Symbol", "symbol"),
            ("Variant", "variant_number"),
            ("Strategy ID", "strategy_id"),
            ("Side", "side"),
            ("Timeframe", "timeframe"),
        ]:
            card = KpiCard(kpi_row, title)
            card.pack(side="left", fill="x", expand=True, padx=4)
            card.set_value(safe_text(row.get(key)))

        body = tk.Frame(win, bg=BG_PANEL, highlightbackground=BORDER, highlightthickness=1)
        body.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        tk.Label(
            body,
            text="Profile Metadata",
            font=FONT_SECTION,
            bg=BG_PANEL,
            fg=FG_MAIN,
        ).pack(anchor="w", padx=10, pady=(10, 8))

        text = tk.Text(
            body,
            wrap="none",
            bg=BG_PANEL,
            fg=FG_MAIN,
            insertbackground=FG_MAIN,
            relief="flat",
            font=FONT_MONO,
        )
        text.pack(fill="both", expand=True, padx=10, pady=(0, 10))

        fields = [
            "strategy_uid",
            "row_key",
            "symbol",
            "variant_number",
            "strategy_id",
            "side",
            "timeframe",
            "base_name",
            "exit_label",
            "signal_label",
            "time_label",
            "display_name",
            "extended_display_name",
            "exit_profile",
            "signal_family",
            "risk_model_type",
            "sl_type",
            "tp_type",
            "trailing_type",
            "fixed_sl",
            "fixed_tp",
            "sl_coef",
            "tp_coef",
            "trailing_coef",
            "risk_percent",
            "fixed_lot",
            "initial_capital",
            "mm_enabled",
            "limit_time_range",
            "time_from",
            "time_to",
            "eod_exit",
            "friday_exit",
            "weekend_protection",
            "max_trades_per_day",
            "has_defined_stop_loss",
            "has_defined_take_profit_or_exit",
            "uses_aggressive_mm",
            "has_parser_uncertainty",
            "has_tight_stop",
            "profile_file",
            "profile_relative_path",
            "profile_path",
            "ea_file",
            "ea_path",
        ]

        lines = [f"{key:<32}: {safe_text(row.get(key))}" for key in fields]
        text.insert("1.0", "\n".join(lines))
        text.configure(state="disabled")

    # ========================================================
    # AUTO REFRESH
    # ========================================================

    def _on_toggle_auto_refresh(self):
        self.live_status_var.set(
            "LIVE | auto refresh enabled"
            if self.auto_refresh_enabled.get()
            else "LIVE | auto refresh disabled"
        )
        self._schedule_auto_refresh()

    def _schedule_auto_refresh(self):
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None

        if self.auto_refresh_enabled.get():
            self._refresh_job = self.after(AUTO_REFRESH_MS, self._auto_refresh_tick)

    def _auto_refresh_tick(self):
        try:
            if self.auto_refresh_enabled.get():
                self._refresh_all(live=True)
        finally:
            self._schedule_auto_refresh()

    def destroy(self):
        if self._refresh_job is not None:
            try:
                self.after_cancel(self._refresh_job)
            except Exception:
                pass
            self._refresh_job = None
        super().destroy()


# ============================================================
# STANDALONE WINDOW
# ============================================================

class StrategyDashboard(tk.Tk):
    def __init__(self, repo: StrategyProfileRepository):
        super().__init__()

        self.title(APP_TITLE)
        self.geometry("1860x1080")
        self.minsize(1460, 900)
        self.configure(bg=BG_MAIN)

        self.panel = StrategyDashboardPanel(self, repo=repo)
        self.panel.pack(fill="both", expand=True)

    def destroy(self):
        try:
            self.panel.destroy()
        except Exception:
            pass
        super().destroy()


# ============================================================
# MAIN
# ============================================================

def main():
    if not STRATEGY_PROFILE_ROOT.exists():
        raise RuntimeError(f"Strategy_Profile Root nicht gefunden: {STRATEGY_PROFILE_ROOT}")

    repo = StrategyProfileRepository(STRATEGY_PROFILE_ROOT)
    app = StrategyDashboard(repo)
    app.mainloop()


if __name__ == "__main__":
    main()