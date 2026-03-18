"""REST API テスト — Pi VM 内から自分自身のAPIを叩く"""
import os, sys, time, json
sys.path.insert(0, "/opt/iot-app")
import requests

BASE = "http://localhost:5000/api"

print("=" * 55)
print("  REST API テスト")
print("=" * 55)

# 1. ヘルスチェック
print("\n[1] GET /api/health")
r = requests.get(f"{BASE}/health")
print(f"  Status: {r.status_code}")
print(f"  Body: {json.dumps(r.json(), indent=2)}")

# 2. 全デバイス一覧
print("\n[2] GET /api/devices")
r = requests.get(f"{BASE}/devices")
devices = r.json()
print(f"  デバイス数: {len(devices)}")
for name, info in devices.items():
    print(f"  - {name} [{info['category']}] state={info['state']}")

# 3. 特定デバイス取得
print("\n[3] GET /api/devices/servo")
r = requests.get(f"{BASE}/devices/servo")
print(f"  {json.dumps(r.json(), indent=2)}")

# 4. コマンド実行: LED ON
print("\n[4] POST /api/devices/led_red/action {on}")
r = requests.post(f"{BASE}/devices/led_red/action", json={"action": "on"})
print(f"  Status: {r.status_code}")
print(f"  Result: {r.json()}")

# 5. コマンド実行: サーボ位置設定
print("\n[5] POST /api/devices/servo/action {set 0.75}")
r = requests.post(f"{BASE}/devices/servo/action", json={"action": "set", "value": "0.75"})
print(f"  Status: {r.status_code}")
print(f"  Result: {r.json()}")

# 6. コマンド実行: RGB LED
print("\n[6] POST /api/devices/led_rgb/action {set 0.2,0.8,0.3}")
r = requests.post(f"{BASE}/devices/led_rgb/action", json={"action": "set", "value": "0.2,0.8,0.3"})
print(f"  Status: {r.status_code}")
print(f"  Result: {r.json()}")

# 7. コマンド実行: モーター
print("\n[7] POST /api/devices/motor/action {forward}")
r = requests.post(f"{BASE}/devices/motor/action", json={"action": "forward"})
print(f"  Result: {r.json()}")

# 8. 存在しないデバイス
print("\n[8] GET /api/devices/nonexistent (エラーテスト)")
r = requests.get(f"{BASE}/devices/nonexistent")
print(f"  Status: {r.status_code}")
print(f"  Error: {r.json()}")

# 9. 不正なアクション
print("\n[9] POST /api/devices/led_red/action {invalid} (エラーテスト)")
r = requests.post(f"{BASE}/devices/led_red/action", json={"action": "fly"})
print(f"  Status: {r.status_code}")
print(f"  Error: {r.json()}")

# 10. LED OFF で元に戻す
print("\n[10] クリーンアップ")
requests.post(f"{BASE}/devices/led_red/action", json={"action": "off"})
requests.post(f"{BASE}/devices/motor/action", json={"action": "stop"})
print("  完了")
