"""
Hangos visszajelzés a beolvasás eredményéről.

A hangokat a winsound (Windows beépített modul) állítja elő, így nincs
becsomagolandó hangfájl, a magasság és a hossz pedig szabadon hangolható. A
lejátszás daemon szálon fut, így a gyors beolvasás soha nem akasztja meg a
felületet. Nem Windows rendszereken (pl. macOS fejlesztés alatt) a lejátszás
csendben nem csinál semmit.
"""
import threading

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:  # nem Windows rendszeren
    _HAS_WINSOUND = False


# Rövid, magas, nem zavaró — minden sikeres beolvasásnál hallható, ezért rövid.
_SUCCESS = [(1000, 70)]

# Mélyebb, leszálló kéthangú zümmögés — ritka és szándékosan figyelemfelkeltő.
_ERROR = [(400, 150), (250, 150)]


def _play(sequence):
    if not _HAS_WINSOUND:
        return
    for frequency, duration in sequence:
        winsound.Beep(frequency, duration)


def _play_async(sequence):
    threading.Thread(target=_play, args=(sequence,), daemon=True).start()


def play_success():
    _play_async(_SUCCESS)


def play_error():
    _play_async(_ERROR)
