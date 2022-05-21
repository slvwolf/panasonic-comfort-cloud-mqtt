import unittest

from pcfmqtt.device import Device

raw_data = {"name": "name", "group": "group", "model": "model", "id": "id"}

class TestStringMethods(unittest.TestCase):

    def test_init(self):
        device = Device("topic", raw_data)
        self.assertEqual("pcc_name_ac", device.get_name())
        self.assertEqual(device.get_name(), device.get_id())
        self.assertEqual("model", device.get_model())
        self.assertEqual("id", device.get_internal_id())

    def test_state_available_without_init(self):
        device = Device("topic", raw_data)
        self.assertEqual("off", device.get_power_str())

    def test_fail_missing_raw_data(self):
        with self.assertRaises(KeyError):
            Device("topic", {})

if __name__ == '__main__':
    unittest.main()