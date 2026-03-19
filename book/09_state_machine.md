# 第9章 ステートマシンで本格的なIoTシステムを設計する

この章では、有限状態機械（ステートマシン）パターンを使って、複雑なIoT制御ロジックを整理・管理する方法を学びます。

## 9.1 ステートマシンとは

前章の制御ロジックでは、if-elif-elseの条件分岐が増えるにつれてコードが複雑になっていきます。ステートマシンは、この複雑さを「状態」と「遷移」に整理するデザインパターンです。

### 基本概念

- **状態（State）**: システムが今どの状態にあるか（例：待機中、監視中、警報中）
- **遷移（Transition）**: ある状態から別の状態への切り替え（例：温度上昇で監視中→警報中）
- **アクション（Action）**: 各状態で実行する処理（例：警報中→ファン全開、ブザーON）

```
        ┌────────────┐
        │   IDLE     │  最小電力
        └─────┬──────┘
              │ 起動
        ┌─────▼──────┐
   ┌───►│ MONITORING │  通常監視
   │    └──┬──────┬──┘
   │       │      │
   │   warning  critical
   │       │      │
   │  ┌────▼──┐   │
   │  │ ALERT │   │
   │  └──┬──┬─┘   │
   │     │  │     │
   │  正常化 悪化  │
   │     │  │     │
   │     │  ▼     ▼
   │   ┌───────────┐
   │   │ EMERGENCY │  全力対応
   │   └─────┬─────┘
   │         │ 改善
   │   ┌─────▼─────┐
   └───┤ RECOVERY  │  回復中
       └───────────┘
```

## 9.2 温室制御ステートマシンの実装

### 5つの状態

| 状態 | RGB LED | ファン | ポンプ | ブザー | 説明 |
|------|---------|--------|--------|--------|------|
| IDLE | 暗い青 | OFF | OFF | OFF | 最小電力待機 |
| MONITORING | 緑 | 低速 | 低速 | OFF | 通常監視 |
| ALERT | 黄 | 70% | 70% | OFF | 警告 |
| EMERGENCY | 赤 | 100% | 100% | ON | 緊急対応 |
| RECOVERY | 青 | 50% | 20% | OFF | 回復中 |

### 遷移条件

```python
def evaluate_transition(t_val, h_val, s_val):
    if current_state == "MONITORING":
        if t_val > 28 or s_val < 25:
            transition("EMERGENCY", "critical")
        elif t_val > 25 or h_val > 75 or s_val < 40:
            transition("ALERT", "warning")

    elif current_state == "ALERT":
        if t_val > 28 or s_val < 25:
            transition("EMERGENCY", "escalated")
        elif t_val < 24 and h_val < 70 and s_val > 50:
            transition("MONITORING", "normalized")

    elif current_state == "EMERGENCY":
        if t_val < 26 and s_val > 40:
            transition("RECOVERY", "de-escalated")

    elif current_state == "RECOVERY":
        if t_val < 24 and h_val < 65 and s_val > 55:
            transition("MONITORING", "recovered")
        elif t_val > 27:
            transition("EMERGENCY", "relapse")
```

### ヒステリシスの適用

MONITORING→ALERTの閾値（温度25°C）とALERT→MONITORINGの閾値（温度24°C）に1°Cのギャップがあります。これにより、25°C付近でALERTとMONITORINGが高速で切り替わるチャタリングを防止しています。

## 9.3 実行結果の分析

```
Cycle  1: IDLE       -> MONITORING  | system activated
Cycle 15: MONITORING -> ALERT       | warning: T=27.49C（温度ブースト+5.0C）
Cycle 17: ALERT      -> EMERGENCY   | escalated: T=28.81C
Cycle 25: EMERGENCY  -> RECOVERY    | de-escalated: T=19.6C（温度ブースト-8.0C）
Cycle 26: RECOVERY   -> MONITORING  | recovered: T=19.42C
Cycle 40: MONITORING -> IDLE        | manual reset（ボタン押下）
Cycle 41: IDLE       -> MONITORING  | system activated
```

45サイクルで7回の状態遷移が発生。各遷移の理由（`reason`）が記録されているため、後から「なぜその状態に遷移したか」を追跡できます。

## 9.4 手動介入: gpiozeroコールバック

ステートマシンに「手動リセットボタン」を組み込みます。

```python
btn = Button(16, pull_up=True)

def on_button_press():
    print("Manual reset pressed!")
    transition("IDLE", "manual reset")

btn.when_pressed = on_button_press
```

サイクル40でボタンが押されると、状態がIDLEにリセットされ、次のサイクルで自動的にMONITORINGに遷移します。この「人間の介入ポイント」はIoTシステムの安全設計として重要です。

## 9.5 ステートマシン設計のベストプラクティス

1. **遷移判定とアクション実行を分離する**: `evaluate_transition()` と `apply_state_actions()` を別関数にする
2. **遷移履歴を記録する**: デバッグと監査のため
3. **ヒステリシスを必ず設ける**: チャタリング防止
4. **手動介入ポイントを用意する**: 自動制御の暴走防止
5. **EMERGENCYからの自動復旧は慎重に**: 条件を厳しく設定する

## 9.6 この章のまとめ

- ステートマシンは複雑な制御ロジックを「状態」と「遷移」に整理する
- 各状態ごとにアクチュエータの動作を明確に定義できる
- ヒステリシスでチャタリングを防止
- gpiozeroコールバックで手動介入を実現
- 遷移履歴の記録がデバッグと監査に有用
