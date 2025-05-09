""" Main service for pcfmqtt """
import time
import typing
import logging
from pcomfortcloud.session import Session
from pcomfortcloud.exceptions import Error
from pcfmqtt.device import Device
from pcfmqtt.mqtt import Mqtt

log = logging.getLogger(__name__)

class Service:
    """
    Main service
    """
    def __init__(self, username: str, password: str, mqtt: Mqtt, update_interval: int = 60,
                 session_wrapper: type[Session] = Session) -> None:
        self._username = username
        self._password = password
        self._mqtt: Mqtt = mqtt
        self._update_interval = update_interval
        self._devices: typing.Dict[str, Device] = {}
        self._wrapper_session = session_wrapper
        self._session: Session = session_wrapper(self._username, self._password)

    def connect_to_cc(self) -> bool:
        """
        Connect to Panasonic Comfort Cloud. This will also populate the initial devices list.

        @return: True if connected, False otherwise
        """
        log.info("Connecting to Panasonic Comfort Cloud..")
        try:
            self._session.login()
            log.info("Login succesfull. Reading and populating devices")
            self._devices = {}
            for d in self._session.get_devices():
                device = Device(d)
                # Refresh state after 30s so HA can pick it up
                device.update_state(self._session, 30)
                self._devices[device.get_id()] = device
                self._mqtt.introduce_device(device)
        except Error as e:
            log.error(
                "Failed initialization to Panasonic Comfort Cloud: %s. " +
                "Will attempt again in 10 minutes.", e)
            self._session = self._wrapper_session(self._username, self._password)
            return False
        log.info("Total %i devices found", len(self._devices))
        log.info("Connected to Panasonic Comfort Cloud")
        return True

    def _check_connections(self) -> bool:
        """
        Check if we are connected to CC. If not, try to reconnect.

        @return: True if connected, False otherwise
        """
        if not self._session.is_token_valid(): # type: ignore
            return self.connect_to_cc()
        return True

    def _sleep_on_last_error(self, last_error: bool):
        if last_error:
            # Protect Panasonic Comfort Cloud from being spammed with faulty requests.
            # Service seems to experience a good amount of Bad Gateway errors so better
            # to wait if too many errors are encountered.
            log.warning("Sequence of errors detected. " +
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
        last_full_update = 0
        last_error = False  # Flag to represent whether we encountered error on last update pass
        self._mqtt.connect(self.handle_message)
        try:
            while True:
                if not self._check_connections():
                    log.warning("Connection errors. Waiting for 10 minutes")
                    time.sleep(600)
                    continue
                try:
                    for device in self._devices.values():
                        if device.update_state(self._session, self._update_interval):
                            self._mqtt.send_state_event(device)
                    # Do one full update once an hour
                    # just in case we have missed HA restart for some reason
                    if last_full_update + 60*60 < time.time():
                        self._mqtt.send_discovery_events(list(self._devices.values()))
                        last_full_update = time.time()
                        log.info("Full discovery cycle done for all devices")
                    time.sleep(1)
                    last_error = False
                except Error as e:
                    log.exception("Error in Panasonic Comfort Cloud: %r", e)
                    self._sleep_on_last_error(last_error)
                    last_error = True
                    self._session = self._wrapper_session(self._username, self._password)
        except KeyboardInterrupt as e:
            log.exception("Interrupted: %r", e)
        finally:
            log.info("Shutting down")
            self._mqtt.disconnect()
            self._session.logout() # type: ignore
            log.info("Shutdown complete")

    def handle_message(self, device_id: str, command: str, payload: str):
        device = self._devices.get(device_id)
        if device:
            if device.command(self._session, command, payload):
                self._mqtt.send_state_event(device)
                log.info("%s: Reported state change, sending update to HA", device.get_name())
            else:
                log.debug("%s: Reported no state change, ignoring", device.get_name())
        else:
            log.debug("No device for this event, ignoring")
