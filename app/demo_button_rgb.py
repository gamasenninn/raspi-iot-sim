"""ボタンでRGB LEDの色を切り替え、MQTTで状態を通知"""
import os, sys, time, json
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, Button, RGBLED
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

btn = Button(16, pull_up=True)
rgb = RGBLED(22, 23, 24)

# MQTT接続
client = mqtt.Client(client_id="demo-button-rgb")
client.connect("mosquitto", 1883, 60)
client.loop_start()

# 色パターン
COLORS = [
    ("赤",     (1, 0, 0)),
    ("緑",     (0, 1, 0)),
    ("青",     (0, 0, 1)),
    ("黄",     (1, 1, 0)),
    ("シアン",  (0, 1, 1)),
    ("マゼンタ",(1, 0, 1)),
    ("白",     (1, 1, 1)),
    ("消灯",   (0, 0, 0)),
]

print("=" * 50)
print("  ボタン → RGB LED 制御デモ")
print("  ボタンを押すたびに色が変わります")
print("=" * 50)

color_idx = 0

for i in range(8):
    # ボタン押下をシミュレーション
    print(f"\n--- ボタン押下 [{i+1}/8] ---")
    btn.pin.drive_low()   # press
    time.sleep(0.1)
    btn.pin.drive_high()  # release

    # 色を変更
    name, color = COLORS[color_idx]
    rgb.color = color
    color_idx = (color_idx + 1) % len(COLORS)

    print(f"  色: {name} ({color})")
    print(f"  RGB値: R={rgb.red:.1f} G={rgb.green:.1f} B={rgb.blue:.1f}")
    print(f"  ボタン状態: pressed={btn.is_pressed}")

    # MQTTで通知
    payload = json.dumps({
        "event": "color_change",
        "color_name": name,
        "rgb": list(color),
        "press_count": i + 1,
    })
    client.publish("iot/demo/rgb_status", payload)
    print(f"  MQTT送信: {payload}")

    time.sleep(0.3)

rgb.off()
client.loop_stop()
client.disconnect()
print("\n完了!")
