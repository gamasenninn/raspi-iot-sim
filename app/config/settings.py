"""アプリケーション設定"""
import os

# MQTT設定 (PI-CI内からはQEMUゲートウェイ経由)
MQTT_BROKER = os.environ.get("MQTT_BROKER", "mosquitto")
MQTT_PORT = int(os.environ.get("MQTT_PORT", "1883"))
MQTT_KEEPALIVE = 60

# Flask/WebSocket設定
APP_HOST = "0.0.0.0"
APP_PORT = int(os.environ.get("APP_PORT", "5000"))

# シミュレーション設定
SIM_INTERVAL = float(os.environ.get("SIM_INTERVAL", "1.0"))  # 秒
