# Raspberry Pi IoT シミュレーション開発環境

PI-CI (QEMU) による仮想Raspberry Pi OS + gpiozero MockFactory によるGPIOシミュレーション環境。
実機なしでIoTアプリの開発・テストが可能。

## ドキュメント

- **[書籍: 仮想環境で学ぶ Raspberry Pi IoT開発 実践ガイド](book/TABLE_OF_CONTENTS.md)** — 全12章+付録の入門書
- **[セットアップマニュアル](docs/01_SETUP_MANUAL.md)** — 環境構築の全手順
- **[実験結果レポート](docs/02_EXPERIMENT_RESULTS.md)** — 基本実験の結果と知見
- **[追加実験レポート](docs/03_ADVANCED_EXPERIMENTS.md)** — REST API、スマートホーム、エコシステム、データロガー
- **[設計パターン](docs/04_STATE_MACHINE_AND_PATTERNS.md)** — ステートマシン、IoT設計パターン集
- **[ダッシュボード & テスト](docs/05_DASHBOARD_AND_TESTING.md)** — Webダッシュボード使用法 + テスト結果

## アーキテクチャ

```
┌──────────────────────────────────────────────────┐
│  Docker Compose (iot-net)                        │
│                                                  │
│  ┌───────────────┐    ┌───────────────────────┐  │
│  │  Mosquitto    │    │  PI-CI (raspi)        │  │
│  │  MQTT Broker  │◄───│  ┌─────────────────┐  │  │
│  │  :1883 (MQTT) │    │  │ QEMU            │  │  │
│  │  :9001 (WS)   │    │  │ Raspberry Pi OS │  │  │
│  └───────────────┘    │  │                  │  │  │
│                       │  │ IoTアプリ (Python)│  │  │
│  ┌───────────────┐    │  │  - MockFactory   │  │  │
│  │  ブラウザ      │    │  │  - MQTT Client  │  │  │
│  │  ダッシュボード │    │  │  - REST API     │  │  │
│  │  (WS:9001)    │    │  │  - WebSocket    │  │  │
│  └───────────────┘    │  └─────────────────┘  │  │
│                       │  SSH :2222            │  │
│                       └───────────────────────┘  │
└──────────────────────────────────────────────────┘
```

Pi VM から MQTT ブローカーへはホスト名 `mosquitto` で接続する。

## プロジェクト構成

```
RASPI/
├── docker-compose.yml           # PI-CI + Mosquitto
├── start.ps1                    # 環境起動 (PowerShell)
├── provision.ps1                # アプリ転送+セットアップ (PowerShell)
├── stop.ps1                     # 安全停止 (PowerShell)
├── mosquitto/config/            # MQTTブローカー設定
├── dist/                        # (自動生成) Pi VMディスクイメージ
├── app/                         # IoTアプリケーション
│   ├── main.py                  # エントリポイント
│   ├── requirements.txt         # Python依存パッケージ
│   ├── config/                  # 設定・ピン割り当て
│   ├── devices/                 # デバイス定義 (15種)
│   ├── simulation/              # シミュレーションエンジン
│   ├── protocols/               # MQTT, REST API, WebSocket
│   └── demo_*.py                # デモプログラム (10本)
├── dashboard/
│   └── index.html               # Webダッシュボード (MQTT.js + Chart.js)
├── tests/                       # テストスイート (66件)
└── book/                        # 書籍 (全12章+付録)
```

## クイックスタート

### 前提条件

- Docker Desktop (WSL2バックエンド推奨、メモリ6GB以上)
- Python 3.11+
- PowerShell

### 初回セットアップ

```powershell
cd C:\app\RASPI

# ウィンドウ1: 環境起動 (初回はPI-CI初期化+ディスク拡張も行う)
.\start.ps1

# ウィンドウ2: アプリ転送+Python環境セットアップ (Pi VM起動を自動待機)
.\provision.ps1

# ウィンドウ3: アプリ起動
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

### 2回目以降

```powershell
.\start.ps1    # ウィンドウ1

# ウィンドウ2:
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

### 停止

```powershell
.\stop.ps1
```

> **Warning**: Pi VM を強制終了 (`docker kill`, `Ctrl+C`) すると `dist/distro.qcow2` が破損する。必ず `stop.ps1` で停止すること。

## デバイス操作

### MQTT テレメトリ監視

```powershell
docker exec mosquitto mosquitto_sub -t "iot/devices/#" -C 5
```

### MQTT コマンド送信

```powershell
# LED ON
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/led_red/command' -m '{\"action\":\"on\"}'"

# サーボ位置設定
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/servo/command' -m '{\"action\":\"set\",\"value\":\"0.5\"}'"

# モーター前進
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/motor/command' -m '{\"action\":\"forward\"}'"
```

### Webダッシュボード

```powershell
start .\dashboard\index.html
```

ブラウザで15デバイスのリアルタイム監視・操作が可能。Mosquitto の WebSocket (port 9001) に直接接続。

## デバイス一覧 (15種)

### 出力デバイス

| デバイス | 変数名 | GPIOピン | アクション |
|---------|--------|---------|-----------|
| LED (デジタル) | `led_red` | 17 | on, off, toggle |
| PWM LED (調光) | `led_pwm` | 18 | on, off, set(0.0-1.0), pulse |
| RGB LED | `led_rgb` | 22,23,24 | on, off, set("R,G,B") |
| ブザー | `buzzer` | 25 | on, off, beep |
| サーボモーター | `servo` | 13 | min, mid, max, set(-1.0-1.0) |
| DCモーター | `motor` | 5,6 | forward, backward, stop, set |

### 入力デバイス

| デバイス | 変数名 | GPIOピン | アクション |
|---------|--------|---------|-----------|
| ボタン | `button` | 16 | press, release |
| モーションセンサー | `motion_sensor` | 20 | trigger, clear |
| ラインセンサー | `line_sensor` | 21 | detect, clear |

### ソフトウェアセンサー

| デバイス | 変数名 | 単位 | パターン |
|---------|--------|-----|---------|
| 温度 (DHT22) | `dht22_temperature` | °C | ランダムウォーク |
| 湿度 (DHT22) | `dht22_humidity` | % | ランダムウォーク |
| 気圧 (BMP280) | `bmp280_pressure` | hPa | サイン波+ノイズ |
| 照度 (BH1750) | `bh1750_light` | lux | 昼夜サイクル |
| 距離 (HC-SR04) | `hcsr04_distance` | cm | のこぎり波 |
| 土壌水分 | `soil_moisture` | % | 徐々に乾燥→自動水やり |

## デモプログラム (10本)

| ファイル | 内容 |
|---------|------|
| `demo_led_blink.py` | LED 5回点滅 |
| `demo_sensor_monitor.py` | 温湿度監視 + 異常警告 |
| `demo_button_rgb.py` | ボタンで色切替 + MQTT通知 |
| `demo_smart_farm.py` | 自動灌漑 + 侵入検知 |
| `demo_door_lock.py` | スマートドアロック |
| `demo_rest_test.py` | REST API全エンドポイントテスト |
| `demo_smart_home.py` | 照明・空調自律制御 |
| `demo_mqtt_ecosystem.py` | 3ノード協調動作 |
| `demo_data_logger.py` | データ収集 + 統計分析 + 異常検出 |
| `demo_state_machine.py` | ステートマシン温室制御 |

## テスト

```powershell
# 全テスト実行 (66件)
python -m pytest tests/ -v

# ユニットテストのみ (インフラ不要)
python -m pytest tests/test_devices.py tests/test_sensors.py tests/test_mqtt_format.py -v
```

| テストファイル | 件数 | 内容 |
|---------------|------|------|
| test_devices.py | 20 | デバイス生成・状態管理 |
| test_sensors.py | 13 | センサーシミュレーション |
| test_mqtt_format.py | 9 | MQTTトピック・ペイロード |
| test_rest_api.py | 13 | REST APIエンドポイント |
| test_mqtt_integration.py | 3 | MQTT Pub/Sub通信 |
| test_e2e.py | 5+3 | コマンド→状態変化の全フロー |

## 実機への移行

1. 環境変数 `GPIOZERO_PIN_FACTORY` を **削除**（実機のピンファクトリが自動使用される）
2. `config/pin_map.py` のピン番号を実際の配線に合わせて調整
3. `sensors.py` のシミュレーションセンサーを実際のI2C/SPIドライバーに差し替え
4. `config/settings.py` の `MQTT_BROKER` を実際のブローカーアドレスに変更

詳細は [第12章 実機への移行ガイド](book/12_migration.md) を参照。

## トラブルシューティング

### Pi VM に接続できない

```powershell
docker compose ps              # コンテナ状態確認
docker compose logs raspi      # ログ確認
```

起動に30〜90秒かかるため待機すること。

### MQTT に接続できない

Pi VM 内からは **ホスト名 `mosquitto`** で接続する（`10.0.2.2` は不安定）。

```bash
# Pi VM内でテスト
mosquitto_pub -h mosquitto -p 1883 -t test -m "hello"
```

### ディスクイメージが破損した

```powershell
Remove-Item -Recurse -Force dist
.\start.ps1    # 再初期化される
```

### パフォーマンスが遅い

- Docker Desktop のメモリ割当を 6GB 以上にする
- WSL2 バックエンドを使用する
