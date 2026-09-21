# ChipPlayer - a chiptune module player for Thumby Color.
# Browser + transport UI (engine draw/input) + real-time MOD playback
# (ModPlayer sequencer -> viper mixer -> Pin23 PWM DAC).
#
# Format modules live in formats/ and expose a common contract (see mod.py):
#   ModPlayer(sr).load(buf); .step_tick(); .spt; .chans; .meta; .done
# To add a new chiptune format (AY/YM, VGM, ...), write formats/<fmt>.py with the
# same interface and register its magic bytes in detect_format() below.
import engine_main, engine, engine_draw, engine_io, framebuf, time, gc, os
from array import array
from machine import Pin, PWM
import sys
APP_DIR = '/Games/ChipPlayer'
try:                                   # ensure this folder is importable
    _d = __file__.rsplit('/', 1)[0]
    APP_DIR = _d
    if _d not in sys.path:
        sys.path.insert(0, _d)
except Exception:
    pass
from mod import ModPlayer

# ---------- display ----------
# The engine double-buffers: back_fb_data() returns the CURRENT back buffer, which
# alternates each frame. Wrap it fresh every draw so we paint the buffer about to
# be presented (capturing it once causes flashing / half-blank frames).
def _fb():
    return framebuf.FrameBuffer(engine_draw.back_fb_data(), 128, 128, framebuf.RGB565)
def rgb(r, g, b):
    return ((r >> 3) << 11) | ((g >> 2) << 5) | (b >> 3)
BG   = rgb(12, 14, 28);  PANEL = rgb(28, 32, 56); FG = rgb(232, 234, 244)
DIM  = rgb(120, 126, 158); HL = rgb(255, 202, 0); ACC = rgb(90, 200, 255)
OKC  = rgb(90, 220, 120); SELBG = rgb(48, 80, 140)

MUSIC_DIR = '/Music'
SONGS_DIR = APP_DIR + '/songs'         # bundled demo modules ship here

def detect_format(path):
    # magic-byte dispatch; extend here for more formats
    try:
        with open(path, 'rb') as f:
            head = f.read(1084)
    except OSError:
        return None
    if len(head) >= 1084 and head[1080:1084] in (b'M.K.', b'M!K!', b'FLT4', b'4CHN', b'6CHN', b'8CHN'):
        return 'MOD'
    if head[:4] == b'Vgm ':
        return 'VGM'      # not yet implemented
    if head[:4] == b'ZXAY':
        return 'AY'       # not yet implemented
    return None

def list_music():
    # scan /Music and the app's bundled songs/, dedupe by name -> [(name, path), ...]
    seen = set(); out = []
    for d in (MUSIC_DIR, SONGS_DIR):
        try:
            fs = os.listdir(d)
        except OSError:
            continue
        for f in fs:
            lf = f.lower()
            if (lf.endswith('.mod') or lf.endswith('.vgm') or lf.endswith('.ay')) and f not in seen:
                seen.add(f)
                out.append((f, d + '/' + f))
    out.sort(key=lambda t: t[0].lower())
    return out

def trunc(s, n):
    return s if len(s) <= n else s[:n - 1] + '~'

def mmss(sec):
    return '%d:%02d' % (sec // 60, sec % 60)

# ---------- audio engine ----------
SR = 11025
DELAY = 1000000 // SR
setw = None            # bound PWM.duty_u16, referenced by the viper mixer

@micropython.viper
def mix_out(pool: ptr8, cs: ptr32, nch: int, n: int, delay: int, next_time: int) -> int:
    i = 0
    while i < n:
        cur = int(time.ticks_us())
        while int(time.ticks_diff(next_time, cur)) > 0:
            cur = int(time.ticks_us())
        acc = 0
        c = 0
        while c < nch:
            b = c << 3
            fl = int(cs[b + 7])
            if fl & 1:
                pos = int(cs[b + 4])
                idx = pos >> 16
                le = int(cs[b + 3])
                if idx >= le:
                    if fl & 2:
                        pos = pos - ((le - int(cs[b + 2])) << 16)
                        idx = pos >> 16
                    else:
                        cs[b + 7] = 0
                        idx = -1
                if idx >= 0:
                    d = int(pool[int(cs[b + 0]) + idx])
                    if d > 127:
                        d = d - 256
                    acc = acc + d * int(cs[b + 6])
                    cs[b + 4] = pos + int(cs[b + 5])
            c += 1
        o = acc + 32768
        if o < 0:
            o = 0
        elif o > 65535:
            o = 65535
        setw(o)
        next_time = int(time.ticks_add(next_time, delay))
        i += 1
    return next_time

class Player:
    def __init__(self, path):
        buf = open(path, 'rb').read()
        self.raw = buf                     # resident: notes + sample PCM read from here
        self.p = ModPlayer(sr=SR, lean=True)
        self.p.load(buf)
        self.nch = self.p.nch
        self.soff = [0] * 32               # sample number -> absolute byte offset in raw
        for i, s in enumerate(self.p.samples):
            self.soff[i + 1] = s['offset']
        self.cs = array('i', [0] * (self.nch * 8))
        self.pwm = None
        self.played = 0                    # samples output so far
        self.total_sec = self._estimate_seconds()
        gc.collect()

    def _estimate_seconds(self):
        # MODs store no duration; dry-run the sequencer (silent) to one full pass,
        # with loop detection so modules that jump back don't run forever.
        try:
            t = ModPlayer(sr=SR, lean=True)
            t.load(self.raw)
            total = 0; seen = {}; guard = 0
            while not t.done and guard < 20000:
                if t.tickn == 0 and t.row == 0:
                    if t.order_pos in seen:
                        break
                    seen[t.order_pos] = 1
                t.step_tick()
                total += t.spt
                guard += 1
            return total // SR
        except Exception:
            return 0

    def start(self):
        global setw
        self.pwm = PWM(Pin(23), freq=120000)
        setw = self.pwm.duty_u16
        self.next_time = time.ticks_us()

    def _sync(self):
        cs = self.cs; off = self.soff
        for c in range(self.nch):
            ch = self.p.chans[c]; b = c * 8
            if ch.trig:
                cs[b + 0] = off[ch.sample]
                cs[b + 1] = ch.length
                cs[b + 2] = ch.loop_start
                cs[b + 3] = ch.loop_end
                cs[b + 4] = ch.start_offset
                cs[b + 5] = ch.inc
                cs[b + 6] = ch.outvol
                cs[b + 7] = 1 | (2 if ch.loop_len > 2 else 0)
                ch.trig = False
            else:
                cs[b + 5] = ch.inc
                cs[b + 6] = ch.outvol

    def pump(self):
        if self.p.done:
            return False
        self.p.step_tick()
        self._sync()
        self.next_time = mix_out(self.raw, self.cs, self.nch, self.p.spt, DELAY, self.next_time)
        self.played += self.p.spt
        return True

    def stop(self):
        try:
            if self.pwm:
                setw(0)
                self.pwm.deinit()
        except Exception:
            pass
        self.pwm = None

# ---------- screens ----------
def draw_browser(files, sel, top):
    fb = _fb()
    fb.fill(BG)
    fb.fill_rect(0, 0, 128, 13, PANEL)
    fb.text('ChipPlayer', 4, 3, ACC)
    if not files:
        fb.text('No modules in', 6, 50, DIM)
        fb.text('/Music', 30, 62, DIM)
        fb.text('Copy .mod files', 4, 90, DIM)
        return
    rows = 9
    y = 18
    for i in range(top, min(top + rows, len(files))):
        name = trunc(files[i][0], 15)
        if i == sel:
            fb.fill_rect(2, y - 2, 124, 11, SELBG)
            fb.text('>', 4, y, HL)
            fb.text(name, 14, y, FG)
        else:
            fb.text(name, 14, y, DIM)
        y += 11
    fb.fill_rect(0, 116, 128, 12, PANEL)
    fb.text('A play  ' + str(sel + 1) + '/' + str(len(files)), 4, 118, FG)

def draw_now_playing(fname, pl):
    fb = _fb()
    fb.fill(BG)
    fb.fill_rect(0, 0, 128, 13, PANEL)
    fb.text('Now Playing', 4, 3, OKC)
    fb.text(trunc(fname, 16), 4, 20, FG)
    m = pl.p.meta
    fb.text(trunc(m['title'], 16), 4, 34, ACC)
    fb.text(str(m['channels']) + 'ch  ' + str(SR // 1000) + 'kHz', 4, 48, DIM)
    # time position / duration
    el = pl.played // SR
    tot = pl.total_sec
    fb.text(mmss(el) + ' / ' + (mmss(tot) if tot else '?:??'), 4, 64, FG)
    if tot > 0:
        w = (el * 120) // tot
        if w > 120:
            w = 120
    else:
        olen = m['order_len'] or 1
        p = pl.p.order_pos
        w = ((olen if p > olen else p) * 120) // olen
    fb.rect(4, 78, 120, 8, DIM)
    fb.fill_rect(4, 78, w, 8, OKC)
    fb.text('pat ' + str(pl.p.order_pos + 1) + '/' + str(m['order_len']), 4, 94, DIM)
    fb.fill_rect(0, 116, 128, 12, PANEL)
    fb.text('B = stop', 4, 118, FG)

def play_file(path, fname):
    fb = _fb(); fb.fill(BG); fb.fill_rect(0, 0, 128, 13, PANEL)
    fb.text('ChipPlayer', 4, 3, ACC); fb.text('Loading...', 4, 50, FG)
    fb.text(trunc(fname, 16), 4, 66, DIM)
    engine.tick()
    try:
        pl = Player(path)
    except Exception as e:
        fb = _fb(); fb.fill(BG); fb.text('load error:', 4, 40, HL); fb.text(trunc(str(e), 16), 4, 54, DIM)
        engine.tick(); time.sleep_ms(1200)
        return 'stopped'
    pl.start()
    draw_now_playing(fname, pl); engine.tick()
    reason = 'ended'
    while True:
        if not pl.pump():          # song finished
            reason = 'ended'
            break
        if engine.tick():
            if engine_io.B.is_just_pressed:
                reason = 'stopped'
                break
            draw_now_playing(fname, pl)
    pl.stop()
    del pl
    gc.collect()
    return reason

# ---------- main ----------
def main():
    engine.fps_limit(30)
    files = list_music()
    sel = 0; top = 0; rows = 9
    while True:
        if engine.tick():
            if files:
                if engine_io.DOWN.is_just_pressed and sel < len(files) - 1:
                    sel += 1
                if engine_io.UP.is_just_pressed and sel > 0:
                    sel -= 1
                if sel < top:
                    top = sel
                elif sel >= top + rows:
                    top = sel - rows + 1
                if engine_io.A.is_just_pressed:
                    while True:                       # auto-advance to next on end
                        r = play_file(files[sel][1], files[sel][0])
                        if r == 'ended' and sel < len(files) - 1:
                            sel += 1
                            if sel >= top + rows:
                                top = sel - rows + 1
                            continue
                        break
            else:
                if engine_io.A.is_just_pressed:
                    files = list_music()
            draw_browser(files, sel, top)

main()
