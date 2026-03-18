# ステートマシンとIoT設計パターン

## 実験10: 温室ステートマシン (`demo_state_machine.py`)

### 目的
IoTシステムにおけるステートマシンパターンの有効性を検証。
イベント駆動 + gpiozero コールバック機能の統合テスト。

### 状態遷移図

```
                    system start
                        │
                   ┌────▼────┐
                   │  IDLE   │◄──── manual reset (button)
                   └────┬────┘
                        │ activate
                   ┌────▼────────┐
              ┌───►│ MONITORING  │◄──── recovered
              │    └──┬───────┬──┘
              │       │       │
              │  warning   critical
              │       │       │
              │  ┌────▼───┐   │
              │  │ ALERT  │   │
              │  └──┬──┬──┘   │
              │     │  │      │
         normalized │ escalated
              │     │  │      │
              │     │  ▼      ▼
              │    ┌──────────────┐
              │    │  EMERGENCY   │
              │    └──────┬───────┘
              │           │ de-escalated
              │    ┌──────▼───────┐
              └────┤  RECOVERY    │
                   └──────────────┘
```

### 各状態のアクチュエータ制御

| 状態 | RGB LED色 | ファン | ポンプ | アラーム | ブザー |
|------|----------|--------|--------|---------|--------|
| IDLE | 暗い青 | OFF | OFF | OFF | OFF |
| MONITORING | 緑 | 温度>24°C→30% | 土壌<50%→30% | OFF | OFF |
| ALERT | 黄 | 70% | 土壌<45%→70% | ON | OFF |
| EMERGENCY | 赤 | 100% | 100% | ON | ON |
| RECOVERY | 青 | 50% | 20% | OFF | OFF |

### 実行結果（45サイクル、7回の状態遷移）

```
Cycle  1: IDLE         -> MONITORING    | system activated
Cycle 15: MONITORING   -> ALERT         | warning: T=27.49C (temp boost +5.0)
Cycle 17: ALERT        -> EMERGENCY     | escalated: T=28.81C
Cycle 25: EMERGENCY    -> RECOVERY      | de-escalated: T=19.6C (temp boost -8.0)
Cycle 26: RECOVERY     -> MONITORING    | recovered: T=19.42C
Cycle 40: MONITORING   -> IDLE          | manual reset (button callback)
Cycle 41: IDLE         -> MONITORING    | system activated
```

### シナリオ注入

| サイクル | イベント | 効果 |
|---------|---------|------|
| 15 | 温度ブースト +5.0°C | MONITORING→ALERT (温度急上昇) |
| 25 | 温度ブースト -8.0°C | EMERGENCY→RECOVERY (冷却成功) |
| 35 | 温度ブースト +3.0°C | 影響なし（範囲内） |
| 40 | ボタン手動リセット | MONITORING→IDLE→MONITORING |

### 知見

#### ステートマシンパターン
- **明確な責務分離**: 状態判定 (`evaluate_transition`) とアクチュエータ制御 (`apply_state_actions`) を分離
- **遷移履歴**: `state_history` で全遷移をログ。デバッグと監査に有用
- **ヒステリシス**: MONITORING→ALERT の閾値(25°C)と ALERT→MONITORING の閾値(24°C)にギャップを設けることで、境界値でのチャタリングを防止

#### gpiozero コールバック
- `btn.when_pressed = on_button_press` でイベント駆動のリセットを実現
- MockFactory でもコールバックは正常動作
- `pin.drive_low()` → コールバック発火 → 状態遷移 の連鎖が確認できた

#### EMERGENCY パターン
- 全アクチュエータをフル稼働する「最終手段」状態
- 自動復旧条件を厳しく設定（温度26°C以下 AND 土壌40%以上）することで、早期解除を防止
- 実システムでは人間の確認を必要とする設計も検討すべき

---

## IoT設計パターン集 — 本プロジェクトで検証済み

### 1. Pub/Sub パターン (MQTT)
**場所**: 全実験で使用
**概要**: デバイスは自分の状態を publish し、コントローラーは subscribe して受信
**利点**: 疎結合、スケーラブル、新ノードの追加が容易

### 2. Digital Twin パターン
**場所**: `main.py` (テレメトリ配信)
**概要**: 物理デバイスの状態をデジタルでミラーリング。MQTT で 1秒ごとに全状態を配信
**利点**: リモート監視、履歴分析が可能

### 3. Command パターン
**場所**: `rest_api.py`, `mqtt_client.py`
**概要**: `{"action": "on"}` のようなコマンドオブジェクトでデバイスを制御
**利点**: 操作の記録・取り消し・再実行が容易

### 4. Observer パターン (gpiozero callbacks)
**場所**: `demo_state_machine.py`
**概要**: `when_pressed`/`when_released` でイベント駆動制御
**利点**: ポーリング不要、リアルタイム反応

### 5. State Machine パターン
**場所**: `demo_state_machine.py`
**概要**: 有限状態機械による制御ロジック管理
**利点**: 複雑な条件分岐を整理、状態ごとの動作を明確化

### 6. Anomaly Detection パターン
**場所**: `demo_data_logger.py`
**概要**: 統計的手法（平均±2σ）でセンサー異常を検出
**利点**: しきい値のハードコーディングが不要、データ駆動

### 7. Multi-Node Coordination パターン
**場所**: `demo_mqtt_ecosystem.py`
**概要**: 複数ノードがMQTTで協調動作、警報時の連携停止
**利点**: 分散システムの基本。各ノードを独立にデプロイ・更新可能
