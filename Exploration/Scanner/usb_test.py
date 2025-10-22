import usb.core
devs = usb.core.find(find_all=True)
for dev in devs:
    print(f"Device: VID=0x{dev.idVendor:04x}, PID=0x{dev.idProduct:04x}, Class=0x{dev.bDeviceClass:02x}")