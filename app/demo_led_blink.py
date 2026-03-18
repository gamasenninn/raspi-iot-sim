"""LED点滅デモ - 赤LEDを5回点滅させる"""
import os, sys, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import LED
from config.pin_map import LED_RED

led = LED(LED_RED)
print(f"GPIO {LED_RED} に接続された赤LEDを5回点滅します")

for i in range(5):
    led.on()
    print(f"  [{i+1}/5] ON  (is_lit={led.is_lit})")
    time.sleep(0.5)
    led.off()
    print(f"  [{i+1}/5] OFF (is_lit={led.is_lit})")
    time.sleep(0.5)

print("完了!")
