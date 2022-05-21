import re
from time import time
import paho.mqtt.client as mqtt
import pcomfortcloud
from pcfmqtt.events import state_event
import pcfmqtt.mappings as mappings
from pcomfortcloud import constants

class DeviceState:

    def __init__(self, params: dict) -> None:
        self.temperature = params.get("temperature", 0) # type: float
        self.power = params.get("power", constants.Power.Off) # type: constants.Power
        self.temperature_inside = params.get("temperatureInside", 0) # type: int
        self.temperature_outside = params.get("temperatureOutside", 0) # type: int
        self.mode = params.get("mode", constants.OperationMode.Auto) # type: constants.OperationMode
        self.fan_speed = params.get("fanSpeed", constants.FanSpeed.Mid) # type: constants.FanSpeed
        self.air_swing_horizontal = params.get("airSwingHorizontal", constants.AirSwingLR.Mid) # type: constants.AirSwingLR
        self.air_swing_vertical = params.get("airSwingVertical", constants.AirSwingUD.Mid) # type: constants.AirSwingUD
        self.eco = params.get("eco", constants.EcoMode.Auto) # type: constants.EcoMode
        self.nanoe = params.get("nanoe", constants.NanoeMode.On) # type: constants.NanoeMode

    def refresh(self, state: "DeviceState"):
        """
        Refresh the state from the given one. This is to update the current state from desired when device has been succesfully
        update. 
        """
        self.temperature = state.temperature
        self.power = state.power
        self.mode = state.mode
        self.fan_speed = state.fan_speed
        self.air_swing_horizontal = state.air_swing_horizontal
        self.air_swing_vertical = state.air_swing_vertical
        self.eco = state.eco
        self.nanoe = state.nanoe

class Device:

    def __init__(self, topic_prefix: str, raw: dict) -> None:
        self._name = raw["name"]
        self._topic_prefix = topic_prefix
        self._ha_name = "pcc_" + raw["name"].lower().replace(" ", "_").strip()
        self._group = raw["group"]
        self._model = raw["model"]
        self._id = raw["id"]
        self._state = None # type: DeviceState
        self._desired_state = None # type: DeviceState
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
            print("Retrieving data for {}/{} ({})".format(self._name, self._ha_name, self._id))
            data = session.get_device(self._id)
            self._stage = DeviceState(data["parameters"])
            # If we have not initialized the device yet, assume current params are the desired state
            if not self._desired_state:
                self._desired_state = DeviceState(data["parameters"])
            self._target_refresh = time() + refresh_delay
            print("Data received for {}/{} ({})".format(self._name, self._ha_name, self._id))
            return True
        return False

    def get_power(self) -> constants.Power:
        return self._state.power

    def set_power(self, power: constants.Power):
        self._state.power = power
        self._desired_state.power = power

    def get_power_str(self) -> str:
        return mappings.power_to_string.get(self.get_power())

    def get_model(self) -> str:
        return self._model

    def get_name(self) -> str:
        return self._ha_name + "_ac"

    def get_mode(self) -> constants.OperationMode:
        return self._state.mode

    def get_mode_str(self) -> str:
        if self.get_power() == constants.Power.Off:
            return "off"
        return mappings.modes_to_string.get(self.get_mode())

    def set_mode(self, mode: constants.OperationMode):
        self._state.mode = mode
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

    def set_target_temperature(self, target: float):
        self._state.temperature = target
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
        Refresh the state "soonish"
        """
        self._target_refresh = time() + 10

    def _update_state(self, session: pcomfortcloud.Session):
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

    def _cmd_mode(self, session: pcomfortcloud.Session, payload: str):
        """
        Set operating mode command
        """
        literal = mappings.modes_to_literal.get(payload)
        if literal:
            self.set_mode(literal)
            self.set_power(constants.Power.On)
            self._update_state(session)
        elif payload == "off":
            # Don't turn off the device twice
            if self.get_power() != literal:
                self.set_power(constants.Power.Off)
                self._update_state(session)
        else:
            print("Unknown mode command: " + payload)
            return

    def _cmd_temp(self, session: pcomfortcloud.Session, payload: str):
        """
        Set target temperature command
        """
        self.set_target_temperature(float(payload))
        self.update_state(session)

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
            self.update_state(session)

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
