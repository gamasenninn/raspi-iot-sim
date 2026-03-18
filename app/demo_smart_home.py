"""スマートホーム自律制御

複数センサーの値に基づいて照明・空調・警報を自動制御する。
全てのデータは MQTT で配信し、REST API からも操作可能。

制御ルール:
  - 照度 < 200 lux → LED照明ON (明るさを照度に反比例)
  - 温度 > 26°C → ファン(モーター)ON、温度に比例した速度
  - 温度 < 18°C → LED赤で暖房警告
  - 湿度 > 85% → ブザーで除湿アラート
  - 距離 < 30cm → 人感検知 → 全照明ON
"""
import os, sys, time, json
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, LED, PWMLED, RGBLED, Motor, Buzzer
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt
from devices.sensors import (
    DHT22Temp, DHT22Humidity, LightLevel, DistanceUltrasonic
)

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# デバイス
room_light = PWMLED(18)       # メイン照明 (調光)
mood_light = RGBLED(22,23,24) # ムードライト
warn_led = LED(17)            # 警告LED
fan = Motor(5, 6)             # 換気ファン
alarm = Buzzer(25)            # アラーム

# センサー
temp = DHT22Temp()
humidity = DHT22Humidity()
light = LightLevel()
distance = DistanceUltrasonic()

# MQTT
client = mqtt.Client(client_id="smart-home")
client.connect("mosquitto", 1883, 60)
client.loop_start()

print("=" * 65)
print("  スマートホーム 自律制御システム (30サイクル)")
print("=" * 65)
print("  照明: 照度<200lux→ON | 空調: 温度>26°C→ファン")
print("  暖房: 温度<18°C→警告 | 除湿: 湿度>85%→アラーム")
print("  人感: 距離<30cm→全照明ON")
print("-" * 65)

for i in range(30):
    # センサー更新
    temp.update()
    humidity.update()
    light.update()
    distance.update()

    t = temp.value
    h = humidity.value
    lx = light.value
    d = distance.value

    actions = []

    # --- 照明制御 ---
    if d < 30:
        # 人感検知 → 全照明MAX
        room_light.value = 1.0
        mood_light.color = (1.0, 0.9, 0.7)  # 暖色
        actions.append("人感→全灯")
    elif lx < 200:
        # 暗い → 照度に反比例で点灯
        brightness = min(1.0, max(0.1, (200 - lx) / 200))
        room_light.value = brightness
        # ムードライトは青みがかった色
        mood_light.color = (0.1, 0.2, brightness * 0.8)
        actions.append(f"照明:{brightness:.0%}")
    else:
        room_light.off()
        mood_light.off()
        actions.append("照明:OFF")

    # --- 空調制御 ---
    if t > 26:
        speed = min(1.0, (t - 26) / 6)
        fan.forward(speed)
        actions.append(f"ファン:{speed:.0%}")
    elif t < 18:
        fan.stop()
        warn_led.on()
        actions.append("寒い!暖房警告")
    else:
        fan.stop()
        warn_led.off()
        actions.append("空調:OFF")

    # --- 除湿アラート ---
    if h > 85:
        alarm.on()
        actions.append("除湿アラーム!")
    else:
        alarm.off()

    # 表示
    status = " | ".join(actions)
    print(f"[{i+1:2d}] "
          f"T:{t:5.1f}°C H:{h:5.1f}% L:{lx:6.1f}lx D:{d:6.1f}cm "
          f"→ {status}")

    # MQTT配信
    data = {
        "cycle": i+1,
        "sensors": {"temp": t, "humidity": h, "light": lx, "distance": d},
        "actuators": {
            "room_light": round(room_light.value, 2),
            "mood_light": [round(c,2) for c in mood_light.value],
            "fan_speed": round(fan.value, 2),
            "warning": warn_led.is_lit,
            "alarm": alarm.is_active,
        },
        "actions": actions,
    }
    client.publish("iot/demo/smart_home", json.dumps(data))
    time.sleep(0.3)

# クリーンアップ
room_light.off()
mood_light.off()
fan.stop()
warn_led.off()
alarm.off()
client.loop_stop()
client.disconnect()
print("\n完了! 全デバイスOFF。")
