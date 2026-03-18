# =============================================================
# IoT開発環境 安全停止スクリプト (PowerShell)
#
# 使い方:
#   cd C:\app\RASPI
#   .\stop.ps1
# =============================================================

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  Raspberry Pi IoT 開発環境 停止" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

$SSH_OPTS = @("-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL", "-o", "ConnectTimeout=5")

# --- Pi VMをシャットダウン ---
Write-Host "`n[1/2] Pi VM をシャットダウン中..." -ForegroundColor Yellow
try {
    ssh @SSH_OPTS -p 2222 root@localhost "shutdown now" 2>$null
    Write-Host "  -> シャットダウンコマンド送信" -ForegroundColor Green
    Write-Host "  -> 10秒待機中..."
    Start-Sleep -Seconds 10
} catch {
    Write-Host "  -> Pi VMに接続できません (既に停止済み?)" -ForegroundColor DarkYellow
}

# --- Docker Compose停止 ---
Write-Host "`n[2/2] Docker Compose 停止中..." -ForegroundColor Yellow
docker compose down
Write-Host "  -> 完了" -ForegroundColor Green
