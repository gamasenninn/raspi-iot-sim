"""MQTT エコシステム — 複数の仮想IoTノードがMQTT経由で協調動作

3つの仮想ノードを1プロセス内のスレッドでシミュレーション:
  - [WeatherStation] 気象データを定期配信
  - [GardenController] 気象データを受信し、灌漑・日除けを制御
  - [SecuritySystem] 距離・モーションで侵入検知、全ノードに警報配信
"""
import os, sys, time, json, threading
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, LED, Motor, Buzzer, Servo
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt
from devices.sensors import (
    DHT22Temp, DHT22Humidity, BMP280Pressure,
    LightLevel, SoilMoisture, DistanceUltrasonic
)

Device.pin_factory = MockFactory(pin_class=MockPWMPin)


def make_client(name):
    c = mqtt.Client(client_id=name)
    c.connect("mosquitto", 1883, 60)
    c.loop_start()
    return c


class WeatherStation(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.client = make_client("weather-station")
        self.temp = DHT22Temp()
        self.humidity = DHT22Humidity()
        self.pressure = BMP280Pressure()
        self.light = LightLevel()

    def run(self):
        for i in range(15):
            self.temp.update()
            self.humidity.update()
            self.pressure.update()
            self.light.update()

            data = {
                "node": "WeatherStation",
                "temp": self.temp.value,
                "humidity": self.humidity.value,
                "pressure": self.pressure.value,
                "light": self.light.value,
                "cycle": i + 1,
            }
            self.client.publish("iot/weather/data", json.dumps(data))
            t = self.temp.value
            h = self.humidity.value
            p = self.pressure.value
            lx = self.light.value
            print(f"  [Weather] #{i+1:2d} T:{t:5.1f}C H:{h:5.1f}% P:{p:7.1f}hPa L:{lx:6.1f}lux")
            time.sleep(0.5)
        self.client.loop_stop()


class GardenController(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.client = make_client("garden-controller")
        self.pump = Motor(5, 6)
        self.shade = Servo(13)
        self.soil = SoilMoisture()
        self.irrigating = False
        self.shade_deployed = False
        self.alert_mode = False

        self.client.on_message = self.on_message
        self.client.subscribe("iot/weather/data")
        self.client.subscribe("iot/security/alert")
        self.last_weather = {}

    def on_message(self, client, userdata, msg):
        data = json.loads(msg.payload.decode())
        if msg.topic == "iot/weather/data":
            self.last_weather = data
        elif msg.topic == "iot/security/alert":
            self.alert_mode = data.get("alert", False)
            if self.alert_mode:
                print("  [Garden] !!! Alert received -> pump OFF !!!")
                self.pump.stop()
                self.irrigating = False

    def run(self):
        time.sleep(0.3)
        for i in range(15):
            self.soil.update()

            if self.alert_mode:
                print(f"  [Garden] #{i+1:2d} ALERT MODE - all stopped")
                time.sleep(0.5)
                continue

            actions = []

            if self.soil.value < 35 and not self.irrigating:
                self.pump.forward(0.7)
                self.irrigating = True
                self.soil.value = 75.0
                actions.append("irrigate-ON")
            elif self.soil.value > 65 and self.irrigating:
                self.pump.stop()
                self.irrigating = False
                actions.append("irrigate-OFF")

            lx = self.last_weather.get("light", 500)
            if lx > 700 and not self.shade_deployed:
                self.shade.max()
                self.shade_deployed = True
                actions.append("shade-OPEN")
            elif lx < 300 and self.shade_deployed:
                self.shade.min()
                self.shade_deployed = False
                actions.append("shade-CLOSE")

            if not actions:
                actions.append("hold")

            act_str = "|".join(actions)
            pump_s = "ON" if self.irrigating else "OFF"
            shade_s = "OPEN" if self.shade_deployed else "CLOSED"
            print(f"  [Garden] #{i+1:2d} soil:{self.soil.value:5.1f}% pump:{pump_s} shade:{shade_s} -> {act_str}")

            status = {
                "node": "GardenController",
                "soil": self.soil.value,
                "irrigating": self.irrigating,
                "shade": self.shade_deployed,
                "actions": actions,
            }
            self.client.publish("iot/garden/status", json.dumps(status))
            time.sleep(0.5)
        self.client.loop_stop()


class SecuritySystem(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.client = make_client("security-system")
        self.alarm = Buzzer(25)
        self.warn_led = LED(17)
        self.distance = DistanceUltrasonic()
        self.alert_count = 0

    def run(self):
        for i in range(15):
            self.distance.update()
            d = self.distance.value

            intruder = d < 40

            if intruder:
                self.alarm.on()
                self.warn_led.on()
                self.alert_count += 1

                alert = {
                    "node": "SecuritySystem",
                    "alert": True,
                    "distance": d,
                    "alert_count": self.alert_count,
                }
                self.client.publish("iot/security/alert", json.dumps(alert))
                print(f"  [Security] #{i+1:2d} *** INTRUDER! D:{d:6.1f}cm count:{self.alert_count} ***")
            else:
                if self.alarm.is_active:
                    self.alarm.off()
                    self.warn_led.off()
                    alert = {"node": "SecuritySystem", "alert": False}
                    self.client.publish("iot/security/alert", json.dumps(alert))
                    print(f"  [Security] #{i+1:2d} Alert cleared D:{d:6.1f}cm")
                else:
                    print(f"  [Security] #{i+1:2d} Safe D:{d:6.1f}cm")

            time.sleep(0.5)
        self.client.loop_stop()


print("=" * 65)
print("  IoT Ecosystem - 3-Node Cooperative Demo")
print("=" * 65)
print("  [Weather]  -> publish weather data")
print("  [Garden]   <- receive weather -> control irrigation/shade")
print("  [Security] -> intrusion detect -> alert all nodes")
print("-" * 65)

weather = WeatherStation()
garden = GardenController()
security = SecuritySystem()

weather.start()
garden.start()
security.start()

weather.join()
garden.join()
security.join()

print()
print("=" * 65)
print(f"  Done! Total alerts: {security.alert_count}")
print("=" * 65)
