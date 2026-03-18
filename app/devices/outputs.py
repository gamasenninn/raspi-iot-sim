"""出力デバイス: LED, Buzzer, Servo, Motor"""
from gpiozero import LED, PWMLED, RGBLED, Buzzer, Servo, Motor
from config.pin_map import (
    LED_RED, LED_PWM, RGBLED_RED, RGBLED_GREEN, RGBLED_BLUE,
    BUZZER, SERVO, MOTOR_FWD, MOTOR_BWD,
)


def create_output_devices():
    """出力デバイスを生成して辞書で返す"""
    devices = {}

    # LED (デジタル)
    led = LED(LED_RED)
    devices["led_red"] = {
        "device": led,
        "type": "output",
        "category": "LED",
        "get_state": lambda d=led: {"on": d.is_lit},
        "actions": {
            "on": lambda d=led: d.on(),
            "off": lambda d=led: d.off(),
            "toggle": lambda d=led: d.toggle(),
        },
    }

    # PWM LED (調光)
    pwm_led = PWMLED(LED_PWM)
    devices["led_pwm"] = {
        "device": pwm_led,
        "type": "output",
        "category": "LED",
        "get_state": lambda d=pwm_led: {"value": round(d.value, 3)},
        "actions": {
            "on": lambda d=pwm_led: d.on(),
            "off": lambda d=pwm_led: d.off(),
            "set": lambda v, d=pwm_led: setattr(d, "value", float(v)),
            "pulse": lambda d=pwm_led: d.pulse(),
        },
    }

    # RGB LED
    rgb = RGBLED(RGBLED_RED, RGBLED_GREEN, RGBLED_BLUE)
    devices["led_rgb"] = {
        "device": rgb,
        "type": "output",
        "category": "LED",
        "get_state": lambda d=rgb: {
            "color": [round(c, 3) for c in d.value],
        },
        "actions": {
            "on": lambda d=rgb: d.on(),
            "off": lambda d=rgb: d.off(),
            "set": lambda v, d=rgb: setattr(d, "color", tuple(float(x) for x in v.split(","))),
        },
    }

    # ブザー
    buzzer = Buzzer(BUZZER)
    devices["buzzer"] = {
        "device": buzzer,
        "type": "output",
        "category": "Buzzer",
        "get_state": lambda d=buzzer: {"on": d.is_active},
        "actions": {
            "on": lambda d=buzzer: d.on(),
            "off": lambda d=buzzer: d.off(),
            "beep": lambda d=buzzer: d.beep(),
        },
    }

    # サーボモーター
    servo = Servo(SERVO)
    devices["servo"] = {
        "device": servo,
        "type": "output",
        "category": "Servo",
        "get_state": lambda d=servo: {"value": d.value},
        "actions": {
            "min": lambda d=servo: d.min(),
            "mid": lambda d=servo: d.mid(),
            "max": lambda d=servo: d.max(),
            "set": lambda v, d=servo: setattr(d, "value", float(v)),
        },
    }

    # DCモーター
    motor = Motor(MOTOR_FWD, MOTOR_BWD)
    devices["motor"] = {
        "device": motor,
        "type": "output",
        "category": "Motor",
        "get_state": lambda d=motor: {"speed": round(d.value, 3)},
        "actions": {
            "forward": lambda d=motor: d.forward(),
            "backward": lambda d=motor: d.backward(),
            "stop": lambda d=motor: d.stop(),
            "set": lambda v, d=motor: d.forward(float(v)) if float(v) >= 0 else d.backward(abs(float(v))),
        },
    }

    return devices
