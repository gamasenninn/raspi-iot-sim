"""ユニットテスト: デバイス生成と状態管理"""
import time
import pytest


class TestDeviceCreation:
    def test_registry_has_15_devices(self, registry):
        assert len(registry) == 15

    def test_output_devices_exist(self, registry):
        outputs = ["led_red", "led_pwm", "led_rgb", "buzzer", "servo", "motor"]
        for name in outputs:
            assert name in registry, f"{name} がレジストリにない"
            assert registry[name]["type"] == "output"

    def test_input_devices_exist(self, registry):
        inputs = ["button", "motion_sensor", "line_sensor"]
        for name in inputs:
            assert name in registry, f"{name} がレジストリにない"
            assert registry[name]["type"] == "input"

    def test_sensor_devices_exist(self, registry):
        sensors = [
            "dht22_temperature", "dht22_humidity", "bmp280_pressure",
            "bh1750_light", "hcsr04_distance", "soil_moisture",
        ]
        for name in sensors:
            assert name in registry, f"{name} がレジストリにない"
            assert registry[name]["type"] == "sensor"

    def test_all_devices_have_get_state(self, registry):
        for name, info in registry.items():
            assert callable(info["get_state"]), f"{name} に get_state がない"

    def test_all_devices_have_actions(self, registry):
        for name, info in registry.items():
            assert "actions" in info, f"{name} に actions がない"
            assert len(info["actions"]) > 0, f"{name} の actions が空"


class TestLED:
    def test_led_on_off(self, registry):
        led = registry["led_red"]
        led["actions"]["on"]()
        assert led["get_state"]()["on"] is True

        led["actions"]["off"]()
        assert led["get_state"]()["on"] is False

    def test_led_toggle(self, registry):
        led = registry["led_red"]
        led["actions"]["off"]()
        led["actions"]["toggle"]()
        assert led["get_state"]()["on"] is True
        led["actions"]["toggle"]()
        assert led["get_state"]()["on"] is False

    def test_pwm_led_set_value(self, registry):
        pwm = registry["led_pwm"]
        pwm["actions"]["set"]("0.5")
        state = pwm["get_state"]()
        assert abs(state["value"] - 0.5) < 0.01

    def test_pwm_led_boundaries(self, registry):
        pwm = registry["led_pwm"]
        pwm["actions"]["set"]("0.0")
        assert pwm["get_state"]()["value"] == 0.0
        pwm["actions"]["set"]("1.0")
        assert abs(pwm["get_state"]()["value"] - 1.0) < 0.01

    def test_rgb_led_set_color(self, registry):
        rgb = registry["led_rgb"]
        rgb["actions"]["set"]("1.0,0.0,0.5")
        color = rgb["get_state"]()["color"]
        assert abs(color[0] - 1.0) < 0.01
        assert abs(color[1] - 0.0) < 0.01
        assert abs(color[2] - 0.5) < 0.01


class TestServoMotor:
    def test_servo_min_mid_max(self, registry):
        servo = registry["servo"]
        servo["actions"]["min"]()
        assert servo["get_state"]()["value"] == -1.0
        servo["actions"]["mid"]()
        assert servo["get_state"]()["value"] == 0.0
        servo["actions"]["max"]()
        assert servo["get_state"]()["value"] == 1.0

    def test_servo_set_value(self, registry):
        servo = registry["servo"]
        servo["actions"]["set"]("0.75")
        assert abs(servo["get_state"]()["value"] - 0.75) < 0.01

    def test_motor_forward(self, registry):
        motor = registry["motor"]
        motor["actions"]["forward"]()
        assert motor["get_state"]()["speed"] > 0

    def test_motor_backward(self, registry):
        motor = registry["motor"]
        motor["actions"]["backward"]()
        assert motor["get_state"]()["speed"] < 0

    def test_motor_stop(self, registry):
        motor = registry["motor"]
        motor["actions"]["forward"]()
        motor["actions"]["stop"]()
        assert motor["get_state"]()["speed"] == 0.0


class TestInputDevices:
    def test_button_press_release(self, registry):
        btn = registry["button"]
        btn["actions"]["press"]()
        assert btn["get_state"]()["pressed"] is True
        btn["actions"]["release"]()
        assert btn["get_state"]()["pressed"] is False

    def test_motion_sensor_trigger_clear(self, registry):
        ms = registry["motion_sensor"]
        ms["actions"]["trigger"]()
        time.sleep(0.1)
        assert ms["get_state"]()["motion_detected"] is True
        ms["actions"]["clear"]()
        time.sleep(0.5)  # SmoothedInputDevice のデバウンス待ち
        assert ms["get_state"]()["motion_detected"] is False

    def test_line_sensor_detect_clear(self, registry):
        ls = registry["line_sensor"]
        ls["actions"]["detect"]()
        time.sleep(0.1)
        assert ls["get_state"]()["line_detected"] is True
        ls["actions"]["clear"]()
        time.sleep(0.5)  # SmoothedInputDevice のデバウンス待ち
        assert ls["get_state"]()["line_detected"] is False


class TestBuzzer:
    def test_buzzer_on_off(self, registry):
        bz = registry["buzzer"]
        bz["actions"]["on"]()
        assert bz["get_state"]()["on"] is True
        bz["actions"]["off"]()
        assert bz["get_state"]()["on"] is False
