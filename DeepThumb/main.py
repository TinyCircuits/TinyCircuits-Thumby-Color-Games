"""
DeepThumb (pure Python edition)

A faithful re-implementation of the original C-firmware DeepThumb game,
running entirely in MicroPython with a pure-Python port of the Chal
chess engine. No custom firmware required.

Engine: chal.py (faithful port of TinyCircuits-Tiny-Game-Engine/chess/chal.c)
"""

import engine_main
import engine
import engine_io
import engine_audio
import engine_save
import gc
import time
import framebuf

from engine_math import Vector2
from engine_nodes import CameraNode, Sprite2DNode
from engine_resources import TextureResource, WaveSoundResource

# Allocate the 32KB framebuffer FIRST while the heap is empty and
# unfragmented — chal.py's module-level tables would otherwise leave no
# contiguous slot big enough for it.
gc.collect()
screen_tex = TextureResource(128, 128, 0, 16)
gc.collect()

import chal

# ===============================================================
# Constants
# ===============================================================

SCREEN_W = 128
SCREEN_H = 128
TILE = 16

COLOR_LIGHT      = 0xEF3C
COLOR_DARK       = 0x8C51
COLOR_CURSOR     = 0x07FF
COLOR_SELECTED   = 0xFFE0
COLOR_VALID_MOVE = 0x47E0
COLOR_BG         = 0x2104
COLOR_TEXT_WHITE = 0xFFFF
COLOR_TEXT_DIM   = 0x8410
COLOR_HL_ROW     = 0x2945
COLOR_GREEN      = 0x07E0
COLOR_RED        = 0xF800

# Sprite sheet column indices
SPRITE_ROOK   = 0
SPRITE_KNIGHT = 1
SPRITE_BISHOP = 2
SPRITE_KING   = 3
SPRITE_QUEEN  = 4
SPRITE_PAWN   = 5
TRANSPARENT_COLOR = 0xFFFF

# Difficulty
chal_depth = (1, 2, 4, 6, 64)
chal_time  = (200, 500, 1500, 3000, 8000)
chal_elo   = ("~800", "~1200", "~1600", "~1900", "~2200")
diff_names = ("BEGINNER", "EASY", "MEDIUM", "HARD", "EXPERT")
NUM_DIFF   = 5

# Game states
ST_TITLE       = 0
ST_SETUP       = 1
ST_PLAYER_TURN = 2
ST_AI_THINKING = 3
ST_GAME_OVER   = 4

# Pause menu
PAUSE_RESUME = 0
PAUSE_SOUND  = 1
PAUSE_EVAL   = 2
PAUSE_SAVE   = 3
PAUSE_QUIT   = 4
PAUSE_COUNT  = 5

# ===============================================================
# Engine setup
# ===============================================================

engine.fps_limit(30)
engine_audio.set_volume(0.5)

# Load assets
sprite_tex = TextureResource("chess.bmp")
board_tex  = TextureResource("board.bmp")

snd_move = WaveSoundResource("move.wav")
snd_take = WaveSoundResource("take.wav")
snd_pawn = WaveSoundResource("pawn.wav")

# screen_tex was allocated above, before chal import.
fbuf = framebuf.FrameBuffer(screen_tex.data, SCREEN_W, SCREEN_H, framebuf.RGB565)

camera = CameraNode()
screen_sprite = Sprite2DNode(texture=screen_tex, position=Vector2(0, 0), layer=0)
camera.add_child(screen_sprite)

# Raw access pointers for the framebuffer
_screen_data = screen_tex.data            # bytearray, 2 bytes per pixel
_sprite_data = sprite_tex.data
_board_data  = board_tex.data
_sprite_w = sprite_tex.width
_board_w  = board_tex.width

# Initialise the chess engine
gc.collect()
chal.init(256)


# ===============================================================
# Pixel-level rendering helpers
# ===============================================================

@micropython.viper
def _put_px(x: int, y: int, color: int):
    if x < 0 or x >= 128 or y < 0 or y >= 128:
        return
    buf = ptr16(_screen_data)
    buf[x + (y << 7)] = color


@micropython.viper
def _fill_rect(x: int, y: int, w: int, h: int, color: int):
    buf = ptr16(_screen_data)
    x0 = x
    y0 = y
    x1 = x + w
    y1 = y + h
    if x0 < 0: x0 = 0
    if y0 < 0: y0 = 0
    if x1 > 128: x1 = 128
    if y1 > 128: y1 = 128
    yy = y0
    while yy < y1:
        row = yy << 7
        xx = x0
        while xx < x1:
            buf[row + xx] = color
            xx += 1
        yy += 1


@micropython.viper
def _draw_rect_outline(x: int, y: int, w: int, h: int, color: int):
    buf = ptr16(_screen_data)
    x1 = x + w - 1
    y1 = y + h - 1
    i = x
    while i <= x1:
        if i >= 0 and i < 128:
            if y >= 0 and y < 128:  buf[(y << 7) + i]  = color
            if y1 >= 0 and y1 < 128: buf[(y1 << 7) + i] = color
        i += 1
    j = y
    while j <= y1:
        if j >= 0 and j < 128:
            if x >= 0 and x < 128:  buf[(j << 7) + x]  = color
            if x1 >= 0 and x1 < 128: buf[(j << 7) + x1] = color
        j += 1


@micropython.viper
def _blit_sprite(sx: int, sy: int, src_x: int, src_y: int, sw: int):
    """Blit a 16x16 tile from sprite sheet at (src_x, src_y) into screen at (sx, sy)."""
    dst = ptr16(_screen_data)
    src = ptr16(_sprite_data)
    transparent = 0xFFFF
    row = 0
    while row < 16:
        dy = sy + row
        if dy >= 0 and dy < 128:
            sy_off = (src_y + row) * sw
            dy_off = dy << 7
            col = 0
            while col < 16:
                dx = sx + col
                if dx >= 0 and dx < 128:
                    pixel = src[sy_off + src_x + col]
                    if pixel != transparent:
                        dst[dy_off + dx] = pixel
                col += 1
        row += 1


@micropython.viper
def _blit_tile(sx: int, sy: int, src_x: int, sw: int):
    """Blit a 16x16 board tile (no transparency) at column src_x of board.bmp."""
    dst = ptr16(_screen_data)
    src = ptr16(_board_data)
    row = 0
    while row < 16:
        dy = sy + row
        if dy >= 0 and dy < 128:
            sy_off = row * sw
            dy_off = dy << 7
            col = 0
            while col < 16:
                dx = sx + col
                if dx >= 0 and dx < 128:
                    dst[dy_off + dx] = src[sy_off + src_x + col]
                col += 1
        row += 1


@micropython.viper
def _darken_screen():
    buf = ptr16(_screen_data)
    i = 0
    n = 128 * 128
    while i < n:
        p = buf[i]
        r = (p >> 12) & 0x0F
        g = (p >> 6) & 0x1F
        b = (p >> 1) & 0x0F
        buf[i] = (r << 11) | (g << 5) | b
        i += 1


# ===============================================================
# Tiny 4x6 font (subset matching the C version)
# ===============================================================

# Each glyph is 6 bytes (rows), bits 3..0 = pixels left to right.
_FONT = (
    b"\x00\x00\x00\x00\x00\x00",  # 32 space
    b"\x04\x04\x04\x00\x04\x00",  # !
    b"\x0A\x0A\x00\x00\x00\x00",  # "
    b"\x0A\x0F\x0A\x0F\x0A\x00",  # #
    b"\x04\x0E\x0C\x06\x0E\x04",  # $
    b"\x09\x02\x04\x09\x00\x00",  # %
    b"\x04\x0A\x04\x0A\x05\x00",  # &
    b"\x04\x04\x00\x00\x00\x00",  # '
    b"\x02\x04\x04\x04\x02\x00",  # (
    b"\x04\x02\x02\x02\x04\x00",  # )
    b"\x00\x0A\x04\x0A\x00\x00",  # *
    b"\x00\x04\x0E\x04\x00\x00",  # +
    b"\x00\x00\x00\x04\x04\x08",  # ,
    b"\x00\x00\x0E\x00\x00\x00",  # -
    b"\x00\x00\x00\x00\x04\x00",  # .
    b"\x01\x02\x04\x08\x00\x00",  # /
    b"\x06\x09\x09\x09\x06\x00",  # 0
    b"\x04\x0C\x04\x04\x0E\x00",  # 1
    b"\x06\x09\x02\x04\x0F\x00",  # 2
    b"\x0E\x01\x06\x01\x0E\x00",  # 3
    b"\x02\x06\x0A\x0F\x02\x00",  # 4
    b"\x0F\x08\x0E\x01\x0E\x00",  # 5
    b"\x06\x08\x0E\x09\x06\x00",  # 6
    b"\x0F\x01\x02\x04\x04\x00",  # 7
    b"\x06\x09\x06\x09\x06\x00",  # 8
    b"\x06\x09\x07\x01\x06\x00",  # 9
    b"\x00\x04\x00\x04\x00\x00",  # :
    b"\x00\x04\x00\x04\x08\x00",  # ;
    b"\x01\x02\x04\x02\x01\x00",  # <
    b"\x00\x0E\x00\x0E\x00\x00",  # =
    b"\x04\x02\x01\x02\x04\x00",  # >
    b"\x06\x09\x02\x00\x02\x00",  # ?
    b"\x06\x09\x0B\x08\x06\x00",  # @
    b"\x06\x09\x0F\x09\x09\x00",  # A
    b"\x0E\x09\x0E\x09\x0E\x00",  # B
    b"\x07\x08\x08\x08\x07\x00",  # C
    b"\x0E\x09\x09\x09\x0E\x00",  # D
    b"\x0F\x08\x0E\x08\x0F\x00",  # E
    b"\x0F\x08\x0E\x08\x08\x00",  # F
    b"\x07\x08\x0B\x09\x07\x00",  # G
    b"\x09\x09\x0F\x09\x09\x00",  # H
    b"\x0E\x04\x04\x04\x0E\x00",  # I
    b"\x07\x01\x01\x09\x06\x00",  # J
    b"\x09\x0A\x0C\x0A\x09\x00",  # K
    b"\x08\x08\x08\x08\x0F\x00",  # L
    b"\x09\x0F\x0F\x09\x09\x00",  # M
    b"\x09\x0D\x0B\x09\x09\x00",  # N
    b"\x06\x09\x09\x09\x06\x00",  # O
    b"\x0E\x09\x0E\x08\x08\x00",  # P
    b"\x06\x09\x09\x0A\x05\x00",  # Q
    b"\x0E\x09\x0E\x0A\x09\x00",  # R
    b"\x07\x08\x06\x01\x0E\x00",  # S
    b"\x0F\x04\x04\x04\x04\x00",  # T
    b"\x09\x09\x09\x09\x06\x00",  # U
    b"\x09\x09\x09\x06\x06\x00",  # V
    b"\x09\x09\x0F\x0F\x09\x00",  # W
    b"\x09\x06\x06\x06\x09\x00",  # X
    b"\x09\x09\x07\x01\x06\x00",  # Y
    b"\x0F\x02\x04\x08\x0F\x00",  # Z
)


def _draw_char(x, y, c, color):
    o = ord(c)
    if o < 32 or o > 90:
        return
    glyph = _FONT[o - 32]
    for row in range(6):
        bits = glyph[row]
        for col in range(4):
            if bits & (8 >> col):
                _put_px(x + col, y + row, color)


def draw_text(x, y, s, color):
    for c in s:
        if 'a' <= c <= 'z':
            c = chr(ord(c) - 32)
        _draw_char(x, y, c, color)
        x += 5


# ===============================================================
# Board → screen mapping helpers
# ===============================================================
# game.cursor_rank uses the same convention as the C version:
#   rank 0 = top of board on screen, rank 7 = bottom on screen
# (which corresponds to chal's rank 8 .. rank 1).
# In chal's indexing, rank 0 = chal-rank 8.
# So game_rank == chal_rank when chal's get_piece(rank, file) is called directly.
# (chal.get_piece(0, ...) returns rank 8.)
# Sprite-row in chess.bmp: sprite_row 0 = white (bottom 16 of bmp -> top 16 after flip),
# sprite_row 1 = black (top 16 of bmp -> bottom 16 after flip).
# Effective: black -> src_y=0, white -> src_y=16
def _piece_sprite_col(piece):
    pt = piece & 7
    if pt == chal.PAWN:   return SPRITE_PAWN
    if pt == chal.KNIGHT: return SPRITE_KNIGHT
    if pt == chal.BISHOP: return SPRITE_BISHOP
    if pt == chal.ROOK:   return SPRITE_ROOK
    if pt == chal.QUEEN:  return SPRITE_QUEEN
    if pt == chal.KING:   return SPRITE_KING
    return -1


def _draw_piece_at(screen_x, screen_y, piece):
    col_idx = _piece_sprite_col(piece)
    if col_idx < 0:
        return
    is_black = (piece & 8) != 0
    src_x = col_idx * TILE
    src_y = 0 if is_black else TILE
    _blit_sprite(screen_x, screen_y, src_x, src_y, _sprite_w)


def _game_to_0x88(rank, file):
    return ((7 - rank) * 16) + file


# ===============================================================
# Game state
# ===============================================================

class Game:
    def __init__(self):
        self.state = ST_TITLE
        self.player_is_white = 1
        self.difficulty = 1
        self.cursor_file = 4
        self.cursor_rank = 6
        self.selected = 0
        self.sel_file = 0
        self.sel_rank = 0
        self.legal_targets = []     # list of (to_sq, promo)
        self.has_last_move = 0
        self.last_from_file = 0
        self.last_from_rank = 0
        self.last_to_file = 0
        self.last_to_rank = 0
        self.result = 0
        self.winner_is_white = 0
        self.think_frame = 0
        self.eval_score = 0
        self.sound_on = 1
        self.show_eval_bar = 0
        self.paused = 0
        self.pause_cursor = 0
        self.move_count = 0
        self.title_init_done = 0


game = Game()


# ===============================================================
# Sound helpers
# ===============================================================

def play_sound(snd):
    if not game.sound_on or snd is None:
        return
    try:
        engine_audio.play(snd, 0, False)
    except Exception:
        pass


# ===============================================================
# Save/load
# ===============================================================

def init_save():
    engine_save.set_location("deepthumb.sav")


def save_game():
    init_save()
    fen = chal.get_fen()
    engine_save.save("fen", fen)
    engine_save.save("diff", game.difficulty)
    engine_save.save("white", game.player_is_white)
    engine_save.save("moves", game.move_count)


def clear_save():
    init_save()
    try:
        engine_save.delete("fen")
    except Exception:
        pass


def load_game():
    init_save()
    fen = engine_save.load("fen", None)
    if not fen:
        return False
    diff  = engine_save.load("diff", 1)
    white = engine_save.load("white", 1)
    moves = engine_save.load("moves", 0)
    game.difficulty = int(diff)
    game.player_is_white = int(white)
    game.move_count = int(moves)
    chal.set_fen(fen)
    game.cursor_file = 4
    game.cursor_rank = 6 if game.player_is_white else 1
    game.selected = 0
    game.legal_targets = []
    game.has_last_move = 0
    game.result = 0
    update_eval()
    return True


# ===============================================================
# Move helpers
# ===============================================================

def is_player_turn():
    s = chal.get_side()
    return (game.player_is_white and s == chal.WHITE) or \
           (not game.player_is_white and s == chal.BLACK)


def update_legal_for_selection():
    game.legal_targets = []
    from_sq = _game_to_0x88(game.sel_rank, game.sel_file)
    for f, t, p in chal.get_legal_moves():
        if f == from_sq:
            game.legal_targets.append((t, p))


def is_valid_target(file, rank):
    to_sq = _game_to_0x88(rank, file)
    for t, p in game.legal_targets:
        if t == to_sq:
            return True
    return False


def update_eval():
    ev = chal.evaluate_position()
    game.eval_score = ev if chal.get_side() == chal.WHITE else -ev


def check_game_end():
    if chal.is_checkmate():
        game.result = 1
        game.winner_is_white = (chal.get_side() == chal.BLACK)
        enter_state(ST_GAME_OVER)
    elif chal.is_stalemate():
        game.result = 2
        game.winner_is_white = -1
        enter_state(ST_GAME_OVER)


def enter_state(s):
    game.state = s
    game.think_frame = 0


def do_undo():
    if game.move_count < 2:
        return
    if chal.undo_move():
        game.move_count -= 1
    if chal.undo_move():
        game.move_count -= 1
    game.selected = 0
    game.legal_targets = []
    game.has_last_move = 0
    update_eval()


# ===============================================================
# Drawing
# ===============================================================

def draw_board():
    flip = not game.player_is_white
    for rank in range(8):
        for file in range(8):
            display_rank = (7 - rank) if flip else rank
            display_file = (7 - file) if flip else file
            sx = display_file * TILE
            sy = display_rank * TILE
            is_dark = (rank + file) & 1
            _blit_tile(sx, sy, is_dark * TILE, _board_w)

            # Last move highlight
            if game.has_last_move:
                if (file == game.last_from_file and rank == game.last_from_rank) or \
                   (file == game.last_to_file   and rank == game.last_to_rank):
                    _draw_rect_outline(sx, sy, TILE, TILE, COLOR_SELECTED)

            # Selected highlight
            if game.selected and file == game.sel_file and rank == game.sel_rank:
                _fill_rect(sx + 1, sy + 1, TILE - 2, TILE - 2, COLOR_SELECTED)

            # Valid move dots
            if game.selected and is_valid_target(file, rank):
                p = chal.get_piece(rank, file)
                if (p & 7) == chal.EMPTY:
                    _fill_rect(sx + 6, sy + 6, 4, 4, COLOR_VALID_MOVE)
                else:
                    _fill_rect(sx,      sy,      3, 3, COLOR_VALID_MOVE)
                    _fill_rect(sx + 13, sy,      3, 3, COLOR_VALID_MOVE)
                    _fill_rect(sx,      sy + 13, 3, 3, COLOR_VALID_MOVE)
                    _fill_rect(sx + 13, sy + 13, 3, 3, COLOR_VALID_MOVE)

            piece = chal.get_piece(rank, file)
            if (piece & 7) != chal.EMPTY:
                _draw_piece_at(sx, sy, piece)

    # Cursor
    df = game.cursor_file if game.player_is_white else (7 - game.cursor_file)
    dr = game.cursor_rank if game.player_is_white else (7 - game.cursor_rank)
    cx = df * TILE
    cy = dr * TILE
    _draw_rect_outline(cx,     cy,     TILE,     TILE,     COLOR_CURSOR)
    _draw_rect_outline(cx + 1, cy + 1, TILE - 2, TILE - 2, COLOR_CURSOR)


def draw_board_backdrop():
    for rank in range(8):
        for file in range(8):
            sx = file * TILE
            sy = rank * TILE
            is_dark = (rank + file) & 1
            _blit_tile(sx, sy, is_dark * TILE, _board_w)
            piece = chal.get_piece(rank, file)
            if (piece & 7) != chal.EMPTY:
                _draw_piece_at(sx, sy, piece)


def draw_eval_bar():
    if not game.show_eval_bar:
        return
    score = game.eval_score
    if score > 500: score = 500
    if score < -500: score = -500
    mid = SCREEN_H // 2
    bar_h = (score * mid) // 500
    _fill_rect(0, 0, 4, SCREEN_H, COLOR_BG)
    white_top = mid - bar_h
    if white_top < 0: white_top = 0
    if white_top > SCREEN_H: white_top = SCREEN_H
    _fill_rect(0, white_top, 4, SCREEN_H - white_top, 0xFFFF)
    for x in range(4):
        _put_px(x, mid, COLOR_TEXT_DIM)


# ===============================================================
# Pause menu
# ===============================================================

def draw_pause_menu():
    _fill_rect(14, 16, 100, 96, COLOR_BG)
    _draw_rect_outline(14, 16, 100, 96, COLOR_TEXT_WHITE)
    draw_text(36, 20, "PAUSED", COLOR_TEXT_WHITE)
    for x in range(20, 108):
        _put_px(x, 29, COLOR_TEXT_DIM)
    items = ("RESUME", "SOUND", "EVAL BAR", "SAVE+QUIT", "QUIT")
    vals  = ("",
             "ON" if game.sound_on else "OFF",
             "ON" if game.show_eval_bar else "OFF",
             "", "")
    for i in range(PAUSE_COUNT):
        y = 34 + i * 13
        color = COLOR_TEXT_WHITE if i == game.pause_cursor else COLOR_TEXT_DIM
        if i == game.pause_cursor:
            _fill_rect(18, y - 1, 92, 11, COLOR_HL_ROW)
        draw_text(24, y, items[i], color)
        if vals[i]:
            draw_text(76, y, vals[i], COLOR_GREEN)


def handle_pause_menu():
    """Returns 1 if we should leave to title."""
    if engine_io.UP.is_just_pressed:
        game.pause_cursor = (game.pause_cursor + PAUSE_COUNT - 1) % PAUSE_COUNT
    if engine_io.DOWN.is_just_pressed:
        game.pause_cursor = (game.pause_cursor + 1) % PAUSE_COUNT
    if engine_io.A.is_just_pressed:
        c = game.pause_cursor
        if c == PAUSE_RESUME:
            game.paused = 0
        elif c == PAUSE_SOUND:
            game.sound_on = 0 if game.sound_on else 1
        elif c == PAUSE_EVAL:
            game.show_eval_bar = 0 if game.show_eval_bar else 1
        elif c == PAUSE_SAVE:
            save_game()
            return 1
        elif c == PAUSE_QUIT:
            clear_save()
            return 1
    if engine_io.MENU.is_just_pressed or engine_io.B.is_just_pressed:
        game.paused = 0
    return 0


# ===============================================================
# Player action: select / move
# ===============================================================

def do_player_select():
    cursor_piece = chal.get_piece(game.cursor_rank, game.cursor_file)

    if game.selected:
        if is_valid_target(game.cursor_file, game.cursor_rank):
            to_sq = _game_to_0x88(game.cursor_rank, game.cursor_file)
            from_sq = _game_to_0x88(game.sel_rank, game.sel_file)
            promo = 0
            for t, p in game.legal_targets:
                if t == to_sq:
                    promo = p
                    break
            moving_type = chal.get_piece(game.sel_rank, game.sel_file) & 7
            is_capture = (chal.get_piece(game.cursor_rank, game.cursor_file) & 7) != chal.EMPTY
            ok = chal.play_move(from_sq, to_sq, promo)
            if ok:
                if is_capture:
                    play_sound(snd_take)
                elif moving_type == chal.PAWN:
                    play_sound(snd_pawn)
                else:
                    play_sound(snd_move)
                game.has_last_move = 1
                game.last_from_file = game.sel_file
                game.last_from_rank = game.sel_rank
                game.last_to_file = game.cursor_file
                game.last_to_rank = game.cursor_rank
                game.selected = 0
                game.legal_targets = []
                game.move_count += 1
                update_eval()
                check_game_end()
                if game.state != ST_GAME_OVER:
                    enter_state(ST_AI_THINKING)
                return

        # Re-select own piece
        player_color_bit = 0 if game.player_is_white else 8
        if (cursor_piece & 7) != chal.EMPTY and (cursor_piece & 8) == player_color_bit:
            game.sel_file = game.cursor_file
            game.sel_rank = game.cursor_rank
            update_legal_for_selection()
            return

        game.selected = 0
        game.legal_targets = []
        return

    player_color_bit = 0 if game.player_is_white else 8
    if (cursor_piece & 7) != chal.EMPTY and (cursor_piece & 8) == player_color_bit:
        game.selected = 1
        game.sel_file = game.cursor_file
        game.sel_rank = game.cursor_rank
        update_legal_for_selection()


# ===============================================================
# State tick functions
# ===============================================================

def tick_title():
    if not game.title_init_done:
        chal.new_game()
        game.title_init_done = 1

    draw_board_backdrop()
    _darken_screen()
    draw_text(29, 34, "DEEPTHUMB", 0)
    draw_text(30, 33, "DEEPTHUMB", COLOR_TEXT_WHITE)
    draw_text(41, 47, "CHESS", 0)
    draw_text(42, 46, "CHESS", COLOR_TEXT_DIM)
    _fill_rect(16, 72, 96, 34, COLOR_BG)
    _draw_rect_outline(16, 72, 96, 34, COLOR_TEXT_DIM)
    draw_text(30, 76, "A: NEW GAME", COLOR_TEXT_WHITE)
    draw_text(30, 88, "B: CONTINUE", COLOR_TEXT_DIM)

    if engine_io.A.is_just_pressed:
        game.difficulty = 1
        game.player_is_white = 1
        enter_state(ST_SETUP)
    elif engine_io.B.is_just_pressed:
        if load_game():
            enter_state(ST_PLAYER_TURN)


def tick_setup():
    draw_board_backdrop()
    _darken_screen()

    _fill_rect(6, 8, 116, 112, COLOR_BG)
    _draw_rect_outline(6, 8, 116, 112, COLOR_TEXT_DIM)
    draw_text(30, 12, "NEW GAME", COLOR_TEXT_WHITE)
    for x in range(12, 116):
        _put_px(x, 21, COLOR_TEXT_DIM)

    draw_text(12, 25, "ENGINE", COLOR_TEXT_DIM)
    draw_text(55, 25, "CHAL.PY", COLOR_TEXT_WHITE)

    draw_text(12, 35, "SIDE", COLOR_TEXT_DIM)
    draw_text(55, 35, "WHITE" if game.player_is_white else "BLACK", COLOR_TEXT_WHITE)
    _draw_piece_at(102, 31, (chal.KING) if game.player_is_white else ((chal.BLACK << 3) | chal.KING))

    draw_text(12, 45, "LEVEL", COLOR_TEXT_DIM)
    draw_text(55, 45, diff_names[game.difficulty], COLOR_TEXT_WHITE)
    draw_text(12, 55, "ELO", COLOR_TEXT_DIM)
    draw_text(55, 55, chal_elo[game.difficulty], COLOR_GREEN)

    for x in range(12, 116):
        _put_px(x, 65, COLOR_TEXT_DIM)
    draw_text(12, 69, "UP/DN  LEVEL", COLOR_TEXT_DIM)
    draw_text(12, 78, "LT/RT  SIDE", COLOR_TEXT_DIM)

    _fill_rect(28, 100, 72, 14, COLOR_HL_ROW)
    _draw_rect_outline(28, 100, 72, 14, COLOR_TEXT_WHITE)
    draw_text(38, 104, "A: PLAY", COLOR_TEXT_WHITE)

    if engine_io.UP.is_just_pressed:
        game.difficulty = (game.difficulty + 1) % NUM_DIFF
    if engine_io.DOWN.is_just_pressed:
        game.difficulty = (game.difficulty + NUM_DIFF - 1) % NUM_DIFF
    if engine_io.LEFT.is_just_pressed or engine_io.RIGHT.is_just_pressed \
       or engine_io.LB.is_just_pressed or engine_io.RB.is_just_pressed:
        game.player_is_white = 0 if game.player_is_white else 1
        chal.new_game()  # refresh backdrop board

    if engine_io.A.is_just_pressed:
        chal.new_game()
        game.cursor_file = 4
        game.cursor_rank = 6 if game.player_is_white else 1
        game.selected = 0
        game.legal_targets = []
        game.has_last_move = 0
        game.result = 0
        game.move_count = 0
        update_eval()
        if is_player_turn():
            enter_state(ST_PLAYER_TURN)
        else:
            enter_state(ST_AI_THINKING)


def tick_player_turn():
    if game.paused:
        draw_board()
        draw_eval_bar()
        _darken_screen()
        draw_pause_menu()
        if handle_pause_menu():
            game.title_init_done = 0
            enter_state(ST_TITLE)
        return

    draw_board()
    draw_eval_bar()

    if engine_io.MENU.is_just_pressed:
        game.paused = 1
        game.pause_cursor = 0
        return

    # Direction handling — flipped board when playing black
    rank_dec = 7 if game.player_is_white else 1
    rank_inc = 1 if game.player_is_white else 7
    file_dec = 7 if game.player_is_white else 1
    file_inc = 1 if game.player_is_white else 7

    if engine_io.UP.is_just_pressed:
        game.cursor_rank = (game.cursor_rank + rank_dec) % 8
    if engine_io.DOWN.is_just_pressed:
        game.cursor_rank = (game.cursor_rank + rank_inc) % 8
    if engine_io.LEFT.is_just_pressed:
        game.cursor_file = (game.cursor_file + file_dec) % 8
    if engine_io.RIGHT.is_just_pressed:
        game.cursor_file = (game.cursor_file + file_inc) % 8

    if engine_io.A.is_just_pressed:
        do_player_select()

    if engine_io.B.is_just_pressed:
        if game.selected:
            game.selected = 0
            game.legal_targets = []
        else:
            do_undo()

    if engine_io.LB.is_just_pressed:
        do_undo()


def tick_ai_thinking():
    draw_board()
    _fill_rect(0, SCREEN_H - 10, SCREEN_W, 10, COLOR_BG)
    draw_text(30, SCREEN_H - 9, "THINKING...", COLOR_TEXT_WHITE)

    # Frame 0: render once so player sees the position; frame 1: search.
    game.think_frame += 1
    if game.think_frame < 2:
        return

    depth   = chal_depth[game.difficulty]
    time_ms = chal_time[game.difficulty]
    gc.collect()
    fr, to, pr = chal.search_best_move(depth, time_ms)

    if fr == 0x80:
        game.result = 2
        game.winner_is_white = game.player_is_white
        enter_state(ST_GAME_OVER)
        return

    game.has_last_move = 1
    # 0x88 -> game (rank,file)
    game.last_from_rank = 7 - (fr >> 4)
    game.last_from_file = fr & 7
    game.last_to_rank = 7 - (to >> 4)
    game.last_to_file = to & 7
    chal.play_move(fr, to, pr)
    game.move_count += 1
    play_sound(snd_move)
    update_eval()
    check_game_end()
    if game.state != ST_GAME_OVER:
        enter_state(ST_PLAYER_TURN)


def tick_game_over():
    draw_board()
    _fill_rect(14, 42, 100, 44, COLOR_BG)
    _draw_rect_outline(14, 42, 100, 44, COLOR_TEXT_WHITE)
    if game.result == 1:
        draw_text(27, 48, "CHECKMATE!", COLOR_TEXT_WHITE)
        if game.winner_is_white == game.player_is_white:
            draw_text(33, 58, "YOU WIN!", COLOR_GREEN)
        else:
            draw_text(30, 58, "YOU LOSE!", COLOR_RED)
    else:
        draw_text(33, 48, "STALEMATE", COLOR_TEXT_WHITE)
        draw_text(40, 58, "DRAW", COLOR_TEXT_DIM)
    _fill_rect(30, 70, 68, 12, COLOR_HL_ROW)
    _draw_rect_outline(30, 70, 68, 12, COLOR_TEXT_DIM)
    draw_text(33, 72, "A: AGAIN", COLOR_TEXT_WHITE)

    if engine_io.A.is_just_pressed:
        game.title_init_done = 0
        enter_state(ST_TITLE)


# ===============================================================
# Main loop
# ===============================================================

while True:
    if engine.tick():
        # MENU exits to launcher from title/setup
        if engine_io.MENU.is_just_pressed and game.state in (ST_TITLE, ST_SETUP):
            engine.end()
            break

        s = game.state
        if   s == ST_TITLE:       tick_title()
        elif s == ST_SETUP:       tick_setup()
        elif s == ST_PLAYER_TURN: tick_player_turn()
        elif s == ST_AI_THINKING: tick_ai_thinking()
        elif s == ST_GAME_OVER:   tick_game_over()
