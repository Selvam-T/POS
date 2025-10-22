from escpos.printer import Network  # or Usb, Serial depending on your setup

# Example: Ethernet printer
printer = Network("192.168.0.10")  # Replace with your printer's IP

# Send pulse to open drawer
printer.cashdraw(2)  # 2 = Drawer kick connector pin 2 (default for Epson)

# Optional: print receipt after opening
printer.text("Drawer opened!\n")
printer.cut()
