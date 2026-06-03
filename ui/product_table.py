"""
Görgethető, szerkeszthető terméklista.
"""
import tkinter as tk
from tkinter import ttk

# (fejléc szövege, pixel szélesség, igazítás) minden oszlophoz.
_COLUMNS = [
    ("#", 36, tk.CENTER),
    ("Vonalkód", 110, tk.W),
    ("Terméknév", 300, tk.W),
    ("", 30, tk.CENTER),       # mínusz gomb
    ("Darabszám", 44, tk.CENTER),
    ("", 30, tk.CENTER),       # plusz gomb
    ("Egységár (nettó)", 84, tk.E),
    ("Idő", 84, tk.CENTER),
    ("", 40, tk.CENTER),       # törlés gomb
]
_WIDTHS = [w for _, w, _ in _COLUMNS]
_TOTAL_WIDTH = sum(_WIDTHS)
_NAME_MAX_CHARS = 44

_LINE_BG = "#dcdcdc"        # belső háttérszín
_HEADER_BG = "#f3f3f3"
_ROW_BG = "#ffffff"
_ROW_HIGHLIGHT_BG = "#d4f4d7"  # sor kiemelés az utolsó szkennelt termékhez


def _truncate(text: str) -> str:
    return text if len(text) <= _NAME_MAX_CHARS else text[: _NAME_MAX_CHARS - 1] + "…"


class _Row:
    __slots__ = ("frame", "num", "name", "pcs", "price", "time", "minus", "labels")

    def __init__(self, frame, num, name, pcs, price, time, minus, labels):
        self.frame = frame
        self.num = num
        self.name = name
        self.pcs = pcs
        self.price = price
        self.time = time
        self.minus = minus
        self.labels = labels  # tk.Label-ek, háttérszín kiemeléskor változik


class ProductTable(ttk.Frame):
    def __init__(self, parent, on_increment, on_decrement, on_delete,
                 delete_icon=None, delete_fallback="X"):
        super().__init__(parent)
        self._on_increment = on_increment
        self._on_decrement = on_decrement
        self._on_delete = on_delete
        self._delete_icon = delete_icon
        self._delete_fallback = delete_fallback

        self._order: list[str] = []       # vonalkódok megjelenítési sorrendben
        self._rows: dict[str, _Row] = {}
        self._highlight_value: str | None = None

        style = ttk.Style(self)
        style.configure("Cell.TButton", padding=(0, 0))
        style.configure("CellIcon.TButton", padding=(1, 1))

        self._build()

    # ------------------------------------------------------------------ #
    #  Felépítés                                                          #
    # ------------------------------------------------------------------ #

    def _build(self):
        self.columnconfigure(0, weight=1)
        self.rowconfigure(1, weight=1)

        header = tk.Frame(self, bg=_HEADER_BG)
        header.grid(row=0, column=0, sticky="ew")
        self._apply_columns(header)
        for col, (text, _w, anchor) in enumerate(_COLUMNS):
            tk.Label(
                header, text=text, bg=_HEADER_BG, anchor=anchor,
                font=("TkDefaultFont", 10, "bold"),
            ).grid(row=0, column=col, sticky="nsew", padx=(4, 0), pady=4)

        self._canvas = tk.Canvas(self, bg=_LINE_BG, highlightthickness=0)
        self._canvas.grid(row=1, column=0, sticky="nsew")
        vsb = ttk.Scrollbar(self, orient=tk.VERTICAL, command=self._canvas.yview)
        vsb.grid(row=1, column=1, sticky="ns")
        self._canvas.configure(yscrollcommand=vsb.set)

        self._inner = tk.Frame(self._canvas, bg=_LINE_BG)
        self._window = self._canvas.create_window((0, 0), window=self._inner, anchor="nw")
        self._inner.columnconfigure(0, weight=1)

        self._inner.bind(
            "<Configure>",
            lambda e: self._canvas.configure(scrollregion=self._canvas.bbox("all")),
        )
        self._canvas.bind(
            "<Configure>",
            lambda e: self._canvas.itemconfigure(
                self._window, width=max(e.width, _TOTAL_WIDTH)
            ),
        )
        # Görgetés egérgörgővel csak akkor, ha a mutató a táblázat felett van
        self._canvas.bind("<Enter>", lambda e: self._canvas.bind_all("<MouseWheel>", self._on_wheel))
        self._canvas.bind("<Leave>", lambda e: self._canvas.unbind_all("<MouseWheel>"))

    def _apply_columns(self, frame):
        for col, w in enumerate(_WIDTHS):
            frame.columnconfigure(col, minsize=w, weight=0)

    def _on_wheel(self, event):
        self._canvas.yview_scroll(-1 if event.delta > 0 else 1, "units")

    # ------------------------------------------------------------------ #
    #  Nyilvános API                                                      #
    # ------------------------------------------------------------------ #

    def values(self) -> list[str]:
        return list(self._order)

    def clear(self):
        for row in self._rows.values():
            row.frame.destroy()
        self._rows.clear()
        self._order.clear()
        self._highlight_value = None

    def set_rows(self, rows):
        """rows: value/name/count/price/time kulcsú szótárak iterálható sorozata."""
        self.clear()
        for r in rows:
            self._append(r["value"], r["name"], r["count"], r["price"], r["time"])

    def upsert(self, value, name, count, price, time):
        row = self._rows.get(value)
        if row is None:
            self._append(value, name, count, price, time)
        else:
            row.name.config(text=_truncate(name))
            row.price.config(text=price)
            row.time.config(text=time)
            self.set_count(value, count)

    def update_cells(self, value, name, price):
        row = self._rows.get(value)
        if row is not None:
            row.name.config(text=_truncate(name))
            row.price.config(text=price)

    def set_count(self, value, count):
        row = self._rows.get(value)
        if row is None:
            return
        row.pcs.config(text=str(count))
        row.minus.state(["disabled"] if count <= 1 else ["!disabled"])

    def remove(self, value):
        row = self._rows.pop(value, None)
        if row is None:
            return
        row.frame.destroy()
        self._order.remove(value)
        if self._highlight_value == value:
            self._highlight_value = None
        # A megmaradt sorok újraszámozása
        for idx, val in enumerate(self._order):
            r = self._rows[val]
            r.frame.grid_configure(row=idx)
            r.num.config(text=str(idx + 1))

    def highlight(self, value):
        if value not in self._rows:
            return
        if (
            self._highlight_value is not None
            and self._highlight_value in self._rows
            and self._highlight_value != value
        ):
            self._set_row_bg(self._rows[self._highlight_value], _ROW_BG)
        self._set_row_bg(self._rows[value], _ROW_HIGHLIGHT_BG)
        self._highlight_value = value
        self._see(self._rows[value].frame)

    # ------------------------------------------------------------------ #
    #  Belső működés                                                      #
    # ------------------------------------------------------------------ #

    def _append(self, value, name, count, price, time):
        idx = len(self._order)
        frame = tk.Frame(self._inner, bg=_ROW_BG)
        frame.grid(row=idx, column=0, sticky="ew", pady=(0, 1))
        self._apply_columns(frame)

        num = tk.Label(frame, text=str(idx + 1), bg=_ROW_BG, anchor=tk.CENTER)
        barcode = tk.Label(frame, text=value, bg=_ROW_BG, anchor=tk.W)
        name_lbl = tk.Label(frame, text=_truncate(name), bg=_ROW_BG, anchor=tk.W)
        pcs = tk.Label(frame, text=str(count), bg=_ROW_BG, anchor=tk.CENTER)
        price_lbl = tk.Label(frame, text=price, bg=_ROW_BG, anchor=tk.E)
        time_lbl = tk.Label(frame, text=time, bg=_ROW_BG, anchor=tk.CENTER)

        minus = ttk.Button(
            frame, text="−", width=2, style="Cell.TButton", takefocus=False,
            command=lambda v=value: self._on_decrement(v),
        )
        plus = ttk.Button(
            frame, text="+", width=2, style="Cell.TButton", takefocus=False,
            command=lambda v=value: self._on_increment(v),
        )
        if self._delete_icon is not None:
            delete = ttk.Button(
                frame, image=self._delete_icon, style="CellIcon.TButton",
                takefocus=False, command=lambda v=value: self._on_delete(v),
            )
        else:
            delete = ttk.Button(
                frame, text=self._delete_fallback, width=2, style="Cell.TButton",
                takefocus=False, command=lambda v=value: self._on_delete(v),
            )

        num.grid(row=0, column=0, sticky="nsew", padx=(4, 0))
        barcode.grid(row=0, column=1, sticky="nsew", padx=(4, 0))
        name_lbl.grid(row=0, column=2, sticky="nsew", padx=(4, 0))
        minus.grid(row=0, column=3, sticky="nsew", padx=1, pady=1)
        pcs.grid(row=0, column=4, sticky="nsew")
        plus.grid(row=0, column=5, sticky="nsew", padx=1, pady=1)
        price_lbl.grid(row=0, column=6, sticky="nsew", padx=(4, 0))
        time_lbl.grid(row=0, column=7, sticky="nsew", padx=(4, 0))
        delete.grid(row=0, column=8, sticky="nsew", padx=2, pady=1)

        row = _Row(
            frame=frame, num=num, name=name_lbl, pcs=pcs, price=price_lbl,
            time=time_lbl, minus=minus,
            labels=[num, barcode, name_lbl, pcs, price_lbl, time_lbl],
        )
        self._rows[value] = row
        self._order.append(value)
        self.set_count(value, count)

    def _set_row_bg(self, row, color):
        row.frame.configure(bg=color)
        for label in row.labels:
            label.configure(bg=color)

    def _see(self, frame):
        self.update_idletasks()
        inner_h = self._inner.winfo_height()
        view_h = self._canvas.winfo_height()
        if inner_h <= view_h or inner_h <= 0:
            return
        y0 = frame.winfo_y()
        y1 = y0 + frame.winfo_height()
        view_top = self._canvas.canvasy(0)
        if y0 < view_top:
            self._canvas.yview_moveto(y0 / inner_h)
        elif y1 > view_top + view_h:
            self._canvas.yview_moveto((y1 - view_h) / inner_h)
