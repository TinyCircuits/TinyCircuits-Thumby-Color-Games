import engine_main # type: ignore
import engine # type: ignore
import engine_draw # type: ignore
import engine_io as btn # type: ignore
from engine_resources import TextureResource as txtr, FontResource as font # type: ignore
from engine_draw import Color, set_background # type: ignore
from engine_nodes import CameraNode, Sprite2DNode as sprt, Text2DNode as text # type: ignore
from engine_math import Vector2, Vector3 # type: ignore
from engine_animation import Delay
import engine_save # type: ignore
import math
import framebuf # type: ignore
import random

engine_save.set_location("save.data")

engine.fps_limit(30)

camera = CameraNode(position = Vector3(63, 63, 0))

tileTxtr = txtr("textures/tile.bmp")
flagTxtr = txtr("textures/flag.bmp")
zeroTxtr = txtr("textures/zero.bmp")
oneTxtr = txtr("textures/one.bmp")
twoTxtr = txtr("textures/two.bmp")
threeTxtr = txtr("textures/three.bmp")
fourTxtr = txtr("textures/four.bmp")
fiveTxtr = txtr("textures/five.bmp")
sixTxtr = txtr("textures/six.bmp")
sevenTxtr = txtr("textures/seven.bmp")
eightTxtr = txtr("textures/eight.bmp")
selectTxtr = txtr("textures/select.bmp")

fontTxtr = font("textures/5x7Font.bmp")

screen = txtr(128, 128, 0, 16)

select = sprt(position = Vector2(0, 0),
            texture = selectTxtr,
            transparent_color = Color(0, 0, 0),
            opacity = 0,
            layer = 10)

topTxt = text(position = Vector2(63, 60),
           font = fontTxtr,
           text = "Set Bomb Count",
           scale = Vector2(1, 1),
           letter_spacing = 1,
           color = Color(1, 1, 1),
           layer = 10)
totalTxt = text(position = Vector2(63, 70),
           font = fontTxtr,
           text = "36 / 196",
           scale = Vector2(1, 1),
           letter_spacing = 1,
           color = Color(1, 1, 1),
           layer = 10)

def color(r,g,b):
    rgb565 = ((r & 0xF8) << 8) | ((g & 0xFC) << 3) | (b >> 3)
    return rgb565

fb = engine_draw.front_fb()
#fbuf = framebuf.FrameBuffer(bytearray(128 * 128 * 2), 128, 128, framebuf.RGB565)
fbuf = framebuf.FrameBuffer(screen.data, 128, 128, framebuf.RGB565)
tile = framebuf.FrameBuffer(tileTxtr.data, tileTxtr.width, tileTxtr.height, framebuf.RGB565)
flag = framebuf.FrameBuffer(flagTxtr.data, flagTxtr.width, flagTxtr.height, framebuf.RGB565)
zero = framebuf.FrameBuffer(zeroTxtr.data, zeroTxtr.width, zeroTxtr.height, framebuf.RGB565)
one = framebuf.FrameBuffer(oneTxtr.data, oneTxtr.width, oneTxtr.height, framebuf.RGB565)
two = framebuf.FrameBuffer(twoTxtr.data, twoTxtr.width, twoTxtr.height, framebuf.RGB565)
three = framebuf.FrameBuffer(threeTxtr.data, threeTxtr.width, threeTxtr.height, framebuf.RGB565)
four = framebuf.FrameBuffer(fourTxtr.data, fourTxtr.width, fourTxtr.height, framebuf.RGB565)
five = framebuf.FrameBuffer(fiveTxtr.data, fiveTxtr.width, fiveTxtr.height, framebuf.RGB565)
six = framebuf.FrameBuffer(sixTxtr.data, sixTxtr.width, sixTxtr.height, framebuf.RGB565)
seven = framebuf.FrameBuffer(sevenTxtr.data, sevenTxtr.width, sevenTxtr.height, framebuf.RGB565)
eight = framebuf.FrameBuffer(eightTxtr.data, eightTxtr.width, eightTxtr.height, framebuf.RGB565)

Screen = sprt(position = Vector2(63, 63),
            texture = screen,
            layer = 1)

rumble_delay = Delay()
def rumble(intensity=0.5, delay=90):
    btn.rumble(intensity)
    rumble_delay.start(delay, lambda _: btn.rumble(0.0))


grid = []
bomb = []

total = int(engine_save.load("total", 36))

while True:
    if engine.tick():
        totalTxt.text = f'{total} / 196'
        if btn.UP.is_just_pressed or btn.RIGHT.is_just_pressed:
            if total < 196:
                total += 1
        elif btn.DOWN.is_just_pressed or btn.LEFT.is_just_pressed:
            if total > 0:
                total -= 1
        elif btn.A.is_just_pressed:
            break
        engine.tick()
    
engine_save.save("total", round(total))
select.opacity = 1
totalTxt.opacity = 0
topTxt.opacity = 0


def reset():
    global grid
    global bomb
    global total
    grid = [[9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9],
            [9,9,9,9,9,9,9,9,9,9,9,9,9,9]]

    bomb = [[0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],
            [0,0,0,0,0,0,0,0,0,0,0,0,0,0],]

    count = total

    while count > 0:
        x = random.randint(0, 13)
        y = random.randint(0, 13)
        if bomb[y][x] == 0:
            bomb[y][x] = 1
            count -= 1
            
reset()


def draw():
    fbuf.rect(-1, -1, 128, 128, color(0, 0, 0), 1)
    for y in range(len(grid)):
        for x in range(len(grid[y])):
            if grid[y][x] == 9:
                fbuf.blit(tile, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 10:
                fbuf.blit(flag, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 0:
                fbuf.blit(zero, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 1:
                fbuf.blit(one, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 2:
                fbuf.blit(two, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 3:
                fbuf.blit(three, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 4:
                fbuf.blit(four, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 5:
                fbuf.blit(five, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 6:
                fbuf.blit(six, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 7:
                fbuf.blit(seven, x * 9 + 1, y * 9 + 1)
            elif grid[y][x] == 8:
                fbuf.blit(eight, x * 9 + 1, y * 9 + 1)
                

posX = 6
posY = 6


def countSurrounding(x, y, bomb, check):
    count = 0
    if x > 0 and y > 0:
        if bomb[y - 1][x - 1] == check:
            count += 1
    if y > 0:
        if bomb[y - 1][x] == check:
            count += 1
    if x < 13 and y > 0:
        if bomb[y - 1][x + 1] == check:
            count += 1
    if x > 0:
        if bomb[y][x - 1] == check:
            count += 1
    if x < 13:
        if bomb[y][x + 1] == check:
            count += 1
    if x > 0 and y < 13:
        if bomb[y + 1][x - 1] == check:
            count += 1
    if y < 13:
        if bomb[y + 1][x] == check:
            count += 1
    if x < 13 and y < 13:
        if bomb[y + 1][x + 1] == check:
            count += 1
    return count

def replaceSurrounding(x, y, replaceTarget, replaceValue):
        global grid
        if x > 0 and y > 0:
            if grid[y - 1][x - 1] == replaceTarget:
                grid[y - 1][x - 1] = replaceValue
        if y > 0:
            if grid[y - 1][x] == replaceTarget:
                grid[y - 1][x] = replaceValue
        if x < 13 and y > 0:
            if grid[y - 1][x + 1] == replaceTarget:
                grid[y - 1][x + 1] = replaceValue
        if x > 0:
            if grid[y][x - 1] == replaceTarget:
                grid[y][x - 1] = replaceValue
        if x < 13:
            if grid[y][x + 1] == replaceTarget:
                grid[y][x + 1] = replaceValue
        if x > 0 and y < 13:
            if grid[y + 1][x - 1] == replaceTarget:
                grid[y + 1][x - 1] = replaceValue
        if y < 13:
            if grid[y + 1][x] == replaceTarget:
                grid[y + 1][x] = replaceValue
        if x < 13 and y < 13:
            if grid[y + 1][x + 1] == replaceTarget:
                grid[y + 1][x + 1] = replaceValue

def sweep(x, y, bomb, check):
    global grid
    count = countSurrounding(x, y, bomb, 1)
    flag = countSurrounding(x, y, grid, 10)
  
    if count == 0 or check == flag:
        replaceSurrounding(x, y, 9, -1)
        
    
    return count

def clear():
    global grid
    global bomb
    for row in range(len(grid)):
        if min(grid[row]) == -1:
            for column in range(len(grid[row])):
                if grid[row][column] == -1:
                    if bomb[row][column] == 1:
                       reset()
                       break
                    grid[row][column] = sweep(column, row, bomb, 9)

def hasWon():
    global grid
    global bomb
    global total
    flag = 0
    for row in range(len(grid)):
        for column in range(len(grid[row])):
            if (grid[row][column] == 9 or grid[row][column] == 10) and bomb[row][column] == 0:
                return False
    return True

while True:
    if engine.tick():
        
        if hasWon():
            
            topTxt.opacity = 1
            topTxt.text = 'You Win!'
            
            if btn.A.is_just_pressed:
                reset()
                topTxt.opacity = 0
            elif btn.MENU.is_just_pressed:
                break
            
            continue
            
        
        
        if btn.MENU.is_just_pressed:
            break
        elif btn.UP.is_pressed_autorepeat:
            if posY > 0:
                posY -= 1
            else:
                posY = 13
        elif btn.DOWN.is_pressed_autorepeat:
            if posY < 13:
                posY += 1
            else:
                posY = 0
        elif btn.LEFT.is_pressed_autorepeat:
            if posX > 0:
                posX -= 1
            else:
                posX = 13
        elif btn.RIGHT.is_pressed_autorepeat:
            if posX < 13:
                posX += 1
            else:
                posX = 0
        elif btn.B.is_just_pressed:
            if grid[posY][posX] == 9:
                grid[posY][posX] = 10
            elif grid[posY][posX] == 10:
                grid[posY][posX] = 9
            elif grid[posY][posX] == countSurrounding(posX, posY, grid, 9) + countSurrounding(posX, posY, grid, 10):
                replaceSurrounding(posX, posY, 9, 10)
        elif btn.A.is_just_pressed:
            if grid[posY][posX] < 10 and grid[posY][posX] > 0:
                if bomb[posY][posX] == 1:
                    rumble()
                    reset()
                else:
                    grid[posY][posX] = sweep(posX, posY, bomb, grid[posY][posX])
                 

        clear()
        
        select.position = Vector2(posX * 9 + 5, posY * 9 + 5)
        draw()
        #fb.blit(fbuf,0,0)
        engine.tick()
