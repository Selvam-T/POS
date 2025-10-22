from pynput import keyboard
import time

buffer = ''
last_time = 0
timeout = 0.05  # 50 milliseconds

def on_press(key):
    global buffer, last_time
    now = time.time()
    diff = now - last_time

    try:
        char = key.char
    except AttributeError:
        # handle special keys
        if key == keyboard.Key.enter and buffer:
            print("Barcode scanned:", buffer)
            buffer = ''
        return

    if diff > timeout:
        # slow typing → treat as manual input
        buffer = char
    else:
        # fast input → part of barcode
        buffer += char

    last_time = now

with keyboard.Listener(on_press=on_press) as listener:
    listener.join()
