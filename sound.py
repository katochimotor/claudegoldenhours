"""Sound notifications via winsound (no external audio files needed)."""

import threading
import winsound

# Ascending C-E-G arpeggio — "golden hours started"
GOLDEN_CHIME = [(523, 120), (659, 120), (784, 280)]
# Descending G-E-C — "peak hours started"
PEAK_CHIME   = [(784, 120), (659, 120), (523, 280)]
# Soft double-beep for promo end
INACTIVE_CHIME = [(440, 200), (330, 350)]


def _play(sequence: list[tuple[int, int]]) -> None:
    for freq, ms in sequence:
        try:
            winsound.Beep(freq, ms)
        except Exception:
            pass


def play_transition(state: str, enabled: bool = True) -> None:
    if not enabled:
        return
    seq = {
        "golden":   GOLDEN_CHIME,
        "peak":     PEAK_CHIME,
        "inactive": INACTIVE_CHIME,
    }.get(state, [])
    if seq:
        threading.Thread(target=_play, args=(seq,), daemon=True).start()
