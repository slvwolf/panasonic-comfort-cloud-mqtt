"""
Device class for handling the state of the device and the commands coming 
from HomeAssistant / MQTT.
"""
from time import time
import typing
import logging
from pcomfortcloud.session import Session
from pcomfortcloud import constants
import pcfmqtt.mappings as mappings


class DeviceState:
    """ State of a single device """

    def __init__(self, logger: logging.Logger, name: str, params: typing.Dict[str, typing.Any]) -> None:
        self.name: str = name
        self._log = logger
        self.defaults: bool = len(params) == 0
        self.temperature: float = params.get("temperature", 0)
        self.power: constants.Power = params.get("power", constants.Power.Off)
        self.temperature_inside: int = params.get("temperatureInside", 0)
        self.temperature_outside: int = params.get("temperatureOutside", 0)
        self.mode: constants.OperationMode = params.get(
            "mode", constants.OperationMode.Auto)
        self.fan_speed: constants.FanSpeed = params.get(
            "fanSpeed", constants.FanSpeed.Auto)
        self.air_swing_horizontal: constants.AirSwingLR = params.get(
            "airSwingHorizontal", constants.AirSwingLR.Auto)
        self.air_swing_vertical: constants.AirSwingUD = params.get(
            "airSwingVertical", constants.AirSwingUD.Auto)
        self.eco: constants.EcoMode = params.get("eco", constants.EcoMode.Auto)
        self.nanoe: constants.NanoeMode = params.get(
            "nanoe", constants.NanoeMode.On)
        self.epoch: float = time()

    def log_if_updated(self, current_value: typing.Any, new_value: typing.Any, value_name: str):
        if current_value != new_value:
            self._log.info("Updated %s ( %r -> %r )", value_name, current_value, new_value)
        return new_value

    def refresh_all(self, state: "DeviceState"):
        """
        Refresh the full state, including read-only metrics
        """
        self.refresh(state)
        self.temperature_inside = self.log_if_updated(
            self.temperature_inside, state.temperature_inside, "temperature inside")
        self.temperature_outside = self.log_if_updated(
            self.temperature_outside, state.temperature_outside, "temperature outside")

    def refresh(self, state: "DeviceState"):
        """
        Refresh the state from the given one. This is to update the current state from desired when 
        device has been succesfully update. 
        """
        self.defaults = False
        self.temperature = self.log_if_updated(
            self.temperature, state.temperature, "temperature")
        self.power = self.log_if_updated(
            self.power, state.power, "power")
        self.mode = self.log_if_updated(
            self.mode, state.mode, "mode")
        self.fan_speed = self.log_if_updated(
            self.fan_speed, state.fan_speed, "fan speed")
        self.air_swing_horizontal = self.log_if_updated(
            self.air_swing_horizontal, state.air_swing_horizontal,
            "air swing horizontal")
        self.air_swing_vertical = self.log_if_updated(
            self.air_swing_vertical, state.air_swing_vertical, "air swing vertical")
        self.eco = self.log_if_updated(self.eco, state.eco, "eco")
        self.nanoe = self.log_if_updated(
            self.nanoe, state.nanoe, "nanoe")
        self.epoch = time()


class Device:

    def __init__(self, raw: typing.Dict[str, typing.Any]) -> None:
        self._dirty = False # True if there is some message that failed and needs to be resent
        self._name: str = raw["name"]
        self._ha_name: str = "pcc_" + \
            raw["name"].lower().replace(" ", "_").strip()
        self._group: str = raw["group"]
        self._model: str = raw["model"]
        self._id: str = raw["id"]
        self._target_refresh: float = 0
        self._log = logging.getLogger(f"Device.{self.get_name()}")
        self._state: DeviceState = DeviceState(self._log, self.get_name(), {})
        self._desired_state: DeviceState = DeviceState(
            self._log, self.get_name(), {})
        self._log.info("New device: %s (%s)", self._name, self._ha_name)

    def update_state(self, session: Session, refresh_delay: float) -> bool:
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
        # Push delayed updates
        if self._dirty:
            self._send_update(session)
            self._dirty = False
        if self._target_refresh < time():
            self._log.debug("Retrieving data")
            data: typing.Dict[str, typing.Any] = session.get_device(self._id) # type: ignore
            if self._desired_state.defaults:
                self._desired_state = DeviceState(
                    self._log, self.get_name(), data["parameters"]) # type: ignore
            self._state.refresh_all(DeviceState(
                self._log, self.get_name(), data["parameters"])) # type: ignore
            self._target_refresh = time() + refresh_delay
            return True
        return False
    
    def set_eco(self, eco: constants.EcoMode):
        self._desired_state.eco = eco

    def set_nanoe(self, nanoe: constants.NanoeMode):
        self._desired_state.nanoe = nanoe

    def get_power(self) -> constants.Power:
        return self._state.power

    def set_power(self, power: constants.Power):
        self._desired_state.power = power

    def get_eco_str(self) -> str:
        return mappings.eco_to_string.get(self._state.eco, "none")

    def get_nanoe_str(self) -> str:
        return mappings.nanoe_to_string.get(self._state.nanoe, "none")

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
    
    def get_fanmode_str(self) -> str:
        return mappings.fans_to_string.get(self._state.fan_speed, "")

    def set_fanmode(self, fan: constants.FanSpeed):
        self._desired_state.fan_speed = fan

    def get_swingmode_str(self) -> str:
        return mappings.airswing_to_string.get(self._state.air_swing_vertical, "")
    
    def set_swingmode(self, swing: constants.AirSwingUD):
        self._desired_state.air_swing_vertical = swing

    def get_swing_horizontal_str(self) -> str:
        return mappings.airswing_horizontal_to_string.get(self._state.air_swing_horizontal, "")

    def set_swing_horizontal(self, swing: constants.AirSwingLR):
        self._desired_state.air_swing_horizontal = swing

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

    def _refresh_soon(self):
        """
        Refresh the state "soonish". It sometimes can take some seconds before the state is reflected
        in the response so wait a while before checking it. Fetching the state too soonish will result
        in the value being reverted back to the original one in HA eventhough the state is correct in 
        reality. 
        """
        self._target_refresh = time() + 5

    def _send_update(self, session: Session):
        try:
            if session.set_device(self.get_internal_id(), # type: ignore
                                mode=self._desired_state.mode,
                                power=self._desired_state.power,
                                temperature=self._desired_state.temperature,
                                fanSpeed=self._desired_state.fan_speed,
                                airSwingHorizontal=self._desired_state.air_swing_horizontal,
                                airSwingVertical=self._desired_state.air_swing_vertical,
                                nanoe=self._desired_state.nanoe,
                                eco=self._desired_state.eco):
                self._state.refresh(self._desired_state)
                self._refresh_soon()
            else:
                self._log.info("Device update failed")
        except Exception as e:
            # Occasionally the update fails with comfort cloud and needs to be retried at later time
            self._log.exception("Error in device update: %r", e)
            self._dirty = True
            self._refresh_soon()

    def _cmd_mode(self, session: Session, payload: str) -> bool:
        """
        Set operating mode command

        Sets the state according to the received payload (from HomeAssistant) and
        apply the change to the device.

        Returns true if something changed and state update needs to be delivered
        """
        target_mode = mappings.modes_to_literal.get(payload)
        target_power = mappings.power_to_literal.get(payload)
        # Change device mode
        if target_mode is not None:
            self.set_mode(target_mode)
            self.set_power(constants.Power.On)
            self._send_update(session)
            self._log.info("Command ->  Mode set to %s", payload)
            return True
        # Change power state
        if target_power is not None:
            # Don't turn off the device twice
            if self.get_power() != target_power:
                self.set_power(target_power)
                self._send_update(session)
                self._log.info("Command -> Mode set to %s", payload)
                return True
            self._log.info(
                "Mode command would not lead to action, skipping: %r", payload)
            return False
        # Unknown command
        self._log.info("Unknown mode command: %r", payload)
        return False

    def _cmd_fan(self, session: Session, payload: str) -> bool:
        """
        Set fan speed command

        Returns true if something changed and state update needs to be delivered
        """
        target_fan = mappings.fans_to_literal.get(payload)
        if target_fan is None:
            self._log.info("Unknown fan command: %r", payload)
            return False
        if self.get_fanmode_str() != target_fan:
            self.set_fanmode(target_fan)
            self._send_update(session)
            self._log.info("Command -> Fan set to %s", payload)
            return True
        self._log.info(
            "Fan command would not lead to action, skipping: %r", payload)
        return False

    def _cmd_swing(self, session: Session, payload: str) -> bool:
        """
        Set air swing command

        Returns true if something changed and state update needs to be delivered
        """
        target_swing = mappings.airswing_to_literal.get(payload)
        if target_swing is None:
            self._log.info("Unknown air swing command: %r", payload)
            return False
        if self.get_swingmode_str() != target_swing:
            self.set_swingmode(target_swing)
            self._send_update(session)
            self._log.info("Command -> Air swing set to %s", payload)
            return True
        self._log.info(
            "Air swing command would not lead to action, skipping: %r", payload)
        return False

    def _cmd_swing_horizontal(self, session: Session, payload: str) -> bool:
        """
        Set air swing horizontal command

        Returns true if something changed and state update needs to be delivered
        """
        target_swing = mappings.airswing_horizontal_to_literal.get(payload)
        if target_swing is None:
            self._log.info("Unknown air swing horizontal command: %r", payload)
            return False
        if self.get_swing_horizontal_str() != target_swing:
            self.set_swing_horizontal(target_swing)
            self._send_update(session)
            self._log.info("Command -> Air swing horizontal set to %s", payload)
            return True
        self._log.info(
            "Air swing horizontal command would not lead to action, skipping: %r", payload)
        return False

    def _cmd_temp(self, session: Session, payload: str) -> bool:
        """
        Set target temperature command

        Returns true if something changed and state update needs to be delivered
        """
        new_temp = float(payload)
        if new_temp == self._desired_state.temperature:
            self._log.info(
                "Temperature command would not lead to action, skipping: %s", payload)
            return False
        self.set_target_temperature(new_temp)
        self._send_update(session)
        self._log.info("Command ->  Temperature set to %r", payload)
        return True
    
    def _cmd_nanoe(self, session: Session, payload: str) -> bool:
        """
        Set nanoe command

        Returns true if something changed and state update needs to be delivered
        """
        target_nanoe = mappings.nanoe_to_literal.get(payload)
        if target_nanoe is None:
            self._log.info("Unknown nanoe command: %r", payload)
            return False
        if self.get_nanoe_str() != target_nanoe:
            self.set_nanoe(target_nanoe)
            self._send_update(session)
            self._log.info("Command -> Nanoe set to %s", payload)
            return True
        self._log.info(
            "Nanoe command would not lead to action, skipping: %r", payload)
        return False
    
    def _cmd_eco(self, session: Session, payload: str) -> bool:
        """
        Set eco command
        Returns true if something changed and state update needs to be delivered
        """
        target_eco = mappings.eco_to_literal.get(payload)
        if target_eco is None:
            self._log.info("Unknown eco command: %r", payload)
            return False
        if self.get_eco_str() != target_eco:
            self.set_eco(target_eco)
            self._send_update(session)
            self._log.info("Command -> Eco set to %s", payload)
            return True
        self._log.info(
            "Eco command would not lead to action, skipping: %r", payload)
        return False

    def _cmd_power(self, session: Session, payload: str) -> bool:
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
        self._log.info(
            "Power command would not lead to action, skipping: %r", payload)
        return False

    def command(self, session: Session, command: str, payload: str) -> bool:
        """
        Resolve command coming from HomeAssistant / MQTT. 

        Returns true if something changed and state update needs to be delivered
        """
        cmd = {"mode_cmd": self._cmd_mode,
               "temp_cmd": self._cmd_temp,
               "fan_cmd": self._cmd_fan,
               "swing_cmd": self._cmd_swing,
               "s_eco_cmd": self._cmd_eco,
               "s_nanoe_cmd": self._cmd_nanoe,
               "swing_h_cmd": self._cmd_swing_horizontal,
               "power_cmd": self._cmd_power}.get(command)
        if cmd:
            return cmd(session, payload)
        elif command in ["config", "state"]:
            return False
        else:
            self._log.warning("Unknown command: %s", command)
            return False
