# セットアップマニュアル — Raspberry Pi IoT 仮想環境

## 概要

PI-CI (QEMU) を使った仮想Raspberry Pi OS上で、gpiozero MockFactoryによるGPIOシミュレーション環境を構築する手順書。

Windows 11 + Docker Desktop + PowerShell で動作確認済み。

---

## 前提条件

- **OS**: Windows 10/11
- **Docker Desktop**: インストール済み、WSL2バックエンド推奨
- **メモリ**: Docker Desktopに6GB以上割当推奨
- **ターミナル**: PowerShell（Git Bashはパス変換問題あり、後述）
- **ネットワーク**: Docker イメージのダウンロードにインターネット接続が必要

---

## ステップ1: プロジェクトの配置

```
C:\app\RASPI\              ← プロジェクトルート
├── docker-compose.yml
├── mosquitto\config\mosquitto.conf
├── app\                   ← IoTアプリケーション
└── dist\                  ← (自動生成) Pi VMディスクイメージ
```

---

## ステップ2: PI-CI 初期化（初回のみ）

PowerShell で実行:

```powershell
cd C:\app\RASPI

# PI-CIイメージをダウンロードし、ディスクイメージを初期化
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init
```

**所要時間**: 初回はイメージダウンロード（約1GB）で5〜10分。

成功すると `dist/` に以下が生成される:
- `distro.qcow2` — Raspberry Pi OS ディスクイメージ
- `kernel.img` — カーネル

---

## ステップ3: ディスクサイズ拡張（初回のみ）

デフォルトは2GB。IoTアプリ+Pythonパッケージ用に4GBに拡張:

```powershell
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G
```

確認プロンプトで `y` を入力。

---

## ステップ4: Mosquitto (MQTTブローカー) 起動

```powershell
docker compose up -d mosquitto
```

確認:
```powershell
docker compose ps
# mosquitto が Running であること
```

---

## ステップ5: Pi VM 起動

```powershell
docker compose up raspi
```

- フォアグラウンドで起動される（シリアルコンソール表示）
- 起動完了まで **30〜90秒** 待つ
- `Started ssh.service` が表示されたらSSH接続可能

**注意**: このターミナルは Pi VM のコンソールとして占有される。以降の操作は別のPowerShellウィンドウで行う。

---

## ステップ6: SSH接続確認

別のPowerShellウィンドウを開く:

```powershell
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
```

- ユーザー: `root`
- パスワード: なし
- `root@raspberrypi:~#` が表示されれば成功

---

## ステップ7: MQTT接続テスト

Pi VM 内で:

```bash
apt-get update && apt-get install -y mosquitto-clients

# ホスト名で接続テスト
mosquitto_pub -h mosquitto -p 1883 -t test -m "hello from pi"
```

エラーなく返ればOK。

### MQTT接続先について

| 接続元 | アドレス | 備考 |
|--------|---------|------|
| Pi VM 内 | `mosquitto:1883` | Dockerネットワーク名で接続 |
| Windows ホスト | `localhost:1883` | ポートフォワード経由 |
| Docker コンテナ間 | `mosquitto:1883` | 同一ネットワーク |

**注意**: `10.0.2.2` (QEMUゲートウェイ) は使えない場合がある。`mosquitto` ホスト名が確実。

---

## ステップ8: アプリケーションデプロイ

3つ目のPowerShellウィンドウで:

```powershell
cd C:\app\RASPI

# ディレクトリ作成
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost "mkdir -p /opt/iot-app"

# ファイル転送
scp -o StrictHostKeyChecking=no -P 2222 -r ./app/* root@localhost:/opt/iot-app/

# Python環境セットアップ (10〜30分かかる場合あり)
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost "cd /opt/iot-app && python3 -m venv venv && ./venv/bin/pip install -r requirements.txt"
```

**重要**: `pip install` はQEMUエミュレーション上で実行されるため非常に遅い。特に `gevent` のようなC拡張を含むパッケージは時間がかかる。辛抱強く待つこと。

---

## ステップ9: アプリ起動

Pi VM の SSH セッションで:

```bash
cd /opt/iot-app && ./venv/bin/python main.py
```

起動ログ:
```
==================================================
  Raspberry Pi IoT シミュレーション
==================================================
[Factory] MockFactory (MockPWMPin) を初期化しました
[Factory] 15 デバイスを登録しました
[Simulation] エンジン開始
[MQTT] mosquitto:1883 に接続中... (1/10)
[MQTT] ブローカーに接続しました
[API] http://0.0.0.0:5000/api/devices
```

---

## ステップ10: 動作確認

PowerShell から:

```powershell
# テレメトリ受信 (5件)
docker exec mosquitto mosquitto_sub -t "iot/devices/#" -C 5

# LED ON コマンド
docker exec mosquitto sh -c "mosquitto_pub -t 'iot/devices/led_red/command' -m '{\"action\":\"on\"}'"

# 状態確認
docker exec mosquitto mosquitto_sub -t "iot/devices/led_red/state" -C 1
```

---

## 安全な停止方法

**絶対に守ること**: Pi VM を強制終了しない。`distro.qcow2` が破損する。

### 正しい停止手順

```powershell
# 1. Pi VM をシャットダウン
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost "shutdown now"

# 2. 10秒待つ
Start-Sleep 10

# 3. Docker Compose 停止
docker compose down
```

### ディスクイメージが破損した場合

```powershell
# dist を削除して再初期化
Remove-Item -Recurse -Force dist
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G
# → ステップ7からやり直し
```

---

## トラブルシューティング

### Git Bash を使うとパスエラーになる

```
docker: Error response from daemon: .\dist;C%!(EXTRA string=is not a valid Windows path)
```

**原因**: Git Bash (MSYS2) がUnixパスをWindows形式に自動変換する。
**対策**: PowerShell を使う。やむを得ずGit Bashを使う場合は `MSYS_NO_PATHCONV=1` を先頭に付ける。

### Git Bash で TTY エラー

```
the input device is not a TTY. If you are using mintty, try prefixing the command with 'winpty'
```

**原因**: mintty が Docker の TTY と互換性がない。
**対策**: PowerShell を使う。

### pip install が終わらない

QEMUのARM→x86変換のため、ネイティブの5〜20倍遅い。特にC拡張のコンパイルを含むパッケージ (`gevent`, `numpy` 等) は10〜30分かかることがある。

**対策**: 辛抱強く待つ。軽量化したい場合は `gevent` を `requirements.txt` から外す。

### MQTT接続拒否 (Connection refused)

Pi VM 内から `10.0.2.2:1883` で接続できない場合:
- `mosquitto` ホスト名で試す
- Mosquitto コンテナのIPを調べる: `docker inspect mosquitto --format "{{range .NetworkSettings.Networks}}{{.IPAddress}}{{end}}"`

---

## ネットワーク構成図

```
Windows Host
├── PowerShell (操作用)
│
├── Docker Desktop (WSL2)
│   ├── mosquitto コンテナ
│   │   ├── :1883 (MQTT)
│   │   └── :9001 (WebSocket)
│   │
│   └── raspi コンテナ (PI-CI)
│       └── QEMU (qemu-system-aarch64)
│           └── Raspberry Pi OS (ARM64)
│               ├── IoTアプリ (:5000)
│               └── SSH (:22 → コンテナ:2222 → ホスト:2222)
│
└── Docker Network: iot-net (bridge)
    └── mosquitto ←→ raspi コンテナ間通信
```

---

## 2回目以降の起動手順 (クイックスタート)

```powershell
cd C:\app\RASPI
docker compose up -d mosquitto          # Mosquitto起動
docker compose up raspi                  # Pi VM起動 (別窓で)

# 別PowerShellで
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

ファイルを更新した場合は再転送:
```powershell
scp -o StrictHostKeyChecking=no -P 2222 -r ./app/* root@localhost:/opt/iot-app/
```
