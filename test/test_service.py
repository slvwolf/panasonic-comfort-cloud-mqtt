import unittest
from unittest import mock

from pcomfortcloud.session import Session
from pcfmqtt.mqtt import Mqtt
from pcfmqtt.service import Service


class TestService(unittest.TestCase):

    def test_init(self):
        self.mqtt_mock = mock.create_autospec(Mqtt, instance=True)
        self.session_mock = mock.create_autospec(Session)
        Service("username", "password", self.mqtt_mock, 60, self.session_mock)

