import engine_main
import engine
import engine_io
from engine_nodes import CameraNode, Line2DNode, Circle2DNode, Text2DNode, Rectangle2DNode
import engine_time
from math import pi, sin, cos
from engine_math import Vector2
from time import sleep_ms

engine.fps_limit(30)
camera = CameraNode()
outline = Circle2DNode(radius=60, color=31727, outline=True, layer=5)
hrHd = Line2DNode(start=Vector2(0,0), thickness=3, color=65535, layer=4)
minHd = Line2DNode(start=Vector2(0,0), thickness=1, color=48631, layer=3)
secHd = Line2DNode(start=Vector2(0,0), thickness=1, color=14823, layer=2)
RmLb = ["XII","I","II","III","IV","V","VI","VII","VIII","IX","X","XI"]
ArLb = ["12","1","2","3","4","5","6","7","8","9","10","11"]
MonLb = ["nul","Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
dspMd = 0
lbMd = int(1)
pipAr = []
numAr = []
mnBk = Rectangle2DNode(position=Vector2(256,0),width=128,height=128,layer=6,color=7)
mnFd = 7
mnTt = Text2DNode(text="Set Clock",position=Vector2(0,-50),scale=Vector2(2,2),layer=7)
mnHn = Text2DNode(text="L/R: change position\nU/D: change value\nA  : save\nB  : toggle numerals\nRB : close menu",
                       position=Vector2(0,45),color=31727,layer=7)
mnPt = Text2DNode(text=">   <",rotation=(pi/2),color=65504,layer=8)
ptPos = 3
if(engine_time.is_compromised()): tgtTime = [2026,1,1,12,34,56]
else: tgtTime = list(engine_time.datetime())
hrSt = Text2DNode(text=f"{tgtTime[3]:2}",position=Vector2(-29,-20),scale=Vector2(2,2),layer=7)
minSt = Text2DNode(text=f":{tgtTime[4]:02}",position=Vector2(-2,-20),scale=Vector2(2,2),layer=7)
secSt = Text2DNode(text=f":{tgtTime[5]:02}",position=Vector2(27,-20),scale=Vector2(2,2),layer=7)
yrSt = Text2DNode(text=f"{tgtTime[0]:4}",position=Vector2(-36,10),scale=Vector2(2,2),layer=7)
monSt = Text2DNode(text=f"/{MonLb[tgtTime[1]]}",position=Vector2(4,10),scale=Vector2(2,2),layer=7)
daySt = Text2DNode(text=f"/{tgtTime[2]:2}",position=Vector2(39,10),scale=Vector2(2,2),layer=7)
mnBk.add_child(mnTt)
mnBk.add_child(mnHn)
mnBk.add_child(hrSt)
mnBk.add_child(minSt)
mnBk.add_child(secSt)
mnBk.add_child(yrSt)
mnBk.add_child(monSt)
mnBk.add_child(daySt)
hrSt.add_child(mnPt)
if(engine_time.is_compromised()):
    warnLabel=Text2DNode(text="RTC not set\nRB to set clock\nMenu to exit",color=63488,scale=Vector2(1.5,1.5))
    while(not(engine_io.MENU.is_pressed)):
        if(engine_io.RB.is_just_pressed):
            if(dspMd == 0): dspMd = 1
            else: dspMd = 0
        if(dspMd == 1):
            if(mnBk.position.x > 0): mnBk.position.x -= 16
            else:
                hrSt.text = f"{tgtTime[3]:2}"
                minSt.text = f":{tgtTime[4]:02}"
                secSt.text = f":{tgtTime[5]:02}"
                yrSt.text = f"{tgtTime[0]:4}"
                monSt.text = f"/{MonLb[tgtTime[1]]}"
                daySt.text = f"/{tgtTime[2]:2}"
                if(ptPos == 0): yrSt.remove_child(mnPt)
                elif(ptPos == 1): monSt.remove_child(mnPt)
                elif(ptPos == 2): daySt.remove_child(mnPt)
                elif(ptPos == 3): hrSt.remove_child(mnPt)
                elif(ptPos == 4): minSt.remove_child(mnPt)
                elif(ptPos == 5): secSt.remove_child(mnPt)
                if(engine_io.RIGHT.is_just_pressed):
                    ptPos += 1
                    if(ptPos > 5): ptPos = 0
                if(engine_io.LEFT.is_just_pressed):
                    ptPos -= 1
                    if(ptPos < 0): ptPos = 5
                if(ptPos == 0): yrSt.add_child(mnPt)
                elif(ptPos == 1): monSt.add_child(mnPt)
                elif(ptPos == 2): daySt.add_child(mnPt)
                elif(ptPos == 3): hrSt.add_child(mnPt)
                elif(ptPos == 4): minSt.add_child(mnPt)
                elif(ptPos == 5): secSt.add_child(mnPt)
                if(engine_io.UP.is_just_pressed or engine_io.UP.is_long_pressed):
                    tgtTime[ptPos] += 1
                    if(tgtTime[1] > 12): tgtTime[1] = 1
                    if(tgtTime[2] > 31): tgtTime[2] = 1
                    if(tgtTime[3] > 23): tgtTime[3] = 0
                    if(tgtTime[4] > 59): tgtTime[4] = 0
                    if(tgtTime[5] > 59): tgtTime[5] = 0
                if(engine_io.DOWN.is_just_pressed or engine_io.DOWN.is_long_pressed):
                    tgtTime[ptPos] -= 1
                    if(tgtTime[1] < 1): tgtTime[1] = 12
                    if(tgtTime[2] < 1): tgtTime[2] = 31
                    if(tgtTime[3] < 0): tgtTime[3] = 23
                    if(tgtTime[4] < 0): tgtTime[4] = 59
                    if(tgtTime[5] < 0): tgtTime[5] = 59
                if(engine_io.A.is_just_pressed):
                    engine_time.datetime(tuple(tgtTime))
                    tgtTime = list(engine_time.datetime())
                    mnFd = 967
        else:
            if(mnBk.position.x < 256): mnBk.position.x += 16
        if(mnFd > 7):
            mnFd -= 64
            mnBk.color = mnFd
        if(engine_io.B.is_just_pressed):
            lbMd += 1
            if(lbMd > 2): lbMd = 0
        while(not(engine.tick())): sleep_ms(1)
    warnLabel.mark_destroy()
engine_io.release_all_buttons()
if(not(engine_time.is_compromised())):
    for i in range(12):
        pipAr.append(Line2DNode(color=31727,layer=5))
        pipAr[i].start = Vector2(60 * sin(i * pi / 6), -60 * cos(i * pi / 6))
        pipAr[i].end = Vector2(56 * sin(i * pi / 6), -56 * cos(i * pi / 6))
        numAr.append(Text2DNode(color=31727,layer=5))
        if(lbMd == 1): numAr[i].text = RmLb[i]
        elif(lbMd == 2): numAr[i].text = ArLb[i]
        else: numAr[i].text = ""
        pipAr[i].add_child(numAr[i])
        numAr[i].position = Vector2(-8 * sin(i * pi / 6), 8 * cos(i * pi / 6))
    while(not(engine_io.MENU.is_pressed)):
        if(engine_io.RB.is_just_pressed):
            if(dspMd == 0):
                dspMd = 1
                tgtTime = list(engine_time.datetime())
            else: dspMd = 0
        if(dspMd == 1):
            if(mnBk.position.x > 0): mnBk.position.x -= 16
            else:
                hrSt.text = f"{tgtTime[3]:2}"
                minSt.text = f":{tgtTime[4]:02}"
                secSt.text = f":{tgtTime[5]:02}"
                yrSt.text = f"{tgtTime[0]:4}"
                monSt.text = f"/{MonLb[tgtTime[1]]}"
                daySt.text = f"/{tgtTime[2]:2}"
                if(ptPos == 0): yrSt.remove_child(mnPt)
                elif(ptPos == 1): monSt.remove_child(mnPt)
                elif(ptPos == 2): daySt.remove_child(mnPt)
                elif(ptPos == 3): hrSt.remove_child(mnPt)
                elif(ptPos == 4): minSt.remove_child(mnPt)
                elif(ptPos == 5): secSt.remove_child(mnPt)
                if(engine_io.RIGHT.is_just_pressed):
                    ptPos += 1
                    if(ptPos > 5): ptPos = 0
                if(engine_io.LEFT.is_just_pressed):
                    ptPos -= 1
                    if(ptPos < 0): ptPos = 5
                if(ptPos == 0): yrSt.add_child(mnPt)
                elif(ptPos == 1): monSt.add_child(mnPt)
                elif(ptPos == 2): daySt.add_child(mnPt)
                elif(ptPos == 3): hrSt.add_child(mnPt)
                elif(ptPos == 4): minSt.add_child(mnPt)
                elif(ptPos == 5): secSt.add_child(mnPt)
                if(engine_io.UP.is_just_pressed or engine_io.UP.is_long_pressed):
                    tgtTime[ptPos] += 1
                    if(tgtTime[1] > 12): tgtTime[1] = 1
                    if(tgtTime[2] > 31): tgtTime[2] = 1
                    if(tgtTime[3] > 23): tgtTime[3] = 0
                    if(tgtTime[4] > 59): tgtTime[4] = 0
                    if(tgtTime[5] > 59): tgtTime[5] = 0
                if(engine_io.DOWN.is_just_pressed or engine_io.DOWN.is_long_pressed):
                    tgtTime[ptPos] -= 1
                    if(tgtTime[1] < 1): tgtTime[1] = 12
                    if(tgtTime[2] < 1): tgtTime[2] = 31
                    if(tgtTime[3] < 0): tgtTime[3] = 23
                    if(tgtTime[4] < 0): tgtTime[4] = 59
                    if(tgtTime[5] < 0): tgtTime[5] = 59
                if(engine_io.A.is_just_pressed):
                    engine_time.datetime(tuple(tgtTime))
                    tgtTime = list(engine_time.datetime())
                    mnFd = 967
        else:
            if(mnBk.position.x < 256): mnBk.position.x += 16
            curTime = list(engine_time.datetime())
            dspSec = curTime[5]
            dspMin = curTime[4] + (dspSec / 60)
            dspHr = curTime[3] + (dspMin / 60)
            if(dspHr >= 12): dspHr -= 12
            secHd.end = Vector2(36 * sin(dspSec * pi / 30), -36 * cos(dspSec * pi / 30))
            minHd.end = Vector2(50 * sin(dspMin * pi / 30), -50 * cos(dspMin * pi / 30))
            hrHd.end = Vector2(25 * sin(dspHr * pi / 6), -25 * cos(dspHr * pi / 6))
        if(mnFd > 7):
            mnFd -= 64
            mnBk.color = mnFd
        if(engine_io.B.is_just_pressed):
            lbMd += 1
            if(lbMd > 2): lbMd = 0
            for i in range(12):
                if(lbMd == 1): numAr[i].text = RmLb[i]
                elif(lbMd == 2): numAr[i].text = ArLb[i]
                else: numAr[i].text = ""
        while(not(engine.tick())): sleep_ms(1)
engine_io.release_all_buttons()