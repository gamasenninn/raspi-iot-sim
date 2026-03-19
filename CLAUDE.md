# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Raspberry Pi IoT simulation environment that teaches IoT development without hardware. Uses PI-CI (QEMU-based virtual Raspberry Pi OS) + gpiozero MockFactory to simulate 15 GPIO devices, with MQTT/REST/WebSocket protocols and a web dashboard. Documentation and book are in Japanese.

## Commands

### Running Tests
```bash
# All 66 tests
python -m pytest tests/ -v

# Unit tests only (no infrastructure needed)
python -m pytest tests/test_devices.py tests/test_sensors.py tests/test_mqtt_format.py -v

# Single test file
python -m pytest tests/test_rest_api.py -v

# By marker (integration requires Mosquitto on localhost:1883; e2e requires full Pi VM stack)
python -m pytest -m integration
python -m pytest -m e2e
```

### Environment Lifecycle
```bash
# Bash (Linux/macOS/WSL)
./start.sh          # Init PI-CI disk image + start Docker Compose (Mosquitto + QEMU VM)
./provision.sh      # Transfer app to VM, create venv, install deps (run in separate terminal after start)
./stop.sh           # Graceful shutdown (MUST use this — force-kill risks qcow2 corruption)

# PowerShell (Windows)
.\start.ps1 / .\provision.ps1 / .\stop.ps1
```

### Running the App (inside Pi VM)
```bash
ssh -o StrictHostKeyChecking=no -p 2222 root@localhost
cd /opt/iot-app && ./venv/bin/python main.py
```

## Architecture

**Docker Compose network (`iot-net`)** runs two containers:
- **Mosquitto** MQTT broker — `:1883` (MQTT), `:9001` (WebSocket)
- **PI-CI** QEMU VM — `:2222` (SSH), `:5000` (REST/WebSocket API)

**Python app (`app/`)** runs inside the Pi VM:
- `main.py` — entry point: creates devices, starts simulation engine, MQTT, REST API, WebSocket server
- `config/settings.py` — MQTT broker hostname (`mosquitto`), ports, simulation interval
- `config/pin_map.py` — GPIO pin assignments (change for hardware migration)
- `devices/factory.py` — creates all 15 devices via gpiozero MockFactory, maintains global registry
- `devices/outputs.py` — LED, PWMLED, RGBLED, Buzzer, Servo, Motor
- `devices/inputs.py` — Button, MotionSensor, LineSensor
- `devices/sensors.py` — DHT22, BMP280, BH1750, ultrasonic, soil moisture (software-simulated, no GPIO)
- `simulation/engine.py` — daemon thread updating sensors every 1s and randomly triggering input events
- `protocols/mqtt_client.py` — publishes to `iot/devices/{name}/state`, subscribes to `iot/devices/+/command`
- `protocols/rest_api.py` — Flask REST API (`/api/health`, `/api/devices`, `/api/devices/<name>/action`)
- `protocols/websocket_server.py` — Flask-SocketIO broadcasting device state updates

**Device registry pattern**: each device is a dict with `device`, `type`, `category`, `get_state()` callable, and `actions` dict — uniform interface across all 15 devices.

**Dashboard (`dashboard/index.html`)**: standalone HTML using MQTT.js (CDN) and Chart.js for real-time monitoring.

## MQTT Topics

- Telemetry (publish): `iot/devices/{name}/state` — JSON with device state + timestamp
- Commands (subscribe): `iot/devices/+/command` — `{"action": "on/off/set/toggle", "value": "..."}`

## Test Structure

Tests use pytest with fixtures in `conftest.py`. Unit tests create devices via MockFactory independently of the running app. Integration tests (`test_mqtt_integration.py`) need a live Mosquitto broker. E2E tests (`test_e2e.py`) need the full Docker stack running.

## Key Dependencies

Python: gpiozero 2.0+, paho-mqtt 1.6-1.9, flask 3.0+, flask-socketio 5.3+, gevent 23.0+
