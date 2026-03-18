"""ユニットテスト: MQTTトピックとペイロード形式"""
import pytest
import json
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

from protocols.mqtt_client import TOPIC_TELEMETRY, TOPIC_COMMAND, TOPIC_COMMAND_ALL


class TestTopicFormat:
    def test_telemetry_topic(self):
        assert TOPIC_TELEMETRY.format("led_red") == "iot/devices/led_red/state"

    def test_command_topic(self):
        assert TOPIC_COMMAND.format("servo") == "iot/devices/servo/command"

    def test_command_wildcard(self):
        assert TOPIC_COMMAND_ALL == "iot/devices/+/command"

    def test_telemetry_topic_all_devices(self, registry):
        for name in registry:
            topic = TOPIC_TELEMETRY.format(name)
            parts = topic.split("/")
            assert len(parts) == 4
            assert parts[0] == "iot"
            assert parts[1] == "devices"
            assert parts[2] == name
            assert parts[3] == "state"


class TestPayloadStructure:
    def test_output_device_payload(self, registry):
        """出力デバイスのペイロードに必須フィールドがある"""
        led = registry["led_red"]
        state = led["get_state"]()
        # MQTTクライアントが送信する形式をシミュレーション
        payload = {
            "device": "led_red",
            "type": led["type"],
            "category": led["category"],
            **state,
            "timestamp": 12345.0,
        }
        assert "device" in payload
        assert "type" in payload
        assert "category" in payload
        assert "timestamp" in payload
        assert payload["type"] == "output"

    def test_sensor_payload(self, registry):
        """センサーのペイロードに value と unit がある"""
        temp = registry["dht22_temperature"]
        state = temp["get_state"]()
        payload = {
            "device": "dht22_temperature",
            "type": temp["type"],
            "category": temp["category"],
            **state,
            "timestamp": 12345.0,
        }
        assert "value" in payload
        assert "unit" in payload
        assert isinstance(payload["value"], float)

    def test_command_payload_on(self):
        """ONコマンドのペイロード形式"""
        payload = json.dumps({"action": "on"})
        parsed = json.loads(payload)
        assert "action" in parsed
        assert parsed["action"] == "on"

    def test_command_payload_with_value(self):
        """値付きコマンドのペイロード形式"""
        payload = json.dumps({"action": "set", "value": "0.5"})
        parsed = json.loads(payload)
        assert parsed["action"] == "set"
        assert parsed["value"] == "0.5"

    def test_all_payloads_are_json_serializable(self, registry):
        """全デバイスのペイロードがJSON化可能"""
        for name, info in registry.items():
            state = info["get_state"]()
            payload = {
                "device": name,
                "type": info["type"],
                "category": info["category"],
                **state,
                "timestamp": 0.0,
            }
            serialized = json.dumps(payload)
            assert isinstance(serialized, str)
            deserialized = json.loads(serialized)
            assert deserialized["device"] == name
