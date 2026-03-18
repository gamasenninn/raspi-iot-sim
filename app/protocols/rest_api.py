"""REST API - デバイス状態の取得とコマンド送信"""
from flask import Flask, jsonify, request


def create_app(registry):
    app = Flask(__name__)

    @app.route("/api/health")
    def health():
        return jsonify({"status": "ok", "devices": len(registry)})

    @app.route("/api/devices")
    def list_devices():
        result = {}
        for name, info in registry.items():
            result[name] = {
                "type": info["type"],
                "category": info["category"],
                "state": info["get_state"](),
                "actions": list(info["actions"].keys()),
            }
        return jsonify(result)

    @app.route("/api/devices/<name>")
    def get_device(name):
        if name not in registry:
            return jsonify({"error": f"デバイス '{name}' が見つかりません"}), 404
        info = registry[name]
        return jsonify({
            "name": name,
            "type": info["type"],
            "category": info["category"],
            "state": info["get_state"](),
            "actions": list(info["actions"].keys()),
        })

    @app.route("/api/devices/<name>/action", methods=["POST"])
    def device_action(name):
        if name not in registry:
            return jsonify({"error": f"デバイス '{name}' が見つかりません"}), 404

        info = registry[name]
        data = request.get_json(silent=True) or {}
        action = data.get("action")
        value = data.get("value")

        if not action:
            return jsonify({"error": "'action' を指定してください"}), 400
        if action not in info["actions"]:
            return jsonify({
                "error": f"不明なアクション '{action}'",
                "available": list(info["actions"].keys()),
            }), 400

        try:
            if value is not None:
                info["actions"][action](value)
            else:
                info["actions"][action]()
            return jsonify({
                "ok": True,
                "device": name,
                "action": action,
                "state": info["get_state"](),
            })
        except Exception as e:
            return jsonify({"error": str(e)}), 500

    return app
