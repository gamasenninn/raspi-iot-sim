#!/bin/bash
# =============================================================
# IoT開発環境 安全停止スクリプト
#
# Pi VMを安全にシャットダウンしてからコンテナを停止する。
# 強制停止するとqcow2ディスクイメージが破損するため、
# 必ずこのスクリプトで停止すること。
# =============================================================

SSH_OPTS="-o StrictHostKeyChecking=no -o UserKnownHostsFile=/dev/null -o ConnectTimeout=5"

echo "=========================================="
echo "  Raspberry Pi IoT 開発環境 停止"
echo "=========================================="

# Pi VMをシャットダウン
echo "[1/2] Pi VM をシャットダウン中..."
if ssh $SSH_OPTS -p 2222 root@localhost "shutdown now" 2>/dev/null; then
    echo "  -> シャットダウンコマンド送信"
    echo "  -> 10秒待機中..."
    sleep 10
else
    echo "  -> Pi VMに接続できません (既に停止済み?)"
fi

# Docker Compose停止
echo "[2/2] Docker Compose 停止中..."
docker compose down
echo "  -> 完了"
