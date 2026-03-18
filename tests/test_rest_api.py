"""インテグレーションテスト: REST APIエンドポイント"""
import json
import pytest


class TestHealthEndpoint:
    def test_health_returns_200(self, flask_client):
        resp = flask_client.get("/api/health")
        assert resp.status_code == 200

    def test_health_has_device_count(self, flask_client):
        resp = flask_client.get("/api/health")
        data = resp.get_json()
        assert data["status"] == "ok"
        assert data["devices"] == 15


class TestListDevices:
    def test_returns_all_devices(self, flask_client):
        resp = flask_client.get("/api/devices")
        data = resp.get_json()
        assert len(data) == 15

    def test_each_device_has_required_fields(self, flask_client):
        resp = flask_client.get("/api/devices")
        data = resp.get_json()
        for name, info in data.items():
            assert "type" in info, f"{name} に type がない"
            assert "category" in info, f"{name} に category がない"
            assert "state" in info, f"{name} に state がない"
            assert "actions" in info, f"{name} に actions がない"
            assert isinstance(info["actions"], list)


class TestGetDevice:
    def test_get_existing_device(self, flask_client):
        resp = flask_client.get("/api/devices/led_red")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["name"] == "led_red"
        assert data["type"] == "output"

    def test_get_sensor(self, flask_client):
        resp = flask_client.get("/api/devices/dht22_temperature")
        assert resp.status_code == 200
        data = resp.get_json()
        assert "value" in data["state"]
        assert "unit" in data["state"]

    def test_get_unknown_device_returns_404(self, flask_client):
        resp = flask_client.get("/api/devices/nonexistent")
        assert resp.status_code == 404


class TestDeviceAction:
    def test_led_on(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "on"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["ok"] is True
        assert data["state"]["on"] is True

    def test_led_off(self, flask_client):
        flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "on"}),
            content_type="application/json",
        )
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "off"}),
            content_type="application/json",
        )
        assert resp.get_json()["state"]["on"] is False

    def test_servo_set_value(self, flask_client):
        resp = flask_client.post(
            "/api/devices/servo/action",
            data=json.dumps({"action": "set", "value": "0.5"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert abs(resp.get_json()["state"]["value"] - 0.5) < 0.01

    def test_motor_forward_stop(self, flask_client):
        resp = flask_client.post(
            "/api/devices/motor/action",
            data=json.dumps({"action": "forward"}),
            content_type="application/json",
        )
        assert resp.get_json()["state"]["speed"] > 0

        resp = flask_client.post(
            "/api/devices/motor/action",
            data=json.dumps({"action": "stop"}),
            content_type="application/json",
        )
        assert resp.get_json()["state"]["speed"] == 0.0

    def test_missing_action_returns_400(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({}),
            content_type="application/json",
        )
        assert resp.status_code == 400

    def test_invalid_action_returns_400(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_red/action",
            data=json.dumps({"action": "fly"}),
            content_type="application/json",
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert "available" in data

    def test_action_on_unknown_device_returns_404(self, flask_client):
        resp = flask_client.post(
            "/api/devices/nonexistent/action",
            data=json.dumps({"action": "on"}),
            content_type="application/json",
        )
        assert resp.status_code == 404

    def test_rgb_set_color(self, flask_client):
        resp = flask_client.post(
            "/api/devices/led_rgb/action",
            data=json.dumps({"action": "set", "value": "0.5,1.0,0.3"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        color = resp.get_json()["state"]["color"]
        assert abs(color[0] - 0.5) < 0.01
        assert abs(color[1] - 1.0) < 0.01
        assert abs(color[2] - 0.3) < 0.01

    def test_button_press(self, flask_client):
        resp = flask_client.post(
            "/api/devices/button/action",
            data=json.dumps({"action": "press"}),
            content_type="application/json",
        )
        assert resp.status_code == 200
        assert resp.get_json()["state"]["pressed"] is True
