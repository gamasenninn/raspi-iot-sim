# ドキュメント一覧

## マニュアル
- [01_SETUP_MANUAL.md](01_SETUP_MANUAL.md) — 環境構築手順書（Windows + Docker Desktop + PowerShell）

## 実験レポート
- [02_EXPERIMENT_RESULTS.md](02_EXPERIMENT_RESULTS.md) — 基本実験5件の結果と知見
- [03_ADVANCED_EXPERIMENTS.md](03_ADVANCED_EXPERIMENTS.md) — 追加実験4件（REST API、スマートホーム、エコシステム、データロガー）
- [04_STATE_MACHINE_AND_PATTERNS.md](04_STATE_MACHINE_AND_PATTERNS.md) — ステートマシン実験 + IoT設計パターン集

## デモプログラム一覧

| ファイル | 内容 | 使用デバイス | 使用プロトコル |
|---------|------|------------|--------------|
| `demo_led_blink.py` | LED 5回点滅 | LED | - |
| `demo_sensor_monitor.py` | 温湿度監視 + 異常警告 | LED, PWM LED, Buzzer, DHT22, BMP280 | - |
| `demo_button_rgb.py` | ボタンで色切替 | Button, RGB LED | MQTT |
| `demo_smart_farm.py` | 自動灌漑 + 侵入検知 | Motor, Buzzer, 5種センサー | MQTT |
| `demo_door_lock.py` | スマートドアロック | Servo, Button, MotionSensor, LED, Buzzer | MQTT |
| `demo_rest_test.py` | REST API全エンドポイントテスト | 全デバイス | REST |
| `demo_smart_home.py` | 照明・空調自律制御 | PWM LED, RGB LED, Motor, Buzzer | MQTT |
| `demo_mqtt_ecosystem.py` | 3ノード協調動作 | Motor, Servo, Buzzer, LED, 6種センサー | MQTT |
| `demo_data_logger.py` | データ収集 + 統計分析 + 異常検出 | 6種センサー | MQTT, CSV |
| `demo_state_machine.py` | ステートマシン温室制御 | RGB LED, LED, Motor, PWM LED, Buzzer, Button | MQTT |

## ダッシュボード & テスト
- [05_DASHBOARD_AND_TESTING.md](05_DASHBOARD_AND_TESTING.md) — Webダッシュボード使用法 + テストスイート全結果

## Webダッシュボード
- `dashboard/index.html` — ブラウザで開くだけでリアルタイムデバイス監視・操作

## テスト実行
```powershell
python -m pytest tests/ -v   # 全テスト (66件)
```
