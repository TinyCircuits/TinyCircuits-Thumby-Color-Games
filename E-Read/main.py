import time
from engine_draw import Color, update, clear, text
import engine
import engine_io
from engine_resources import FontResource

engine.fps_limit(60)

white = Color(255, 255, 255)
black = Color(0, 0, 0)

font = FontResource("SperryPC8x16-1bit.bmp")

chars = 14
lines = 6
pgturns = 0

try:
    with open("loc.txt", "r") as file:
        pgturns = int(file.read().strip() or 0)
except (OSError, ValueError):
    pgturns = 0
try:
    with open("chars.txt", "r") as file:
        chars = int(file.read().strip() or 0)
except (OSError, ValueError):
    chars = 14

def remove_enters_from_file(input_path, output_path):
    """
    Removes all newline characters from a text file and writes the result to a new file.
    """
    try:
        # Read file content
        with open(input_path, 'r') as infile:
            content = infile.read()
        
        # Remove both Unix (\n) and Windows (\r\n) line breaks, and ’ along with " as they show up as question marks.
        cleaned = content.replace('\n', '  ').replace('\r', '  ').replace('’', "'").replace('"', "'")

        # Write cleaned content to output file
        with open(output_path, 'w') as outfile:
            outfile.write(cleaned)

        print("All line breaks removed. Output saved to:", output_path)

    except OSError:
        print("Error: Could not open file", input_path)
    except Exception as e:
        print("Unexpected error:", e)

while True:
    clear(black)
    
    # Read the file and render text every frame so it stays on screen
    try:
        with open("processed.txt", "r", encoding="utf-8") as f:
            file_content = f.read()
            
        for i in range(lines):
            start_idx = chars * i
            start_idx += pgturns * chars
            end_idx = start_idx + chars
            current_text = file_content[start_idx:end_idx]
            
            text(font, current_text, white, 0, i * 20, 1, 1, 1)
            
    except FileNotFoundError:
        text(font, "processed.txt missing!", white, 0, 0, 1, 1, 1)

    # Handle button inputs to adjust layout dynamically
    if engine.tick():
        if engine_io.LEFT.is_pressed:
            chars = max(1, chars - 1)
        elif engine_io.RIGHT.is_pressed:
            chars += 1
        if engine_io.UP.is_pressed:
            lines = max(1, lines - 1)
        elif engine_io.DOWN.is_pressed:
            lines += 1
        if engine_io.RB.is_pressed:
            pgturns += 1
        elif engine_io.LB.is_pressed:
            if pgturns > 0:
                pgturns -= 1
        if engine_io.A.is_pressed:
            remove_enters_from_file("book.txt", "processed.txt")
        if engine_io.MENU.is_pressed:
            try:
                with open("loc.txt", "w") as file:
                    file.write(str(pgturns))
            except OSError:
                pass
            try:
                with open("chars.txt", "w") as file:
                    file.write(str(chars))
            except OSError:
                pass
            
            break
    
    time.sleep(0.1)
    update()