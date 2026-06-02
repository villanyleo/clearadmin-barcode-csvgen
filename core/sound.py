"""
Audio feedback for scan results.

Tones are generated with winsound (Windows stdlib) so there are no audio files
to bundle and the pitch/length is fully tunable. Playback runs on a daemon
thread so rapid scanning never blocks the UI. On non-Windows platforms (e.g.
development on macOS) playback is a silent no-op.
"""
import threading

try:
    import winsound
    _HAS_WINSOUND = True
except ImportError:  # not on Windows
    _HAS_WINSOUND = False


# Short, bright, unobtrusive — heard on every successful scan, so it stays brief.
_SUCCESS = [(1000, 70)]

# Lower, descending two-tone buzz — rare and deliberately attention-grabbing.
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
