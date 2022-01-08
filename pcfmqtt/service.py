import pcomfortcloud
import paho.mqtt.client as mqtt
import time
from pcfmqtt.device import Device
from pcfmqtt.events import discovery_event, state_event


class Service:
    """
    Main service
    """
    def __init__(self, username: str, password: str, mqtt: str, mqtt_port: int, topic_prefix: str, update_interval: int = 60) -> None:
        self._topic_prefix = topic_prefix
        self._username = username
        self._password = password
        self._mqtt = mqtt
        self._mqtt_port = mqtt_port
        self._update_interval = update_interval
        self._devices = {}
        self._client = None  # type: mqtt.Client
        self._session = None  # type: pcomfortcloud.Session

    def start(self):
        print("Connecting to Panasonic Comfort Cloud..")
        self._session = pcomfortcloud.Session(self._username, self._password)
        self._session.login()
        print("Connected")

        print("Reading and populating devices")
        for d in self._session.get_devices():
            device = Device(self._topic_prefix, d)
            device.update_state(self._session, 30) # Refresh state after 30s so HA can pick it up
            self._devices[device.get_id()] = device

        print("Total {} devices found".format(len(self._devices)))

        print("Starting up MQTT")
        self._client = mqtt.Client()
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.connect(self._mqtt, self._mqtt_port, 60)
        self._client.loop_start()

        try:
            while True:
                for device in self._devices.values():
                    if device.update_state(self._session, self._update_interval):
                        state_topic, state_payload = state_event(self._topic_prefix, device)
                        self._client.publish(state_topic, state_payload)
                time.sleep(1)
        except KeyboardInterrupt:
            pass
        finally:
            print("Shutting down")
            self._client.disconnect()
            self._session.logout()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        print("Connected")
        client.subscribe("{}/#".format(self._topic_prefix))

        for device in self._devices.values():
            events = discovery_event(self._topic_prefix, device)
            for topic, payload in events:
                print("Registering to {}".format(topic))
                client.publish(topic, payload)

    def on_message(self, client: mqtt.Client, userdata, msg):
        parts = msg.topic.split("/")
        if parts[0] != self._topic_prefix or len(parts) < 4:
            return
        device_id = parts[2]
        command = parts[3]

        device = self._devices.get(device_id)
        if device:
            device.command(client, self._session, command,
                           msg.payload.decode('utf-8'))
            print("{}:{} >> {}".format(device_id, command, msg.payload))
