# 付録

## A. トラブルシューティング

### A.1 Docker関連

**症状**: `docker: command not found`

**原因**: Docker Desktopが起動していない、またはPATHが設定されていない

**対策**: Docker Desktopを起動する。WSL2ターミナルの場合はPowerShellを使用する。

---

**症状**: `Error response from daemon: ... is not a valid Windows path`

**原因**: Git Bash (MSYS2) がパスを自動変換している

**対策**: PowerShellを使用する。Git Bashを使う場合は `MSYS_NO_PATHCONV=1` を先頭に付ける。

---

**症状**: `the input device is not a TTY`

**原因**: Git BashのminttyとDockerのTTY非互換

**対策**: PowerShellを使用する。

### A.2 PI-CI関連

**症状**: Pi VMに接続できない

**対策**: 起動に30〜90秒かかるため待機する。`docker compose logs raspi` でログを確認。

---

**症状**: `distro.qcow2` が破損した

**原因**: Pi VMの強制終了

**対策**: `dist/` フォルダを削除して再初期化。

### A.3 MQTT関連

**症状**: Pi VMから `10.0.2.2:1883` で接続できない

**対策**: ホスト名 `mosquitto` で接続する（Dockerネットワーク名）。

---

**症状**: WindowsホストのPythonクライアントからMQTTメッセージを受信できない

**原因**: Docker Desktop のネットワーキング制約。Pi VM → Mosquitto → ホストの経路で、publish されたメッセージがホスト側の subscriber に配信されない場合がある。

**対策**: `docker exec mosquitto mosquitto_sub` でコンテナ内からsubscribeする。

### A.4 パフォーマンス関連

**症状**: pip install が非常に遅い

**原因**: QEMUのARM→x86変換オーバーヘッド

**対策**: 辛抱強く待つ。`gevent` を外すと大幅に高速化。

## B. コマンドリファレンス

### B.1 Docker Compose

```powershell
docker compose up -d mosquitto   # Mosquittoをバックグラウンド起動
docker compose up raspi           # Pi VMをフォアグラウンド起動
docker compose ps                 # コンテナ状態確認
docker compose logs mosquitto     # Mosquittoログ確認
docker compose down               # 全コンテナ停止
```

### B.2 PI-CI

```powershell
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init      # 初期化
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G  # ディスク拡張
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci export     # イメージ出力
```

### B.3 SSH/SCP

```powershell
# SSH接続
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost

# ファイル転送（ホスト→Pi VM）
scp -o StrictHostKeyChecking=no -P 2222 file.py root@localhost:/opt/iot-app/

# フォルダ転送
scp -o StrictHostKeyChecking=no -P 2222 -r ./app/* root@localhost:/opt/iot-app/
```

### B.4 MQTT

```powershell
# テレメトリ受信（5件で終了）
docker exec mosquitto mosquitto_sub -t "iot/devices/#" -C 5

# コマンド送信
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/led_red/command' -m '{\"action\":\"on\"}'"
```

### B.5 自動化スクリプト

```powershell
.\start.ps1       # 環境起動（初回はPI-CI初期化も実行）
.\provision.ps1   # Pi VMへのアプリ転送 + Python環境セットアップ
.\stop.ps1        # Pi VM安全シャットダウン + Docker Compose停止
```

### B.6 テスト

```powershell
python -m pytest tests/ -v              # 全テスト
python -m pytest tests/test_devices.py -v  # デバイステストのみ
python -m pytest tests/ -k "test_led"   # LED関連テストのみ
```

## C. gpiozero デバイスクラス一覧

| クラス | 用途 | 主なメソッド/プロパティ |
|--------|------|----------------------|
| `LED` | デジタルLED | `on()`, `off()`, `toggle()`, `is_lit` |
| `PWMLED` | 調光LED | `value` (0-1), `pulse()`, `blink()` |
| `RGBLED` | フルカラーLED | `color` (r,g,b), `on()`, `off()` |
| `Buzzer` | ブザー | `on()`, `off()`, `beep()`, `is_active` |
| `Servo` | サーボモーター | `min()`, `mid()`, `max()`, `value` (-1 to 1) |
| `Motor` | DCモーター | `forward()`, `backward()`, `stop()`, `value` |
| `Button` | ボタン | `is_pressed`, `when_pressed`, `when_released` |
| `MotionSensor` | 人感センサー | `is_active`, `when_motion`, `when_no_motion` |
| `LineSensor` | ラインセンサー | `is_active`, `when_line`, `when_no_line` |
| `DistanceSensor` | 距離センサー | `distance` (meters) |

## D. MQTTトピック一覧

| トピック | 方向 | ペイロード例 |
|---------|------|------------|
| `iot/devices/{name}/state` | デバイス→ブローカー | `{"device":"led_red","on":true}` |
| `iot/devices/{name}/command` | ブローカー→デバイス | `{"action":"on"}` |
| `iot/weather/data` | WeatherStation→ | `{"temp":22.5,"humidity":55}` |
| `iot/garden/status` | GardenController→ | `{"irrigating":true}` |
| `iot/security/alert` | SecuritySystem→ | `{"alert":true,"distance":15}` |
| `iot/demo/smart_home` | SmartHome→ | `{"sensors":{...},"actuators":{...}}` |
| `iot/demo/state` | StateMachine→ | `{"state":"ALERT","reason":"..."}` |
| `iot/demo/data_report` | DataLogger→ | `{"temperature":{"mean":22.3,...}}` |

## E. REST APIエンドポイント一覧

| メソッド | パス | 説明 | レスポンス例 |
|---------|------|------|------------|
| GET | `/api/health` | ヘルスチェック | `{"status":"ok","devices":15}` |
| GET | `/api/devices` | 全デバイス一覧 | `{"led_red":{...},...}` |
| GET | `/api/devices/{name}` | 特定デバイス | `{"name":"led_red","state":{...}}` |
| POST | `/api/devices/{name}/action` | コマンド実行 | `{"ok":true,"state":{...}}` |

## F. 参考リンク

- [PI-CI (GitHub)](https://github.com/ptrsr/pi-ci) — 仮想Raspberry Pi環境
- [gpiozero ドキュメント](https://gpiozero.readthedocs.io/) — GPIO制御ライブラリ
- [Eclipse Mosquitto](https://mosquitto.org/) — MQTTブローカー
- [MQTT.js](https://github.com/mqttjs/MQTT.js) — ブラウザ用MQTTクライアント
- [Chart.js](https://www.chartjs.org/) — JavaScriptグラフライブラリ
- [paho-mqtt (Python)](https://pypi.org/project/paho-mqtt/) — Python MQTTクライアント
- [Flask](https://flask.palletsprojects.com/) — Python Webフレームワーク
- [pytest](https://docs.pytest.org/) — Pythonテストフレームワーク

## G. 本書で作成したファイル一覧

### アプリケーション (app/)
| ファイル | 行数 | 説明 |
|---------|------|------|
| main.py | 50行 | エントリポイント |
| config/settings.py | 15行 | 設定値 |
| config/pin_map.py | 20行 | ピン割り当て |
| devices/factory.py | 35行 | デバイスファクトリ |
| devices/outputs.py | 90行 | 出力デバイス6種 |
| devices/inputs.py | 45行 | 入力デバイス3種 |
| devices/sensors.py | 110行 | ソフトウェアセンサー6種 |
| simulation/engine.py | 60行 | シミュレーションエンジン |
| protocols/mqtt_client.py | 90行 | MQTTクライアント |
| protocols/rest_api.py | 60行 | REST API |
| protocols/websocket_server.py | 55行 | WebSocketサーバー |

### デモプログラム (app/)
| ファイル | 説明 |
|---------|------|
| demo_led_blink.py | LED点滅 |
| demo_sensor_monitor.py | 温湿度モニター |
| demo_button_rgb.py | ボタン→RGB LED |
| demo_smart_farm.py | スマート農業 |
| demo_door_lock.py | スマートドアロック |
| demo_rest_test.py | REST APIテスト |
| demo_smart_home.py | スマートホーム |
| demo_mqtt_ecosystem.py | 3ノード協調 |
| demo_data_logger.py | データロガー |
| demo_state_machine.py | ステートマシン |

### テスト (tests/)
| ファイル | テスト数 |
|---------|---------|
| test_devices.py | 20 |
| test_sensors.py | 13 |
| test_mqtt_format.py | 9 |
| test_rest_api.py | 13 |
| test_mqtt_integration.py | 3 |
| test_e2e.py | 5 |
| **合計** | **66** |

### インフラ・スクリプト
| ファイル | 説明 |
|---------|------|
| docker-compose.yml | Docker定義 |
| mosquitto/config/mosquitto.conf | MQTT設定 |
| dashboard/index.html | Webダッシュボード |
| start.ps1 | 環境起動スクリプト (PowerShell) |
| provision.ps1 | アプリ転送+セットアップ (PowerShell) |
| stop.ps1 | 安全停止スクリプト (PowerShell) |
| pytest.ini | テスト設定 |
| .gitignore | Git除外設定 |
