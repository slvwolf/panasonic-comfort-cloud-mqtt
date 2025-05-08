""" Main service for pcfmqtt """
import time
import typing
import logging
import paho.mqtt.client as mqtt
from pcomfortcloud.session import Session
from pcomfortcloud.exceptions import Error
from pcfmqtt.device import Device
from pcfmqtt.events import discovery_event, state_event

class Service:
    """s
    Main service
    """
    def __init__(self, username: str, password: str, mqtt_addr: str,
                 mqtt_port: int, topic_prefix: str, update_interval: int = 60,
                 mqtt_wrapper: type[mqtt.Client] = mqtt.Client,
                 session_wrapper: type[Session] = Session) -> None:
        self._topic_prefix = topic_prefix
        self._username = username
        self._password = password
        self._mqtt = mqtt_addr
        self._mqtt_port = mqtt_port
        self._log = logging.getLogger('Service')
        self._update_interval = update_interval
        self._devices: typing.Dict[str, Device] = {}
        self._wrapper_mqtt = mqtt_wrapper
        self._wrapper_session = session_wrapper
        self._client: mqtt.Client = mqtt_wrapper()
        self._session: Session = session_wrapper(self._username, self._password)

    def connect_to_cc(self) -> bool:
        """
        Connect to Panasonic Comfort Cloud. This will also populate the initial devices list.

        @return: True if connected, False otherwise
        """
        self._log.info("Connecting to Panasonic Comfort Cloud..")
        try:
            self._session.login()
            self._log.info("Login succesfull. Reading and populating devices")
            self._devices = {}
            for d in self._session.get_devices():
                device = Device(self._topic_prefix, d)
                # Refresh state after 30s so HA can pick it up
                device.update_state(self._session, 30)
                self._devices[device.get_id()] = device
        except Error as e:
            self._log.error(
                "Failed initialization to Panasonic Comfort Cloud: %s. " +
                "Will attempt again in 10 minutes.", e)
            self._session = self._wrapper_session(self._username, self._password)
            return False
        self._log.info("Total %i devices found", len(self._devices))
        self._log.info("Connected to Panasonic Comfort Cloud")
        return True

    def connect_mqtt(self):
        """ Connect to MQTT """
        try:
            if self._client.is_connected():
                self._log.info("Disconnecting MQTT")
                self._client.disconnect()
        except mqtt.WebsocketConnectionError as e:
            self._log.info("MQTT client already disconnected: %s", e)
        self._log.info("Starting up MQTT..")
        self._client = self._wrapper_mqtt()
        self._client.on_connect = self.on_connect
        self._client.on_message = self.on_message
        self._client.connect(self._mqtt, self._mqtt_port, 60)
        self._client.loop_start()
        self._log.info("MQTT started")

    def _check_connections(self) -> bool:
        """
        Check if we are connected to CC and MQTT. If not, try to reconnect.

        @return: True if connected, False otherwise
        """
        if not self._client.is_connected():
            self.connect_mqtt()
        if not self._session.is_token_valid():
            return self.connect_to_cc()
        return True

    def _sleep_on_last_error(self, last_error: bool):
        if last_error:
            # Protect Panasonic Comfort Cloud from being spammed with faulty requests.
            # Service seems to experience a good amount of Bad Gateway errors so better
            # to wait if too many errors are encountered.
            self._log.warning("Sequence of errors detected. " +
                              "Halting requests for 10 minutes")
            time.sleep(600)
        else:
            time.sleep(60)

    def start(self):
        """
        Start the service
        
        Main loop will update the devices and publish the state to MQTT. If connection to
        either CC or MQTT is lost, it will reset the connection and try to reconnect again
        in start of the loop.
        """
        last_full_update = time.time()
        last_error = False  # Flag to represent whether we encountered error on last update pass
        try:
            while True:
                if not self._check_connections():
                    self._log.warning("Connection errors. Waiting for 10 minutes")
                    time.sleep(600)
                    continue
                try:
                    for device in self._devices.values():
                        if device.update_state(self._session, self._update_interval):
                            state_topic, state_payload = state_event(
                                self._topic_prefix, device)
                            self._client.publish(state_topic, state_payload)
                    # Do one full update once an hour
                    # just in case we have missed HA restart for some reason
                    if last_full_update + 60*60 < time.time():
                        self._send_discovery_events()
                        last_full_update = time.time()
                    time.sleep(1)
                    last_error = False
                except Error as e:
                    self._log.exception("Error in Panasonic Comfort Cloud: %r", e)
                    self._sleep_on_last_error(last_error)
                    last_error = True
                    self._session = self._wrapper_session(self._username, self._password)
                except mqtt.WebsocketConnectionError as e:
                    self._log.exception("Error in MQTT: %r", e)
                    self._sleep_on_last_error(last_error)
                    last_error = True
                    self._mqtt = self._wrapper_mqtt()
        except KeyboardInterrupt as e:
            self._log.exception("Interrupted: %r", e)
        finally:
            self._log.info("Shutting down")
            self._client.disconnect()
            self._session.logout()

    def on_connect(self, client: mqtt.Client, _userdata, _flags, _rc):
        """ Handle MQTT connection """
        self._log.info("Connected")
        for k in self._devices:
            client.subscribe(f"{self._topic_prefix}/climate/{k}/#")
        client.subscribe("homeassistant/status")
        self._send_discovery_events()

    def _send_discovery_events(self):
        for device in self._devices.values():
            events = discovery_event(self._topic_prefix, device)
            for topic, payload in events:
                self._log.info("Publishing entity configuration to %s", topic)
                self._client.publish(topic, payload)

    def _handle_hass_status(self, _client: mqtt.Client, payload: str):
        if payload == "online":
            self._log.info(
                "Received hass online event, resending configuration..")
            self._send_discovery_events()
        elif payload == "offline":
            self._log.info("Received hass offline event")
        else:
            self._log.info("Unknown status from hass: %s", payload)

    def on_message(self, client: mqtt.Client, _userdata: typing.Any, msg: mqtt.MQTTMessage):
        """ Handle incoming MQTT messages and relay it to devices """
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
                self._log.info(
                    "%s: Reported state change, sending update to HA", device.get_name())
                state_topic, state_payload = state_event(
                    self._topic_prefix, device)
                self._client.publish(state_topic, state_payload)
            else:
                self._log.debug(
                    "%s: Reported no state change, ignoring", device.get_name())
        else:
            self._log.debug("No device for this event, ignoring")
