"""WebSocketサーバー - リアルタイムデバイス状態配信"""
import time
import json
from flask_socketio import SocketIO, emit


def create_socketio(app, registry):
    socketio = SocketIO(app, cors_allowed_origins="*", async_mode="threading")

    @socketio.on("connect")
    def handle_connect():
        print("[WebSocket] クライアント接続")
        # 接続時に全デバイス状態を送信
        states = {}
        for name, info in registry.items():
            states[name] = {
                "type": info["type"],
                "category": info["category"],
                "state": info["get_state"](),
            }
        emit("all_states", states)

    @socketio.on("device_command")
    def handle_command(data):
        name = data.get("device")
        action = data.get("action")
        value = data.get("value")

        if name not in registry:
            emit("error", {"message": f"不明なデバイス: {name}"})
            return

        info = registry[name]
        if action not in info["actions"]:
            emit("error", {"message": f"不明なアクション: {action}"})
            return

        try:
            if value is not None:
                info["actions"][action](value)
            else:
                info["actions"][action]()
            emit("device_update", {
                "device": name,
                "state": info["get_state"](),
                "timestamp": time.time(),
            })
        except Exception as e:
            emit("error", {"message": str(e)})

    def broadcast_states():
        """定期的に全クライアントへ状態をブロードキャスト"""
        while True:
            for name, info in registry.items():
                try:
                    socketio.emit("device_update", {
                        "device": name,
                        "state": info["get_state"](),
                        "timestamp": time.time(),
                    })
                except Exception:
                    pass
            time.sleep(1)

    return socketio, broadcast_states
