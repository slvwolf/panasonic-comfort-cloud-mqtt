import paho.mqtt.client as mqtt
import pcomfortcloud
from pcfmqtt.events import state_event
import pcfmqtt.mappings as mappings
from pcomfortcloud import constants

class Device:

    def __init__(self, topic_prefix: str, raw: dict) -> None:
        self._name = raw["name"]
        self._topic_prefix = topic_prefix
        # TODO: Have proper name mangling herThis will definitely fail with unique names
        self._ha_name = "pcc_" + raw["name"].lower().replace(" ", "_").strip()
        self._group = raw["group"]
        self._model = raw["model"]
        self._id = raw["id"]
        self._params = {}
        self._target_temp = 0
        self._mode = "off"
        print("New device: {} ({})".format(self._name, self._ha_name))

    def update_state(self, session: pcomfortcloud.Session):
        """
        Update device state from the cloud

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
        print("Reading data for {}/{} ({})".format(self._name, self._ha_name, self._id))
        data = session.get_device(self._id)
        if data["id"] != self._id:
            print("Received incorrect device update. Ignoring the data.")
            return
        self._params = data["parameters"]
        self._target_temp = self._params["temperature"]
        if self._params["power"] == constants.Power.Off:
            self._mode = "off"
        else:
            self._mode = mappings.modes_to_string.get(self._params["mode"])
            if not self._mode:
                print("Problem when mapping mode - " + str(self._params["mode"]))

    def get_model(self) -> str:
        return self._model

    def get_name(self) -> str:
        return self._name

    def get_mode(self) -> str:
        return self._mode

    def get_component(self) -> str:
        return "climate"

    def get_id(self) -> str:
        return self._ha_name

    def get_internal_id(self) -> str:
        return self._id

    def get_target_temperature(self) -> float:
        return self._target_temp

    def get_temperature(self) -> float:
        return self._params["temperatureInside"]
    
    def get_temperature_outside(self) -> float:
        return self._params["temperatureOutside"]

    def command(self, client: mqtt.Client, session: pcomfortcloud.Session, command: str, payload: str):
        """
        Resolve command coming from HomeAssistant / MQTT
        """
        if command == "mode_cmd":
            literal = mappings.modes_to_literal.get(payload)
            if literal:
                session.set_device(self._id, mode=literal, power=constants.Power.On)
            elif payload == "off":
                session.set_device(self._id, power=constants.Power.Off)
            else:
                print("Unknown mode command: " + payload)
                return
            self._mode = "off"
            topic, mqtt_payload = state_event(self._topic_prefix, self)
            client.publish(topic, mqtt_payload)
        elif command == "temp_cmd":
            value = float(payload)
            session.set_device(self._id, temperature=value)
            self._target_temp = value
            topic, mqtt_payload = state_event(self._topic_prefix, self)
            client.publish(topic, mqtt_payload)
        elif command in ["config", "state"]:
            pass
        else:
            print("Unknown command: " + command)
            return