"""E2Eテスト: コマンド送信→状態変化の完全フロー

Pi VM上でmain.pyが稼働中 + Mosquittoが起動中の状態で実行する。
docker exec 経由で Mosquitto コンテナ内の mosquitto_sub/pub を使用。
"""
import json
import subprocess
import time
import pytest
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


def _docker_available():
    try:
        r = subprocess.run(
            ["docker", "exec", "mosquitto", "mosquitto_sub", "-t", "iot/devices/+/state", "-C", "1", "-W", "5"],
            capture_output=True, text=True, timeout=10,
        )
        return r.returncode == 0 and r.stdout.strip()
    except Exception:
        return False


requires_e2e = pytest.mark.skipif(
    not _docker_available(),
    reason="Pi VM app (main.py) is not running or docker not available"
)


def wait_for_state(topic, condition_fn, timeout=10):
    """docker exec 経由で mosquitto_sub を実行し、条件を満たすメッセージを待つ"""
    try:
        r = subprocess.run(
            ["docker", "exec", "mosquitto", "mosquitto_sub", "-t", topic, "-C", "5", "-W", str(timeout)],
            capture_output=True, text=True, timeout=timeout + 5,
        )
        for line in r.stdout.strip().split("\n"):
            if not line:
                continue
            try:
                data = json.loads(line)
                if condition_fn(data):
                    return data
            except json.JSONDecodeError:
                pass
    except Exception:
        pass
    return None


def send_command(device, action, value=None):
    """docker exec 経由でMQTTコマンドを送信"""
    payload = {"action": action}
    if value is not None:
        payload["value"] = str(value)
    payload_str = json.dumps(payload)
    subprocess.run(
        ["docker", "exec", "mosquitto", "mosquitto_pub",
         "-t", f"iot/devices/{device}/command", "-m", payload_str],
        capture_output=True, timeout=5,
    )


@requires_e2e
class TestE2ELed:
    def test_led_on_command_changes_state(self):
        """LED ON コマンド → テレメトリで on=true を確認"""
        send_command("led_red", "on")
        data = wait_for_state(
            "iot/devices/led_red/state",
            lambda d: d.get("on") is True,
        )
        assert data is not None, "LED ON の状態を受信できなかった"
        assert data["on"] is True

    def test_led_off_command_changes_state(self):
        """LED OFF コマンド → テレメトリで on=false を確認"""
        send_command("led_red", "off")
        data = wait_for_state(
            "iot/devices/led_red/state",
            lambda d: d.get("on") is False,
        )
        assert data is not None
        assert data["on"] is False


@requires_e2e
class TestE2EServo:
    def test_servo_set_value(self):
        """サーボ値設定 → テレメトリで反映を確認"""
        send_command("servo", "set", "0.5")
        data = wait_for_state(
            "iot/devices/servo/state",
            lambda d: d.get("value") is not None and abs(d["value"] - 0.5) < 0.1,
        )
        assert data is not None, "Servo value 0.5 を受信できなかった"


@requires_e2e
class TestE2ESensor:
    def test_temperature_telemetry_stream(self):
        """温度センサーのテレメトリが連続して届く"""
        r = subprocess.run(
            ["docker", "exec", "mosquitto", "mosquitto_sub",
             "-t", "iot/devices/dht22_temperature/state", "-C", "3", "-W", "15"],
            capture_output=True, text=True, timeout=20,
        )
        lines = [l for l in r.stdout.strip().split("\n") if l]
        received = [json.loads(l) for l in lines]

        assert len(received) >= 3, f"3件未満: {len(received)}件しか受信できなかった"
        for i in range(1, len(received)):
            assert received[i]["timestamp"] > received[i-1]["timestamp"]
        for rec in received:
            assert isinstance(rec["value"], float)
            assert rec["unit"] == "\u00b0C"


@requires_e2e
class TestE2EMotor:
    def test_motor_forward_stop(self):
        """モーター前進→停止の完全フロー"""
        send_command("motor", "forward")
        data = wait_for_state(
            "iot/devices/motor/state",
            lambda d: d.get("speed", 0) > 0,
        )
        assert data is not None, "Motor forward を受信できなかった"

        send_command("motor", "stop")
        data = wait_for_state(
            "iot/devices/motor/state",
            lambda d: d.get("speed", 1) == 0.0,
        )
        assert data is not None, "Motor stop を受信できなかった"
