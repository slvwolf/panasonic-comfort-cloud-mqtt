from time import time
import typing
import logging
import paho.mqtt.client as mqtt # type: ignore
import pcomfortcloud # type: ignore
from pcfmqtt.events import state_event
import pcfmqtt.mappings as mappings
from pcomfortcloud import constants

class DeviceState:

    def __init__(self, logger: logging.Logger, name: str, params: dict) -> None:
        self.name: str = name
        self._log = logger
        self.defaults: bool = len(params) == 0
        self.temperature: float = params.get("temperature", 0) 
        self.power: constants.Power = params.get("power", constants.Power.Off)
        self.temperature_inside: int = params.get("temperatureInside", 0)
        self.temperature_outside: int = params.get("temperatureOutside", 0)
        self.mode: constants.OperationMode = params.get("mode", constants.OperationMode.Auto)
        self.fan_speed: constants.FanSpeed = params.get("fanSpeed", constants.FanSpeed.Auto)
        self.air_swing_horizontal: constants.AirSwingLR = params.get("airSwingHorizontal", constants.AirSwingLR.Auto) 
        self.air_swing_vertical: constants.AirSwingUD = params.get("airSwingVertical", constants.AirSwingUD.Auto) 
        self.eco: constants.EcoMode = params.get("eco", constants.EcoMode.Auto) 
        self.nanoe: constants.NanoeMode = params.get("nanoe", constants.NanoeMode.On) 
        self.epoch: float = time()

    def log_if_updated(self, current_value: typing.Any, new_value: typing.Any, device_name: str, value_name: str):
        if current_value != new_value:
            self._log.info("%s: Updated %s ( %r -> %r )", device_name, value_name, current_value, new_value)
        return new_value

    def refresh_all(self, state: "DeviceState"):
        """
        Refresh the full state, including read-only metrics
        """
        self.refresh(state)
        self.temperature_inside = self.log_if_updated(self.temperature_inside, state.temperature_inside, self.name, "temperature inside")
        self.temperature_outside = self.log_if_updated(self.temperature_outside, state.temperature_outside, self.name, "temperature outside")
    
    def refresh(self, state: "DeviceState"):
        """
        Refresh the state from the given one. This is to update the current state from desired when device has been succesfully
        update. 
        """
        self.defaults = False
        self.temperature = self.log_if_updated(self.temperature, state.temperature, self.name, "temperature")
        self.power = self.log_if_updated(self.power, state.power, self.name, "power")
        self.mode = self.log_if_updated(self.mode, state.mode, self.name, "mode")
        self.fan_speed = self.log_if_updated(self.fan_speed, state.fan_speed, self.name, "fan speed")
        self.air_swing_horizontal = self.log_if_updated(self.air_swing_horizontal, state.air_swing_horizontal, self.name, "air swing horizontal")
        self.air_swing_vertical = self.log_if_updated(self.air_swing_vertical, state.air_swing_vertical, self.name, "air swing vertical")
        self.eco = self.log_if_updated(self.eco, state.eco, self.name, "eco")
        self.nanoe = self.log_if_updated(self.nanoe, state.nanoe, self.name, "nanoe")
        self.epoch = time()

class Device:

    def __init__(self, topic_prefix: str, raw: dict) -> None:
        self._name: str = raw["name"]
        self._topic_prefix: str = topic_prefix
        self._ha_name: str = "pcc_" + raw["name"].lower().replace(" ", "_").strip()
        self._group: str = raw["group"]
        self._model: str = raw["model"]
        self._id: str = raw["id"]
        self._target_refresh: float = 0
        self._log = logging.getLogger(f"Device.{self.get_name()}")
        self._state: DeviceState = DeviceState(self._log, self.get_name(), {}) 
        self._desired_state: DeviceState = DeviceState(self._log, self.get_name(), {})
        self._log.info("New device: %s (%s)", self._name, self._ha_name)

    def update_state(self, session: pcomfortcloud.Session, refresh_delay: float) -> bool:
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
            # If we have not initialized the device yet

            self._log.info("Retrieving data")
            data = session.get_device(self._id)
            if self._desired_state.defaults:
                self._desired_state = DeviceState(self._log, self.get_name(), data["parameters"])

            self._state.refresh_all(DeviceState(self._log, self.get_name(), data["parameters"]))
            self._target_refresh = time() + refresh_delay
            return True
        return False

    def get_power(self) -> constants.Power:
        return self._state.power

    def set_power(self, power: constants.Power):
        self._desired_state.power = power

    def get_power_str(self) -> str:
        return mappings.power_to_string.get(self.get_power(), "none")

    def get_model(self) -> str:
        return self._model

    def get_name(self) -> str:
        return self._ha_name + "_ac"

    def get_mode(self) -> constants.OperationMode:
        return self._state.mode

    def get_mode_str(self) -> str:
        if self.get_power() == constants.Power.Off:
            return "off"
        return mappings.modes_to_string.get(self.get_mode(), "none")

    def set_mode(self, mode: constants.OperationMode):
        self._desired_state.mode = mode

    def get_component(self) -> str:
        return "climate"

    def get_id(self) -> str:
        return self.get_name()

    def get_internal_id(self) -> str:
        """
        Unique device id to identify the devices in Panasonic Cloud
        """
        return self._id

    def get_update_epoch(self) -> float:
        return self._state.epoch

    def set_target_temperature(self, target: float):
        self._desired_state.temperature = target

    def get_target_temperature(self) -> float:
        return self._state.temperature

    def get_temperature(self) -> float:
        return self._state.temperature_inside

    def get_temperature_outside(self) -> float:
        return self._state.temperature_outside

    def _publish_state(self, client: mqtt.Client):
        topic, mqtt_payload = state_event(self._topic_prefix, self)
        client.publish(topic, mqtt_payload)

    def _refresh_soon(self):
        """
        Refresh the state "soonish". It sometimes can take some seconds before the state is reflected
        in the response so wait a while before checking it. Fetching the state too soonish will result
        in the value being reverted back to the original one in HA eventhough the state is correct in 
        reality. 
        """
        self._target_refresh = time() + 5

    def _send_update(self, session: pcomfortcloud.Session):
        if session.set_device(self.get_internal_id(), 
                mode=self._desired_state.mode,
                power=self._desired_state.power,
                temperature=self._desired_state.temperature,
                fanSpeed=self._desired_state.fan_speed,
                airSwingHorizontal=self._desired_state.air_swing_horizontal,
                airSwingVertical=self._desired_state.air_swing_vertical,
                eco=self._desired_state.eco):
            self._state.refresh(self._desired_state)
            self._refresh_soon()
        else:
            self._log.info("Device update failed")

    def _cmd_mode(self, session: pcomfortcloud.Session, payload: str) -> bool:
        """
        Set operating mode command

        Returns true if something changed and state update needs to be delivered
        """
        literal = mappings.modes_to_literal.get(payload)
        if literal:
            self.set_mode(literal)
            self.set_power(constants.Power.On)
            self._send_update(session)
            self._log.info("Command ->  Mode set to %s", payload)
            return True
        elif payload == "off":
            # Don't turn off the device twice
            if self.get_power() != literal:
                self.set_power(constants.Power.Off)
                self._send_update(session)
                self._log.info("Command -> Mode set to %s", payload)
                return True
            self._log.info("Mode command would not lead to action, skipping: %r", payload)
            return False
        else:
            self._log.info("Unknown mode command: " + payload)
            return False

    def _cmd_temp(self, session: pcomfortcloud.Session, payload: str) -> bool:
        """
        Set target temperature command

        Returns true if something changed and state update needs to be delivered
        """
        new_temp = float(payload)
        if new_temp == self._desired_state.temperature:
            self._log.info("Temperature command would not lead to action, skipping: %s", payload)
            return False
        self.set_target_temperature(new_temp)
        self._send_update(session)
        self._log.info("Command ->  Temperature set to %r", payload)
        return True

    def _cmd_power(self, session: pcomfortcloud.Session, payload: str) -> bool:
        """
        Set power on/off command

        Returns true if something changed and state update needs to be delivered
        """
        literal = mappings.power_to_literal.get(payload.lower())
        if not literal:
            self._log.info("Bad power command received: %r", payload)
            return False
        # Don't turn off the device twice
        if self.get_power() != literal:
            self.set_power(literal)
            self._send_update(session)
            self._log.info("Command -> Power set to %r", payload)
            return True
        self._log.info("Power command would not lead to action, skipping: %r", payload)
        return False

    def command(self, client: mqtt.Client, session: pcomfortcloud.Session, command: str, payload: str) -> bool:
        """
        Resolve command coming from HomeAssistant / MQTT. 
        
        Returns true if something changed and state update needs to be delivered
        """
        cmd = {"mode_cmd": self._cmd_mode,
               "temp_cmd": self._cmd_temp,
               "power_cmd": self._cmd_power}.get(command)
        if cmd:
            return cmd(session, payload)
        elif command in ["config", "state"]:
            return False
        else:
            self._log.warn("Unknown command: %s", command)
            return False
