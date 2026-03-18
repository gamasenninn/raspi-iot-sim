# 第4章 はじめてのGPIOプログラミング

この章では、仮想Raspberry Pi上で実際にPythonプログラムを書いて、LEDやボタン、サーボモーターなどのデバイスを制御します。

## 4.1 最初のプログラム — LED点滅

プログラミングの世界では、最初に「Hello, World!」を表示するのが伝統です。ハードウェアの世界では、最初に「LEDを点滅させる」のが伝統です。これを通称「Lチカ」（LEDチカチカ）と呼びます。

### プログラムの作成

以下のプログラムをWindowsホスト側で `C:\app\RASPI\app\demo_led_blink.py` として保存します。

```python
"""LED点滅デモ - 赤LEDを5回点滅させる"""
import os
import time

# MockFactoryを使用する設定
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, LED
from gpiozero.pins.mock import MockFactory, MockPWMPin

# MockPWMPinで初期化（PWMデバイスも使えるようにする）
Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# GPIO 17番ピンにLEDを接続
led = LED(17)

print("GPIO 17 に接続された赤LEDを5回点滅します")

for i in range(5):
    led.on()    # LEDを点灯
    print(f"  [{i+1}/5] ON  (is_lit={led.is_lit})")
    time.sleep(0.5)  # 0.5秒待つ

    led.off()   # LEDを消灯
    print(f"  [{i+1}/5] OFF (is_lit={led.is_lit})")
    time.sleep(0.5)

print("完了!")
```

### プログラムの解説

**1行目〜6行目: 初期設定**

```python
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
```

環境変数を設定して、gpiozeroにMockFactoryを使用することを伝えます。

**8行目〜12行目: MockFactoryの初期化**

```python
from gpiozero import Device, LED
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)
```

gpiozeroのグローバル設定として、MockPWMPinを使用するMockFactoryを登録します。以降作成されるすべてのデバイスがこのファクトリを使用します。

**14行目: LEDの作成**

```python
led = LED(17)
```

GPIO 17番ピンにLEDを接続します。実機では物理的にLEDと抵抗をGPIO 17番ピンに接続しますが、仮想環境ではメモリ上に仮想的なLEDが作成されます。

**16行目〜23行目: 点滅ループ**

```python
led.on()           # LEDを点灯
print(led.is_lit)  # True — LEDが光っているかどうか
led.off()          # LEDを消灯
print(led.is_lit)  # False
```

### 実行方法

仮想Raspberry Piにファイルを転送して実行します。

**Windows PowerShellで：**

```powershell
scp -o StrictHostKeyChecking=no -P 2222 C:\app\RASPI\app\demo_led_blink.py root@localhost:/opt/iot-app/
```

**仮想Raspberry Pi（SSH）で：**

```bash
cd /opt/iot-app && ./venv/bin/python demo_led_blink.py
```

### 実行結果

```
GPIO 17 に接続された赤LEDを5回点滅します
  [1/5] ON  (is_lit=True)
  [1/5] OFF (is_lit=False)
  [2/5] ON  (is_lit=True)
  [2/5] OFF (is_lit=False)
  [3/5] ON  (is_lit=True)
  [3/5] OFF (is_lit=False)
  [4/5] ON  (is_lit=True)
  [4/5] OFF (is_lit=False)
  [5/5] ON  (is_lit=True)
  [5/5] OFF (is_lit=False)
完了!
```

`is_lit` が `True` と `False` で交互に切り替わっていることが確認できます。実機であれば、LEDが0.5秒間隔で光ったり消えたりします。

## 4.2 PWM LED — 明るさを制御する

デジタルLEDは「点灯」と「消灯」の2状態しかありません。明るさを段階的に変えたい場合は、PWM（Pulse Width Modulation：パルス幅変調）を使用します。

### PWMの仕組み

PWMは、非常に高速でON/OFFを繰り返すことで、見かけ上の明るさを制御する技術です。

```
明るさ 100%: ████████████████████  (常にON)
明るさ  75%: ███████████████░░░░░  (75%の時間ON)
明るさ  50%: ██████████░░░░░░░░░░  (50%の時間ON)
明るさ  25%: █████░░░░░░░░░░░░░░░  (25%の時間ON)
明るさ   0%: ░░░░░░░░░░░░░░░░░░░░  (常にOFF)
```

ONの時間の割合を「デューティ比」と呼びます。

### プログラム

```python
"""PWM LEDデモ - LEDの明るさを段階的に変化させる"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, PWMLED
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

led = PWMLED(18)  # GPIO 18番ピンにPWM LEDを接続

print("PWM LED 明るさ制御デモ")

# 0%から100%まで段階的に明るくする
for brightness in [0, 0.1, 0.25, 0.5, 0.75, 1.0]:
    led.value = brightness
    print(f"  明るさ: {brightness:>5.0%}  (value={led.value})")
    time.sleep(0.3)

# パルス（ゆっくり明滅）
print("\n  パルス開始...")
led.pulse()
time.sleep(0.5)

led.off()
print("完了!")
```

### 重要なポイント

```python
led.value = 0.5  # 50%の明るさに設定
```

`PWMLED.value` は 0.0（消灯）〜 1.0（最大輝度）の浮動小数点数です。

## 4.3 RGB LED — フルカラー制御

RGB LEDは、赤（Red）・緑（Green）・青（Blue）の3つのLEDが1つのパッケージに収められたデバイスです。3色の混合比を変えることで、理論上1677万色（256^3）を表現できます。

### 色の作り方

```
赤   = (1, 0, 0)    # 赤だけ最大
緑   = (0, 1, 0)    # 緑だけ最大
青   = (0, 0, 1)    # 青だけ最大
黄   = (1, 1, 0)    # 赤+緑
シアン = (0, 1, 1)   # 緑+青
マゼンタ = (1, 0, 1)  # 赤+青
白   = (1, 1, 1)    # 全色最大
消灯 = (0, 0, 0)    # 全色OFF
```

### プログラム

```python
"""RGB LEDデモ"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, RGBLED
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# 3つのGPIOピンにRGB LEDを接続
rgb = RGBLED(red=22, green=23, blue=24)

colors = [
    ("赤",      (1, 0, 0)),
    ("緑",      (0, 1, 0)),
    ("青",      (0, 0, 1)),
    ("暖色白",  (1, 0.9, 0.7)),
    ("紫",      (0.5, 0, 0.8)),
]

for name, color in colors:
    rgb.color = color
    r, g, b = rgb.value
    print(f"  {name:6s}: R={r:.1f} G={g:.1f} B={b:.1f}")
    time.sleep(0.3)

rgb.off()
```

## 4.4 ボタン入力

ボタンは最も基本的な入力デバイスです。ユーザーの操作を検出します。

### ポーリング方式とコールバック方式

ボタンの状態を読み取る方法は2つあります。

**ポーリング方式（状態を繰り返し確認する）**

```python
while True:
    if btn.is_pressed:
        print("押された!")
    time.sleep(0.1)
```

**コールバック方式（押されたときに自動で関数が呼ばれる）**

```python
def on_press():
    print("押された!")

btn.when_pressed = on_press
```

コールバック方式のほうが効率的で、リアルタイム性も高いため、一般的に推奨されます。

### ボタンプログラム

```python
"""ボタン入力デモ"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, Button, LED
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

btn = Button(16, pull_up=True)
led = LED(17)

# コールバック設定
press_count = 0

def on_press():
    global press_count
    press_count += 1
    led.toggle()
    print(f"  ボタン押下 #{press_count} → LED={led.is_lit}")

btn.when_pressed = on_press

# ボタン押下をシミュレーション
print("ボタン押下シミュレーション:")
for i in range(5):
    btn.pin.drive_low()   # 押す
    time.sleep(0.1)
    btn.pin.drive_high()  # 離す
    time.sleep(0.3)

print(f"\n合計 {press_count} 回押されました")
```

## 4.5 サーボモーター

サーボモーターは、指定した角度に正確に回転するモーターです。ドアロック、ロボットアーム、カメラの首振りなどに使用されます。

### サーボの制御値

| メソッド | 値 | 角度（一般的なサーボ） |
|---------|-----|---------------------|
| `servo.min()` | -1.0 | 0° |
| `servo.mid()` | 0.0 | 90° |
| `servo.max()` | 1.0 | 180° |

### プログラム

```python
"""サーボモーターデモ"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, Servo
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

servo = Servo(13)

print("サーボモーター制御デモ")

positions = [
    ("最小 (0°)",   "min"),
    ("中間 (90°)",  "mid"),
    ("最大 (180°)", "max"),
]

for name, method in positions:
    getattr(servo, method)()
    print(f"  {name:15s} → value={servo.value:+.1f}")
    time.sleep(0.5)

# 細かい角度制御
print("\n段階的に回転:")
for v in [-1.0, -0.5, 0.0, 0.5, 1.0]:
    servo.value = v
    print(f"  value={v:+.1f}")
    time.sleep(0.3)
```

## 4.6 DCモーター

DCモーター（直流モーター）は、前進・後退・速度制御ができるモーターです。車輪の駆動やポンプの制御に使用されます。

### gpiozeroのMotorクラス

```python
motor = Motor(forward=5, backward=6)  # 2つのGPIOピンを使用

motor.forward()      # 前進（全速）
motor.forward(0.5)   # 前進（50%速度）
motor.backward()     # 後退（全速）
motor.stop()         # 停止
```

`motor.value` は -1.0（全速後退）〜 0.0（停止）〜 1.0（全速前進）の値を取ります。

### プログラム

```python
"""DCモーターデモ"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, Motor
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

motor = Motor(forward=5, backward=6)

operations = [
    ("前進 100%",  lambda: motor.forward()),
    ("前進  50%",  lambda: motor.forward(0.5)),
    ("停止",       lambda: motor.stop()),
    ("後退  70%",  lambda: motor.backward(0.7)),
    ("停止",       lambda: motor.stop()),
]

print("DCモーター制御デモ")
for name, action in operations:
    action()
    print(f"  {name:10s} → speed={motor.value:+.2f}")
    time.sleep(0.3)
```

## 4.7 ブザー

ブザーは音を出すデバイスです。アラーム、通知音、メロディの再生に使用されます。

```python
"""ブザーデモ"""
import os, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"

from gpiozero import Device, Buzzer
from gpiozero.pins.mock import MockFactory, MockPWMPin

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

buzzer = Buzzer(25)

print("ブザーデモ")
buzzer.on()
print(f"  ON  (is_active={buzzer.is_active})")
time.sleep(0.5)

buzzer.off()
print(f"  OFF (is_active={buzzer.is_active})")

# beep: 一定間隔で鳴る
print("  ビープ開始...")
buzzer.beep(on_time=0.1, off_time=0.1, n=3)
time.sleep(1)
print("完了!")
```

## 4.8 全デバイスの一括管理 — デバイスファクトリ

ここまで個別のデバイスを見てきましたが、実際のIoTアプリケーションでは複数のデバイスをまとめて管理する必要があります。本書では「デバイスファクトリ」パターンを採用しています。

### デバイスファクトリの概念

```python
# devices/factory.py の概要

def create_all_devices():
    """全デバイスを生成してレジストリに登録"""
    registry = {}

    # 出力デバイス
    led = LED(17)
    registry["led_red"] = {
        "device": led,
        "type": "output",
        "category": "LED",
        "get_state": lambda: {"on": led.is_lit},
        "actions": {
            "on": lambda: led.on(),
            "off": lambda: led.off(),
            "toggle": lambda: led.toggle(),
        },
    }

    # ... 他のデバイスも同様に登録 ...

    return registry
```

各デバイスは以下の統一インターフェースで管理されます。

| キー | 型 | 説明 |
|------|-----|------|
| `device` | object | gpiozeroのデバイスオブジェクト |
| `type` | str | "output", "input", "sensor" |
| `category` | str | "LED", "Servo", "Sensor" 等 |
| `get_state` | callable | 現在の状態を辞書で返す |
| `actions` | dict | 実行可能な操作の辞書 |

この統一インターフェースにより、MQTT、REST API、WebSocketなどの通信プロトコルから、デバイスの種類を意識せずに制御できます。

## 4.9 この章のまとめ

この章では、以下のデバイスの制御方法を学びました。

| デバイス | クラス | 主な操作 |
|---------|--------|---------|
| LED | `LED` | on(), off(), toggle() |
| PWM LED | `PWMLED` | value = 0.0〜1.0 |
| RGB LED | `RGBLED` | color = (r, g, b) |
| ボタン | `Button` | is_pressed, when_pressed |
| サーボ | `Servo` | min(), mid(), max(), value |
| モーター | `Motor` | forward(), backward(), stop() |
| ブザー | `Buzzer` | on(), off(), beep() |

重要なポイント：
- MockPWMPinを使えば、すべてのデバイスが仮想環境で動作する
- 入力デバイスは `pin.drive_low()`/`pin.drive_high()` でシミュレーション
- コールバック（`when_pressed`）はMockFactoryでも正常動作する
- デバイスファクトリで統一的に管理すると、コードの見通しが良くなる

次の章では、温度や湿度などのセンサーを使ったデータ収集を学びます。
