import unittest
from unittest import mock
from pcfmqtt.service import Service


class TestService(unittest.TestCase):

    def test_init(self):
        service = Service("username", "password", "mqtt", 1883, "topic")
        service._wrapper_mqtt = mock.Mock()
        service._wrapper_session = mock.Mock()
        self.assertEqual("topic", service._topic_prefix)
        self.assertEqual("username", service._username)
        self.assertEqual("password", service._password)
        self.assertEqual("mqtt", service._mqtt)
        self.assertEqual(1883, service._mqtt_port)
        self.assertEqual(60, service._update_interval)
        self.assertEqual({}, service._devices)
        self.assertIsNone(service._client)
        self.assertIsNone(service._session)
