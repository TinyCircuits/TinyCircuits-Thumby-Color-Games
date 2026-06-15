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
from engine_resources import TextureResource
from engine_nodes import CameraNode,Sprite2DNode
#from engine_animation import Tween, ONE_SHOT, EASE_SINE_IN
import random

camera = CameraNode()
engine.fps_limit(20)

def count_inversions(seq):
    """Count the number of inversions in the array, excluding the blank (15)"""
    inv = 0
    n = len(seq)
    for i in range(n):
        for j in range(i + 1, n):
            if seq[i] > seq[j]:
                inv += 1
    return inv

def make_Puzzle():
    """
    Generate and return a solvable 15-puzzle board.
    `board` is an array of integers from 0 to 15, where 15 represents a blank space.
    The blank space must be placed at the last index (the 15th position).
    """
    while True:
        # Randomly arrange the numbers 0 through 14 (with 15 fixed as a blank at the end)
        tiles = list(range(15))
        #random.shuffle(tiles)
        for i in range(15):
            tmp=tiles[i]
            R=random.randint(0,14)
            tiles[R],tiles[i]=tiles[i],tiles[R]
            
        # Since the blank is in the bottom-right corner of the 4x4 grid (the first row from the bottom = an odd row), the puzzle can be solved when the number of inversions is even.
        inv = count_inversions(tiles)
        if inv % 2 == 0:
            boad = tiles + [15]  #  Finally, add a blank line (15)
            return boad
        

class PicView:
    def __init__(self,pic):
        sprite_resource = TextureResource("./bmp/"+PicList[pic]+".bmp")  
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(0, 0),
            rotation=0, layer=1)
    def Show(self):
        self.sprite.position.y = 0
    def Hide(self):
        self.sprite.position.y = 300



class piece():
    def __init__(self):
        self.sprite = Sprite2DNode(
            position=Vector2(300, 300),
            frame_count_x = 4,
            frame_count_y = 4,
            playing = False,
            rotation=0, layer=4 )
    def picSelect(self,pic):
        #sprite_resource = TextureResource("./bmp/"+PicList[pic]+".bmp",True)
        sprite_resource =PIC[pic].sprite.texture
        self.sprite.texture=sprite_resource      
    def Show(self,posX,posY,ptn):
        ofset=-64+16
        self.sprite.frame_current_x = (ptn)%4       
        self.sprite.frame_current_y = (ptn)//4
        self.sprite.position.x = posX+ofset
        self.sprite.position.y = posY+ofset
    def Hide(self):
        self.sprite.position.y = 300    

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
            self.sprite.position.y = 40
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
        if (self.CNT%10<5):
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
        
PicList=("Pic01","Pic02","Pic03","Pic04","Pic05","Pic06","Pic07","Pic08")
PIC=[0]*len(PicList)
for i in range(len(PicList)):
    PIC[i]=PicView(i)
    PIC[i].Hide()
PIC[0].Show()

pic=0
boad=[0]*16
PIECE=[0]*16
for i in range(16):
    PIECE[i]=piece()
    PIECE[i].picSelect(1)    

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

SX=[0]*16
SY=[0]*16
EX=[0]*16
EY=[0]*16

CNT=0
E_CNT=24

while 1:
    BTN_FLG-=(BTN_FLG>0)
    
    if engine.tick():
        
        if(Mode==1):#Pic select #################################################
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
                    EX[tmp]=SX[i]
                    EY[tmp]=SY[i]
                EY[15]=200
                EX[15]=200
                E_CNT=24
                CNT=24
                arrow_L.Hide()
                arrow_R.Hide()
                Mode=6

        if(Mode==6): #START Effect #################################################
            
            txt_start.Show()
            if(CNT>0):
                for i in range(16):
                    MX=EX[i]+int((SX[i]-EX[i])*CNT/E_CNT)
                    MY=EY[i]+int((SY[i]-EY[i])*CNT/E_CNT)
                    PIECE[i].Show(MX,MY,i)                       
                CNT-=1
            else:
                for i in range(16):
                    if (boad[i]==15):
                        X=i%4
                        Y=i//4
                        print(f"Boad={boad}")
                    else:
                        PIECE[i].Show(i%4*32,i//4*32,boad[i])
                txt_start.Hide()
                Mode=2
            
        if(Mode==2):#Puzzle Play #################################################
            
            if (BTN_FLG==0)and(engine_io.B.is_just_pressed):
                ExitMenu.Show()
                BTN_FLG=3
                Mode=4

            if (engine_io.LEFT.is_just_pressed)and(X<3):
                 MovePiece=Y*4+X+1
                 Dir="R"
                 CNT=4
                 Mode=3
            if (engine_io.RIGHT.is_just_pressed)and(X>0):
                 MovePiece=Y*4+X-1
                 Dir="L"
                 CNT=4
                 Mode=3                 
            if (engine_io.DOWN.is_just_pressed)and(Y>0):
                 MovePiece=Y*4+X-4
                 Dir="U"
                 CNT=4
                 Mode=3
            if (engine_io.UP.is_just_pressed)and(Y<3):
                 MovePiece=Y*4+X+4
                 Dir="D"
                 CNT=4
                 Mode=3
            
            
        if(Mode==3):# Move Piece #################################################
            CNT=CNT-1
            add=CNT*4
            ofX=(Dir=="R")*add-(Dir=="L")*add
            ofY=(Dir=="D")*add-(Dir=="U")*add
            PIECE[MovePiece].Show(X*32+ofX,Y*32+ofY,boad[MovePiece])
                      
            if (CNT==0):
                #print(f"MOVE={MovePiece}")
                tmp1=Y*4+X # Null Piece
                if (Dir=="R"):
                    tmp2=Y*4+X+1 #Move Piece
                    X=X+1
                if (Dir=="L"):
                    tmp2=Y*4+X-1 #Move Piece
                    X=X-1                    
                if (Dir=="U"):
                    tmp2=Y*4+X-4 #Move Piece
                    Y=Y-1                        
                if (Dir=="D"):
                    tmp2=Y*4+X+4 #Move Piece
                    Y=Y+1                        
                boad[tmp1],boad[tmp2]=boad[tmp2],boad[tmp1]
                #print(f"Boad={boad}")
                for i in range(16):
                    for i in range(16):
                        PIECE[i].Hide()
                        if (boad[i]<15):
                            PIECE[i].Show(i%4*32,i//4*32,boad[i])                   
                    
                if (boad== list(range(16))):
                    for i in range(16):
                        PIECE[i].Hide()
                    PIC[pic].Show()                  
                    Mode=5
           
                else:
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

