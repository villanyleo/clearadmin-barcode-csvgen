"""
Main application window.
"""
import os
import sys
import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog

from core import export, persistence, sound
from core.catalog import Catalog, load_catalog
from core.session import Session, SessionManager
from core.validation import is_valid_ean13


class MainWindow(tk.Tk):
    # Last-scan status colours (bottom bar text).
    COLOR_SUCCESS = "#1a7f37"  # green text
    COLOR_ERROR = "#cf222e"    # red text
    COLOR_ROW_HIGHLIGHT = "#d4f4d7"  # light-green row background for last scan

    # Accent for the active-tab underline (Windows 11 default blue).
    COLOR_ACCENT = "#0067c0"

    # Fallback glyphs used only if the PNG icons cannot be loaded.
    FALLBACK_EDIT = "✎"
    FALLBACK_DELETE = "🗑"

    # Widget classes that should receive keystrokes for normal typing, so the
    # scanner handler doesn't swallow text entry (e.g. the rename dialog).
    _TEXT_ENTRY_CLASSES = {"Entry", "TEntry", "TCombobox", "Text", "Spinbox"}

    def __init__(self):
        super().__init__()
        self.title("HJC Barcode Scanner")
        self.geometry("980x600")
        self.minsize(820, 420)

        self.style = ttk.Style(self)
        self._configure_styles()
        # Background colour the native theme uses for frames, so our tab
        # containers and inactive underlines blend in seamlessly.
        self._tab_bg = self._safe_color(
            self.style.lookup("TFrame", "background"), "#f0f0f0"
        )

        self._manager = SessionManager()
        self._input_buffer: list[str] = []
        # Maps a barcode value -> its Treeview row id for the ACTIVE session,
        # so re-scans update in place. Rebuilt whenever the active tab changes.
        self._row_for_value: dict[str, str] = {}
        self._highlighted_item: str | None = None
        # Product catalog loaded from a CSV (shared by all sessions; None until loaded).
        self._catalog: Catalog | None = None
        self._csv_path: str | None = None  # last opened CSV, remembered across runs
        self._price_var = tk.StringVar()
        self._icons = self._load_icons()

        self._build_ui()
        self._bind_scanner_input()

        # Restore the previous run's sessions and CSV, or start fresh.
        if not self._restore_state():
            self._manager.start_session()
        self._on_session_changed()

        # Persist everything when the window is closed.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  Styling / assets                                                    #
    # ------------------------------------------------------------------ #

    def _configure_styles(self):
        self.style.configure("Tab.Toolbutton", font=("TkDefaultFont", 10), padding=(8, 3))
        self.style.configure(
            "TabActive.Toolbutton", font=("TkDefaultFont", 10, "bold"), padding=(8, 3)
        )
        self.style.configure("TabIcon.Toolbutton", padding=(3, 3))

    def _safe_color(self, color, fallback):
        try:
            if color:
                self.winfo_rgb(color)  # raises TclError if not a usable colour
                return color
        except tk.TclError:
            pass
        return fallback

    def _asset_path(self, name: str) -> str:
        # When frozen by PyInstaller, assets are unpacked under sys._MEIPASS.
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        return os.path.join(base, "assets", name)

    def _load_icons(self) -> dict:
        icons = {}
        for key, fname in (("edit", "edit.png"), ("delete", "delete.png")):
            try:
                icons[key] = tk.PhotoImage(file=self._asset_path(fname))
            except tk.TclError:
                pass  # fall back to a text glyph
        return icons

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── Top toolbar ──────────────────────────────────────────────────
        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self._btn_start = ttk.Button(
            toolbar, text="New session", command=self._on_start_session
        )
        self._btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self._btn_reset = ttk.Button(toolbar, text="Reset", command=self._on_reset)
        self._btn_reset.pack(side=tk.LEFT)

        self._btn_export = ttk.Button(
            toolbar, text="Export…", command=self._on_export
        )
        self._btn_export.pack(side=tk.LEFT, padx=(6, 0))

        self._status_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self._status_var, anchor=tk.W).pack(
            side=tk.LEFT, padx=16
        )

        # ── Right side: CSV catalog + price-list selector ────────────────
        # Packed right-to-left, so the visual order is: [Load CSV…] [Price:] [▾]
        self._price_combo = ttk.Combobox(
            toolbar, textvariable=self._price_var, state="disabled", width=14
        )
        self._price_combo.bind("<<ComboboxSelected>>", self._on_price_change)
        self._price_combo.pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Label(toolbar, text="Price:").pack(side=tk.RIGHT, padx=(12, 4))

        self._btn_load = ttk.Button(
            toolbar, text="Load CSV…", command=self._on_load_csv
        )
        self._btn_load.pack(side=tk.RIGHT)

        # ── Session tab bar (always visible; one tab per open session) ───
        self._tab_bar = tk.Frame(self, bg=self._tab_bg)
        self._tab_bar.pack(side=tk.TOP, fill=tk.X)

        # ── Barcode table ────────────────────────────────────────────────
        table_frame = ttk.Frame(self, padding=(8, 6, 8, 8))
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("#", "Barcode", "Name", "pcs", "Price", "Time")
        self._tree = ttk.Treeview(
            table_frame, columns=columns, show="headings", selectmode="browse"
        )

        self._tree.heading("#", text="#")
        self._tree.heading("Barcode", text="Barcode")
        self._tree.heading("Name", text="Name")
        self._tree.heading("pcs", text="pcs")
        self._tree.heading("Price", text="Price")
        self._tree.heading("Time", text="Time")

        self._tree.column("#", width=40, anchor=tk.CENTER, stretch=False)
        self._tree.column("Barcode", width=130, anchor=tk.W, stretch=False)
        self._tree.column("Name", width=380, anchor=tk.W)
        self._tree.column("pcs", width=55, anchor=tk.CENTER, stretch=False)
        self._tree.column("Price", width=90, anchor=tk.E, stretch=False)
        self._tree.column("Time", width=110, anchor=tk.CENTER, stretch=False)

        # Light-green background marking the most recently scanned row.
        self._tree.tag_configure("last_scanned", background=self.COLOR_ROW_HIGHLIGHT)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ── Bottom status bar (last-scan result) ─────────────────────────
        self._scan_status_var = tk.StringVar(value="")
        bottom = ttk.Frame(self, padding=(8, 2, 8, 4))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        self._scan_status_lbl = ttk.Label(
            bottom,
            textvariable=self._scan_status_var,
            anchor=tk.W,
            font=("TkDefaultFont", 11, "bold"),
        )
        self._scan_status_lbl.pack(side=tk.LEFT)

    # ------------------------------------------------------------------ #
    #  Tab bar                                                             #
    # ------------------------------------------------------------------ #

    def _rebuild_tab_bar(self):
        for child in self._tab_bar.winfo_children():
            child.destroy()

        active = self._manager.current
        for session in self._manager.sessions:
            is_active = session is active

            tab = tk.Frame(self._tab_bar, bg=self._tab_bg)
            tab.pack(side=tk.LEFT, padx=(6, 0), pady=(3, 0))

            row = tk.Frame(tab, bg=self._tab_bg)
            row.pack(side=tk.TOP)

            name_btn = ttk.Button(
                row,
                text=session.name,
                style="TabActive.Toolbutton" if is_active else "Tab.Toolbutton",
                command=lambda s=session: self._select_session(s),
            )
            name_btn.pack(side=tk.LEFT)

            self._make_icon_button(
                row, "edit", self.FALLBACK_EDIT,
                lambda s=session: self._on_rename_session(s)
            ).pack(side=tk.LEFT)

            self._make_icon_button(
                row, "delete", self.FALLBACK_DELETE,
                lambda s=session: self._on_delete_session(s)
            ).pack(side=tk.LEFT, padx=(0, 4))

            # Accent underline marks the active tab (Windows 11 style).
            underline = tk.Frame(
                tab, height=2, bg=self.COLOR_ACCENT if is_active else self._tab_bg
            )
            underline.pack(side=tk.TOP, fill=tk.X, pady=(2, 0))

    def _make_icon_button(self, parent, icon_key, fallback_text, command):
        if icon_key in self._icons:
            return ttk.Button(
                parent, image=self._icons[icon_key],
                style="TabIcon.Toolbutton", command=command, takefocus=False,
            )
        return ttk.Button(
            parent, text=fallback_text,
            style="TabIcon.Toolbutton", command=command, takefocus=False,
        )

    # ------------------------------------------------------------------ #
    #  Scanner input handling                                              #
    # ------------------------------------------------------------------ #

    def _bind_scanner_input(self):
        """Capture all key presses regardless of which widget has focus."""
        self.bind_all("<Key>", self._on_key)

    def _on_key(self, event):
        # Let normal typing through when a text field (e.g. the rename dialog) is focused.
        focus = self.focus_get()
        if focus is not None and focus.winfo_class() in self._TEXT_ENTRY_CLASSES:
            return

        if not self._manager.is_active:
            return

        if event.keysym == "Return":
            code = "".join(self._input_buffer).strip()
            self._input_buffer.clear()
            if code:
                self._handle_scan(code)
        elif event.char and event.char.isprintable():
            self._input_buffer.append(event.char)

    def _handle_scan(self, code: str):
        """Validate a scanned code, then give audio + visual feedback."""
        if is_valid_ean13(code):
            self._register_barcode(code)
            self._set_scan_status(f"{code} scanned", success=True)
            sound.play_success()
        else:
            self._set_scan_status(f"{code} is not an EAN-code", success=False)
            sound.play_error()

    def _register_barcode(self, value: str):
        entry = self._manager.add_barcode(value)
        if entry is None:
            return

        count = self._manager.current.count_for(value)
        time_str = entry.timestamp.strftime("%H:%M:%S")

        item = self._row_for_value.get(value)
        if item is None:
            # First time this barcode appears in this session — add a new row.
            row_number = len(self._row_for_value) + 1
            name, price = self._catalog_fields(value)
            item = self._tree.insert(
                "", tk.END, values=(row_number, value, name, count, price, time_str)
            )
            self._row_for_value[value] = item
        else:
            # Seen before — bump the pcs count and refresh the last-scan time.
            self._tree.set(item, "pcs", count)
            self._tree.set(item, "Time", time_str)

        self._highlight_row(item)
        self._tree.see(item)
        self._refresh_status()

    def _catalog_fields(self, value: str) -> tuple[str, str]:
        """Return (name, price) for *value* from the loaded catalog, or blanks."""
        if self._catalog is None:
            return "", ""
        product = self._catalog.get(value)
        if product is None:
            return "", ""
        return product.name, product.prices.get(self._price_var.get(), "")

    def _highlight_row(self, item: str):
        """Mark *item* as the last-scanned row (light green) and clear the previous one."""
        if (
            self._highlighted_item is not None
            and self._highlighted_item != item
            and self._tree.exists(self._highlighted_item)
        ):
            self._tree.item(self._highlighted_item, tags=())
        self._tree.item(item, tags=("last_scanned",))
        self._highlighted_item = item

    # ------------------------------------------------------------------ #
    #  Session / tab callbacks                                             #
    # ------------------------------------------------------------------ #

    def _restore_state(self) -> bool:
        """Reload the previous run's sessions + CSV. Returns True if anything restored."""
        state = persistence.load_state()
        if not state:
            return False
        try:
            manager_data = state.get("manager") or {}
            if not manager_data.get("sessions"):
                return False
            self._manager.load_state(manager_data)

            csv_path = state.get("csv_path")
            if csv_path and os.path.exists(csv_path):
                try:
                    self._catalog = load_catalog(csv_path)
                    self._csv_path = csv_path
                    self._price_combo.config(
                        values=self._catalog.price_names, state="readonly"
                    )
                except Exception:
                    self._catalog = None  # file changed/unreadable — carry on without it
        except Exception:
            # Corrupt/incompatible state — start fresh rather than crash.
            self._manager = SessionManager()
            return False
        return self._manager.current is not None

    def _on_close(self):
        persistence.save_state(
            {"manager": self._manager.to_dict(), "csv_path": self._csv_path}
        )
        self.destroy()

    def _on_start_session(self):
        self._manager.start_session()
        self._scan_status_var.set("")
        self._on_session_changed()

    def _select_session(self, session: Session):
        self._manager.select_session(session)
        self._scan_status_var.set("")
        self._on_session_changed()

    def _on_rename_session(self, session: Session):
        new_name = simpledialog.askstring(
            "Rename session", "Session name:", initialvalue=session.name, parent=self
        )
        if new_name is not None and new_name.strip():
            session.name = new_name.strip()
            self._rebuild_tab_bar()
            self._refresh_status()

    def _on_delete_session(self, session: Session):
        if session.entries and not messagebox.askyesno(
            "Delete session",
            f"Delete “{session.name}” and its {session.count} scanned "
            f"piece{'s' if session.count != 1 else ''}?",
        ):
            return
        self._manager.delete_session(session)
        if self._manager.current is None:
            # Never leave zero sessions — keep the tab row populated.
            self._manager.start_session()
        self._scan_status_var.set("")
        self._on_session_changed()

    def _on_reset(self):
        if self._manager.current is None:
            return
        self._manager.reset_session()
        self._populate_table_from_session(self._manager.current)
        self._scan_status_var.set("")
        self._refresh_status()

    def _on_export(self):
        session = self._manager.current
        if session is None or session.count == 0:
            messagebox.showinfo("Export", "This session has no scanned items to export.")
            return

        # Build rows in the same order as the table: (name, price, quantity).
        rows = []
        unmatched = 0
        for value, count, _last_ts in session.aggregated():
            name, price = self._catalog_fields(value)
            if not name:
                unmatched += 1
                name = value  # fall back to the barcode so the item is still identifiable
            rows.append((name, price, count))

        if unmatched and not messagebox.askokcancel(
            "Export",
            f"{unmatched} of {len(rows)} item(s) are not in the loaded product list.\n"
            f"They will be exported with the barcode as the name and no price.\n\n"
            f"Continue?",
        ):
            return

        path = filedialog.asksaveasfilename(
            title="Export session",
            defaultextension=".csv",
            initialfile=f"{session.name}.csv",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return

        try:
            export.write_export(path, rows)
        except Exception as exc:
            messagebox.showerror("Export failed", f"Could not write the file:\n\n{exc}")
            return

        # The session is intentionally left intact so it can still be edited later.
        self._set_scan_status(
            f"Exported {len(rows)} item{'s' if len(rows) != 1 else ''} "
            f"to {os.path.basename(path)}",
            success=True,
        )

    def _on_session_changed(self):
        """Sync the whole UI to the currently active session."""
        self._rebuild_tab_bar()
        session = self._manager.current
        if session is None:
            self._clear_table()
            self._refresh_status()
            return

        # Default this session's price list to the first one if a catalog is loaded.
        if self._catalog and not session.price_type and self._catalog.price_names:
            session.price_type = self._catalog.price_names[0]
        self._price_var.set(session.price_type or "")

        self._populate_table_from_session(session)
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  CSV catalog callbacks                                               #
    # ------------------------------------------------------------------ #

    def _on_load_csv(self):
        path = filedialog.askopenfilename(
            title="Select product CSV",
            filetypes=[("CSV files", "*.csv"), ("All files", "*.*")],
        )
        if not path:
            return
        try:
            catalog = load_catalog(path)
        except Exception as exc:
            messagebox.showerror(
                "Could not load CSV", f"Failed to read the file:\n\n{exc}"
            )
            return

        self._catalog = catalog
        self._csv_path = path
        self._price_combo.config(values=catalog.price_names, state="readonly")

        session = self._manager.current
        if session is not None:
            if not session.price_type and catalog.price_names:
                session.price_type = catalog.price_names[0]
            self._price_var.set(session.price_type or "")
        self._refresh_catalog_columns()
        self._set_scan_status(
            f"Loaded {len(catalog)} products from {os.path.basename(path)}",
            success=True,
        )

    def _on_price_change(self, event=None):
        # The chosen price list belongs to the active session.
        session = self._manager.current
        if session is not None:
            session.price_type = self._price_var.get()
        self._refresh_catalog_columns()

    def _refresh_catalog_columns(self):
        """Update the Name and Price cells of every row from the loaded catalog."""
        if self._catalog is None:
            return
        for value, item in self._row_for_value.items():
            name, price = self._catalog_fields(value)
            self._tree.set(item, "Name", name)
            self._tree.set(item, "Price", price)

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _clear_table(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._row_for_value.clear()
        self._highlighted_item = None

    def _populate_table_from_session(self, session: Session):
        """Rebuild the table to show *session*'s scans (used on tab switch / reset)."""
        self._clear_table()
        for value, count, last_ts in session.aggregated():
            name, price = self._catalog_fields(value)
            row_number = len(self._row_for_value) + 1
            item = self._tree.insert(
                "",
                tk.END,
                values=(row_number, value, name, count, price,
                        last_ts.strftime("%H:%M:%S")),
            )
            self._row_for_value[value] = item

        last = session.last_value()
        if last is not None and last in self._row_for_value:
            self._highlight_row(self._row_for_value[last])
            self._tree.see(self._row_for_value[last])

    def _set_scan_status(self, text: str, success: bool):
        """Show the last-scan result in the bottom bar, colour-coded."""
        self._scan_status_var.set(text)
        self._scan_status_lbl.configure(
            foreground=self.COLOR_SUCCESS if success else self.COLOR_ERROR
        )

    def _refresh_status(self):
        session = self._manager.current
        if session is None:
            self._status_var.set("No active session")
            return
        started = session.started_at.strftime("%H:%M:%S")
        text = f"{session.name}  —  started {started}   ·   {session.count} scanned"
        n = len(self._manager.sessions)
        if n > 1:
            text += f"   ({n} sessions open)"
        self._status_var.set(text)
