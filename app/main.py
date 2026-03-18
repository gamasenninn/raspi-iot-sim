"""Raspberry Pi IoT シミュレーション - メインエントリポイント

PI-CI (QEMU) 上のRaspberry Pi OS内で動作する。
gpiozero MockFactoryにより実機なしでGPIOデバイスを操作可能。
"""
import os
import sys
import threading

# MockFactory環境変数を設定 (PI-CI上ではGPIOハードウェアがないため)
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from devices.factory import create_all_devices
from simulation.engine import SimulationEngine
from protocols.mqtt_client import MQTTClient
from protocols.rest_api import create_app
from protocols.websocket_server import create_socketio
from config.settings import APP_HOST, APP_PORT


def main():
    print("=" * 50)
    print("  Raspberry Pi IoT シミュレーション")
    print("=" * 50)

    # 1. デバイス生成
    registry = create_all_devices()
    for name, info in registry.items():
        print(f"  [{info['category']}] {name}")

    # 2. シミュレーションエンジン開始
    sim = SimulationEngine(registry)
    sim.start()

    # 3. MQTT接続
    mqtt_client = MQTTClient(registry)
    if mqtt_client.connect():
        mqtt_client.start_publishing()
    else:
        print("[警告] MQTTなしで続行します")

    # 4. Flask + WebSocket
    app = create_app(registry)
    socketio, broadcast_fn = create_socketio(app, registry)

    # WebSocket定期配信をバックグラウンドで
    threading.Thread(target=broadcast_fn, daemon=True).start()

    print(f"\n[API] http://{APP_HOST}:{APP_PORT}/api/devices")
    print(f"[WS]  ws://{APP_HOST}:{APP_PORT}/socket.io/")
    print()

    # 5. Flaskサーバー起動 (ブロッキング)
    socketio.run(app, host=APP_HOST, port=APP_PORT, allow_unsafe_werkzeug=True)


if __name__ == "__main__":
    main()
