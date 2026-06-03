"""
A fülsorban használt PNG ikonok (szerkesztés / törlés) előállítása.

Futtasd egyszer, miután megváltozott az ikonok kinézete:
    venv/bin/python tools/gen_icons.py

A Pillow csak itt, az előállításkor kell — az alkalmazás a kész PNG-ket a
tkinter.PhotoImage-dzsel tölti be, és futásidőben nem függ a Pillow-tól.
"""
import os

from PIL import Image, ImageDraw

OUT_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets")
COLOR = (60, 60, 60, 255)        # sötétszürke vonalak, natív hatás a világos füleken
COLOR_RED = (207, 34, 46, 255)   # #cf222e — piros törlés/kuka
SS = 16                          # túlmintavételezési tényező a sima élekért


def _canvas(size):
    img = Image.new("RGBA", (size * SS, size * SS), (0, 0, 0, 0))
    return img, ImageDraw.Draw(img)


def _save(img, size, name):
    os.makedirs(OUT_DIR, exist_ok=True)
    img.resize((size, size), Image.LANCZOS).save(os.path.join(OUT_DIR, name))


def draw_edit(size, name):
    """Átlós ceruza (Fluent „szerkesztés” stílus)."""
    img, d = _canvas(size)
    u = size * SS / 20.0   # 20 egységes rácsban dolgozunk
    w = 2.4 * u            # a ceruza fél szélessége

    ax, ay = 15.5 * u, 4.5 * u    # radíros vég (jobb felső)
    bx, by = 4.5 * u, 15.5 * u    # hegy (bal alsó)
    dx, dy = bx - ax, by - ay
    length = (dx * dx + dy * dy) ** 0.5
    dx, dy = dx / length, dy / length
    px, py = -dy, dx              # unit perpendicular

    cx, cy = ax + 0.78 * (bx - ax), ay + 0.78 * (by - ay)  # ahol a hegy kúpja kezdődik

    d.polygon(
        [
            (ax + px * w, ay + py * w),
            (ax - px * w, ay - py * w),
            (cx - px * w, cy - py * w),
            (cx + px * w, cy + py * w),
        ],
        fill=COLOR,
    )
    d.polygon(
        [(cx + px * w, cy + py * w), (cx - px * w, cy - py * w), (bx, by)],
        fill=COLOR,
    )
    # Fémgyűrű a radír közelében, átlátszó résként kivágva.
    fx, fy = ax + 0.22 * (bx - ax), ay + 0.22 * (by - ay)
    d.line(
        [(fx + px * w, fy + py * w), (fx - px * w, fy - py * w)],
        fill=(0, 0, 0, 0),
        width=int(1.4 * u),
    )
    _save(img, size, name)


def draw_delete(size, name, color=COLOR):
    """Körvonalas kuka (Fluent „törlés” stílus)."""
    img, d = _canvas(size)
    u = size * SS / 20.0
    width = int(1.7 * u)

    def line(p0, p1):
        d.line([(p0[0] * u, p0[1] * u), (p1[0] * u, p1[1] * u)], fill=color, width=width)

    line((3, 5.3), (17, 5.3))          # fedő
    line((8, 5.3), (8.4, 3.4))         # fogantyú
    line((8.4, 3.4), (11.6, 3.4))
    line((11.6, 3.4), (12, 5.3))
    line((4.7, 6.2), (6.0, 16.6))      # a kuka oldalai + alja
    line((15.3, 6.2), (14.0, 16.6))
    line((6.0, 16.6), (14.0, 16.6))
    line((8.0, 8.0), (8.3, 15.0))      # belső függőleges vonalak
    line((10.0, 8.0), (10.0, 15.0))
    line((12.0, 8.0), (11.7, 15.0))

    # A vonalvégek lekerekítése.
    r = width / 2
    for (x, y) in [(3, 5.3), (17, 5.3), (6.0, 16.6), (14.0, 16.6)]:
        d.ellipse([x * u - r, y * u - r, x * u + r, y * u + r], fill=color)

    _save(img, size, name)


def build_app_ico():
    """Az assets/icon.ico (több méret) előállítása az assets/icon.png-ből az .exe/telepítőhöz."""
    src = os.path.join(OUT_DIR, "icon.png")
    if not os.path.exists(src):
        return
    img = Image.open(src).convert("RGBA")
    sizes = [(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)]
    img.save(os.path.join(OUT_DIR, "icon.ico"), sizes=sizes)


if __name__ == "__main__":
    draw_edit(18, "edit.png")
    draw_edit(36, "edit@2x.png")
    draw_delete(18, "delete_red.png", COLOR_RED)
    draw_delete(36, "delete_red@2x.png", COLOR_RED)
    build_app_ico()
    print(f"Icons written to {OUT_DIR}")
