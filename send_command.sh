#!/bin/bash
# =============================================================
# MQTTコマンド送信ヘルパー
#
# 使い方:
#   bash send_command.sh <デバイス名> <アクション> [値]
#
# 例:
#   bash send_command.sh led_red on
#   bash send_command.sh led_pwm set 0.5
#   bash send_command.sh led_rgb set "1.0,0.0,0.5"
#   bash send_command.sh servo set 0.5
#   bash send_command.sh motor forward
#   bash send_command.sh button press
# =============================================================

DEVICE=${1:?"使い方: $0 <デバイス名> <アクション> [値]"}
ACTION=${2:?"使い方: $0 <デバイス名> <アクション> [値]"}
VALUE=$3

if [ -n "$VALUE" ]; then
    PAYLOAD="{\"action\": \"$ACTION\", \"value\": \"$VALUE\"}"
else
    PAYLOAD="{\"action\": \"$ACTION\"}"
fi

TOPIC="iot/devices/$DEVICE/command"

echo "送信: $TOPIC <- $PAYLOAD"
mosquitto_pub -h localhost -p 1883 -t "$TOPIC" -m "$PAYLOAD"
