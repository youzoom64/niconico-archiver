import pyautogui
import time
import logging
from .chrome_manager import ChromeManager

DEBUGLOG = logging.getLogger(__name__)

class RecordingController:
    def __init__(self, chrome_manager: ChromeManager, extension_coordinates: dict):
        self.chrome_manager = chrome_manager
        self.extension_coordinates = extension_coordinates
        self.recording_active = False

    def start_recording(self):
        """録画開始"""
        DEBUGLOG.info("録画開始処理")
        
        # 1. ウィンドウサイズを650pxに設定（クリック用）
        self.chrome_manager.driver.set_window_size(650, 500)
        time.sleep(0.3)
        
        # 2. 拡張機能アイコンクリック
        ext_x, ext_y = self.extension_coordinates['extension_icon']
        self.activate_and_click(ext_x, ext_y, "拡張機能アイコン")
        time.sleep(0.3)

        # 3. スタートボタンクリック（650pxのまま）
        start_x, start_y = self.extension_coordinates['start_button']
        adjusted_start_x, adjusted_start_y = self.chrome_manager.get_adjusted_coordinates(start_x, start_y)
        pyautogui.click(adjusted_start_x, adjusted_start_y)
        time.sleep(0.3)
        
        # 4. 録画開始後、200x400に変更
        self.chrome_manager.driver.set_window_size(200, 400)
        time.sleep(0.3)
        
        # 5. 再生・フルスクリーン（200x400のまま）
        self.chrome_manager.click_play_button()
        time.sleep(0.3)
        self.chrome_manager.click_fullscreen_button()
        
        self.recording_active = True

    def activate_and_click(self, base_x: int, base_y: int, description: str):
        # setup_window_and_activate()は呼ばない（サイズを変えないため）
        adjusted_x, adjusted_y = self.chrome_manager.get_adjusted_coordinates(base_x, base_y)
        pyautogui.click(adjusted_x, adjusted_y)
        return True

    def stop_recording(self):
        """録画停止（録画タブクローズ方式）"""
        DEBUGLOG.info("録画停止処理（録画タブクローズ）")
        
        success = self.chrome_manager.close_recording_tab_safely()
        
        if success:
            time.sleep(1)  # ダウンロード完了待機
            stop_time = int(time.time())
            self._save_stop_info(stop_time)
            self.recording_active = False
        else:
            DEBUGLOG.error("録画タブクローズに失敗")
            self.recording_active = False

    def _save_stop_info(self, stop_time: int):
        """停止時刻情報をJSONに保存"""
        import json
        import os
        
        data_dir = os.path.join('.', 'data')
        os.makedirs(data_dir, exist_ok=True)
        
        stop_info = {'stop_time': stop_time}
        stop_file = os.path.join(data_dir, f'stop_info_{stop_time}.json')
        
        with open(stop_file, 'w', encoding='utf-8') as f:
            json.dump(stop_info, f)
        DEBUGLOG.info(f"停止情報保存: {stop_file}")

    def is_recording(self) -> bool:
        """録画状態を取得"""
        return self.recording_active