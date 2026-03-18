"""温湿度モニター - しきい値を超えたらLEDとブザーで警告"""
import os, sys, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, LED, PWMLED, Buzzer
from gpiozero.pins.mock import MockFactory, MockPWMPin
from devices.sensors import DHT22Temp, DHT22Humidity, BMP280Pressure
from config.pin_map import LED_RED, LED_PWM, BUZZER

# MockPWMPin で初期化 (PWM対応)
Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# デバイス初期化
led_warn = LED(LED_RED)
led_level = PWMLED(LED_PWM)
buzzer = Buzzer(BUZZER)

# センサー初期化
temp_sensor = DHT22Temp()
humi_sensor = DHT22Humidity()
pres_sensor = BMP280Pressure()

# しきい値
TEMP_WARN = 24.0
HUMI_WARN = 80.0

print("=" * 55)
print("  温湿度モニター (10回計測)")
print(f"  警告: 温度>{TEMP_WARN}°C or 湿度>{HUMI_WARN}%")
print("=" * 55)

for i in range(10):
    temp_sensor.update()
    humi_sensor.update()
    pres_sensor.update()

    temp = temp_sensor.value
    humi = humi_sensor.value
    pres = pres_sensor.value

    alert = temp > TEMP_WARN or humi > HUMI_WARN
    if alert:
        led_warn.on()
        buzzer.on()
        brightness = min(1.0, max(0, (temp - 20) / 10))
        led_level.value = brightness
        status = "!! 警告 !!"
    else:
        led_warn.off()
        buzzer.off()
        led_level.value = 0
        status = "   正常   "

    print(f"[{i+1:2d}/10] {status} | "
          f"温度: {temp:6.2f}°C | "
          f"湿度: {humi:6.2f}% | "
          f"気圧: {pres:7.2f}hPa | "
          f"LED:{led_warn.is_lit} Buzzer:{buzzer.is_active}")
    
    time.sleep(0.3)

led_warn.off()
led_level.off()
buzzer.off()
print("\n計測完了。全デバイスOFF。")
