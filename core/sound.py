"""
Csipogó visszajelzés a beolvasás eredményéről

A hangokat a winsound (Windows beépített modul) állítja elő, a magasság állítható,
nincs szükség külső hangfájlra.
A lejátszás daemon szálon fut, a beolvasás nem akasztja meg a
felületet. Nem Windows rendszereken (MacOS, Linux) jelenleg nincs hang.
"""
import threading

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:  # nem Windows rendszeren
    _HAS_WINSOUND = False


# Rövid, magas csipp (sikeres olvasás)
_SUCCESS = [(1000, 70)]

# Mélyebb, hosszabb csipp (hiba esetén)
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
