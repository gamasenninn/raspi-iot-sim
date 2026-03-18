"""GPIOピン割り当て定義

実機に移行する際もこのファイルのみ変更すればよい。
"""

# === 出力デバイス ===
LED_RED = 17
LED_PWM = 18
RGBLED_RED = 22
RGBLED_GREEN = 23
RGBLED_BLUE = 24
BUZZER = 25
SERVO = 13
MOTOR_FWD = 5
MOTOR_BWD = 6

# === 入力デバイス ===
BUTTON = 16
MOTION_SENSOR = 20
LINE_SENSOR = 21

# === ソフトウェアシミュレーション用センサー ===
# DHT22, BMP280等はI2C/SPIで接続されるため
# GPIOピンではなくソフトウェアで値を生成する
