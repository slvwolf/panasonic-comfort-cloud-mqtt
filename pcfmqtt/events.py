"""
MQTT events.
"""
import json
import typing

def discovery_topic(topic_prefix: str, device) -> str:
    """
    Create discovery topic based on device, follows definition from Home Assistant:
    <discovery_prefix>/<component>/[<node_id>/]<object_id>/config

    Details: https://www.home-assistant.io/docs/mqtt/discovery/
    """
    return "{}/{}/{}/config".format(topic_prefix, device.get_component(), device.get_id())

def discovery_event(topic_prefix: str, device) -> typing.List[typing.Tuple[str, str]]:
    """
    Create list of discovery events. Tuple consists of (discovery topic, event payload) 
    """
    topics = []
    base_topic_path = "{}/{}/{}".format(topic_prefix, device.get_component(), device.get_id())
    data = {
        "name": device.get_name(),
        "unique_id": device.get_id(),
        "device_class": device.get_component(),
        "state_topic": "{}/state".format(base_topic_path),        
        "mode_command_topic": "{}/mode_cmd".format(base_topic_path),
        "mode_state_topic": "{}/state".format(base_topic_path),
        "mode_state_template": "{{ value_json.mode }}",
        "temperature_command_topic": "{}/temp_cmd".format(base_topic_path),
        "temperature_state_topic": "{}/state".format(base_topic_path),
        "temperature_state_template": "{{ value_json.target_temperature }}",
        "device": {
            "model": device.get_model(),
            "manufacturer": "Panasonic",
            "identifiers": device.get_internal_id(),
        }
    }
    topics.append((discovery_topic(topic_prefix, device), json.dumps(data)))
    return topics

def state_event(topic_prefix: str, device) -> typing.Tuple[str, str]:
    topic = "{}/{}/{}/state".format(topic_prefix, device.get_component(), device.get_id())
    payload = {
        "mode": device.get_mode(),
        "target_temperature": device.get_target_temperature(),
        "current_temperature": device.get_temperature(),
    }
    return (topic, json.dumps(payload))
