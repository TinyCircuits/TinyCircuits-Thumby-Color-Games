"""
chal.py - Faithful MicroPython port of the Chal chess engine.

Original C source: TinyCircuits-Tiny-Game-Engine/chess/chal.c
Original engine:   https://github.com/nogiator/c_chess_engine (MIT)

Mirrors chal.h's API:
    init(), new_game(), set_fen(fen), get_fen() -> str
    get_piece(rank, file) -> int            (rank 0 = rank8, 7 = rank1)
    get_side() -> 0|1                       (0 = white, 1 = black)
    get_legal_moves() -> list[(from, to, promo)]   (from/to are 0x88)
    play_move(from, to, promo) -> bool
    search_best_move(max_depth, time_ms) -> (from, to, promo)  ; from = 0x80 if none
    undo_move() -> bool
    evaluate_position() -> int
    is_in_check() -> bool
    is_checkmate() -> bool
    is_stalemate() -> bool
    get_last_score() -> int
    get_last_depth() -> int
    stop_search()

This is a literal port; runtime is dramatically slower than the C version
(plan on depth ~3-4 in a few seconds on the RP2350). Move generation,
make/undo, eval and search structure are all faithful, including TT,
quiescence, LMR, null-move pruning, killers and history heuristic.
"""

import time
import math
from array import array

# ===============================================================
# S1  CONSTANTS
# ===============================================================

EMPTY  = 0
PAWN   = 1
KNIGHT = 2
BISHOP = 3
ROOK   = 4
QUEEN  = 5
KING   = 6

WHITE = 0
BLACK = 1

SQ_NONE = -1
INF  = 50000
MATE = 30000

WP = 1   # white pawn  encoding
BP = 9   # black pawn  encoding ((1<<3)|1)

MAX_PLY = 64
LIST_OFF = 0x88

TT_EXACT = 0
TT_ALPHA = 1
TT_BETA  = 2

# ---- Move encoding ----
# Bits 0-6 = from, 7-13 = to, 14-17 = promo
def _from(m):   return m & 0x7F
def _to(m):     return (m >> 7) & 0x7F
def _promo(m):  return (m >> 14) & 0xF
def _enc(fr, to, pr): return fr | (to << 7) | (pr << 14)

def _ptype(p): return p & 7
def _pcol(p):  return p >> 3
def _mp(c, t): return (c << 3) | t

# ---- Direction tables ----
step_dir = (
    0,0,0,0,
    -33,-31,-18,-14, 14, 18, 31, 33,
    -17,-15, 15, 17,
    -16, -1,  1, 16,
    -17,-16,-15, -1,  1, 15, 16, 17,
)
piece_offsets = (0, 0, 4, 12, 16, 12, 20)
piece_limits  = (0, 0, 12, 16, 20, 20, 28)

# ---- Castling tables ----
castle_kf = (4, 4, 116, 116)
castle_kt = (6, 2, 118, 114)
castle_rf = (7, 0, 119, 112)
castle_rt = (5, 3, 117, 115)
castle_col = (WHITE, WHITE, BLACK, BLACK)
# castle_rights is only 4 bits wide, mask after AND with 0xF
castle_kmask = (12, 12, 3, 3)        # ~3, ~3, ~12, ~12
cr_sq        = (0, 7, 112, 119)
cr_mask      = (13, 14, 7, 11)       # ~2, ~1, ~8, ~4

# ---- Piece values & eval params ----
piece_val   = (0, 100, 320, 330, 500, 900, 20000)
phase_inc   = (0, 0, 1, 1, 2, 4, 0)
mob_center  = (0, 0, 4, 6, 6, 13, 0)
mob_step_mg = (0, 0, 3, 4, 3, 2, 0)
mob_step_eg = (0, 0, 3, 4, 4, 2, 0)

# ---- Piece-square tables (PeSTO-style) ----
mg_pst = (
    # PAWN
    ( 82, 82, 82, 82, 82, 82, 82, 82,
      47, 76, 57, 60, 67,100,107, 56,
      56, 71, 78, 74, 87, 87,104, 70,
      53, 77, 78, 96, 99, 88, 90, 55,
      66, 94, 90,105,107, 96,100, 57,
      76, 90,101,105,120,141,108, 63,
     162,158,131,136,132,139,108, 79,
      82, 82, 82, 82, 82, 82, 82, 82),
    # KNIGHT
    (231,318,281,306,322,311,317,315,
     310,286,327,336,338,357,325,320,
     312,330,347,349,358,356,364,319,
     325,343,353,349,367,357,360,330,
     330,355,355,392,372,407,354,360,
     290,398,374,400,422,465,411,379,
     266,297,411,374,360,401,342,322,
     172,250,305,290,400,241,322,232),
    # BISHOP
    (333,364,353,346,354,351,326,344,
     370,384,382,365,374,388,401,367,
     363,382,380,378,377,393,384,373,
     361,380,376,392,398,375,374,370,
     362,368,384,417,400,400,370,362,
     347,403,408,403,400,417,402,361,
     339,382,348,353,397,425,385,318,
     338,370,283,329,342,325,373,358),
    # ROOK
    (460,466,479,492,491,486,438,452,
     434,462,459,467,476,490,473,405,
     433,454,461,460,478,479,474,443,
     439,453,464,474,486,471,483,452,
     455,467,482,502,499,512,469,457,
     471,496,501,511,492,523,538,493,
     502,507,533,537,555,542,501,519,
     510,519,508,526,539,488,510,522),
    # QUEEN
    (1023,1008,1018,1037,1012,1002, 996, 976,
      991,1016,1036,1029,1035,1042,1024,1028,
     1009,1025,1012,1021,1018,1025,1038,1030,
     1014, 997,1014,1013,1021,1019,1026,1020,
      996, 996,1007,1007,1022,1040,1022,1024,
     1014,1006,1030,1031,1054,1083,1072,1082,
     1002, 984,1020,1028,1008,1084,1054,1081,
      999,1026,1056,1038,1086,1071,1070,1072),
    # KING
    (-17, 36, 14,-56,  6,-26, 26, 12,
       1,  8, -6,-66,-45,-14, 11,  7,
     -13,-12,-20,-48,-46,-28,-13,-25,
     -48,  1,-25,-41,-48,-42,-32,-53,
     -16,-18,-10,-29,-31,-25,-13,-35,
      -7, 26,  4,-17,-22,  8, 24,-24,
      30,  1,-18, -5,-10, -2,-36,-28,
     -66, 24, 18,-14,-58,-32,  3, 13),
)

eg_pst = (
    # PAWN
    ( 94, 94, 94, 94, 94, 94, 94, 94,
     108,100,102,102,106, 92, 94, 85,
      96, 99, 86, 94, 94, 89, 91, 84,
     105,101, 89, 85, 85, 84, 95, 91,
     124,116,105, 97, 90, 96,109,109,
     166,163,140,119,118,125,146,156,
     189,186,180,156,159,182,187,218,
      94, 94, 94, 94, 94, 94, 94, 94),
    # KNIGHT
    (254,232,260,268,261,265,233,219,
     241,263,273,278,281,263,260,239,
     260,279,280,297,293,279,263,261,
     265,277,299,308,298,298,287,265,
     266,286,305,305,305,293,291,261,
     259,263,290,291,278,270,262,239,
     258,275,257,281,272,254,255,231,
     225,245,270,255,251,256,220,183),
    # BISHOP
    (276,290,276,294,290,283,294,282,
     285,281,292,298,302,290,284,271,
     287,296,307,307,312,299,292,284,
     293,301,311,317,304,306,295,290,
     296,308,310,306,311,305,301,301,
     301,290,297,297,297,303,299,303,
     291,295,306,287,295,286,293,285,
     285,278,288,291,292,290,282,275),
    # ROOK
    (506,517,518,512,510,502,519,495,
     509,509,515,517,506,506,504,512,
     511,515,510,514,508,503,507,499,
     518,520,523,516,509,509,507,504,
     519,518,528,513,513,516,513,517,
     522,522,520,517,517,512,510,512,
     522,524,524,522,508,514,519,514,
     528,524,533,526,525,527,523,520),
    # QUEEN
    (904,910,916,896,934,906,919,897,
     917,916,909,922,922,916,903,906,
     923,911,952,944,947,955,949,944,
     920,967,956,985,967,973,976,962,
     941,960,960,983,996,977,996,975,
     918,943,946,987,986,974,956,948,
     921,959,970,980,997,964,969,938,
     930,961,960,966,966,958,949,959),
    # KING
    (-55,-36,-19,-12,-30,-12,-26,-45,
     -28, -9,  6, 11, 12,  6, -3,-19,
     -21, -1, 13, 19, 21, 18,  9,-10,
     -19, -3, 23, 22, 25, 25, 11,-12,
     -10, 24, 26, 25, 24, 35, 28,  1,
      10, 18, 24, 13, 18, 46, 45, 11,
     -12, 19, 16, 16, 15, 40, 25, 12,
     -74,-34,-18,-20,-13, 17,  5,-19),
)

# ===============================================================
# S2  GLOBAL STATE
# ===============================================================
# Mirroring chal.c statics; using module-level for speed.

board = bytearray(128)
side = WHITE
xside = BLACK
ep_square = SQ_NONE
ply = 0
halfmove_clock = 0
castle_rights = 0
hash_key = 0
count = [bytearray(7), bytearray(7)]

# Piece list
list_piece  = bytearray(32)              # type 0..6
list_square = bytearray(32)              # 0..127 or 0x88(=136) sentinel
for _i in range(32): list_square[_i] = LIST_OFF
list_index  = array('b', [-1] * 128)     # signed slot index 0..31 or -1
list_count  = [0, 0]

# History (parallel arrays of length 256)
HIST_MAX = 256
h_move    = array('i', [0]   * HIST_MAX)
h_cap     = bytearray(HIST_MAX)
h_slot    = array('b', [-1]  * HIST_MAX)
h_ep      = array('h', [SQ_NONE] * HIST_MAX)
h_castle  = bytearray(HIST_MAX)
h_hm      = array('h', [0] * HIST_MAX)
h_hash    = array('Q', [0] * HIST_MAX)
h_check   = bytearray(HIST_MAX)

# Search auxiliaries
killers   = array('i', [0] * (MAX_PLY * 2))    # killers[sply*2 + slot]
hist      = array('h', [0] * (64 * 64))        # hist[fr64*64 + to64]; range fits in int16
pv_length = array('h', [0] * MAX_PLY)

# Zobrist (flat: zobrist_piece[(c*7 + p)*128 + sq]) — 64-bit raw to avoid boxing
zobrist_piece  = array('Q', [0] * (2 * 7 * 128))
zobrist_ep     = array('Q', [0] * 128)
zobrist_castle = array('Q', [0] * 16)
zobrist_side   = 0

# Transposition table
tt_size  = 0
tt_key   = None   # list[int]
tt_score = None
tt_best  = None
tt_df    = None   # depth<<2 | flag

# Search globals
nodes_searched = 0
root_depth = 0
best_root_move = 0
time_budget_ms = 0
t_start_ms = 0
time_over_flag = 0
chal_stop_flag = 0
root_ply = 0
last_search_score = 0
last_search_depth = 0

# LMR table
lmr_table = None  # filled in init()


# ===============================================================
# Helpers
# ===============================================================

def _sq_off(sq):  return sq & 0x88
def _is_empty(sq): return board[sq] == EMPTY
def _color_on(sq): return board[sq] >> 3
def _ptype_on(sq): return board[sq] & 7
def _sq64(sq):     return (sq >> 4) * 8 + (sq & 7)

def _king_sq(color):
    base = 0 if color == WHITE else 16
    return list_square[base + list_count[color] - 1]

def _list_set_sq(slot, sq):
    list_square[slot] = sq
    list_index[sq] = slot

def _list_remove(slot, sq):
    list_square[slot] = LIST_OFF
    list_index[sq] = -1


def _set_list():
    global list_count
    for i in range(32):
        list_piece[i] = EMPTY
        list_square[i] = LIST_OFF
    for i in range(128):
        list_index[i] = -1
    list_count[WHITE] = 0
    list_count[BLACK] = 0
    for pt in range(PAWN, KING + 1):
        sq = 0
        while sq < 128:
            if sq & 0x88:
                sq += 8
                continue
            p = board[sq]
            if p and (p & 7) == pt:
                color = p >> 3
                slot = (0 if color == WHITE else 16) + list_count[color]
                list_count[color] += 1
                list_piece[slot] = pt
                list_square[slot] = sq
                list_index[sq] = slot
            sq += 1


# ===============================================================
# S4  Zobrist
# ===============================================================

_rand_state = 1070372631

def _rand64():
    global _rand_state
    s = _rand_state
    s ^= (s >> 12) & 0xFFFFFFFFFFFFFFFF
    s ^= (s << 25) & 0xFFFFFFFFFFFFFFFF
    s ^= (s >> 27) & 0xFFFFFFFFFFFFFFFF
    s &= 0xFFFFFFFFFFFFFFFF
    _rand_state = s
    return (s * 0x2545F4914F6CDD1D) & 0xFFFFFFFFFFFFFFFF


def _init_zobrist():
    global zobrist_side
    for c in range(2):
        for p in range(7):
            base = (c * 7 + p) * 128
            for s in range(128):
                zobrist_piece[base + s] = _rand64()
    zobrist_side = _rand64()
    for s in range(128):
        zobrist_ep[s] = _rand64()
    for s in range(16):
        zobrist_castle[s] = _rand64()


def _generate_hash():
    h = 0
    sq = 0
    while sq < 128:
        if sq & 0x88:
            sq += 8
            continue
        p = board[sq]
        if p:
            h ^= zobrist_piece[(((p >> 3) * 7) + (p & 7)) * 128 + sq]
        sq += 1
    if side == BLACK:
        h ^= zobrist_side
    if ep_square != SQ_NONE:
        h ^= zobrist_ep[ep_square]
    return h ^ zobrist_castle[castle_rights]


# ===============================================================
# S5  Attack detection
# ===============================================================

def is_square_attacked(sq, ac):
    if ac == WHITE:
        t = sq - 17
        if not (t & 0x88) and board[t] == WP: return True
        t = sq - 15
        if not (t & 0x88) and board[t] == WP: return True
    else:
        t = sq + 15
        if not (t & 0x88) and board[t] == BP: return True
        t = sq + 17
        if not (t & 0x88) and board[t] == BP: return True

    knight_p = (ac << 3) | KNIGHT
    for i in range(piece_offsets[KNIGHT], piece_limits[KNIGHT]):
        t = sq + step_dir[i]
        if not (t & 0x88) and board[t] == knight_p:
            return True

    # Sliders: bishop/queen on diag, rook/queen on file/rank
    bishop_p = (ac << 3) | BISHOP
    rook_p   = (ac << 3) | ROOK
    queen_p  = (ac << 3) | QUEEN
    for i in range(piece_offsets[BISHOP], piece_limits[QUEEN]):
        step = step_dir[i]
        t = sq + step
        while not (t & 0x88):
            p = board[t]
            if p:
                if i < piece_limits[BISHOP]:
                    if p == bishop_p or p == queen_p:
                        return True
                else:
                    if p == rook_p or p == queen_p:
                        return True
                break
            t += step

    king_p = (ac << 3) | KING
    for i in range(piece_offsets[KING], piece_limits[KING]):
        t = sq + step_dir[i]
        if not (t & 0x88) and board[t] == king_p:
            return True
    return False


def _in_check(s):
    return is_square_attacked(_king_sq(s), s ^ 1)


def _is_illegal():
    return is_square_attacked(_king_sq(xside), side)


# ===============================================================
# S6  Make / undo
# ===============================================================

def _make_move(m):
    global ep_square, halfmove_clock, side, xside, castle_rights, hash_key, ply
    fr = m & 0x7F
    to = (m >> 7) & 0x7F
    pr = (m >> 14) & 0xF
    p = board[fr]
    pt = p & 7
    cap = board[to]

    h_move[ply]   = m
    h_cap[ply]    = cap
    h_ep[ply]     = ep_square
    h_castle[ply] = castle_rights
    h_hm[ply]     = halfmove_clock
    h_hash[ply]   = hash_key
    h_slot[ply]   = -1
    halfmove_clock = 0 if (pt == PAWN or cap) else halfmove_clock + 1

    # En-passant capture
    if pt == PAWN and to == ep_square:
        ep_pawn = to + (-16 if side == WHITE else 16)
        h_cap[ply]  = board[ep_pawn]
        h_slot[ply] = list_index[ep_pawn]
        list_square[h_slot[ply]] = LIST_OFF
        list_index[ep_pawn] = -1
        board[ep_pawn] = EMPTY
        hash_key ^= zobrist_piece[((xside * 7) + PAWN) * 128 + ep_pawn]
        count[xside][PAWN] -= 1

    # Capture
    if cap:
        h_slot[ply] = list_index[to]
        list_square[h_slot[ply]] = LIST_OFF
        list_index[to] = -1
        ct = cap & 7
        hash_key ^= zobrist_piece[((xside * 7) + ct) * 128 + to]
        count[xside][ct] -= 1

    # Move piece in lists/board
    list_set_slot = list_index[fr]
    list_square[list_set_slot] = to
    list_index[to] = list_set_slot
    list_index[fr] = -1
    board[to] = p
    board[fr] = EMPTY
    _zb = ((side * 7) + pt) * 128
    hash_key ^= zobrist_piece[_zb + fr]
    hash_key ^= zobrist_piece[_zb + to]

    # Promotion
    if pr:
        slot = list_index[to]
        list_piece[slot] = pr
        board[to] = (side << 3) | pr
        hash_key ^= zobrist_piece[((side * 7) + pt) * 128 + to]
        hash_key ^= zobrist_piece[((side * 7) + pr) * 128 + to]
        count[side][PAWN] -= 1
        count[side][pr] += 1

    # Castling rook move
    hash_key ^= zobrist_castle[castle_rights]
    if pt == KING:
        for ci in range(4):
            if fr == castle_kf[ci] and to == castle_kt[ci]:
                rook_from = castle_rf[ci]
                rook_to = castle_rt[ci]
                rook_slot = list_index[rook_from]
                board[rook_from] = EMPTY
                board[rook_to] = (castle_col[ci] << 3) | ROOK
                list_square[rook_slot] = rook_to
                list_index[rook_to] = rook_slot
                list_index[rook_from] = -1
                _zr = ((castle_col[ci] * 7) + ROOK) * 128
                hash_key ^= zobrist_piece[_zr + rook_from]
                hash_key ^= zobrist_piece[_zr + rook_to]
                break
        castle_rights &= castle_kmask[side * 2]
    for ci in range(4):
        if fr == cr_sq[ci] or to == cr_sq[ci]:
            castle_rights &= cr_mask[ci]
    hash_key ^= zobrist_castle[castle_rights]

    if ep_square != SQ_NONE:
        hash_key ^= zobrist_ep[ep_square]
    ep_square = SQ_NONE
    if pt == PAWN and ((to - fr) == 32 or (fr - to) == 32):
        ep_square = fr + (16 if side == WHITE else -16)
        hash_key ^= zobrist_ep[ep_square]

    hash_key ^= zobrist_side
    side ^= 1
    xside ^= 1
    h_check[ply] = is_square_attacked(_king_sq(side), xside)
    ply += 1


def _undo_move():
    global ep_square, halfmove_clock, side, xside, castle_rights, hash_key, ply
    ply -= 1
    side ^= 1
    xside ^= 1
    m = h_move[ply]
    fr = m & 0x7F
    to = (m >> 7) & 0x7F
    pr = (m >> 14) & 0xF
    cap = h_cap[ply]

    slot = list_index[to]
    list_square[slot] = fr
    list_index[fr] = slot
    list_index[to] = -1
    board[fr] = board[to]
    board[to] = cap

    if pr:
        slot2 = list_index[fr]
        list_piece[slot2] = PAWN
        board[fr] = (side << 3) | PAWN
        count[side][pr] -= 1
        count[side][PAWN] += 1

    pt = board[fr] & 7

    if pt == PAWN and to == h_ep[ply]:
        # en passant: cap was the enemy pawn placed on different sq
        ep_pawn = to + (-16 if side == WHITE else 16)
        board[to] = EMPTY
        board[ep_pawn] = cap
        if cap:
            list_square[h_slot[ply]] = ep_pawn
            list_index[ep_pawn] = h_slot[ply]
        count[xside][PAWN] += 1
    elif cap:
        list_square[h_slot[ply]] = to
        list_index[to] = h_slot[ply]
        count[xside][cap & 7] += 1

    if pt == KING:
        for ci in range(4):
            if fr == castle_kf[ci] and to == castle_kt[ci]:
                rook_from = castle_rt[ci]
                rook_to   = castle_rf[ci]
                rook_slot = list_index[rook_from]
                board[rook_from] = EMPTY
                board[rook_to] = (castle_col[ci] << 3) | ROOK
                list_square[rook_slot] = rook_to
                list_index[rook_to] = rook_slot
                list_index[rook_from] = -1
                break

    ep_square      = h_ep[ply]
    castle_rights  = h_castle[ply]
    halfmove_clock = h_hm[ply]
    hash_key       = h_hash[ply]


# ===============================================================
# S7  Move generation
# ===============================================================

def _add_promo(moves, fr, to):
    moves.append(_enc(fr, to, QUEEN))
    moves.append(_enc(fr, to, ROOK))
    moves.append(_enc(fr, to, BISHOP))
    moves.append(_enc(fr, to, KNIGHT))


def generate_moves(caps_only):
    moves = []
    d_pawn      = 16 if side == WHITE else -16
    pawn_start  = 1 if side == WHITE else 6
    pawn_promo  = 6 if side == WHITE else 1
    base = 0 if side == WHITE else 16
    top  = 16 if side == WHITE else 32

    for slot in range(base, top):
        sq = list_square[slot]
        if sq == LIST_OFF:
            continue
        pt = list_piece[slot]

        if pt == PAWN:
            tgt = sq + d_pawn
            if not (tgt & 0x88) and board[tgt] == EMPTY:
                if (sq >> 4) == pawn_promo:
                    _add_promo(moves, sq, tgt)
                elif not caps_only:
                    moves.append(_enc(sq, tgt, 0))
                    if (sq >> 4) == pawn_start and board[tgt + d_pawn] == EMPTY:
                        moves.append(_enc(sq, tgt + d_pawn, 0))
            for di in (-1, 1):
                tgt = sq + d_pawn + di
                if not (tgt & 0x88):
                    bt = board[tgt]
                    if (bt and (bt >> 3) == xside) or tgt == ep_square:
                        if (sq >> 4) == pawn_promo:
                            _add_promo(moves, sq, tgt)
                        else:
                            moves.append(_enc(sq, tgt, 0))
            continue

        if pt == KNIGHT or pt == KING:
            for i in range(piece_offsets[pt], piece_limits[pt]):
                tgt = sq + step_dir[i]
                if tgt & 0x88:
                    continue
                bt = board[tgt]
                if bt == EMPTY:
                    if not caps_only:
                        moves.append(_enc(sq, tgt, 0))
                elif (bt >> 3) == xside:
                    moves.append(_enc(sq, tgt, 0))
        else:
            for i in range(piece_offsets[pt], piece_limits[pt]):
                step = step_dir[i]
                tgt = sq + step
                while not (tgt & 0x88):
                    bt = board[tgt]
                    if bt == EMPTY:
                        if not caps_only:
                            moves.append(_enc(sq, tgt, 0))
                    else:
                        if (bt >> 3) == xside:
                            moves.append(_enc(sq, tgt, 0))
                        break
                    tgt += step

        if pt == KING and not caps_only:
            for ci in range(4):
                kf = castle_kf[ci]
                kt = castle_kt[ci]
                rf = castle_rf[ci]
                bit = (1, 2, 4, 8)[ci]
                ac = BLACK if castle_col[ci] == WHITE else WHITE
                if sq != kf or castle_col[ci] != side:
                    continue
                if not (castle_rights & bit):
                    continue
                if board[rf] != ((side << 3) | ROOK):
                    continue
                sq1 = kf + 1 if kf < rf else rf + 1
                sq2 = rf if kf < rf else kf
                clear_ok = True
                for sq3 in range(sq1, sq2):
                    if board[sq3] != EMPTY:
                        clear_ok = False
                        break
                if not clear_ok:
                    continue
                step2 = 1 if kt > kf else -1
                clear_ok = True
                sq3 = kf
                while True:
                    if is_square_attacked(sq3, ac):
                        clear_ok = False
                        break
                    if sq3 == kt:
                        break
                    sq3 += step2
                if clear_ok:
                    moves.append(_enc(kf, kt, 0))
    return moves


# ===============================================================
# S8  FEN parser / writer
# ===============================================================

STARTPOS = "rnbqkbnr/pppppppp/8/8/8/8/PPPPPPPP/RNBQKBNR w KQkq - 0 1"

_PIECE_CHARS = "pnbrqk"

def _char_to_piece(c):
    i = _PIECE_CHARS.find(c)
    return (i + 1) if i >= 0 else EMPTY


def _parse_fen(fen):
    global castle_rights, ep_square, ply, hash_key, side, xside, halfmove_clock
    for i in range(128):
        board[i] = EMPTY
    castle_rights = 0
    ep_square = SQ_NONE
    ply = 0
    hash_key = 0
    for c in range(2):
        for p in range(7):
            count[c][p] = 0
    for i in range(MAX_PLY * 2):
        killers[i] = 0
    for i in range(MAX_PLY):
        pv_length[i] = 0
    for i in range(64 * 64):
        hist[i] = 0

    rank = 7
    file = 0
    idx = 0
    n = len(fen)
    while idx < n and fen[idx] != ' ':
        ch = fen[idx]
        if ch == '/':
            file = 0
            rank -= 1
        elif '0' <= ch <= '9':
            file += ord(ch) - ord('0')
        else:
            sq = rank * 16 + file
            color = WHITE if ch.isupper() else BLACK
            piece = _char_to_piece(ch.lower())
            if piece == EMPTY:
                idx += 1
                continue
            board[sq] = (color << 3) | piece
            count[color][piece] += 1
            file += 1
        idx += 1

    if idx < n: idx += 1
    side  = WHITE if (idx < n and fen[idx] == 'w') else BLACK
    xside = side ^ 1
    if idx < n: idx += 1
    if idx < n: idx += 1

    while idx < n and fen[idx] != ' ':
        c = fen[idx]
        if c == 'K': castle_rights |= 1
        elif c == 'Q': castle_rights |= 2
        elif c == 'k': castle_rights |= 4
        elif c == 'q': castle_rights |= 8
        idx += 1
    if idx < n: idx += 1

    if idx < n and fen[idx] != '-' and idx + 1 < n:
        ep_square = (ord(fen[idx + 1]) - ord('1')) * 16 + (ord(fen[idx]) - ord('a'))

    while idx < n and fen[idx] != ' ':
        idx += 1
    halfmove_clock = 0
    if idx < n and fen[idx] == ' ':
        idx += 1
        num = ""
        while idx < n and '0' <= fen[idx] <= '9':
            num += fen[idx]
            idx += 1
        if num:
            halfmove_clock = int(num)

    _set_list()


def get_fen():
    parts = []
    for r in range(7, -1, -1):
        empty = 0
        row = ""
        for f in range(8):
            sq = r * 16 + f
            p = board[sq]
            if p == EMPTY:
                empty += 1
                continue
            if empty:
                row += str(empty)
                empty = 0
            ch = ".pnbrqk"[p & 7]
            if (p >> 3) == WHITE:
                ch = ch.upper()
            row += ch
        if empty:
            row += str(empty)
        parts.append(row)
    out = "/".join(parts)
    out += " " + ("w" if side == WHITE else "b") + " "
    cs = ""
    if castle_rights & 1: cs += "K"
    if castle_rights & 2: cs += "Q"
    if castle_rights & 4: cs += "k"
    if castle_rights & 8: cs += "q"
    if not cs: cs = "-"
    out += cs + " "
    if ep_square != SQ_NONE:
        out += chr(ord('a') + (ep_square & 7)) + chr(ord('1') + (ep_square >> 4))
    else:
        out += "-"
    out += " " + str(halfmove_clock) + " 1"
    return out


# ===============================================================
# S9  Evaluation
# ===============================================================

def _abs(x):
    return -x if x < 0 else x

def _distance(s1, s2):
    a = _abs((s1 & 7) - (s2 & 7))
    b = _abs((s1 >> 4) - (s2 >> 4))
    return a if a > b else b


def evaluate():
    mg_w = 0; mg_b = 0
    eg_w = 0; eg_b = 0
    phase = 0
    lpr_w = [7]*8
    lpr_b = [7]*8
    pr_list = []

    for slot in range(32):
        sq = list_square[slot]
        if sq == LIST_OFF:
            continue
        pt = list_piece[slot]
        color = WHITE if slot < 16 else BLACK
        rank = sq >> 4
        f = sq & 7

        if pt == PAWN:
            own_rank = rank if color == WHITE else (7 - rank)
            if color == WHITE:
                if own_rank < lpr_w[f]: lpr_w[f] = own_rank
            else:
                if own_rank < lpr_b[f]: lpr_b[f] = own_rank
            pr_list.append(sq)
        elif pt == ROOK:
            pr_list.append(sq)

        idx = (rank * 8 + f) if color == WHITE else ((7 - rank) * 8 + f)
        mg_v = mg_pst[pt - 1][idx]
        eg_v = eg_pst[pt - 1][idx]
        if color == WHITE:
            mg_w += mg_v; eg_w += eg_v
        else:
            mg_b += mg_v; eg_b += eg_v
        phase += phase_inc[pt]

        if KNIGHT <= pt <= QUEEN:
            mob = 0
            for i in range(piece_offsets[pt], piece_limits[pt]):
                step = step_dir[i]
                target = sq + step
                while not (target & 0x88):
                    bt = board[target]
                    if bt == EMPTY:
                        mob += 1
                    else:
                        if (bt >> 3) != color:
                            mob += 1
                        break
                    if pt == KNIGHT:
                        break
                    target += step
            mob -= mob_center[pt]
            mv = mob_step_mg[pt] * mob
            ev = mob_step_eg[pt] * mob
            if color == WHITE:
                mg_w += mv; eg_w += ev
            else:
                mg_b += mv; eg_b += ev

    if count[WHITE][BISHOP] >= 2:
        mg_w += 31; eg_w += 30
    if count[BLACK][BISHOP] >= 2:
        mg_b += 31; eg_b += 30

    shield_val = (0, 12, 4, -2, -2, 0, 0, -12)
    for color in (WHITE, BLACK):
        ksq = _king_sq(color)
        kf = ksq & 7
        if kf <= 2 or kf >= 5:
            shield = 0
            own = lpr_w if color == WHITE else lpr_b
            opp = lpr_b if color == WHITE else lpr_w
            ft = kf - 1
            while ft <= kf + 1:
                if 0 <= ft <= 7:
                    shield += shield_val[own[ft]]
                    if own[ft] == 7 and opp[ft] == 7:
                        shield -= 18
                ft += 1
            if color == WHITE:
                mg_w += shield
            else:
                mg_b += shield

    pp_eg = (0, 20, 30, 55, 80, 115, 170, 0)
    pp_mg = (0,  5, 10, 20, 35,  55,  80, 0)

    for sq in pr_list:
        p = board[sq]
        pt = p & 7
        color = p >> 3
        f = sq & 7
        if pt == ROOK:
            own = lpr_w if color == WHITE else lpr_b
            opp = lpr_b if color == WHITE else lpr_w
            if own[f] == 7:
                bonus = 20 if opp[f] == 7 else 10
                if color == WHITE:
                    mg_w += bonus; eg_w += bonus
                else:
                    mg_b += bonus; eg_b += bonus
            continue

        rank = sq >> 4
        own_rank = rank if color == WHITE else (7 - rank)
        own = lpr_w if color == WHITE else lpr_b
        opp = lpr_b if color == WHITE else lpr_w
        enemy = color ^ 1

        if own_rank != own[f]:
            if color == WHITE:
                mg_w -= 20; eg_w -= 20
            else:
                mg_b -= 20; eg_b -= 20

        passed = True
        isolated = True
        for df in (-1, 0, 1):
            ef = f + df
            if ef < 0 or ef > 7:
                continue
            if opp[ef] != 7:
                enemy_front_rank = 7 - opp[ef]
                if enemy_front_rank >= own_rank:
                    passed = False
            if df != 0 and own[ef] != 7:
                isolated = False

        if isolated:
            if color == WHITE:
                mg_w -= 10; eg_w -= 10
            else:
                mg_b -= 10; eg_b -= 10
        if not passed:
            continue

        bonus_mg = pp_mg[own_rank]
        bonus_eg = pp_eg[own_rank]
        bonus_eg += 4 * (_distance(sq, _king_sq(enemy)) - _distance(sq, _king_sq(color)))

        front = sq + (16 if color == WHITE else -16)
        if not (front & 0x88) and board[front] != EMPTY and (board[front] >> 3) == enemy:
            bonus_mg //= 2
            bonus_eg //= 2

        if color == WHITE:
            mg_w += bonus_mg; eg_w += bonus_eg
        else:
            mg_b += bonus_mg; eg_b += bonus_eg

    if phase > 24:
        phase = 24
    if side == WHITE:
        mg_score = mg_w - mg_b
        eg_score = eg_w - eg_b
    else:
        mg_score = mg_b - mg_w
        eg_score = eg_b - eg_w
    return (mg_score * phase + eg_score * (24 - phase)) // 24


# ===============================================================
# S10  Move ordering / SEE
# ===============================================================

def _pawn_defended_by_pawn(s):
    p = board[s]
    if not p or (p & 7) != PAWN:
        return False
    c = p >> 3
    if c == WHITE:
        a1 = s - 17; a2 = s - 15
    else:
        a1 = s + 15; a2 = s + 17
    pp = (c << 3) | PAWN
    if not (a1 & 0x88) and board[a1] == pp: return True
    if not (a2 & 0x88) and board[a2] == pp: return True
    return False


def _line_step(fr, to):
    diff = to - fr
    if (fr & 7) == (to & 7):     return 16 if diff > 0 else -16
    if (fr >> 4) == (to >> 4):   return 1 if diff > 0 else -1
    if diff % 17 == 0:           return 17 if diff > 0 else -17
    if diff % 15 == 0:           return 15 if diff > 0 else -15
    return 0


def _piece_attacks_sq(fr, to, cleared):
    diff = to - fr
    p = board[fr]
    pt = p & 7
    col = p >> 3
    if pt == PAWN:
        if col == WHITE:
            return diff == 15 or diff == 17
        return diff == -17 or diff == -15
    if pt == KNIGHT:
        return diff in (-33, -31, -18, -14, 14, 18, 31, 33)
    if pt == KING:
        return diff in (-17, -16, -15, -1, 1, 15, 16, 17)
    step = _line_step(fr, to)
    if not step:
        return False
    if pt == BISHOP and step not in (-17, -15, 15, 17):
        return False
    if pt == ROOK and step not in (-16, -1, 1, 16):
        return False
    sq = fr + step
    while not (sq & 0x88):
        if sq == to:
            return True
        if board[sq] != EMPTY and sq not in cleared:
            break
        sq += step
    return False


def _see(fr, to):
    cap_type = board[to] & 7
    if not cap_type:
        return 0
    cleared = set()
    cleared.add(fr)
    target_seq = [cap_type]
    piece_on_to = board[fr] & 7
    cur_side = (board[fr] >> 3) ^ 1
    nsteps = 0
    while nsteps < 31:
        lva_sq = -1
        lva_type = 0
        lva_val = INF
        base = 0 if cur_side == WHITE else 16
        top = base + list_count[cur_side]
        for i in range(base, top):
            psq = list_square[i]
            if psq == LIST_OFF: continue
            if psq in cleared: continue
            pv = piece_val[list_piece[i]]
            if pv < lva_val and _piece_attacks_sq(psq, to, cleared):
                lva_val = pv
                lva_sq = psq
                lva_type = list_piece[i]
        if lva_sq < 0:
            break
        target_seq.append(piece_on_to)
        cleared.add(lva_sq)
        piece_on_to = lva_type
        cur_side ^= 1
        nsteps += 1

    result = 0
    for d in range(nsteps - 1, -1, -1):
        gain = piece_val[target_seq[d + 1]] - result
        result = gain if gain > 0 else 0
    return piece_val[cap_type] - result


def _is_bad_capture(fr, to):
    if piece_val[board[fr] & 7] <= piece_val[board[to] & 7]:
        return False
    return _see(fr, to) < 0


def _score_move(m, hash_move, sply):
    if m == hash_move:
        return 30000
    fr = m & 0x7F
    to = (m >> 7) & 0x7F
    pr = (m >> 14) & 0xF
    cap = board[to]
    if not cap and (board[fr] & 7) == PAWN and to == ep_square:
        cap = (xside << 3) | PAWN
    if cap:
        hunter_type = board[fr] & 7
        prey_type = cap & 7
        if prey_type == PAWN and hunter_type != PAWN and _pawn_defended_by_pawn(to):
            return -17000 + 10 * piece_val[prey_type] - piece_val[hunter_type]
        return 20000 + 10 * piece_val[prey_type] - piece_val[hunter_type]
    if pr:
        return 19999
    if sply < MAX_PLY and m == killers[sply * 2]:
        return 19998
    if sply < MAX_PLY and m == killers[sply * 2 + 1]:
        return 19997
    return hist[_sq64(fr) * 64 + _sq64(to)]


def _score_moves(moves, hash_move, sply):
    return [_score_move(m, hash_move, sply) for m in moves]


def _pick_move(moves, scores, n, idx):
    best = idx
    bs = scores[idx]
    for i in range(idx + 1, n):
        if scores[i] > bs:
            best = i
            bs = scores[i]
    if best != idx:
        scores[idx], scores[best] = scores[best], scores[idx]
        moves[idx], moves[best] = moves[best], moves[idx]


# ===============================================================
# S11  Search
# ===============================================================

def _time_check():
    global time_over_flag
    if time_budget_ms > 0:
        ms = time.ticks_diff(time.ticks_ms(), t_start_ms)
        if ms >= time_budget_ms:
            time_over_flag = 1
            return True
    return False


def _qsearch(alpha, beta, sply):
    global nodes_searched, time_over_flag
    pv_length[sply] = sply
    if (nodes_searched & 1023) == 0:
        if _time_check(): return 0
    if time_over_flag or chal_stop_flag:
        return 0

    best_sc = evaluate()
    if best_sc >= beta:
        return best_sc
    if best_sc > alpha:
        alpha = best_sc
    nodes_searched += 1

    moves = generate_moves(True)
    cnt = len(moves)
    scores = _score_moves(moves, 0, sply)

    for i in range(cnt):
        _pick_move(moves, scores, cnt, i)
        m = moves[i]
        to_sq = (m >> 7) & 0x7F
        fr_sq = m & 0x7F
        pr = (m >> 14) & 0xF
        dp_cap = board[to_sq]
        dp_ep = (not dp_cap and (board[fr_sq] & 7) == PAWN and to_sq == ep_square)
        if dp_cap or dp_ep:
            cap_val = piece_val[dp_cap & 7] if dp_cap else piece_val[PAWN]
            if best_sc + cap_val + 200 < alpha:
                continue

        if not pr and _is_bad_capture(fr_sq, to_sq):
            continue

        _make_move(m)
        if _is_illegal():
            _undo_move()
            continue
        sc = -_qsearch(-beta, -alpha, sply + 1)
        _undo_move()
        if sc > best_sc:
            best_sc = sc
        if sc > alpha:
            alpha = sc
        if alpha >= beta:
            break
    return best_sc


def _search(depth, alpha, beta, sply, was_null):
    global nodes_searched, time_over_flag, ep_square, side, xside, hash_key, ply
    global best_root_move

    if depth <= 0:
        return _qsearch(alpha, beta, sply)

    pv_length[sply] = sply
    if (nodes_searched & 1023) == 0:
        if _time_check(): return 0
    if time_over_flag or chal_stop_flag:
        return 0

    is_pv = (beta - alpha > 1)
    tt_idx = hash_key % tt_size
    e_key = tt_key[tt_idx]
    e_score = tt_score[tt_idx]
    e_best = tt_best[tt_idx]
    e_df = tt_df[tt_idx]
    hash_move = 0

    # Repetition / 50-move / insufficient material
    if ply > root_ply:
        i = ply - 2
        while i >= root_ply:
            if h_hash[i] == hash_key:
                return 0
            i -= 2
        reps = 0
        i = ply - 2
        limit = ply - halfmove_clock
        while i >= 0 and i >= limit:
            if h_hash[i] == hash_key:
                reps += 1
                if reps >= 2:
                    return 0
            i -= 2
        if halfmove_clock >= 100:
            return 0
        wm = count[WHITE][KNIGHT] + count[WHITE][BISHOP]
        bm = count[BLACK][KNIGHT] + count[BLACK][BISHOP]
        if (wm + bm == 1
            and not count[WHITE][PAWN] and not count[BLACK][PAWN]
            and not count[WHITE][ROOK] and not count[BLACK][ROOK]
            and not count[WHITE][QUEEN] and not count[BLACK][QUEEN]):
            return 0

    if e_key == hash_key and e_key != 0:
        hash_move = e_best
        e_depth = e_df >> 2
        if e_depth >= depth:
            flag = e_df & 3
            tt_sc = e_score
            if tt_sc > MATE - MAX_PLY: tt_sc -= sply
            if tt_sc < -(MATE - MAX_PLY): tt_sc += sply
            if sply > 0:
                if flag == TT_EXACT: return tt_sc
                if not is_pv and flag == TT_BETA  and tt_sc >= beta:  return tt_sc
                if not is_pv and flag == TT_ALPHA and tt_sc <= alpha: return tt_sc

    best_sc = -INF
    nodes_searched += 1

    node_in_check = h_check[ply - 1] if sply > 0 else _in_check(side)

    static_eval = -INF
    if (not is_pv) and sply > 0 and (not node_in_check) and beta < MATE - MAX_PLY and depth <= 7:
        static_eval = evaluate()
    if static_eval != -INF:
        if depth <= 7 and static_eval - 70 * depth >= beta:
            return static_eval - 70 * depth
        if depth <= 3 and static_eval + 300 + 60 * depth < alpha:
            return _qsearch(alpha, beta, sply)

    # Null-move pruning
    if ((not is_pv) and sply > 0 and depth >= 3 and not was_null
        and not node_in_check and beta < MATE - MAX_PLY
        and (count[side][KNIGHT] + count[side][BISHOP]
             + count[side][ROOK] + count[side][QUEEN] > 0)):
        if static_eval == -INF:
            static_eval = evaluate()
        if static_eval >= beta:
            R = 4 if depth >= 7 else 3
            ep_prev = ep_square
            hash_key ^= zobrist_side
            if ep_square != SQ_NONE:
                hash_key ^= zobrist_ep[ep_square]
            ep_square = SQ_NONE
            side ^= 1
            xside ^= 1
            h_hash[ply] = hash_key
            ply += 1
            null_sc = -_search(depth - R - 1, -beta, -beta + 1, sply + 1, 1)
            ply -= 1
            side ^= 1
            xside ^= 1
            ep_square = ep_prev
            if ep_square != SQ_NONE:
                hash_key ^= zobrist_ep[ep_square]
            hash_key ^= zobrist_side
            if null_sc >= beta:
                return null_sc

    # IID-style: shallow if no hash move at high depth
    if depth >= 4 and not hash_move and not node_in_check:
        depth -= 1

    moves = generate_moves(False)
    cnt = len(moves)
    scores = _score_moves(moves, hash_move, sply)
    quiet_moves = []
    nquiet = 0
    quiet = 0
    legal = 0
    best = 0
    old_alpha = alpha

    for i in range(cnt):
        _pick_move(moves, scores, cnt, i)
        m = moves[i]
        to_sq = (m >> 7) & 0x7F
        fr_sq = m & 0x7F
        pr = (m >> 14) & 0xF
        is_cap = (board[to_sq] != EMPTY) or ((board[fr_sq] & 7) == PAWN and to_sq == ep_square)

        if (not is_pv and not node_in_check and is_cap and not pr and legal > 0
            and piece_val[board[fr_sq] & 7] > piece_val[board[to_sq] & 7]
            and _see(fr_sq, to_sq) < -piece_val[PAWN] * depth):
            continue

        _make_move(m)
        if _is_illegal():
            _undo_move()
            continue
        legal += 1
        if not is_cap and not pr:
            quiet += 1

        gives_check = h_check[ply - 1]

        if (not is_pv and depth < 4 and not node_in_check and quiet > 4 * depth + 1
            and not is_cap and not pr):
            if not gives_check:
                _undo_move()
                continue

        if not is_cap and not pr:
            quiet_moves.append(m)
            nquiet += 1
        ext = 1 if gives_check else 0

        if legal == 1:
            sc = -_search(depth - 1 + ext, -beta, -alpha, sply + 1, 0)
        else:
            lmr = 0
            if depth >= 3 and legal > 4 and not is_cap and not pr and not ext:
                d_idx = depth if depth < 32 else 31
                m_idx = legal if legal < 64 else 63
                lmr = lmr_table[d_idx * 64 + m_idx]
                if lmr > depth - 2: lmr = depth - 2
                if lmr < 0: lmr = 0
            sc = -_search(depth - 1 + ext - lmr, -alpha - 1, -alpha, sply + 1, 0)
            if sc > alpha and lmr > 0:
                sc = -_search(depth - 1 + ext, -alpha - 1, -alpha, sply + 1, 0)
            if sc > alpha and is_pv:
                sc = -_search(depth - 1 + ext, -beta, -alpha, sply + 1, 0)

        _undo_move()

        if sc > best_sc:
            best_sc = sc
        if sc > alpha:
            alpha = sc
            best = m
            if not time_over_flag and m != 0 and sply == 0:
                best_root_move = m
        if alpha >= beta:
            if not is_cap and not pr:
                d_kill = sply if sply < MAX_PLY else MAX_PLY - 1
                killers[d_kill * 2 + 1] = killers[d_kill * 2]
                killers[d_kill * 2] = m
                bonus = depth * depth
                hidx = _sq64(fr_sq) * 64 + _sq64(to_sq)
                h = hist[hidx]
                h += bonus - h * bonus // 16000
                if h > 16000: h = 16000
                hist[hidx] = h
                for j in range(nquiet - 1):
                    qm = quiet_moves[j]
                    qidx = _sq64(qm & 0x7F) * 64 + _sq64((qm >> 7) & 0x7F)
                    hm2 = hist[qidx]
                    hm2 -= bonus + hm2 * bonus // 16000
                    if hm2 < -16000: hm2 = -16000
                    hist[qidx] = hm2
            break

    if not legal:
        return -(MATE - sply) if node_in_check else 0

    if not time_over_flag and (tt_key[tt_idx] != hash_key or depth >= (tt_df[tt_idx] >> 2)):
        if best_sc <= old_alpha:
            flag = TT_ALPHA
        elif best_sc >= beta:
            flag = TT_BETA
        else:
            flag = TT_EXACT
        sc_store = best_sc
        if sc_store > MATE - MAX_PLY: sc_store += sply
        if sc_store < -(MATE - MAX_PLY): sc_store -= sply
        store_move = best if best else hash_move
        tt_key[tt_idx]   = hash_key
        tt_score[tt_idx] = sc_store
        tt_best[tt_idx]  = store_move
        tt_df[tt_idx]    = ((depth if depth > 0 else 0) << 2) | flag

    return best_sc


def _search_root(max_depth):
    global nodes_searched, root_depth, best_root_move, t_start_ms
    global time_over_flag, chal_stop_flag, root_ply
    global last_search_score, last_search_depth

    sc = 0
    prev_sc = 0
    time_over_flag = 0
    chal_stop_flag = 0
    best_root_move = 0
    t_start_ms = time.ticks_ms()
    for i in range(64 * 64):
        hist[i] = 0
    for i in range(MAX_PLY * 2):
        killers[i] = 0
    for i in range(MAX_PLY):
        pv_length[i] = 0
    nodes_searched = 0
    root_ply = ply

    rd = 1
    while rd <= max_depth:
        root_depth = rd
        if rd < 5:
            sc = _search(rd, -INF, INF, 0, 0)
        else:
            delta = 15 + prev_sc * prev_sc // 16384
            alpha = max(prev_sc - delta, -INF)
            beta  = min(prev_sc + delta,  INF)
            while True:
                sc = _search(rd, alpha, beta, 0, 0)
                if time_over_flag or chal_stop_flag:
                    break
                if sc <= alpha:
                    beta = (alpha + beta) // 2
                    alpha = max(alpha - delta, -INF)
                elif sc >= beta:
                    beta = min(beta + delta, INF)
                else:
                    break
                delta += delta // 2
        if time_over_flag or chal_stop_flag:
            break
        prev_sc = sc
        last_search_score = sc
        last_search_depth = rd
        if time_budget_ms > 0:
            ms = time.ticks_diff(time.ticks_ms(), t_start_ms)
            if ms >= time_budget_ms // 2:
                break
        rd += 1


# ===============================================================
# Public API
# ===============================================================

def _make_lmr():
    t = bytearray(32 * 64)
    for d in range(1, 32):
        for m in range(1, 64):
            r = int(round(math.log(d) * math.log(m) / 1.6))
            if r < 1: r = 1
            if r > 5: r = 5
            t[d * 64 + m] = r
    return t


def init(tt_entries=4096):
    """Initialize engine. Allocate TT (default 4096 entries ~ small)."""
    global tt_size, tt_key, tt_score, tt_best, tt_df, lmr_table
    global last_search_score, last_search_depth
    tt_size = tt_entries
    tt_key   = array('Q', [0] * tt_entries)
    tt_score = array('i', [0] * tt_entries)
    tt_best  = array('i', [0] * tt_entries)
    tt_df    = array('i', [0] * tt_entries)
    lmr_table = _make_lmr()
    _init_zobrist()
    _parse_fen(STARTPOS)
    global hash_key
    hash_key = _generate_hash()
    last_search_score = 0
    last_search_depth = 0


def new_game():
    global hash_key, last_search_score, last_search_depth
    if tt_key is not None:
        for i in range(tt_size):
            tt_key[i] = 0
            tt_score[i] = 0
            tt_best[i] = 0
            tt_df[i] = 0
    for i in range(64 * 64):
        hist[i] = 0
    _parse_fen(STARTPOS)
    hash_key = _generate_hash()
    last_search_score = 0
    last_search_depth = 0


def set_fen(fen):
    global hash_key
    _parse_fen(fen)
    hash_key = _generate_hash()


def get_piece(rank, file):
    """rank 0 = rank 8 (black back rank), 7 = rank 1 (white back)."""
    return board[(7 - rank) * 16 + file]


def get_side():
    return side


def get_legal_moves():
    """Return list of (from, to, promo) tuples for the side to move."""
    out = []
    moves = generate_moves(False)
    for m in moves:
        _make_move(m)
        if not _is_illegal():
            _undo_move()
            out.append((m & 0x7F, (m >> 7) & 0x7F, (m >> 14) & 0xF))
        else:
            _undo_move()
    return out


def play_move(from_sq, to_sq, promo):
    moves = generate_moves(False)
    for m in moves:
        if (m & 0x7F) == from_sq and ((m >> 7) & 0x7F) == to_sq and ((m >> 14) & 0xF) == promo:
            _make_move(m)
            if _is_illegal():
                _undo_move()
                return False
            return True
    return False


def search_best_move(max_depth, time_ms):
    """Returns (from, to, promo). from = 0x80 if no move."""
    global time_budget_ms
    if max_depth < 1: max_depth = 1
    if max_depth > MAX_PLY: max_depth = MAX_PLY
    time_budget_ms = time_ms if time_ms > 0 else 0
    _search_root(max_depth)
    if best_root_move:
        m = best_root_move
        return (m & 0x7F, (m >> 7) & 0x7F, (m >> 14) & 0xF)
    return (0x80, 0, 0)


def stop_search():
    global chal_stop_flag
    chal_stop_flag = 1


def undo_move():
    if ply <= 0:
        return False
    _undo_move()
    return True


def evaluate_position():
    return evaluate()


def is_in_check():
    return _in_check(side)


def is_checkmate():
    if not _in_check(side):
        return False
    moves = generate_moves(False)
    for m in moves:
        _make_move(m)
        if not _is_illegal():
            _undo_move()
            return False
        _undo_move()
    return True


def is_stalemate():
    if _in_check(side):
        return False
    moves = generate_moves(False)
    for m in moves:
        _make_move(m)
        if not _is_illegal():
            _undo_move()
            return False
        _undo_move()
    return True


def get_last_score():
    return last_search_score


def get_last_depth():
    return last_search_depth
