import typing
import json
import paho.mqtt.client as mqtt
from pcfmqtt.device import Device
from pcfmqtt.events import discovery_event

class Mqtt:

    def __init__(self, discovery_prefix: str, devices: typing.Dict[str, Device]) -> None:
        self._discovery_prefix = discovery_prefix
        self._devices = devices
        self._client = None # type: mqtt.Client

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        print("Connected with result code "+str(rc))
        client.subscribe("{}/#".format(self._discovery_prefix))

        for device in self._devices:
            events = discovery_event(self._discovery_prefix, device)
            for topic, payload in events:
                print("Registering to {}".format(topic))
                client.publish(topic, json.dumps(payload))

    def on_message(self, client: mqtt.Client, userdata, msg):
        parts = msg.topic.split("/")
        if parts[0] != self._discovery_prefix:
            return
        device_id = parts[2]
        command = parts[3]

        device = self._devices.get(device_id)
        if device:
            device.command(client, command, msg.payload)
            print("(Handled) {}:{} >> {}".format(device_id, command, str(msg.payload)))
        else:
            print("{}:{} >> {}".format(device_id, command, str(msg.payload)))

    def start(self, server: str, port: int):
        self._client = mqtt.Client()
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.connect(server, port, 60)
        self._client.loop_start()
        