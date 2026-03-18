"""スマート農業デモ
- 土壌水分が低下 → モーターで自動灌漑(ポンプ)
- 距離センサーで近接 → ブザー警報 + MQTT通知
- 全データをMQTTで配信
"""
import os, sys, time, json
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, Motor, Buzzer, LED
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt
from devices.sensors import (
    SoilMoisture, DistanceUltrasonic, DHT22Temp, DHT22Humidity
)

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# デバイス
pump = Motor(5, 6)        # 灌漑ポンプ
alarm = Buzzer(25)        # 侵入警報
status_led = LED(17)      # 稼働中LED

# センサー
soil = SoilMoisture()
distance = DistanceUltrasonic()
temp = DHT22Temp()
humidity = DHT22Humidity()

# MQTT
client = mqtt.Client(client_id="smart-farm")
client.connect("mosquitto", 1883, 60)
client.loop_start()

# しきい値
SOIL_DRY = 40.0      # %以下で灌漑開始
SOIL_WET = 70.0      # %以上で灌漑停止
INTRUDER_DIST = 50.0 # cm以下で侵入検知

print("=" * 60)
print("  スマート農業シミュレーション (20サイクル)")
print(f"  灌漑: 土壌水分 < {SOIL_DRY}% で開始, > {SOIL_WET}% で停止")
print(f"  警報: 距離 < {INTRUDER_DIST}cm で侵入検知")
print("=" * 60)

status_led.on()
irrigating = False

for i in range(20):
    # センサー更新
    soil.update()
    distance.update()
    temp.update()
    humidity.update()

    # --- 灌漑制御 ---
    if soil.value < SOIL_DRY and not irrigating:
        pump.forward(0.8)
        irrigating = True
        print(f"  >>> 灌漑開始! (土壌水分: {soil.value}%)")
        # 水やりシミュレーション: 水分を急上昇
        soil.value = 75.0
    elif soil.value > SOIL_WET and irrigating:
        pump.stop()
        irrigating = False
        print(f"  <<< 灌漑停止 (土壌水分: {soil.value}%)")

    # --- 侵入検知 ---
    intruder = distance.value < INTRUDER_DIST
    if intruder:
        alarm.on()
    else:
        alarm.off()

    # 表示
    pump_status = "稼働" if irrigating else "停止"
    alarm_status = "検知!" if intruder else "安全"
    print(f"[{i+1:2d}/20] "
          f"土壌:{soil.value:5.1f}% "
          f"距離:{distance.value:6.1f}cm "
          f"温度:{temp.value:5.1f}°C "
          f"湿度:{humidity.value:5.1f}% "
          f"| ポンプ:{pump_status} 警報:{alarm_status}")

    # MQTT配信
    data = {
        "cycle": i + 1,
        "soil_moisture": soil.value,
        "distance": distance.value,
        "temperature": temp.value,
        "humidity": humidity.value,
        "pump_active": irrigating,
        "intruder_detected": intruder,
    }
    client.publish("iot/demo/smart_farm", json.dumps(data))

    time.sleep(0.3)

# クリーンアップ
pump.stop()
alarm.off()
status_led.off()
client.loop_stop()
client.disconnect()
print("\nシミュレーション完了!")
