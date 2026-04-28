"""IMA ADPCM audio implementation for Thumby Color - Simplified"""

import time
import struct
import _thread
import array
import gc
from machine import Timer, PWM, Pin

# Configuration
BUFFER_SIZE = 800
PWM_FREQ = 120000
VALID_RATES = [15625, 12500, 10000, 8000, 6250, 5000, 4000]
DEFAULT_VOLUME = 100

class AudioState:
    def __init__(self):
        self.buf1 = bytearray(BUFFER_SIZE)
        self.buf2 = bytearray(BUFFER_SIZE)
        self.data_file = None
        
        # Create timers once
        self.frame_timer = Timer()
        self.callback_timer = Timer()
        
        # ALL playback state in bufstate for Viper access
        # [0: current_buffer, 1: pos_in_buffer, 2: buffer_size, 
        #  3: current_sample, 4: total_samples, 5: buf1_needs_filling, 6: buf2_needs_filling,
        #  7: volume, 8: loop_start, 9: loop_end, 10: loop_enabled, 11: loop_resync_needed,
        #  12: saved_prediction, 13: saved_index, 14: loop_state_saved, 
        #  15: thread_active, 16: stop_requested, 17: playback_done, 18: callback_triggered]
        self.bufstate = array.array("I", [0, 0, BUFFER_SIZE, 0, 0, 1, 1, DEFAULT_VOLUME, 
                                          0, 0, 0, 0, 32768, 0, 0, 0, 0, 0, 0])
        
        # File management
        self.file_start_pos = 0
        self.sample_delay = 125
        self.sample_rate = 8000
        self.file_handles = []
        
        # Callback system  
        self.end_callback = None
        self.callback_args = None
        
        # IMA ADPCM tables
        self.ima_index_table = array.array("i", [
            -1, -1, -1, -1, 2, 4, 6, 8,
            -1, -1, -1, -1, 2, 4, 6, 8
        ])
        
        self.ima_step_table = array.array("h", [
            7, 8, 9, 10, 11, 12, 13, 14, 16, 17, 
            19, 21, 23, 25, 28, 31, 34, 37, 41, 45, 
            50, 55, 60, 66, 73, 80, 88, 97, 107, 118, 
            130, 143, 157, 173, 190, 209, 230, 253, 279, 307,
            337, 371, 408, 449, 494, 544, 598, 658, 724, 796,
            876, 963, 1060, 1166, 1282, 1411, 1552, 1707, 1878, 2066, 
            2272, 2499, 2749, 3024, 3327, 3660, 4026, 4428, 4871, 5358,
            5894, 6484, 7132, 7845, 8630, 9493, 10442, 11487, 12635, 13899, 
            15289, 16818, 18500, 20350, 22385, 24623, 27086, 29794, 32767
        ])

audio = AudioState()

@micropython.viper
def audio_loop():
    """Main audio playback loop"""
    state:ptr32 = ptr32(audio.bufstate)
    b1:ptr8 = ptr8(audio.buf1)
    b2:ptr8 = ptr8(audio.buf2)
    delay:int = int(audio.sample_delay)
    
    indextable:ptr32 = ptr32(audio.ima_index_table)
    steptable:ptr16 = ptr16(audio.ima_step_table)
    
    # IMA ADPCM state
    prediction:int = 32768
    index:int = 0
    step:int = steptable[index]
    delta:int = 0
    diff:int = 0
    
    # Timing
    next_time:int = int(time.ticks_us())
    
    # PWM setup
    pwm = PWM(Pin(23), freq=PWM_FREQ)
    setwidth = pwm.duty_u16
    
    # Track first pass for loop state saving
    first_pass:int = 1
    
    # Main playback loop
    while state[3] < state[4] and state[16] == 0:  # current < total and not stop_requested
        # Wait if both buffers need filling
        while state[5] and state[6]:
            if state[16]:  # Check stop during wait
                break
                
            volume:int = int(state[7])
            output:int = prediction
            if volume != 100:
                sample_signed:int = prediction - 32768
                sample_signed = (sample_signed * volume) // 100
                if sample_signed > 32767: 
                    sample_signed = 32767
                elif sample_signed < -32768: 
                    sample_signed = -32768
                output = sample_signed + 32768
            
            setwidth(output)
            
            current_time:int = int(time.ticks_us())
            while int(time.ticks_diff(next_time, current_time)) > 0:
                current_time = int(time.ticks_us())
            next_time = int(time.ticks_add(next_time, delay))
        
        if state[16]:  # Stop requested
            break
            
        # Save loop state at loop start point
        if state[10] and first_pass and state[3] == state[8] and state[8] > 0:
            state[12] = prediction
            state[13] = index
            state[14] = 1
            first_pass = 0
        
        # Get nibble
        if state[0]:
            delta = b2[state[1]]
        else:
            delta = b1[state[1]]
        
        # Process nibble (even = high, odd = low)
        if state[3] & 1:  # Odd - low nibble
            delta &= 0x0F
            state[1] += 1
            
            if state[1] >= state[2]:
                state[5 + state[0]] = 1
                state[0] ^= 1
                state[1] = 0
        else:  # Even - high nibble
            delta >>= 4
        
        state[3] += 1
        
        # Check loop point
        if state[10]:
            loop_end:int = state[9] if state[9] > 0 else state[4]
            if state[3] >= loop_end:
                state[3] = state[8]
                if state[14]:
                    prediction = state[12]
                    index = state[13]
                    step = steptable[index]
                state[5] = 1
                state[6] = 1
                state[0] = 0
                state[1] = 0
                state[11] = 1
                continue
        
        # IMA ADPCM decode
        diff = step >> 3
        if delta & 0b100: diff += step
        if delta & 0b10: diff += (step >> 1)
        if delta & 0b1: diff += (step >> 2)
        
        if delta & 0b1000:
            prediction -= diff
            if prediction < 0: prediction = 0
        else:
            prediction += diff
            if prediction > 65535: prediction = 65535
        
        index += indextable[delta]
        if index < 0: index = 0
        elif index > 88: index = 88
        step = steptable[index]
        
        # Apply volume
        volume:int = int(state[7])
        output:int = prediction
        if volume != 100:
            sample_signed:int = prediction - 32768
            sample_signed = (sample_signed * volume) // 100
            if sample_signed > 32767: 
                sample_signed = 32767
            elif sample_signed < -32768: 
                sample_signed = -32768
            output = sample_signed + 32768
        
        # Precise timing
        current_time:int = int(time.ticks_us())
        while int(time.ticks_diff(next_time, current_time)) > 0:
            current_time = int(time.ticks_us())
        
        setwidth(output)
        next_time = int(time.ticks_add(next_time, delay))
    
    # Cleanup
    setwidth(0)
    pwm.deinit()
    
    # Signal thread done - ORDER MATTERS
    state[17] = 1  # playback_done first
    state[15] = 0  # thread_active last (after thread is truly done)

def fill_buffers(timer=None):
    """Fill audio buffers"""
    if not audio.data_file:
        return
    
    # Check if playback naturally ended
    if audio.bufstate[17] and not audio.bufstate[10]:  # playback_done and not looping
        if audio.bufstate[18] == 0:  # callback not yet triggered
            audio.bufstate[18] = 1  # Mark as triggered
            audio.frame_timer.deinit()
            audio.bufstate[17] = 0
            
            # Store callback for deferred execution
            callback_func = audio.end_callback
            callback_args = audio.callback_args
            
            if callback_func:
                def deferred_callback(t):
                    try:
                        if callback_args:
                            callback_func(*callback_args)
                        else:
                            callback_func()
                    except:
                        pass
                
                audio.callback_timer.init(mode=Timer.ONE_SHOT, period=10, callback=deferred_callback)
        return
    
    # Handle loop resync
    if audio.bufstate[11]:
        byte_offset = audio.bufstate[8] // 2
        audio.data_file.seek(audio.file_start_pos + byte_offset)
        audio.bufstate[11] = 0
    
    # Fill buffers
    if audio.bufstate[5]:
        bytes_read = audio.data_file.readinto(audio.buf1)
        if bytes_read:
            audio.bufstate[5] = 0
            
    if audio.bufstate[6]:
        bytes_read = audio.data_file.readinto(audio.buf2)
        if bytes_read:
            audio.bufstate[6] = 0

def stop():
    """Stop playback"""
    if audio.bufstate[15]:  # thread_active
        audio.bufstate[16] = 1  # request stop
        
        # Brief wait for thread to exit
        timeout = 50
        while audio.bufstate[15] and timeout > 0:
            time.sleep_ms(2)
            timeout -= 1
    
    # Deinit timers
    try:
        audio.frame_timer.deinit()
    except:
        pass
    
    try:
        audio.callback_timer.deinit()
    except:
        pass
        
    if audio.data_file:
        audio.data_file.close()
        audio.data_file = None

def _start_playback():
    """Common playback startup"""
    # Reset state
    audio.bufstate[0] = 0   # current_buffer
    audio.bufstate[1] = 0   # pos_in_buffer
    audio.bufstate[3] = 0   # current_sample
    audio.bufstate[5] = 1   # buf1_needs_filling
    audio.bufstate[6] = 1   # buf2_needs_filling
    audio.bufstate[11] = 0  # loop_resync_needed
    audio.bufstate[12] = 32768  # saved_prediction
    audio.bufstate[13] = 0  # saved_index
    audio.bufstate[14] = 0  # loop_state_saved
    audio.bufstate[16] = 0  # stop_requested
    audio.bufstate[17] = 0  # playback_done
    audio.bufstate[18] = 0  # callback_triggered
    
    # Pre-fill buffers
    fill_buffers()
    
    # Start audio thread
    audio.bufstate[15] = 1  # thread_active
    try:
        _thread.start_new_thread(audio_loop, ())
    except OSError:
        audio.bufstate[15] = 0
        return False
    
    # Start buffer timer
    audio.frame_timer.init(freq=30, mode=Timer.PERIODIC, callback=fill_buffers)
    return True

def load(ima_filename):
    """Load and play IMA file"""
    stop()
    
    try:
        f = open(ima_filename, "rb")
        
        if f.read(4) != b'IMAA':
            f.close()
            return False
            
        sample_rate = struct.unpack('<I', f.read(4))[0]
        sample_count = struct.unpack('<I', f.read(4))[0]
        f.read(12)
        
        if sample_rate not in VALID_RATES:
            f.close()
            return False
        
        audio.data_file = f
        audio.file_start_pos = f.tell()
        audio.sample_delay = 1000000 // sample_rate
        audio.sample_rate = sample_rate
        audio.bufstate[4] = sample_count
        
        _start_playback()
        return True
        
    except:
        return False

def play():
    """Resume playback if paused"""
    if audio.data_file and not audio.bufstate[15]:
        _start_playback()
        return True
    return False

def open_id(ima_filename, file_id=None):
    """Open file for quick switching"""
    try:
        f = open(ima_filename, "rb")
        
        if f.read(4) != b'IMAA':
            f.close()
            return -1
            
        sample_rate = struct.unpack('<I', f.read(4))[0]
        sample_count = struct.unpack('<I', f.read(4))[0]
        f.read(12)
        
        if sample_rate not in VALID_RATES:
            f.close()
            return -1
        
        file_start_pos = f.tell()
        
        if file_id is None:
            audio.file_handles.append((f, sample_rate, sample_count, file_start_pos))
            return len(audio.file_handles) - 1
        else:
            while len(audio.file_handles) <= file_id:
                audio.file_handles.append(None)
            if audio.file_handles[file_id] and audio.file_handles[file_id][0]:
                audio.file_handles[file_id][0].close()
            audio.file_handles[file_id] = (f, sample_rate, sample_count, file_start_pos)
            return file_id
    except:
        return -1

def play_id(file_id=0):
    """Play opened file with retry logic"""
    if file_id >= len(audio.file_handles) or not audio.file_handles[file_id]:
        return False
    
    # Stop current playback if active
    if audio.bufstate[15]:  # thread_active
        audio.bufstate[16] = 1  # request stop
        
        retry_count = 10
        while audio.bufstate[15] and retry_count > 0:
            time.sleep_ms(2)
            retry_count -= 1
            
        if audio.bufstate[15]:
            return False
    
    # Setup file reference
    f, sample_rate, sample_count, file_start_pos = audio.file_handles[file_id]
    audio.data_file = f
    audio.file_start_pos = file_start_pos
    f.seek(file_start_pos)
    audio.sample_delay = 1000000 // sample_rate
    audio.sample_rate = sample_rate
    audio.bufstate[4] = sample_count
    
    # Try to start playback with retry
    retry_count = 3
    while retry_count > 0:
        if _start_playback():
            return True
        time.sleep_ms(5)
        retry_count -= 1
    
    return False

def close_ids():
    """Close all file handles"""
    stop()
    
    for file_info in audio.file_handles:
        if file_info and file_info[0]:
            try:
                file_info[0].close()
            except:
                pass
    audio.file_handles = []

def set_volume(volume):
    """Set volume 0-200"""
    audio.bufstate[7] = max(0, min(200, int(volume)))

def get_volume():
    """Get current volume"""
    return audio.bufstate[7]

def set_loop(enabled=True, start_sample=0, end_sample=0):
    """Set loop points"""
    audio.bufstate[10] = 1 if enabled else 0
    audio.bufstate[8] = start_sample & ~1
    audio.bufstate[9] = end_sample & ~1 if end_sample else 0
    audio.bufstate[14] = 0

def set_loop_seconds(enabled=True, start_seconds=0.0, end_seconds=0.0):
    """Set loop points in seconds"""
    start_sample = int(start_seconds * audio.sample_rate)
    end_sample = int(end_seconds * audio.sample_rate) if end_seconds > 0 else 0
    set_loop(enabled, start_sample, end_sample)

def get_loop_status():
    """Get current loop settings"""
    return {
        'enabled': bool(audio.bufstate[10]),
        'start_sample': audio.bufstate[8],
        'end_sample': audio.bufstate[9],
        'start_seconds': audio.bufstate[8] / audio.sample_rate if audio.sample_rate > 0 else 0,
        'end_seconds': audio.bufstate[9] / audio.sample_rate if audio.sample_rate > 0 else 0
    }

def set_end_callback(callback_func, *args):
    """Set playback end callback"""
    audio.end_callback = callback_func
    audio.callback_args = args if args else None

def clear_end_callback():
    """Clear callback"""
    audio.end_callback = None
    audio.callback_args = None
    audio.bufstate[18] = 0

def is_playing():
    """Check if playing"""
    return audio.bufstate[15] == 1

def get_position():
    """Get position 0-1"""
    if audio.bufstate[4] > 0:
        return audio.bufstate[3] / audio.bufstate[4]
    return 0.0

def get_position_seconds():
    """Get position in seconds"""
    if audio.sample_rate > 0:
        return audio.bufstate[3] / audio.sample_rate
    return 0.0

def get_duration_seconds():
    """Get duration in seconds"""
    if audio.sample_rate > 0:
        return audio.bufstate[4] / audio.sample_rate
    return 0.0

def get_status():
    """Get current playback status"""
    return {
        'playing': is_playing(),
        'thread_active': audio.bufstate[15],
        'current_sample': audio.bufstate[3],
        'total_samples': audio.bufstate[4],
        'sample_rate': audio.sample_rate,
        'volume': audio.bufstate[7],
        'loop_start': audio.bufstate[8],
        'loop_end': audio.bufstate[9],
        'loop_enabled': bool(audio.bufstate[10]),
        'callback_set': audio.end_callback is not None,
        'callback_triggered': audio.bufstate[18]
    }