import re
from time import time
import paho.mqtt.client as mqtt
import pcomfortcloud
from pcfmqtt.events import state_event
import pcfmqtt.mappings as mappings
from pcomfortcloud import constants


class Device:

    def __init__(self, topic_prefix: str, raw: dict) -> None:
        self._name = raw["name"]
        self._topic_prefix = topic_prefix
        self._ha_name = "pcc_" + raw["name"].lower().replace(" ", "_").strip()
        self._group = raw["group"]
        self._model = raw["model"]
        self._id = raw["id"]
        self._params = {}
        self._target_refresh = 0
        print("New device: {} ({})".format(self._name, self._ha_name))

    def update_state(self, session: pcomfortcloud.Session, refresh_delay: int) -> bool:
        """
        Update device state from the cloud, return true if something was done

        Example payload for parameters for future reference,
            'parameters': 
                {'temperatureInside': 21,
                'temperatureOutside': -9,   
                'temperature': 22.0, 
                'power': <Power.Off: 0>, 
                'mode': <OperationMode.Auto: 0>, 
                'fanSpeed': <FanSpeed.Auto: 0>, 
                'airSwingHorizontal': <AirSwingLR.Auto: -1>, 
                'airSwingVertical': <AirSwingUD.Auto: -1>, 
                'eco': <EcoMode.Auto: 0>, 
                'nanoe': <NanoeMode.Off: 1>
            }
        """
        if self._target_refresh < time():
            print("Reading data for {}/{} ({})".format(self._name, self._ha_name, self._id))
            data = session.get_device(self._id)
            self._params = data["parameters"]
            self._target_refresh = time() + refresh_delay
            return True
        return False

    def get_power(self) -> constants.Power:
        return self._params["power"]

    def set_power(self, power: constants.Power):
        self._params["power"] = power

    def get_power_str(self) -> str:
        return mappings.power_to_string.get(self.get_power())

    def get_model(self) -> str:
        return self._model

    def get_name(self) -> str:
        return self._ha_name + "_ac"

    def get_mode(self) -> constants.OperationMode:
        return self._params["mode"]

    def get_mode_str(self) -> str:
        if not self.get_power():
            return "off"
        return mappings.modes_to_string.get(self.get_mode())

    def set_mode(self, mode: constants.OperationMode):
        self._params["mode"] = mode

    def get_component(self) -> str:
        return "climate"

    def get_id(self) -> str:
        return self.get_name()

    def get_internal_id(self) -> str:
        """
        Unique device id to identify the devices in Panasonic Cloud
        """
        return self._id

    def set_target_temperature(self, target: float):
        self._params["temperature"] = target

    def get_target_temperature(self) -> float:
        return self._params.get("temperature", 0)

    def get_temperature(self) -> float:
        return self._params.get("temperatureInside", 0)

    def get_temperature_outside(self) -> float:
        return self._params.get("temperatureOutside", 0)

    def _publish_state(self, client: mqtt.Client):
        topic, mqtt_payload = state_event(self._topic_prefix, self)
        client.publish(topic, mqtt_payload)

    def _cmd_mode(self, session: pcomfortcloud.Session, payload: str):
        """
        Set operating mode command
        """
        literal = mappings.modes_to_literal.get(payload)
        if literal:
            self.set_mode(literal)
            session.set_device(self.get_internal_id(), mode=literal,
                               power=constants.Power.On)
        elif payload == "off":
            # Don't turn off the device twice
            if self.get_power() != literal:
                self.set_power(constants.Power.Off)
                session.set_device(self.get_internal_id(),
                                power=constants.Power.Off)
        else:
            print("Unknown mode command: " + payload)
            return
        self._target_refresh = time() + 2

    def _cmd_temp(self, session: pcomfortcloud.Session, payload: str):
        """
        Set target temperature command
        """
        value = float(payload)
        session.set_device(self.get_internal_id(), temperature=value)
        self.set_target_temperature(payload)
        self._target_refresh = time() + 2

    def _cmd_power(self, session: pcomfortcloud.Session, payload: str):
        """
        Set power on/off command
        """
        literal = mappings.power_to_literal.get(payload.lower())
        if not literal:
            print("Bad power command received: " + payload)
            return
        # Don't turn off the device twice
        if self.get_power() != literal:
            self.set_power(literal)
            session.set_device(self.get_internal_id(), power=self.get_power())
            # Update state right away to get the current mode if the device was turned on
        self._target_refresh = time() + 2

    def command(self, client: mqtt.Client, session: pcomfortcloud.Session, command: str, payload: str):
        """
        Resolve command coming from HomeAssistant / MQTT
        """
        cmd = {"mode_cmd": self._cmd_mode,
               "temp_cmd": self._cmd_temp,
               "power_cmd": self._cmd_power}.get(command)
        if cmd:
            cmd(session, payload)
        elif command in ["config", "state"]:
            pass
        else:
            print("Unknown command: " + command)
            return
