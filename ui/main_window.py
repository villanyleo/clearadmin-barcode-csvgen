"""
Main application window.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from core import sound
from core.session import SessionManager
from core.validation import is_valid_ean13


class MainWindow(tk.Tk):
    # Minimum time (ms) between two Enter presses to be treated as distinct barcodes.
    # Scanner fires Enter nearly instantly after the last digit, so a human pressing
    # Enter much slower will still work fine as a separator.
    BARCODE_TIMEOUT_MS = 100

    # Last-scan status colours.
    COLOR_SUCCESS = "#1a7f37"  # green text
    COLOR_ERROR = "#cf222e"    # red text
    COLOR_ROW_HIGHLIGHT = "#d4f4d7"  # light-green row background for last scan

    def __init__(self):
        super().__init__()
        self.title("HJC Barcode Scanner")
        self.geometry("780x520")
        self.minsize(600, 400)

        self._manager = SessionManager()
        self._input_buffer: list[str] = []
        # Maps a barcode value -> its Treeview row id, so re-scans update in place.
        self._row_for_value: dict[str, str] = {}
        self._highlighted_item: str | None = None

        self._build_ui()
        self._bind_scanner_input()
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  UI construction                                                     #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── Top toolbar ──────────────────────────────────────────────────
        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self._btn_start = ttk.Button(
            toolbar, text="Start session", command=self._on_start_session
        )
        self._btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self._btn_reset = ttk.Button(
            toolbar, text="Reset", command=self._on_reset, state=tk.DISABLED
        )
        self._btn_reset.pack(side=tk.LEFT)

        self._status_var = tk.StringVar(value="No active session")
        status_lbl = ttk.Label(toolbar, textvariable=self._status_var, anchor=tk.W)
        status_lbl.pack(side=tk.LEFT, padx=16)

        # ── Barcode table ────────────────────────────────────────────────
        table_frame = ttk.Frame(self, padding=(8, 0, 8, 8))
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)

        columns = ("#", "Barcode", "pcs", "Time")
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self._tree.heading("#", text="#")
        self._tree.heading("Barcode", text="Barcode")
        self._tree.heading("pcs", text="pcs")
        self._tree.heading("Time", text="Time")

        self._tree.column("#", width=50, anchor=tk.CENTER, stretch=False)
        self._tree.column("Barcode", width=300, anchor=tk.W)
        self._tree.column("pcs", width=70, anchor=tk.CENTER, stretch=False)
        self._tree.column("Time", width=150, anchor=tk.CENTER, stretch=False)

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
    #  Scanner input handling                                              #
    # ------------------------------------------------------------------ #

    def _bind_scanner_input(self):
        """Capture all key presses regardless of which widget has focus."""
        self.bind_all("<Key>", self._on_key)

    def _on_key(self, event):
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
            # First time this barcode appears this session — add a new row.
            row_number = len(self._row_for_value) + 1
            item = self._tree.insert(
                "", tk.END, values=(row_number, value, count, time_str)
            )
            self._row_for_value[value] = item
        else:
            # Seen before — bump the pcs count and refresh the last-scan time.
            self._tree.set(item, "pcs", count)
            self._tree.set(item, "Time", time_str)

        self._highlight_row(item)
        self._tree.see(item)
        self._refresh_status()

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
    #  Button callbacks                                                    #
    # ------------------------------------------------------------------ #

    def _on_start_session(self):
        session = self._manager.start_session()
        self._clear_table()
        self._scan_status_var.set("")
        self._btn_start.config(text="New session")
        self._btn_reset.config(state=tk.NORMAL)
        self._refresh_status()

    def _on_reset(self):
        self._manager.reset_session()
        self._clear_table()
        self._scan_status_var.set("")
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _clear_table(self):
        for item in self._tree.get_children():
            self._tree.delete(item)
        self._row_for_value.clear()
        self._highlighted_item = None

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
        else:
            started = session.started_at.strftime("%H:%M:%S")
            count = session.count
            self._status_var.set(
                f"Session #{session.id}  —  started {started}   ·   "
                f"{count} barcode{'s' if count != 1 else ''} scanned"
            )
