# TEST
import random
from math import pi

import engine_main
import engine
import engine_io
import engine_draw
import engine_save
import sys

from engine_draw import Color
from engine_animation import Delay
from engine_math import Vector2
from engine_resources import TextureResource
from engine_nodes import CameraNode,Sprite2DNode
#from engine_nodes import CameraNode  Rectangle2DNode, Text2DNode, Vector3

from engine_animation import Tween, ONE_SHOT, EASE_SINE_IN
import random

camera = CameraNode()
engine.fps_limit(20)

class UnderBand:
    def __init__(self):
        sprite_resource = TextureResource("./bmp/UnderBand.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(0, 44),
            rotation=0, layer=5)

class BG_SPR:
    def __init__(self,posX):
        self.x=posX
        sprite_resource = TextureResource("./bmp/BG.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(self.x, -20),
            rotation=0, layer=1)
    def move(self):
      xpos = self.sprite.position.x
      self.sprite.position.x = xpos + 1-(xpos>128)*256

class AYANE:
    def __init__(self,posX,posY):
        self.eyeCNT=10
        self.ripCNT=10
        self.ptn=1
        self.ptn2=1
        self.rip_table=(1,1,0,0,1,1,2,0,0,2,1,1,0,0,2,0,1,1,2,2,0,0,2,2,1,0,1,1,0,0,1,1,2,0,1,1,0,0,1,1,0,0,2,2,1,1,2,2,0,0,2,2,1,1)
        sprite_resource = TextureResource("./bmp/AYANE01.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(posX, posY),
            rotation=0, layer=4)        
    def move(self,posX,posY):
        self.sprite.position.x = posX
        self.sprite.position.y = posY
        self.ptn=self.ptn-(self.ptn>0)
        eye.Show(posX,posY,int(self.ptn/2))
        self.eyeCNT=self.eyeCNT-1
        if (self.eyeCNT==0):
            self.ptn=6
            self.eyeCNT=10+random.randint(1, 80)
        ######
        self.ptn2=self.ptn2-(self.ptn2>0)
        rip.Show(posX,posY,self.rip_table[int(self.ptn2/2)])
    def Talk(self,ptn):
        self.ptn2=ptn
        
        
class EYE():
    def __init__(self,posX,posY,frame_y):
        sprite_resource  = TextureResource("./bmp/eye01.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(posX-7, posY-18),
            frame_count_y = 3,
            playing = False,
            rotation=0, layer=4)    
    def Show(self,posX,posY,ptn):
        self.sprite.frame_current_y = ptn
        self.sprite.position.x = posX-7
        self.sprite.position.y = posY-18
class RIP():
    def __init__(self,posX,posY,frame_y):
        sprite_resource  = TextureResource("./bmp/rip01.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(posX-7, posY-1),
            frame_count_y = 3,
            playing = False,
            rotation=0, layer=4)    
    def Show(self,posX,posY,ptn):
        self.ptn=ptn
        self.sprite.frame_current_y = self.ptn
        self.sprite.position.x = posX-7
        self.sprite.position.y = posY-1



class AYANE_BINGO:
    def __init__(self):
        self.x=168
        sprite_resource = TextureResource("./bmp/AYANE_BINGO.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(self.x, 0),
            rotation=0, layer=8)
    def Show(self,CNT):
        stopcnt=16
        posX=(CNT-stopcnt)*8
        if(CNT<stopcnt):
            posX=0
        #if(CNT==1):
        #    posX=168
        self.x=posX            
        self.sprite.position.x = self.x
    def Hide(self):
        self.x=168
        self.sprite.position.x = self.x
class HandB:
    def __init__(self,OnOff):    
        sprite_resource = TextureResource("./bmp/TXT_HITand.bmp")
        posY=200
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(-33, posY),
            rotation=0, layer=6)    
    def Show(self,OnOff):
        posY=-21
        if(OnOff==0):
            posY=200        
        self.sprite.position.y = posY
class TRIES:
    def __init__(self):    
        sprite_resource = TextureResource("./bmp/TXT_TRIES.bmp")
        posY=200
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(46, posY),
            rotation=0, layer=8)    
    def Show(self,OnOff):
        posY=35
        if(OnOff==0):
            posY=200        
        self.sprite.position.y = posY
class TXT_Nothing:
    def __init__(self):    
        sprite_resource = TextureResource("./bmp/TXT_Nothing.bmp")
        posY=200
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(-32, 200),
            rotation=0, layer=6)    
    def Show(self,OnOff):
        posY=-20
        if(OnOff==0):
            posY=200        
        self.sprite.position.y = posY
class BINGO:
    def __init__(self):    
        sprite_resource = TextureResource("./bmp/BINGO.bmp")
        posY=300
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(-32, posY),
            rotation=0, layer=8)    
    def Show(self,posY):     
        self.sprite.position.y = posY
    def Hide(self):
        self.sprite.position.y = 300        
        
        
class Balloon:
    def __init__(self,TYP):
        self.type=TYP
        self.startPosX=(0,40,45,40,47)
        self.startPosY=(0,48,48,52,52)
        self.fixPosX=(0,16,45,16,47)
        self.fixPosY=(0,36,36,52,52)
        if(self.type==1):
            sprite_resource = TextureResource("./bmp/balloon1.bmp")         
        if(self.type==2):
            sprite_resource = TextureResource("./bmp/balloon2.bmp")                   
        if(self.type==3):
            sprite_resource = TextureResource("./bmp/balloon3.bmp")                      
        if(self.type==4):
            sprite_resource = TextureResource("./bmp/balloon4.bmp")           
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(0, 300),
            rotation=0, layer=6)
        self.CNT=0
    def Show(self,CNT):
        TYP=self.type
        tmp=int((self.startPosX[TYP]-self.fixPosX[TYP])*CNT/6)
        posX=self.fixPosX[TYP]+tmp
        tmp=int((self.startPosY[TYP]-self.fixPosY[TYP])*CNT/6)
        posY=self.fixPosY[TYP]+tmp
        self.sprite.position.x = posX-64
        self.sprite.position.y = posY-64
    def Hide(self):
        self.sprite.position.y = 200

class NumBig:
    def __init__(self): 
        sprite_resource  = TextureResource("./bmp/NumberBIG.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(0, 300),
            frame_count_x = 10,
            playing = False,
            rotation=0, layer=6)
        self.Number=[0,1,2,3]
        self.CNT=0
        self.X=-47
    def ShowMyNum(self,MyNum,Dig,Num1,Num2,Num3,CUR):
        #MyNum：表示しようとする数字
        #Dig：表示しようとする数字の桁
        #Num1～Num3：他の数字（順不同）
        #CUR：カーソルの値
        flg=0
        if(MyNum==Num1)or(MyNum==Num2)or(MyNum==Num3):
            flg=1#同じ数字がある
        posX=self.X+Dig*19+(self.CNT%10<5)*flg*200#同じ数字がある場合、点滅表示する。
        self.sprite.frame_current_x = MyNum
        self.sprite.position.x = posX
        self.sprite.position.y = 45-(Dig==CUR)*7#カーソルと桁数が同じ場合、上にあげる。
        self.CNT=self.CNT+1
        if (self.CNT>1000):
            self.CNT=0
        return flg
    def HideMyNum(self):
        self.sprite.position.y = 300
        
class NumSmall:
    def __init__(self): 
        sprite_resource  = TextureResource("./bmp/NumberSmall.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            transparent_color=Color(0xF81F), 
            position=Vector2(0, 300),
            frame_count_x = 10,
            playing = False,
            rotation=0, layer=8)
    def ShowNum(self,MyNum,Dig,PosX,PosY,lay):
        #MyNum：表示しようとする数字
        #Dig：表示しようとする数字の桁
        self.sprite.frame_current_x = MyNum
        self.sprite.position.x = PosX+Dig*11
        self.sprite.position.y = PosY
        self.sprite.layer = lay
    def HideNum(self):
        self.sprite.position.y = 300

class HitCountBig:
    def __init__(self): 
        sprite_resource  = TextureResource("./bmp/CH_HIT.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(0, 300),
            frame_count_y= 5,
            playing = False,
            rotation=0, layer=6)
    def Show(self,CNT):
        #CNT：表示しようとするHIT数
        posX=42
        self.sprite.frame_current_y = CNT
        self.sprite.position.x = -35
        self.sprite.position.y = -27+(CNT==4)*6+(CNT==0)*300
        #print(f"CNT={CNT}")
    def Hide(self):
        self.sprite.position.y = 300

class BlowCountBig:
    def __init__(self): 
        sprite_resource  = TextureResource("./bmp/CH_BLOW.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(0, 300),
            frame_count_y= 5,
            playing = False,
            rotation=0, layer=6)
    def Show(self,CNT):
        #CNT：表示しようとするBlows数
        posX=42
        self.sprite.frame_current_y = CNT
        self.sprite.position.x = -35
        self.sprite.position.y = -15-(CNT==4)*6+(CNT==0)*300
        #print(f"CNT={CNT}")
    def Hide(self):
        self.sprite.position.y = 300

class HitCountSmall:
    def __init__(self): 
        sprite_resource  = TextureResource("./bmp/H_Count.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(-15, 300),
            frame_count_y= 5,
            playing = False,
            rotation=0, layer=3)
    def Show(self,CNT,Line,ofs):
        #CNT：表示しようとするBlows数
        self.sprite.frame_current_y = CNT
        self.sprite.position.y = 43-Line*26+ofs
        #print(f"CNT={CNT}")
    def Hide(self):
        self.sprite.position.y = 300
        
class BlowCountSmall:
    def __init__(self): 
        sprite_resource = TextureResource("./bmp/B_Count.bmp")
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(0,300),
            frame_count_y= 5,
            playing = False,
            rotation=0, layer=3)
    def Show(self,CNT,Line,ofs):
        #CNT：表示しようとするBlows数
        self.sprite.frame_current_y = CNT
        self.sprite.position.y = 43-Line*26+ofs
        #print(f"CNT={CNT}")
    def Hide(self):
        self.sprite.position.y = 300
        
class Blank:
    def __init__(self):    
        sprite_resource = TextureResource("./bmp/BLANK.bmp")
        posY=200
        self.sprite = Sprite2DNode(
            texture=sprite_resource,
            position=Vector2(-23,300),
            rotation=0, layer=3)    
    def Show(self,OnOff):
        posY=-20
        if(OnOff==0):
            posY=300       
        self.sprite.position.y = posY

def BalloonShow(tmp):
    balloon_1.Show(tmp)
    balloon_2.Show(tmp)
    balloon_3.Show(tmp)
    balloon_4.Show(tmp)
def BalloonHide():
    balloon_1.Hide()
    balloon_2.Hide()
    balloon_3.Hide()
    balloon_4.Hide()
def BigNumHide():
    NumBig0.HideMyNum()
    NumBig1.HideMyNum()
    NumBig2.HideMyNum()
    NumBig3.HideMyNum()

def CheckBingo(MyNum,Answer):
    Hit=0
    Blow=0
    for Num in range(4):
        for Tmp in range(4):
            if (MyNum[Tmp]==Answer[Num]): #Number Booking
                if(Num==Tmp):
                    Hit=Hit+1
                else:
                    Blow=Blow+1
        tmp=Hit*10+Blow
    return tmp

def ShowREC(TryRec,Line):
    ofset=int(Line%10*2.6)
    START=Line//10
    LenRec=len(TryRec)
    #print(f"len={LenRec}")
    for i in range(5):
        CNT=START+i
        if (CNT<=LenRec):
            tmp=TryRec[CNT-1]
            B=tmp%10
            tmp=tmp//10
            H=tmp%10
            BlowCountS[i-1].Show(B,i,ofset)
            HitCountS[i-1].Show(H,i,ofset)
            
            PosY=31-i*26+ofset
            PosX=-50
            for j in range(4):
                tmp=tmp//10
                MyNum=tmp%10
                #print(f"num={MyNum}")
                NumS[i*4+j].ShowNum(MyNum,4-j,PosX,PosY,3)
        else:
            BlowCountS[i-1].Hide()
            HitCountS[i-1].Hide()
            for j in range(4):
                NumS[i*4+j].HideNum()
            
def HideRec():
    for i in range(5):
        BlowCountS[i-1].Hide()
        HitCountS[i-1].Hide()
    for i in range(25):
        NumS[i].HideNum()
        

def MakeAnswer():
    numbers=[0,1,2,3,4,5,6,7,8,9]
    for i in range(10):
        tmp=numbers[i]
        R=random.randint(0,9)
        tmp2=numbers[R]
        numbers[R]=tmp
        numbers[i]=tmp2
    R=random.randint(0,5)
    for i in range(4):
        Answer[i]=numbers[R+i]
    return Answer


flg=1

BG1=BG_SPR(0)
BG2=BG_SPR(-128)
ayane=AYANE(30,-12)
eye=EYE(30,0,2)
rip=RIP(30,0,2)
UB=UnderBand()
balloon_1=Balloon(1)
balloon_2=Balloon(2)
balloon_3=Balloon(3)
balloon_4=Balloon(4)
ayaneBINGO=AYANE_BINGO()
TXT_HandB=HandB(0)
TXT_TRIES=TRIES()
Bingo=BINGO()
balloonCNT=-1
NumBig0=NumBig()
NumBig1=NumBig()
NumBig2=NumBig()
NumBig3=NumBig()
NumSmall0=NumSmall()
NumSmall1=NumSmall()

HitCountB=HitCountBig()
BlowCountB=BlowCountBig()
TXT_Not=TXT_Nothing()
BLANK=Blank()

HitCountS=[1,2,3,4,5]
BlowCountS=[1,2,3,4,5]
NumS=[1,2,3,4,5,6,7,8,9,10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25]
for i in range(5):
    HitCountS[i]=HitCountSmall()
    BlowCountS[i]=BlowCountSmall()
for i in range(25):
    NumS[i]=NumSmall()

MyNum=[0,1,2,3]
Answer=[6,5,0,2]
w_table=(-1,-2,-4,-5,-5,-6,-6,-6,-6,-6,-5,-5,-4,-2,-1)
####################################################################
CNT=0
BingoCNT=-1
ptn=2
MODE=0
AX0=22
AX=35
TryRec=[]
RecLine=0
while 1:
    BtnFlg=0
    if engine.tick():
        BG1.move()
        BG2.move()
        AY=-12+w_table[CNT]
        if(AX>AX0):
            AX=AX-1
        if(AX<AX0):
            AX=AX+1
        ayane.move(AX,AY)
        
        
        if (MODE==0):###########################################　ゲーム以前
            AX0=22

            if engine_io.A.is_just_pressed:#----[ A ]ボタン（モード０）
                if(balloonCNT<0):
                    ayane.Talk(35)
                    balloonCNT=6
                else:
                    balloonCNT=-1            
                    BalloonHide()
                    TXT_HandB.Show(0)
                    BtnFlg=1
                    MyNum=[0,1,2,3]
                    Answer=MakeAnswer()
                    CUR=0
                    HB=0
                    TRIES=0
                    MODE=1   ##ゲームスタート
                    
            if(balloonCNT >=0):
                tmp=int(balloonCNT)
                BalloonShow(tmp)
                balloonCNT=balloonCNT-(balloonCNT>0)
                if(balloonCNT==0):
                        TXT_HandB.Show(1)#バルーンが広がってから「HIT and BLOW？」表示
                        
            if engine_io.B.is_just_pressed:#----[ B ]ボタン（モード０）
                if(balloonCNT >=0):
                    ayane.Talk(20)
                else:
                    tmp=20+random.randint(1, 40)
                    ayane.Talk(tmp)
                balloonCNT=-1            
                BalloonHide()
                TXT_HandB.Show(0)
                
            if (engine_io.UP.is_just_pressed)and(engine_io.B.is_pressed):#----[ 上+B ]ボタン（モード０）：裏技 綾音アップ表示
                BingoCNT=32
                
        if (MODE==1):###########################################　マイナンバー入力
            AX0=30
            TXT_TRIES.Show(1)
            tmp=TRIES//10
            NumSmall0.ShowNum(tmp,0,42,50,8)
            tmp=TRIES%10
            NumSmall1.ShowNum(tmp,1,42,50,8)
            
            if(balloonCNT<0):
                if engine_io.LEFT.is_just_pressed:#----[ 左 ]ボタン（モード１）
                    CUR=CUR-1
                    if(CUR<0):
                        CUR=3
                if engine_io.RIGHT.is_just_pressed:#----[ 右 ]ボタン（モード１）
                    CUR=CUR+1
                    if(CUR>3):
                        CUR=0
                if engine_io.UP.is_just_pressed:#----[ 上　]ボタン（モード１）
                    tmp=MyNum[CUR]+1
                    if(tmp>9):
                        tmp=0
                    MyNum[CUR]=tmp
                if engine_io.DOWN.is_just_pressed:#----[ 下 ]ボタン（モード１）
                    tmp=MyNum[CUR]-1
                    if(tmp<0):
                        tmp=9
                    MyNum[CUR]=tmp                    
            flg=0    
            flg=flg+NumBig0.ShowMyNum(MyNum[0],0,MyNum[1],MyNum[2],MyNum[3],CUR)        
            flg=flg+NumBig1.ShowMyNum(MyNum[1],1,MyNum[0],MyNum[2],MyNum[3],CUR)     
            flg=flg+NumBig2.ShowMyNum(MyNum[2],2,MyNum[0],MyNum[1],MyNum[3],CUR)     
            flg=flg+NumBig3.ShowMyNum(MyNum[3],3,MyNum[0],MyNum[1],MyNum[2],CUR)

            if(BtnFlg==0)and(flg==0)and(engine_io.A.is_just_pressed):#----[ A ]ボタン（モード１）
                if(balloonCNT<0):
                    HB=CheckBingo(MyNum,Answer)
                    #print(f"tmp={HB}")
                    balloonCNT=6
                    tmp=HB+MyNum[3]*100+MyNum[2]*1000+MyNum[1]*10000+MyNum[0]*100000
                    TryRec.insert(0,tmp)
                    #print(f"Rec={TryRec}")
                    TRIES=TRIES+(TRIES<99)
                    
                    ayane.Talk(25)
                else:
                    balloonCNT=-1
                    HitCountB.Hide()
                    BlowCountB.Hide()
                    TXT_Not.Show(0)
                    BalloonHide()
                    if(HB==40):
                        BingoCNT=32
                        
            
            if(balloonCNT >=0):
                tmp=int(balloonCNT)
                BalloonShow(tmp)
                balloonCNT=balloonCNT-(balloonCNT>0)
                if(balloonCNT==0):
                    if(HB==0):
                        TXT_Not.Show(1)
                    else:
                        HitCountB.Show(HB//10)#バルーンが出来ってから「ビンゴチェック」表示
                        BlowCountB.Show(HB%10)#
                    
            
            if (BingoCNT<0)and(engine_io.B.is_just_pressed):#----[ B ]ボタン（モード１）
                balloonCNT=-1
                HitCountB.Hide()
                BlowCountB.Hide()
                TXT_Not.Show(0)
                BalloonHide() 
                BtnFlg=1
                BLANK.Show(1)
                RecLine=0
                MODE=2
        
        if(MODE==2):########################################################　履歴表示
            AX0=45
            TXT_TRIES.Show(1)
            tmp=TRIES//10
            NumSmall0.ShowNum(tmp,0,42,50,8)
            tmp=TRIES%10
            NumSmall1.ShowNum(tmp,1,42,50,8)

            if (engine_io.UP.is_pressed):#----[ 上 ]ボタン（モード2）
                RecLine=RecLine+(RecLine<((len(TryRec)-1)*10))*2
                
            if (engine_io.DOWN.is_pressed):#----[ 下 ]ボタン（モード2）
                RecLine=RecLine-2
                if (RecLine<0):
                        RecLine=0
                        
            if(len(TryRec)>0):
                ShowREC(TryRec,RecLine)

            if (BtnFlg==0)and (engine_io.B.is_just_pressed):#----[ B ]ボタン（モード2）
                BLANK.Show(0)
                if(len(TryRec)>0):
                    HideRec()
                MODE=1

        
        if(BingoCNT>0):
            ayaneBINGO.Show(int(BingoCNT))
            BingoCNT=BingoCNT-(BingoCNT>1)
            if (BingoCNT<20):
                Bingo.Show(-44+w_table[CNT])
            if (BingoCNT==1)and(engine_io.A.is_just_pressed)and(BtnFlg==0):
                BingoCNT=-1
                MODE=0
                TryRec=[]
                ayaneBINGO.Hide()
                BigNumHide()
                TXT_TRIES.Show(0)
                NumSmall0.HideNum()
                NumSmall1.HideNum()
                Bingo.Hide()

        CNT=CNT+1
        if (CNT>len(w_table)-1):
            CNT=0
sys.exit()
