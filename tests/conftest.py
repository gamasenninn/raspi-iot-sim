"""テスト共通設定・フィクスチャ"""
import os
import sys
import pytest

# MockFactory環境変数を設定
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
os.environ["MQTT_BROKER"] = "localhost"

# appディレクトリをパスに追加
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))


@pytest.fixture
def registry():
    """全デバイスを生成したレジストリを返す。テストごとにリセット。"""
    from gpiozero import Device
    from gpiozero.pins.mock import MockFactory, MockPWMPin

    Device.pin_factory = MockFactory(pin_class=MockPWMPin)

    import devices.factory as f
    f._registry = {}
    return f.create_all_devices()


@pytest.fixture
def flask_client(registry):
    """Flask テストクライアント"""
    from protocols.rest_api import create_app
    app = create_app(registry)
    app.config["TESTING"] = True
    with app.test_client() as client:
        yield client


def mqtt_broker_available():
    """localhostのMQTTブローカーに接続できるか確認"""
    try:
        import socket
        s = socket.create_connection(("localhost", 1883), timeout=2)
        s.close()
        return True
    except (ConnectionRefusedError, OSError):
        return False


requires_mqtt = pytest.mark.skipif(
    not mqtt_broker_available(),
    reason="MQTT broker not available on localhost:1883"
)

def pi_vm_app_running():
    """Pi VM上のmain.pyからテレメトリが届いているか確認"""
    if not mqtt_broker_available():
        return False
    try:
        import paho.mqtt.client as mqtt
        import threading
        received = threading.Event()

        def on_msg(c, ud, msg):
            received.set()

        c = mqtt.Client(client_id="e2e-check")
        c.on_message = on_msg
        c.connect("localhost", 1883, 60)
        c.subscribe("iot/devices/+/state")
        c.loop_start()
        result = received.wait(timeout=5)
        c.loop_stop()
        c.disconnect()
        return result
    except Exception:
        return False


requires_e2e = pytest.mark.skipif(
    not pi_vm_app_running(),
    reason="Pi VM app (main.py) is not running - no telemetry received"
)
