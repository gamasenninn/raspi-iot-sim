# 第6章 MQTT通信でIoTシステムを作る

この章では、IoTの世界で最も広く使われている通信プロトコル「MQTT」を学び、センサーデータのリアルタイム配信とデバイスの遠隔制御を実装します。

## 6.1 MQTTとは

MQTT（Message Queuing Telemetry Transport）は、軽量なメッセージ通信プロトコルです。1999年にIBMによって開発され、現在はIoTの標準プロトコルとして広く使われています。

### MQTTの特徴

- **軽量**: ヘッダーサイズがわずか2バイトで、低帯域・低電力のデバイスに最適
- **Pub/Subモデル**: 送信者（Publisher）と受信者（Subscriber）が直接接続しない
- **信頼性**: 3段階のQoS（Quality of Service）レベルをサポート
- **常時接続**: TCPベースで永続的な接続を維持

### Pub/Sub（パブリッシュ/サブスクライブ）モデル

MQTTでは、メッセージの送信者と受信者が直接やりとりしません。「ブローカー」と呼ばれる中継サーバーがすべてのメッセージを仲介します。

```
  温度センサー                              ダッシュボード
  (Publisher)                                (Subscriber)
       │                                          ▲
       │  publish                     subscribe    │
       │  "iot/temp" = "22.5"        "iot/temp"    │
       ▼                                          │
  ┌────────────────────────────────────────────────┐
  │                MQTTブローカー                    │
  │               (Mosquitto)                       │
  │  トピック "iot/temp" に 22.5 が届いた            │
  │  → "iot/temp" を購読している全クライアントに配信  │
  └────────────────────────────────────────────────┘
       │                                          ▲
       │                              subscribe    │
       │                             "iot/temp"    │
       ▼                                          │
                                        スマホアプリ
                                        (Subscriber)
```

このモデルの利点：
- **疎結合**: センサーはダッシュボードの存在を知る必要がない
- **1対多**: 1つのPublisherのメッセージを、複数のSubscriberが同時に受信できる
- **スケーラブル**: 新しいデバイスの追加が容易

### トピック

MQTTのトピックはファイルパスのような階層構造を持ちます。

```
iot/                          ← 最上位
iot/devices/                  ← デバイス全般
iot/devices/led_red/          ← 特定のデバイス
iot/devices/led_red/state     ← 状態
iot/devices/led_red/command   ← コマンド
```

ワイルドカードも使用できます：
- `+`: 1レベルの任意の文字列にマッチ
  - `iot/devices/+/state` → すべてのデバイスのstateにマッチ
- `#`: 残りのすべてのレベルにマッチ
  - `iot/#` → iot以下のすべてにマッチ

## 6.2 本書のMQTTトピック設計

```
iot/devices/{デバイス名}/state     ← テレメトリ（デバイス→ブローカー）
iot/devices/{デバイス名}/command   ← コマンド（ブローカー→デバイス）
```

### テレメトリ（状態配信）

デバイスが1秒間隔で自分の状態をpublishします。

```json
{
    "device": "dht22_temperature",
    "type": "sensor",
    "category": "Sensor",
    "value": 22.5,
    "unit": "°C",
    "timestamp": 1773684532.72
}
```

### コマンド（制御指示）

外部からデバイスに指示を送ります。

```json
{"action": "on"}
{"action": "set", "value": "0.5"}
{"action": "forward"}
```

## 6.3 MQTTクライアントの実装

Pythonでは `paho-mqtt` ライブラリを使用します。

### 基本的な使い方

```python
import paho.mqtt.client as mqtt

# クライアントの作成と接続
client = mqtt.Client(client_id="my-sensor")
client.connect("mosquitto", 1883, 60)

# メッセージの送信
client.publish("iot/devices/temp/state", '{"value": 22.5}')

# メッセージの受信
def on_message(client, userdata, msg):
    print(f"受信: {msg.topic} = {msg.payload.decode()}")

client.on_message = on_message
client.subscribe("iot/devices/+/command")

# ネットワークループの開始（バックグラウンドで実行）
client.loop_start()
```

### 本書のMQTTクライアント

本書のIoTアプリケーション（`protocols/mqtt_client.py`）では、以下の機能を持つMQTTクライアントを実装しています。

**テレメトリ配信:**
- デバイスレジストリ内の全15デバイスの状態を1秒間隔でpublish
- 各デバイスの `get_state()` を呼び出してJSON化

**コマンド受信:**
- `iot/devices/+/command` をsubscribe
- 受信したJSONから `action` と `value` を取り出し、デバイスレジストリの対応するアクションを実行

**接続リトライ:**
- ブローカーに接続できない場合、最大10回リトライ（3秒間隔）
- MQTTなしでもアプリケーションは動作を継続

## 6.4 実践: MQTTコマンドでLEDを制御

MQTTを使って外部からLEDを制御してみましょう。

### 手順

**1. IoTアプリを起動（仮想Raspberry Pi内）**

```bash
cd /opt/iot-app && ./venv/bin/python main.py
```

**2. テレメトリを確認（Windows PowerShell）**

```powershell
docker exec mosquitto mosquitto_sub -t "iot/devices/led_red/state" -C 1
```

出力:
```json
{"device": "led_red", "type": "output", "category": "LED", "on": false, "timestamp": 1773684532.72}
```

**3. LEDをONにする**

```powershell
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/led_red/command' -m '{\"action\":\"on\"}'"
```

**4. 状態の変化を確認**

```powershell
docker exec mosquitto mosquitto_sub -t "iot/devices/led_red/state" -C 1
```

出力:
```json
{"device": "led_red", "type": "output", "category": "LED", "on": true, "timestamp": 1773684597.62}
```

`"on": false` から `"on": true` に変化しました。

## 6.5 実践: 3ノード協調エコシステム

MQTTの真価は、複数のデバイスが疎結合で連携できることにあります。

### システム構成

```
WeatherStation ──publish──> iot/weather/data
                                    │
GardenController <──subscribe───────┘
       │
       └──subscribe──> iot/security/alert
                              │
SecuritySystem ──publish──────┘
```

3つの独立したノードがMQTTトピックを通じて協調動作します。

- **WeatherStation**: 気象データ（温度・湿度・気圧・照度）を配信
- **GardenController**: 気象データを受信して灌漑・日除けを制御。警報時は全停止
- **SecuritySystem**: 距離センサーで侵入を検知し、全ノードに警報を配信

### 協調動作の実例

```
[Weather] # 1 T: 22.2C H: 54.8% P: 1013.5hPa L: 494.9lux
[Security] # 1 *** INTRUDER! D: 3.3cm count:1 ***
[Garden] !!! Alert received -> pump OFF !!!
[Garden] # 1 ALERT MODE - all stopped
...
[Security] #13 Alert cleared D: 46.2cm
[Garden] #13 soil: 69.3% pump:OFF shade:CLOSED -> hold
```

侵入検知→警報→全停止→警報解除→通常復帰という一連の流れが、MQTTメッセージの送受信だけで実現されています。

## 6.6 MQTTのQoSレベル

| レベル | 名前 | 保証 | 使用場面 |
|--------|------|------|---------|
| 0 | At most once | 最大1回配信（ロスあり） | テレメトリ（多少欠損してもOK） |
| 1 | At least once | 最低1回配信（重複あり） | コマンド（確実に届けたい） |
| 2 | Exactly once | 正確に1回配信 | 課金・注文（重複不可） |

本書では、テレメトリにQoS 0、コマンドにQoS 1を使用しています。

## 6.7 この章のまとめ

- MQTTはPub/Subモデルの軽量メッセージプロトコル
- トピックは階層構造で、ワイルドカードでフィルタリング可能
- テレメトリ（状態配信）とコマンド（制御指示）の双方向通信
- 複数ノードの疎結合な協調動作が容易に実現できる

次の章では、REST APIを使ったHTTPベースの制御を学びます。
