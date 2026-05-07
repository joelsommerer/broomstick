#!/usr/bin/env python3
"""MacCleaner — modernes UI mit Sidebar, 4 Hauptbereichen + 4 Tools."""

from __future__ import annotations

import os
import subprocess
import threading
from pathlib import Path

import tkinter as tk
from tkinter import ttk, messagebox
import customtkinter as ctk

from icons import make_icon, register_fonts

from data import (
    HOME,
    CLEANUP_CATEGORIES,
    MANAGE_CATEGORIES,
    collect_subcategory_items,
    disk_breakdown,
    find_archives,
    find_biggest_files,
    find_duplicates,
    find_leftovers,
    heavy_running_apps,
    human_size,
    is_protected,
    list_browser_extensions,
    list_files_in,
    list_installed_apps,
    list_login_items,
    memory_info,
    move_to_trash,
    open_path,
    reveal_in_finder,
    scan_downloads,
    scan_installers,
    scan_language_files,
    scan_screenshots,
)


# ─────────────────────────────────────────────────────────────────────
#  Theme
# ─────────────────────────────────────────────────────────────────────

C = {
    "bg":           "#0e1024",
    "bg_alt":       "#141733",
    "sidebar":      "#0a0c1f",
    "card":         "#1a1d3d",
    "card_hover":   "#232651",
    "card_alt":     "#222557",
    "border":       "#2a2e58",
    "accent":       "#7c5cff",
    "accent_2":     "#3b82f6",
    "accent_hover": "#9472ff",
    "accent_dim":   "#4c3aab",
    "success":      "#22c55e",
    "warning":      "#f59e0b",
    "danger":       "#ef4444",
    "text":         "#ffffff",
    "text_dim":     "#9ca3c4",
    "text_muted":   "#6b7299",
}

# Farben für die Disk-Bar (System / Apps / Duplicates / Documents / Movies / Music / Pictures / Archives / Downloads)
DISK_COLORS = {
    "System":       "#6b7299",
    "Applications": "#f97316",
    "Documents":    "#eab308",
    "Movies":       "#22c55e",
    "Music":        "#06b6d4",
    "Pictures":     "#3b82f6",
    "Downloads":    "#a78bfa",
    "Archives":     "#ec4899",
}

FONT_FAMILY = "SF Pro Display"


# ─────────────────────────────────────────────────────────────────────
#  Hilfen
# ─────────────────────────────────────────────────────────────────────

def style_ttk_widgets(root):
    style = ttk.Style(root)
    style.theme_use("default")
    for variant in ("MC.Treeview", "MC.Files.Treeview"):
        style.configure(
            variant,
            background=C["card"], foreground=C["text"],
            fieldbackground=C["card"], bordercolor=C["card"],
            borderwidth=0, rowheight=28,
            font=(FONT_FAMILY, 12),
        )
        style.configure(
            f"{variant}.Heading",
            background=C["bg_alt"], foreground=C["text_dim"],
            bordercolor=C["bg_alt"], borderwidth=0,
            font=(FONT_FAMILY, 11, "bold"), padding=(10, 6),
        )
        style.map(variant,
                  background=[("selected", C["accent_dim"])],
                  foreground=[("selected", C["text"])])


def show_partial_failure_dialog(parent, succeeded, failed, total):
    dlg = ctk.CTkToplevel(parent)
    dlg.title("Teilweise erfolgreich")
    dlg.geometry("700x480")
    dlg.minsize(540, 340)
    dlg.configure(fg_color=C["bg"])
    dlg.after(50, lambda: dlg.lift())

    frm = ctk.CTkFrame(dlg, fg_color="transparent")
    frm.pack(fill="both", expand=True, padx=20, pady=20)
    summary = (f"{len(succeeded)} von {total} Einträgen verschoben — "
               f"{len(failed)} konnte(n) nicht gelöscht werden.")
    ctk.CTkLabel(frm, text=summary, font=(FONT_FAMILY, 16, "bold"),
                 text_color=C["text"], anchor="w").pack(fill="x", pady=(0, 8))

    has_tcc = any("-5000" in err or "Zugriffsrechte" in err for _, err in failed)
    if has_tcc:
        hint = ("Diese Pfade sind durch macOS-Sandbox-Schutz gesichert. "
                "Klicke auf „Im Finder zeigen“ und lösche sie dort manuell — "
                "macOS fragt dabei nach deinem Login-Passwort.")
        ctk.CTkLabel(frm, text=hint, font=(FONT_FAMILY, 12),
                     text_color=C["text_dim"], wraplength=640,
                     justify="left", anchor="w").pack(fill="x", pady=(0, 12))

    list_frame = ctk.CTkFrame(frm, fg_color=C["card"], corner_radius=10)
    list_frame.pack(fill="both", expand=True, pady=(0, 12))
    txt = tk.Text(list_frame, wrap="word", font=("Menlo", 11),
                  bg=C["card"], fg=C["text"], insertbackground=C["text"],
                  borderwidth=0, highlightthickness=0, padx=12, pady=12)
    sb = ctk.CTkScrollbar(list_frame, command=txt.yview)
    txt.config(yscrollcommand=sb.set)
    sb.pack(side="right", fill="y", padx=(0, 4), pady=8)
    txt.pack(side="left", fill="both", expand=True)
    for p, err in failed:
        short = "Sandbox-Schutz (Admin-Passwort nötig)" if "-5000" in err else err
        txt.insert("end", f"• {p}\n  → {short}\n\n")
    txt.config(state="disabled")

    btns = ctk.CTkFrame(frm, fg_color="transparent")
    btns.pack(fill="x")
    ctk.CTkButton(btns, text="Alle im Finder zeigen", height=36,
                  fg_color=C["accent"], hover_color=C["accent_hover"],
                  command=lambda: reveal_in_finder([p for p, _ in failed])).pack(side="left")
    ctk.CTkButton(btns, text="Pfade kopieren", height=36,
                  fg_color=C["card"], hover_color=C["card_hover"],
                  text_color=C["text"], border_width=1, border_color=C["border"],
                  command=lambda: (dlg.clipboard_clear(),
                                   dlg.clipboard_append("\n".join(str(p) for p, _ in failed)))
                  ).pack(side="left", padx=(8, 0))
    ctk.CTkButton(btns, text="Schließen", height=36,
                  fg_color="transparent", text_color=C["text_dim"],
                  hover_color=C["card_hover"], command=dlg.destroy).pack(side="right")


def primary_button(parent, text, command, width=None):
    kw = dict(text=text, height=42, corner_radius=10,
              font=(FONT_FAMILY, 13, "bold"),
              fg_color=C["accent"], hover_color=C["accent_hover"],
              command=command)
    if width:
        kw["width"] = width
    return ctk.CTkButton(parent, **kw)


def secondary_button(parent, text, command, width=None):
    kw = dict(text=text, height=38, corner_radius=10,
              font=(FONT_FAMILY, 13),
              fg_color="transparent", text_color=C["text"],
              border_width=1, border_color=C["border"],
              hover_color=C["card_hover"], command=command)
    if width:
        kw["width"] = width
    return ctk.CTkButton(parent, **kw)


def danger_button(parent, text, command, width=None):
    kw = dict(text=text, height=42, corner_radius=10,
              font=(FONT_FAMILY, 13, "bold"),
              fg_color=C["danger"], hover_color="#dc2626", command=command)
    if width:
        kw["width"] = width
    return ctk.CTkButton(parent, **kw)


# ─────────────────────────────────────────────────────────────────────
#  Sidebar-Element mit Größenangabe rechts
# ─────────────────────────────────────────────────────────────────────

class SidebarItem(ctk.CTkFrame):
    def __init__(self, master, icon_key, text, command):
        super().__init__(master, fg_color="transparent", height=44, corner_radius=10)
        self.pack_propagate(False)
        self.command = command
        self.active = False

        self.icon = make_icon(self, icon_key, size=20,
                                color=C["text_dim"], bg_color=C["sidebar"])
        self.icon.place(x=14, rely=0.5, anchor="w")
        self.text_lbl = ctk.CTkLabel(self, text=text, font=(FONT_FAMILY, 13),
                                      text_color=C["text_dim"])
        self.text_lbl.place(x=48, rely=0.5, anchor="w")
        self.value_lbl = ctk.CTkLabel(self, text="", font=(FONT_FAMILY, 11),
                                       text_color=C["text_muted"])
        self.value_lbl.place(relx=1.0, x=-14, rely=0.5, anchor="e")

        for w in (self, self.text_lbl, self.value_lbl,
                   self.icon, self.icon.bg_lbl, self.icon.fg_lbl):
            w.bind("<Button-1>", lambda e: self.command())
            w.bind("<Enter>", self._hover_in)
            w.bind("<Leave>", self._hover_out)

    def _hover_in(self, _):
        if not self.active:
            self.configure(fg_color=C["card_hover"])
            self.icon.set_color(C["text_dim"], C["card_hover"])

    def _hover_out(self, _):
        if not self.active:
            self.configure(fg_color="transparent")
            self.icon.set_color(C["text_dim"], C["sidebar"])

    def set_active(self, active):
        self.active = active
        if active:
            self.configure(fg_color=C["accent"])
            self.icon.set_color(C["text"], C["accent"])
            self.text_lbl.configure(text_color=C["text"])
            self.value_lbl.configure(text_color=C["text"])
        else:
            self.configure(fg_color="transparent")
            self.icon.set_color(C["text_dim"], C["sidebar"])
            self.text_lbl.configure(text_color=C["text_dim"])
            self.value_lbl.configure(text_color=C["text_muted"])

    def set_value(self, text):
        self.value_lbl.configure(text=text)


# ─────────────────────────────────────────────────────────────────────
#  Übersicht
# ─────────────────────────────────────────────────────────────────────

class OverviewPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.disk_data: dict | None = None
        self.junk_bytes = 0

        self._build()
        self.after(200, self.refresh)

    def _build(self):
        # Header
        ctk.CTkLabel(self, text="Übersicht", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=32, pady=(28, 4))
        ctk.CTkLabel(self, text="Speicherplatz, Junk-Files und Quick-Actions auf einen Blick.",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]
                     ).pack(anchor="w", padx=32, pady=(0, 18))

        # Disk-Karte
        disk_card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14)
        disk_card.pack(fill="x", padx=32, pady=(0, 14))
        head = ctk.CTkFrame(disk_card, fg_color="transparent")
        head.pack(fill="x", padx=22, pady=(18, 6))
        make_icon(head, "hard_drive", size=22,
                   color=C["text"], bg_color=C["card"]).pack(side="left", padx=(0, 8))
        ctk.CTkLabel(head, text="Macintosh HD", font=(FONT_FAMILY, 16, "bold"),
                     text_color=C["text"]).pack(side="left")
        self.disk_free_lbl = ctk.CTkLabel(head, text="—", font=(FONT_FAMILY, 13),
                                            text_color=C["text_dim"])
        self.disk_free_lbl.pack(side="right")

        self.bar_canvas = tk.Canvas(disk_card, height=14, bg=C["card"],
                                     highlightthickness=0, borderwidth=0)
        self.bar_canvas.pack(fill="x", padx=22, pady=(8, 4))
        self.bar_canvas.bind("<Configure>", lambda _e: self._draw_bar())

        self.legend_frame = ctk.CTkFrame(disk_card, fg_color="transparent")
        self.legend_frame.pack(fill="x", padx=18, pady=(8, 18))

        # Junk + Memory + Hero
        hero = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14)
        hero.pack(fill="x", padx=32, pady=(0, 14))
        inner = ctk.CTkFrame(hero, fg_color="transparent")
        inner.pack(fill="both", expand=True, padx=24, pady=22)
        inner.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(inner, text="Fast Cleanup Mode", font=(FONT_FAMILY, 20, "bold"),
                     text_color=C["text"]).grid(row=0, column=0, sticky="w")

        stats_row = ctk.CTkFrame(inner, fg_color="transparent")
        stats_row.grid(row=1, column=0, sticky="ew", pady=(14, 16))
        stats_row.grid_columnconfigure(2, weight=1)

        ctk.CTkLabel(stats_row, text="Junk Files:", font=(FONT_FAMILY, 13),
                     text_color=C["text_dim"]).grid(row=0, column=0, padx=(0, 12))
        self.junk_lbl = ctk.CTkLabel(stats_row, text="—", font=(FONT_FAMILY, 22, "bold"),
                                       text_color=C["text"])
        self.junk_lbl.grid(row=0, column=1, sticky="w")
        ctk.CTkLabel(stats_row, text="Memory Usage:", font=(FONT_FAMILY, 13),
                     text_color=C["text_dim"]).grid(row=1, column=0, padx=(0, 12), pady=(8, 0))
        self.mem_lbl = ctk.CTkLabel(stats_row, text="—", font=(FONT_FAMILY, 22, "bold"),
                                      text_color=C["text"])
        self.mem_lbl.grid(row=1, column=1, sticky="w", pady=(8, 0))

        primary_button(inner, "Review and Clean Up",
                       lambda: self.app.show_page("cleanup")
                       ).grid(row=2, column=0, sticky="ew")

        # Quick-Aktionen
        ctk.CTkLabel(self, text="Schnellaktionen", font=(FONT_FAMILY, 16, "bold"),
                     text_color=C["text"]).pack(anchor="w", padx=32, pady=(4, 12))
        actions = ctk.CTkFrame(self, fg_color="transparent")
        actions.pack(fill="x", padx=32, pady=(0, 32))
        for i in range(4):
            actions.grid_columnconfigure(i, weight=1, uniform="act")
        self._action_card(actions, 0, "cleanup", "Clean Up", "Caches, Logs, Müll", "cleanup")
        self._action_card(actions, 1, "speedup", "Speed Up", "Startup, RAM", "speedup")
        self._action_card(actions, 2, "manage", "Manage Files", "Große Files finden", "manage")
        self._action_card(actions, 3, "duplicates", "Duplicates", "Doppelte Files", "duplicates")

    def _action_card(self, parent, col, icon_key, title, desc, target):
        card = ctk.CTkFrame(parent, fg_color=C["card"], corner_radius=12, height=92,
                             cursor="pointinghand")
        card.grid(row=0, column=col, padx=(0 if col == 0 else 10, 0), sticky="nsew")
        card.grid_propagate(False)
        ic = make_icon(card, icon_key, size=26,
                        color=C["accent"], bg_color=C["card"])
        ic.place(x=18, y=18)
        ctk.CTkLabel(card, text=title, font=(FONT_FAMILY, 13, "bold"),
                     text_color=C["text"]).place(x=62, y=20)
        ctk.CTkLabel(card, text=desc, font=(FONT_FAMILY, 11),
                     text_color=C["text_dim"]).place(x=62, y=42)
        for w in (card, *card.winfo_children(), ic, ic.bg_lbl, ic.fg_lbl):
            w.bind("<Button-1>", lambda e: self.app.show_page(target))

    def refresh(self):
        self.disk_free_lbl.configure(text="Wird berechnet …")
        self.junk_lbl.configure(text="…")
        self.mem_lbl.configure(text="…")

        def worker():
            data = disk_breakdown()
            mem = memory_info()
            junk = 0
            for cat in CLEANUP_CATEGORIES:
                if cat.get("readonly"):
                    continue
                for sub in cat.get("subcategories", []):
                    items = collect_subcategory_items(sub)
                    for it in items:
                        try:
                            from data import get_size_bytes
                            junk += get_size_bytes(it)
                        except Exception:
                            pass
                if cat.get("scan") == "downloads":
                    pass  # Downloads zählen wir nicht zu Junk
                elif cat.get("scan") == "installers":
                    for it in scan_installers():
                        try:
                            junk += it.stat().st_size
                        except Exception:
                            pass
                elif cat.get("scan") == "screenshots":
                    for it in scan_screenshots():
                        try:
                            junk += it.stat().st_size
                        except Exception:
                            pass
            self.after(0, lambda: self._update(data, mem, junk))

        threading.Thread(target=worker, daemon=True).start()

    def _update(self, data, mem, junk):
        self.disk_data = data
        self.junk_bytes = junk
        free_gb = data["free"] / 1e9
        total_gb = data["total"] / 1e9
        self.disk_free_lbl.configure(
            text=f"{free_gb:.1f} GB frei von {total_gb:.0f} GB"
        )
        self._draw_bar()
        self._draw_legend()
        self.junk_lbl.configure(text=human_size(junk))
        self.mem_lbl.configure(text=f"{mem.get('used_pct', 0)}%")
        # Sidebar-Werte aktualisieren
        self.app.set_sidebar_value("overview", human_size(junk))

    def _draw_bar(self):
        if not self.disk_data:
            return
        cv = self.bar_canvas
        cv.delete("all")
        cv.update_idletasks()
        w = cv.winfo_width() or 600
        h = 14
        cv.config(height=h)
        # Rounded background
        cv.create_rectangle(0, 0, w, h, fill=C["bg_alt"], outline="")
        total = self.disk_data["total"] or 1
        x = 0
        order = ["System", "Applications", "Documents", "Movies",
                 "Music", "Pictures", "Downloads"]
        for cat in order:
            sz = self.disk_data["categories"].get(cat, 0)
            seg_w = sz / total * w
            if seg_w < 1:
                continue
            cv.create_rectangle(x, 0, x + seg_w, h,
                                 fill=DISK_COLORS.get(cat, C["accent"]),
                                 outline="")
            x += seg_w

    def _draw_legend(self):
        for w in self.legend_frame.winfo_children():
            w.destroy()
        cats = self.disk_data["categories"]
        order = ["System", "Applications", "Documents",
                 "Movies", "Music", "Pictures", "Downloads"]
        for i, name in enumerate(order):
            self.legend_frame.grid_columnconfigure(i, weight=1, uniform="leg")
            tile = ctk.CTkFrame(self.legend_frame, fg_color="transparent")
            tile.grid(row=0, column=i, sticky="w", padx=4, pady=2)
            dot = ctk.CTkFrame(tile, fg_color=DISK_COLORS.get(name, C["accent"]),
                                width=8, height=8, corner_radius=2)
            dot.pack(side="left", pady=(6, 0))
            wrap = ctk.CTkFrame(tile, fg_color="transparent")
            wrap.pack(side="left", padx=(8, 0))
            ctk.CTkLabel(wrap, text=name, font=(FONT_FAMILY, 11),
                         text_color=C["text_dim"]).pack(anchor="w")
            ctk.CTkLabel(wrap, text=human_size(cats.get(name, 0)),
                         font=(FONT_FAMILY, 12, "bold"),
                         text_color=C["text"]).pack(anchor="w")


# ─────────────────────────────────────────────────────────────────────
#  Master-Detail-Liste (gemeinsam für CleanUp/SpeedUp/ManageFiles)
# ─────────────────────────────────────────────────────────────────────

class MasterListItem(ctk.CTkFrame):
    """Karten-Eintrag in der linken Liste. Klickbar."""
    def __init__(self, master, icon_key, name, on_click, has_checkbox=False):
        super().__init__(master, fg_color=C["card"], corner_radius=12, height=64)
        self.pack_propagate(False)
        self.on_click = on_click
        self.active = False
        self.checked = False
        self.has_checkbox = has_checkbox
        self._bg = C["card"]

        x = 14
        if has_checkbox:
            self.cb_var = tk.BooleanVar(value=False)
            self.cb = ctk.CTkCheckBox(self, text="", variable=self.cb_var,
                                       checkbox_width=20, checkbox_height=20,
                                       corner_radius=5, border_width=1,
                                       border_color=C["border"],
                                       fg_color=C["accent"],
                                       hover_color=C["accent_hover"],
                                       command=self._on_check)
            self.cb.place(x=x, rely=0.5, anchor="w")
            x += 30

        self.icon = make_icon(self, icon_key, size=22,
                                color=C["accent"], bg_color=self._bg)
        self.icon.place(x=x + 4, rely=0.5, anchor="w")
        x += 44
        self.name_lbl = ctk.CTkLabel(self, text=name, font=(FONT_FAMILY, 13, "bold"),
                                       text_color=C["text"], anchor="w")
        self.name_lbl.place(x=x, rely=0.5, anchor="w")

        self.size_lbl = ctk.CTkLabel(self, text="…", font=(FONT_FAMILY, 13, "bold"),
                                       text_color=C["text"])
        self.size_lbl.place(relx=1.0, x=-44, rely=0.5, anchor="e")

        self.chev = make_icon(self, "chevron_right", size=14,
                                 color=C["text_dim"], bg_color=self._bg)
        self.chev.place(relx=1.0, x=-16, rely=0.5, anchor="e")

        # Click bindings (nur auf nicht-checkbox Bereiche)
        for w in (self, self.name_lbl, self.size_lbl,
                   self.icon, self.icon.bg_lbl, self.icon.fg_lbl,
                   self.chev, self.chev.bg_lbl, self.chev.fg_lbl):
            w.bind("<Button-1>", lambda e: self.on_click())
            w.bind("<Enter>", self._hover_in)
            w.bind("<Leave>", self._hover_out)

    def _hover_in(self, _):
        if not self.active:
            self._bg = C["card_hover"]
            self.configure(fg_color=self._bg)
            self.icon.set_color(C["accent"], self._bg)
            self.chev.set_color(C["text_dim"], self._bg)

    def _hover_out(self, _):
        if not self.active:
            self._bg = C["card"]
            self.configure(fg_color=self._bg)
            self.icon.set_color(C["accent"], self._bg)
            self.chev.set_color(C["text_dim"], self._bg)

    def _on_check(self):
        self.checked = self.cb_var.get()

    def set_active(self, active):
        self.active = active
        self._bg = C["accent_dim"] if active else C["card"]
        self.configure(fg_color=self._bg)
        self.icon.set_color(C["accent"], self._bg)
        self.chev.set_color(C["text_dim"], self._bg)

    def set_value(self, text):
        self.size_lbl.configure(text=text)


# ─────────────────────────────────────────────────────────────────────
#  Clean Up
# ─────────────────────────────────────────────────────────────────────

class CleanUpPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.cat_widgets: dict[str, MasterListItem] = {}
        self.cat_data: dict[str, list[Path]] = {}  # alle Pfade pro Kategorie
        self.sub_state: dict[str, dict[str, dict]] = {}  # cat → sub_name → {var, items}
        self.selected_key: str | None = None
        self.detail_checks: list[tuple[tk.BooleanVar, Path, int]] = []

        self._build()
        self.after(200, self.scan_all)

    def _build(self):
        # Header
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "cleanup", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Clean Up", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Caches, Downloads, Screenshots, Mails, Papierkorb …",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        # Body: zwei Spalten
        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=(20, 14))
        body.grid_columnconfigure(0, weight=1, uniform="x")
        body.grid_columnconfigure(1, weight=2, uniform="x")
        body.grid_rowconfigure(0, weight=1)

        # Linke Liste
        left_wrap = ctk.CTkScrollableFrame(body, fg_color="transparent",
                                            scrollbar_button_color=C["card_hover"],
                                            scrollbar_button_hover_color=C["accent"])
        left_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        for cat in CLEANUP_CATEGORIES:
            item = MasterListItem(left_wrap, cat["icon"], cat["name"],
                                   on_click=lambda k=cat["key"]: self.select(k),
                                   has_checkbox=not cat.get("readonly", False))
            item.pack(fill="x", pady=4)
            self.cat_widgets[cat["key"]] = item

        # Detail-Panel
        right_card = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=14)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))

        self.detail_title = ctk.CTkLabel(right_card, text="Wähle eine Kategorie",
                                           font=(FONT_FAMILY, 16, "bold"),
                                           text_color=C["text"], anchor="w")
        self.detail_title.pack(fill="x", padx=22, pady=(18, 4))
        self.detail_desc = ctk.CTkLabel(right_card, text="",
                                          font=(FONT_FAMILY, 12),
                                          text_color=C["text_dim"],
                                          anchor="w", justify="left")
        self.detail_desc.pack(fill="x", padx=22, pady=(0, 12))

        sel_row = ctk.CTkFrame(right_card, fg_color="transparent")
        sel_row.pack(fill="x", padx=18, pady=(0, 8))
        self.select_all_var = tk.BooleanVar(value=True)
        self.select_all_cb = ctk.CTkCheckBox(
            sel_row, text=" Alle auswählen", variable=self.select_all_var,
            font=(FONT_FAMILY, 12), text_color=C["text"],
            checkbox_width=18, checkbox_height=18,
            fg_color=C["accent"], hover_color=C["accent_hover"],
            border_width=1, border_color=C["border"],
            command=self._toggle_select_all,
        )
        self.select_all_cb.pack(side="left")

        self.detail_scroll = ctk.CTkScrollableFrame(
            right_card, fg_color="transparent",
            scrollbar_button_color=C["card_hover"],
            scrollbar_button_hover_color=C["accent"],
        )
        self.detail_scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

        # Footer
        foot = ctk.CTkFrame(self, fg_color=C["bg_alt"], corner_radius=14, height=72)
        foot.pack(fill="x", padx=32, pady=(0, 24))
        foot.pack_propagate(False)
        self.total_lbl = ctk.CTkLabel(foot, text="0 B  ausgewählt",
                                        font=(FONT_FAMILY, 16, "bold"),
                                        text_color=C["text"])
        self.total_lbl.place(x=22, rely=0.5, anchor="w")
        primary_button(foot, "Review to Clean Up",
                        self.do_cleanup, width=200
                        ).place(relx=1.0, x=-22, rely=0.5, anchor="e")

    def scan_all(self):
        for w in self.cat_widgets.values():
            w.set_value("…")

        def worker():
            for cat in CLEANUP_CATEGORIES:
                items = self._gather_items(cat)
                self.cat_data[cat["key"]] = items
                size = 0
                for p in items:
                    try:
                        from data import get_size_bytes
                        size += get_size_bytes(p)
                    except Exception:
                        pass
                self.after(0, lambda k=cat["key"], s=size: self.cat_widgets[k].set_value(human_size(s)))
            # Zur ersten Kategorie springen
            self.after(0, lambda: self.select(CLEANUP_CATEGORIES[0]["key"]))

        threading.Thread(target=worker, daemon=True).start()

    def _gather_items(self, cat) -> list[Path]:
        items = []
        if "subcategories" in cat:
            for sub in cat["subcategories"]:
                items.extend(collect_subcategory_items(sub))
        elif cat.get("scan") == "downloads":
            items.extend(scan_downloads())
        elif cat.get("scan") == "installers":
            items.extend(scan_installers())
        elif cat.get("scan") == "screenshots":
            items.extend(scan_screenshots())
        elif cat.get("scan") == "languages":
            items.extend(scan_language_files())
        return items

    def select(self, key):
        self.selected_key = key
        for k, w in self.cat_widgets.items():
            w.set_active(k == key)
        cat = next(c for c in CLEANUP_CATEGORIES if c["key"] == key)
        self.detail_title.configure(text=cat["name"])
        self.detail_desc.configure(text=cat["desc"])

        # Detail-Liste neu aufbauen
        for w in self.detail_scroll.winfo_children():
            w.destroy()
        self.detail_checks = []

        items = self.cat_data.get(key, [])
        from data import get_size_bytes
        if not items:
            ctk.CTkLabel(self.detail_scroll,
                          text="Keine Einträge gefunden.",
                          font=(FONT_FAMILY, 12),
                          text_color=C["text_dim"]).pack(pady=20)
            self._update_total()
            return

        readonly = cat.get("readonly", False)
        # Sortiere nach Größe (lazy: nutze cached du-output via get_size_bytes)
        sized = [(p, get_size_bytes(p)) for p in items]
        sized.sort(key=lambda t: -t[1])

        for p, sz in sized:
            row = ctk.CTkFrame(self.detail_scroll, fg_color=C["card_alt"],
                                corner_radius=8, height=44)
            row.pack(fill="x", pady=2)
            row.pack_propagate(False)
            if not readonly:
                var = tk.BooleanVar(value=True)
                cb = ctk.CTkCheckBox(row, text="", variable=var,
                                       checkbox_width=18, checkbox_height=18,
                                       fg_color=C["accent"], hover_color=C["accent_hover"],
                                       border_width=1, border_color=C["border"],
                                       command=self._update_total)
                cb.place(x=14, rely=0.5, anchor="w")
                self.detail_checks.append((var, p, sz))

            label_text = self._short_path(p)
            ctk.CTkLabel(row, text=label_text, font=(FONT_FAMILY, 12),
                          text_color=C["text"], anchor="w").place(
                          x=42 if not readonly else 14, rely=0.5, anchor="w")
            ctk.CTkLabel(row, text=human_size(sz), font=(FONT_FAMILY, 12, "bold"),
                          text_color=C["text_dim"]).place(relx=1.0, x=-14, rely=0.5, anchor="e")

            # Rechtsklick → reveal
            for w in (row, *row.winfo_children()):
                w.bind("<Button-2>", lambda e, pp=p: reveal_in_finder([pp]))
                w.bind("<Button-3>", lambda e, pp=p: reveal_in_finder([pp]))
                w.bind("<Control-Button-1>", lambda e, pp=p: reveal_in_finder([pp]))

        self._update_total()

    def _short_path(self, p: Path) -> str:
        s = str(p)
        if s.startswith(str(HOME)):
            s = "~" + s[len(str(HOME)):]
        if len(s) > 70:
            s = s[:30] + " … " + s[-35:]
        return s

    def _toggle_select_all(self):
        on = self.select_all_var.get()
        for var, _, _ in self.detail_checks:
            var.set(on)
        self._update_total()

    def _update_total(self):
        total = sum(sz for var, _, sz in self.detail_checks if var.get())
        count = sum(1 for var, _, _ in self.detail_checks if var.get())
        self.total_lbl.configure(text=f"{human_size(total)}  ·  {count} Einträge ausgewählt")

    def do_cleanup(self):
        to_delete = [p for var, p, _ in self.detail_checks if var.get() and not is_protected(p)]
        if not to_delete:
            messagebox.showinfo("MacCleaner", "Nichts ausgewählt.")
            return
        msg = f"{len(to_delete)} Einträge in den Papierkorb verschieben?"
        if not messagebox.askyesno("Bestätigen", msg):
            return

        def worker():
            succ, fail = move_to_trash(to_delete)
            self.after(0, lambda: self._after(succ, fail, len(to_delete)))

        threading.Thread(target=worker, daemon=True).start()

    def _after(self, succeeded, failed, total):
        if not failed:
            messagebox.showinfo("Fertig", f"{len(succeeded)} von {total} Einträgen verschoben.")
        else:
            show_partial_failure_dialog(self, succeeded, failed, total)
        self.scan_all()


# ─────────────────────────────────────────────────────────────────────
#  Speed Up
# ─────────────────────────────────────────────────────────────────────

SPEEDUP_CATEGORIES = [
    {"key": "startup", "icon": "startup", "name": "Startup-Apps",
     "desc": "Apps die beim Anmelden automatisch starten"},
    {"key": "heavy", "icon": "heavy", "name": "Schwere Apps",
     "desc": "Aktuell laufende Apps mit hohem RAM-Verbrauch"},
    {"key": "ram", "icon": "ram", "name": "RAM optimieren",
     "desc": "Speicher-Status und freigeben"},
    {"key": "extensions", "icon": "extensions", "name": "Browser-Erweiterungen",
     "desc": "Safari, Chrome, Firefox"},
]


class SpeedUpPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.cat_widgets = {}
        self.selected_key = None
        self.startup_items = []
        self.heavy_items = []
        self.extensions = []
        self.mem = {}

        self._build()
        self.after(200, self.scan_all)

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "speedup", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Speed Up", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Programme verwalten und Mac beschleunigen",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=(20, 14))
        body.grid_columnconfigure(0, weight=1, uniform="x")
        body.grid_columnconfigure(1, weight=2, uniform="x")
        body.grid_rowconfigure(0, weight=1)

        left_wrap = ctk.CTkFrame(body, fg_color="transparent")
        left_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        for cat in SPEEDUP_CATEGORIES:
            item = MasterListItem(left_wrap, cat["icon"], cat["name"],
                                    on_click=lambda k=cat["key"]: self.select(k))
            item.pack(fill="x", pady=4)
            self.cat_widgets[cat["key"]] = item

        right_card = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=14)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.detail_title = ctk.CTkLabel(right_card, text="Wähle eine Kategorie",
                                           font=(FONT_FAMILY, 16, "bold"),
                                           text_color=C["text"], anchor="w")
        self.detail_title.pack(fill="x", padx=22, pady=(18, 4))
        self.detail_desc = ctk.CTkLabel(right_card, text="",
                                          font=(FONT_FAMILY, 12),
                                          text_color=C["text_dim"],
                                          anchor="w", justify="left", wraplength=600)
        self.detail_desc.pack(fill="x", padx=22, pady=(0, 12))

        self.detail_scroll = ctk.CTkScrollableFrame(
            right_card, fg_color="transparent",
            scrollbar_button_color=C["card_hover"],
            scrollbar_button_hover_color=C["accent"],
        )
        self.detail_scroll.pack(fill="both", expand=True, padx=14, pady=(0, 14))

    def scan_all(self):
        for w in self.cat_widgets.values():
            w.set_value("…")

        def worker():
            self.startup_items = list_login_items()
            self.heavy_items = heavy_running_apps()
            self.extensions = list_browser_extensions()
            self.mem = memory_info()
            self.after(0, self._update_counts)

        threading.Thread(target=worker, daemon=True).start()

    def _update_counts(self):
        self.cat_widgets["startup"].set_value(f"{len(self.startup_items)} Items")
        self.cat_widgets["heavy"].set_value(f"{len(self.heavy_items)} Apps")
        self.cat_widgets["ram"].set_value(f"{self.mem.get('used_pct', 0)}%")
        self.cat_widgets["extensions"].set_value(f"{len(self.extensions)} Erw.")
        self.select("startup")

    def select(self, key):
        self.selected_key = key
        for k, w in self.cat_widgets.items():
            w.set_active(k == key)
        cat = next(c for c in SPEEDUP_CATEGORIES if c["key"] == key)
        self.detail_title.configure(text=cat["name"])
        self.detail_desc.configure(text=cat["desc"])
        for w in self.detail_scroll.winfo_children():
            w.destroy()
        if key == "startup":
            self._render_startup()
        elif key == "heavy":
            self._render_heavy()
        elif key == "ram":
            self._render_ram()
        elif key == "extensions":
            self._render_extensions()

    def _render_startup(self):
        if not self.startup_items:
            ctk.CTkLabel(self.detail_scroll,
                          text="Keine Startup-Items gefunden.",
                          text_color=C["text_dim"]).pack(pady=20)
            return
        for it in self.startup_items:
            row = ctk.CTkFrame(self.detail_scroll, fg_color=C["card_alt"],
                                corner_radius=8, height=46)
            row.pack(fill="x", pady=3)
            row.pack_propagate(False)

            kind_color = C["accent_2"] if it["type"] == "login" else C["warning"]
            badge = ctk.CTkLabel(row, text=" Login " if it["type"] == "login" else " Agent ",
                                   font=(FONT_FAMILY, 9, "bold"),
                                   text_color=C["text"], fg_color=kind_color,
                                   corner_radius=6, width=60)
            badge.place(x=14, rely=0.5, anchor="w")
            ctk.CTkLabel(row, text=it["name"], font=(FONT_FAMILY, 12),
                          text_color=C["text"], anchor="w").place(x=84, rely=0.5, anchor="w")

            sw_var = tk.BooleanVar(value=bool(it["enabled"]))
            sw = ctk.CTkSwitch(row, text="", variable=sw_var,
                                width=42, switch_width=42, switch_height=22,
                                progress_color=C["accent"], button_color=C["text"])
            sw.place(relx=1.0, x=-16, rely=0.5, anchor="e")
            sw.configure(state="disabled")  # Toggle würde sudo brauchen → nur Anzeige

    def _render_heavy(self):
        if not self.heavy_items:
            ctk.CTkLabel(self.detail_scroll, text="Keine Daten.",
                          text_color=C["text_dim"]).pack(pady=20)
            return
        for app in self.heavy_items:
            row = ctk.CTkFrame(self.detail_scroll, fg_color=C["card_alt"],
                                corner_radius=8, height=44)
            row.pack(fill="x", pady=3)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=app["name"], font=(FONT_FAMILY, 12, "bold"),
                          text_color=C["text"], anchor="w").place(x=18, rely=0.5, anchor="w")
            ctk.CTkLabel(row, text=human_size(app["rss_bytes"]),
                          font=(FONT_FAMILY, 12, "bold"),
                          text_color=C["accent"]).place(relx=1.0, x=-18, rely=0.5, anchor="e")

    def _render_ram(self):
        m = self.mem
        wrap = ctk.CTkFrame(self.detail_scroll, fg_color="transparent")
        wrap.pack(fill="x", pady=10)
        for label, key, color in [
            ("Total RAM", "total", C["accent"]),
            ("Verwendet", "used", C["danger"]),
            ("Frei", "free", C["success"]),
        ]:
            row = ctk.CTkFrame(wrap, fg_color=C["card_alt"], corner_radius=8, height=46)
            row.pack(fill="x", pady=3)
            row.pack_propagate(False)
            ctk.CTkLabel(row, text=label, font=(FONT_FAMILY, 12),
                          text_color=C["text_dim"]).place(x=18, rely=0.5, anchor="w")
            ctk.CTkLabel(row, text=human_size(m.get(key, 0)),
                          font=(FONT_FAMILY, 13, "bold"),
                          text_color=color).place(relx=1.0, x=-18, rely=0.5, anchor="e")
        ctk.CTkLabel(self.detail_scroll,
                      text=f"\nAuslastung: {m.get('used_pct', 0)}%",
                      font=(FONT_FAMILY, 14, "bold"),
                      text_color=C["text"]).pack(pady=(20, 8))

        info = ("RAM-Optimieren („purge“) erfordert Administrator-Rechte und "
                "wird daher nicht direkt aus der App ausgeführt. Tipp: Apps "
                "schließen die du gerade nicht brauchst, oder Mac neu starten.")
        ctk.CTkLabel(self.detail_scroll, text=info,
                      font=(FONT_FAMILY, 11), text_color=C["text_dim"],
                      wraplength=500, justify="left").pack(padx=20, pady=10)
        secondary_button(self.detail_scroll, "Activity Monitor öffnen",
                          lambda: subprocess.run(["open", "-a", "Activity Monitor"])
                          ).pack(pady=10)

    def _render_extensions(self):
        if not self.extensions:
            ctk.CTkLabel(self.detail_scroll, text="Keine Browser-Erweiterungen gefunden.",
                          text_color=C["text_dim"]).pack(pady=20)
            return
        # Gruppieren nach Browser
        by_browser = {}
        for ext in self.extensions:
            by_browser.setdefault(ext["browser"], []).append(ext)
        for browser, exts in by_browser.items():
            ctk.CTkLabel(self.detail_scroll, text=browser,
                          font=(FONT_FAMILY, 14, "bold"),
                          text_color=C["accent"]).pack(anchor="w", padx=10, pady=(12, 6))
            for ext in exts:
                row = ctk.CTkFrame(self.detail_scroll, fg_color=C["card_alt"],
                                     corner_radius=8, height=44)
                row.pack(fill="x", pady=3)
                row.pack_propagate(False)
                ctk.CTkLabel(row, text=ext["name"], font=(FONT_FAMILY, 12),
                              text_color=C["text"], anchor="w").place(x=18, rely=0.5, anchor="w")
                ctk.CTkLabel(row, text=human_size(ext["size"]),
                              font=(FONT_FAMILY, 11), text_color=C["text_dim"]
                              ).place(relx=1.0, x=-18, rely=0.5, anchor="e")


# ─────────────────────────────────────────────────────────────────────
#  Manage Files
# ─────────────────────────────────────────────────────────────────────

class ManageFilesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.cat_widgets = {}
        self.cat_files: dict[str, list[dict]] = {}
        self.selected_key = None
        self.detail_checks: list[tuple[tk.BooleanVar, Path]] = []
        self._build()
        self.after(200, self.scan_all)

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "manage", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Manage Files", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box,
                      text="Dateien die viel Platz belegen anzeigen und löschen.",
                      font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=(20, 14))
        body.grid_columnconfigure(0, weight=1, uniform="x")
        body.grid_columnconfigure(1, weight=2, uniform="x")
        body.grid_rowconfigure(0, weight=1)

        left_wrap = ctk.CTkScrollableFrame(body, fg_color="transparent",
                                              scrollbar_button_color=C["card_hover"],
                                              scrollbar_button_hover_color=C["accent"])
        left_wrap.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        for cat in MANAGE_CATEGORIES:
            item = MasterListItem(left_wrap, cat["icon"], cat["name"],
                                    on_click=lambda k=cat["key"]: self.select(k))
            item.pack(fill="x", pady=4)
            self.cat_widgets[cat["key"]] = item

        right_card = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=14)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        self.detail_title = ctk.CTkLabel(right_card, text="Wähle eine Kategorie",
                                           font=(FONT_FAMILY, 16, "bold"),
                                           text_color=C["text"], anchor="w")
        self.detail_title.pack(fill="x", padx=22, pady=(18, 12))

        tree_wrap = ctk.CTkFrame(right_card, fg_color="transparent")
        tree_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.tree = ttk.Treeview(
            tree_wrap, columns=("size", "modified"), show="tree headings",
            selectmode="extended", style="MC.Files.Treeview",
        )
        self.tree.heading("#0", text="Datei")
        self.tree.heading("size", text="Größe")
        self.tree.heading("modified", text="Geändert")
        self.tree.column("#0", width=380)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("modified", width=110, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ctk.CTkScrollbar(tree_wrap, command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=sb.set)
        self.tree.bind("<Double-Button-1>", self._on_double)
        self.tree.bind("<Button-2>", self._on_right)
        self.tree.bind("<Button-3>", self._on_right)
        self.tree.bind("<Control-Button-1>", self._on_right)

        # Footer
        foot = ctk.CTkFrame(self, fg_color=C["bg_alt"], corner_radius=14, height=72)
        foot.pack(fill="x", padx=32, pady=(0, 24))
        foot.pack_propagate(False)
        self.foot_lbl = ctk.CTkLabel(foot, text="—",
                                       font=(FONT_FAMILY, 14, "bold"),
                                       text_color=C["text"])
        self.foot_lbl.place(x=22, rely=0.5, anchor="w")
        primary_button(foot, "Markierte in Papierkorb",
                        self.do_delete, width=220
                        ).place(relx=1.0, x=-22, rely=0.5, anchor="e")

    def scan_all(self):
        for w in self.cat_widgets.values():
            w.set_value("…")

        def worker():
            for cat in MANAGE_CATEGORIES:
                if cat.get("scan") == "archives":
                    files = find_archives()
                else:
                    files = list_files_in(cat["path"])
                self.cat_files[cat["key"]] = files
                size = sum(f["size"] for f in files)
                self.after(0, lambda k=cat["key"], s=size: self.cat_widgets[k].set_value(human_size(s)))
            self.after(0, lambda: self.select(MANAGE_CATEGORIES[0]["key"]))

        threading.Thread(target=worker, daemon=True).start()

    def select(self, key):
        self.selected_key = key
        for k, w in self.cat_widgets.items():
            w.set_active(k == key)
        cat = next(c for c in MANAGE_CATEGORIES if c["key"] == key)
        self.detail_title.configure(text=cat["name"])

        self.tree.delete(*self.tree.get_children())
        files = self.cat_files.get(key, [])
        from datetime import datetime
        for f in files:
            try:
                date = datetime.fromtimestamp(f["mtime"]).strftime("%d.%m.%Y")
            except Exception:
                date = "—"
            self.tree.insert("", "end", iid=str(f["path"]),
                              text="📁  " + f["name"] if f.get("is_dir") else "📄  " + f["name"],
                              values=(human_size(f["size"]), date))
        self.foot_lbl.configure(
            text=f"{len(files)} Einträge  ·  {human_size(sum(f['size'] for f in files))}"
        )

    def _on_double(self, _evt):
        sel = self.tree.selection()
        if sel:
            open_path(Path(sel[0]))

    def _on_right(self, evt):
        iid = self.tree.identify_row(evt.y)
        if iid:
            self.tree.selection_set(iid)
            menu = tk.Menu(self, tearoff=0,
                            bg=C["card"], fg=C["text"],
                            activebackground=C["accent"], activeforeground=C["text"],
                            borderwidth=0, font=(FONT_FAMILY, 12))
            menu.add_command(label="Im Finder zeigen",
                              command=lambda: reveal_in_finder([Path(iid)]))
            menu.add_command(label="Öffnen", command=lambda: open_path(Path(iid)))
            menu.add_separator()
            menu.add_command(label="Pfad kopieren",
                              command=lambda: (self.clipboard_clear(),
                                                self.clipboard_append(iid)))
            try:
                menu.tk_popup(evt.x_root, evt.y_root)
            finally:
                menu.grab_release()

    def do_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("MacCleaner", "Nichts ausgewählt.")
            return
        paths = [Path(s) for s in sel if not is_protected(Path(s))]
        if not messagebox.askyesno("Bestätigen",
                                     f"{len(paths)} Einträge in den Papierkorb verschieben?"):
            return

        def worker():
            succ, fail = move_to_trash(paths)
            self.after(0, lambda: self._after(succ, fail, len(paths)))

        threading.Thread(target=worker, daemon=True).start()

    def _after(self, succeeded, failed, total):
        if not failed:
            messagebox.showinfo("Fertig", f"{len(succeeded)} von {total} verschoben.")
        else:
            show_partial_failure_dialog(self, succeeded, failed, total)
        self.scan_all()


# ─────────────────────────────────────────────────────────────────────
#  Duplicates
# ─────────────────────────────────────────────────────────────────────

class DuplicatesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.groups: list[list[dict]] = []
        self.checks: list[tuple[tk.BooleanVar, Path]] = []
        self._build()

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "duplicates", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Duplicates", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box,
                      text="Findet identische Dateien in Documents, Downloads, Desktop, Pictures.",
                      font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=32, pady=(20, 12))
        primary_button(ctrl, "Scan starten", self.start_scan, width=140
                        ).pack(side="left")
        self.status_lbl = ctk.CTkLabel(ctrl, text="Noch nicht gescannt.",
                                          font=(FONT_FAMILY, 12),
                                          text_color=C["text_dim"])
        self.status_lbl.pack(side="left", padx=(16, 0))

        self.scroll = ctk.CTkScrollableFrame(self, fg_color="transparent",
                                                scrollbar_button_color=C["card_hover"],
                                                scrollbar_button_hover_color=C["accent"])
        self.scroll.pack(fill="both", expand=True, padx=32, pady=(0, 14))

        foot = ctk.CTkFrame(self, fg_color=C["bg_alt"], corner_radius=14, height=72)
        foot.pack(fill="x", padx=32, pady=(0, 24))
        foot.pack_propagate(False)
        self.foot_lbl = ctk.CTkLabel(foot, text="0 Duplikate ausgewählt",
                                       font=(FONT_FAMILY, 14, "bold"),
                                       text_color=C["text"])
        self.foot_lbl.place(x=22, rely=0.5, anchor="w")
        primary_button(foot, "Markierte in Papierkorb", self.do_delete, width=220
                        ).place(relx=1.0, x=-22, rely=0.5, anchor="e")

    def start_scan(self):
        self.status_lbl.configure(text="Scanne … (kann eine Weile dauern)")
        for w in self.scroll.winfo_children():
            w.destroy()

        def worker():
            groups = find_duplicates()
            self.after(0, lambda: self._render(groups))

        threading.Thread(target=worker, daemon=True).start()

    def _render(self, groups):
        self.groups = groups
        self.checks = []
        if not groups:
            self.status_lbl.configure(text="Keine Duplikate gefunden.")
            return
        total = sum((len(g) - 1) * g[0]["size"] for g in groups)
        self.status_lbl.configure(
            text=f"{len(groups)} Duplikat-Gruppen, {human_size(total)} freisetzbar."
        )
        for i, group in enumerate(groups):
            grp_card = ctk.CTkFrame(self.scroll, fg_color=C["card"], corner_radius=12)
            grp_card.pack(fill="x", pady=6)
            ctk.CTkLabel(grp_card,
                          text=f"Gruppe {i+1}  ·  {len(group)}× {human_size(group[0]['size'])}",
                          font=(FONT_FAMILY, 12, "bold"),
                          text_color=C["accent"]).pack(anchor="w", padx=18, pady=(12, 6))
            for j, item in enumerate(group):
                row = ctk.CTkFrame(grp_card, fg_color=C["card_alt"],
                                     corner_radius=8, height=40)
                row.pack(fill="x", padx=14, pady=2)
                row.pack_propagate(False)
                # Erste Datei nicht vorausgewählt (zum Behalten), Rest vorausgewählt
                var = tk.BooleanVar(value=(j != 0))
                cb = ctk.CTkCheckBox(row, text="", variable=var,
                                       checkbox_width=18, checkbox_height=18,
                                       fg_color=C["accent"], hover_color=C["accent_hover"],
                                       border_width=1, border_color=C["border"],
                                       command=self._update_total)
                cb.place(x=12, rely=0.5, anchor="w")
                self.checks.append((var, item["path"]))

                short = str(item["path"]).replace(str(HOME), "~")
                if len(short) > 80:
                    short = short[:30] + " … " + short[-45:]
                ctk.CTkLabel(row, text=short, font=(FONT_FAMILY, 11),
                              text_color=C["text"], anchor="w").place(x=42, rely=0.5, anchor="w")
                ctk.CTkButton(row, text="Im Finder", width=80, height=24,
                                fg_color="transparent", text_color=C["accent"],
                                hover_color=C["card_hover"],
                                command=lambda p=item["path"]: reveal_in_finder([p])
                                ).place(relx=1.0, x=-14, rely=0.5, anchor="e")
            ctk.CTkFrame(grp_card, fg_color="transparent", height=10).pack()
        self._update_total()

    def _update_total(self):
        cnt = sum(1 for v, _ in self.checks if v.get())
        self.foot_lbl.configure(text=f"{cnt} Duplikate ausgewählt")

    def do_delete(self):
        paths = [p for v, p in self.checks if v.get()]
        if not paths:
            messagebox.showinfo("MacCleaner", "Nichts ausgewählt.")
            return
        if not messagebox.askyesno("Bestätigen",
                                     f"{len(paths)} Duplikate in den Papierkorb verschieben?"):
            return

        def worker():
            succ, fail = move_to_trash(paths)
            self.after(0, lambda: self._after(succ, fail, len(paths)))

        threading.Thread(target=worker, daemon=True).start()

    def _after(self, succeeded, failed, total):
        if not failed:
            messagebox.showinfo("Fertig", f"{len(succeeded)} von {total} verschoben.")
        else:
            show_partial_failure_dialog(self, succeeded, failed, total)
        self.start_scan()


# ─────────────────────────────────────────────────────────────────────
#  Applications (Uninstaller)
# ─────────────────────────────────────────────────────────────────────

class ApplicationsPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.apps: list[dict] = []
        self.filtered_apps: list[dict] = []
        self.selected_app: dict | None = None
        self.leftovers: list[tuple[Path, int]] = []
        self._ctx_iid: str | None = None
        self._build()
        self.after(200, self.reload_apps)

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "applications", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Applications", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="App + Reste sauber deinstallieren",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        top = ctk.CTkFrame(self, fg_color="transparent")
        top.pack(fill="x", padx=32, pady=(20, 14))
        self.search_var = tk.StringVar()
        self.search_var.trace_add("write", lambda *a: self._apply_filter())
        ctk.CTkEntry(top, textvariable=self.search_var,
                      placeholder_text="App suchen …",
                      height=38, corner_radius=10, font=(FONT_FAMILY, 13),
                      fg_color=C["card"], border_color=C["border"]
                      ).pack(side="left", fill="x", expand=True)
        secondary_button(top, "Aktualisieren", self.reload_apps, width=120
                          ).pack(side="left", padx=(10, 0))

        body = ctk.CTkFrame(self, fg_color="transparent")
        body.pack(fill="both", expand=True, padx=32, pady=(0, 14))
        body.grid_columnconfigure(0, weight=1, uniform="x")
        body.grid_columnconfigure(1, weight=2, uniform="x")
        body.grid_rowconfigure(0, weight=1)

        apps_card = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=14)
        apps_card.grid(row=0, column=0, sticky="nsew", padx=(0, 8))
        ctk.CTkLabel(apps_card, text="Installierte Apps",
                      font=(FONT_FAMILY, 14, "bold"),
                      text_color=C["text"], anchor="w").pack(fill="x", padx=18, pady=(14, 8))
        list_wrap = ctk.CTkFrame(apps_card, fg_color="transparent")
        list_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 14))
        self.app_list = tk.Listbox(list_wrap, exportselection=False, activestyle="none",
                                     bg=C["card"], fg=C["text"],
                                     selectbackground=C["accent_dim"], selectforeground=C["text"],
                                     borderwidth=0, highlightthickness=0,
                                     font=(FONT_FAMILY, 13), relief="flat")
        self.app_list.pack(side="left", fill="both", expand=True)
        sb = ctk.CTkScrollbar(list_wrap, command=self.app_list.yview)
        sb.pack(side="right", fill="y")
        self.app_list.config(yscrollcommand=sb.set)
        self.app_list.bind("<<ListboxSelect>>", self._on_app_select)

        right_card = ctk.CTkFrame(body, fg_color=C["card"], corner_radius=14)
        right_card.grid(row=0, column=1, sticky="nsew", padx=(8, 0))
        head2 = ctk.CTkFrame(right_card, fg_color="transparent")
        head2.pack(fill="x", padx=18, pady=(14, 8))
        self.right_title = ctk.CTkLabel(head2, text="Reste",
                                          font=(FONT_FAMILY, 14, "bold"),
                                          text_color=C["text"], anchor="w")
        self.right_title.pack(side="left")
        self.right_subtitle = ctk.CTkLabel(head2, text="Wähle eine App",
                                              font=(FONT_FAMILY, 12),
                                              text_color=C["text_dim"], anchor="w")
        self.right_subtitle.pack(side="left", padx=(12, 0))

        tree_wrap = ctk.CTkFrame(right_card, fg_color="transparent")
        tree_wrap.pack(fill="both", expand=True, padx=14, pady=(0, 12))
        self.tree = ttk.Treeview(tree_wrap, columns=("size",),
                                   show="tree headings", selectmode="browse",
                                   style="MC.Treeview")
        self.tree.heading("#0", text="Pfad")
        self.tree.heading("size", text="Größe")
        self.tree.column("#0", width=400)
        self.tree.column("size", width=90, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)
        tsb = ctk.CTkScrollbar(tree_wrap, command=self.tree.yview)
        tsb.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=tsb.set)
        self.tree.bind("<Button-1>", self._on_tree_click)
        self.tree.bind("<Button-2>", self._show_ctx)
        self.tree.bind("<Button-3>", self._show_ctx)
        self.tree.bind("<Control-Button-1>", self._show_ctx)

        self.ctx_menu = tk.Menu(self, tearoff=0,
                                  bg=C["card"], fg=C["text"],
                                  activebackground=C["accent"], activeforeground=C["text"],
                                  borderwidth=0, font=(FONT_FAMILY, 12))
        self.ctx_menu.add_command(label="Im Finder zeigen", command=self._ctx_reveal)
        self.ctx_menu.add_command(label="Übergeordneten Ordner öffnen", command=self._ctx_open_parent)
        self.ctx_menu.add_separator()
        self.ctx_menu.add_command(label="Pfad kopieren", command=self._ctx_copy)

        actions = ctk.CTkFrame(right_card, fg_color="transparent")
        actions.pack(fill="x", padx=14, pady=(0, 14))
        self.scan_btn = primary_button(actions, "Reste suchen",
                                          self.scan_leftovers)
        self.scan_btn.configure(state="disabled")
        self.scan_btn.pack(side="left")
        secondary_button(actions, "Alle ✓", lambda: self._toggle_all(True), width=80
                          ).pack(side="left", padx=(8, 0))
        secondary_button(actions, "Alle ✗", lambda: self._toggle_all(False), width=80
                          ).pack(side="left", padx=(4, 0))
        self.delete_btn = danger_button(actions, "In den Papierkorb",
                                          self.delete_selected)
        self.delete_btn.configure(state="disabled")
        self.delete_btn.pack(side="right")

    def reload_apps(self):
        def worker():
            apps = list_installed_apps()
            self.after(0, lambda: self._set_apps(apps))
        threading.Thread(target=worker, daemon=True).start()

    def _set_apps(self, apps):
        self.apps = apps
        self._apply_filter()
        self.app.set_sidebar_value("applications", f"{len(apps)} Apps")

    def _apply_filter(self):
        q = self.search_var.get().strip().lower()
        self.filtered_apps = ([a for a in self.apps if q in a["name"].lower() or q in a["bundle_id"].lower()]
                                if q else list(self.apps))
        self.app_list.delete(0, "end")
        for a in self.filtered_apps:
            self.app_list.insert("end", "  " + a["name"])

    def _on_app_select(self, _evt):
        sel = self.app_list.curselection()
        if not sel:
            return
        self.selected_app = self.filtered_apps[sel[0]]
        self.scan_btn.configure(state="normal")
        self.delete_btn.configure(state="disabled")
        self.tree.delete(*self.tree.get_children())
        self.right_title.configure(text=self.selected_app["name"])
        self.right_subtitle.configure(text=self.selected_app["bundle_id"] or "(kein Bundle-Identifier)")

    def scan_leftovers(self):
        if not self.selected_app:
            return
        self.scan_btn.configure(state="disabled")
        self.tree.delete(*self.tree.get_children())
        app = self.selected_app

        def worker():
            from data import get_size_bytes
            leftovers = find_leftovers(app["bundle_id"], app["name"])
            sized = [(p, get_size_bytes(p)) for p in leftovers]
            app_size = get_size_bytes(app["path"])
            self.after(0, lambda: self._show_leftovers(app["path"], app_size, sized))
        threading.Thread(target=worker, daemon=True).start()

    def _show_leftovers(self, app_path, app_size, leftovers):
        self.tree.insert("", "end", iid="app", text=f"☑   {app_path}",
                          values=(human_size(app_size),), tags=("checked",))
        for i, (p, sz) in enumerate(leftovers):
            self.tree.insert("", "end", iid=f"item_{i}", text=f"☑   {p}",
                              values=(human_size(sz),), tags=("checked",))
        self.leftovers = [(app_path, app_size)] + leftovers
        total = sum(sz for _, sz in self.leftovers)
        self.right_subtitle.configure(text=f"{len(leftovers)} Reste · Gesamt: {human_size(total)}")
        self.scan_btn.configure(state="normal")
        self.delete_btn.configure(state="normal")

    def _on_tree_click(self, evt):
        region = self.tree.identify("region", evt.x, evt.y)
        if region not in ("tree", "cell"):
            return
        iid = self.tree.identify_row(evt.y)
        if not iid:
            return
        tags = list(self.tree.item(iid, "tags"))
        text = self.tree.item(iid, "text")
        if "checked" in tags:
            tags.remove("checked")
            text = text.replace("☑", "☐", 1)
        else:
            tags.append("checked")
            text = text.replace("☐", "☑", 1)
        self.tree.item(iid, tags=tags, text=text)

    def _toggle_all(self, on):
        for iid in self.tree.get_children():
            tags = list(self.tree.item(iid, "tags"))
            text = self.tree.item(iid, "text")
            if on and "checked" not in tags:
                tags.append("checked")
                text = text.replace("☐", "☑", 1)
            elif not on and "checked" in tags:
                tags.remove("checked")
                text = text.replace("☑", "☐", 1)
            self.tree.item(iid, tags=tags, text=text)

    def _path_for_iid(self, iid):
        if iid == "app":
            return self.leftovers[0][0]
        if iid.startswith("item_"):
            try:
                return self.leftovers[int(iid.split("_", 1)[1]) + 1][0]
            except Exception:
                return None
        return None

    def _show_ctx(self, evt):
        iid = self.tree.identify_row(evt.y)
        if not iid:
            return
        self._ctx_iid = iid
        try:
            self.tree.selection_set(iid)
        except Exception:
            pass
        try:
            self.ctx_menu.tk_popup(evt.x_root, evt.y_root)
        finally:
            self.ctx_menu.grab_release()

    def _ctx_reveal(self):
        if self._ctx_iid:
            p = self._path_for_iid(self._ctx_iid)
            if p:
                reveal_in_finder([p])

    def _ctx_open_parent(self):
        if self._ctx_iid:
            p = self._path_for_iid(self._ctx_iid)
            if p and p.parent.exists():
                open_path(p.parent)

    def _ctx_copy(self):
        if self._ctx_iid:
            p = self._path_for_iid(self._ctx_iid)
            if p:
                self.clipboard_clear()
                self.clipboard_append(str(p))

    def delete_selected(self):
        to_delete = []
        for iid in self.tree.get_children():
            if "checked" in self.tree.item(iid, "tags"):
                p = self._path_for_iid(iid)
                if p:
                    to_delete.append(p)
        to_delete = [p for p in to_delete if not is_protected(p)]
        if not to_delete:
            messagebox.showinfo("MacCleaner", "Nichts ausgewählt.")
            return
        msg = f"{len(to_delete)} Eintrag/Einträge in den Papierkorb verschieben?\n\n"
        msg += "\n".join(f"• {p}" for p in to_delete[:8])
        if len(to_delete) > 8:
            msg += f"\n… und {len(to_delete) - 8} weitere"
        if not messagebox.askyesno("Löschen bestätigen", msg):
            return

        def worker():
            succ, fail = move_to_trash(to_delete)
            self.after(0, lambda: self._after_delete(succ, fail, len(to_delete)))
        threading.Thread(target=worker, daemon=True).start()

    def _after_delete(self, succeeded, failed, total):
        if not failed:
            messagebox.showinfo("Fertig", f"{len(succeeded)} von {total} verschoben.")
        else:
            show_partial_failure_dialog(self, succeeded, failed, total)
        if self.selected_app:
            self.scan_leftovers()


# ─────────────────────────────────────────────────────────────────────
#  Biggest Files
# ─────────────────────────────────────────────────────────────────────

class BiggestFilesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self.files: list[dict] = []
        self._build()

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "biggest", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Biggest Files", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Größte Dateien in deinem Home-Verzeichnis",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        ctrl = ctk.CTkFrame(self, fg_color="transparent")
        ctrl.pack(fill="x", padx=32, pady=(20, 12))
        ctk.CTkLabel(ctrl, text="Mindestgröße (MB):",
                      font=(FONT_FAMILY, 12),
                      text_color=C["text_dim"]).pack(side="left")
        self.min_size_var = tk.StringVar(value="50")
        ctk.CTkEntry(ctrl, textvariable=self.min_size_var, width=80,
                      height=34, corner_radius=8,
                      fg_color=C["card"], border_color=C["border"]
                      ).pack(side="left", padx=(8, 12))
        primary_button(ctrl, "Scan starten", self.start_scan, width=140
                        ).pack(side="left")
        self.status_lbl = ctk.CTkLabel(ctrl, text="",
                                          font=(FONT_FAMILY, 12),
                                          text_color=C["text_dim"])
        self.status_lbl.pack(side="left", padx=(16, 0))

        card = ctk.CTkFrame(self, fg_color=C["card"], corner_radius=14)
        card.pack(fill="both", expand=True, padx=32, pady=(0, 14))
        tree_wrap = ctk.CTkFrame(card, fg_color="transparent")
        tree_wrap.pack(fill="both", expand=True, padx=14, pady=14)
        self.tree = ttk.Treeview(tree_wrap, columns=("size", "modified"),
                                   show="tree headings", selectmode="extended",
                                   style="MC.Files.Treeview")
        self.tree.heading("#0", text="Datei")
        self.tree.heading("size", text="Größe")
        self.tree.heading("modified", text="Geändert")
        self.tree.column("#0", width=440)
        self.tree.column("size", width=90, anchor="e")
        self.tree.column("modified", width=110, anchor="e")
        self.tree.pack(side="left", fill="both", expand=True)
        sb = ctk.CTkScrollbar(tree_wrap, command=self.tree.yview)
        sb.pack(side="right", fill="y")
        self.tree.config(yscrollcommand=sb.set)
        self.tree.bind("<Double-Button-1>", lambda e: self._reveal_selected())
        self.tree.bind("<Button-2>", self._on_right)
        self.tree.bind("<Button-3>", self._on_right)
        self.tree.bind("<Control-Button-1>", self._on_right)

        foot = ctk.CTkFrame(self, fg_color=C["bg_alt"], corner_radius=14, height=72)
        foot.pack(fill="x", padx=32, pady=(0, 24))
        foot.pack_propagate(False)
        self.foot_lbl = ctk.CTkLabel(foot, text="—",
                                       font=(FONT_FAMILY, 14, "bold"),
                                       text_color=C["text"])
        self.foot_lbl.place(x=22, rely=0.5, anchor="w")
        primary_button(foot, "Markierte in Papierkorb",
                        self.do_delete, width=220
                        ).place(relx=1.0, x=-22, rely=0.5, anchor="e")

    def start_scan(self):
        try:
            min_mb = int(self.min_size_var.get())
        except ValueError:
            min_mb = 50
        self.status_lbl.configure(text="Scanne … (kann Minuten dauern)")
        self.tree.delete(*self.tree.get_children())

        def worker():
            files = find_biggest_files(min_size_mb=min_mb)
            self.after(0, lambda: self._render(files))
        threading.Thread(target=worker, daemon=True).start()

    def _render(self, files):
        self.files = files
        from datetime import datetime
        for f in files:
            try:
                date = datetime.fromtimestamp(f["mtime"]).strftime("%d.%m.%Y")
            except Exception:
                date = "—"
            self.tree.insert("", "end", iid=str(f["path"]),
                              text="📄  " + f["name"],
                              values=(human_size(f["size"]), date))
        total = sum(f["size"] for f in files)
        self.status_lbl.configure(text=f"{len(files)} Dateien, gesamt {human_size(total)}")
        self.foot_lbl.configure(text=f"{len(files)} Dateien · {human_size(total)}")

    def _reveal_selected(self):
        sel = self.tree.selection()
        if sel:
            reveal_in_finder([Path(s) for s in sel])

    def _on_right(self, evt):
        iid = self.tree.identify_row(evt.y)
        if iid:
            self.tree.selection_set(iid)
            menu = tk.Menu(self, tearoff=0,
                            bg=C["card"], fg=C["text"],
                            activebackground=C["accent"], activeforeground=C["text"],
                            borderwidth=0, font=(FONT_FAMILY, 12))
            menu.add_command(label="Im Finder zeigen",
                              command=lambda: reveal_in_finder([Path(iid)]))
            menu.add_command(label="Öffnen", command=lambda: open_path(Path(iid)))
            try:
                menu.tk_popup(evt.x_root, evt.y_root)
            finally:
                menu.grab_release()

    def do_delete(self):
        sel = self.tree.selection()
        if not sel:
            messagebox.showinfo("MacCleaner", "Nichts ausgewählt.")
            return
        paths = [Path(s) for s in sel if not is_protected(Path(s))]
        if not messagebox.askyesno("Bestätigen",
                                     f"{len(paths)} Dateien in den Papierkorb verschieben?"):
            return

        def worker():
            succ, fail = move_to_trash(paths)
            self.after(0, lambda: self._after(succ, fail, len(paths)))
        threading.Thread(target=worker, daemon=True).start()

    def _after(self, succeeded, failed, total):
        if not failed:
            messagebox.showinfo("Fertig", f"{len(succeeded)} von {total} verschoben.")
        else:
            show_partial_failure_dialog(self, succeeded, failed, total)
        # Entferne erfolgreich gelöschte aus Tree
        for p in succeeded:
            try:
                self.tree.delete(str(p))
            except Exception:
                pass


# ─────────────────────────────────────────────────────────────────────
#  Utilities
# ─────────────────────────────────────────────────────────────────────

UTILITIES = [
    ("activity", "Activity Monitor", "Prozesse und Ressourcen-Verbrauch",
     lambda: subprocess.run(["open", "-a", "Activity Monitor"])),
    ("disk", "Disk Utility", "Festplatten-Verwaltung und Reparatur",
     lambda: subprocess.run(["open", "-a", "Disk Utility"])),
    ("console", "Konsole", "System-Logs anzeigen",
     lambda: subprocess.run(["open", "-a", "Console"])),
    ("spotlight", "Spotlight neu indizieren", "Reindex via Terminal (sudo benötigt)",
     lambda: subprocess.run(["open", "-a", "Terminal", "-e", "sudo mdutil -E /"])),
    ("globe", "DNS-Cache leeren (Terminal)", "Öffnet Terminal mit Befehl",
     lambda: subprocess.run(["osascript", "-e",
        'tell app "Terminal" to do script "sudo dscacheutil -flushcache && sudo killall -HUP mDNSResponder"'])),
    ("trash", "Papierkorb leeren",
     "Verschiebt nichts mehr — entleert ~/.Trash sofort",
     lambda: subprocess.run(["osascript", "-e", 'tell application "Finder" to empty trash'])),
    ("folder", "Library-Ordner öffnen",
     "~/Library im Finder",
     lambda: subprocess.run(["open", str(HOME / "Library")])),
    ("settings", "Systemeinstellungen", "macOS Einstellungen",
     lambda: subprocess.run(["open", "-a", "System Settings"])),
]


class UtilitiesPage(ctk.CTkFrame):
    def __init__(self, master, app):
        super().__init__(master, fg_color="transparent")
        self.app = app
        self._build()

    def _build(self):
        head = ctk.CTkFrame(self, fg_color="transparent")
        head.pack(fill="x", padx=32, pady=(28, 4))
        make_icon(head, "utilities", size=34,
                   color=C["accent"], bg_color=C["bg"]).pack(side="left", padx=(0, 4))
        title_box = ctk.CTkFrame(head, fg_color="transparent")
        title_box.pack(side="left", padx=(12, 0))
        ctk.CTkLabel(title_box, text="Utilities", font=(FONT_FAMILY, 26, "bold"),
                     text_color=C["text"]).pack(anchor="w")
        ctk.CTkLabel(title_box, text="Schnellzugriffe auf System-Tools",
                     font=(FONT_FAMILY, 13), text_color=C["text_dim"]).pack(anchor="w")

        grid = ctk.CTkFrame(self, fg_color="transparent")
        grid.pack(fill="both", expand=True, padx=32, pady=(20, 24))
        for c in range(2):
            grid.grid_columnconfigure(c, weight=1, uniform="u")

        for i, (icon_key, title, desc, cmd) in enumerate(UTILITIES):
            row, col = divmod(i, 2)
            card = ctk.CTkFrame(grid, fg_color=C["card"], corner_radius=12,
                                  height=86, cursor="pointinghand")
            card.grid(row=row, column=col, padx=8, pady=6, sticky="nsew")
            card.grid_propagate(False)
            icon = make_icon(card, icon_key, size=28,
                              color=C["accent"], bg_color=C["card"])
            icon.place(x=22, rely=0.5, anchor="w")
            ctk.CTkLabel(card, text=title, font=(FONT_FAMILY, 14, "bold"),
                          text_color=C["text"]).place(x=68, y=22)
            ctk.CTkLabel(card, text=desc, font=(FONT_FAMILY, 11),
                          text_color=C["text_dim"]).place(x=68, y=46)
            chev = make_icon(card, "chevron_right", size=14,
                              color=C["text_dim"], bg_color=C["card"])
            chev.place(relx=1.0, x=-20, rely=0.5, anchor="e")
            for w in (card, *card.winfo_children()):
                w.bind("<Button-1>", lambda e, c=cmd: c())


# ─────────────────────────────────────────────────────────────────────
#  Hauptanwendung
# ─────────────────────────────────────────────────────────────────────

class App(ctk.CTk):
    def __init__(self):
        super().__init__()
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        self.title("MacCleaner Pro")
        self.geometry("1180x780")
        self.minsize(1000, 660)
        self.configure(fg_color=C["bg"])

        style_ttk_widgets(self)

        self.grid_columnconfigure(1, weight=1)
        self.grid_rowconfigure(0, weight=1)

        # Sidebar
        self.sidebar = ctk.CTkFrame(self, width=240, corner_radius=0,
                                      fg_color=C["sidebar"])
        self.sidebar.grid(row=0, column=0, sticky="nsew")
        self.sidebar.grid_propagate(False)

        # Logo
        logo = ctk.CTkFrame(self.sidebar, fg_color="transparent", height=70)
        logo.pack(fill="x", padx=20, pady=(28, 10))
        logo.pack_propagate(False)
        make_icon(logo, "logo", size=28,
                   color=C["accent"], bg_color=C["sidebar"]).pack(side="left", padx=(0, 4))
        ctk.CTkLabel(logo, text=" MacCleaner Pro",
                     font=(FONT_FAMILY, 17, "bold"),
                     text_color=C["text"]).pack(side="left", pady=(4, 0))

        ctk.CTkFrame(self.sidebar, fg_color=C["border"], height=1
                      ).pack(fill="x", padx=18, pady=(8, 14))

        # Hauptnavigation
        self.nav: dict[str, SidebarItem] = {}
        for key, icon_key, text in [
            ("overview",     "overview",     "Übersicht"),
            ("cleanup",      "cleanup",      "Clean Up"),
            ("speedup",      "speedup",      "Speed Up"),
            ("manage",       "manage",       "Manage Files"),
        ]:
            it = SidebarItem(self.sidebar, icon_key, text,
                              command=lambda k=key: self.show_page(k))
            it.pack(fill="x", padx=10, pady=2)
            self.nav[key] = it

        # Tools
        ctk.CTkLabel(self.sidebar, text="  TOOLS",
                     font=(FONT_FAMILY, 10, "bold"),
                     text_color=C["text_muted"], anchor="w"
                     ).pack(fill="x", padx=22, pady=(20, 6))

        for key, icon_key, text in [
            ("duplicates",   "duplicates",   "Duplicates"),
            ("applications", "applications", "Applications"),
            ("biggest",      "biggest",      "Biggest Files"),
            ("utilities",    "utilities",    "Utilities"),
        ]:
            it = SidebarItem(self.sidebar, icon_key, text,
                              command=lambda k=key: self.show_page(k))
            it.pack(fill="x", padx=10, pady=2)
            self.nav[key] = it

        # Footer
        ctk.CTkLabel(self.sidebar, text="Version 2.0 · joelsommerer",
                     font=(FONT_FAMILY, 10),
                     text_color=C["text_muted"], anchor="w"
                     ).pack(side="bottom", anchor="w", padx=20, pady=20)
        ctk.CTkFrame(self.sidebar, fg_color=C["border"], height=1
                      ).pack(side="bottom", fill="x", padx=18, pady=(0, 12))

        # Content
        content = ctk.CTkFrame(self, fg_color=C["bg"], corner_radius=0)
        content.grid(row=0, column=1, sticky="nsew")
        content.grid_columnconfigure(0, weight=1)
        content.grid_rowconfigure(0, weight=1)

        self.pages = {
            "overview":     OverviewPage(content, self),
            "cleanup":      CleanUpPage(content, self),
            "speedup":      SpeedUpPage(content, self),
            "manage":       ManageFilesPage(content, self),
            "duplicates":   DuplicatesPage(content, self),
            "applications": ApplicationsPage(content, self),
            "biggest":      BiggestFilesPage(content, self),
            "utilities":    UtilitiesPage(content, self),
        }
        for p in self.pages.values():
            p.grid(row=0, column=0, sticky="nsew")

        self.show_page("overview")

    def show_page(self, key: str):
        for k, btn in self.nav.items():
            btn.set_active(k == key)
        self.pages[key].tkraise()

    def set_sidebar_value(self, key: str, value: str):
        if key in self.nav:
            self.nav[key].set_value(value)


if __name__ == "__main__":
    register_fonts()
    App().mainloop()
