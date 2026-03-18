#!/bin/bash
# =============================================================
# IoT開発環境 起動スクリプト
# =============================================================

set -e

# Git Bash (MSYS2) のパス自動変換を無効化
export MSYS_NO_PATHCONV=1

echo "=========================================="
echo "  Raspberry Pi IoT 開発環境 起動"
echo "=========================================="

# --- 1. PI-CIの初期化 (初回のみ) ---
if [ ! -f "./dist/distro.qcow2" ]; then
    echo "[1/3] PI-CI 初期化中 (初回のみ)..."
    docker run --rm -v ./dist:/dist ptrsr/pi-ci init
    echo "  -> ディスクサイズを4GBに拡張中..."
    docker run --rm -v ./dist:/dist ptrsr/pi-ci resize 4G
    echo "  -> 完了"
else
    echo "[1/3] PI-CI 初期化済み (スキップ)"
fi

# --- 2. Docker Compose起動 ---
echo "[2/3] Docker Compose 起動中..."
docker compose up -d mosquitto
echo "  -> Mosquitto起動完了"

echo ""
echo "[3/3] Pi VM 起動中..."
echo "  コンソールが表示されます。ログインプロンプトが出たらEnterを押してください。"
echo "  別ターミナルから provision.sh を実行してアプリをセットアップできます。"
echo ""
echo "  終了時は必ず Pi VM 内で 'shutdown now' を実行してください。"
echo "  (強制終了するとディスクイメージが破損します)"
echo ""

docker compose up raspi
