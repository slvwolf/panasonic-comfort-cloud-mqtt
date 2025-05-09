import typing
from paho.mqtt.client import Client, WebsocketConnectionError
from paho.mqtt.client import MQTTMessage
import logging

from pcfmqtt.device import Device
from pcfmqtt.events import discovery_event, state_event

log = logging.getLogger(__name__)

class Mqtt(object):
    """
    MQTT client wrapper for the paho-mqtt library.
    This class handles the connection to the MQTT broker, subscribes to topics,
    and publishes messages to the broker.
    """

    def __init__(self, broker: str, port: int, topic_prefix: str, mqtt_wrapper: type[Client] = Client):
        self._port = port
        self._broker = broker
        self._topic_prefix = topic_prefix
        self._mqtt_wrapper: type[Client] = mqtt_wrapper
        self._client: Client = mqtt_wrapper()
        self._msg_callback: typing.Callable[[str, str, str], None] = lambda topic, payload, device_id: None
        self._ready = False
        # The last devices that were discovered, used to resend discovery events on reconnect
        self._last_discovery_devices: typing.List[Device] = []

    def _on_connect(self, client: Client, userdata: typing.Any, _flags: int, _rc: int):
        """ Handle MQTT connection """
        log.info("Connected to MQTT broker at %s:%s", self._broker, self._port)
        log.info("Subscribing to homeassistant/status")
        self._client.subscribe("homeassistant/status") # type: ignore
        self._ready = True

    def is_ready(self) -> bool:
        """ Check if the MQTT client is ready and it is ok to subscribe to topics """
        return self._ready

    def _subscribe(self, topic: str) -> None:
        """ Subscribe to a topic """
        log.info("Subscribing to %s", topic)
        self._client.subscribe(topic) # type: ignore

    def introduce_device(self, device: Device):
        """ Introduce a device to the MQTT broker, subscribing to its topics """
        for postfix in ["power_cmd", "mode_cmd", "temp_cmd", "fan_cmd", "swing_cmd", "swing_h_cmd", 
                       "s_eco_cmd", "s_nanoe_cmd"]:
            self._subscribe(f"{self._topic_prefix}/climate/{device.get_id()}/{postfix}")
    
    def _publish(self, topic: str, payload: str) -> None:
        """ Publish a message to the MQTT broker """
        log.debug("Publishing to %s: %s", topic, payload)
        try:
            self._client.publish(topic, payload) # type: ignore
        except WebsocketConnectionError as e:
            log.error("MQTT publish failed: %s", e)
            log.info("Starting recovery process")
            self.disconnect()
            self.connect(self._msg_callback)
            self.send_discovery_events(self._last_discovery_devices)
            log.info("Recovery process done")
            return

    def send_discovery_events(self, devices: typing.List[Device]) -> None:
        """ Send discovery events for the given device IDs """
        self._last_discovery_devices = devices
        for device in devices:
            events = discovery_event(self._topic_prefix, device)
            for topic, payload in events:
                log.info("Publishing entity configuration to %s", topic)
                self._publish(topic, payload)

    def send_state_event(self, device: Device) -> None:
        """ Send state event for the given device """
        state_topic, state_payload = state_event(self._topic_prefix, device)
        log.info("%s: Reported state change, sending update to HA", device.get_name())
        self._publish(state_topic, state_payload) # type: ignore

    def connect(self, message_callback: typing.Callable[[str, str, str], None]) -> None:
        """ Connect to MQTT """
        self._msg_callback = message_callback
        try:
            if self._client.is_connected(): # type: ignore
                log.info("MQTT client already connected, disconnecting..")
                self._client.disconnect() # type: ignore
        except WebsocketConnectionError as e:
            log.info("MQTT client already disconnected: %s", e)
        print(f"Connecting to MQTT broker at {self._broker}:{self._port}")
        self._client = self._mqtt_wrapper()
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._client.connect(self._broker, self._port, 60) # type: ignore
        self._client.loop_start() # type: ignore
        log.info("MQTT started")

    def disconnect(self) -> None:
        """ Disconnect from MQTT """
        log.info("Disconnecting from MQTT")
        self._client.loop_stop() # type: ignore
        self._client.disconnect() # type: ignore

    def is_connected(self) -> bool:
        """ Check if the MQTT client is connected """
        return self._client.is_connected() # type: ignore

    def _handle_hass_status(self, payload: str):
        if payload == "online":
            log.info("Received hass online event, resending configuration..")
            self.send_discovery_events(self._last_discovery_devices)
        elif payload == "offline":
            log.info("Received hass offline event")
        else:
            log.info("Unknown status from hass: %s", payload)

    def _on_message(self, client: Client, userdata: typing.Any, msg: MQTTMessage):
        """ Handle incoming MQTT messages and relay it to devices """
        payload = str(msg.payload.decode('utf-8')) # type: ignore
        topic = str(msg.topic) # type: ignore
        log.debug("Received message (%s): %s", topic, payload)
        if topic == "homeassistant/status":
            self._handle_hass_status(payload)
            return
        parts = topic.split("/")
        if parts[0] != self._topic_prefix or len(parts) < 4:
            return
        device_id = parts[2]
        command = parts[3]
        try:
            self._msg_callback(device_id, command, payload)
        except Exception as e:
            log.exception("Error in MQTT message callback: %s", e)
            return
