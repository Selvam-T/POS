import sys
import unittest

# Ensure project package is on path
sys.path.insert(0, r'c:\Users\SELVAM\OneDrive\Desktop\POS\Project')
import main

class DrawerGatingTest(unittest.TestCase):
    def test_cash_present_opens(self):
        self.assertTrue(main.MainLoader._should_open_cash_drawer(None, {'cash': 50}))
        self.assertTrue(main.MainLoader._should_open_cash_drawer(None, {'cash': 50, 'tender': 0}))

    def test_no_cash_does_not_open(self):
        self.assertFalse(main.MainLoader._should_open_cash_drawer(None, {'cash': 0}))
        self.assertFalse(main.MainLoader._should_open_cash_drawer(None, {'voucher': 100}))

if __name__ == '__main__':
    unittest.main()
