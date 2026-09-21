# MOD format plugin for ChipPlayer.
# Sequencer + 4..N channel sample mixer implementing the shared render() interface:
#   load(buf)                -> parse & init
#   render(out_i16, n)       -> fill n signed-16 PCM frames (mono), return frames written
#   meta                     -> {'title','channels','order_len',...}
#   done                     -> True after one full pass through the order list
#
# Pure-integer (MicroPython-safe: uses // not /). The per-sample mix loop is written
# plainly here for host verification; on-device it gets a @micropython.viper twin.
try:
    from .mod_parser import parse_mod
except ImportError:
    from mod_parser import parse_mod

PAL_CLOCK = 7093789          # Amiga PAL Paula clock: rate = PAL_CLOCK // (period*2)

class Channel:
    __slots__ = ('data', 'length', 'loop_start', 'loop_len', 'loop_end',
                 'pos', 'inc', 'vol', 'outvol', 'period', 'sample', 'on',
                 'arp_note', 'trig', 'start_offset', 'fx', 'fxparam',
                 'porta_target', 'porta_speed',
                 'vib_speed', 'vib_depth', 'vib_pos',
                 'trem_speed', 'trem_depth', 'trem_pos')
    def __init__(self):
        self.data = None; self.length = 0; self.loop_start = 0; self.loop_len = 0
        self.loop_end = 0; self.pos = 0; self.inc = 0; self.vol = 0; self.outvol = 0
        self.period = 0; self.sample = 0; self.on = False; self.arp_note = 0
        self.trig = False; self.start_offset = 0; self.fx = 0; self.fxparam = 0
        self.porta_target = 0; self.porta_speed = 0
        self.vib_speed = 0; self.vib_depth = 0; self.vib_pos = 0
        self.trem_speed = 0; self.trem_depth = 0; self.trem_pos = 0

class ModPlayer:
    def __init__(self, sr=22050, lean=False):
        self.sr = sr
        self.lean = lean          # lean=True: don't pre-decode patterns (low RAM)

    def load(self, buf):
        m = parse_mod(buf, decode_patterns=not self.lean)
        self.m = m
        self.samples = m['samples']
        self.order = m['order']
        self.patterns = m['patterns']
        self.nch = m['num_channels']
        if self.lean:
            self.raw = buf
            self.pat_off = m['pattern_offset']
            self.row_bytes = self.nch * 4
            self.pat_bytes = 64 * self.row_bytes
        self.chans = [Channel() for _ in range(self.nch)]
        self.speed = 6                # ticks per row
        self.set_bpm(125)
        self.order_pos = 0
        self.row = 0
        self.tickn = 0
        self.samples_left = 0         # output samples until next tick
        self.done = False
        self._pending_jump = -1       # Bxx target order
        self._pending_break = -1      # Dxx target row
        self.meta = {'title': m['title'], 'channels': self.nch,
                     'order_len': m['song_length'], 'patterns': m['num_patterns']}
        return self

    def set_bpm(self, bpm):
        self.bpm = bpm
        # tick rate = bpm*2/5 Hz  -> samples per tick
        self.spt = (self.sr * 5) // (bpm * 2)

    def _period_inc(self, period):
        if period <= 0:
            return 0
        rate = PAL_CLOCK // (period * 2)          # sample-playback rate (Hz)
        return (rate << 16) // self.sr            # 16.16 step through sample per out-frame

    def _rowdata(self):
        if not self.lean:
            return self.patterns[self.order[self.order_pos]][self.row]
        raw = self.raw
        base = self.pat_off + self.order[self.order_pos] * self.pat_bytes + self.row * self.row_bytes
        out = []
        for c in range(self.nch):
            o = base + c * 4
            b0 = raw[o]; b1 = raw[o + 1]; b2 = raw[o + 2]; b3 = raw[o + 3]
            out.append(((b0 & 0xF0) | (b2 >> 4), ((b0 & 0x0F) << 8) | b1, b2 & 0x0F, b3))
        return out

    def _row(self):
        rowdata = self._rowdata()
        for c in range(self.nch):
            sample, period, effect, param = rowdata[c]
            ch = self.chans[c]
            ch.fx = effect; ch.fxparam = param
            porta = (effect == 0x3 or effect == 0x5)   # tone porta: don't retrigger
            if sample:
                s = self.samples[sample - 1]
                ch.sample = sample
                ch.data = s['data']; ch.length = s['length']
                ch.loop_start = s['loop_start']; ch.loop_len = s['loop_len']
                ch.loop_end = (s['loop_start'] + s['loop_len']) if s['loop_len'] > 2 else s['length']
                ch.vol = s['volume']
            if period:
                if porta:
                    ch.porta_target = period
                else:
                    ch.period = period
                    ch.pos = 0; ch.start_offset = 0
                    ch.vib_pos = 0; ch.trem_pos = 0
                    if ch.length > 0:
                        ch.on = True
                    if effect == 0x9:                  # sample offset
                        ch.pos = (param * 256) << 16
                        ch.start_offset = ch.pos
                    ch.trig = True
            # tick-0 effect setup
            if effect == 0x0:
                ch.arp_note = 0
            elif effect == 0x3:
                if param: ch.porta_speed = param
            elif effect == 0x4:
                if param >> 4: ch.vib_speed = param >> 4
                if param & 0x0F: ch.vib_depth = param & 0x0F
            elif effect == 0x7:
                if param >> 4: ch.trem_speed = param >> 4
                if param & 0x0F: ch.trem_depth = param & 0x0F
            elif effect == 0xC:                        # set volume
                ch.vol = param if param <= 64 else 64
            elif effect == 0xF:                        # set speed / tempo
                if param < 0x20:
                    if param: self.speed = param
                else:
                    self.set_bpm(param)
            elif effect == 0xB:                        # position jump
                self._pending_jump = param
            elif effect == 0xD:                        # pattern break
                self._pending_break = (param >> 4) * 10 + (param & 0x0F)
            ch.outvol = ch.vol
            ch.inc = self._period_inc(ch.period)

    def _tick_fx(self):
        for ch in self.chans:
            ch.outvol = ch.vol
            fx = ch.fx; p = ch.fxparam
            if fx == 0x0:                      # arpeggio
                if p:
                    ch.arp_note = (ch.arp_note + 1) % 3
                    if ch.arp_note == 0:
                        ch.inc = self._period_inc(ch.period)
                    else:
                        semis = (p >> 4) if ch.arp_note == 1 else (p & 0x0F)
                        ch.inc = self._period_inc(_arp_period(ch.period, semis))
            elif fx == 0x1:                    # portamento up (period down)
                ch.period -= p
                if ch.period < 113: ch.period = 113
                ch.inc = self._period_inc(ch.period)
            elif fx == 0x2:                    # portamento down (period up)
                ch.period += p
                if ch.period > 856: ch.period = 856
                ch.inc = self._period_inc(ch.period)
            elif fx == 0x3:                    # tone portamento
                self._tone_porta(ch)
            elif fx == 0x5:                    # tone porta + volume slide
                self._tone_porta(ch); self._volslide(ch, p)
            elif fx == 0x4:                    # vibrato
                self._vibrato(ch)
            elif fx == 0x6:                    # vibrato + volume slide
                self._vibrato(ch); self._volslide(ch, p)
            elif fx == 0x7:                    # tremolo
                self._tremolo(ch)
            elif fx == 0xA:                    # volume slide
                self._volslide(ch, p)

    def _tone_porta(self, ch):
        t = ch.porta_target
        if t:
            if ch.period < t:
                ch.period += ch.porta_speed
                if ch.period > t: ch.period = t
            elif ch.period > t:
                ch.period -= ch.porta_speed
                if ch.period < t: ch.period = t
        ch.inc = self._period_inc(ch.period)

    def _vibrato(self, ch):
        ch.vib_pos = (ch.vib_pos + ch.vib_speed) & 63
        delta = (_SIN[ch.vib_pos & 31] * ch.vib_depth) >> 7
        if ch.vib_pos >= 32: delta = -delta
        ch.inc = self._period_inc(ch.period + delta)

    def _tremolo(self, ch):
        ch.trem_pos = (ch.trem_pos + ch.trem_speed) & 63
        delta = (_SIN[ch.trem_pos & 31] * ch.trem_depth) >> 6
        if ch.trem_pos >= 32: delta = -delta
        o = ch.vol + delta
        ch.outvol = 0 if o < 0 else (64 if o > 64 else o)

    def _volslide(self, ch, p):
        v = ch.vol + (p >> 4) - (p & 0x0F)
        ch.vol = 0 if v < 0 else (64 if v > 64 else v)
        ch.outvol = ch.vol

    def step_tick(self):
        if self.tickn == 0:
            self._row()
        else:
            self._tick_fx()
        self._advance()

    def _advance(self):
        self.tickn += 1
        if self.tickn >= self.speed:
            self.tickn = 0
            if self._pending_jump >= 0 or self._pending_break >= 0:
                nxt = self._pending_jump if self._pending_jump >= 0 else (self.order_pos + 1)
                self.row = self._pending_break if self._pending_break >= 0 else 0
                self._pending_jump = -1; self._pending_break = -1
                self.order_pos = nxt
            else:
                self.row += 1
                if self.row >= 64:
                    self.row = 0
                    self.order_pos += 1
            if self.order_pos >= self.meta['order_len']:
                self.order_pos = 0
                self.done = True

    def render(self, out, n):
        """Fill out[0:n] (array 'h', signed 16) with mixed mono PCM."""
        chans = self.chans
        i = 0
        while i < n:
            if self.samples_left <= 0:
                self.step_tick()
                self.samples_left = self.spt
            chunk = self.samples_left
            if chunk > n - i:
                chunk = n - i
            end = i + chunk
            while i < end:
                acc = 0
                for ch in chans:
                    if ch.on:
                        idx = ch.pos >> 16
                        if idx >= ch.loop_end:
                            if ch.loop_len > 2:
                                ch.pos -= ch.loop_len << 16
                                idx = ch.pos >> 16
                            else:
                                ch.on = False
                                continue
                        d = ch.data[idx]
                        if d > 127:
                            d -= 256
                        acc += d * ch.outvol
                        ch.pos += ch.inc
                if acc > 32767: acc = 32767
                elif acc < -32768: acc = -32768
                out[i] = acc
                i += 1
            self.samples_left -= chunk
        return n


# ProTracker vibrato/tremolo sine table (one hump, 0..255), indexed by pos & 31
_SIN = (0, 24, 49, 74, 97, 120, 141, 161, 180, 197, 212, 224, 235, 244, 250, 253,
        255, 253, 250, 244, 235, 224, 212, 197, 180, 161, 141, 120, 97, 74, 49, 24)

# arpeggio helper: raise pitch by `semis` semitones == divide period by 2^(semis/12)
_ARP = (4096, 3866, 3649, 3444, 3251, 3069, 2896, 2734, 2580, 2435, 2299, 2170, 2048)
def _arp_period(period, semis):
    if semis <= 0 or semis >= len(_ARP):
        return period
    return (period * _ARP[semis]) >> 12
