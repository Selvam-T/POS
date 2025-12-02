# honeywell_reader.py

import serial

def read_barcode(port="/dev/ttyUSB0", baudrate=9600, timeout=1):
    try:
        ser = serial.Serial(port, baudrate=baudrate, timeout=timeout)
        print(f"Listening for barcodes on {port} ... Press Ctrl+C to stop.")

        while True:
            data = ser.readline().decode('utf-8').strip()
            if data:
                print(f"[Captured Barcode] {data}")
                
                # Example parse: numeric / alphanumeric check
                if data.isdigit():
                    print(f"→ Parsed as numeric code: {data}")
                elif data.isalnum():
                    print(f"→ Parsed as alphanumeric code: {data}")
                else:
                    print(f"→ Raw barcode data: {repr(data)}")

    except serial.SerialException as e:
        print(f"Error: {e}")
    except KeyboardInterrupt:
        print("\nStopped by user.")

if __name__ == "__main__":
    # adjust /dev/ttyUSB0 based on your device
    read_barcode("/dev/ttyUSB0")
