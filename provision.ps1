# =============================================================
# PI-CI 仮想Raspberry Pi プロビジョニングスクリプト (PowerShell)
#
# Pi VM起動後に実行すると、アプリケーションの転送とセットアップを自動で行う。
#
# 使い方:
#   cd C:\app\RASPI
#   .\provision.ps1
# =============================================================

$PI_HOST = "localhost"
$PI_PORT = "2222"
$PI_USER = "root"
$SSH_OPTS = @("-o", "StrictHostKeyChecking=no", "-o", "UserKnownHostsFile=NUL", "-o", "ConnectTimeout=10")
$APP_DIR = "/opt/iot-app"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  PI-CI プロビジョニング" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan

# --- Pi VMの起動待ち ---
Write-Host "`n[1/5] Pi VMの起動を待機中..." -ForegroundColor Yellow
$connected = $false
for ($i = 1; $i -le 30; $i++) {
    $result = ssh @SSH_OPTS -p $PI_PORT "$PI_USER@$PI_HOST" "echo ok" 2>$null
    if ($result -eq "ok") {
        Write-Host "  -> Pi VM 接続成功" -ForegroundColor Green
        $connected = $true
        break
    }
    Write-Host "  -> 待機中... ($i/30)"
    Start-Sleep -Seconds 5
}
if (-not $connected) {
    Write-Host "  -> タイムアウト: Pi VMに接続できません" -ForegroundColor Red
    Write-Host "     docker compose up raspi を実行してください"
    exit 1
}

# --- パッケージインストール ---
Write-Host "`n[2/5] システムパッケージをインストール中..." -ForegroundColor Yellow
ssh @SSH_OPTS -p $PI_PORT "$PI_USER@$PI_HOST" "apt-get update -qq && apt-get install -y -qq python3-pip python3-venv mosquitto-clients > /dev/null 2>&1"
Write-Host "  -> 完了" -ForegroundColor Green

# --- アプリディレクトリ作成 ---
Write-Host "`n[3/5] アプリケーションディレクトリを準備中..." -ForegroundColor Yellow
ssh @SSH_OPTS -p $PI_PORT "$PI_USER@$PI_HOST" "mkdir -p $APP_DIR"

# --- ファイル転送 ---
Write-Host "`n[4/5] アプリケーションファイルを転送中..." -ForegroundColor Yellow
scp @SSH_OPTS -P $PI_PORT -r ./app/* "$PI_USER@${PI_HOST}:${APP_DIR}/"
Write-Host "  -> 転送完了" -ForegroundColor Green

# --- Python仮想環境 + 依存関係 ---
Write-Host "`n[5/5] Python環境をセットアップ中..." -ForegroundColor Yellow
Write-Host "  (QEMUエミュレーションのため時間がかかります。お待ちください...)" -ForegroundColor DarkYellow
ssh @SSH_OPTS -p $PI_PORT "$PI_USER@$PI_HOST" "cd $APP_DIR && python3 -m venv venv && ./venv/bin/pip install -q -r requirements.txt"
Write-Host "  -> 完了" -ForegroundColor Green

# --- 完了 ---
Write-Host ""
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "  プロビジョニング完了!" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "アプリ起動:" -ForegroundColor White
Write-Host "  ssh -o StrictHostKeyChecking=no -p 2222 root@localhost"
Write-Host '  cd /opt/iot-app && ./venv/bin/python main.py'
Write-Host ""
Write-Host "MQTT確認:" -ForegroundColor White
Write-Host '  docker exec mosquitto mosquitto_sub -t "iot/devices/#" -C 5'
Write-Host ""
Write-Host "ダッシュボード:" -ForegroundColor White
Write-Host "  start .\dashboard\index.html"
