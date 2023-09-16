import pcomfortcloud # type: ignore
import paho.mqtt.client as mqtt # type: ignore
import time
import types
import logging
from pcfmqtt.device import Device
from pcfmqtt.events import discovery_event, state_event


class SessionWrapper(pcomfortcloud.Session):
    """
    Wrapper for changing the version string in session 
    """
    def _headers(self):
        return {
            "X-APP-TYPE": "1",
            "X-APP-VERSION": "1.19.0",
            "X-User-Authorization": self._vid,
            "X-APP-TIMESTAMP": "1",
            "X-APP-NAME": "Comfort Cloud",
            "X-CFC-API-KEY": "Comfort Cloud",
            "User-Agent": "G-RAC",
            "Accept": "application/json; charset=utf-8",
            "Content-Type": "application/json; charset=utf-8"
        }


class Service:
    """
    Main service
    """

    def __init__(self, username: str, password: str, mqtt_addr: str, mqtt_port: int, topic_prefix: str, update_interval: int = 60) -> None:
        self._topic_prefix = topic_prefix
        self._username = username
        self._password = password
        self._mqtt = mqtt_addr
        self._mqtt_port = mqtt_port
        self._log = logging.getLogger('Service')
        self._update_interval = update_interval
        self._devices: types.Dict[str, Device] = {} # type: ignore
        self._client: mqtt.Client = None # type: ignore
        self._session: pcomfortcloud.Session = None
        self._wrapper_session = SessionWrapper
        self._wrapper_mqtt = mqtt.Client
    
    def connect_to_cc(self) -> bool:
        """
        Connect to Panasonic Comfort Cloud. This will also populate the initial devices list.

        @return: True if connected, False otherwise
        """
        self._log.info("Connecting to Panasonic Comfort Cloud..")
        self._session = self._wrapper_session(self._username, self._password)
        try:
            self._session.login()
            self._log.info("Login succesfull. Reading and populating devices")
            self._devices = {}
            for d in self._session.get_devices():
                device = Device(self._topic_prefix, d)
                # Refresh state after 30s so HA can pick it up
                device.update_state(self._session, 30)
                self._devices[device.get_id()] = device
        except Exception as e:
            self._log.error("Failed initialization to Panasonic Comfort Cloud: %s. Will attempt again in 10 minutes.", e)
            self._session = None
            return False
        self._log.info("Total %i devices found", len(self._devices))
        self._log.info("Connected to Panasonic Comfort Cloud")
        return True

    def connect_mqtt(self):
        try:
            if self._client is not None:
                self._client.disconnect()
        except:
            self._log.info("MQTT client already disconnected")
        self._log.info("Starting up MQTT..")
        self._client = self._wrapper_mqtt()
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.connect(self._mqtt, self._mqtt_port, 60)
        self._client.loop_start()
        self._log.info("MQTT started")

    def _check_and_reconnect(self) -> bool:
        """
        Check if we are connected to CC and MQTT. If not, try to reconnect.

        @return: True if connected, False otherwise
        """
        if self._session is None:
            self._log.info("Resetting connection")
            status = self.connect_to_cc()
            self.connect_mqtt()
            return status
        return True

    def start(self):
        self.connect_to_cc()
        self.connect_mqtt()
        last_full_update = time.time()
        last_error = False  # Flag to represent whether we encountered error on last update pass
        try:
            while True:
                if not self._check_and_reconnect():
                    self._log.warn("Connection errors. Waiting for 10 minutes")
                    time.sleep(600)
                    continue
                try:
                    for device in self._devices.values():
                        if device.update_state(self._session, self._update_interval):
                            state_topic, state_payload = state_event(
                                self._topic_prefix, device)
                            self._client.publish(state_topic, state_payload)
                    # Do one full update once an hour - just in case we have missed HA restart for some reason
                    if last_full_update + 60*60 < time.time():
                        self._send_discovery_events()
                        last_full_update = time.time()
                    time.sleep(1)
                    last_error = False
                except Exception as e:
                    if isinstance(e, KeyboardInterrupt):
                        raise e
                    if last_error:
                        # Protect Panasonic Comfort Cloud from being spammed with faulty requests. Service seems to
                        # experience a good amount of Bad Gateway errors so better to wait if too many errors are
                        # encountered.
                        self._log.warn("Sequence of errors detected. Halting requests for 10 minutes: %r", e)
                        time.sleep(600)
                        # Reset everything
                        self._session = None
                    else:
                        self._log.exception("Error when updating device state", e)
                        last_error = True
                        time.sleep(60)
        except KeyboardInterrupt as e:
            self._log.exception("Interrupted", e)
        finally:
            self._log.info("Shutting down")
            if self._client is not None:
                self._client.disconnect()
            if self._session is not None:
                self._session.logout()

    def on_connect(self, client: mqtt.Client, userdata, flags, rc):
        self._log.info("Connected")
        for k in self._devices.keys():        
            client.subscribe(f"{self._topic_prefix}/climate/{k}/#")
        client.subscribe("homeassistant/status")
        self._send_discovery_events()

    def _send_discovery_events(self):
        for device in self._devices.values():
            events = discovery_event(self._topic_prefix, device)
            for topic, payload in events:
                self._log.info("Publishing entity configuration to %s", topic)
                self._client.publish(topic, payload)

    def _handle_hass_status(self, client: mqtt.Client, payload: str):
        if payload == "online":
            self._log.info("Received hass online event, resending configuration..")
            self._send_discovery_events()
        elif payload == "offline":
            self._log.info("Received hass offline event")
        else:
            self._log.info("Unknown status from hass: %s", payload)

    def on_message(self, client: mqtt.Client, userdata, msg):
        if msg.topic == "homeassistant/status":
            self._handle_hass_status(client, msg.payload.decode('utf-8'))
            return
        parts = msg.topic.split("/")
        if parts[0] != self._topic_prefix or len(parts) < 4:
            return
        device_id = parts[2]
        command = parts[3]

        payload = msg.payload.decode('utf-8')
        self._log.debug("Received message (%s): %r", msg.topic, payload)
        device = self._devices.get(device_id)
        if device:
            if device.command(client, self._session, command, payload):
                self._log.info("%s: Reported state change, sending update to HA", device.get_name())
                state_topic, state_payload = state_event(self._topic_prefix, device)
                self._client.publish(state_topic, state_payload)
            else:
                self._log.debug("%s: Reported no state change, ignoring", device.get_name())
        else:
            self._log.debug("No device for this event, ignoring")
