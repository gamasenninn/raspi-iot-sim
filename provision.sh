#!/bin/bash
# =============================================================
# PI-CI 仮想Raspberry Pi プロビジョニングスクリプト
#
# PI-CI起動後にSSH経由でPi VM内に環境を構築する。
# ホスト側から実行: bash provision.sh
# =============================================================

set -e

PI_HOST="localhost"
PI_PORT="2222"
PI_USER="root"
SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=10"
APP_DIR="/opt/iot-app"

echo "=========================================="
echo "  PI-CI プロビジョニング"
echo "=========================================="

# --- Pi VMの起動待ち ---
echo "[1/5] Pi VMの起動を待機中..."
for i in $(seq 1 30); do
    if ssh $SSH_OPTS -p $PI_PORT $PI_USER@$PI_HOST "echo ok" 2>/dev/null; then
        echo "  -> Pi VM 接続成功"
        break
    fi
    if [ "$i" -eq 30 ]; then
        echo "  -> タイムアウト: Pi VMに接続できません"
        echo "     docker compose up raspi を実行してください"
        exit 1
    fi
    echo "  -> 待機中... ($i/30)"
    sleep 5
done

# --- SSHコマンド実行ヘルパー ---
run_ssh() {
    ssh $SSH_OPTS -p $PI_PORT $PI_USER@$PI_HOST "$@"
}

# --- パッケージインストール ---
echo "[2/5] システムパッケージをインストール中..."
run_ssh "apt-get update -qq && apt-get install -y -qq python3-pip python3-venv mosquitto-clients > /dev/null 2>&1"
echo "  -> 完了"

# --- アプリディレクトリ作成 ---
echo "[3/5] アプリケーションディレクトリを準備中..."
run_ssh "mkdir -p $APP_DIR"

# --- ファイル転送 ---
echo "[4/5] アプリケーションファイルを転送中..."
scp $SSH_OPTS -P $PI_PORT -r ./app/* $PI_USER@$PI_HOST:$APP_DIR/
echo "  -> 転送完了"

# --- Python仮想環境 + 依存関係 ---
echo "[5/5] Python環境をセットアップ中..."
run_ssh "cd $APP_DIR && python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt"
echo "  -> 完了"

echo ""
echo "=========================================="
echo "  プロビジョニング完了!"
echo "=========================================="
echo ""
echo "アプリ起動:"
echo "  ssh $SSH_OPTS -p $PI_PORT $PI_USER@$PI_HOST"
echo "  cd $APP_DIR && ./venv/bin/python main.py"
echo ""
echo "または一括実行:"
echo "  ssh $SSH_OPTS -p $PI_PORT $PI_USER@$PI_HOST 'cd $APP_DIR && ./venv/bin/python main.py'"
echo ""
echo "API確認 (Pi VM内のポート5000):"
echo "  curl http://localhost:5000/api/devices"
echo ""
echo "MQTT確認:"
echo "  mosquitto_sub -h localhost -p 1883 -t 'iot/devices/#'"
