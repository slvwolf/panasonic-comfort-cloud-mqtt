"""
MQTT events.
"""
import json
import typing


def discovery_topic(topic_prefix: str, component: str, device_id: str) -> str:
    """
    Create discovery topic based on device, follows definition from Home Assistant:
    <topic_prefix>/<component>/<device_id>/config

    Details: https://www.home-assistant.io/docs/mqtt/discovery/
    """
    return "{}/{}/{}/config".format(topic_prefix, component, device_id)


def _create_discovery_temperature_sensor_tuple(topic_prefix: str, base_topic_path: str, sensor_name: str, device) -> typing.Tuple[str, str]:
    """
    Creates tuple containing the topic and json payload to register new temperature sensor.
    """
    unique_name = device.get_name() + "_temperature_" + sensor_name
    return (
        discovery_topic(topic_prefix, "sensor",
                        device.get_id() + "_temperature_" + sensor_name),
        json.dumps({
            "name": unique_name,
            "unique_id": unique_name,
            "device_class": "sensor",
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "icon": "mdi:thermometer",
            "state_topic": "{}/state".format(base_topic_path),
            "value_template": "{{ value_json." + sensor_name + "_temperature }}",
            "device": {
                "model": device.get_model(),
                "manufacturer": "Panasonic",
                "identifiers": device.get_internal_id() + "_tmp_" + sensor_name,
            }}))


def discovery_event(topic_prefix: str, device) -> typing.List[typing.Tuple[str, str]]:
    """
    Create list of discovery events. Tuple consists of (discovery topic, event payload) 
    """
    base_topic_path = "{}/{}/{}".format(topic_prefix,
                                        device.get_component(), device.get_id())
    topics = [
        (discovery_topic(topic_prefix, "climate", device.get_id()),
         json.dumps({
             "name": device.get_name(),
             "unique_id": device.get_name(),
             "device_class": "climate",
             "state_topic": "{}/state".format(base_topic_path),
             "icon": "mdi:air-conditioner",
             "temperature_unit": "C",
             "mode_command_topic": "{}/mode_cmd".format(base_topic_path),
             "mode_state_topic": "{}/state".format(base_topic_path),
             "mode_state_template": "{{ value_json.mode }}",
             "temperature_command_topic": "{}/temp_cmd".format(base_topic_path),
             "temperature_state_topic": "{}/state".format(base_topic_path),
             "temperature_state_template": "{{ value_json.target_temperature }}",
             "power_command_topic": "{}/power_cmd".format(base_topic_path),
             "device": {
                 "model": device.get_model(),
                 "manufacturer": "Panasonic",
                 "identifiers": device.get_internal_id(),
             }})),
        _create_discovery_temperature_sensor_tuple(
            topic_prefix, base_topic_path, "outside", device),
        _create_discovery_temperature_sensor_tuple(
            topic_prefix, base_topic_path, "inside", device),
    ]
    return topics


def state_event(topic_prefix: str, device) -> typing.Tuple[str, str]:
    topic = "{}/{}/{}/state".format(topic_prefix,
                                    device.get_component(), device.get_id())
    payload = {
        "mode": device.get_mode_str(),
        "power": device.get_power_str(),
        "target_temperature": device.get_target_temperature(),
        "inside_temperature": device.get_temperature(),
        "outside_temperature": device.get_temperature_outside(),
    }
    return (topic, json.dumps(payload))
