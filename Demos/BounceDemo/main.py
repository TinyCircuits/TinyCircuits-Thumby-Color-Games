import engine_main
import engine
from engine_nodes import CameraNode, PhysicsCircle2DNode, Text2DNode, EmptyNode
from engine_resources import ToneSoundResource
import engine_audio
import engine_physics
from time import sleep_ms
import engine_io
import random

class BouncyCircle(PhysicsCircle2DNode):
    def __init__(self):
        super().__init__(self)
        self.radius = int(5 * random.random() + 2)
        self.outline = True
        self.outline_color = int((random.getrandbits(4) << 11) + (random.getrandbits(5) << 5) + (random.getrandbits(4)) + 0b0100001000001000)
        self.velocity.x = random.random()
        self.velocity.y = random.random()
        self.friction = 0
        self.position.x = 120 * random.random() - 60
        self.position.y = 120 * random.random() - 60
        self.dynamic = True
        self.collision_mask = 1
        self.enable_collision_layer(1)
    def tick(self,dt):
        global soundMode
        global soundHandler
        myFreq = self.outline_color.value / 16 - 512
        if((self.position.x > (64 - self.radius)) and (self.velocity.x > 0)):
            self.velocity.x = -self.velocity.x
            if(soundMode > 1): soundHandler.playSound(myFreq)
        if((self.position.x < (self.radius - 64)) and (self.velocity.x < 0)):
            self.velocity.x = -self.velocity.x
            if(soundMode > 1): soundHandler.playSound(myFreq)
        self.position.x += self.velocity.x
        if((self.position.y > (64 - self.radius)) and (self.velocity.y > 0)):
            self.velocity.y = -self.velocity.y
            if(soundMode > 1): soundHandler.playSound(myFreq)
        if((self.position.y < (self.radius - 64)) and (self.velocity.y < 0)):
            self.velocity.y = -self.velocity.y
            if(soundMode > 1): soundHandler.playSound(myFreq)
        self.position.y += self.velocity.y
    def on_collide(self,contact):
        global soundHandler
        global soundMode
        if(soundMode > 0):
            soundHandler.playSound(self.outline_color.value / 16 - 512)

class SoundHandler(EmptyNode):
    def __init__(self):
        super().__init__(self)
        self.toneRes = []
        self.toneDur = []
        self.toneChan = []
        engine_audio.set_volume(0)
        for i in range(0,3):
            self.toneRes.append(ToneSoundResource())
            self.toneDur.append(0)
            self.toneChan.append(engine_audio.play(self.toneRes[i],i,False))
            self.toneChan[i].stop()
        engine_audio.set_volume(1)
    def playSound(self,freq):
        try:
            emptyChan = self.toneDur.index(0)
        except ValueError:
            pass
        else:
            self.toneDur[emptyChan] = 3
            self.toneRes[emptyChan].frequency = freq
            self.toneChan[emptyChan].play(self.toneRes[emptyChan], True)
            self.toneChan[emptyChan].gain = 0.25
    def endSound(self):
        for i in range(0,3):
            self.toneChan[i].stop()
    def tick(self,dt):
        for i in range(0,3):
            if(self.toneDur[i] > 0):
                self.toneDur[i] -= 1
            else:
                self.toneChan[i].stop()
        
gravX = 0
gravY = 0
soundHandler = SoundHandler()
engine_physics.set_gravity(gravX,gravY)
circleList = []
camera = CameraNode()
engine.fps_limit(60)
bubbleLabel = Text2DNode(color=31727)
bubbleLabel.position.y = 55
gravLabel = Text2DNode(color=31727)
gravLabel.position.x = 48
gravLabel.position.y = -55
soundLabel = Text2DNode(color=31727)
soundLabel.position.x = -54
soundLabel.position.y = -59
soundLabel.text = "<)))"
soundMode = 2
idleCount = 0

while(not(engine_io.MENU.is_just_pressed)):
    if(engine_io.A.is_just_pressed):
        if(len(circleList) < 16): circleList.append(BouncyCircle())
    if(engine_io.B.is_just_pressed):
        if(len(circleList) > 0):
            circleList[0].mark_destroy()
            circleList.pop(0)
    if(engine_io.UP.is_just_pressed): gravY += 0.1
    if(engine_io.DOWN.is_just_pressed): gravY -= 0.1
    if(engine_io.LEFT.is_just_pressed): gravX += 0.1
    if(engine_io.RIGHT.is_just_pressed): gravX -= 0.1
    if(engine_io.RB.is_pressed):
        gravX = 0
        gravY = 0
    engine_physics.set_gravity(gravX,gravY)
    gravLabel.text = f"X:{gravX: .1f}\nY:{gravY: .1f}"
    bubbleLabel.text = f"Bubbles:{len(circleList):2}\nIdle: {idleCount:2}ms"
    if(engine_io.LB.is_just_pressed):
        if(soundMode == 0):
            soundMode = 1
            soundLabel.text = "<)  "
        elif(soundMode == 1):
            soundMode = 2
            soundLabel.text = "<)))"
        else:
            soundMode = 0
            soundLabel.text = "< X "
            soundHandler.endSound()
    idleCount = 0
    while(not(engine.tick())):
        idleCount += 1
        sleep_ms(1)
soundHandler.endSound()
engine_io.release_all_buttons()