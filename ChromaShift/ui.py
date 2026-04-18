"""ChromaShift main window — built with CustomTkinter."""

from __future__ import annotations

import tkinter as tk
from tkinter import messagebox
from typing import TYPE_CHECKING, Callable, Optional

import customtkinter as ctk

from profiles import CVD_TYPES, PREVIEW_PAIRS, apply_matrix, get_matrix

if TYPE_CHECKING:
    from settings_manager import Settings

# ── Theme constants ───────────────────────────────────────────────────────────

_ACCENT = "#1A82E2"
_ACCENT_HOVER = "#1464B4"
_GREEN = "#2ECC71"
_RED = "#E74C3C"
_CARD = "#1E1E1E"
_BG = "#141414"
_TEXT = "#F0F0F0"
_SUBTEXT = "#999999"
_SEPARATOR = "#2A2A2A"

_CVD_ORDER = list(CVD_TYPES.keys())  # deterministic display order


class ChromaShiftWindow(ctk.CTk):
    """Main settings and control window for ChromaShift."""

    def __init__(
        self,
        settings: "Settings",
        on_toggle: Callable,
        on_cvd_change: Callable,
        on_mode_change: Callable,
        on_intensity_change: Callable,
        on_hotkey_change: Callable,
        on_startup_change: Callable,
        on_minimize_change: Callable,
        on_quit: Callable,
    ):
        super().__init__()

        self._settings = settings
        self._on_toggle = on_toggle
        self._on_cvd_change = on_cvd_change
        self._on_mode_change = on_mode_change
        self._on_intensity_change = on_intensity_change
        self._on_hotkey_change = on_hotkey_change
        self._on_startup_change = on_startup_change
        self._on_minimize_change = on_minimize_change
        self._on_quit = on_quit

        self._hotkey_listening = False

        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")

        self.title("ChromaShift")
        self.geometry("500x760")
        self.resizable(False, True)
        self.configure(fg_color=_BG)
        self.protocol("WM_DELETE_WINDOW", self._hide)

        # Try to set a decent icon
        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._build_ui()
        self._refresh_all()

    # ── Build ─────────────────────────────────────────────────────────────────

    def _build_ui(self):
        # Scrollable container
        self._scroll = ctk.CTkScrollableFrame(self, fg_color=_BG, scrollbar_button_color=_CARD)
        self._scroll.pack(fill="both", expand=True, padx=0, pady=0)

        self._build_header()
        self._build_status_card()
        self._build_cvd_selector()
        self._build_mode_selector()
        self._build_intensity()
        self._build_preview()
        self._build_settings()

    def _section(self, label: str) -> ctk.CTkFrame:
        """Return a styled section card frame, with a label above it."""
        ctk.CTkLabel(
            self._scroll, text=label,
            font=ctk.CTkFont(size=11, weight="bold"),
            text_color=_SUBTEXT, anchor="w",
        ).pack(fill="x", padx=20, pady=(18, 4))
        frame = ctk.CTkFrame(self._scroll, fg_color=_CARD, corner_radius=12)
        frame.pack(fill="x", padx=16, pady=(0, 4))
        return frame

    def _build_header(self):
        hdr = ctk.CTkFrame(self._scroll, fg_color=_BG)
        hdr.pack(fill="x", padx=20, pady=(20, 0))
        ctk.CTkLabel(
            hdr, text="ChromaShift",
            font=ctk.CTkFont(size=26, weight="bold"),
            text_color=_TEXT,
        ).pack(side="left")
        ctk.CTkLabel(
            hdr, text="Color accessibility for Windows",
            font=ctk.CTkFont(size=12),
            text_color=_SUBTEXT,
        ).pack(side="left", padx=(10, 0), pady=(6, 0))

    def _build_status_card(self):
        card = ctk.CTkFrame(self._scroll, fg_color=_CARD, corner_radius=14)
        card.pack(fill="x", padx=16, pady=(14, 0))

        inner = ctk.CTkFrame(card, fg_color="transparent")
        inner.pack(fill="x", padx=18, pady=14)

        # Status indicator row
        row = ctk.CTkFrame(inner, fg_color="transparent")
        row.pack(fill="x")
        self._status_dot = ctk.CTkLabel(row, text="●", font=ctk.CTkFont(size=18), text_color=_RED)
        self._status_dot.pack(side="left")
        self._status_label = ctk.CTkLabel(
            row, text="ChromaShift is OFF",
            font=ctk.CTkFont(size=15, weight="bold"), text_color=_TEXT,
        )
        self._status_label.pack(side="left", padx=8)

        self._mode_display = ctk.CTkLabel(
            inner, text="Select your vision type below to get started",
            font=ctk.CTkFont(size=12), text_color=_SUBTEXT, anchor="w",
        )
        self._mode_display.pack(fill="x", pady=(4, 10))

        self._toggle_btn = ctk.CTkButton(
            inner, text="Enable ChromaShift",
            font=ctk.CTkFont(size=14, weight="bold"),
            fg_color=_ACCENT, hover_color=_ACCENT_HOVER,
            height=44, corner_radius=10,
            command=self._on_toggle,
        )
        self._toggle_btn.pack(fill="x")

    def _build_cvd_selector(self):
        frame = self._section("YOUR VISION TYPE")

        self._cvd_var = tk.StringVar(value=self._settings.cvd_type)

        rows_frame = ctk.CTkFrame(frame, fg_color="transparent")
        rows_frame.pack(fill="x", padx=12, pady=12)

        # 2-column grid of radio buttons
        for idx, (key, info) in enumerate(CVD_TYPES.items()):
            col = idx % 2
            row = idx // 2
            cell = ctk.CTkFrame(rows_frame, fg_color="transparent")
            cell.grid(row=row, column=col, sticky="nsew", padx=4, pady=3)
            rows_frame.columnconfigure(col, weight=1)

            rb = ctk.CTkRadioButton(
                cell,
                text=info["label"],
                variable=self._cvd_var,
                value=key,
                font=ctk.CTkFont(size=13),
                text_color=_TEXT,
                command=lambda k=key: self._cvd_selected(k),
            )
            rb.pack(anchor="w")
            ctk.CTkLabel(
                cell, text=info["subtitle"],
                font=ctk.CTkFont(size=10), text_color=_SUBTEXT, anchor="w",
            ).pack(anchor="w", padx=(22, 0))

    def _build_mode_selector(self):
        frame = self._section("CORRECTION MODE")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=12)

        self._mode_seg = ctk.CTkSegmentedButton(
            inner,
            values=["Correct", "High Contrast", "Maximum", "Simulate"],
            command=self._mode_selected,
            font=ctk.CTkFont(size=12),
            height=36,
            selected_color=_ACCENT,
            selected_hover_color=_ACCENT_HOVER,
        )
        self._mode_seg.pack(fill="x")

        desc_map = {
            "Correct":       "Shifts confused colors so you can distinguish them.",
            "High Contrast": "2.5x stronger shift — pushes colors further apart.",
            "Maximum":       "4x aggressive shift — reds go dark, greens go bright.\nBest for severe red-green color blindness.",
            "Simulate":      "Shows what content looks like to a CVD viewer\n(useful for designers & developers).",
        }
        self._mode_desc = ctk.CTkLabel(
            inner, text=desc_map["Correct"],
            font=ctk.CTkFont(size=11), text_color=_SUBTEXT,
            anchor="w", justify="left",
        )
        self._mode_desc.pack(fill="x", pady=(8, 0))
        self._mode_desc_map = desc_map

    def _build_intensity(self):
        frame = self._section("INTENSITY")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=12)

        slider_row = ctk.CTkFrame(inner, fg_color="transparent")
        slider_row.pack(fill="x")

        self._intensity_pct = ctk.CTkLabel(
            slider_row, text="100%",
            font=ctk.CTkFont(size=14, weight="bold"),
            text_color=_TEXT, width=48,
        )
        self._intensity_pct.pack(side="right")

        self._intensity_slider = ctk.CTkSlider(
            slider_row,
            from_=0, to=100,
            number_of_steps=100,
            command=self._intensity_changed,
            button_color=_ACCENT,
            button_hover_color=_ACCENT_HOVER,
            progress_color=_ACCENT,
        )
        self._intensity_slider.pack(side="left", fill="x", expand=True, padx=(0, 8))

        ctk.CTkLabel(
            inner, text="Lower intensity for a more subtle effect.",
            font=ctk.CTkFont(size=11), text_color=_SUBTEXT,
        ).pack(anchor="w", pady=(4, 0))

    def _build_preview(self):
        frame = self._section("COLOR PREVIEW")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=(8, 12))

        ctk.CTkLabel(
            inner,
            text="Common confusion pairs — how they look with and without ChromaShift",
            font=ctk.CTkFont(size=11), text_color=_SUBTEXT,
        ).pack(anchor="w", pady=(0, 6))

        # Header row
        header = ctk.CTkFrame(inner, fg_color="transparent")
        header.pack(fill="x")
        for col_text, anchor in [("Pair", "w"), ("Without filter", "center"), ("With ChromaShift", "center")]:
            ctk.CTkLabel(
                header, text=col_text,
                font=ctk.CTkFont(size=10, weight="bold"),
                text_color=_SUBTEXT, anchor=anchor,
            ).pack(side="left", expand=True, fill="x")

        self._preview_canvas = tk.Canvas(
            inner, bg=_CARD, highlightthickness=0,
            height=len(PREVIEW_PAIRS) * 36 + 4,
        )
        self._preview_canvas.pack(fill="x", pady=(4, 0))
        self._preview_canvas.bind("<Configure>", lambda e: self._draw_preview())

    def _build_settings(self):
        frame = self._section("SETTINGS")
        inner = ctk.CTkFrame(frame, fg_color="transparent")
        inner.pack(fill="x", padx=12, pady=12)

        # Hotkey row
        hk_row = ctk.CTkFrame(inner, fg_color="transparent")
        hk_row.pack(fill="x", pady=(0, 10))
        ctk.CTkLabel(
            hk_row, text="Toggle Hotkey:",
            font=ctk.CTkFont(size=13), text_color=_TEXT,
        ).pack(side="left")
        self._hotkey_btn = ctk.CTkButton(
            hk_row,
            text=self._settings.hotkey.upper(),
            font=ctk.CTkFont(size=12, weight="bold"),
            fg_color="#2A2A2A", hover_color="#333333",
            text_color=_ACCENT, width=160, height=30,
            corner_radius=6,
            command=self._start_hotkey_capture,
        )
        self._hotkey_btn.pack(side="right")

        # Auto-start toggle
        self._startup_switch = ctk.CTkSwitch(
            inner,
            text="Start with Windows",
            font=ctk.CTkFont(size=13), text_color=_TEXT,
            progress_color=_ACCENT,
            command=self._startup_toggled,
        )
        self._startup_switch.pack(anchor="w", pady=4)

        # Start minimized toggle
        self._minimized_switch = ctk.CTkSwitch(
            inner,
            text="Start minimized to system tray",
            font=ctk.CTkFont(size=13), text_color=_TEXT,
            progress_color=_ACCENT,
            command=self._minimized_toggled,
        )
        self._minimized_switch.pack(anchor="w", pady=4)

        # Separator + quit
        ctk.CTkFrame(inner, height=1, fg_color=_SEPARATOR).pack(fill="x", pady=12)
        ctk.CTkButton(
            inner, text="Quit ChromaShift",
            font=ctk.CTkFont(size=13),
            fg_color="transparent", hover_color="#2A2A2A",
            text_color=_SUBTEXT, height=32,
            command=self._quit,
        ).pack(fill="x")

    # ── Event handlers ────────────────────────────────────────────────────────

    def _cvd_selected(self, key: str):
        self._settings.cvd_type = key
        self._on_cvd_change(key)
        self._draw_preview()
        self._refresh_status()

    def _mode_selected(self, label: str):
        mode_map = {"Correct": "correct", "High Contrast": "high_contrast", "Maximum": "maximum", "Simulate": "simulate"}
        mode = mode_map.get(label, "correct")
        self._settings.mode = mode
        self._on_mode_change(mode)
        self._mode_desc.configure(text=self._mode_desc_map.get(label, ""))
        self._draw_preview()
        self._refresh_status()

    def _intensity_changed(self, value: float):
        pct = int(value)
        self._intensity_pct.configure(text=f"{pct}%")
        self._settings.intensity = value / 100.0
        self._on_intensity_change(value / 100.0)
        self._draw_preview()

    def _startup_toggled(self):
        enabled = self._startup_switch.get()
        self._settings.start_with_windows = bool(enabled)
        self._on_startup_change(bool(enabled))

    def _minimized_toggled(self):
        enabled = self._minimized_switch.get()
        self._settings.start_minimized = bool(enabled)
        self._on_minimize_change(bool(enabled))

    def _start_hotkey_capture(self):
        self._hotkey_btn.configure(
            text="Press keys...", text_color="#FFA500",
            fg_color="#1A1A1A",
        )
        self._hotkey_listening = True
        self.bind("<KeyPress>", self._capture_key)
        self.focus_set()

    def _capture_key(self, event: tk.Event):
        if not self._hotkey_listening:
            return
        parts = []
        if event.state & 0x4:
            parts.append("ctrl")
        if event.state & 0x1:
            parts.append("shift")
        if event.state & 0x8:
            parts.append("alt")
        key = event.keysym.lower()
        if key not in ("control_l", "control_r", "shift_l", "shift_r", "alt_l", "alt_r"):
            parts.append(key)
            hotkey = "+".join(parts)
            self._hotkey_listening = False
            self.unbind("<KeyPress>")
            self._settings.hotkey = hotkey
            self._hotkey_btn.configure(
                text=hotkey.upper(),
                text_color=_ACCENT,
                fg_color="#2A2A2A",
            )
            self._on_hotkey_change(hotkey)

    def _quit(self):
        if messagebox.askyesno("Quit ChromaShift", "Quit ChromaShift and restore normal colors?"):
            self._on_quit()

    # ── Drawing ───────────────────────────────────────────────────────────────

    def _draw_preview(self):
        canvas = self._preview_canvas
        canvas.delete("all")
        w = canvas.winfo_width()
        if w < 10:
            return

        cvd = self._settings.cvd_type
        mode = self._settings.mode
        intensity = self._settings.intensity
        matrix = get_matrix(cvd, mode, intensity)

        col_w = w // 3
        swatch_h = 28
        pad_y = 4
        swatch_w = col_w - 16

        for i, (color_a, color_b, label) in enumerate(PREVIEW_PAIRS):
            y = i * 36 + 4

            # Label column
            canvas.create_text(
                6, y + swatch_h // 2,
                text=label, anchor="w",
                fill=_SUBTEXT, font=("Segoe UI", 9),
            )

            x_start = col_w  # "without" column starts here

            # Without filter: show original colors side by side
            for j, color in enumerate([color_a, color_b]):
                xc = x_start + j * (swatch_w // 2 + 2) + 4
                hex_c = "#{:02X}{:02X}{:02X}".format(*color)
                canvas.create_rectangle(xc, y, xc + swatch_w // 2, y + swatch_h,
                                        fill=hex_c, outline="")

            # With ChromaShift: show corrected colors
            x_start2 = col_w * 2
            for j, color in enumerate([color_a, color_b]):
                r, g, b = (v / 255.0 for v in color)
                cr, cg, cb = apply_matrix(matrix, (r, g, b))
                hex_c = "#{:02X}{:02X}{:02X}".format(
                    int(cr * 255), int(cg * 255), int(cb * 255)
                )
                xc = x_start2 + j * (swatch_w // 2 + 2) + 4
                canvas.create_rectangle(xc, y, xc + swatch_w // 2, y + swatch_h,
                                        fill=hex_c, outline="")

    # ── State refresh ─────────────────────────────────────────────────────────

    def _refresh_all(self):
        self._refresh_status()
        self._refresh_cvd()
        self._refresh_mode()
        self._refresh_intensity()
        self._refresh_settings()
        self.after(100, self._draw_preview)  # canvas needs to be rendered first

    def _refresh_status(self):
        enabled = self._settings.enabled
        cvd_label = CVD_TYPES.get(self._settings.cvd_type, {}).get("label", "")
        mode_label = {"correct": "Correction", "high_contrast": "High Contrast", "maximum": "Maximum", "simulate": "Simulation"}.get(
            self._settings.mode, ""
        )
        if enabled:
            self._status_dot.configure(text_color=_GREEN)
            self._status_label.configure(text="ChromaShift is ON")
            self._mode_display.configure(
                text=f"{cvd_label}  •  {mode_label}  •  {int(self._settings.intensity * 100)}% intensity"
            )
            self._toggle_btn.configure(text="Disable ChromaShift", fg_color=_RED, hover_color="#B03030")
        else:
            self._status_dot.configure(text_color=_RED)
            self._status_label.configure(text="ChromaShift is OFF")
            self._mode_display.configure(text="Select your vision type below, then click Enable.")
            self._toggle_btn.configure(text="Enable ChromaShift", fg_color=_ACCENT, hover_color=_ACCENT_HOVER)

    def _refresh_cvd(self):
        self._cvd_var.set(self._settings.cvd_type)

    def _refresh_mode(self):
        mode_label = {"correct": "Correct", "high_contrast": "High Contrast", "maximum": "Maximum", "simulate": "Simulate"}.get(
            self._settings.mode, "Correct"
        )
        self._mode_seg.set(mode_label)
        self._mode_desc.configure(text=self._mode_desc_map.get(mode_label, ""))

    def _refresh_intensity(self):
        pct = int(self._settings.intensity * 100)
        self._intensity_slider.set(pct)
        self._intensity_pct.configure(text=f"{pct}%")

    def _refresh_settings(self):
        self._hotkey_btn.configure(text=self._settings.hotkey.upper())
        if self._settings.start_with_windows:
            self._startup_switch.select()
        else:
            self._startup_switch.deselect()
        if self._settings.start_minimized:
            self._minimized_switch.select()
        else:
            self._minimized_switch.deselect()

    # ── Window management ─────────────────────────────────────────────────────

    def _hide(self):
        self.withdraw()

    def show(self):
        self.deiconify()
        self.lift()
        self.focus_force()
        self._refresh_all()
        self._draw_preview()

    def notify_toggle(self):
        """Called by app when the overlay state changes (e.g. via hotkey)."""
        self._refresh_status()

    def quit_app(self):
        self.destroy()
