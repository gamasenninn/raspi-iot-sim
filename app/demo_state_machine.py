"""ステートマシンベースのIoTデバイス制御

gpiozero のコールバック機能を活用した、イベント駆動の温室制御システム。
状態遷移:
  IDLE -> MONITORING -> ALERT -> EMERGENCY -> RECOVERY -> IDLE

各状態で異なるデバイス組み合わせが動作する。
"""
import os, sys, time, json
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, LED, PWMLED, RGBLED, Motor, Buzzer, Button
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt
from devices.sensors import DHT22Temp, DHT22Humidity, SoilMoisture

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# Devices
status_led = RGBLED(22, 23, 24)
alarm_led = LED(17)
fan = Motor(5, 6)
buzzer = Buzzer(25)
water_pump = PWMLED(18)  # PWM pump speed
btn = Button(16, pull_up=True)

# Sensors
temp = DHT22Temp()
humidity = DHT22Humidity()
soil = SoilMoisture()

# MQTT
client = mqtt.Client(client_id="state-machine")
client.connect("mosquitto", 1883, 60)
client.loop_start()

# === State Machine ===
STATES = {
    "IDLE":       {"color": (0, 0, 0.1), "desc": "Standby - minimal power"},
    "MONITORING": {"color": (0, 1, 0),   "desc": "Active monitoring"},
    "ALERT":      {"color": (1, 1, 0),   "desc": "Warning - parameters drifting"},
    "EMERGENCY":  {"color": (1, 0, 0),   "desc": "Critical - immediate action"},
    "RECOVERY":   {"color": (0, 0, 1),   "desc": "Recovering to normal"},
}

current_state = "IDLE"
state_history = []
cycle = 0


def transition(new_state, reason):
    global current_state
    old = current_state
    current_state = new_state
    state_history.append({"from": old, "to": new_state, "reason": reason, "cycle": cycle})

    info = STATES[new_state]
    status_led.color = info["color"]
    print(f"  >>> STATE: {old} -> {new_state} ({reason})")

    client.publish("iot/demo/state", json.dumps({
        "state": new_state,
        "previous": old,
        "reason": reason,
        "description": info["desc"],
        "cycle": cycle,
    }))


def apply_state_actions(t_val, h_val, s_val):
    """現在の状態に応じたアクチュエータ制御"""
    if current_state == "IDLE":
        fan.stop()
        water_pump.off()
        buzzer.off()
        alarm_led.off()

    elif current_state == "MONITORING":
        # 温度に応じた穏やかなファン制御
        if t_val > 24:
            fan.forward(0.3)
        else:
            fan.stop()
        # 土壌に応じた少量灌漑
        if s_val < 50:
            water_pump.value = 0.3
        else:
            water_pump.off()
        buzzer.off()
        alarm_led.off()

    elif current_state == "ALERT":
        # 強めのファン
        fan.forward(0.7)
        # 灌漑強化
        if s_val < 45:
            water_pump.value = 0.7
            soil.value = 65.0  # simulate watering effect
        alarm_led.on()
        buzzer.off()

    elif current_state == "EMERGENCY":
        # 全力冷却
        fan.forward(1.0)
        # 全力灌漑
        water_pump.value = 1.0
        soil.value = 80.0
        buzzer.on()
        alarm_led.on()

    elif current_state == "RECOVERY":
        fan.forward(0.5)
        water_pump.value = 0.2
        buzzer.off()
        alarm_led.off()


def evaluate_transition(t_val, h_val, s_val):
    """センサー値に基づく状態遷移判定"""
    if current_state == "IDLE":
        transition("MONITORING", "system activated")

    elif current_state == "MONITORING":
        if t_val > 28 or s_val < 25:
            transition("EMERGENCY", f"critical: T={t_val}C soil={s_val}%")
        elif t_val > 25 or h_val > 75 or s_val < 40:
            transition("ALERT", f"warning: T={t_val}C H={h_val}% soil={s_val}%")

    elif current_state == "ALERT":
        if t_val > 28 or s_val < 25:
            transition("EMERGENCY", f"escalated: T={t_val}C soil={s_val}%")
        elif t_val < 24 and h_val < 70 and s_val > 50:
            transition("MONITORING", f"normalized: T={t_val}C H={h_val}% soil={s_val}%")

    elif current_state == "EMERGENCY":
        if t_val < 26 and s_val > 40:
            transition("RECOVERY", f"de-escalated: T={t_val}C soil={s_val}%")

    elif current_state == "RECOVERY":
        if t_val < 24 and h_val < 65 and s_val > 55:
            transition("MONITORING", f"recovered: T={t_val}C H={h_val}% soil={s_val}%")
        elif t_val > 27:
            transition("EMERGENCY", f"relapse: T={t_val}C")


# === gpiozero Callback: ボタンで手動リセット ===
def on_button_press():
    print("  [BUTTON] Manual reset pressed!")
    transition("IDLE", "manual reset")

btn.when_pressed = on_button_press

# === Main Loop ===
print("=" * 65)
print("  Greenhouse State Machine Controller")
print("=" * 65)
print("  States: IDLE -> MONITORING -> ALERT -> EMERGENCY -> RECOVERY")
print("-" * 65)

# 温度を意図的に上昇させるシナリオ
temp_boost_cycles = {15: 5.0, 25: -8.0, 35: 3.0}  # cycle: delta

for cycle in range(1, 46):
    # センサー更新
    temp.update()
    humidity.update()
    soil.update()

    # シナリオ: 温度ブースト
    if cycle in temp_boost_cycles:
        temp.value += temp_boost_cycles[cycle]
        print(f"  ** SCENARIO: temp boost {temp_boost_cycles[cycle]:+.1f}C **")

    t_val = temp.value
    h_val = humidity.value
    s_val = soil.value

    # 状態遷移判定
    evaluate_transition(t_val, h_val, s_val)

    # アクチュエータ制御
    apply_state_actions(t_val, h_val, s_val)

    # 表示
    state_info = STATES[current_state]
    print(f"  [{cycle:2d}] {current_state:12s} | "
          f"T:{t_val:5.1f}C H:{h_val:5.1f}% Soil:{s_val:5.1f}% | "
          f"Fan:{fan.value:4.1f} Pump:{water_pump.value:3.1f} "
          f"Alarm:{alarm_led.is_lit} Buzzer:{buzzer.is_active}")

    # MQTT
    client.publish("iot/demo/greenhouse", json.dumps({
        "cycle": cycle,
        "state": current_state,
        "sensors": {"temp": t_val, "humidity": h_val, "soil": s_val},
        "actuators": {
            "fan": round(fan.value, 2),
            "pump": round(water_pump.value, 2),
            "alarm": alarm_led.is_lit,
            "buzzer": buzzer.is_active,
        },
    }))

    # ボタンリセットシミュレーション (cycle 40で)
    if cycle == 40:
        print("  ** SCENARIO: manual reset button **")
        btn.pin.drive_low()
        time.sleep(0.05)
        btn.pin.drive_high()

    time.sleep(0.15)

# === Summary ===
print("\n" + "=" * 65)
print("  State Transition History")
print("=" * 65)
for entry in state_history:
    print(f"  Cycle {entry['cycle']:2d}: {entry['from']:12s} -> {entry['to']:12s} | {entry['reason']}")

print(f"\n  Total transitions: {len(state_history)}")

client.loop_stop()
client.disconnect()
print("  Done!")
