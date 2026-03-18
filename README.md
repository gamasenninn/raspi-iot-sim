# Raspberry Pi IoT シミュレーション開発環境

PI-CI (QEMU) による仮想Raspberry Pi OS + gpiozero MockFactory によるGPIOシミュレーション環境。
実機なしでIoTアプリの開発・テストが可能。

## ドキュメント

詳細なマニュアル・実験レポートは [docs/](docs/) を参照:

- **[セットアップマニュアル](docs/01_SETUP_MANUAL.md)** — 環境構築の全手順
- **[実験結果レポート](docs/02_EXPERIMENT_RESULTS.md)** — 基本実験の結果と知見
- **[追加実験レポート](docs/03_ADVANCED_EXPERIMENTS.md)** — REST API、スマートホーム、エコシステム、データロガー
- **[設計パターン](docs/04_STATE_MACHINE_AND_PATTERNS.md)** — ステートマシン、IoT設計パターン集
- **[ドキュメント一覧](docs/INDEX.md)** — 全ドキュメントとデモプログラムの索引

## アーキテクチャ

```
┌─────────────────────────────────────────────────┐
│  Docker Compose (iot-net)                       │
│                                                 │
│  ┌───────────────┐    ┌──────────────────────┐  │
│  │  Mosquitto    │    │  PI-CI (raspi)       │  │
│  │  MQTT Broker  │◄───│  ┌────────────────┐  │  │
│  │  :1883 (MQTT) │    │  │ QEMU           │  │  │
│  │  :9001 (WS)   │    │  │ Raspberry Pi OS│  │  │
│  └───────────────┘    │  │                │  │  │
│                       │  │ IoTアプリ       │  │  │
│                       │  │  - MockFactory │  │  │
│                       │  │  - MQTT Client │  │  │
│                       │  │  - REST API    │  │  │
│                       │  │  - WebSocket   │  │  │
│                       │  └────────────────┘  │  │
│                       │  SSH :2222           │  │
│                       └──────────────────────┘  │
└─────────────────────────────────────────────────┘
```

Pi VM から MQTT ブローカーへは QEMU ゲートウェイ `10.0.2.2:1883` 経由で接続する。

## プロジェクト構成

```
RASPI/
├── docker-compose.yml        # PI-CI + Mosquitto
├── start.sh                  # 起動スクリプト
├── stop.sh                   # 安全停止スクリプト
├── provision.sh              # Pi VMへのアプリ自動デプロイ
├── send_command.sh           # MQTTコマンド送信ヘルパー
├── mosquitto/config/         # MQTTブローカー設定
├── dist/                     # (起動後に生成) Pi VMディスクイメージ
└── app/                      # IoTアプリケーション
    ├── main.py               # エントリポイント
    ├── requirements.txt      # Python依存パッケージ
    ├── config/
    │   ├── settings.py       # MQTT・Flask・シミュレーション設定
    │   └── pin_map.py        # GPIOピン割り当て定義
    ├── devices/
    │   ├── factory.py        # MockFactory初期化 + デバイスレジストリ
    │   ├── outputs.py        # LED, RGBLED, Buzzer, Servo, Motor
    │   ├── inputs.py         # Button, MotionSensor, LineSensor
    │   └── sensors.py        # DHT22, BMP280, 照度, 距離, 土壌水分
    ├── simulation/
    │   └── engine.py         # 自動シミュレーション (ランダムイベント生成)
    └── protocols/
        ├── mqtt_client.py    # MQTT配信 + コマンド受信
        ├── rest_api.py       # REST API (GET/POST)
        └── websocket_server.py  # WebSocketリアルタイム配信
```

## 使い方

### 前提条件

- Docker Desktop (WSL2バックエンド推奨)
- Git Bash または WSL2 ターミナル
- Docker Desktopのメモリ割当: 6GB以上推奨

### 1. 初回起動

```bash
bash start.sh
```

以下が自動的に行われる:

1. PI-CI ディスクイメージの初期化 (`dist/distro.qcow2`)
2. ディスクサイズを 4GB に拡張
3. Mosquitto MQTT ブローカー起動
4. Pi VM 起動 (シリアルコンソール表示)

初回は PI-CI イメージのダウンロード + 初期化に数分かかる。

### 2. 別ターミナルでアプリデプロイ

```bash
bash provision.sh
```

SSH経由で以下を自動実行:

1. Pi VM の起動待ち (最大150秒)
2. システムパッケージインストール (`python3-pip`, `python3-venv`, `mosquitto-clients`)
3. アプリケーションファイルの転送 (`/opt/iot-app/`)
4. Python仮想環境の構築 + 依存パッケージインストール

### 3. Pi VM 内でアプリ起動

```bash
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

起動すると以下のサービスが開始される:

- **シミュレーションエンジン**: デバイスの状態を自動更新
- **MQTT配信**: `iot/devices/{name}/state` トピックに1秒間隔で配信
- **REST API**: Pi VM 内の `http://0.0.0.0:5000`
- **WebSocket**: Pi VM 内の `ws://0.0.0.0:5000/socket.io/`

### 4. デバイス操作

#### MQTT で状態を監視

```bash
mosquitto_sub -h localhost -p 1883 -t 'iot/devices/#'
```

#### MQTT でコマンド送信

```bash
# LED制御
bash send_command.sh led_red on
bash send_command.sh led_red off
bash send_command.sh led_pwm set 0.5
bash send_command.sh led_rgb set "1.0,0.0,0.5"

# モーター・サーボ
bash send_command.sh servo set 0.5
bash send_command.sh motor forward
bash send_command.sh motor stop

# ブザー
bash send_command.sh buzzer on
bash send_command.sh buzzer beep

# 入力シミュレーション
bash send_command.sh button press
bash send_command.sh motion_sensor trigger
```

#### REST API (Pi VM 内から)

```bash
# 全デバイス一覧
curl http://localhost:5000/api/devices

# 特定デバイスの状態
curl http://localhost:5000/api/devices/led_red

# コマンド実行
curl -X POST http://localhost:5000/api/devices/led_red/action \
  -H "Content-Type: application/json" \
  -d '{"action": "on"}'

# 値指定コマンド
curl -X POST http://localhost:5000/api/devices/led_pwm/action \
  -H "Content-Type: application/json" \
  -d '{"action": "set", "value": "0.75"}'

# ヘルスチェック
curl http://localhost:5000/api/health
```

### 5. 安全停止

```bash
bash stop.sh
```

**重要**: Pi VM を強制終了 (`docker kill`, `Ctrl+C`) すると `dist/distro.qcow2` が破損する。
必ず `stop.sh` を使うか、Pi VM 内で `shutdown now` を実行してから Docker を停止すること。

## デバイス一覧

### 出力デバイス (gpiozero MockFactory)

| デバイス | 変数名 | GPIOピン | アクション |
|---------|--------|---------|-----------|
| LED (デジタル) | `led_red` | 17 | on, off, toggle |
| PWM LED (調光) | `led_pwm` | 18 | on, off, set(0.0-1.0), pulse |
| RGB LED | `led_rgb` | 22,23,24 | on, off, set("R,G,B") |
| ブザー | `buzzer` | 25 | on, off, beep |
| サーボモーター | `servo` | 13 | min, mid, max, set(-1.0-1.0) |
| DCモーター | `motor` | 5,6 | forward, backward, stop, set |

### 入力デバイス (gpiozero MockFactory)

| デバイス | 変数名 | GPIOピン | アクション |
|---------|--------|---------|-----------|
| ボタン | `button` | 16 | press, release |
| モーションセンサー (PIR) | `motion_sensor` | 20 | trigger, clear |
| ラインセンサー | `line_sensor` | 21 | detect, clear |

### ソフトウェアセンサー (値生成シミュレーション)

| デバイス | 変数名 | 単位 | パターン |
|---------|--------|-----|---------|
| 温度 (DHT22) | `dht22_temperature` | °C | ランダムウォーク (22°C付近) |
| 湿度 (DHT22) | `dht22_humidity` | % | ランダムウォーク (55%付近) |
| 気圧 (BMP280) | `bmp280_pressure` | hPa | サイン波 (1013hPa付近) |
| 照度 (BH1750) | `bh1750_light` | lux | 昼夜サイクル (600秒周期) |
| 距離 (HC-SR04) | `hcsr04_distance` | cm | のこぎり波 (2-400cm) |
| 土壌水分 | `soil_moisture` | % | 徐々に乾燥→自動水やり |

## 通信プロトコル

### MQTT

- **ブローカー**: Mosquitto (ポート1883)
- **テレメトリ**: `iot/devices/{デバイス名}/state` (QoS 0, 1秒間隔)
- **コマンド**: `iot/devices/{デバイス名}/command` (QoS 1)
- **コマンド形式**: `{"action": "on"}` または `{"action": "set", "value": "0.5"}`
- **WebSocket**: ポート9001 (ブラウザからの直接接続用)

### REST API

| メソッド | パス | 説明 |
|---------|------|------|
| GET | `/api/health` | ヘルスチェック |
| GET | `/api/devices` | 全デバイス一覧 + 状態 |
| GET | `/api/devices/{name}` | 特定デバイスの状態 |
| POST | `/api/devices/{name}/action` | コマンド実行 |

### WebSocket (Socket.IO)

- **イベント受信**: `device_update` — デバイス状態の更新 (1秒間隔)
- **イベント受信**: `all_states` — 接続時に全状態を受信
- **イベント送信**: `device_command` — `{"device": "led_red", "action": "on"}`
- **イベント受信**: `error` — エラーメッセージ

## 実機への移行

この環境で開発したアプリを実機に移行するには:

1. `config/settings.py` の `MQTT_BROKER` を実際のブローカーアドレスに変更
2. `config/pin_map.py` のピン番号を実際の配線に合わせて調整
3. 環境変数 `GPIOZERO_PIN_FACTORY` を **削除** (実機のピンファクトリが自動使用される)
4. `sensors.py` のシミュレーションセンサーを実際のI2C/SPIドライバーに差し替え
5. `requirements.txt` に実機用ライブラリ (`adafruit-circuitpython-dht` 等) を追加

ピンマップが分離されているため、コードの大部分はそのまま動作する。

## トラブルシューティング

### Pi VM に接続できない

```bash
# Pi VMのステータス確認
docker compose ps

# コンテナログ確認
docker compose logs raspi
```

起動に30〜90秒かかるため待機すること。

### MQTT に接続できない

Pi VM 内から MQTT ブローカーへは `10.0.2.2:1883` (QEMUゲートウェイ) を使用する。
`localhost:1883` では接続できない。

```bash
# Pi VM内でテスト
mosquitto_pub -h 10.0.2.2 -p 1883 -t test -m "hello"
```

### ディスクイメージが破損した

```bash
# distディレクトリを削除して再初期化
rm -rf dist/
bash start.sh
```

### パフォーマンスが遅い

- Docker Desktop のメモリ割当を 6GB 以上にする
- WSL2 バックエンドを使用する
- `dist/` を WSL2 内のLinuxファイルシステムに配置する (`/home/user/` 配下)
