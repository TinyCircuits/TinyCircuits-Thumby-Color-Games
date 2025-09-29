import engine_main
import engine
import engine_io
from engine_nodes import CameraNode, Text2DNode, Rectangle2DNode
from engine_math import Vector2
from time import sleep_ms

engine.fps_limit(30)
camera = CameraNode()
btyOutline = Rectangle2DNode(width=40, height=100, layer=1)
btyOutline.position.x = -30
btyBlack = Rectangle2DNode(color=0, width=30, height=90, layer=2)
btyBlack.position.x = -30
btyFilled = Rectangle2DNode(color=2016, width=30, layer=3)
btyFilled.position.x = -30
btyVolts = Text2DNode(layer=3, scale=Vector2(2,2), position=Vector2(30,-15))
btyCharging = Text2DNode(text="=D---", color=0, layer=3, scale=Vector2(2,2), position=Vector2(28,12))
titleText = Text2DNode(text="Battery\n Check", layer=3, scale=Vector2(2,2), position=Vector2(26,-50), letter_spacing=0.3)
helpText = Text2DNode(text="LB  : brite+\nRB  : brite-\nMenu: exit", color=31727, layer=3, position=Vector2(30,40))

while (not(engine_io.MENU.is_pressed)):
    btyPercent = engine_io.battery_level()
    btyFilled.height = 90 * btyPercent
    btyFilled.position.y = 45 - (45 * btyPercent)
    btyVolts.text = f"{engine_io.battery_voltage():.2f} V"
    if (engine_io.is_charging()):
        btyCharging.color = 65472
    else:
        btyCharging.color = 0
    scrBright = engine.setting_brightness()
    if (engine_io.LB.is_just_pressed):
        scrBright -= 0.1
        if scrBright < 0.0: scrBright = 0.0
    if (engine_io.RB.is_just_pressed):
        scrBright += 0.1
        if scrBright > 1.0: scrBright = 1.0
    engine.setting_brightness(scrBright, False)
    while (not(engine.tick())):
        sleep_ms(1)
engine_io.release_all_buttons()