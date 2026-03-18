# 第10章 Webダッシュボードでリアルタイム監視

この章では、ブラウザで動くリアルタイムダッシュボードを構築し、15台のIoTデバイスを視覚的に監視・操作します。

## 10.1 ダッシュボードのアーキテクチャ

本書のダッシュボードは、サーバーサイドのコードを一切使わない、**単一HTMLファイル**で構成されています。

```
ブラウザ (index.html)
  │
  │ MQTT over WebSocket (ws://localhost:9001)
  │
  ▼
Mosquitto (:9001)
  │
  │ MQTT (:1883)
  │
  ▼
Pi VM (main.py)
```

ブラウザからMQTTブローカーに直接WebSocketで接続し、テレメトリを受信、コマンドを送信します。Webサーバーは不要です。

### なぜこの構成なのか

Pi VM内のFlask APIのポート5000は、QEMUの外にフォワードされていません。しかし、MosquittoのWebSocketポート9001はDockerからホストに公開されているため、ブラウザから直接アクセスできます。

## 10.2 使用ライブラリ（CDN）

| ライブラリ | バージョン | 用途 |
|-----------|----------|------|
| mqtt.js | v5 | MQTT over WebSocketクライアント |
| Chart.js | v4 | センサー履歴の折れ線グラフ |

いずれもCDNから読み込むため、npmやビルドツールは不要です。

## 10.3 MQTT.jsによるブラウザ接続

```javascript
// MQTTブローカーにWebSocketで接続
const client = mqtt.connect('ws://localhost:9001');

// 接続成功時
client.on('connect', () => {
    // 全デバイスの状態トピックを購読
    client.subscribe('iot/devices/+/state');
});

// メッセージ受信時
client.on('message', (topic, msg) => {
    const name = topic.split('/')[2];   // "led_red" 等
    const data = JSON.parse(msg.toString());
    updateCard(name, data);             // UIを更新
});
```

### コマンドの送信

```javascript
function sendCommand(device, action, value) {
    const payload = value !== undefined
        ? JSON.stringify({action, value: String(value)})
        : JSON.stringify({action});
    client.publish(`iot/devices/${device}/command`, payload);
}
```

> **Note:** `value` は文字列として送信します。サーバー側のアクションハンドラが `float(v)` で数値に変換するためです。

## 10.4 デバイスカードの表示

ダッシュボードは3列のグリッドレイアウトで構成されます。

```
┌───────────────┬───────────────┬───────────────┐
│   Outputs     │    Inputs     │   Sensors     │
│               │               │               │
│ ● LED Red     │ ○ Button      │ 22.5°C 📈    │
│   [ON][OFF]   │  [Press]      │ Temperature   │
│               │               │               │
│ ● PWM LED     │ ○ Motion      │ 55.3% 📈     │
│   ═══════     │  [Trigger]    │ Humidity      │
│               │               │               │
│ ● RGB LED     │ ○ Line        │ 1013.2hPa 📈 │
│   R═══G═══B═══│  [Detect]     │ Pressure      │
│               │               │               │
│ ● Buzzer      │               │ 483.1lux 📈  │
│   [ON][BEEP]  │               │ Light         │
│               │               │               │
│ Servo: 0.50   │               │ 142.0cm 📈   │
│   ═══════     │               │ Distance      │
│   [Min][Max]  │               │               │
│               │               │ 76.8% 📈     │
│ Motor: 0.00   │               │ Soil Moisture │
│   [Fwd][Stop] │               │               │
└───────────────┴───────────────┴───────────────┘
```

### デバイスタイプ別の表示

**LED（デジタル）**: 色付き円インジケータ。ONで赤く光り、OFFで灰色。

**PWM LED**: インジケータの透明度が明るさ（0.0〜1.0）に連動。スライダーで制御。

**RGB LED**: インジケータの色がRGB値に連動。R/G/B 3本のスライダーで制御。

**センサー**: 大きな数値表示 + Chart.jsの折れ線グラフ（直近60件）。

## 10.5 センサーグラフ

Chart.jsを使って、センサーの値の推移をリアルタイムでグラフ表示します。

```javascript
// センサーごとにリングバッファで履歴を管理
const sensorHistory = {};  // {name: [{time, value}, ...]}
const MAX_HISTORY = 60;

// 新しい値が届いたらバッファに追加
if (data.type === 'sensor') {
    if (!sensorHistory[name]) sensorHistory[name] = [];
    sensorHistory[name].push({time: Date.now(), value: data.value});
    if (sensorHistory[name].length > MAX_HISTORY) {
        sensorHistory[name].shift();  // 古いデータを削除
    }
}
```

Chart.jsのアニメーションは無効化（`animation: false`）して、高頻度更新でもスムーズに表示します。

## 10.6 接続状態の表示

ヘッダー右上に接続状態を示すインジケータを配置します。

- **緑の点**: MQTT接続中
- **赤の点**: 切断中（3秒ごとに自動再接続）

```javascript
client.on('connect', () => {
    document.getElementById('connDot').classList.add('on');
    document.getElementById('connText').textContent = 'Connected';
});

client.on('close', () => {
    document.getElementById('connDot').classList.remove('on');
    document.getElementById('connText').textContent = 'Disconnected';
});
```

## 10.7 ダッシュボードの起動方法

```powershell
# ファイルを直接ブラウザで開く
start C:\app\RASPI\dashboard\index.html

# または HTTPサーバー経由（他のPCからもアクセスしたい場合）
cd C:\app\RASPI\dashboard
python -m http.server 8080
# → http://localhost:8080 でアクセス
```

### 前提条件

1. Mosquittoが起動中（`docker compose up -d mosquitto`）
2. Pi VM で `main.py` が稼働中
3. ポート9001（WebSocket）が利用可能

## 10.8 この章のまとめ

- ダッシュボードは単一HTMLファイルで完結（ビルド不要）
- MQTT.jsでブラウザからMosquittoに直接WebSocket接続
- 15デバイスのリアルタイム表示と操作
- Chart.jsでセンサー履歴を折れ線グラフ表示
- 接続状態の自動表示と自動再接続
