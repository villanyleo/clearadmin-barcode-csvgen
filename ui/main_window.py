"""
Main application window.
"""
import tkinter as tk
from tkinter import ttk
from datetime import datetime

from core.session import SessionManager


class MainWindow(tk.Tk):
    # Minimum time (ms) between two Enter presses to be treated as distinct barcodes.
    # Scanner fires Enter nearly instantly after the last digit, so a human pressing
    # Enter much slower will still work fine as a separator.
    BARCODE_TIMEOUT_MS = 100

    def __init__(self):
        super().__init__()
        self.title("HJC Barcode Scanner")
        self.geometry("780x520")
        self.minsize(600, 400)

        self._manager = SessionManager()
        self._input_buffer: list[str] = []

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

        columns = ("#", "Barcode", "Time")
        self._tree = ttk.Treeview(
            table_frame,
            columns=columns,
            show="headings",
            selectmode="browse",
        )

        self._tree.heading("#", text="#")
        self._tree.heading("Barcode", text="Barcode")
        self._tree.heading("Time", text="Time")

        self._tree.column("#", width=50, anchor=tk.CENTER, stretch=False)
        self._tree.column("Barcode", width=320, anchor=tk.W)
        self._tree.column("Time", width=160, anchor=tk.CENTER, stretch=False)

        vsb = ttk.Scrollbar(table_frame, orient=tk.VERTICAL, command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)

        self._tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        table_frame.rowconfigure(0, weight=1)
        table_frame.columnconfigure(0, weight=1)

        # ── Bottom status bar ────────────────────────────────────────────
        self._count_var = tk.StringVar(value="")
        bottom = ttk.Frame(self, padding=(8, 2, 8, 4))
        bottom.pack(side=tk.BOTTOM, fill=tk.X)
        ttk.Label(bottom, textvariable=self._count_var, anchor=tk.W).pack(side=tk.LEFT)

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
            barcode = "".join(self._input_buffer).strip()
            self._input_buffer.clear()
            if barcode:
                self._register_barcode(barcode)
        elif event.char and event.char.isprintable():
            self._input_buffer.append(event.char)

    def _register_barcode(self, value: str):
        entry = self._manager.add_barcode(value)
        if entry is None:
            return
        self._tree.insert(
            "",
            tk.END,
            values=(
                entry.sequence,
                entry.value,
                entry.timestamp.strftime("%H:%M:%S"),
            ),
        )
        # Auto-scroll to the new row
        children = self._tree.get_children()
        if children:
            self._tree.see(children[-1])
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  Button callbacks                                                    #
    # ------------------------------------------------------------------ #

    def _on_start_session(self):
        session = self._manager.start_session()
        self._clear_table()
        self._btn_start.config(text="New session")
        self._btn_reset.config(state=tk.NORMAL)
        self._refresh_status()

    def _on_reset(self):
        self._manager.reset_session()
        self._clear_table()
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  Helpers                                                             #
    # ------------------------------------------------------------------ #

    def _clear_table(self):
        for item in self._tree.get_children():
            self._tree.delete(item)

    def _refresh_status(self):
        session = self._manager.current
        if session is None:
            self._status_var.set("No active session")
            self._count_var.set("")
        else:
            started = session.started_at.strftime("%H:%M:%S")
            self._status_var.set(f"Session #{session.id}  —  started {started}")
            count = session.count
            self._count_var.set(
                f"{count} barcode{'s' if count != 1 else ''} scanned this session"
            )
