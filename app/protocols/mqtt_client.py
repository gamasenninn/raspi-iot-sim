"""MQTTクライアント - デバイス状態の配信とコマンド受信"""
import json
import time
import threading
import paho.mqtt.client as mqtt
from config.settings import MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE, SIM_INTERVAL


TOPIC_TELEMETRY = "iot/devices/{}/state"
TOPIC_COMMAND = "iot/devices/{}/command"
TOPIC_COMMAND_ALL = "iot/devices/+/command"


class MQTTClient:
    def __init__(self, registry):
        self._registry = registry
        self._client = mqtt.Client(client_id="raspi-iot-sim")
        self._client.on_connect = self._on_connect
        self._client.on_message = self._on_message
        self._connected = False
        self._publish_thread = None
        self._running = False

    def connect(self, retries=10, delay=3):
        """MQTTブローカーに接続 (リトライ付き)"""
        for i in range(retries):
            try:
                print(f"[MQTT] {MQTT_BROKER}:{MQTT_PORT} に接続中... ({i+1}/{retries})")
                self._client.connect(MQTT_BROKER, MQTT_PORT, MQTT_KEEPALIVE)
                self._client.loop_start()
                return True
            except Exception as e:
                print(f"[MQTT] 接続失敗: {e}")
                time.sleep(delay)
        print("[MQTT] 接続を断念しました")
        return False

    def _on_connect(self, client, userdata, flags, rc):
        if rc == 0:
            self._connected = True
            print("[MQTT] ブローカーに接続しました")
            client.subscribe(TOPIC_COMMAND_ALL, qos=1)
            print(f"[MQTT] {TOPIC_COMMAND_ALL} をサブスクライブ")
        else:
            print(f"[MQTT] 接続失敗 rc={rc}")

    def _on_message(self, client, userdata, msg):
        """コマンド受信ハンドラ"""
        try:
            parts = msg.topic.split("/")
            device_name = parts[2]
            payload = json.loads(msg.payload.decode())
            action = payload.get("action")
            value = payload.get("value")

            if device_name not in self._registry:
                print(f"[MQTT] 不明なデバイス: {device_name}")
                return

            info = self._registry[device_name]
            if action in info["actions"]:
                if value is not None:
                    info["actions"][action](value)
                else:
                    info["actions"][action]()
                print(f"[MQTT] コマンド実行: {device_name}.{action}({value or ''})")
            else:
                print(f"[MQTT] 不明なアクション: {device_name}.{action}")
        except Exception as e:
            print(f"[MQTT] コマンド処理エラー: {e}")

    def start_publishing(self):
        """定期的にテレメトリを配信"""
        self._running = True
        self._publish_thread = threading.Thread(target=self._publish_loop, daemon=True)
        self._publish_thread.start()

    def stop(self):
        self._running = False
        self._client.loop_stop()
        self._client.disconnect()

    def _publish_loop(self):
        while self._running:
            if self._connected:
                for name, info in self._registry.items():
                    try:
                        state = info["get_state"]()
                        topic = TOPIC_TELEMETRY.format(name)
                        payload = json.dumps({
                            "device": name,
                            "type": info["type"],
                            "category": info["category"],
                            **state,
                            "timestamp": time.time(),
                        })
                        self._client.publish(topic, payload, qos=0)
                    except Exception as e:
                        print(f"[MQTT] 配信エラー ({name}): {e}")
            time.sleep(SIM_INTERVAL)
