# =============================================================
# IoT開発環境 起動スクリプト (PowerShell)
#
# 使い方:
#   cd C:\app\RASPI
#   .\start.ps1
# =============================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Raspberry Pi IoT 開発環境 起動" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# --- 1. PI-CIの初期化 (初回のみ) ---
if (-not (Test-Path ".\dist\distro.qcow2")) {
    Write-Host "`n[1/3] PI-CI 初期化中 (初回のみ)..." -ForegroundColor Yellow
    docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci init
    Write-Host "  -> ディスクサイズを4GBに拡張中..."
    docker run --rm -it -v "$PWD\dist:/dist" ptrsr/pi-ci resize 4G
    Write-Host "  -> 完了" -ForegroundColor Green
} else {
    Write-Host "`n[1/3] PI-CI 初期化済み (スキップ)" -ForegroundColor DarkGray
}

# --- 2. Docker Compose起動 ---
Write-Host "`n[2/3] Mosquitto 起動中..." -ForegroundColor Yellow
docker compose up -d mosquitto
Write-Host "  -> 完了" -ForegroundColor Green

# --- 3. Pi VM起動 ---
Write-Host "`n[3/3] Pi VM 起動中..." -ForegroundColor Yellow
Write-Host ""
Write-Host "  別のPowerShellウィンドウで以下を実行してください:" -ForegroundColor White
Write-Host "    cd C:\app\RASPI" -ForegroundColor White
Write-Host "    .\provision.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  終了時は必ず Pi VM 内で 'shutdown now' を実行してください。" -ForegroundColor Red
Write-Host "  (強制終了するとディスクイメージが破損します)" -ForegroundColor Red
Write-Host ""

docker compose up raspi
