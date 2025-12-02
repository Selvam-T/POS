# honeywell_reader2.py
from pynput import keyboard
import time

pressed_keys = []  # Accumulate chars
timestamps = []    # Track timings
SCAN_THRESHOLD = 0.3  # 300ms for burst
MIN_SCAN_LENGTH = 4   # Min chars for scanner

def on_press(key):
    timestamp = time.time()
    try:
        print(f"Key detected: {key}")  # Debug (remove later)
        if key.char:
            pressed_keys.append(key.char)
            timestamps.append(timestamp)
            # Check for burst end on char (or Enter)
        elif key == keyboard.Key.enter:
            print("Enter detected—checking for scan...")  # Debug
            if len(pressed_keys) >= MIN_SCAN_LENGTH:
                burst_time = timestamps[-1] - timestamps[0] if len(timestamps) > 1 else 0
                if burst_time <= SCAN_THRESHOLD * (len(pressed_keys) - 1):
                    # It's a fast scan: process and suppress (but since per-key, retro suppress not direct; flag for next)
                    data = ''.join(pressed_keys)
                    print(f"[Captured Barcode] {data.strip()}")
                    if data.isdigit():
                        print(f"→ Parsed as numeric code: {data}")
                    pressed_keys.clear()
                    timestamps.clear()
                    return False  # Suppress Enter
            # Slow typing: allow
    except AttributeError:
        pass
    return None  # Allow non-char/Enter

def on_release(key):
    if key == keyboard.Key.esc:
        return False

print("Listening for barcode input ... Press ESC to stop. Type normally for keyboard test.")
with keyboard.Listener(on_press=on_press, on_release=on_release, suppress=False) as listener:  # No global suppress
    listener.join()