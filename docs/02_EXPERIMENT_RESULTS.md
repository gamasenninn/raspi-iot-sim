# 実験結果レポート

## 実験環境

- **ホストOS**: Windows 11 Home 10.0.26200
- **Docker**: Docker Desktop 20.10.17 (WSL2バックエンド)
- **PI-CI**: ptrsr/pi-ci:latest
- **ゲストOS**: Debian GNU/Linux 12 (bookworm) — Raspberry Pi OS 64-bit ARM64
- **Python**: 3.11 (Pi VM内)
- **gpiozero**: 2.0+
- **MQTTブローカー**: Eclipse Mosquitto 2.1.2
- **実施日**: 2026-03-17

---

## 実験1: LED点滅 (`demo_led_blink.py`)

### 目的
gpiozero MockFactory で LED の ON/OFF が正しくシミュレーションできるか確認。

### 手法
```python
from gpiozero import LED
led = LED(17)
led.on()   # → is_lit = True
led.off()  # → is_lit = False
```

5回の点滅ループを0.5秒間隔で実行。

### 結果
- **成功**: `is_lit` が正しく `True`/`False` に切り替わった
- 5回の点滅が全て正常に完了
- MockFactory では実際のGPIO電圧変化はないが、状態管理は完全に動作

### 知見
- `LED` クラスは `MockFactory` でそのまま動作する
- `os.environ["GPIOZERO_PIN_FACTORY"] = "mock"` だけでは不十分。`MockPWMPin` を使う場合は明示的に `Device.pin_factory = MockFactory(pin_class=MockPWMPin)` が必要
- 環境変数だけの場合、デフォルトの `MockPin` が使われ、PWM系デバイスでエラーになる

---

## 実験2: 温湿度モニター + 異常検知 (`demo_sensor_monitor.py`)

### 目的
ソフトウェアシミュレーションセンサーの値変動を確認し、しきい値ベースの判定ロジックをテスト。

### 手法
- DHT22(温度/湿度)、BMP280(気圧) のシミュレーションセンサーを10回計測
- 温度>24°C or 湿度>80% で LED+ブザー警告
- PWM LED の明るさを温度に比例させる

### 結果
- **成功**: 10回の計測すべて正常
- 温度: 21.44〜22.33°C の範囲でランダムウォーク（初期値22°C付近）
- 湿度: 54.18〜56.67%
- 気圧: 1012.97〜1014.33 hPa
- 今回は全て正常範囲内で警告は発生しなかった

### 知見
- **PWMSupportエラー**: `PWMLED` を使うには `MockPWMPin` が必須。通常の `MockPin` では `PinPWMUnsupported` エラーが発生する
- ソフトウェアセンサーのランダムウォークは `random.gauss(0, sigma)` で実現。sigma を調整することでセンサーの「ノイズ感」を制御できる
- 短時間（10サイクル）ではしきい値を超えにくい。長時間実行するとドリフトで警告が発生する設計

---

## 実験3: ボタン→RGB LED色切替 + MQTT通知 (`demo_button_rgb.py`)

### 目的
入力デバイス（ボタン）のシミュレーションと、RGB LED の色制御、MQTT配信の統合テスト。

### 手法
- `btn.pin.drive_low()` / `drive_high()` でボタン押下/解放をシミュレーション
- 8色パターンを順次切替
- 各色変更時に MQTT で `iot/demo/rgb_status` に JSON を配信

### 結果
- **成功**: 8色すべて正常に切替
- ボタンのpress/release シミュレーションが正常動作
- MQTT配信も全8回成功
- RGB LED の `red`, `green`, `blue` 各チャンネルが独立制御可能

### 知見
- **ボタンシミュレーションの方法**: `pull_up=True` の場合、`drive_low()` が「押下」、`drive_high()` が「解放」（Active Low）
- MQTT の日本語は `\uXXXX` でエスケープされるが、受信側で正しくデコードできる
- `RGBLED.color` はタプル `(r, g, b)` で設定。各値は0.0〜1.0

---

## 実験4: スマート農業 (`demo_smart_farm.py`)

### 目的
複数センサー＋アクチュエータの連携動作を統合テスト。土壌水分による自動灌漑と距離センサーによる侵入検知。

### 手法
- 土壌水分 < 40% → モーター(ポンプ)前進で灌漑開始
- 土壌水分 > 70% → モーター停止
- 距離 < 50cm → ブザー警報
- 全データを MQTT で配信

### 結果
- **成功**: 20サイクル完了
- 土壌水分: 70.0% → 68.9% に徐々に低下（灌漑しきい値40%には未到達）
- 距離: 3.2cm 〜 41.1cm（のこぎり波パターンで増加中）
- 全サイクルで侵入検知状態（< 50cm）
- モーターの `forward()`, `stop()` が正常動作

### 知見
- **距離センサーのパターン**: のこぎり波（60秒周期で2→400cm）のため、起動直後は必ず近距離値になる。実用では起動後の安定待ち時間を設ける必要がある
- **土壌水分の減少速度**: `random.uniform(0.01, 0.1)` は1サイクルあたり最大0.1%の減少。20サイクルでは約1%しか減少しない。長時間実行しないと灌漑トリガーがかからない
- モーターの `forward(0.8)` のように速度指定が可能

---

## 実験5: スマートドアロック (`demo_door_lock.py`)

### 目的
シナリオベースの複合デバイス制御。サーボによるロック機構、モーション検知、ボタン操作の統合。

### 手法
8段階のシナリオを順次実行:
1. 人が接近 → モーション検知 → 施錠中なので通知音
2. ボタン解錠 → サーボ max → LED ON
3. 自動施錠タイマー → サーボ min → LED OFF
4. 再度接近 → 通知音
5. 再度解錠
6. 解錠中に接近 → 通知なし
7. ボタン施錠
8. 不審な動き → 警報発動

### 結果
- **成功**: 全8シナリオが正常動作
- サーボ値: 施錠=-1.0 (min), 解錠=1.0 (max)
- モーションセンサーの `drive_high()`/`drive_low()` で検知/非検知を制御
- 施錠中のモーション検知時のみブザーが鳴る条件分岐が正常

### 知見
- **サーボの警告**: `PWMSoftwareFallback` 警告が出るが動作に影響なし。実機では `pigpio` ピンファクトリを使えば解消
- サーボの値範囲は -1.0（min）〜 1.0（max）。`mid()` で0.0（中間位置）
- シナリオベースのテストは IoT ロジックの検証に非常に有効

---

## メインアプリ (main.py) の動作確認

### テレメトリ配信
```json
{"device": "led_red", "type": "output", "category": "LED", "on": true, "timestamp": 1773685280.20}
{"device": "dht22_temperature", "type": "sensor", "category": "Sensor", "value": 22.62, "unit": "°C", "timestamp": 1773685280.23}
```

- 15デバイス全てが1秒間隔で MQTT 配信
- JSON 形式で `device`, `type`, `category`, 状態値, `timestamp` を含む

### コマンド受信
```json
// 送信: iot/devices/led_red/command
{"action": "on"}

// 結果: iot/devices/led_red/state
{"device": "led_red", "type": "output", "category": "LED", "on": true, ...}
```

- コマンド送信から状態反映まで約1秒以内
- PowerShell からの JSON 送信は `sh -c` 経由が確実

---

## 総合知見

### gpiozero MockFactory について

1. **MockPin vs MockPWMPin**: PWM を使うデバイス (PWMLED, RGBLED, Servo, Motor) には `MockPWMPin` が必須
2. **入力シミュレーション**: `device.pin.drive_low()` / `drive_high()` で物理的な入力を再現
3. **制限**: `LightSensor` (充放電タイミング依存) と `DistanceSensor` (トリガーピン依存) は MockFactory での動作が難しく、ソフトウェアセンサーで代替が現実的
4. **実機移行**: 環境変数 `GPIOZERO_PIN_FACTORY` を削除するだけで実機のピンファクトリに自動切替

### PI-CI + Docker について

1. **パフォーマンス**: QEMU の ARM→x86 変換により全体的に5〜20倍遅い。pip install は特に顕著
2. **ネットワーク**: Pi VM から Docker ネットワーク上の他コンテナには**ホスト名で直接アクセス可能**（`mosquitto` 等）。`10.0.2.2` は不安定
3. **ファイル転送**: `scp -P 2222` でホスト↔Pi VM 間のファイル転送が可能。共有フォルダは非対応
4. **永続性**: `dist/distro.qcow2` にディスク状態が保存される。再起動しても環境は維持される
5. **破損リスク**: 強制終了で qcow2 が破損する。必ず `shutdown now` で停止すること

### Windows 環境での注意点

1. **PowerShell を使う**: Git Bash はパス変換問題と TTY 問題がある
2. **JSON の送信**: PowerShell から docker exec 経由で JSON を送る場合、`sh -c` でラップし `\"` でエスケープする
3. **複数ターミナル**: 最低3つの PowerShell ウィンドウが必要（Pi VMコンソール、SSH、操作用）
