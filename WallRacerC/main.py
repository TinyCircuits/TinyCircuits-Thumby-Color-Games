import os
import engine_main
import engine
from engine_nodes import EmptyNode, Rectangle2DNode, CameraNode, Text2DNode, Sprite2DNode
import engine_io
import gc
import framebuf
import engine_draw
import time
import random
from engine_math import Vector2
from engine_resources import FontResource, TextureResource
import math
import engine_link
import engine_save
import json
from gaclib import options
from gaclib import helper
from gaclib import highscore

# Const Definitions
GAME_NAME = "WallRacer"
VERSION = "V1.41"
SCREEN_WIDTH = 128
SCREEN_HEIGHT = 128
VIRTUAL_WIDTH = SCREEN_WIDTH * 2 
VIRTUAL_HEIGHT = SCREEN_HEIGHT * 2 
BYTES_PER_PIXEL = 2
BYTE_SIZE = VIRTUAL_WIDTH * VIRTUAL_HEIGHT * BYTES_PER_PIXEL
BONUS_FACTOR = 20  # points for collecting a bonus dot multiplied by speed
BONUS_DISTANCE = 20  # minimum distance between dots
BONUS_COUNT = 3  # number of bonus dots displayed
BONUS_TOLERANCE = 1  # how near the player needs to be to collect the bonus
BONUS_BORDER_DISTANCE = 10 # minimum distance from border for bonus points 
EXPLOSION_BITS = 72  # number of pixels in the explosion
EXPLOSION_STEPS = 20  # number of steps the explosion runs
EXPLOSION_RUMBLE = 0.4 # rumble intensity during explosion
POINTS_WON = 1000  # extra points for winning
BOOST_COOLDOWN = 80  # number of pixels to wait for next boost
BOOST_TIME = 40  # number of pixels to boost
BOOST_SPEED = 3  # increase of speed during boost
BOOST_RUMBLE = 0.2  # rumble intensity during boost
# map direction to offsets
PLAYERXADD = [1, 0, -1, 0]  # mapping of direction to x add
PLAYERYADD = [0, 1, 0, -1]  # mapping of direction to y add
START_POSITIONS = [
    [30, 30, 0],
    [30, VIRTUAL_HEIGHT - 30, 0],
    [VIRTUAL_WIDTH - 30, 30, 2],
    [VIRTUAL_WIDTH - 30, VIRTUAL_HEIGHT - 30, 2],
]

# game modes
MODE_FULL = 0
MODE_PURE = 1
MODE_LINK = 2

# message kind
KIND_SETTINGS = 1
KIND_COUNTDOWN = 2
KIND_PLAYER = 3
KIND_EXPLOSION = 4

# pages
PAGE_QUIT = 0
PAGE_TITLE = 1
PAGE_GAME = 2
PAGE_OPTIONS = 3
PAGE_WAITFORPLAYER = 4
PAGE_HIGHSCORE = 5
PAGE_ENTERHIGHSCORE = 6

# map engine colors to framebuffer
BLACK = engine_draw.black.value
GREEN = engine_draw.green.value
WHITE = engine_draw.white.value
RED = engine_draw.red.value
YELLOW = engine_draw.yellow.value
PINK = engine_draw.pink.value
GREY = engine_draw.darkgrey.value
GREYL = engine_draw.lightgrey.value
BLUE = engine_draw.blue.value
DARKGREEN = engine_draw.darkgreen.value
GREENYELLOW = engine_draw.greenyellow.value

# used colors
BACKGROUND = BLACK
FRAME1 = WHITE
FRAME2 = RED
PLAYER1 = GREEN
PLAYER1A = 0x0c64  # darkgreen
PLAYER1B = 0x4eec  # medium green
PLAYER1C = 0x7ff2  # light green
PLAYER2 = BLUE
PLAYER2A = 0x0291  # dark blue
PLAYER2B = 0x4479  # medium blue
PLAYER2C = 0x65bf  # light blue
EXPLOSION = RED
ANIMATION = [YELLOW, RED]


# uncomment and remove pass to activate logfile
# do not use print for multiplayer debugging
# it uses the same usb buffer
#logfile = open("/Games/1WallRacerC/WallRacerC.log", "a")
def log(msg):
    pass
    #global logfile
    #xmsg = str(time.ticks_ms()) + ": " + msg
    #logfile.write(xmsg + "\n")
    #logfile.flush()


# align node relative to a position
# 0 middle, 1 left/top 2 right/bottom
def align(textnode, x, y, xalign, yalign, xscreen=False, yscreen=False):
    if xalign == 1:
        if xscreen:
            x = -int(SCREEN_WIDTH // 2) + math.ceil(textnode.width / 2)
        else:
            x = x + math.ceil(textnode.width / 2)
    elif xalign == 2:
        if xscreen:
            x = int(SCREEN_WIDTH // 2) - math.ceil(textnode.width / 2)
        else:
            x = x - math.ceil(textnode.width / 2)
    if yalign == 1:
        if yscreen:
            y = -int(SCREEN_HEIGHT // 2) + math.ceil(textnode.height / 2) + 2
        else:
            y = y + math.ceil(textnode.height / 2)
    elif yalign == 2:
        if yscreen:
            y = int(SCREEN_HEIGHT // 2) - math.ceil(textnode.height / 2)
        else:
            y = y - math.ceil(textnode.height / 2)
    textnode.position = Vector2(x, y)


def print_memory_usage():
    gc.collect()
    free_memory = gc.mem_free()
    allocated_memory = gc.mem_alloc()
    total_memory = free_memory + allocated_memory
    print(f"Total Memory: {total_memory} bytes")
    print(f"Allocated Memory: {allocated_memory} bytes")
    print(f"Free Memory: {free_memory} bytes")
    print()

# Initialization
random.seed(time.ticks_ms())

camera = CameraNode()

# Virtual Screen and graphics
texture = TextureResource(VIRTUAL_WIDTH, VIRTUAL_HEIGHT,0,16)
virtual_screen = framebuf.FrameBuffer(texture.data, texture.width, texture.height, framebuf.RGB565)

# init fonts
os.chdir("/Games/WallRacerC")
font16 = FontResource("font16.bmp")
font6 = FontResource("font6x8.bmp")
logo = TextureResource("WallRacerCLogo.bmp")

def initHighscore():
    showtitle = helper.Text("Highscore", font16, Vector2(1.5, 1.5), GREEN )
    showsubtitle = helper.Format(font16, Vector2(1, 1), GREEN)
    showfooter = helper.Text("U/D Scroll A/B Exit",font6,Vector2(1, 1),YELLOW)
    showtable = helper.Format(font16, Vector2(1, 1), WHITE)
    letter = helper.Format(font16, Vector2(3, 3), GREY)
    entertitle = helper.Text("New\nHighscore", font16, Vector2(1.5, 1.5), GREEN )
    enterfooter = helper.Text("L/R Move Selection\nU/D Change Letter\nA/B Confirm",font6,Vector2(1, 1),YELLOW)
    
    score = highscore.highscore(showtitle, showsubtitle, showfooter, showtable, entertitle, enterfooter, letter, WHITE, 10, "wallracer.data")

    #register all possible highscore ids
    for mode in range(0,2):
        if mode == MODE_FULL:
            ext = "Full"
        else:
            ext = "Pure"            
        
        for speed in range(1,11):
            id=str(mode)+'-'+str(speed)
            name = ext +" Speed " + str(speed)
            score.register(id, name, 100, "GAC")
            
    return score 

def loadSettings():
    global game_mode
    global speed
    engine_save.set_location("wallracer.data")
    game_mode = engine_save.load("gamemode", 0)
    speed = engine_save.load("speed", 5) 
    
def saveSettings():
    global game_mode
    global speed
    engine_save.set_location("wallracer.data")
    engine_save.save("gamemode", game_mode)
    engine_save.save("speed", speed) 


# Global Vars
speed = 5  # speed of the game
boost = 0
bonus = []  # position of bonus dots
game_mode = MODE_FULL  # 0 = full with bonus dots 1 = pure 2 = multiplayer
player_x = 0
player_y = 0
player_direction = 0
lasthigh = "AAA"

loadSettings()
score = initHighscore()

# for multiplayer
won = False
first_player = True

# Add a bonus dot at random position but keep distance to other dots and player
def addBonus():
    global player_x
    global player_y

    ok = False

    while not ok:
        ok = True
        x = random.randint(BONUS_BORDER_DISTANCE, VIRTUAL_WIDTH - BONUS_BORDER_DISTANCE)
        y = random.randint(BONUS_BORDER_DISTANCE, VIRTUAL_HEIGHT - BONUS_BORDER_DISTANCE)

        # check distance to player
        if (
            (x >= player_x - BONUS_DISTANCE)
            and (x <= player_x + BONUS_DISTANCE)
            and (y >= player_y - BONUS_DISTANCE)
            and (y <= player_y + BONUS_DISTANCE)
        ):
            ok = False

        # check distance to other bonus
        for point in bonus:
            if (
                (x >= point[0] - BONUS_DISTANCE)
                and (x <= point[0] + BONUS_DISTANCE)
                and (y >= point[1] - BONUS_DISTANCE)
                and (y <= point[1] + BONUS_DISTANCE)
            ):
                ok = False

    point = [x, y]
    bonus.append(point)


# Add inital bonus
def initBonus():
    bonus.clear()
    for c in range(BONUS_COUNT):
        addBonus()


# Draw one bonus dot at x,y location
def drawBonus(x, y, animation):
    if animation == -1:
        color = BACKGROUND
    else:
        color = ANIMATION[int(animation // 5) % 2]

    # draw 3x3 dot
    for nx in range(x - 1, x + 2):
        virtual_screen.vline(nx, y - 1, 3, color)


# Draw all bonus dots from the list
def drawBonusList(animation):
    for point in bonus:
        drawBonus(point[0], point[1], animation)


# Check if a bonus is at location x,y if yes remove it from screen and return the index in the list
def checkBonus(x, y):
    hit = -1
    for index in range(len(bonus)):
        point = bonus[index]
        if (
            (x >= point[0] - BONUS_TOLERANCE)
            and (x <= point[0] + BONUS_TOLERANCE)
            and (y >= point[1] - BONUS_TOLERANCE)
            and (y <= point[1] + BONUS_TOLERANCE)
        ):
            # remove the bonus
            drawBonus(point[0], point[1], -1)
            hit = index
    return hit


def setStartPosition():
    global game_mode
    global player_x
    global player_y
    global player_direction

    if game_mode == MODE_LINK:
        if first_player:
            startpos = random.randint(0, 1)
        else:
            startpos = random.randint(2, 3)
    else:
        startpos = random.randint(0, 3)

    start = START_POSITIONS[startpos]
    player_x = start[0]
    player_y = start[1]
    player_direction = start[2]

#move arena sprite so the player is in the middle of the screen
def updateScreen(arena):
    global player_x
    global player_y

    # update screen
    screen_x = SCREEN_WIDTH - player_x
    screen_y = SCREEN_HEIGHT -  player_y

    arena.position = Vector2(screen_x,screen_y)

#wait for next frame and display it
def refreshScreen():
    sleep_time = engine.time_to_next_tick() / 1000
    time.sleep(sleep_time)
    engine.tick()


# send kind, x and y as 9 byte packet over usb
def sendXY(kind, ax, ay):
    buffer = bytearray(9)
    buffer[0] = kind
    x = int(ax)
    y = int(ay)

    buffer[1] = (x >> 24) & 0b11111111
    buffer[2] = (x >> 16) & 0b11111111
    buffer[3] = (x >> 8) & 0b11111111
    buffer[4] = (x >> 0) & 0b11111111

    buffer[5] = (y >> 24) & 0b11111111
    buffer[6] = (y >> 16) & 0b11111111
    buffer[7] = (y >> 8) & 0b11111111
    buffer[8] = (y >> 0) & 0b11111111

    engine_link.send(buffer)


# read 9 byte packet from usb and decode to kind, x and y
def recvXY():
    buffer = bytearray(9)
    engine_link.read_into(buffer, 9)

    kind = buffer[0]
    x = 0
    y = 0

    x = x | (buffer[1] << 24)
    x = x | (buffer[2] << 16)
    x = x | (buffer[3] << 8)
    x = x | (buffer[4] << 0)

    y = y | (buffer[5] << 24)
    y = y | (buffer[6] << 16)
    y = y | (buffer[7] << 8)
    y = y | (buffer[8] << 0)

    return kind, x, y


# draw a frame with alternating colors
def drawFrame(screen):
    screen.rect(0, 0, VIRTUAL_WIDTH , VIRTUAL_HEIGHT , FRAME1)

    lw = int(SCREEN_WIDTH / 4)
    c = int((VIRTUAL_WIDTH / (lw * 2)) )
    for step in range(c):
        screen.hline(lw + step * lw * 2, 0, lw, FRAME2)
        screen.hline(lw + step * lw * 2, VIRTUAL_HEIGHT - 1, lw, FRAME2)

    w = int(SCREEN_HEIGHT / 4)
    c = int((VIRTUAL_HEIGHT / (lw * 2)) )
    for step in range(c):
        screen.vline(0, lw + step * lw * 2, lw, FRAME2)
        screen.vline(VIRTUAL_WIDTH - 1, lw + step * lw * 2, lw, FRAME2)

#displasy the bonus for a short time
def displayBonus(points):
    text_bonus = Text2DNode(
        position=Vector2(0, -20),
        text="Bonus!",
        font=font16,
        line_spacing=1,
        color=WHITE,
        scale=Vector2(2, 2),
    )

    text_points = Text2DNode(
        position=Vector2(0, 20),
        text=str(points),
        font=font16,
        line_spacing=1,
        color=WHITE,
        scale=Vector2(2, 2),
    )

    refreshScreen()
    time.sleep(1)
    text_bonus.mark_destroy()
    text_points.mark_destroy()


def playerColor():
    global game_mode
    global first_player
    global boost
    
    if game_mode == MODE_LINK:
        if first_player:
            if boost < 0:
                color = PLAYER1A
            elif boost == 0:
                color = PLAYER1B
            else:
                color = PLAYER1C
        else:
            if boost < 0:
                color = PLAYER2A
            elif boost == 0:
                color = PLAYER2B
            else:
                color = PLAYER2C
    else:
        if first_player:
            color = PLAYER1
        else:
            color = PLAYER2
    return color        

def playGame():
    global texture
    global game_mode
    global speed
    global player_x
    global player_y
    global player_direction
    global virtual_screen
    global first_player
    global won
    global boost

    log("Game")

    engine.fps_limit(60)

    # Clear virtual screen
    virtual_screen.fill(BACKGROUND)
    # Add the frame
    drawFrame(virtual_screen)

    # start with cooldown
    boost = -BOOST_COOLDOWN

    # Initialize player position in one of the corners
    setStartPosition()

    # points player has collected for this game
    points = 0
    # used for bonus flashing and speed
    counter = 0

    # Bonus dots only for full game
    if game_mode == MODE_FULL:
        initBonus()

    # refresh speed
    throttle = 11 - speed

    #add a sprite displaying the virtual_screen
    arena = Sprite2DNode(texture=texture)
    updateScreen(arena)

    log("Loop")
    while True:
        if engine.tick():

            # Turn left on LB
            if engine_io.LB.is_just_pressed:
                player_direction = (player_direction - 1) % 4

            # Turn right on RB
            if engine_io.RB.is_just_pressed:
                player_direction = (player_direction + 1) % 4

            # Start boost on B
            if (game_mode == MODE_LINK) and (boost == 0) and engine_io.B.is_just_pressed:
                boost = BOOST_TIME
                throttle -= BOOST_SPEED
                engine_io.rumble(BOOST_RUMBLE)
                #limit throttle to max speed
                if throttle < 1:
                    throttle = 1

            # throttle player
            if counter % throttle == 0:
                # update boost
                if game_mode == MODE_LINK:
                    if boost < 0:
                        boost += 1
                    elif boost > 0:
                        boost -= 1
                        if boost == 0:
                            # return to normal speed
                            throttle = 11 - speed
                            engine_io.rumble(0)
                            # start cooldown
                            boost = -BOOST_COOLDOWN
                # calculate new player position
                player_x += PLAYERXADD[player_direction]
                player_y += PLAYERYADD[player_direction]

                # check for bonus
                if game_mode == MODE_FULL:
                    hit = checkBonus(player_x, player_y)
                    if hit >= 0:
                        # if hit remove the existing bonus and add a new one
                        del bonus[hit]
                        addBonus()
                        bonus_points = speed * BONUS_FACTOR
                        log("Bonus: " + str(bonus_points))
                        points += bonus_points
                        displayBonus(bonus_points)

                # check for crash
                if virtual_screen.pixel(player_x, player_y) != BACKGROUND:
                    # always in the middle of the screen
                    explosion(player_x, player_y, arena)
   
                    if game_mode == MODE_LINK:
                        won = False 
                        # send explosion
                        sendXY(KIND_EXPLOSION, player_x, player_y)

                    time.sleep(0.5)
                    break

                # Draw the player
                color = playerColor()
                virtual_screen.pixel(player_x, player_y, color)

                # increase points for survival
                points += 1

            # flash bonus points
            if game_mode == MODE_FULL:
                drawBonusList(counter)

            # muliplayer messages
            if game_mode == MODE_LINK:
                # first send own position
                sendXY(KIND_PLAYER, player_x, player_y)

                # now wait for position from other player
                while engine_link.available() < 9:
                    pass

                kind, x, y = recvXY()

                if kind == KIND_PLAYER:
                    # player position
                    if first_player:
                        virtual_screen.pixel(x, y, PLAYER2)
                    else:
                        virtual_screen.pixel(x, y, PLAYER1)
                elif kind == KIND_EXPLOSION:
                    # explosion of other player
                    explosion(x, y, arena)
                    won = True
                    points += POINTS_WON
                    time.sleep(0.5)
                    break

            counter += 1
            updateScreen(arena)
    
    # always stop rumble
    engine_io.rumble(0)
    
    #remove the arena sprite
    arena.mark_destroy()

    # clear all remaining messages in usb buffer for next game
    if game_mode == MODE_LINK:
        engine_link.clear_send()
        engine_link.clear_read()
    return points


def displayTitle():
    engine.fps_limit(60)

    logo_node = Sprite2DNode(
        position=Vector2(0, 80),
        texture=logo,
        opacity=0.0,
    )

    text1 = Text2DNode(
        position=Vector2(-50, 16),
        text="A\nB\nU\nM",
        font=font16,
        line_spacing=1,
        color=WHITE,
        scale=Vector2(1, 1),
        opacity=0.0,
    )
    text2 = Text2DNode(
        position=Vector2(10, 16),
        text="Start\nOptions\nHighscore\nQuit",
        font=font16,
        line_spacing=1,
        color=WHITE,
        scale=Vector2(1, 1),
        opacity=0.0,
    )

    page = 0
    count = 0

    ypos = 80
    opacity = 0

    while True:
        if engine.tick():
            logo_node.position = Vector2(0, ypos)
            logo_node.opacity = opacity
            if ypos > -40:
                ypos -= 1
            else:
                text1.opacity = 1
                text2.opacity = 1

            if opacity < 1:
                opacity = opacity + 0.002

            count += 1

            # check buttons
            if engine_io.A.is_just_pressed:
                if game_mode == MODE_LINK:
                    page = PAGE_WAITFORPLAYER
                else:
                    page = PAGE_GAME
                break
            if engine_io.B.is_just_pressed:
                page = PAGE_OPTIONS
                break
            if engine_io.MENU.is_just_pressed:
                page = PAGE_QUIT
                break
            if engine_io.UP.is_just_pressed:
                page = PAGE_HIGHSCORE
                break
    logo_node.mark_destroy()
    text1.mark_destroy()
    text2.mark_destroy()
    return page


def displayPoints(points):
    global won
    global game_mode

    if game_mode == MODE_LINK:
        if won:
            text = "Victory!"
        else:
            text = "Lost!"
    else:
        text = "Crash!"

    crash = Text2DNode(
        position=Vector2(0, -30),
        text=text,
        font=font16,
        color=WHITE,
        scale=Vector2(2, 2),
    )

    pointst = Text2DNode(
        position=Vector2(0, 0),
        text="Points",
        font=font16,
        color=WHITE,
        scale=Vector2(1, 1),
    )

    points = Text2DNode(
        position=Vector2(0, 20),
        text=str(points),
        font=font16,
        color=WHITE,
        scale=Vector2(2, 2),
    )

    while True:
        if engine.tick():
            if engine_io.A.is_just_pressed:
                break
            if engine_io.B.is_just_pressed:
                break
    crash.mark_destroy()
    pointst.mark_destroy()
    points.mark_destroy()

def modeID():
    global speed
    global game_mode
    
    m = game_mode
    if m == MODE_LINK:
        m = MODE_FULL
    
    return str(m)+"-"+str(speed)

def displayHighscore():
    score.show(modeID())
   
def displayOptions():
    global game_mode
    global first_player
    global speed
    
    title = helper.Text("Options",font16,Vector2(1.5, 1.5),WHITE)
    help = helper.Text("U/D Select\nL/R Change\nA Ok B Help",font6,Vector2(1, 1),YELLOW)
    info = helper.Text(VERSION,font6,Vector2(1, 1), YELLOW)
    listformat = options.OptionsFormat(font16, Vector2(1, 1),WHITE, GREEN, 84)

    gamemodes = [options.OptionsValue("Full",MODE_FULL),
                 options.OptionsValue("Pure",MODE_PURE),
                 options.OptionsValue("Link",MODE_LINK),
                ]
    
    gamespeeds = []
    for sp in range(1,11):
        gamespeeds.append(options.OptionsValue(str(sp),sp))

    data={}
    node =  options.OptionsNode(title, help, info, listformat, BLACK, data)
    helptext=("Dont crash in any Wall. Use left and right shoulder buttons to stear.\n\n"
              "Full\n"
              "Collect flashing dots for bonus points.\n\n"
              "Pure\n"
              "Just you and the line.\n\n"
              "Link\n"
              "Multiplayer using a link cable. Use B for temporary speed boost. Line color shows if ready to boost."
             )
    
    helptext = helper.word_wrap(helptext, font16, Vector2(1,1), SCREEN_WIDTH)
    node.addoption("Mode:", helptext,"mode", gamemodes, game_mode)

    helptext=("Speed of the game, 10 is fastest.\n"
              "There is a highscore for each speed.\n"
              "Boost in link mode is speed + 3 so use a maximum of 7 for link mode."
             )
    
    helptext = helper.word_wrap(helptext, font16, Vector2(1,1), SCREEN_WIDTH)

    node.addoption("Speed:",helptext ,"speed", gamespeeds, speed)
    
    node.show()
    
    game_mode = data["mode"]
    speed = data["speed"]

    print("mode="+str(game_mode))
    print("speed="+str(speed))

    node.mark_destroy()

def connected():
    # Clear anything that might not be related to the game
    engine_link.clear_send()
    engine_link.clear_read()

def waitForPlayer():
    global game_mode
    global first_player
    global speed
    
    cancel = False

    #log("Link")
    #log("Mode: " + str(game_mode))
    #log("Player: " + str(first_player + 1))
    #log("Speed (before): " + str(speed))

    connecting = Text2DNode(
        position=Vector2(0, -30),
        text="Connecting",
        font=font16,
        color=WHITE,
        scale=Vector2(1, 1),
    )

    countdown = Text2DNode(
        position=Vector2(0, 10),
        text="",
        font=font16,
        color=WHITE,
        scale=Vector2(3, 3),
    )
    
    
    wait_help = Text2DNode(
        text="M Cancel",
        font=font6,
        color=WHITE,
        scale=Vector2(1, 1),
    )
    align(wait_help, 0, 0, 1, 2, True, True)    

    engine_link.set_connected_cb(connected)
    engine_link.start()

    engine.fps_limit(10)
    # wait for connection
    while True:
        if engine.tick():
            if engine_io.MENU.is_just_pressed:
                log("Cancel Connect")
                cancel = True
                engine_link.stop()
                break
            if engine_link.connected():
                break
    if not cancel:
        if engine_link.is_host():
            #log("is host")
            first_player = True
        else:
            #log("is client")
            first_player = False

        # send game settings
        buffer = bytearray(9)
        buffer[0] = KIND_SETTINGS
        buffer[1] = (speed >> 0) & 0b11111111
        #log("Buffer (send): " + str(buffer))

        engine_link.send(buffer)

        # wait for settings
        while engine_link.available() < 9:
            pass
        engine_link.read_into(buffer, 9)
        #log("Buffer (rcv): " + str(buffer))
      
        # use slower speed
        kind = buffer[0]
        remotespeed = buffer[1]
        if kind == 1:
            if remotespeed < speed:
                speed = remotespeed

        #wait for next tick to display countdown  
        sleep_time = engine.time_to_next_tick() / 1000
        time.sleep(sleep_time)
        for count in range(5):
            countdown.text = str(5 - count)
            engine.tick()  # to update the text

            buffer[0] = KIND_COUNTDOWN
            buffer[1] = count # currently not used 
            engine_link.send(buffer)
            time.sleep(1)
            # wait for the message from the other thumby
            while engine_link.available() < 9:
                pass
            engine_link.read_into(buffer, 9)

    connecting.mark_destroy()
    countdown.mark_destroy()
    wait_help.mark_destroy()
    
    if cancel:
        return PAGE_TITLE
    else:
        return PAGE_GAME

def explosion(x, y, arena):
    global virtual_screen

    # reduce fps for animation
    engine.fps_limit(30)

    step = 0

    bits = []
    for count in range(EXPLOSION_BITS):
        # x,y x speed, y speed
        bit = [
            x,
            y,
            (random.randint(0, 20) - 10) / 10,
            (random.randint(0, 20) - 10) / 10,
        ]
        bits.append(bit)

    engine_io.rumble(EXPLOSION_RUMBLE)

    while step < EXPLOSION_STEPS:

        step += 1

        # remove from current position
        for bit in bits:
            virtual_screen.pixel(int(bit[0]), int(bit[1]), BACKGROUND)

        # move bits to new position
        for bit in bits:
            bit[0] = bit[0] + bit[2]
            if bit[0] < 0:
                bit[0] = 0
            if bit[0] >= VIRTUAL_WIDTH:
                bit[0] = VIRTUAL_WIDTH - 1

            bit[1] = bit[1] + bit[3]
            if bit[1] < 0:
                bit[1] = 0
            if bit[1] >= VIRTUAL_HEIGHT:
                bit[1] = VIRTUAL_HEIGHT - 1

        # draw at new position
        for bit in bits:
            virtual_screen.pixel(int(bit[0]), int(bit[1]), EXPLOSION)

        updateScreen(arena)
        refreshScreen()
    engine_io.rumble(0)

log("Start")
page = 1
while page != PAGE_QUIT:
    if page == PAGE_TITLE:
        page = displayTitle()
    if page == PAGE_GAME:
        points = playGame()
        displayPoints(points)
        if (game_mode == MODE_FULL) or (game_mode == MODE_PURE):
            score.check(modeID(), points)
        page = PAGE_TITLE
    if page == PAGE_OPTIONS:
        displayOptions()
        page = PAGE_TITLE
    if page == PAGE_WAITFORPLAYER:
        page = waitForPlayer()
    if page == PAGE_HIGHSCORE:
        displayHighscore()
        page = PAGE_TITLE        
    if page == PAGE_ENTERHIGHSCORE:
        enterHighscore(points)
        page = PAGE_HIGHSCORE

engine.tick()
log("Exit")
