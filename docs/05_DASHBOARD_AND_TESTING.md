# Webダッシュボード & テストスイート

## Webダッシュボード

### 概要
Mosquitto の WebSocket ポート (9001) に直接接続する単一HTMLファイルのダッシュボード。
Pi VM やアプリのポートフォワードなしで、MQTT テレメトリをリアルタイム表示。

### アーキテクチャ
```
Browser (index.html)
  │
  │ MQTT over WebSocket (ws://localhost:9001)
  │
  ▼
Mosquitto (:9001 WebSocket)
  │
  │ MQTT (:1883)
  │
  ▼
Pi VM (main.py) ── publish ──> iot/devices/{name}/state
                 ── subscribe ─> iot/devices/{name}/command
```

### 起動方法
```powershell
# ブラウザで直接開く
start C:\app\RASPI\dashboard\index.html

# または HTTP サーバー経由
cd C:\app\RASPI\dashboard
python -m http.server 8080
# → http://localhost:8080 でアクセス
```

### 前提条件
- Mosquitto が起動中 (`docker compose up -d mosquitto`)
- Pi VM で `main.py` が稼働中
- ポート 9001 が利用可能

### 機能

#### デバイスカード (15デバイス)

**Outputs (6デバイス)**
| デバイス | 表示 | 操作 |
|---------|------|------|
| LED Red | 赤円インジケータ | ON/OFF/Toggle ボタン |
| PWM LED | 透明度で明るさ表現 | スライダー + ON/OFF/Pulse |
| RGB LED | 実際のRGB色で表示 | R/G/B 3本スライダー + ON/OFF |
| Buzzer | 黄色インジケータ | ON/OFF/Beep ボタン |
| Servo | 数値表示 (-1.0〜1.0) | スライダー + Min/Mid/Max |
| Motor | 速度バー + 数値 | Forward/Stop/Backward |

**Inputs (3デバイス)**
| デバイス | 表示 | 操作 |
|---------|------|------|
| Button | 緑/灰インジケータ | Press/Release |
| Motion | 赤/灰インジケータ | Trigger/Clear |
| Line | 青/灰インジケータ | Detect/Clear |

**Sensors (6デバイス)**
| デバイス | 表示 |
|---------|------|
| Temperature | 数値 + Chart.js 折れ線グラフ (赤) |
| Humidity | 数値 + 折れ線グラフ (青) |
| Pressure | 数値 + 折れ線グラフ (紫) |
| Light | 数値 + 折れ線グラフ (橙) |
| Distance | 数値 + 折れ線グラフ (緑) |
| Soil Moisture | 数値 + 折れ線グラフ (茶) |

各センサーは直近60件の履歴をグラフ表示。

#### 接続状態
ヘッダー右上に接続状態ドット:
- 緑: MQTT接続中
- 赤: 切断中 (3秒ごとに自動再接続)

### 使用CDNライブラリ
- **mqtt.js v5** — MQTT over WebSocket クライアント
- **Chart.js v4** — センサー履歴グラフ

---

## テストスイート

### 構成

```
tests/
├── conftest.py              # 共通フィクスチャ + スキップ条件
├── test_devices.py          # Unit: デバイス生成・状態管理 (20テスト)
├── test_sensors.py          # Unit: センサーシミュレーション (13テスト)
├── test_mqtt_format.py      # Unit: MQTTトピック・ペイロード (9テスト)
├── test_rest_api.py         # Integration: REST API (13テスト)
├── test_mqtt_integration.py # Integration: MQTT Pub/Sub (3テスト)
└── test_e2e.py              # E2E: コマンド→状態変化 (5テスト)
```

### テスト実行方法

```powershell
cd C:\app\RASPI

# ユニットテストのみ (インフラ不要)
python -m pytest tests/test_devices.py tests/test_sensors.py tests/test_mqtt_format.py -v

# REST APIテスト (インフラ不要)
python -m pytest tests/test_rest_api.py -v

# MQTTインテグレーション (Mosquitto必要)
python -m pytest tests/test_mqtt_integration.py -v

# E2Eテスト (全スタック稼働必要)
python -m pytest tests/test_e2e.py -v

# 全テスト
python -m pytest tests/ -v
```

### テスト結果 (2026-03-17)

| テストファイル | テスト数 | 結果 |
|---------------|---------|------|
| test_devices.py | 20 | 20 passed |
| test_sensors.py | 13 | 13 passed |
| test_mqtt_format.py | 9 | 9 passed |
| test_rest_api.py | 13 | 13 passed |
| test_mqtt_integration.py | 3 | 3 passed |
| test_e2e.py | 5 | 5 skipped (main.py未稼働) |
| **合計** | **63** | **61 passed, 5 skipped, 0 failed** |

### テスト詳細

#### Unit: デバイス (test_devices.py)
- デバイス数が15であること
- 出力/入力/センサーの分類が正しいこと
- LED の ON/OFF/Toggle が状態に反映されること
- PWM LED の値設定 (0.0〜1.0) が正しく動作
- RGB LED のカラー設定が反映されること
- サーボの Min/Mid/Max/Set が正しい値を返すこと
- モーターの Forward/Backward/Stop が正しい速度を返すこと
- ボタン・モーション・ラインセンサーの入力シミュレーション

#### Unit: センサー (test_sensors.py)
- 各センサーの初期値が期待範囲内
- update() で値が変化すること
- 長時間更新しても値が有効範囲内に留まること
- 土壌水分の自動水やり機能 (30%以下→80%付近に回復)

#### Unit: MQTT形式 (test_mqtt_format.py)
- テレメトリ/コマンドトピックのフォーマット検証
- ペイロードの必須フィールド検証
- 全デバイスのペイロードがJSON直列化可能であること

#### Integration: REST API (test_rest_api.py)
- Flask テストクライアントを使用 (サーバー起動不要)
- 全エンドポイントのステータスコード検証
- コマンド実行後の状態変化検証
- エラーケース (404, 400) の検証

#### Integration: MQTT (test_mqtt_integration.py)
- Mosquitto ブローカー経由のメッセージ送受信
- ワイルドカードサブスクリプション
- コマンドのJSON形式ラウンドトリップ
- ブローカー未起動時は自動スキップ

#### E2E (test_e2e.py)
- LED ON/OFF コマンド→テレメトリ確認
- サーボ値設定→テレメトリ確認
- 温度センサーのストリーミング受信 (3件以上)
- モーターの Forward→Stop フロー
- Pi VM未稼働時は自動スキップ

### スキップ条件
- `requires_mqtt`: localhost:1883 に接続できない場合スキップ
- `requires_e2e`: `iot/devices/+/state` にテレメトリが5秒以内に届かない場合スキップ
