# TEST
import engine_main
import engine
import engine_io
import engine_draw
#import engine_save
import sys
from engine_draw import Color
#from engine_animation import Delay
from engine_math import Vector2
from engine_math import Vector3
from engine_resources import TextureResource
from engine_nodes import CameraNode,Sprite2DNode
#from engine_animation import Tween, ONE_SHOT, EASE_SINE_IN
import random
import math

camera = CameraNode()


def make_Puzzle():

    # Randomly arrange the numbers 0 through 14 (with 15 fixed as a blank at the end)
    tiles = list(range(16))
    #random.shuffle(tiles)
    for i in range(16):
        tmp=tiles[i]
        R=random.randint(0,15)
        tiles[R],tiles[i]=tiles[i],tiles[R]
    
    boad = tiles
    return boad    

def Frame_B_Show():
    for i in range(16):
        ofset=-64+16
        tmpX=i%4*32+ofset
        tmpY=i//4*32+ofset
        frame_B[i].Show(tmpX,tmpY)

def Frame_B_Hide():
    for i in range(16):
        frame_B[i].Hide()
        
class STAR():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            frame_count_y = 4,
            playing = False,
            rotation=0, layer=8 )
        sprite_resource = TextureResource("./bmp/STAR.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = random.randint(0,144)-68
        self.Spd=random.randint(4,20)
        self.Y=-64-self.Spd*random.randint(0,3)
        self.sprite.frame_current_y=random.randint(0,3)
    def born(self):
        self.sprite.position.x = random.randint(0,128)-64
        self.sprite.position.y = random.randint(0,128)-256
        self.Spd=random.randint(4,30)
        self.Y=-64-self.Spd*random.randint(0,64)        
    def Show(self):
        CNT=self.sprite.frame_current_y
        CNT=CNT+1
        if (CNT>3):
            CNT=0
        self.sprite.frame_current_y = CNT
        if(self.Y<90):
            self.Y=self.Y+self.Spd*.5
        self.sprite.position.y = int(self.Y)
    def Hide(self):
        self.sprite.position.y = 200


class CHECKER():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            frame_count_x = 4,
            playing = True,
            rotation=0, layer=8 )
        sprite_resource = TextureResource("./bmp/Check.bmp")
        self.sprite.texture=sprite_resource
 
    def Born(self,posX,posY):
        ofset=-64+16
        self.sprite.position.x = posX+ofset
        self.sprite.position.y = posY+ofset
        self.sprite.frame_current_x=0    
 
    def Show(self):
        CNT=self.sprite.frame_current_x
        if (CNT==3):
            self.sprite.position=Vector2(0, 300)


class FRAME():
    def __init__(self,ptn):
        tmp=8
        if (ptn==0):
            tmp=7
        if (ptn==2):
            tmp=6
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            frame_count_x = 3,
            playing = False,
            rotation=0, layer=tmp )
        sprite_resource = TextureResource("./bmp/Frame.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.frame_current_x = ptn   
    def Show(self,PosX,PosY):
        self.sprite.position.x = PosX
        self.sprite.position.y = PosY        
    def Hide(self):
        self.sprite.position.y = 300

 
class TXT_CLEAR():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            playing = False,
            rotation=0, layer=10 )
        sprite_resource = TextureResource("./bmp/TXT_CLEAR.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = 0
        self.sprite.position.y = 300
        self.CNT=0
 
    def Show(self):
        self.CNT+=1
        if self.CNT>1000:
            self.CNT=0
        if (self.CNT%10<5):
            self.sprite.position.y = 30
        else:
            self.sprite.position.y = 300            
    def Hide(self):
        self.sprite.position.y = 300
class TXT_START():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            playing = False,
            rotation=0, layer=10 )
        sprite_resource = TextureResource("./bmp/TXT_START.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = 0
        self.sprite.position.y = 300
        self.CNT=0
 
    def Show(self):
        self.CNT+=1
        if self.CNT>1000:
            self.CNT=0
        if (self.CNT%8<4):
            self.sprite.position.y = 0
        else:
            self.sprite.position.y = 300            
    def Hide(self):
        self.sprite.position.y = 300
        
        
class ARROW_L():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            playing = False,
            rotation=0, layer=10 )
        sprite_resource = TextureResource("./bmp/ARROW_L.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = -55
        self.sprite.position.y = 300
        self.CNT=0  
    def Show(self):
        self.CNT+=1
        if self.CNT>1000:
            self.CNT=0
        if (self.CNT%10<5):
            self.sprite.position.y = 20
        else:
            self.sprite.position.y = 300            
    def Hide(self):
        self.sprite.position.y = 300
class ARROW_R():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300),
            transparent_color=Color(0xF81F), 
            playing = False,
            rotation=0, layer=10 )
        sprite_resource = TextureResource("./bmp/ARROW_R.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = 55
        self.sprite.position.y = 300
        self.CNT=0  
    def Show(self):
        self.CNT+=1
        if self.CNT>1000:
           self.CNT=0
        if (self.CNT%10<5):
            self.sprite.position.y = 20
        else:
            self.sprite.position.y = 300            
    def Hide(self):
        self.sprite.position.y = 300
        
class Exit_Menu():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(0, 300), 
            playing = False,
            rotation=0, layer=10 )
        sprite_resource = TextureResource("./bmp/ExitMenu.bmp")
        self.sprite.texture=sprite_resource
        self.sprite.position.x = 0
        self.sprite.position.y = 300 
    def Show(self):
        self.Y=self.sprite.position.y
        if self.Y>0:
           self.Y=int(self.Y/2)
        self.sprite.position.y = self.Y
          
    def Hide(self):
        self.sprite.position.y = 300  

################################################################
class PicView:
    def __init__(self,pic):
        sprite_resource = TextureResource("./bmp/"+PicList[pic]+".bmp")
        
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            frame_count_y = PicLen[pic],
            position=Vector2(0, 0),
            scale=Vector2(8.0,8.0),
            playing = True,
            rotation=0, layer=1)
    def Show(self):
        self.sprite.position.y = 0
        self.sprite.frame_current_y=0
        self.sprite.playing=True
    def Hide(self):
        self.sprite.playing=False
        self.sprite.position.y = 300
###############################################################
class piece():
    def __init__(self,pic):
        self.sprite = Sprite2DNode(
            position=Vector2(300, 300),
            frame_count_x = 4,
            playing = False,
            scale=Vector2(8.0,8.0),
            rotation=0, layer=4 )
    def picSelect(self,pic):
        #sprite_resource = TextureResource("./bmp/"+PicList[pic]+".bmp",True)
        sprite_resource =PIC[pic].sprite.texture
        self.sprite.texture=sprite_resource 
        self.sprite.frame_count_y = 4*PicLen[pic]        
    def Show(self,posX,posY,ptn,frm,Lay):
        ofset=-64+16
        self.sprite.frame_current_x = (ptn)%4   
        self.sprite.frame_current_y = ((ptn)//4)+frm*4
        self.sprite.position=Vector2(posX+ofset, posY+ofset)
        self.sprite.layer=Lay
        #print(f"PosX={posX}")
        #print(f"PosY={posY}")
    def Hide(self):
        self.sprite.position=Vector2(300, 300)
        
################################################################ 
# anim_00=60, anim_01=60, anim_02=51, anim_03=59, anim_04=44, anim_06=58
# anim_07=31, anim_08=34, anim_09=58, anim_10_60
PicList=("anim_00","anim_02","anim_03","anim_04","anim_06","anim_07","anim_08","anim_01","anim_09","anim_10")
PicLen=(60,51,59,44,58,31,34,60,58,60)

PIC=[0]*len(PicList)
for i in range(len(PicList)):
    PIC[i]=PicView(i)
    PIC[i].Hide()
PIC[0].Show()

pic=0
boad=[0]*16
PIECE=[0]*16
for i in range(16):
    PIECE[i]=piece(0)
    PIECE[i].picSelect(0)    


Mode=1
BTN_FLG=0
X=0
Y=0
MovePiece=0
Dir=""
starNum=24
star=[0]*starNum
for i in range(starNum):
    star[i]=STAR()
for i in range(starNum):
    star[i].born()
    
txt_clear=TXT_CLEAR()
txt_start=TXT_START()
arrow_L=ARROW_L()
arrow_R=ARROW_R()
ExitMenu=Exit_Menu()

checker=CHECKER()

frame_S=FRAME(0)#RED:Source panel
frame_C=FRAME(1)#Blue:Change panel
frame_B=[0]*16
for i in range(16):
    frame_B[i]=FRAME(2)#Black:Moving panel


SX=[0]*16
SY=[0]*16
EX=[0]*16
EY=[0]*16


CNT2=0
CNT=24
E_CNT=24
ofset=-64+16

addX=0
addY=0
frm=0
frmCNT=0
while 1:
    BTN_FLG-=(BTN_FLG>0)
    
    if engine.tick():
        
        if(Mode==1):#Pic select #################################################
            engine.fps_limit(8)
            select=-1
            arrow_L.Show()
            arrow_R.Show()
            if engine_io.RIGHT.is_just_pressed:
                PIC[pic].Hide()
                pic=pic+1
                if pic>(len(PicList)-1):
                    pic=0
                PIC[pic].Show()
                #print(f"pic={pic}")
                
            if engine_io.LEFT.is_just_pressed:
                PIC[pic].Hide()
                pic=pic-1
                if (pic<0):
                    pic=len(PicList)-1
                PIC[pic].Show()
                #print(f"pic={pic}")
              
            if (BTN_FLG==0)and(engine_io.A.is_just_pressed):
                PIC[pic].Hide()
                boad=make_Puzzle()
                for i in range(16):
                    PIECE[i].Hide()
                    PIECE[i].picSelect(pic) 
                    SX[i]=i%4*32
                    SY[i]=i//4*32
                    tmp=boad[i]
                    #tmp=i
                    EX[tmp]=SX[i]
                    EY[tmp]=SY[i]
                E_CNT=18
                CNT=18
                arrow_L.Hide()
                arrow_R.Hide()
                engine.fps_limit(16)
                CNT=24
                E_CNT=24
                Mode=6

        if(Mode==6): #START Effect #################################################

            txt_start.Show()
            if(CNT>0):
                for i in range(16):
                    MX=EX[i]+int((SX[i]-EX[i])*CNT/E_CNT)
                    MY=EY[i]+int((SY[i]-EY[i])*CNT/E_CNT)
                    PIECE[i].Show(MX,MY,i,frm,3)                       
                CNT-=1
            else:
                for i in range(16):
                    if (boad[i]==15):
                        X=i%4
                        Y=i//4
                        print(f"Boad={boad}")
                    #else:
                        
                txt_start.Hide()
                
                select=0 #Source not selected = 0:Source selected = 1
                SLX=0
                SLY=0
                CX=0
                CY=0
                C_flg=0
                Mode=2
            
        if(Mode==2):#Puzzle Play #################################################
            
            for i in range(16):
                PIECE[i].Show(EX[i],EY[i],i,frm,3)    
            
            Frame_B_Show()
            checker.Show()
            
            if (BTN_FLG==0)and(engine_io.B.is_just_pressed):# Cancel
                if(select==0):
                    ExitMenu.Show()
                    BTN_FLG=3
                    frame_S.Hide()                   
                    Mode=4
                else:
                    frame_C.Hide()  
                    select=0                    

            if (BTN_FLG==0)and(engine_io.A.is_just_pressed):# SELECT
                if(select==0):
                    select=1#-------------------------------------------1st panel select
                    CX=SLX
                    CY=SLY
                    
                    checker.Born(SLX*32,SLY*32)
                    
                else:
                    select=3
                    frame_S.Hide()
                    frame_C.Hide()  
                    CNT=5
                    E_CNT=5
                    Mode=3#------------------------------------------ 2nd select and goto Panel Move!

            if (engine_io.LEFT.is_just_pressed):
                if (select==0):
                    SLX=SLX-(SLX>0) 
                else:
                    CX=CX-(CX>0)
            if (engine_io.RIGHT.is_just_pressed):
                if (select==0):
                    SLX=SLX+(SLX<3)  
                else:
                    CX=CX+(CX<3)                   
            if (engine_io.DOWN.is_just_pressed):
                if (select==0):
                    SLY=SLY+(SLY<3)  
                else:
                    CY=CY+(CY<3)  
            if (engine_io.UP.is_just_pressed):
                if (select==0):
                    SLY=SLY-(SLY>0) 
                else:
                    CY=CY-(CY>0)
                    
            if(select==0):
                if(CNT2%8<4):
                    tmpX=SLX*32+ofset
                    tmpY=SLY*32+ofset
                    frame_S.Show(tmpX,tmpY)                    
                else:
                    frame_S.Hide()
                    
            if(select==1):
                tmpX=SLX*32+ofset
                tmpY=SLY*32+ofset
                frame_S.Show(tmpX,tmpY)   
                if(CNT2%8<4):
                    tmpX=CX*32+ofset
                    tmpY=CY*32+ofset
                    frame_C.Show(tmpX,tmpY)                    
                else:
                    frame_C.Hide()                    
            
        if(Mode==3):# Move Piece #################################################

            BD1=SLY*4+SLX
            BD2=CY*4+CX
            MP1=boad[BD1]
            MP2=boad[BD2]

            if(BD1==BD2):# Red and Blue is same panel.
                select=1
                Mode=2
            else:
                if (CNT>0):
                    addX=int((CX-SLX)*32/E_CNT*CNT)
                    addY=int((CY-SLY)*32/E_CNT*CNT)
                    
                    tmpX=CX*32-addX
                    tmpY=CY*32-addY
                    PIECE[MP1].Show(tmpX,tmpY,MP1,frm,5)
                    frame_S.Show(tmpX+ofset,tmpY+ofset)
                    tmpX=SLX*32+addX
                    tmpY=SLY*32+addY
                    PIECE[MP2].Show(tmpX,tmpY,MP2,frm,4)
                    frame_C.Show(tmpX+ofset,tmpY+ofset)
                    CNT=CNT-1
                else:
                    frame_C.Hide()
                    tmpX=CX*32
                    tmpY=CY*32
                    EX[MP1]=tmpX
                    EY[MP1]=tmpY
                    tmpX=SLX*32
                    tmpY=SLY*32
                    EX[MP2]=tmpX
                    EY[MP2]=tmpY                    
                    print(f"MP1={MP1}")
                    print(f"MP2={MP2}")
                    boad[BD1],boad[BD2]=boad[BD2],boad[BD1]
                    print(f"boad={boad}")
                    SLX=CX
                    SLY=CY
                    if (boad== list(range(16))):
                        for i in range(16):
                            PIECE[i].Hide()
                        frame_S.Hide()
                        PIC[pic].Show()                  
                        Mode=5#----------------------------------- goto clear !!
                    else:
                        select=0
                        Mode=2

        if(Mode==4):# Exit Menu #################################################
            ExitMenu.Show()
            if (BTN_FLG==0)and(engine_io.B.is_just_pressed):
                print(f"B Pressed")
                ExitMenu.Hide()
                BTN_FLG=3
                Mode=2

            if (BTN_FLG==0)and(engine_io.A.is_just_pressed):
                ExitMenu.Hide()
                for i in range(16):
                    PIECE[i].Hide()
                PIC[pic].Show()
                BTN_FLG=5
                Mode=1

        if (Mode==5): #Clear
            Frame_B_Hide()
            engine.fps_limit(8)
            for i in range(starNum):
                star[i].Show()
            txt_clear.Show()
            if engine_io.B.is_just_pressed:
                for i in range(starNum):
                    star[i].born()  
                for i in range(16):
                    PIECE[i].Hide()
                PIC[pic].Show()
                txt_clear.Hide()
                Mode=1
        frmCNT=frmCNT+0.5
        frm=int(frmCNT)
        if (frm>=PicLen[pic]):
            frm=0
            frmCNT=0
        CNT2=CNT2+1
        if (CNT2>10000):
            CNT2=0
            
