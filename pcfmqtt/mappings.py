from pcomfortcloud import constants

modes_to_literal = {
    "fan_only": constants.OperationMode.Fan,
    "heat": constants.OperationMode.Heat,
    "cool": constants.OperationMode.Cool,
    "dry": constants.OperationMode.Dry,
    "auto": constants.OperationMode.Auto,
}

modes_to_string = {b: a for a, b in modes_to_literal.items()}
