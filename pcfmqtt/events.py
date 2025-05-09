"""
MQTT events.
"""
import json
import typing

from pcfmqtt.mappings import fans_to_literal, airswing_to_literal, airswing_horizontal_to_literal, eco_to_literal, nanoe_to_literal
from pcfmqtt.device import Device


def discovery_topic(topic_prefix: str, component: str, device_id: str) -> str:
    """
    Create discovery topic based on device, follows definition from Home Assistant:
    <topic_prefix>/<component>/<device_id>/config

    Details: https://www.home-assistant.io/docs/mqtt/discovery/
    """
    return f"{topic_prefix}/{component}/{device_id}/config"

def _create_device_block(device: Device) -> typing.Dict[str, typing.Any]:
    """
    Creates shared device block for discovery payload.
    """
    return {
                 "model": device.get_model(),
                 "name": device.get_name(),
                 "manufacturer": "Panasonic",
                 "identifiers": [device.get_internal_id()],
    }

def _create_discovery_temperature_sensor_tuple(
        topic_prefix: str, base_topic_path: str, sensor_name: str,
        device: Device) -> typing.Tuple[str, str]:
    """
    Creates tuple containing the topic and json payload to register new temperature sensor.
    """
    return (
        discovery_topic(topic_prefix, "sensor",
                        device.get_id() + "_temperature_" + sensor_name),
        json.dumps({
            "name": "temperature_" + sensor_name,
            "unique_id": device.get_id() + "_temperature_" + sensor_name,
            "unit_of_measurement": "°C",
            "device_class": "temperature",
            "icon": "mdi:thermometer",
            "state_topic": f"{base_topic_path}/state",
            "value_template": "{{ value_json." + sensor_name + "_temperature }}",
            "device": _create_device_block(device),
            }))

def _create_discovery_alive_sensor_tuple(
        topic_prefix: str, base_topic_path: str, device: Device) -> typing.Tuple[str, str]:
    """
    Creates tuple containing the topic and json payload to register new alive sensor.
    """
    return (
        discovery_topic(topic_prefix, "sensor",
                        device.get_id() + "_alive"),
        json.dumps({
            "name": "Alive",
            "unique_id": device.get_id() + "_alive",
            "unit_of_measurement": "s",
            "device_class": "timestamp",
            "icon": "mdi:clock",
            "state_topic": f"{base_topic_path}/state",
            "value_template": "{{ value_json.update_epoch | int | timestamp_custom('%Y-%m-%dT%H:%M:%S%:z', true) }}",
            "device": _create_device_block(device),
            "expire_after": 300,
        }))

def _create_discovery_select_tuple(
        topic_prefix: str, base_topic_path: str, select_name: str, title: str,
        device: Device, options: typing.List[str], icon: str) -> typing.Tuple[str, str]:
    """
    Creates tuple containing the topic and json payload to register new select entity.
    """
    return (
        discovery_topic(topic_prefix, "select",
                        device.get_id() + "_" + select_name),
        json.dumps({
            "name": title,
            "unique_id":  device.get_id() + "select_" + select_name,
            "icon": icon,
            "state_topic": f"{base_topic_path}/state",
            "options": options,
            "command_topic": f"{base_topic_path}/s_{select_name}_cmd",
            "value_template": "{{ value_json.s_" + select_name + " }}",
            "device": _create_device_block(device),
            }))

def discovery_event(topic_prefix: str, device: Device) -> typing.List[typing.Tuple[str, str]]:
    """
    Create list of discovery events. Tuple consists of (discovery topic, event payload) 
    """ 
    base_topic_path = "{}/{}/{}".format(topic_prefix,
                                        device.get_component(), device.get_id())
    topics = [
        (discovery_topic(topic_prefix, "climate", device.get_id()),
         json.dumps({
             "name": "climate",             
             "unique_id": device.get_id() + "_climate",
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
             "fan_mode_command_topic": "{}/fan_cmd".format(base_topic_path),
             "fan_mode_state_topic": "{}/state".format(base_topic_path),
             "fan_mode_state_template": "{{ value_json.fan_mode }}",
             "fan_modes": list(fans_to_literal.keys()),
             "swing_mode_command_topic": "{}/swing_cmd".format(base_topic_path),
             "swing_mode_state_topic": "{}/state".format(base_topic_path),
             "swing_mode_state_template": "{{ value_json.swing_mode }}",
             "swing_modes": list(airswing_to_literal.keys()),
             "swing_horizontal_mode_command_topic": "{}/swing_h_cmd".format(base_topic_path),
             "swing_horizontal_mode_state_topic": "{}/state".format(base_topic_path),
             "swing_horizontal_mode_state_template": "{{ value_json.swing_horizontal }}",
             "swing_horizontal_modes": list(airswing_horizontal_to_literal.keys()),
             "power_command_topic": "{}/power_cmd".format(base_topic_path),
             "device": _create_device_block(device),
             })),
        _create_discovery_temperature_sensor_tuple(
            topic_prefix, base_topic_path, "outside", device),
        _create_discovery_temperature_sensor_tuple(
            topic_prefix, base_topic_path, "inside", device),
        # TODO: Figure out and fix the alive sensor
        #_create_discovery_alive_sensor_tuple(
        #    topic_prefix, base_topic_path, device),
        _create_discovery_select_tuple(
            topic_prefix, base_topic_path, "eco", "Eco mode", device,
            list(eco_to_literal.keys()), "mdi:leaf"),
        _create_discovery_select_tuple(
            topic_prefix, base_topic_path, "nanoe", "Nanoe mode", device,
            list(nanoe_to_literal.keys()), "mdi:air-filter"),
    ]
    return topics


def state_event(topic_prefix: str, device: Device) -> typing.Tuple[str, str]:
    topic = "{}/{}/{}/state".format(topic_prefix,
                                    device.get_component(), device.get_id())
    payload = {
        "mode": device.get_mode_str(),
        "power": device.get_power_str(),
        "fan_mode": device.get_fanmode_str(),
        "swing_mode": device.get_swingmode_str(),
        "swing_horizontal": device.get_swing_horizontal_str(),
        "target_temperature": device.get_target_temperature(),
        "inside_temperature": device.get_temperature(),
        "outside_temperature": device.get_temperature_outside(),
        "update_epoch": device.get_update_epoch(),
        "s_eco": device.get_eco_str(),
        "s_nanoe": device.get_nanoe_str(),
    }
    return (topic, json.dumps(payload))
