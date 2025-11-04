"""
Barcode Scanner Module
Listens for rapid keyboard input from barcode scanners using pynput.
Emits Qt signals when complete barcodes are detected.

Usage:
    scanner = BarcodeScanner()
    scanner.barcode_scanned.connect(my_handler_function)
    scanner.start()
"""

from PyQt5.QtCore import QObject, pyqtSignal, QThread
from pynput import keyboard
import time


class BarcodeScanner(QObject):
    """
    Barcode scanner listener that distinguishes scanner input from manual typing.
    
    Signals:
        barcode_scanned(str): Emitted when a complete barcode is detected
    """
    
    # Qt Signal: emitted when barcode is scanned
    barcode_scanned = pyqtSignal(str)
    
    def __init__(self, timeout=0.05):
        """
        Initialize barcode scanner.
        
        Args:
            timeout: Time threshold in seconds to distinguish scanner from manual typing
                    Scanner typically inputs characters in <50ms intervals
                    Manual typing is typically >100ms intervals
        """
        super().__init__()
        self._buffer = ''
        self._last_time = 0
        self._timeout = timeout
        self._listener = None
        self._listener_thread = None
        self._enabled = True
        self._min_barcode_length = 3  # Minimum characters for valid barcode
        
    def start(self):
        """Start listening for barcode scanner input."""
        if self._listener is not None:
            return
            
        # Create keyboard listener
        self._listener = keyboard.Listener(on_press=self._on_key_press)
        
        # Start listener in background thread
        self._listener.start()
        
    def stop(self):
        """Stop listening for barcode scanner input."""
        if self._listener is not None:
            self._listener.stop()
            self._listener = None
            self._buffer = ''
            
    def set_enabled(self, enabled: bool):
        """
        Enable or disable barcode processing without stopping the listener.
        
        Args:
            enabled: True to process barcodes, False to ignore
        """
        self._enabled = enabled
        if not enabled:
            self._buffer = ''  # Clear buffer when disabled
            
    def _on_key_press(self, key):
        """
        Callback for keyboard events from pynput.
        
        Args:
            key: The key that was pressed
        """
        if not self._enabled:
            return
            
        now = time.time()
        time_diff = now - self._last_time
        
        try:
            # Get character from key
            char = key.char
        except AttributeError:
            # Handle special keys (Enter, Shift, etc.)
            if key == keyboard.Key.enter:
                if self._buffer and len(self._buffer) >= self._min_barcode_length:
                    # Enter key pressed with data in buffer → barcode complete
                    barcode = self._buffer.strip()
                    if barcode:
                        # Emit Qt signal (thread-safe)
                        self.barcode_scanned.emit(barcode)
                    self._buffer = ''
                else:
                    self._buffer = ''
            return
        
        # Check timing to distinguish scanner from manual typing
        if time_diff > self._timeout:
            # Slow typing → likely manual input, start new buffer
            self._buffer = char
            
        else:
            # Fast input → likely scanner, append to buffer
            self._buffer += char
            
            
        self._last_time = now
