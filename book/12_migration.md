# 第12章 実機への移行ガイド

この章では、仮想環境で開発・テストしたIoTアプリケーションを、実際のRaspberry Piに移植する手順を解説します。

## 12.1 移行の基本方針

本書のアプリケーションは、**最小限の変更で実機に移植できる** ように設計されています。

変更が必要な箇所は以下の3点のみです。

1. **MockFactoryの無効化** — 環境変数を削除するだけ
2. **ピンマップの調整** — 実際の配線に合わせる
3. **ソフトウェアセンサーの置き換え** — 実センサードライバーに差し替え

## 12.2 ステップ1: MockFactoryの無効化

### 変更箇所

`app/main.py` の以下の行を削除またはコメントアウトします。

```python
# 削除する行:
os.environ.setdefault("GPIOZERO_PIN_FACTORY", "mock")
```

`app/devices/factory.py` の `init_mock_factory()` も修正します。

```python
def init_mock_factory():
    # 環境変数が"mock"のときだけMockFactoryを使う
    # 実機では環境変数を設定しないので、自動的に実GPIOが使われる
    if os.environ.get("GPIOZERO_PIN_FACTORY") == "mock":
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        print("[Factory] MockFactory を使用")
    else:
        print("[Factory] 実機GPIOを使用")
```

gpiozeroは環境変数 `GPIOZERO_PIN_FACTORY` が設定されていない場合、自動的に実機のピンファクトリ（`RPiGPIOFactory` または `PiGPIOFactory`）を使用します。

## 12.3 ステップ2: ピンマップの調整

`config/pin_map.py` を実際の配線に合わせて修正します。

```python
# 実機の配線例
LED_RED = 17        # GPIO 17にLEDを接続
LED_PWM = 18        # GPIO 18（PWM対応）にPWM LEDを接続
SERVO = 12          # GPIO 12（PWM対応）にサーボを接続
# ... 配線に合わせて変更
```

> **Note:** サーボやPWM LEDには、ハードウェアPWMに対応したGPIOピン（GPIO 12, 13, 18, 19）を使用することを推奨します。

## 12.4 ステップ3: 実センサードライバーの導入

ソフトウェアシミュレーションセンサーを、実際のセンサードライバーに差し替えます。

### DHT22（温湿度）

```bash
pip install adafruit-circuitpython-dht
sudo apt install libgpiod2
```

```python
import adafruit_dht
import board

dht = adafruit_dht.DHT22(board.D4)

temperature = dht.temperature  # 温度（°C）
humidity = dht.humidity        # 湿度（%）
```

### BMP280（気圧）

```bash
pip install adafruit-circuitpython-bmp280
```

```python
import adafruit_bmp280
import board, busio

i2c = busio.I2C(board.SCL, board.SDA)
bmp = adafruit_bmp280.Adafruit_BMP280_I2C(i2c)

pressure = bmp.pressure      # 気圧（hPa）
temperature = bmp.temperature  # 温度（°C）
```

### HC-SR04（超音波距離）

gpiozeroに組み込みのクラスがあります。

```python
from gpiozero import DistanceSensor

sensor = DistanceSensor(echo=9, trigger=10)
distance_cm = sensor.distance * 100  # メートル→センチ
```

## 12.5 ステップ4: MQTTブローカーの設定

実機では、Mosquittoを同じRaspberry Pi上で動かすか、ネットワーク上の別のサーバーを使用します。

### 同じPi上でMosquittoを動かす場合

```bash
sudo apt install mosquitto mosquitto-clients
sudo systemctl enable mosquitto
sudo systemctl start mosquitto
```

`config/settings.py` を修正：

```python
MQTT_BROKER = os.environ.get("MQTT_BROKER", "localhost")
```

### 外部のMQTTブローカーを使う場合

```python
MQTT_BROKER = os.environ.get("MQTT_BROKER", "192.168.1.100")
```

## 12.6 移行チェックリスト

| # | 項目 | 確認 |
|---|------|------|
| 1 | Raspberry Pi OSがインストール済み | □ |
| 2 | Python 3.11+がインストール済み | □ |
| 3 | 配線がpin_map.pyと一致している | □ |
| 4 | 環境変数GPIOZERO_PIN_FACTORYが未設定 | □ |
| 5 | 実センサードライバーがインストール済み | □ |
| 6 | MQTTブローカーが動作中 | □ |
| 7 | ユニットテスト（デバイス・センサー以外）がパス | □ |
| 8 | LEDの点灯テストが成功 | □ |
| 9 | センサーの読み取りテストが成功 | □ |
| 10 | MQTTテレメトリが配信されている | □ |

## 12.7 仮想環境と実機の併用

開発フローとして、以下のサイクルを推奨します。

```
仮想環境で開発 → ユニットテスト → 実機でテスト → 仮想環境に戻る
```

制御ロジックの開発やテストは仮想環境で行い、ハードウェア固有の調整（タイミング、ノイズ対策など）のみを実機で行います。

## 12.8 この章のまとめ

- 移行に必要な変更は3点のみ（MockFactory無効化、ピンマップ、センサードライバー）
- gpiozeroの抽象化により、コードの大部分は変更不要
- 仮想環境と実機を併用する開発フローが最も効率的
