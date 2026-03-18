# 第7章 REST APIでデバイスを遠隔制御する

この章では、HTTPベースのREST APIを実装し、Webブラウザやcurlコマンドからデバイスを制御する方法を学びます。

## 7.1 REST APIとは

REST（Representational State Transfer）は、Webサービスを設計するためのアーキテクチャスタイルです。HTTPメソッド（GET, POST, PUT, DELETE）を使ってリソースを操作します。

### MQTTとREST APIの使い分け

| 特性 | MQTT | REST API |
|------|------|----------|
| 通信方式 | Pub/Sub（常時接続） | リクエスト/レスポンス |
| リアルタイム性 | 高い | 低い（ポーリング必要） |
| オーバーヘッド | 極めて小さい | HTTPヘッダー分大きい |
| 適した用途 | センサーデータの連続配信 | 状態の問い合わせ、コマンド実行 |
| ツール | 専用クライアント必要 | ブラウザやcurlで使える |

両方を提供することで、用途に応じて最適なインターフェースを選択できます。

## 7.2 FlaskによるREST APIの実装

PythonのWebフレームワーク「Flask」を使ってREST APIを実装します。

### エンドポイント一覧

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/devices` | 全デバイス一覧+状態 |
| GET | `/api/devices/{name}` | 特定デバイスの状態 |
| POST | `/api/devices/{name}/action` | コマンド実行 |

### 実装コード

```python
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

        if not action:
            return jsonify({"error": "'action' を指定してください"}), 400
        if action not in info["actions"]:
            return jsonify({
                "error": f"不明なアクション '{action}'",
                "available": list(info["actions"].keys()),
            }), 400

        try:
            value = data.get("value")
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
```

> **Note:** エラーレスポンスには利用可能なアクションの一覧（`available`）を含めています。これにより、クライアント側で「どの操作ができるか」を動的に取得できます。

### デバイスレジストリとの連携

REST APIはデバイスファクトリが生成したレジストリ（辞書）をそのまま参照します。MQTTクライアントも同じレジストリを使用するため、どちらから操作しても同じデバイスの状態が変化します。

```
REST API ──┐
            ├──> デバイスレジストリ ──> gpiozero デバイス
MQTT     ──┘
```

## 7.3 APIの使い方

### ヘルスチェック

```bash
curl http://localhost:5000/api/health
```

```json
{"devices": 15, "status": "ok"}
```

### 全デバイス一覧

```bash
curl http://localhost:5000/api/devices
```

### LEDを点灯

```bash
curl -X POST http://localhost:5000/api/devices/led_red/action \
  -H "Content-Type: application/json" \
  -d '{"action": "on"}'
```

```json
{"ok": true, "device": "led_red", "action": "on", "state": {"on": true}}
```

### サーボの角度を設定

```bash
curl -X POST http://localhost:5000/api/devices/servo/action \
  -H "Content-Type: application/json" \
  -d '{"action": "set", "value": "0.75"}'
```

### エラーハンドリング

存在しないデバイスへのアクセス:
```json
{"error": "Device 'nonexistent' not found"}  // 404
```

不正なアクション:
```json
{"error": "Unknown action 'fly'", "available": ["on", "off", "toggle"]}  // 400
```

利用可能なアクションの一覧が返されるため、クライアント側でのデバッグが容易です。

## 7.4 この章のまとめ

- REST APIはHTTPベースでデバイスを制御するインターフェース
- FlaskでデバイスレジストリをWebエンドポイントとして公開
- MQTTとREST APIは同じレジストリを共有し、どちらからも制御可能
- 適切なエラーレスポンス（404, 400）がデバッグを容易にする
