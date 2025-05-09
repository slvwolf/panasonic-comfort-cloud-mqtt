""" Tests for Device """
import unittest
from unittest import mock
from pcfmqtt.device import Device

raw_data = {"name": "name", "group": "group", "model": "model", "id": "id"}


class TestDevice(unittest.TestCase):
    """ Test Device class """

    def test_init(self):
        """ Initialization needs to set the required values """
        device = Device(raw_data)
        self.assertEqual("pcc_name_ac", device.get_name())
        self.assertEqual(device.get_name(), device.get_id())
        self.assertEqual("model", device.get_model())
        self.assertEqual("id", device.get_internal_id())

    def test_state_available_without_init(self):
        """ Device state is available without providing init value """
        device = Device(raw_data)
        self.assertEqual("off", device.get_power_str())

    def test_fail_missing_raw_data(self):
        """ Exception should be raised if raw data is missing """
        with self.assertRaises(KeyError):
            Device({})

    def test_respect_update_delay(self):
        device = Device(raw_data)
        session = mock.Mock()
        session.get_device.return_value = {"parameters": {"temperature": 40}}
        self.assertTrue(device.update_state(session, 10))
        self.assertEqual(40, device.get_temperature())

        session.get_device.return_value = {"parameters": {"temperature": 45}}
        self.assertFalse(device.update_state(session, 10))
        self.assertEqual(40, device.get_temperature())

    def test_update_desired_state_once(self):
        device = Device(raw_data)
        session = mock.Mock()
        session.get_device.return_value = {"parameters": {"temperature": 40}}

        # Update first time
        device.update_state(session, 0)
        self.assertEqual(40, device.get_temperature())
        self.assertEqual(40, device.get_target_temperature())

        # Ignore new states in desired
        session.get_device.return_value = {"parameters": {"temperature": 45}}
        device.update_state(session, 0)
        self.assertEqual(45, device.get_temperature())
        self.assertEqual(40, device.get_target_temperature())

    def test_update_epoch_on_refresh(self):
        device = Device(raw_data)
        session = mock.Mock()
        session.get_device.return_value = {"parameters": {"temperature": 40}}
        value = device.get_update_epoch()
        device.update_state(session, 0)
        self.assertGreater(device.get_update_epoch(), value)


if __name__ == '__main__':
    unittest.main()
