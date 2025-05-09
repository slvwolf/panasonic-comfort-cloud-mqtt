""" Mapping of modes and power states between pcomfortcloud and pcfmqtt. """
from pcomfortcloud import constants

modes_to_literal = {
    "fan_only": constants.OperationMode.Fan,
    "heat": constants.OperationMode.Heat,
    "cool": constants.OperationMode.Cool,
    "dry": constants.OperationMode.Dry,
    "auto": constants.OperationMode.Auto,
}

# Some modes are in upper case due to missing mapping in Home Assistant
# This will just make the title look better in the UI
fans_to_literal = {
    "auto": constants.FanSpeed.Auto,
    "high": constants.FanSpeed.High,
    "Medium high": constants.FanSpeed.HighMid,
    "medium": constants.FanSpeed.Mid,
    "Medium low": constants.FanSpeed.LowMid,
    "low": constants.FanSpeed.Low,
}

# Some modes are in upper case due to missing mapping in Home Assistant
# This will just make the title look better in the UI
airswing_to_literal = {
    "on": constants.AirSwingUD.Auto,
    "Up": constants.AirSwingUD.Up,
    "Mid-up": constants.AirSwingUD.UpMid,
    "Middle": constants.AirSwingUD.Mid,
    "Mid-down": constants.AirSwingUD.DownMid,
    "All down": constants.AirSwingUD.Down,
}

# Some modes are in upper case due to missing mapping in Home Assistant
# This will just make the title look better in the UI
airswing_horizontal_to_literal = {
    "on": constants.AirSwingLR.Auto,
    "Left": constants.AirSwingLR.Left,
    "Mid-left": constants.AirSwingLR.LeftMid,
    "Middle": constants.AirSwingLR.Mid,
    "Mid-right": constants.AirSwingLR.RightMid,
    "Right": constants.AirSwingLR.Right,
}

eco_to_literal = {
    "Auto": constants.EcoMode.Auto,
    "Powerful": constants.EcoMode.Powerful,
    "Quiet": constants.EcoMode.Quiet,
}

nanoe_to_literal = {
    "On": constants.NanoeMode.On,
    "Off": constants.NanoeMode.Off,
    "All": constants.NanoeMode.All,
    "ModeG": constants.NanoeMode.ModeG,
    "offline": constants.NanoeMode.Unavailable,
}

power_to_literal = {
    "on": constants.Power.On,
    "off": constants.Power.Off,
}

modes_to_string = {b: a for a, b in modes_to_literal.items()}
power_to_string = {b: a for a, b in power_to_literal.items()}
fans_to_string = {b: a for a, b in fans_to_literal.items()}
airswing_horizontal_to_string = {b: a for a, b in airswing_horizontal_to_literal.items()}
airswing_to_string = {b: a for a, b in airswing_to_literal.items()}
eco_to_string = {b: a for a, b in eco_to_literal.items()}
nanoe_to_string = {b: a for a, b in nanoe_to_literal.items()}
