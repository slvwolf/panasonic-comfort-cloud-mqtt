from pcomfortcloud import constants # type: ignore

modes_to_literal = {
    "fan_only": constants.OperationMode.Fan,
    "heat": constants.OperationMode.Heat,
    "cool": constants.OperationMode.Cool,
    "dry": constants.OperationMode.Dry,
    "auto": constants.OperationMode.Auto,
}

power_to_literal = {
    "on": constants.Power.On,
    "off": constants.Power.Off,
}

modes_to_string = {b: a for a, b in modes_to_literal.items()}
power_to_string = {b: a for a, b in power_to_literal.items()}
