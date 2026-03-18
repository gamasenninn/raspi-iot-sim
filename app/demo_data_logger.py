"""データロガー + 統計分析

全センサーの値を一定期間記録し、統計情報(平均/最大/最小/標準偏差)を算出。
CSVファイルに保存し、MQTT経由でサマリーレポートを配信。
実際のIoTシステムにおけるデータ収集パイプラインのプロトタイプ。
"""
import os, sys, time, json, csv, math
os.environ["GPIOZERO_PIN_FACTORY"] = "mock"
sys.path.insert(0, "/opt/iot-app")

from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin
import paho.mqtt.client as mqtt
from devices.sensors import (
    DHT22Temp, DHT22Humidity, BMP280Pressure,
    LightLevel, DistanceUltrasonic, SoilMoisture
)

Device.pin_factory = MockFactory(pin_class=MockPWMPin)

# センサー初期化
sensors = {
    "temperature": {"sensor": DHT22Temp(), "unit": "C"},
    "humidity": {"sensor": DHT22Humidity(), "unit": "%"},
    "pressure": {"sensor": BMP280Pressure(), "unit": "hPa"},
    "light": {"sensor": LightLevel(), "unit": "lux"},
    "distance": {"sensor": DistanceUltrasonic(), "unit": "cm"},
    "soil_moisture": {"sensor": SoilMoisture(), "unit": "%"},
}

# MQTT
client = mqtt.Client(client_id="data-logger")
client.connect("mosquitto", 1883, 60)
client.loop_start()

# データ収集
SAMPLES = 50
data_log = {name: [] for name in sensors}

print("=" * 65)
print(f"  Data Logger - {SAMPLES} samples collection")
print("=" * 65)

# CSV書き込み準備
csv_path = "/opt/iot-app/sensor_log.csv"
with open(csv_path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["sample", "timestamp"] + list(sensors.keys()))

    for i in range(SAMPLES):
        row = [i + 1, time.time()]
        values = {}

        for name, info in sensors.items():
            info["sensor"].update()
            val = info["sensor"].value
            data_log[name].append(val)
            row.append(val)
            values[name] = val

        writer.writerow(row)

        if (i + 1) % 10 == 0:
            print(f"  [{i+1:3d}/{SAMPLES}] "
                  f"T:{values['temperature']:5.1f}C "
                  f"H:{values['humidity']:5.1f}% "
                  f"P:{values['pressure']:7.1f}hPa "
                  f"L:{values['light']:6.1f}lux "
                  f"D:{values['distance']:6.1f}cm "
                  f"S:{values['soil_moisture']:5.1f}%")

        time.sleep(0.1)

print(f"\n  CSV saved: {csv_path}")


# === 統計分析 ===
def calc_stats(values):
    n = len(values)
    mean = sum(values) / n
    variance = sum((x - mean) ** 2 for x in values) / n
    std = math.sqrt(variance)
    return {
        "count": n,
        "mean": round(mean, 2),
        "min": round(min(values), 2),
        "max": round(max(values), 2),
        "std": round(std, 2),
        "range": round(max(values) - min(values), 2),
    }


print("\n" + "=" * 65)
print("  Statistical Analysis")
print("=" * 65)

report = {}
for name, values in data_log.items():
    stats = calc_stats(values)
    unit = sensors[name]["unit"]
    report[name] = stats
    print(f"\n  [{name}] ({unit})")
    print(f"    Mean: {stats['mean']:>8} | Std: {stats['std']:>8}")
    print(f"    Min:  {stats['min']:>8} | Max: {stats['max']:>8}")
    print(f"    Range: {stats['range']:>7} | Samples: {stats['count']}")

# MQTTでレポート配信
client.publish("iot/demo/data_report", json.dumps(report, indent=2))
print("\n  Report published to MQTT: iot/demo/data_report")

# === 異常検出 (平均±2σ 逸脱) ===
print("\n" + "=" * 65)
print("  Anomaly Detection (beyond mean +/- 2*std)")
print("=" * 65)

anomaly_count = 0
for name, values in data_log.items():
    stats = calc_stats(values)
    lower = stats["mean"] - 2 * stats["std"]
    upper = stats["mean"] + 2 * stats["std"]
    anomalies = [(i, v) for i, v in enumerate(values) if v < lower or v > upper]

    if anomalies:
        anomaly_count += len(anomalies)
        print(f"\n  [{name}] {len(anomalies)} anomalies detected:")
        for idx, val in anomalies[:5]:  # 最大5件表示
            direction = "HIGH" if val > upper else "LOW"
            print(f"    Sample #{idx+1}: {val:.2f} ({direction})")
        if len(anomalies) > 5:
            print(f"    ... and {len(anomalies)-5} more")

if anomaly_count == 0:
    print("\n  No anomalies detected.")

print(f"\n  Total anomalies: {anomaly_count}")

client.loop_stop()
client.disconnect()
print("\n" + "=" * 65)
print("  Data Logger complete!")
print("=" * 65)
