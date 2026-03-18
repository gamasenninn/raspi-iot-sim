"""ユニットテスト: ソフトウェアセンサーのシミュレーションロジック"""
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from devices.sensors import (
    DHT22Temp, DHT22Humidity, BMP280Pressure,
    LightLevel, DistanceUltrasonic, SoilMoisture,
)


class TestDHT22Temperature:
    def test_initial_value_near_22(self):
        s = DHT22Temp()
        assert abs(s.value - 22.0) < 0.01

    def test_update_changes_value(self):
        s = DHT22Temp()
        initial = s.value
        # 100回更新すれば少なくとも1回は変化するはず
        changed = False
        for _ in range(100):
            s.update()
            if abs(s.value - initial) > 0.01:
                changed = True
                break
        assert changed

    def test_stays_in_range(self):
        s = DHT22Temp()
        for _ in range(1000):
            s.update()
        assert -10 <= s.value <= 50


class TestDHT22Humidity:
    def test_initial_value_near_55(self):
        s = DHT22Humidity()
        assert abs(s.value - 55.0) < 0.01

    def test_stays_in_range(self):
        s = DHT22Humidity()
        for _ in range(1000):
            s.update()
        assert 0 <= s.value <= 100


class TestBMP280Pressure:
    def test_initial_value_near_1013(self):
        s = BMP280Pressure()
        assert abs(s.value - 1013.25) < 1.0

    def test_oscillates_around_1013(self):
        s = BMP280Pressure()
        values = []
        for _ in range(100):
            s.update()
            values.append(s.value)
        mean = sum(values) / len(values)
        assert abs(mean - 1013.25) < 10.0


class TestLightLevel:
    def test_value_nonnegative(self):
        s = LightLevel()
        for _ in range(500):
            s.update()
            assert s.value >= 0


class TestDistanceUltrasonic:
    def test_stays_in_range(self):
        s = DistanceUltrasonic()
        for _ in range(500):
            s.update()
            assert 0 <= s.value <= 450  # マージン含む


class TestSoilMoisture:
    def test_auto_rewater(self):
        """30%以下になったら自動的に80%付近に回復する"""
        s = SoilMoisture()
        s.value = 25.0  # 強制的に低くする
        s.update()
        assert s.value > 70.0, "自動水やりで回復するはず"

    def test_gradual_decrease(self):
        """値は徐々に減少する"""
        s = SoilMoisture()
        s.value = 70.0
        initial = s.value
        for _ in range(50):
            s.update()
        assert s.value < initial


class TestSensorRegistry:
    def test_sensor_get_state_has_value_and_unit(self, registry):
        sensor_names = [
            "dht22_temperature", "dht22_humidity", "bmp280_pressure",
            "bh1750_light", "hcsr04_distance", "soil_moisture",
        ]
        for name in sensor_names:
            state = registry[name]["get_state"]()
            assert "value" in state, f"{name} の state に value がない"
            assert "unit" in state, f"{name} の state に unit がない"
            assert isinstance(state["value"], float), f"{name} の value が float でない"

    def test_sensor_set_value(self, registry):
        """センサーの値を手動設定できる"""
        temp = registry["dht22_temperature"]
        temp["actions"]["set"]("30.0")
        assert abs(temp["get_state"]()["value"] - 30.0) < 0.01
