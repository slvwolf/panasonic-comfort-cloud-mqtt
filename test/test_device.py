import unittest
from unittest import mock
from pcfmqtt.device import Device

raw_data = {"name": "name", "group": "group", "model": "model", "id": "id"}

class TestDevice(unittest.TestCase):

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

    def test_respect_update_delay(self):
        device = Device("topic", raw_data)
        session = mock.Mock()
        session.get_device.return_value = {"parameters": {"temperature": 40}}
        self.assertTrue(device.update_state(session, 10))
        self.assertEqual(40, device._state.temperature)

        session.get_device.return_value = {"parameters": {"temperature": 45}}
        self.assertFalse(device.update_state(session, 10))
        self.assertEqual(40, device._state.temperature)

    def test_update_desired_state_once(self):
        device = Device("topic", raw_data)
        session = mock.Mock()
        session.get_device.return_value = {"parameters": {"temperature": 40}}

        # Update first time
        device.update_state(session, 0)
        self.assertEqual(40, device._state.temperature)
        self.assertEqual(40, device._desired_state.temperature)

        # Ignore new states in desired
        session.get_device.return_value = {"parameters": {"temperature": 45}}
        device.update_state(session, 0)
        self.assertEqual(45, device._state.temperature)
        self.assertEqual(40, device._desired_state.temperature)

if __name__ == '__main__':
    unittest.main()