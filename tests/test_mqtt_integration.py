"""インテグレーションテスト: MQTT Pub/Sub (要Mosquittoブローカー)"""
import json
import time
import threading
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from conftest import requires_mqtt


@requires_mqtt
class TestMQTTPubSub:
    def _make_client(self, client_id):
        import paho.mqtt.client as mqtt
        c = mqtt.Client(client_id=client_id)
        c.connect("localhost", 1883, 60)
        c.loop_start()
        return c

    def test_publish_and_subscribe(self):
        """メッセージの送受信ができる"""
        received = []
        event = threading.Event()

        sub = self._make_client("test-sub")
        pub = self._make_client("test-pub")

        def on_msg(client, userdata, msg):
            received.append(json.loads(msg.payload.decode()))
            event.set()

        sub.on_message = on_msg
        sub.subscribe("iot/test/ping")
        time.sleep(0.5)

        pub.publish("iot/test/ping", json.dumps({"msg": "hello"}))
        event.wait(timeout=5)

        sub.loop_stop()
        pub.loop_stop()
        sub.disconnect()
        pub.disconnect()

        assert len(received) == 1
        assert received[0]["msg"] == "hello"

    def test_wildcard_subscription(self):
        """ワイルドカードサブスクリプションが動作する"""
        received = []
        event = threading.Event()

        sub = self._make_client("test-wild-sub")
        pub = self._make_client("test-wild-pub")

        def on_msg(client, userdata, msg):
            received.append(msg.topic)
            if len(received) >= 2:
                event.set()

        sub.on_message = on_msg
        sub.subscribe("iot/test/+/state")
        time.sleep(0.5)

        pub.publish("iot/test/device_a/state", "a")
        pub.publish("iot/test/device_b/state", "b")
        event.wait(timeout=5)

        sub.loop_stop()
        pub.loop_stop()
        sub.disconnect()
        pub.disconnect()

        assert "iot/test/device_a/state" in received
        assert "iot/test/device_b/state" in received

    def test_command_roundtrip(self):
        """コマンドの送受信が正しいJSON形式で行われる"""
        received = []
        event = threading.Event()

        sub = self._make_client("test-cmd-sub")
        pub = self._make_client("test-cmd-pub")

        def on_msg(client, userdata, msg):
            received.append({
                "topic": msg.topic,
                "payload": json.loads(msg.payload.decode()),
            })
            event.set()

        sub.on_message = on_msg
        sub.subscribe("iot/devices/+/command")
        time.sleep(0.5)

        cmd = {"action": "set", "value": "0.5"}
        pub.publish("iot/devices/servo/command", json.dumps(cmd))
        event.wait(timeout=5)

        sub.loop_stop()
        pub.loop_stop()
        sub.disconnect()
        pub.disconnect()

        assert len(received) == 1
        assert received[0]["topic"] == "iot/devices/servo/command"
        assert received[0]["payload"]["action"] == "set"
        assert received[0]["payload"]["value"] == "0.5"
