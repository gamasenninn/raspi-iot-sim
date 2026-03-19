# 第2章 開発環境の構築

この章では、仮想Raspberry Pi環境を一からセットアップする手順を解説します。すべての手順はWindows 11で動作確認済みですが、macOSやLinuxでも同様の手順で構築できます。

## 2.1 必要なソフトウェア

以下のソフトウェアが必要です。すべて無料で入手できます。

| ソフトウェア | 用途 | 入手先 |
|------------|------|--------|
| Docker Desktop | コンテナ実行環境 | https://www.docker.com/products/docker-desktop |
| Python 3.11以上 | プログラミング言語 | https://www.python.org/downloads/ |
| PowerShell | ターミナル | Windows標準搭載 |

### Docker Desktopのインストール

1. Docker Desktop公式サイトからインストーラーをダウンロード
2. インストーラーを実行し、画面の指示に従う
3. インストール完了後、PCを再起動
4. Docker Desktopを起動し、WSL2バックエンドが有効であることを確認

> **Note:** Docker DesktopはWSL2バックエンドの使用を推奨します。設定画面の「General」→「Use the WSL 2 based engine」にチェックが入っていることを確認してください。

> **Note:** Docker Desktopの「Resources」→「Advanced」で、メモリを6GB以上に設定することを推奨します。仮想Raspberry Piは内部でQEMUエミュレータを動かすため、ある程度のメモリが必要です。

### Pythonのインストール

Pythonがインストール済みかどうかは、PowerShellで以下のコマンドを実行して確認できます。

```powershell
python --version
```

`Python 3.11.x` 以上が表示されればOKです。インストールされていない場合は、Python公式サイトからダウンロードしてインストールしてください。

> **Warning:** インストール時に「Add Python to PATH」にチェックを入れることを忘れないでください。これにチェックを入れないと、PowerShellからPythonコマンドが使えません。

## 2.2 プロジェクトの作成

まず、作業用のフォルダを作成します。PowerShellを開いて以下を実行してください。

```powershell
mkdir C:\app\RASPI
cd C:\app\RASPI
```

## 2.3 Docker Composeファイルの作成

Docker Composeは、複数のDockerコンテナをまとめて管理するためのツールです。本書では2つのコンテナを使います。

| コンテナ | 役割 |
|---------|------|
| mosquitto | MQTTブローカー（メッセージの中継サーバー） |
| raspi | 仮想Raspberry Pi（PI-CI） |

`C:\app\RASPI\docker-compose.yml` というファイルを作成し、以下の内容を記述します。

```yaml
services:
  mosquitto:
    image: eclipse-mosquitto:2
    container_name: mosquitto
    ports:
      - "1883:1883"
      - "9001:9001"
    volumes:
      - ./mosquitto/config:/mosquitto/config
      - mosquitto_data:/mosquitto/data
      - mosquitto_log:/mosquitto/log
    restart: unless-stopped
    networks:
      - iot-net
    healthcheck:
      test: ["CMD-SHELL", "mosquitto_sub -t '$$SYS/#' -C 1 -i healthcheck -W 3 || exit 1"]
      interval: 10s
      timeout: 5s
      retries: 5

  raspi:
    image: ptrsr/pi-ci
    container_name: raspi
    command: start
    stdin_open: true
    tty: true
    ports:
      - "2222:2222"
    volumes:
      - ./dist:/dist
    depends_on:
      mosquitto:
        condition: service_healthy
    networks:
      - iot-net

volumes:
  mosquitto_data:
  mosquitto_log:

networks:
  iot-net:
    driver: bridge
```

このファイルの各項目を説明しましょう。

### mosquittoサービス

```yaml
mosquitto:
    image: eclipse-mosquitto:2          # Mosquitto公式イメージのバージョン2を使用
    container_name: mosquitto           # コンテナに名前をつける
    ports:
      - "1883:1883"                     # MQTT標準ポート
      - "9001:9001"                     # WebSocket用ポート（ダッシュボードで使用）
```

- **ポート1883**: MQTT通信用のポートです。IoTデバイスはこのポートを使ってメッセージを送受信します
- **ポート9001**: WebSocket用のポートです。Webブラウザからダッシュボードを表示する際に使います

### raspiサービス

```yaml
raspi:
    image: ptrsr/pi-ci                 # PI-CIイメージ
    command: start                      # 仮想Raspberry Piを起動
    stdin_open: true                    # 標準入力を開いておく（コンソール操作用）
    tty: true                          # 擬似端末を割り当てる
    ports:
      - "2222:2222"                    # SSH用ポート
    volumes:
      - ./dist:/dist                   # ディスクイメージの保存先
```

- **ポート2222**: SSH（リモート接続）用のポートです。このポートを通じて、仮想Raspberry Piにログインします

## 2.4 Mosquittoの設定

MQTTブローカーの設定ファイルを作成します。

```powershell
mkdir C:\app\RASPI\mosquitto\config -Force
```

`C:\app\RASPI\mosquitto\config\mosquitto.conf` を以下の内容で作成します。

```
per_listener_settings false
allow_anonymous true

listener 1883

listener 9001
protocol websockets
```

各項目の意味：
- `per_listener_settings false`: セキュリティ設定を全リスナーで共有する
- `allow_anonymous true`: 認証なしで接続を許可する（開発環境用）
- `listener 1883`: 通常のMQTT接続をポート1883で受け付ける
- `listener 9001` + `protocol websockets`: WebSocket接続をポート9001で受け付ける

> **Warning:** `allow_anonymous true` は開発環境専用の設定です。本番環境では必ず認証を設定してください。

## 2.5 仮想Raspberry Piの初期化

ここからが本書の核心部分です。PI-CIを使って仮想Raspberry Piのディスクイメージを作成します。

### ステップ1: ディスクイメージの初期化

PowerShellで以下を実行します。

```powershell
cd C:\app\RASPI
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init
```

初回実行時は、PI-CIのDockerイメージ（約1GB）のダウンロードが行われるため、5〜10分程度かかります。

処理が完了すると、`dist` フォルダに以下のファイルが生成されます。

| ファイル | サイズ | 説明 |
|---------|--------|------|
| distro.qcow2 | 約800MB | Raspberry Pi OSのディスクイメージ |
| kernel.img | 約20MB | Linuxカーネル |

`qcow2` はQEMU独自のディスクイメージ形式で、「使用した分だけディスクを消費する」という特徴があります。

### ステップ2: ディスクサイズの拡張

デフォルトのディスクサイズは2GBですが、Pythonパッケージのインストールなどに空き容量が必要です。4GBに拡張しましょう。

```powershell
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G
```

確認メッセージが表示されたら `y` と入力してEnterを押します。

```
Resizing can damage the image, make sure to make a backup. Continue? [y/n] y
[INFO] Resizing to 4294967296 bytes ...
[INFO] Resize successful
```

### ステップ3: Mosquittoの起動

```powershell
docker compose up -d mosquitto
```

`-d` オプションは「バックグラウンドで実行」という意味です。MQTTブローカーは常に動いている必要があるため、バックグラウンドで起動します。

起動を確認しましょう。

```powershell
docker compose ps
```

`mosquitto` のステータスが `running` であればOKです。

### ステップ4: 仮想Raspberry Piの起動

```powershell
docker compose up raspi
```

今度は `-d` をつけずに実行します。仮想Raspberry Piのコンソール（画面出力）を直接見るためです。

起動が始まると、大量のログが流れます。これはLinuxカーネルの起動メッセージです。30〜90秒ほど待つと、以下のようなメッセージが表示されます。

```
raspi  | [  OK  ] Started ssh.service - OpenBSD Secure Shell server.
raspi  | [  OK  ] Reached target multi-user.target - Multi-User System.
```

これが表示されれば、仮想Raspberry Piの起動は完了です。

> **Note:** このターミナルは仮想Raspberry Piのコンソールとして占有されます。以降の操作は、**別のPowerShellウィンドウ**を開いて行ってください。

## 2.6 仮想Raspberry PiへのSSH接続

SSHとは、ネットワーク経由で別のコンピュータにリモートログインするための仕組みです。新しいPowerShellウィンドウを開き、以下を実行します。

```powershell
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
```

各オプションの意味：
- `-o StrictHostKeyChecking=no`: 初回接続時の確認をスキップする
- `-p 2222`: ポート2222を使う（仮想Raspberry PiのSSHポート）
- `root@localhost`: ユーザー名 `root` で `localhost` に接続する

接続に成功すると、以下のようなプロンプトが表示されます。

```
root@raspberrypi:~#
```

おめでとうございます！仮想Raspberry Piの中に入ることができました。ここからは、本物のRaspberry Piとまったく同じ操作ができます。

### 仮想Raspberry Piの中を確認してみよう

```bash
# OSの情報を確認
cat /etc/os-release

# CPUの情報を確認
uname -m
```

出力結果：
```
PRETTY_NAME="Debian GNU/Linux 12 (bookworm)"
NAME="Debian GNU/Linux"
VERSION_ID="12"
```

```
aarch64
```

`aarch64` は64ビットARMアーキテクチャを意味します。本物のRaspberry Pi 4/5と同じCPUアーキテクチャがエミュレーションされています。

## 2.7 MQTT接続テスト

仮想Raspberry PiからMQTTブローカー（Mosquitto）に接続できることを確認しましょう。

まず、MQTTクライアントツールをインストールします。

```bash
apt-get update && apt-get install -y mosquitto-clients
```

> **Note:** `apt-get update` はパッケージリストの更新、`apt-get install` はパッケージのインストールです。QEMUエミュレーション上で実行されるため、通常よりも時間がかかります。

インストールが完了したら、テストメッセージを送信してみましょう。

```bash
mosquitto_pub -h mosquitto -p 1883 -t test/hello -m "Hello from Raspberry Pi!"
```

各オプションの意味：
- `-h mosquitto`: 接続先のホスト名（Docker Composeのサービス名で接続できる）
- `-p 1883`: MQTTのポート番号
- `-t test/hello`: 送信先のトピック（メッセージの宛先）
- `-m "Hello from ..."`: 送信するメッセージの内容

エラーが表示されなければ、送信成功です。

### 受信テスト

3つ目のPowerShellウィンドウを開き、以下を実行します。

```powershell
docker exec mosquitto mosquitto_sub -t "test/#" -v
```

この状態で、仮想Raspberry Piのターミナルから再度メッセージを送信すると：

```bash
mosquitto_pub -h mosquitto -p 1883 -t test/hello -m "Hello again!"
```

3つ目のウィンドウに以下が表示されるはずです：

```
test/hello Hello again!
```

通信が確認できました。仮想Raspberry Pi → Mosquitto → Windowsホスト の経路でメッセージが正しく流れています。

## 2.8 Pythonアプリケーション環境のセットアップ

仮想Raspberry Pi内にPython仮想環境を構築し、必要なライブラリをインストールします。

### アプリケーションディレクトリの作成

仮想Raspberry Pi内（SSHセッション）で：

```bash
mkdir -p /opt/iot-app
```

### ファイルの転送

Windowsホスト側のPowerShellで：

```powershell
cd C:\app\RASPI
scp -o StrictHostKeyChecking=no -P 2222 -r ./app/* root@localhost:/opt/iot-app/
```

`scp` はSSH経由でファイルをコピーするコマンドです。Windowsホストの `app/` フォルダ内のすべてのファイルを、仮想Raspberry Piの `/opt/iot-app/` にコピーします。

### Python仮想環境の構築

仮想Raspberry Pi内で：

```bash
cd /opt/iot-app
python3 -m venv venv
./venv/bin/pip install -r requirements.txt
```

> **Warning:** `pip install` はQEMUエミュレーション上で実行されるため、ネイティブの5〜20倍の時間がかかります。特に `gevent` のようなC拡張を含むパッケージは10〜30分かかることがあります。コーヒーでも飲みながら気長に待ちましょう。

インストールが完了したら、環境構築は完了です。

## 2.9 安全な停止方法

仮想Raspberry Piの停止方法は非常に重要です。

> **Warning:** 仮想Raspberry Piを強制終了（`docker kill` や `Ctrl+C`）すると、ディスクイメージ（`distro.qcow2`）が破損する可能性があります。必ず以下の手順で安全に停止してください。

### 正しい停止手順

プロジェクトには停止用スクリプトが用意されています。

```powershell
cd C:\app\RASPI
.\stop.ps1
```

このスクリプトは以下を自動で行います：
1. SSHで仮想Raspberry Piに `shutdown now` を送信
2. 10秒待機（シャットダウン完了を待つ）
3. Docker Compose停止

手動で行う場合は以下の通りです。

```powershell
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost "shutdown now"
Start-Sleep 10
docker compose down
```

### ディスクイメージが破損した場合

万が一破損してしまった場合は、以下の手順で復旧できます。

```powershell
# distフォルダを削除して再初期化
Remove-Item -Recurse -Force dist
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init
docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G
```

ただし、仮想Raspberry Pi内にインストールしたパッケージやファイルはすべて失われます。

## 2.10 自動化スクリプト

本書のプロジェクトには、環境の起動・プロビジョニング・停止を自動化するPowerShellスクリプトが付属しています。

| スクリプト | 用途 |
|-----------|------|
| `start.ps1` | PI-CI初期化（初回のみ）+ Mosquitto起動 + Pi VM起動 |
| `provision.ps1` | Pi VMへのアプリ転送 + Python環境セットアップ（自動待機付き） |
| `stop.ps1` | Pi VM安全シャットダウン + Docker Compose停止 |

### 初回セットアップの場合

```powershell
cd C:\app\RASPI

# ウィンドウ1: 環境起動（初回はPI-CI初期化も行う）
.\start.ps1

# ウィンドウ2: アプリ転送+セットアップ（Pi VM起動を自動待機）
.\provision.ps1

# ウィンドウ3: アプリ起動
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

`provision.ps1` は以下を自動で行います：

1. Pi VMのSSH接続可能を最大150秒待機
2. システムパッケージのインストール（`python3-pip`, `python3-venv`, `mosquitto-clients`）
3. `app/` フォルダ内の全ファイルを Pi VM の `/opt/iot-app/` に転送
4. Python仮想環境の作成と依存パッケージのインストール

### 2回目以降のクイックスタート

```powershell
cd C:\app\RASPI

# ウィンドウ1: 起動（初期化はスキップされる）
.\start.ps1

# ウィンドウ2: アプリ起動（環境は前回の状態が維持されている）
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

2回目以降は、Pi VMのディスクイメージに前回の環境が保存されているため、`provision.ps1` の再実行は不要です。ただし、`app/` フォルダのファイルを更新した場合は、再度転送が必要です。

```powershell
# ファイル更新時のみ再転送
scp -o StrictHostKeyChecking=no -P 2222 -r ./app/* root@localhost:/opt/iot-app/
```

### 停止

```powershell
.\stop.ps1
```

## 2.11 この章のまとめ

この章では、以下の環境を構築しました。

- **Docker Compose** で2つのサービス（Mosquitto + PI-CI）を管理
- **PI-CI** で仮想Raspberry Pi OS（Bookworm ARM64）を起動
- **SSH** で仮想Raspberry Piにリモート接続
- **MQTT** で仮想Raspberry PiとMosquitto間の通信を確認
- **Python仮想環境** に必要なライブラリをインストール

次の章では、この仮想Raspberry Piの内部構造を詳しく見ていきます。
