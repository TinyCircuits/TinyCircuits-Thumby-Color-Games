# ProTracker MOD parser (MicroPython-safe: no floats, no big-int truediv).
# Handles 31-sample tagged MODs (M.K./M!K!/FLT4/xCHN/xxCH). Returns plain dicts;
# sample 'data' is a memoryview slice into the input buffer (no copy).
import struct

# Canonical ProTracker period table, finetune 0, notes C-1..B-3 (36 entries).
PERIODS = [
    856,808,762,720,678,640,604,570,538,508,480,453,   # octave 1
    428,404,381,360,339,320,302,285,269,254,240,226,   # octave 2
    214,202,190,180,170,160,151,143,135,127,120,113,   # octave 3
]
NOTE_NAMES = [n+o for o in "123" for n in
              ("C-","C#","D-","D#","E-","F-","F#","G-","G#","A-","A#","B-")]

def _channels_from_tag(tag):
    if tag in (b'M.K.', b'M!K!', b'FLT4', b'4CHN'):
        return 4
    if tag == b'6CHN':
        return 6
    if tag in (b'8CHN', b'FLT8', b'OKTA', b'CD81'):
        return 8
    # 'nCHN' (1..9) and 'nnCH' (10..32)
    try:
        if tag[1:4] == b'CHN' and 0x30 <= tag[0] <= 0x39:
            return tag[0] - 0x30
        if tag[2:4] == b'CH' and 0x30 <= tag[0] <= 0x39 and 0x30 <= tag[1] <= 0x39:
            return (tag[0] - 0x30) * 10 + (tag[1] - 0x30)
    except IndexError:
        pass
    return 0  # unknown/untagged (old 15-sample MOD) -> caller decides

def period_to_note(period):
    """Nearest note name for a period (diagnostics only)."""
    if not period:
        return "..."
    best = 0; bd = 1 << 30
    for i, p in enumerate(PERIODS):
        d = p - period
        if d < 0: d = -d
        if d < bd:
            bd = d; best = i
    return NOTE_NAMES[best]

def parse_mod(buf, decode_patterns=True):
    if len(buf) < 1084:
        raise ValueError("too small to be a 31-sample MOD")
    mv = memoryview(buf)
    title = bytes(buf[0:20]).split(b'\x00')[0].decode('ascii', 'replace')

    samples = []
    off = 20
    for _ in range(31):
        s = buf[off:off + 30]; off += 30
        length = struct.unpack('>H', s[22:24])[0] * 2
        ft = s[24] & 0x0F
        if ft >= 8:
            ft -= 16
        samples.append({
            'name': bytes(s[0:22]).split(b'\x00')[0].decode('ascii', 'replace'),
            'length': length,
            'finetune': ft,
            'volume': s[25],
            'loop_start': struct.unpack('>H', s[26:28])[0] * 2,
            'loop_len': struct.unpack('>H', s[28:30])[0] * 2,
            'data': None,
        })

    song_length = buf[950]
    restart = buf[951]
    order = list(buf[952:952 + 128])
    tag = bytes(buf[1080:1084])
    nch = _channels_from_tag(tag)
    if nch == 0:
        raise ValueError("untagged/old MOD not supported (tag=%r)" % tag)

    used = order[:song_length] if song_length else order
    num_patterns = (max(used) + 1) if used else 0

    row_bytes = nch * 4
    pat_bytes = 64 * row_bytes
    pat_off = 1084
    patterns = None
    if decode_patterns:                    # host path: pre-decode note tuples
        patterns = []
        for p in range(num_patterns):
            base = pat_off + p * pat_bytes
            rows = []
            for r in range(64):
                chans = []
                ro = base + r * row_bytes
                for c in range(nch):
                    o = ro + c * 4
                    b0 = buf[o]; b1 = buf[o + 1]; b2 = buf[o + 2]; b3 = buf[o + 3]
                    sample = (b0 & 0xF0) | (b2 >> 4)
                    period = ((b0 & 0x0F) << 8) | b1
                    chans.append((sample, period, b2 & 0x0F, b3))
                rows.append(chans)
            patterns.append(rows)

    # sample PCM (signed 8-bit) follows the patterns, in sample order.
    # 'offset' is the absolute byte offset into buf (lean mixer reads from there).
    o = pat_off + num_patterns * pat_bytes
    for s in samples:
        L = s['length']
        s['offset'] = o
        s['data'] = mv[o:o + L]
        o += L

    return {
        'title': title, 'samples': samples, 'num_channels': nch,
        'song_length': song_length, 'restart': restart,
        'order': order[:song_length], 'patterns': patterns,
        'num_patterns': num_patterns, 'pattern_offset': pat_off, 'tag': tag,
        'total_len': len(buf), 'sample_data_end': o,
    }
