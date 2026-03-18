"""デバイスファクトリ - gpiozero MockFactoryで全デバイスを生成"""
import os
from gpiozero import Device
from gpiozero.pins.mock import MockFactory, MockPWMPin

from .outputs import create_output_devices
from .inputs import create_input_devices
from .sensors import create_software_sensors


def init_mock_factory():
    """MockFactoryを初期化。実機では呼ばない。"""
    if os.environ.get("GPIOZERO_PIN_FACTORY") == "mock":
        Device.pin_factory = MockFactory(pin_class=MockPWMPin)
        print("[Factory] MockFactory (MockPWMPin) を初期化しました")
    else:
        print("[Factory] 実機のピンファクトリを使用します")


# デバイスレジストリ: 全デバイスをname -> infoで管理
_registry = {}


def get_registry():
    return _registry


def create_all_devices():
    """全デバイスを生成してレジストリに登録"""
    init_mock_factory()

    outputs = create_output_devices()
    inputs = create_input_devices()
    sensors = create_software_sensors()

    for name, info in {**outputs, **inputs, **sensors}.items():
        _registry[name] = info

    print(f"[Factory] {len(_registry)} デバイスを登録しました")
    return _registry
