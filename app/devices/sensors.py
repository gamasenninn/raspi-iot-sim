"""ソフトウェアシミュレーションセンサー

I2C/SPI接続のセンサーはGPIOピンを使わないため、
ソフトウェアで値を生成してMQTTで配信する。
"""
import random
import time
import math


class SimulatedSensor:
    """シミュレーションセンサーの基底クラス"""

    def __init__(self, name, unit):
        self.name = name
        self.unit = unit
        self._value = 0.0
        self._start_time = time.time()

    @property
    def value(self):
        return round(self._value, 2)

    @value.setter
    def value(self, v):
        self._value = v

    def update(self):
        """サブクラスでオーバーライド"""
        raise NotImplementedError


class DHT22Temp(SimulatedSensor):
    """温度センサー (DHT22) - ランダムウォーク"""

    def __init__(self):
        super().__init__("dht22_temperature", "°C")
        self._value = 22.0

    def update(self):
        self._value += random.gauss(0, 0.3)
        self._value = max(-10, min(50, self._value))


class DHT22Humidity(SimulatedSensor):
    """湿度センサー (DHT22) - ランダムウォーク"""

    def __init__(self):
        super().__init__("dht22_humidity", "%")
        self._value = 55.0

    def update(self):
        self._value += random.gauss(0, 1.0)
        self._value = max(0, min(100, self._value))


class BMP280Pressure(SimulatedSensor):
    """気圧センサー (BMP280) - サイン波 + ノイズ"""

    def __init__(self):
        super().__init__("bmp280_pressure", "hPa")
        self._value = 1013.25

    def update(self):
        elapsed = time.time() - self._start_time
        self._value = 1013.25 + 5.0 * math.sin(elapsed / 300) + random.gauss(0, 0.5)


class LightLevel(SimulatedSensor):
    """照度センサー (BH1750) - 時刻ベース"""

    def __init__(self):
        super().__init__("bh1750_light", "lux")
        self._value = 300.0

    def update(self):
        elapsed = time.time() - self._start_time
        # 昼夜サイクルをシミュレーション (600秒周期)
        base = 500 + 400 * math.sin(elapsed / 100)
        self._value = max(0, base + random.gauss(0, 20))


class DistanceUltrasonic(SimulatedSensor):
    """超音波距離センサー (HC-SR04) - のこぎり波"""

    def __init__(self):
        super().__init__("hcsr04_distance", "cm")
        self._value = 100.0

    def update(self):
        elapsed = time.time() - self._start_time
        # 2〜400cm の範囲でのこぎり波
        self._value = 2 + (elapsed % 60) / 60 * 398
        self._value += random.gauss(0, 2)
        self._value = max(2, min(400, self._value))


class SoilMoisture(SimulatedSensor):
    """土壌水分センサー - ゆっくり減少 + 時々水やり"""

    def __init__(self):
        super().__init__("soil_moisture", "%")
        self._value = 70.0
        self._last_water = time.time()

    def update(self):
        # 徐々に乾燥
        self._value -= random.uniform(0.01, 0.1)
        # 30%以下になったら水やり
        if self._value < 30:
            self._value = 80.0 + random.gauss(0, 5)
            self._last_water = time.time()
        self._value = max(0, min(100, self._value))


def create_software_sensors():
    """全ソフトウェアセンサーを生成して辞書で返す"""
    sensor_classes = [
        DHT22Temp, DHT22Humidity, BMP280Pressure,
        LightLevel, DistanceUltrasonic, SoilMoisture,
    ]

    devices = {}
    for cls in sensor_classes:
        sensor = cls()
        devices[sensor.name] = {
            "device": sensor,
            "type": "sensor",
            "category": "Sensor",
            "get_state": lambda s=sensor: {"value": s.value, "unit": s.unit},
            "actions": {
                "set": lambda v, s=sensor: setattr(s, "value", float(v)),
            },
        }

    return devices
