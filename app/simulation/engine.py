"""シミュレーションエンジン

バックグラウンドスレッドで各デバイスの状態を定期更新し、
入力デバイスのイベント(ボタン押下、モーション検知等)を発生させる。
"""
import time
import random
import threading
from config.settings import SIM_INTERVAL


class SimulationEngine:
    def __init__(self, registry):
        self._registry = registry
        self._running = False
        self._thread = None
        self._tick = 0

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        print("[Simulation] エンジン開始")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("[Simulation] エンジン停止")

    def _loop(self):
        while self._running:
            try:
                self._update_sensors()
                self._simulate_inputs()
                self._tick += 1
            except Exception as e:
                print(f"[Simulation] エラー: {e}")
            time.sleep(SIM_INTERVAL)

    def _update_sensors(self):
        """ソフトウェアセンサーの値を更新"""
        for name, info in self._registry.items():
            if info["type"] == "sensor":
                info["device"].update()

    def _simulate_inputs(self):
        """入力デバイスのイベントをランダムに発生"""
        # ボタン: 約10秒に1回押す
        if "button" in self._registry and random.random() < 0.1:
            btn = self._registry["button"]
            btn["actions"]["press"]()
            threading.Timer(0.2, btn["actions"]["release"]).start()

        # モーションセンサー: 約15秒に1回検知
        if "motion_sensor" in self._registry and random.random() < 0.07:
            ms = self._registry["motion_sensor"]
            ms["actions"]["trigger"]()
            threading.Timer(3.0, ms["actions"]["clear"]).start()

        # ラインセンサー: 約20秒に1回検知
        if "line_sensor" in self._registry and random.random() < 0.05:
            ls = self._registry["line_sensor"]
            ls["actions"]["detect"]()
            threading.Timer(1.0, ls["actions"]["clear"]).start()
