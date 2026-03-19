# 書籍ハンズオン検証ワークフロー

書籍（book/）の手順・コード例を実際に実行し、動作を検証するエージェントワークフロー。
読者がつまずくポイントやコードと書籍の乖離を自動で洗い出す。

## ワークフロー概要

```
[Orchestrator (あなた)]
  ├─ 並列 ─────────────────────────────┐
  │  [LocalTestAgent]                   │  [BookDiffAgent]
  │   - pip install                     │   - 書籍 vs コード比較
  │   - pytest 全ユニットテスト          │   - 乖離リスト作成
  │   - MockFactoryデモ実行             │
  ├─ Gate: LocalTest pass? ─────────────┘
  │
  ├─ [VMLifecycleAgent]
  │   - Docker環境構築 → プロビジョニング → 全デモ実行 → 安全停止
  │
  └─ [ReportAgent]
      - 全結果を集約 → Issue #13 にコメント
```

## 実行手順

### Step 1: LocalTestAgent と BookDiffAgent を並列起動

以下の2つのエージェントを **同時に** Agent tool で起動してください。

#### Agent 1: LocalTestAgent

```
subagent_type: general-purpose
prompt は以下:
```

あなたは書籍ハンズオン検証の「ローカルテストエージェント」です。
作業ディレクトリ: /c/app/raspi-iot-sim

以下を順番に実行し、各ステップの結果をJSON形式で報告してください。

**Step 0: 依存パッケージ**
```bash
pip install "gpiozero>=2.0" "paho-mqtt>=1.6,<2.0" "flask>=3.0" "flask-socketio>=5.3" "gevent>=23.0" requests pytest
```
- 結果: インストール成功/失敗、paho-mqttのバージョン確認（v2.0+なら警告）

**Step 1: ユニットテスト**
```bash
python -m pytest tests/test_devices.py tests/test_sensors.py tests/test_mqtt_format.py tests/test_rest_api.py -v
```
- 期待値: 58テスト全パス
- 結果: pass数/fail数/error数、失敗したテスト名（あれば）

**Step 2: MockFactoryデモ（PYTHONPATH=./app を設定してローカル実行）**

demo_led_blink.py:
- 期待する出力: `[1/5] ON  (is_lit=True)` ～ `[5/5] OFF (is_lit=False)` + `完了!`
- 成功判定: exit code 0 かつ `完了!` が出力に含まれる

demo_sensor_monitor.py:
- 期待する出力: `[1/10]` ～ `[10/10]` + `計測完了。全デバイスOFF。`
- 成功判定: exit code 0 かつ `計測完了` が出力に含まれる

**最終レポート形式:**
```json
{
  "agent": "LocalTestAgent",
  "pip_install": "ok",
  "paho_mqtt_version": "1.6.1",
  "unit_tests": {"total": 58, "passed": 58, "failed": 0, "errors": 0, "failures": []},
  "demos": {
    "demo_led_blink.py": {"exit_code": 0, "success": true},
    "demo_sensor_monitor.py": {"exit_code": 0, "success": true}
  },
  "gate_passed": true
}
```

---

#### Agent 2: BookDiffAgent

```
subagent_type: general-purpose
prompt は以下:
```

あなたは書籍ハンズオン検証の「書籍コード差分チェックエージェント」です。
作業ディレクトリ: /c/app/raspi-iot-sim

書籍（book/*.md）と実装コード（app/）を比較し、読者がつまずく可能性のある乖離を検出してください。
**コードの編集は行わないでください。検出と報告のみです。**

**チェック項目:**

1. **エラーメッセージの言語一致**
   - book/07_rest_api.md のエラーレスポンス例 vs app/protocols/rest_api.py の実際のメッセージ
   - 英語/日本語の不一致がないか

2. **状態遷移の完全性**
   - book/09_state_machine.md の `evaluate_transition` コード vs app/demo_state_machine.py
   - 書籍に欠落している遷移がないか（特にRECOVERY→EMERGENCYのrelapse）

3. **ピン番号の整合性**
   - book/04_gpio_programming.md のコード例 vs app/config/pin_map.py
   - 書籍が直接ピン番号(例: `LED(17)`)を使い、デモが `config.pin_map` 経由の場合、それが意図的な教育設計かどうかを判断

4. **MQTTホスト名**
   - 各デモの `client.connect("mosquitto", ...)` がVM内前提であることの確認
   - 書籍がこの違いを説明しているか（book/02_setup.md, book/06_mqtt.md を確認）

5. **パス参照**
   - `sys.path.insert(0, "/opt/iot-app")` がVM内パスであることの確認
   - `demo_data_logger.py` の CSV パス `/opt/iot-app/sensor_log.csv`

6. **paho-mqtt バージョン注意書き**
   - book/06_mqtt.md にv2.0非互換の警告があるか

7. **import文とAPI使用法**
   - 書籍のコード例に存在しないモジュールのimportや、非推奨APIの使用がないか

**最終レポート形式:**
```json
{
  "agent": "BookDiffAgent",
  "issues_found": [
    {
      "severity": "high|medium|low",
      "category": "error_message|state_transition|pin_number|mqtt_host|path|version|import",
      "book_file": "book/07_rest_api.md",
      "book_line": 160,
      "code_file": "app/protocols/rest_api.py",
      "code_line": 27,
      "description": "エラーメッセージが英語(書籍) vs 日本語(実装)",
      "book_value": "Device 'nonexistent' not found",
      "code_value": "デバイス 'nonexistent' が見つかりません",
      "is_intentional": false,
      "recommendation": "書籍を実装に合わせて日本語に修正"
    }
  ],
  "summary": {
    "high": 0,
    "medium": 0,
    "low": 0,
    "intentional": 0
  }
}
```

---

### Step 2: Gate判定

LocalTestAgent の結果を確認する。
- `gate_passed: true` → Step 3 に進む
- `gate_passed: false` → ここで停止。失敗原因を報告して終了

### Step 3: VMLifecycleAgent を起動

```
subagent_type: general-purpose
prompt は以下:
```

あなたは書籍ハンズオン検証の「VM検証エージェント」です。
作業ディレクトリ: /c/app/raspi-iot-sim

**最重要ルール: 何が起きても最後に必ずVMを安全停止すること。**

以下の手順を実行してください。エラーが発生した場合でも、必ず「安全停止」セクションを実行してください。

SSH共通オプション: `-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null`

#### Phase A: Docker環境構築

1. PI-CI初期化（dist/distro.qcow2 が存在しない場合のみ）:
```bash
docker run --rm -v "C:\app\raspi-iot-sim\dist:/dist" ptrsr/pi-ci init
docker run --rm -i -v "C:\app\raspi-iot-sim\dist:/dist" ptrsr/pi-ci resize 4G
# resize は対話式。echo "y" | をパイプする
```

2. Docker Compose起動:
```bash
docker compose up -d mosquitto
docker compose up -d raspi
```

3. SSH接続待機（最大150秒、5秒間隔でリトライ）:
```bash
ssh -o ConnectTimeout=5 -p 2222 root@localhost "echo ok"
```

#### Phase B: プロビジョニング

1. パッケージインストール:
```bash
ssh -p 2222 root@localhost "apt-get update -qq && apt-get install -y -qq python3-pip python3-venv mosquitto-clients > /dev/null 2>&1"
```

2. ファイル転送:
```bash
scp -P 2222 -r ./app/* root@localhost:/opt/iot-app/
```

3. Python環境構築:
```bash
ssh -p 2222 root@localhost "cd /opt/iot-app && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
```

#### Phase C: MQTT接続テスト（Ch2検証）

```bash
ssh -p 2222 root@localhost "mosquitto_pub -h mosquitto -p 1883 -t test/hello -m 'Hello from Pi'"
```
成功判定: exit code 0

#### Phase D: 全デモ実行

以下の各デモをVM内で実行し、結果を記録する。
全デモ共通の実行方法:
```bash
ssh -p 2222 root@localhost "cd /opt/iot-app && ./venv/bin/python <demo_file>"
```

成功判定はそれぞれ:

| デモ | 成功判定（stdout に含まれる文字列） |
|------|------|
| demo_led_blink.py | `完了!` |
| demo_sensor_monitor.py | `計測完了` |
| demo_button_rgb.py | `完了!` |
| demo_data_logger.py | `Data Logger complete!` |
| demo_smart_farm.py | `シミュレーション完了!` |
| demo_door_lock.py | `完了!` |
| demo_smart_home.py | `完了!` |
| demo_mqtt_ecosystem.py | `Done!` |
| demo_state_machine.py | `Done!` |

#### Phase E: main.py + REST API テスト

1. ランナースクリプトを作成してVM内に送る:
```bash
ssh -p 2222 root@localhost 'cat > /tmp/run_rest.sh << "SCRIPT"
#!/bin/bash
cd /opt/iot-app
./venv/bin/python main.py > /tmp/main.log 2>&1 &
MAIN_PID=$!
sleep 8
./venv/bin/python demo_rest_test.py > /tmp/rest_out.txt 2>&1
REST_EXIT=$?
kill $MAIN_PID 2>/dev/null
wait $MAIN_PID 2>/dev/null
echo "REST_EXIT=$REST_EXIT"
cat /tmp/rest_out.txt
SCRIPT
chmod +x /tmp/run_rest.sh'
```

2. 実行:
```bash
ssh -p 2222 root@localhost '/tmp/run_rest.sh'
```
成功判定: `完了` が出力に含まれる

#### Phase F: MQTTインテグレーションテスト

Mosquittoが動いている間にホスト側で:
```bash
python -m pytest tests/test_mqtt_integration.py -v
```
成功判定: 3テスト全パス

#### Phase Z: 安全停止（必ず実行）

```bash
ssh -o ConnectTimeout=5 -p 2222 root@localhost "shutdown now" 2>/dev/null
sleep 10
docker compose down
```

**最終レポート形式:**
```json
{
  "agent": "VMLifecycleAgent",
  "infrastructure": {
    "pi_ci_init": "ok|skipped|failed",
    "docker_compose": "ok|failed",
    "ssh_connect": "ok|failed",
    "provisioning": "ok|failed",
    "mqtt_test": "ok|failed"
  },
  "demos": {
    "demo_led_blink.py": {"exit_code": 0, "success": true},
    "demo_sensor_monitor.py": {"exit_code": 0, "success": true},
    "demo_button_rgb.py": {"exit_code": 0, "success": true},
    "demo_data_logger.py": {"exit_code": 0, "success": true},
    "demo_smart_farm.py": {"exit_code": 0, "success": true},
    "demo_door_lock.py": {"exit_code": 0, "success": true},
    "demo_smart_home.py": {"exit_code": 0, "success": true},
    "demo_mqtt_ecosystem.py": {"exit_code": 0, "success": true},
    "demo_state_machine.py": {"exit_code": 0, "success": true}
  },
  "rest_api": {"exit_code": 0, "success": true, "endpoints_tested": 10},
  "mqtt_integration": {"total": 3, "passed": 3},
  "shutdown": "ok|failed",
  "all_passed": true
}
```

---

### Step 4: ReportAgent でレポート生成

3つのエージェントの結果が揃ったら、以下の形式でIssue #13にコメントを投稿してください。

```bash
gh issue comment 13 --repo gamasenninn/raspi-iot-sim --body "..."
```

レポート構成:
1. **検証環境** (OS, Python, paho-mqtt バージョン)
2. **Phase 1: ユニットテスト結果** (LocalTestAgent)
3. **Phase 2: VM環境構築+デモ実行結果** (VMLifecycleAgent)
4. **Phase 3: 書籍コード差分** (BookDiffAgent)
   - severity: high の項目は修正候補としてハイライト
   - intentional な乖離は「仕様」として記載
5. **結論** (全体の pass/fail + 読者向けの注意点)

### 判断が必要なケース

- **ユニットテストが1つでも失敗**: VMフェーズに進まず即停止。失敗原因を報告
- **VM起動がタイムアウト**: Docker Desktopの状態を確認するよう提案して終了
- **デモが失敗**: 他のデモは続行し、失敗したものを報告
- **BookDiffAgent が high severity を検出**: レポートに修正提案を含める（自動修正はしない）
