# 第3章 仮想Raspberry Piの基礎知識

この章では、仮想Raspberry Piの内部構造と、GPIOシミュレーションの仕組みを解説します。

## 3.1 PI-CIの仕組み

PI-CIの内部では、以下のような多層構造でRaspberry Piがエミュレーションされています。

```
┌──────────────────────────────────────┐
│  Windows (ホストOS)                   │
│  ┌──────────────────────────────────┐│
│  │  Docker Desktop (WSL2)           ││
│  │  ┌──────────────────────────────┐││
│  │  │  PI-CIコンテナ (Ubuntu)      │││
│  │  │  ┌──────────────────────────┐│││
│  │  │  │  QEMU (qemu-system-     ││││
│  │  │  │        aarch64)          ││││
│  │  │  │  ┌──────────────────────┐││││
│  │  │  │  │  Raspberry Pi OS     │││││
│  │  │  │  │  (Debian Bookworm    │││││
│  │  │  │  │   ARM64)             │││││
│  │  │  │  │                      │││││
│  │  │  │  │  ← あなたのアプリは  │││││
│  │  │  │  │    ここで動く        │││││
│  │  │  │  └──────────────────────┘││││
│  │  │  └──────────────────────────┘│││
│  │  └──────────────────────────────┘││
│  └──────────────────────────────────┘│
└──────────────────────────────────────┘
```

**QEMU（キューエミュー）** は、あるCPUアーキテクチャを別のCPUアーキテクチャ上でエミュレーションするソフトウェアです。WindowsのPC（x86_64アーキテクチャ）上で、Raspberry PiのCPU（ARM64アーキテクチャ）を再現しています。

このため、仮想Raspberry Pi上で実行されるプログラムは実機の5〜20倍遅くなりますが、ARMの命令セットが正確に再現されるため、実機向けのバイナリがそのまま動作します。

## 3.2 GPIOとは

GPIO（General Purpose Input/Output）は、Raspberry Piの基板上にある汎用入出力ピンです。実機のRaspberry Piには40本のピンヘッダーがあり、そのうち26本がGPIOピンとして使用できます。

```
GPIO ピンヘッダー配置図（Raspberry Pi 4/5）

              3.3V [1]  [2]  5V
    (GPIO  2) SDA  [3]  [4]  5V
    (GPIO  3) SCL  [5]  [6]  GND
    (GPIO  4)      [7]  [8]  TXD  (GPIO 14)
              GND  [9]  [10] RXD  (GPIO 15)
    (GPIO 17)      [11] [12]      (GPIO 18)
    (GPIO 27)      [13] [14] GND
    (GPIO 22)      [15] [16]      (GPIO 23)
              3.3V [17] [18]      (GPIO 24)
    (GPIO 10) MOSI [19] [20] GND
    (GPIO  9) MISO [21] [22]      (GPIO 25)
    (GPIO 11) SCLK [23] [24]      (GPIO  8)
              GND  [25] [26]      (GPIO  7)
    (GPIO  0)      [27] [28]      (GPIO  1)
    (GPIO  5)      [29] [30] GND
    (GPIO  6)      [31] [32]      (GPIO 12)
    (GPIO 13)      [33] [34] GND
    (GPIO 19)      [35] [36]      (GPIO 16)
    (GPIO 26)      [37] [38]      (GPIO 20)
              GND  [39] [40]      (GPIO 21)
```

各ピンは「デジタル出力」「デジタル入力」「PWM出力」などの機能を持ち、電子部品と接続することで様々な制御が可能になります。

### GPIOの基本機能

| モード | 説明 | 使用例 |
|--------|------|--------|
| デジタル出力 | ピンの電圧をHIGH(3.3V)またはLOW(0V)に設定 | LED点灯/消灯 |
| デジタル入力 | ピンの電圧がHIGHかLOWかを読み取る | ボタンの押下検出 |
| PWM出力 | ピンの電圧をパルス幅変調で制御 | LEDの明るさ調整、サーボ角度 |
| I2C通信 | 2本の線でデバイスとデータ通信 | 温度センサー、ディスプレイ |
| SPI通信 | 4本の線で高速データ通信 | ADコンバータ |

## 3.3 gpiozeroライブラリ

`gpiozero` はRaspberry Pi公式のPythonライブラリで、GPIOを直感的に操作できます。

### 従来の方法（RPi.GPIO）

```python
# 従来のGPIOライブラリ（低レベル）
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BCM)
GPIO.setup(17, GPIO.OUT)
GPIO.output(17, GPIO.HIGH)  # LED点灯
GPIO.output(17, GPIO.LOW)   # LED消灯
GPIO.cleanup()
```

### gpiozeroの方法

```python
# gpiozero（高レベル）
from gpiozero import LED
led = LED(17)
led.on()   # LED点灯
led.off()  # LED消灯
```

gpiozeroは「何をしたいか」を直接書けるため、コードが格段にわかりやすくなります。

## 3.4 MockFactory — GPIOシミュレーションの心臓部

gpiozeroには「ピンファクトリ」という仕組みがあり、実際のGPIOハードウェアの代わりにソフトウェアでピンを模倣する「MockFactory」が提供されています。

### MockFactoryの仕組み

```
実機の場合：
  gpiozero → RPiGPIOFactory → 物理GPIOピン → LED点灯

仮想環境の場合：
  gpiozero → MockFactory → メモリ上の仮想ピン → 状態変更のみ
```

MockFactoryを使うと、物理的なGPIOハードウェアがなくても、gpiozeroのすべてのAPIが正常に動作します。

### 2種類のMockPin

| クラス | 特徴 | 対応デバイス |
|--------|------|------------|
| MockPin | デジタルのON/OFFのみ | LED, Button, Buzzer |
| MockPWMPin | PWM（パルス幅変調）対応 | PWMLED, RGBLED, Servo, Motor |

**本書ではMockPWMPinを使用します。** MockPWMPinはMockPinのスーパーセットなので、デジタルデバイスも含めてすべてのデバイスに対応できます。

### MockFactoryの初期化方法

```python
import os
from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin

# 方法1: 環境変数で設定（プログラム起動前に設定する必要がある）
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

# 方法2: Pythonコードで明示的に設定（推奨）
Device.pin_factory = MockFactory(pin_class=MockPWMPin)
```

方法2を推奨する理由は、MockPWMPinを明示的に指定できるためです。環境変数だけの場合、デフォルトのMockPin（PWM非対応）が使われ、サーボやPWM LEDでエラーが発生します。

## 3.5 入力デバイスのシミュレーション

出力デバイス（LED等）は状態の読み取りだけでシミュレーションできますが、入力デバイス（ボタン等）は「外部からの入力」をシミュレーションする必要があります。

MockFactoryでは、`pin.drive_low()` と `pin.drive_high()` を使って物理的な入力を模倣します。

### ボタンの場合

```python
from gpiozero import Button

btn = Button(16, pull_up=True)

# ボタンが押されたことをシミュレーション
btn.pin.drive_low()    # pull_up=Trueの場合、LOWが「押された」状態
print(btn.is_pressed)  # True

# ボタンが離されたことをシミュレーション
btn.pin.drive_high()   # HIGHが「離された」状態
print(btn.is_pressed)  # False
```

### なぜdrive_low()が「押された」なのか

これは「プルアップ抵抗」という電気回路の仕組みに関係しています。

```
プルアップ回路：
  3.3V ──[抵抗]──┬── GPIOピン
                  │
              [ボタン]
                  │
  GND ────────────┘

ボタンを押さないとき → GPIOピンは3.3V（HIGH）
ボタンを押したとき   → GPIOピンはGND（LOW）
```

つまり、プルアップ回路ではボタンを押すと電圧がLOWになります。`pull_up=True` と設定したボタンでは、`drive_low()` が「押す」操作に対応します。

## 3.6 ソフトウェアセンサー

温度センサーや気圧センサーなど、I2CやSPIで接続するセンサーは、GPIOピンとは異なるインターフェースで動作します。これらは MockFactory ではシミュレーションが難しいため、本書ではPythonクラスとしてソフトウェアでシミュレーションします。

### シミュレーションセンサーの設計

各センサーは以下の特性を持ちます。

| センサー | 初期値 | 変動パターン | 有効範囲 |
|---------|--------|------------|---------|
| DHT22 温度 | 22.0°C | ランダムウォーク | -10〜50°C |
| DHT22 湿度 | 55.0% | ランダムウォーク | 0〜100% |
| BMP280 気圧 | 1013.25hPa | サイン波+ノイズ | — |
| BH1750 照度 | 300 lux | 昼夜サイクル | 0以上 |
| HC-SR04 距離 | 100cm | のこぎり波 | 2〜400cm |
| 土壌水分 | 70% | 徐々に減少→自動水やり | 0〜100% |

### ランダムウォークとは

ランダムウォークは、現在の値からランダムな方向に少しずつ動く変動パターンです。実際のセンサー値に近い自然な変動を再現できます。

```python
import random

class DHT22Temp:
    def __init__(self):
        self._value = 22.0  # 初期値

    def update(self):
        # ガウス分布に従うランダムな変化量を加算
        self._value += random.gauss(0, 0.3)  # 平均0、標準偏差0.3
        # 有効範囲に制限
        self._value = max(-10, min(50, self._value))
```

`random.gauss(0, 0.3)` は「平均0、標準偏差0.3のガウス分布（正規分布）」からランダムな値を生成します。これにより、値は少しずつ上下に揺れながらドリフトしていきます。

## 3.7 ピンマップの設計

実機でもシミュレーションでも、どのGPIOピンにどのデバイスを接続するかを定義する「ピンマップ」が必要です。

本書では以下のピン割り当てを使用します。

```python
# config/pin_map.py

# === 出力デバイス ===
LED_RED = 17        # 赤色LED
LED_PWM = 18        # PWM調光LED
RGBLED_RED = 22     # RGB LEDの赤チャンネル
RGBLED_GREEN = 23   # RGB LEDの緑チャンネル
RGBLED_BLUE = 24    # RGB LEDの青チャンネル
BUZZER = 25         # ブザー
SERVO = 13          # サーボモーター
MOTOR_FWD = 5       # DCモーター前進
MOTOR_BWD = 6       # DCモーター後退

# === 入力デバイス ===
BUTTON = 16         # 押しボタン
MOTION_SENSOR = 20  # モーションセンサー
LINE_SENSOR = 21    # ラインセンサー
```

ピンマップを別ファイルに分離する利点：
- 実機に移行する際、このファイルだけを変更すればよい
- 配線の全体像が一目でわかる
- 同じピンを2つのデバイスに割り当てるミスを防止できる

## 3.8 プロジェクト構成

本書で使用するプロジェクトの全体構成を確認しましょう。

```
C:\app\RASPI\
├── docker-compose.yml           # Docker定義
├── mosquitto/config/            # MQTT設定
│   └── mosquitto.conf
├── dist/                        # 仮想Piディスクイメージ（自動生成）
│   ├── distro.qcow2
│   └── kernel.img
├── app/                         # IoTアプリケーション
│   ├── main.py                  # エントリポイント
│   ├── requirements.txt         # Pythonパッケージ一覧
│   ├── config/
│   │   ├── settings.py          # アプリ設定
│   │   └── pin_map.py           # ピン割り当て
│   ├── devices/
│   │   ├── factory.py           # デバイスファクトリ
│   │   ├── outputs.py           # 出力デバイス定義
│   │   ├── inputs.py            # 入力デバイス定義
│   │   └── sensors.py           # ソフトウェアセンサー
│   ├── simulation/
│   │   └── engine.py            # シミュレーションエンジン
│   └── protocols/
│       ├── mqtt_client.py       # MQTT通信
│       ├── rest_api.py          # REST API
│       └── websocket_server.py  # WebSocket
├── dashboard/
│   └── index.html               # Webダッシュボード
├── tests/                       # テストスイート
└── book/                        # 本書のドキュメント
```

## 3.9 実機との違いと注意点

仮想環境と実機には、いくつかの重要な違いがあります。

| 項目 | 仮想環境 | 実機 |
|------|---------|------|
| GPIO電圧 | なし（状態のみ） | 実際に3.3V/0Vが出力される |
| 処理速度 | x86→ARM変換で遅い | ネイティブ速度 |
| 割り込み | タイミングが不正確 | マイクロ秒単位で正確 |
| I2C/SPI | ソフトウェア模倣 | ハードウェアバス |
| カメラ | 非対応 | CSIインターフェースで接続 |
| Wi-Fi/Bluetooth | コンテナネットワーク | 内蔵無線モジュール |

これらの違いは、制御ロジックの開発には影響しませんが、ハードウェア固有のタイミングに依存するコードは実機での追加テストが必要です。

## 3.10 この章のまとめ

この章では、以下の概念を学びました。

- PI-CIはQEMUを使ってARM64のRaspberry Pi OSを完全にエミュレーションする
- GPIOは汎用入出力ピンで、電子部品の制御に使用する
- gpiozeroはRaspberry Pi公式の高レベルGPIOライブラリ
- MockFactory（MockPWMPin）を使うと、実機なしでGPIOをシミュレーション可能
- 入力デバイスは `pin.drive_low()` / `pin.drive_high()` でシミュレーション
- I2C/SPIセンサーはソフトウェアクラスでシミュレーション

次の章では、実際にプログラムを書いてLEDを点滅させてみましょう。
