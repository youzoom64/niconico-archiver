import time
import psutil
import subprocess
import win32gui
import win32con
import win32process
import logging
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from screeninfo import get_monitors

DEBUGLOG = logging.getLogger(__name__)

class ChromeManager:
    def __init__(self, chrome_path: str, user_data_dir: str, profile_name: str, debug_port: str, target_monitor: int):
        self.chrome_path = chrome_path
        self.user_data_dir = user_data_dir
        self.profile_name = profile_name
        self.debug_port = debug_port
        self.target_monitor = target_monitor
        self.driver = None
        self.current_tab_handle = None
        self.recording_tab_handle = None

    def is_debug_chrome_running(self) -> bool:
        """デバッグモードのChromeが起動中かチェック"""
        DEBUGLOG.debug("デバッグChrome存在チェック開始")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']).lower()
                if self.user_data_dir.lower() in cmdline and f"--remote-debugging-port={self.debug_port}" in cmdline:
                    DEBUGLOG.info(f"デバッグChrome発見! PID: {proc.info['pid']}")
                    return True
        DEBUGLOG.info("デバッグChrome存在: False")
        return False

    def get_debug_chrome_pid(self) -> int:
        """デバッグChromeのプロセスIDを取得"""
        DEBUGLOG.debug("デバッグChrome PID取得開始")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
                cmdline = " ".join(proc.info['cmdline']).lower()
                has_user_data = self.user_data_dir.lower() in cmdline
                has_debug_port = f"--remote-debugging-port={self.debug_port}" in cmdline
                is_main_process = "--type=" not in cmdline
                if has_user_data and has_debug_port and is_main_process:
                    DEBUGLOG.info(f"デバッグChrome メインプロセス特定: PID {proc.info['pid']}")
                    return proc.info['pid']
        DEBUGLOG.warning("デバッグChrome メインプロセスが見つかりません")
        return None

    def launch_chrome_debug_mode(self) -> bool:
        """デバッグモードのChromeを起動"""
        DEBUGLOG.info("デバッグChrome起動開始")
        subprocess.Popen([
            self.chrome_path,
            f"--remote-debugging-port={self.debug_port}",
            f"--user-data-dir={self.user_data_dir}",
            f"--profile-directory={self.profile_name}"
        ])
        DEBUGLOG.info("Chrome起動コマンド実行完了")
        for i in range(10):
            DEBUGLOG.debug(f"起動確認試行 {i+1}/10")
            time.sleep(1)
            if self.is_debug_chrome_running():
                DEBUGLOG.info(f"Chrome起動確認完了 ({i+1}秒後)")
                return True
        DEBUGLOG.error("Chrome起動タイムアウト")
        return False

    def connect_selenium(self) -> bool:
        """SeleniumでデバッグモードのChromeに接続"""
        DEBUGLOG.debug("Selenium接続開始")
        try:
            chrome_options = Options()
            chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{self.debug_port}")
            self.driver = webdriver.Chrome(options=chrome_options)
            DEBUGLOG.info("Selenium接続成功")
            return True
        except WebDriverException as e:
            DEBUGLOG.error(f"Selenium接続失敗: {e}")
            return False

    def _pick_monitor_by_windows_number(self, target_number: int):
        mons = get_monitors()
        if not mons:
            raise RuntimeError("モニター情報を取得できません")
        
        index = target_number - 1
        if 0 <= index < len(mons):
            return mons[index]
        return mons[0]

    def setup_window_and_activate(self) -> bool:
        """ウィンドウ設定・アクティブ化"""
        DEBUGLOG.debug("ウィンドウ設定・アクティブ化開始")

        mons = get_monitors()
        DEBUGLOG.info(f"利用可能モニター数: {len(mons)}")
        for i, m in enumerate(mons):
            DEBUGLOG.info(f"モニター{i}: x={m.x}, y={m.y}, width={m.width}, height={m.height}, primary={getattr(m, 'is_primary', False)}")
        
        DEBUGLOG.info(f"TARGET_MONITOR設定値: {self.target_monitor}")
        
        mon = self._pick_monitor_by_windows_number(self.target_monitor)
        DEBUGLOG.info(f"選択されたモニター: x={mon.x}, y={mon.y}, width={mon.width}, height={mon.height}")
        
        target_x, target_y = mon.x, mon.y
        w, h = 650, 500

        DEBUGLOG.info(f"ウィンドウ設定: 位置({target_x}, {target_y}), サイズ({w}x{h})")
        self.driver.set_window_position(target_x, target_y)
        self.driver.set_window_size(w, h)
        time.sleep(1)
        
        actual_rect = self.driver.get_window_rect()
        DEBUGLOG.info(f"実際のウィンドウ位置: x={actual_rect['x']}, y={actual_rect['y']}")
        return True

    def prepare_debug_chrome(self) -> bool:
        """デバッグChromeを準備"""
        DEBUGLOG.info("デバッグChrome準備開始")
        if self.is_debug_chrome_running():
            DEBUGLOG.info("既存のデバッグChromeに接続します")
            if not self.connect_selenium():
                return False
        else:
            DEBUGLOG.info("デバッグChromeを新規起動します")
            if not self.launch_chrome_debug_mode():
                return False
            time.sleep(3)
            if not self.connect_selenium():
                return False
        
        if not self.setup_window_and_activate():
            return False
        DEBUGLOG.info("デバッグChrome準備完了")
        return True

    def create_new_recording_tab(self) -> str:
        """新しい録画用タブを作成"""
        DEBUGLOG.info("新しい録画用タブを作成中...")
        self.driver.execute_script("window.open('');")
        self.driver.switch_to.window(self.driver.window_handles[-1])
        self.recording_tab_handle = self.driver.current_window_handle  # 録画タブとして記録
        self.current_tab_handle = self.recording_tab_handle
        DEBUGLOG.info(f"新しい録画タブ作成完了: {self.recording_tab_handle}")
        return self.recording_tab_handle

    def close_recording_tab_safely(self):
        """録画タブのみを安全にクローズ"""
        if not self.recording_tab_handle:
            DEBUGLOG.error("録画タブのハンドルが記録されていません")
            return False
        
        try:
            current_handles = self.driver.window_handles
            if self.recording_tab_handle not in current_handles:
                DEBUGLOG.warning("録画タブが既に存在しません")
                return True
            
            self.driver.switch_to.window(self.recording_tab_handle)
            self.driver.close()
            self.recording_tab_handle = None
            DEBUGLOG.info("録画タブクローズ成功")
            return True
        except Exception as e:
            DEBUGLOG.error(f"録画タブクローズでエラー: {e}")
            return False

    def navigate_to_url(self, url: str):
        """指定URLに移動"""
        DEBUGLOG.info(f"配信ページに移動: {url}")
        self.driver.get(url)
        time.sleep(3)

    def click_fullscreen_button(self):
        """フルスクリーンボタンをクリック"""
        DEBUGLOG.info("フルスクリーンボタンクリック開始")
        try:
            button = self.driver.find_element("css selector", '[class^="___fullscreen-button___"]')
            button.click()
            DEBUGLOG.info("Seleniumでフルスクリーンボタンをクリックしました")
            time.sleep(2)
            DEBUGLOG.info("フルスクリーンボタンクリック完了")
        except Exception as e:
            DEBUGLOG.warning(f"フルスクリーンボタンクリックでエラー: {e}")

    def click_play_button(self):
        """再生ボタンをクリック"""
        DEBUGLOG.info("再生ボタンクリック開始")
        try:
            button = self.driver.find_element("css selector", '[class^="___play-button___"]')
            button.click()
            DEBUGLOG.info("Seleniumで再生ボタンをクリックしました")
            time.sleep(2)
            DEBUGLOG.info("再生ボタンクリック完了")
        except Exception as e:
            DEBUGLOG.warning(f"再生ボタンクリックでエラー: {e}")

    def get_adjusted_coordinates(self, base_x: int, base_y: int) -> tuple:
        """ターゲットモニターに配置されたウィンドウの座標に基づいてマウス座標を調整"""
        try:
            window_rect = self.driver.get_window_rect()
            window_x = window_rect['x']
            window_y = window_rect['y']
            
            adjusted_x = window_x + base_x
            adjusted_y = window_y + base_y
            
            DEBUGLOG.debug(f"座標調整: 基準({base_x}, {base_y}) → 調整後({adjusted_x}, {adjusted_y})")
            return adjusted_x, adjusted_y
        except Exception as e:
            DEBUGLOG.error(f"座標調整でエラー: {e}")
            return base_x, base_y