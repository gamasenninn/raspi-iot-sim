# 第11章 テストで品質を保証する

この章では、IoTアプリケーションの自動テストを学びます。ユニットテスト、インテグレーションテスト、E2Eテストの3段階で品質を保証します。

## 11.1 なぜテストが必要か

IoTシステムは「物理世界に影響を与える」ソフトウェアです。バグがあると：

- 灌漑システムが止まらず水害になる
- ドアロックが解除されたままになる
- 温度警報が鳴らず設備が破損する

自動テストは、これらの問題をリリース前に検出する最も効果的な方法です。

## 11.2 テストピラミッド

```
          /\
         /  \      E2E テスト (5件)
        /    \     全スタックの統合動作
       /------\
      /        \   インテグレーションテスト (16件)
     /          \  REST API, MQTT通信
    /------------\
   /              \ ユニットテスト (42件)
  /                \ デバイス, センサー, メッセージ形式
 /──────────────────\
```

- **ユニットテスト**: 個々のコンポーネントを単独でテスト（高速、多数）
- **インテグレーションテスト**: 複数コンポーネントの連携をテスト
- **E2Eテスト**: 全システムの動作をテスト（低速、少数）

## 11.3 テスト環境のセットアップ

### 必要なパッケージ

```powershell
pip install pytest gpiozero paho-mqtt flask flask-socketio requests
```

### ディレクトリ構成

```
tests/
├── conftest.py              # 共通設定・フィクスチャ
├── test_devices.py          # Unit: デバイス (20件)
├── test_sensors.py          # Unit: センサー (13件)
├── test_mqtt_format.py      # Unit: メッセージ形式 (9件)
├── test_rest_api.py         # Integration: REST API (13件)
├── test_mqtt_integration.py # Integration: MQTT通信 (3件)
└── test_e2e.py              # E2E: 全フロー (5件)
```

### conftest.py — テストの共通設定

```python
import os, sys, pytest

os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "app"))

@pytest.fixture
def registry():
    """テストごとに新しいデバイスレジストリを生成"""
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
```

`@pytest.fixture` はテスト関数に自動的に注入される共有オブジェクトです。`registry` フィクスチャを引数に指定するだけで、テストごとに新しいデバイスレジストリが作成されます。

## 11.4 ユニットテスト

### デバイステスト

```python
class TestLED:
    def test_led_on_off(self, registry):
        led = registry["led_red"]
        led["actions"]["on"]()
        assert led["get_state"]()["on"] is True

        led["actions"]["off"]()
        assert led["get_state"]()["on"] is False

    def test_led_toggle(self, registry):
        led = registry["led_red"]
        led["actions"]["off"]()
        led["actions"]["toggle"]()
        assert led["get_state"]()["on"] is True
```

`assert` は「この条件が真であること」を検証します。偽の場合、テストが失敗します。

### センサーテスト

```python
class TestDHT22Temperature:
    def test_stays_in_range(self):
        s = DHT22Temp()
        for _ in range(1000):
            s.update()
        assert -10 <= s.value <= 50

class TestSoilMoisture:
    def test_auto_rewater(self):
        s = SoilMoisture()
        s.value = 25.0  # 強制的に低くする
        s.update()
        assert s.value > 70.0  # 自動水やりで回復
```

## 11.5 インテグレーションテスト

### REST API テスト

FlaskのテストクライアントはHTTPサーバーを起動せずにAPIをテストできます。

```python
class TestDeviceAction:
    def test_led_on(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "on"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["state"]["on"] is True

    def test_invalid_action_returns_400(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "fly"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        assert "available" in resp.get_json()
```

### MQTT通信テスト

```python
def test_publish_and_subscribe(self):
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

    assert len(received) == 1
    assert received[0]["msg"] == "hello"
```

## 11.6 E2Eテスト

E2Eテストは、実際のMQTTメッセージを使って「コマンド送信→デバイス状態変化→テレメトリ確認」の全フローを検証します。

```python
def test_led_on_command_changes_state(self):
    send_command("led_red", "on")
    data = wait_for_state(
        "iot/devices/led_red/state",
        lambda d: d.get("on") is True,
    )
    assert data is not None
    assert data["on"] is True
```

### 自動スキップ

E2Eテストは全スタック（Pi VM + Mosquitto）が稼働中でないと実行できません。`conftest.py` で稼働チェックを行い、未稼働時は自動的にスキップします。

## 11.7 テストの実行

```powershell
cd C:\app\RASPI

# ユニットテストのみ（インフラ不要、数秒で完了）
python -m pytest tests/test_devices.py tests/test_sensors.py -v

# 全テスト
python -m pytest tests/ -v
```

### 全テスト結果

```
66 passed, 0 failed in 44.33s
```

| テストファイル | テスト数 | 結果 |
|---------------|---------|------|
| test_devices.py | 20 | 20 passed |
| test_sensors.py | 13 | 13 passed |
| test_mqtt_format.py | 9 | 9 passed |
| test_rest_api.py | 13 | 13 passed |
| test_mqtt_integration.py | 3 | 3 passed |
| test_e2e.py | 5 | 5 passed |

## 11.8 この章のまとめ

- テストピラミッド: Unit → Integration → E2E の3段階
- pytestのフィクスチャでテストの共通設定を管理
- MockFactoryのおかげで、ユニットテストは実機なしで実行可能
- FlaskテストクライアントでHTTPサーバーなしにAPIテスト
- E2Eテストは全スタック稼働時のみ実行、未稼働時は自動スキップ
