"""入力デバイス: Button, MotionSensor, LineSensor"""
from gpiozero import Button, MotionSensor, LineSensor
from config.pin_map import BUTTON, MOTION_SENSOR, LINE_SENSOR


def create_input_devices():
    """入力デバイスを生成して辞書で返す"""
    devices = {}

    # ボタン
    btn = Button(BUTTON, pull_up=True)
    devices["button"] = {
        "device": btn,
        "type": "input",
        "category": "Button",
        "get_state": lambda d=btn: {"pressed": d.is_pressed},
        "actions": {
            # MockFactory経由でシミュレーション
            "press": lambda d=btn: d.pin.drive_low(),
            "release": lambda d=btn: d.pin.drive_high(),
        },
    }

    # モーションセンサー (PIR)
    motion = MotionSensor(MOTION_SENSOR)
    devices["motion_sensor"] = {
        "device": motion,
        "type": "input",
        "category": "MotionSensor",
        "get_state": lambda d=motion: {"motion_detected": d.is_active},
        "actions": {
            "trigger": lambda d=motion: d.pin.drive_high(),
            "clear": lambda d=motion: d.pin.drive_low(),
        },
    }

    # ラインセンサー
    line = LineSensor(LINE_SENSOR)
    devices["line_sensor"] = {
        "device": line,
        "type": "input",
        "category": "LineSensor",
        "get_state": lambda d=line: {"line_detected": d.is_active},
        "actions": {
            "detect": lambda d=line: d.pin.drive_high(),
            "clear": lambda d=line: d.pin.drive_low(),
        },
    }

    return devices
