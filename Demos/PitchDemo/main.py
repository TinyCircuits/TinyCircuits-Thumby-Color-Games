import engine_main
import engine
import engine_audio
from engine_resources import ToneSoundResource
from engine_nodes import Text2DNode, CameraNode
import engine_io
from time import sleep_ms

cam = CameraNode()
engine.fps_limit(60)
toneLetters = ["C ", "C#", "D ", "D#", "E ", "F ", "F#", "G ", "G#", "A ", "A#", "B "]
foreFreq = 440 # A4 default
foreTone = ToneSoundResource()
foreTone.frequency = foreFreq
forePlaying = False
foreLetter = 9
foreOctave = 4
backFreq = 659.26 # E5 default
backTone = ToneSoundResource()
backTone.frequency = backFreq
backPlaying = False
backLetter = 4
backOctave = 5
foreLabel = Text2DNode()
foreLabel.position.y = -40
foreLabel.scale.x = 2
foreLabel.scale.y = 2
foreLabel.color = 31727
backLabel = Text2DNode()
backLabel.position.y = 0
backLabel.scale.x = 2
backLabel.scale.y = 2
backLabel.color = 31727
helpText = Text2DNode()
helpText.position.y = 40
helpText.color = 14823
helpText.text = "L / R: A freq +/-\nLB/RB: B freq +/-\nA / B: A/B on/off\nMenu : exit"

while(not(engine_io.MENU.is_pressed)):
    if(engine_io.LEFT.is_just_pressed and (foreFreq > 112)):
        foreFreq = foreFreq / 1.059463
        foreLetter -= 1
        foreTone.frequency = foreFreq
        if(foreLetter == -1):
            foreLetter = 11
            foreOctave -= 1
    if(engine_io.RIGHT.is_just_pressed and (foreFreq < 7000)):
        foreFreq = foreFreq * 1.059463
        foreLetter += 1
        foreTone.frequency = foreFreq
        if(foreLetter == 12):
            foreLetter = 0
            foreOctave += 1
    if(abs(foreFreq - 440) < 10): foreFreq = 440 # recalibrate due to math errors
    if(engine_io.LB.is_just_pressed and (backFreq > 112)):
        backFreq = backFreq / 1.059463
        backLetter -= 1
        backTone.frequency = backFreq
        if(backLetter == -1):
            backLetter = 11
            backOctave -= 1
    if(engine_io.RB.is_just_pressed and (backFreq < 7000)):
        backFreq = backFreq * 1.059463
        backLetter += 1
        backTone.frequency = backFreq
        if(backLetter == 12):
            backLetter = 0
            backOctave += 1
    if(abs(backFreq - 659.26) < 10): backFreq = 659.26 # recalibrate due to math errors
    if(engine_io.A.is_just_pressed):
        forePlaying = not(forePlaying)
        if(forePlaying):
            audioChan = engine_audio.play(foreTone,0,True)
            audioChan.gain = 0.5
            foreLabel.color = 65535
        else:
            engine_audio.stop(0)
            foreLabel.color = 31727
    if(engine_io.B.is_just_pressed):
        backPlaying = not(backPlaying)
        if(backPlaying):
            audioChan = engine_audio.play(backTone,1,True)
            audioChan.gain = 0.5
            backLabel.color = 65535
        else:
            engine_audio.stop(1)
            backLabel.color = 31727
    foreLabel.text = f"{foreFreq:.2f}Hz:{toneLetters[foreLetter]}{foreOctave}"
    backLabel.text = f"{backFreq:.2f}Hz:{toneLetters[backLetter]}{backOctave}"
    while(not(engine.tick())):
        sleep_ms(1)
engine_audio.stop(0)
engine_audio.stop(1)
engine_io.release_all_buttons()