import os
import sys
import unittest
import importlib

# Add current folder to path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

# Import using importlib because of hyphens in filename
send_via_taildrop = importlib.import_module("send-via-taildrop")

class TestTaildrop(unittest.TestCase):
    def test_device_icons(self):
        self.assertIn("linux", send_via_taildrop.DEVICE_ICONS)
        self.assertEqual(send_via_taildrop.DEVICE_ICONS["linux"], "computer-symbolic")
        self.assertEqual(send_via_taildrop.DEVICE_ICONS["macos"], "laptop-symbolic")

    def test_device_button_properties(self):
        btn = send_via_taildrop.DeviceButton("MyDevice", "linux", lambda x: None)
        self.assertEqual(btn.name, "MyDevice")
        self.assertIsNotNone(btn.btn)

if __name__ == "__main__":
    unittest.main()
