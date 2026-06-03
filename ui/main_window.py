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
from ui.product_table import ProductTable


class MainWindow(tk.Tk):
    # Az utolsó beolvasás állapotszínei (alsó sor szövege).
    COLOR_SUCCESS = "#1a7f37"  # zöld szöveg
    COLOR_ERROR = "#cf222e"    # piros szöveg
    COLOR_ROW_HIGHLIGHT = "#d4f4d7"  # világoszöld sorháttér az utolsó beolvasáshoz

    # Kiemelőszín az aktív fül aláhúzásához (Windows 11 alap kék).
    COLOR_ACCENT = "#0067c0"

    # Tartalék jelek, csak akkor, ha a PNG ikonok nem tölthetők be.
    FALLBACK_EDIT = "✎"
    FALLBACK_DELETE = "🗑"

    # Beviteli mezők osztályai, amelyeknek el kell kapniuk a billentyűket a
    # normál gépeléshez, hogy az olvasókezelő ne nyelje le (pl. átnevező ablak).
    _TEXT_ENTRY_CLASSES = {"Entry", "TEntry", "TCombobox", "Text", "Spinbox"}

    def __init__(self):
        super().__init__()
        self.title("ClearAdmin CSV vonalkód olvasó")
        self.geometry("980x600")
        self.minsize(820, 420)
        self._set_app_icon()

        self.style = ttk.Style(self)
        self._configure_styles()
        # A natív téma keret-háttérszíne, hogy a fülkonténereink és az inaktív
        # aláhúzások zökkenőmentesen illeszkedjenek.
        self._tab_bg = self._safe_color(
            self.style.lookup("TFrame", "background"), "#f0f0f0"
        )

        self._manager = SessionManager()
        self._input_buffer: list[str] = []
        # CSV-ből betöltött termékkatalógus (minden munkamenet közös; None, amíg nincs betöltve).
        self._catalog: Catalog | None = None
        self._csv_path: str | None = None  # legutóbb megnyitott CSV, indítások között megjegyezve
        self._price_var = tk.StringVar()
        self._icons = self._load_icons()

        self._build_ui()
        self._bind_scanner_input()

        # Az előző futás munkameneteinek és CSV-jének visszatöltése, vagy új kezdés.
        if not self._restore_state():
            self._manager.start_session()
        self._on_session_changed()

        # Mindent elment, amikor az ablak bezárul.
        self.protocol("WM_DELETE_WINDOW", self._on_close)

    # ------------------------------------------------------------------ #
    #  Stílusok / erőforrások                                              #
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
                self.winfo_rgb(color)  # TclError-t dob, ha nem használható szín
                return color
        except tk.TclError:
            pass
        return fallback

    def _asset_path(self, name: str) -> str:
        # PyInstaller-rel csomagolva az erőforrások a sys._MEIPASS alatt vannak kicsomagolva.
        base = getattr(sys, "_MEIPASS", None) or os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        return os.path.join(base, "assets", name)

    def _load_icons(self) -> dict:
        icons = {}
        for key, fname in (("edit", "edit.png"), ("delete", "delete_red.png")):
            try:
                icons[key] = tk.PhotoImage(file=self._asset_path(fname))
            except tk.TclError:
                pass  # visszaesés szöveges jelre
        return icons

    def _set_app_icon(self):
        try:
            self._app_icon = tk.PhotoImage(file=self._asset_path("icon.png"))
            self.iconphoto(True, self._app_icon)
        except tk.TclError:
            pass

    # ------------------------------------------------------------------ #
    #  Felület felépítése                                                  #
    # ------------------------------------------------------------------ #

    def _build_ui(self):
        # ── Felső eszköztár ──────────────────────────────────────────────
        toolbar = ttk.Frame(self, padding=(8, 6))
        toolbar.pack(side=tk.TOP, fill=tk.X)

        self._btn_start = ttk.Button(
            toolbar, text="Új munkamenet", command=self._on_start_session
        )
        self._btn_start.pack(side=tk.LEFT, padx=(0, 6))

        self._btn_export = ttk.Button(
            toolbar, text="Mentés", command=self._on_export
        )
        self._btn_export.pack(side=tk.LEFT)

        self._status_var = tk.StringVar(value="")
        ttk.Label(toolbar, textvariable=self._status_var, anchor=tk.W).pack(
            side=tk.LEFT, padx=16
        )

        # ── Jobb oldal: CSV katalógus + árlista választó ─────────────────
        # Jobbról balra pakolva, így a vizuális sorrend: [Árlista betöltése…] [Ár:] [▾]
        self._price_combo = ttk.Combobox(
            toolbar, textvariable=self._price_var, state="disabled", width=14
        )
        self._price_combo.bind("<<ComboboxSelected>>", self._on_price_change)
        self._price_combo.pack(side=tk.RIGHT, padx=(4, 0))

        ttk.Label(toolbar, text="Ár:").pack(side=tk.RIGHT, padx=(12, 4))

        self._btn_load = ttk.Button(
            toolbar, text="Árlista betöltése…", command=self._on_load_csv
        )
        self._btn_load.pack(side=tk.RIGHT)

        # ── Munkamenet fülsor (mindig látható; munkamenetenként egy fül) ─
        self._tab_bar = tk.Frame(self, bg=self._tab_bg)
        self._tab_bar.pack(side=tk.TOP, fill=tk.X)

        # ── Szerkeszthető terméktáblázat ─────────────────────────────────
        table_frame = ttk.Frame(self, padding=(8, 6, 8, 8))
        table_frame.pack(side=tk.TOP, fill=tk.BOTH, expand=True)
        self._table = ProductTable(
            table_frame,
            on_increment=self._on_increment,
            on_decrement=self._on_decrement,
            on_delete=self._on_delete_product,
            delete_icon=self._icons.get("delete"),
            delete_fallback=self.FALLBACK_DELETE,
        )
        self._table.pack(fill=tk.BOTH, expand=True)

        # ── Alsó állapotsor (utolsó beolvasás eredménye) ─────────────────
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
    #  Fülsor                                                              #
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

            # A kiemelő aláhúzás jelöli az aktív fület (Windows 11 stílus).
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
    #  Olvasó bemenetének kezelése                                         #
    # ------------------------------------------------------------------ #

    def _bind_scanner_input(self):
        """Minden billentyűleütés elkapása, függetlenül attól, melyik elemen van a fókusz."""
        self.bind_all("<Key>", self._on_key)

    def _on_key(self, event):
        # Engedi a normál gépelést, ha beviteli mező (pl. az átnevező ablak) van fókuszban.
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
        """Beolvasott kód ellenőrzése, majd hangos + vizuális visszajelzés."""
        if is_valid_ean13(code):
            self._register_barcode(code)
            self._set_scan_status(f"{code} beolvasva", success=True)
            sound.play_success()
        else:
            self._set_scan_status(f"{code} nem EAN-kód", success=False)
            sound.play_error()

    def _register_barcode(self, value: str):
        entry = self._manager.add_barcode(value)
        if entry is None:
            return
        count = self._manager.current.count_for(value)
        name, price = self._catalog_fields(value)
        self._table.upsert(value, name, count, price, entry.timestamp.strftime("%H:%M:%S"))
        self._table.highlight(value)
        self._refresh_status()

    def _catalog_fields(self, value: str) -> tuple[str, str]:
        """A *value* (name, price) párját adja a betöltött katalógusból, vagy üreset."""
        if self._catalog is None:
            return "", ""
        product = self._catalog.get(value)
        if product is None:
            return "", ""
        return product.name, product.prices.get(self._price_var.get(), "")

    # -- beágyazott mennyiség / termék szerkesztése --------------------- #

    def _on_increment(self, value: str):
        session = self._manager.current
        if session is None:
            return
        session.increment(value)
        self._table.set_count(value, session.count_for(value))
        self._refresh_status()

    def _on_decrement(self, value: str):
        session = self._manager.current
        if session is None:
            return
        session.decrement(value)
        self._table.set_count(value, session.count_for(value))
        self._refresh_status()

    def _on_delete_product(self, value: str):
        session = self._manager.current
        if session is None:
            return
        if not messagebox.askyesno(
            "Termék törlése", "Eltávolítható ez a termék a munkamenetből?"
        ):
            return
        session.remove_product(value)
        self._table.remove(value)
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  Munkamenet / fül visszahívások                                      #
    # ------------------------------------------------------------------ #

    def _restore_state(self) -> bool:
        """Visszatölti az előző futás munkameneteit + CSV-jét. True, ha visszaállt valami."""
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
                    self._catalog = None  # a fájl módosult/olvashatatlan — folytatás nélküle
        except Exception:
            # Sérült/inkompatibilis állapot — inkább új kezdés, mint összeomlás.
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
            "Munkamenet átnevezése", "Munkamenet neve:",
            initialvalue=session.name, parent=self,
        )
        if new_name is not None and new_name.strip():
            session.name = new_name.strip()
            self._rebuild_tab_bar()
            self._refresh_status()

    def _on_delete_session(self, session: Session):
        if session.entries and not messagebox.askyesno(
            "Munkamenet törlése",
            f"Törölhető a(z) „{session.name}” és a benne lévő "
            f"{session.count} beolvasott tétel?",
        ):
            return
        self._manager.delete_session(session)
        if self._manager.current is None:
            # Soha ne maradjon nulla munkamenet — a fülsor maradjon kitöltve.
            self._manager.start_session()
        self._scan_status_var.set("")
        self._on_session_changed()

    def _on_export(self):
        session = self._manager.current
        if session is None or session.count == 0:
            messagebox.showinfo(
                "Exportálás", "Ebben a munkamenetben nincs exportálható tétel."
            )
            return

        # A sorok a táblázattal azonos sorrendben: (name, price, quantity).
        rows = []
        unmatched = 0
        for value, count, _last_ts in session.aggregated():
            name, price = self._catalog_fields(value)
            if not name:
                unmatched += 1
                name = value  # visszaesés a vonalkódra, hogy a tétel azonosítható maradjon
            rows.append((name, price, count))

        if unmatched and not messagebox.askokcancel(
            "Exportálás",
            f"{unmatched} / {len(rows)} tétel nincs a betöltött terméklistában.\n"
            f"Ezek a vonalkóddal, ár nélkül kerülnek exportálásra.\n\n"
            f"Folytatja?",
        ):
            return

        path = filedialog.asksaveasfilename(
            title="Munkamenet exportálása",
            defaultextension=".csv",
            initialfile=f"{session.name}.csv",
            filetypes=[("CSV fájlok", "*.csv"), ("Minden fájl", "*.*")],
        )
        if not path:
            return

        try:
            export.write_export(path, rows)
        except Exception as exc:
            messagebox.showerror(
                "Sikertelen exportálás", f"A fájl írása nem sikerült:\n\n{exc}"
            )
            return

        # A munkamenet szándékosan érintetlen marad, hogy később még szerkeszthető legyen.
        self._set_scan_status(
            f"{len(rows)} tétel exportálva ide: {os.path.basename(path)}",
            success=True,
        )

    def _on_session_changed(self):
        """A teljes felület szinkronizálása az éppen aktív munkamenethez."""
        self._rebuild_tab_bar()
        session = self._manager.current
        if session is None:
            self._clear_table()
            self._refresh_status()
            return

        # A munkamenet árlistája az elsőre áll, ha van betöltött katalógus.
        if self._catalog and not session.price_type and self._catalog.price_names:
            session.price_type = self._catalog.price_names[0]
        self._price_var.set(session.price_type or "")

        self._populate_table_from_session(session)
        self._refresh_status()

    # ------------------------------------------------------------------ #
    #  CSV katalógus visszahívások                                         #
    # ------------------------------------------------------------------ #

    def _on_load_csv(self):
        path = filedialog.askopenfilename(
            title="Termék CSV kiválasztása",
            filetypes=[("CSV fájlok", "*.csv"), ("Minden fájl", "*.*")],
        )
        if not path:
            return
        try:
            catalog = load_catalog(path)
        except Exception as exc:
            messagebox.showerror(
                "A CSV nem tölthető be", f"A fájl beolvasása nem sikerült:\n\n{exc}"
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
            f"{len(catalog)} termék betöltve innen: {os.path.basename(path)}",
            success=True,
        )

    def _on_price_change(self, event=None):
        # A kiválasztott árlista az aktív munkamenethez tartozik.
        session = self._manager.current
        if session is not None:
            session.price_type = self._price_var.get()
        self._refresh_catalog_columns()

    def _refresh_catalog_columns(self):
        """Minden sor Terméknév és Ár cellájának frissítése a betöltött katalógusból."""
        if self._catalog is None:
            return
        for value in self._table.values():
            name, price = self._catalog_fields(value)
            self._table.update_cells(value, name, price)

    # ------------------------------------------------------------------ #
    #  Segédfüggvények                                                     #
    # ------------------------------------------------------------------ #

    def _clear_table(self):
        self._table.clear()

    def _populate_table_from_session(self, session: Session):
        """A táblázat újraépítése a *session* beolvasásaival (fülváltáskor használt)."""
        rows = []
        for value, count, last_ts in session.aggregated():
            name, price = self._catalog_fields(value)
            rows.append({
                "value": value,
                "name": name,
                "count": count,
                "price": price,
                "time": last_ts.strftime("%H:%M:%S"),
            })
        self._table.set_rows(rows)

        last = session.last_value()
        if last is not None:
            self._table.highlight(last)

    def _set_scan_status(self, text: str, success: bool):
        """Az utolsó beolvasás eredménye az alsó sorban, színkóddal."""
        self._scan_status_var.set(text)
        self._scan_status_lbl.configure(
            foreground=self.COLOR_SUCCESS if success else self.COLOR_ERROR
        )

    def _refresh_status(self):
        session = self._manager.current
        if session is None:
            self._status_var.set("Nincs aktív munkamenet")
            return
        started = session.started_at.strftime("%H:%M:%S")
        text = f"{session.name}  —  kezdés {started}   ·   {session.count} beolvasva"
        n = len(self._manager.sessions)
        if n > 1:
            text += f"   ({n} nyitott munkamenet)"
        self._status_var.set(text)
