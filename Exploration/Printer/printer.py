from escpos.printer import Network

def test_print(ip="192.168.0.10", port=9100):
    try:
        # Connect to printer via network
        p = Network(ip, port)

        # Test print
        p.text("Vijay HELLO \n")
        p.text("This is a test receipt over Ethernet.\n")
        p.text("--------------------------------------\n")
        p.text("Thank you for shopping!\n\n\n")
        p.cut()

        print("Test receipt sent successfully.")

    except Exception as e:
        print("Printing failed:", str(e))


if __name__ == "__main__":
    test_print()
