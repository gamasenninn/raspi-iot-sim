"""スマートドアロック
- モーションセンサーで人を検知
- ボタンで解錠/施錠
- サーボモーターでロック動作
- 状態をMQTTで配信 + REST APIから遠隔操作可能
"""
import os, sys, time, json
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, Servo, Button, MotionSensor, LED, Buzzer
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# デバイス
servo = Servo(13)          # ドアロック
btn = Button(16, pull_up=True)
pir = MotionSensor(20)
led_green = LED(17)        # 解錠中
buzzer = Buzzer(25)        # 警告音

# MQTT
client = mqtt.Client(client_id="door-lock")
client.connect("mosquitto", 1883, 60)
client.loop_start()

locked = True
servo.min()  # 施錠位置

def lock_door():
    global locked
    servo.min()
    locked = True
    led_green.off()
    print("  [LOCK] ドア施錠 (サーボ: min)")

def unlock_door():
    global locked
    servo.max()
    locked = False
    led_green.on()
    print("  [UNLOCK] ドア解錠 (サーボ: max)")

print("=" * 55)
print("  スマートドアロック シミュレーション")
print("=" * 55)

scenarios = [
    ("人が接近", "motion", None),
    ("ボタンで解錠", "button", "unlock"),
    ("5秒後自動施錠", "auto_lock", None),
    ("人が接近", "motion", None),
    ("ボタンで解錠", "button", "unlock"),
    ("ドア開放中に再度人が接近", "motion", None),
    ("ボタンで施錠", "button", "lock"),
    ("不審な動き検知 → 警報", "intrusion", None),
]

for i, (desc, action, param) in enumerate(scenarios):
    print(f"\n--- シナリオ [{i+1}/8]: {desc} ---")

    if action == "motion":
        pir.pin.drive_high()
        time.sleep(0.1)
        print(f"  モーション検知: {pir.is_active}")
        if locked:
            buzzer.on()
            time.sleep(0.1)
            buzzer.off()
            print("  → 施錠中のため通知音")
        pir.pin.drive_low()

    elif action == "button":
        btn.pin.drive_low()
        time.sleep(0.1)
        btn.pin.drive_high()
        if param == "unlock":
            unlock_door()
        else:
            lock_door()

    elif action == "auto_lock":
        print("  自動施錠タイマー...")
        time.sleep(0.5)
        lock_door()

    elif action == "intrusion":
        pir.pin.drive_high()
        time.sleep(0.1)
        buzzer.on()
        print(f"  !!! 侵入警報 !!! モーション:{pir.is_active} ブザー:{buzzer.is_active}")
        time.sleep(0.3)
        buzzer.off()
        pir.pin.drive_low()

    # MQTT配信
    status = {
        "scenario": desc,
        "locked": locked,
        "servo": servo.value,
        "motion": pir.is_active,
        "led_green": led_green.is_lit,
        "buzzer": buzzer.is_active,
    }
    client.publish("iot/demo/door_lock", json.dumps(status))
    print(f"  状態: locked={locked} servo={servo.value} LED={led_green.is_lit}")

    time.sleep(0.3)

servo.min()
led_green.off()
buzzer.off()
client.loop_stop()
client.disconnect()
print("\n完了!")
