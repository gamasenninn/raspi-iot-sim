# 第5章 センサーを使ったデータ収集

この章では、温度・湿度・気圧・照度・距離・土壌水分の6種類のセンサーをシミュレーションし、データの収集・分析・異常検出を行います。

## 5.1 IoTにおけるセンサーの役割

IoTシステムにおいて、センサーは「目」と「耳」の役割を果たします。物理世界の状態をデジタルデータに変換し、コンピュータが処理できるようにします。

```
物理現象 → センサー → 電気信号 → ADC → デジタルデータ → 処理
  温度        DHT22     アナログ電圧   変換     22.5°C       判定
```

実際のセンサーはI2CやSPIなどの通信プロトコルでRaspberry Piと接続されますが、仮想環境ではPythonクラスとしてシミュレーションします。

## 5.2 6種類のシミュレーションセンサー

本書で使用するセンサーの一覧です。

| センサー | 型番 | 測定対象 | 通信方式 | 価格目安 |
|---------|------|---------|---------|---------|
| 温湿度センサー | DHT22 | 温度・湿度 | 独自1-wire | 500〜1,000円 |
| 気圧センサー | BMP280 | 気圧（高度） | I2C/SPI | 300〜800円 |
| 照度センサー | BH1750 | 明るさ | I2C | 200〜500円 |
| 超音波距離センサー | HC-SR04 | 距離 | GPIO(トリガー/エコー) | 200〜500円 |
| 土壌水分センサー | 汎用 | 土壌含水率 | アナログ(ADC経由) | 200〜500円 |

## 5.3 センサークラスの設計

すべてのセンサーは共通の基底クラスを継承します。

```python
class SimulatedSensor:
    """シミュレーションセンサーの基底クラス"""

    def __init__(self, name, unit):
        self.name = name      # センサー名
        self.unit = unit      # 単位
        self._value = 0.0     # 現在の値

    @property
    def value(self):
        """現在の値を取得（小数点2桁に丸める）"""
        return round(self._value, 2)

    @value.setter
    def value(self, v):
        """値を手動で設定（テスト用）"""
        self._value = v

    def update(self):
        """値を更新（サブクラスでオーバーライド）"""
        raise NotImplementedError
```

この設計のポイント：
- **`update()`** を呼ぶたびに値が更新される（ポーリングモデル）
- **`value`** プロパティで現在の値を取得できる
- **`value`** のsetterで手動設定も可能（テストやシナリオ制御用）
- `round(self._value, 2)` で表示用に丸める

## 5.4 温度センサー（DHT22）

DHT22は最もポピュラーなIoT温度センサーです。温度と湿度を同時に計測できます。

### シミュレーション方法: ランダムウォーク

```python
import random

class DHT22Temp(SimulatedSensor):
    def __init__(self):
        super().__init__("dht22_temperature", "°C")
        self._value = 22.0  # 室温程度から開始

    def update(self):
        # ガウス分布で微小変化を加算
        self._value += random.gauss(0, 0.3)
        # 物理的に妥当な範囲に制限
        self._value = max(-10, min(50, self._value))
```

`random.gauss(0, 0.3)` の意味：
- **平均 0**: 上にも下にも同じ確率で変化する
- **標準偏差 0.3**: 1回の更新で±0.3°C程度の変化が多い（68%の確率）

### 実行例

```
更新 1: 22.00°C
更新 2: 22.31°C   ← +0.31
更新 3: 22.18°C   ← -0.13
更新 4: 21.95°C   ← -0.23
更新 5: 22.08°C   ← +0.13
```

値が少しずつ揺れながら推移する様子は、実際の温度センサーの挙動に非常に近いものです。

## 5.5 気圧センサー（BMP280）

### シミュレーション方法: サイン波 + ノイズ

```python
import math

class BMP280Pressure(SimulatedSensor):
    def __init__(self):
        super().__init__("bmp280_pressure", "hPa")
        self._value = 1013.25  # 標準大気圧

    def update(self):
        elapsed = time.time() - self._start_time
        # 5分周期のサイン波（±5hPa）+ ランダムノイズ
        self._value = 1013.25 + 5.0 * math.sin(elapsed / 300) + random.gauss(0, 0.5)
```

気圧は天候の変化に伴いゆっくりと変動するため、サイン波（周期的な変動）にノイズを加えたモデルが適しています。

## 5.6 土壌水分センサー

### シミュレーション方法: 減少 + 自動回復

```python
class SoilMoisture(SimulatedSensor):
    def __init__(self):
        super().__init__("soil_moisture", "%")
        self._value = 70.0

    def update(self):
        # 徐々に乾燥（蒸発をシミュレーション）
        self._value -= random.uniform(0.01, 0.1)
        # 30%以下になったら自動水やり
        if self._value < 30:
            self._value = 80.0 + random.gauss(0, 5)
        self._value = max(0, min(100, self._value))
```

このセンサーは「時間とともに乾燥し、しきい値を下回ると灌漑される」という農業IoTの典型的なパターンをシミュレーションしています。

## 5.7 実践: 温湿度モニター

センサーの値を読み取り、しきい値を超えたらLEDとブザーで警告するプログラムを作ります。

```python
"""温湿度モニター - しきい値を超えたらLEDとブザーで警告"""
import os, sys, time
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device, LED, PWMLED, Buzzer
from gpiozero.pins.mock import MockFactory, MockPWMPin
from devices.sensors import DHT22Temp, DHT22Humidity, BMP280Pressure

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# デバイス
led_warn = LED(17)         # 警告LED
led_level = PWMLED(18)     # レベル表示LED
buzzer = Buzzer(25)        # ブザー

# センサー
temp = DHT22Temp()
humidity = DHT22Humidity()
pressure = BMP280Pressure()

# しきい値
TEMP_WARN = 24.0   # °C
HUMI_WARN = 80.0   # %

print("温湿度モニター (10回計測)")
print(f"警告: 温度>{TEMP_WARN}°C or 湿度>{HUMI_WARN}%")

for i in range(10):
    temp.update()
    humidity.update()
    pressure.update()

    alert = temp.value > TEMP_WARN or humidity.value > HUMI_WARN

    if alert:
        led_warn.on()
        buzzer.on()
        led_level.value = min(1.0, (temp.value - 20) / 10)
        status = "!! 警告 !!"
    else:
        led_warn.off()
        buzzer.off()
        led_level.value = 0
        status = "   正常   "

    print(f"[{i+1:2d}] {status} | "
          f"温度: {temp.value:6.2f}°C | "
          f"湿度: {humidity.value:6.2f}% | "
          f"気圧: {pressure.value:7.2f}hPa")

led_warn.off()
buzzer.off()
led_level.off()
print("計測完了。")
```

### 実行結果の例

```
温湿度モニター (10回計測)
警告: 温度>24.0°C or 湿度>80.0%
[ 1]    正常    | 温度:  21.78°C | 湿度:  55.43% | 気圧: 1013.90hPa
[ 2]    正常    | 温度:  22.09°C | 湿度:  54.18% | 気圧: 1012.97hPa
[ 3]    正常    | 温度:  22.02°C | 湿度:  54.44% | 気圧: 1013.93hPa
...
```

## 5.8 実践: データロガー + 統計分析

50回のサンプリングデータを収集し、統計分析と異常検出を行います。

### 統計指標

| 指標 | 意味 | 計算方法 |
|------|------|---------|
| 平均 (mean) | データの中心値 | 合計 ÷ 個数 |
| 標準偏差 (std) | データのばらつき | 分散の平方根 |
| 最小/最大 | データの範囲 | min/max関数 |
| レンジ | 変動幅 | 最大 - 最小 |

### 異常検出（2σルール）

統計的異常検出の基本的な手法として、「平均±2σ（標準偏差の2倍）」の範囲を逸脱した値を異常とみなします。

```
正規分布の場合：
  平均±1σ → 約68%のデータが含まれる
  平均±2σ → 約95%のデータが含まれる  ← この範囲外が異常
  平均±3σ → 約99.7%のデータが含まれる
```

### 実行結果の例

```
Statistical Analysis
=====================
  [temperature] (C)
    Mean:    22.38 | Std:     0.75
    Min:     21.26 | Max:    23.82
    Range:    2.56 | Samples: 50

Anomaly Detection (beyond mean +/- 2*std)
==========================================
  [humidity] 1 anomalies detected:
    Sample #12: 64.13 (HIGH)

  [pressure] 3 anomalies detected:
    Sample #17: 1012.22 (LOW)

  Total anomalies: 5
```

50サンプル×6センサー = 300データポイントから5件の異常を検出（1.67%）。正規分布の理論値（約5%）と比較して妥当な範囲です。

## 5.9 この章のまとめ

この章では以下を学びました。

- 6種類のセンサーのシミュレーション方法
  - ランダムウォーク（温度・湿度）
  - サイン波＋ノイズ（気圧・照度）
  - のこぎり波（距離）
  - 減少＋自動回復（土壌水分）
- センサー値に基づくしきい値判定と警告制御
- CSVファイルへのデータロギング
- 統計分析（平均・標準偏差・レンジ）
- 異常検出（2σルール）

次の章では、MQTT通信を使ってセンサーデータをネットワーク経由で配信する方法を学びます。
