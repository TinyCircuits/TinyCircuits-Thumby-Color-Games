# Template for a new ChipPlayer format module. Copy to formats/<yourformat>.py,
# implement load()/render(), then register the file's magic bytes in
# main.py detect_format() and dispatch to this Player.
#
# Contract:
#   Player().load(buf)        parse the raw file bytes; raise ValueError if invalid
#   Player().render(out, n)   fill out[0:n] (array('h'), signed-16 mono PCM), return n
#   Player().meta             dict: {'title', 'channels', 'order_len'} (for the UI)
#   Player().done             set True when the song has played through once
#   Player().order_pos        current position (0..order_len) for the progress bar
#
# For real-time on-device playback, write the per-sample inner loop with
# @micropython.viper (see formats/mod.py and main.py's mix_out). A plain-Python
# render() still works for host-side rendering / testing via a small WAV driver.

class Player:
    def __init__(self, sr=11025):
        self.sr = sr
        self.done = False
        self.order_pos = 0
        self.meta = {'title': '', 'channels': 1, 'order_len': 1}

    def load(self, buf):
        # Parse `buf` (a bytes/bytearray). Populate self.meta and any state your
        # synthesis needs. Raise ValueError on a file you can't handle.
        raise NotImplementedError

    def render(self, out, n):
        # Fill out[0:n] with signed-16 mono PCM for this block and return the count.
        # Advance your sequencer/synth by n samples. Set self.done = True at the end.
        for i in range(n):
            out[i] = 0
        return n
