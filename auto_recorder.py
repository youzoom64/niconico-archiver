import subprocess
import time
import psutil
import pyautogui
import argparse
import win32gui
import win32con
import logging
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException
from screeninfo import get_monitors
import win32process

# ログ設定
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('niconico_recorder.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

DEBUGLOG = logging.getLogger(__name__)

# 座標設定
EXTENSION_COORDINATES = {
    'extension_icon': (360, 65),
    'start_button': (310, 160),
    'stop_button': (325, 165),
}

# Chrome設定
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeDebug"
PROFILE_NAME = "Default"
DEBUG_PORT = "9222"
TARGET_MONITOR = 2

# グローバル変数
recording_start_time = None
target_url = None
broadcast_id = None         # = lv_no
broadcast_title = None      # = lv_title
broadcaster_name = None     # = display_name
broadcaster_id = None       # = account_id
driver = None
current_tab_handle = None
output_dir = None           # 作成した保存先

# 追加: パス用のサニタイズ
def _sanitize_path_component(name: str) -> str:
    invalid = '<>:"/\\|?*'
    table = str.maketrans({ch: '_' for ch in invalid})
    out = name.translate(table).strip().rstrip('.')
    return out or "unknown"

# 追加: ユーザー設定をロード
def load_user_config(account_id: str):
    """
    config/users/{account_id}.json を読み込み、辞書を返す。
    失敗時は None を返す。
    """
    path = os.path.join('config', 'users', f'{account_id}.json')
    if not os.path.exists(path):
        DEBUGLOG.warning(f"ユーザー設定が見つかりません: {path}")
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            data = json.load(f)
        DEBUGLOG.info(f"ユーザー設定読込成功: {path}")
        return data
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定の読込に失敗: {path} / {e}")
        return None

# run_broadcast_checker関数の前に追加
def create_user_config_if_needed(account_id: str, display_name: str, lv_no: str, lv_title: str, tab_id: str, start_time: int):
    """ユーザー設定が存在しない場合は自動生成"""
    config_path = os.path.join('config', 'users', f'{account_id}.json')
    if os.path.exists(config_path):
        DEBUGLOG.info(f"ユーザー設定が既に存在: {config_path}")
        return
    
    script = 'create_user_config.py'
    if not os.path.exists(script):
        DEBUGLOG.warning(f"{script} が見つかりません")
        return
    
    venv_python = os.path.join('venv', 'Scripts', 'python.exe')
    cmd = [
        venv_python, script,
        '-lv_no', lv_no,
        '-account_id', account_id,
        '-lv_title', lv_title,
        '-display_name', display_name,
        '-tab_id', tab_id,
        '-start_time', str(start_time)
    ]
    
    DEBUGLOG.info(f"ユーザー設定生成スクリプト起動")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if res.returncode == 0:
            DEBUGLOG.info("ユーザー設定生成成功")
        else:
            DEBUGLOG.error(f"ユーザー設定生成失敗: returncode={res.returncode}")
            if res.stderr:
                DEBUGLOG.error(f"[stderr]\n{res.stderr}")
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定生成スクリプト起動失敗: {e}")

# 追加: 保存ディレクトリの生成
def ensure_output_dir(platform_directory: str, account_id: str, display_name: str) -> str:
    safe_name = _sanitize_path_component(display_name)
    base = platform_directory or os.path.abspath(os.path.join('.', 'rec'))
    out = os.path.join(base, f"{account_id}_{safe_name}")
    try:
        os.makedirs(out, exist_ok=True)
        DEBUGLOG.info(f"保存ディレクトリ準備完了: {out}")
    except Exception as e:
        DEBUGLOG.error(f"保存ディレクトリ作成失敗: {out} / {e}")
        raise
    return out

# 追加: broadcast_checker（または bloadcast_checker）呼び出し
def run_broadcast_checker(lv_no: str, account_id: str, lv_title: str, display_name: str,
                          tab_id: str, start_time: int):
    script = 'broadcast_checker.py'
    if not os.path.exists(script):
        DEBUGLOG.warning(f"{script} が見つかりません")
        return

    # 仮想環境の Python を使う
    venv_python = os.path.join('venv', 'Scripts', 'python.exe')

    cmd = [
        venv_python, script,
        '-lv_no', lv_no,
        '-account_id', account_id,
        '-lv_title', lv_title,
        '-display_name', display_name,
        '-tab_id', tab_id,
        '-start_time', str(start_time)
    ]

    DEBUGLOG.info(f"チェッカー起動: {' '.join(cmd)}")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        DEBUGLOG.info(f"チェッカー終了: returncode={res.returncode}")
        if res.stdout:
            DEBUGLOG.debug(f"[checker stdout]\n{res.stdout}")
        if res.stderr:
            DEBUGLOG.debug(f"[checker stderr]\n{res.stderr}")
    except Exception as e:
        DEBUGLOG.error(f"チェッカー起動失敗: {e}")



def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description='ニコニコ生放送録画システム')
    parser.add_argument('-url', required=True, help='録画対象URL')
    parser.add_argument('-tag', required=True, help='放送情報タグ (lv12345_タイトル_放送者名_123)')
    args = parser.parse_args()
    DEBUGLOG.info(f"引数パース完了 - URL: {args.url}, TAG: {args.tag}")
    return args.url, args.tag

def parse_broadcast_tag(tag):
    """放送タグをパースして情報を抽出"""
    DEBUGLOG.debug(f"放送タグをパース中: {tag}")
    parts = tag.split('_')
    if len(parts) < 4:
        DEBUGLOG.error(f"タグフォーマットエラー: {tag}")
        raise ValueError("タグフォーマットが正しくありません (lv12345_タイトル_放送者名_123)")
    broadcast_id = parts[0]         # lv_no
    broadcast_title = parts[1]      # lv_title
    broadcaster_name = parts[2]     # display_name
    broadcaster_id = parts[3]       # account_id
    DEBUGLOG.info("放送情報抽出完了:\n"
                  f"  放送ID(lv_no): {broadcast_id}\n"
                  f"  タイトル(lv_title): {broadcast_title}\n"
                  f"  放送者名(display_name): {broadcaster_name}\n"
                  f"  放送者ID(account_id): {broadcaster_id}")
    return broadcast_id, broadcast_title, broadcaster_name, broadcaster_id

def is_debug_chrome_running():
    """デバッグモードのChromeが起動中かチェック"""
    DEBUGLOG.debug("デバッグChrome存在チェック開始")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
            cmdline = " ".join(proc.info['cmdline']).lower()
            if USER_DATA_DIR.lower() in cmdline and f"--remote-debugging-port={DEBUG_PORT}" in cmdline:
                DEBUGLOG.info(f"デバッグChrome発見! PID: {proc.info['pid']}")
                return True
    DEBUGLOG.info("デバッグChrome存在: False")
    return False

def get_debug_chrome_pid():
    """デバッグChromeのプロセスIDを取得"""
    DEBUGLOG.debug("デバッグChrome PID取得開始")
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        if proc.info['name'] and "chrome.exe" in proc.info['name'].lower():
            cmdline = " ".join(proc.info['cmdline']).lower()
            has_user_data = USER_DATA_DIR.lower() in cmdline
            has_debug_port = f"--remote-debugging-port={DEBUG_PORT}" in cmdline
            is_main_process = "--type=" not in cmdline
            if has_user_data and has_debug_port and is_main_process:
                DEBUGLOG.info(f"デバッグChrome メインプロセス特定: PID {proc.info['pid']}")
                return proc.info['pid']
    DEBUGLOG.warning("デバッグChrome メインプロセスが見つかりません")
    return None

def activate_chrome_window():
    """デバッグChromeをアクティブ化"""
    DEBUGLOG.debug("Chromeアクティブ化処理開始")
    chrome_pid = get_debug_chrome_pid()
    if not chrome_pid:
        DEBUGLOG.error("デバッグChromeのプロセスが見つからないため、アクティブ化できません")
        return False
    DEBUGLOG.info(f"対象Chrome PID: {chrome_pid}")
    activated = False
    def enum_windows_callback(hwnd, pid):
        nonlocal activated
        try:
            _, window_pid = win32process.GetWindowThreadProcessId(hwnd)
            if window_pid == pid and win32gui.IsWindowVisible(hwnd):
                window_title = win32gui.GetWindowText(hwnd)
                if window_title and ("Chrome" in window_title or "Google Chrome" in window_title):
                    DEBUGLOG.info(f"対象Chromeウィンドウ特定: {window_title}")
                    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
                    win32gui.SetForegroundWindow(hwnd)
                    activated = True
                    return False
        except Exception as e:
            DEBUGLOG.debug(f"ウィンドウ処理スキップ (HWND: {hwnd}): {e}")
        return True
    try:
        win32gui.EnumWindows(enum_windows_callback, chrome_pid)
        return activated
    except Exception as e:
        DEBUGLOG.error(f"アクティブ化処理エラー: {e}")
        return False

def launch_chrome_debug_mode():
    """デバッグモードのChromeを起動"""
    DEBUGLOG.info("デバッグChrome起動開始")
    subprocess.Popen([
        CHROME_PATH,
        f"--remote-debugging-port={DEBUG_PORT}",
        f"--user-data-dir={USER_DATA_DIR}",
        f"--profile-directory={PROFILE_NAME}"
    ])
    DEBUGLOG.info("Chrome起動コマンド実行完了")
    for i in range(10):
        DEBUGLOG.debug(f"起動確認試行 {i+1}/10")
        time.sleep(1)
        if is_debug_chrome_running():
            DEBUGLOG.info(f"Chrome起動確認完了 ({i+1}秒後)")
            return True
    DEBUGLOG.error("Chrome起動タイムアウト")
    return False

def connect_selenium():
    """SeleniumでデバッグモードのChromeに接続"""
    DEBUGLOG.debug("Selenium接続開始")
    try:
        chrome_options = Options()
        chrome_options.add_experimental_option("debuggerAddress", f"127.0.0.1:{DEBUG_PORT}")
        driver = webdriver.Chrome(options=chrome_options)
        DEBUGLOG.info("Selenium接続成功")
        return driver
    except WebDriverException as e:
        DEBUGLOG.error(f"Selenium接続失敗: {e}")
        return None

def setup_window_and_activate(driver):
    """ウィンドウをモニター2の(0,0)、300x400に設定してアクティブ化"""
    DEBUGLOG.debug("ウィンドウ設定・アクティブ化開始")
    monitors = get_monitors()
    if len(monitors) < 2:
        DEBUGLOG.error("モニター2が見つかりません")
        return False
    monitor2 = monitors[1]
    target_x = monitor2.x
    target_y = monitor2.y
    DEBUGLOG.info(f"ウィンドウ設定: 位置({target_x}, {target_y}), サイズ(300x400)")
    driver.set_window_position(target_x, target_y)
    driver.set_window_size(550, 500)
    time.sleep(1)
    if not activate_chrome_window():
        DEBUGLOG.warning("アクティブ化に失敗しましたが処理を続行します")
    DEBUGLOG.info("ウィンドウ設定・アクティブ化完了")
    return True

def prepare_debug_chrome():
    """デバッグChromeを準備"""
    global driver
    DEBUGLOG.info("デバッグChrome準備開始")
    if is_debug_chrome_running():
        DEBUGLOG.info("既存のデバッグChromeに接続します")
        driver = connect_selenium()
    else:
        DEBUGLOG.info("デバッグChromeを新規起動します")
        if not launch_chrome_debug_mode():
            return False
        time.sleep(3)
        driver = connect_selenium()
    if not driver:
        DEBUGLOG.error("Selenium接続に失敗しました")
        return False
    if not setup_window_and_activate(driver):
        return False
    DEBUGLOG.info("デバッグChrome準備完了")
    return True

def create_new_recording_tab():
    """新しい録画用タブを作成"""
    global current_tab_handle
    DEBUGLOG.info("新しい録画用タブを作成中...")
    driver.execute_script("window.open('');")
    driver.switch_to.window(driver.window_handles[-1])
    current_tab_handle = driver.current_window_handle
    DEBUGLOG.info(f"新しいタブ作成完了: {current_tab_handle}")
    return current_tab_handle

def save_recording_tab_info(tab_handle, broadcast_id, target_url, tag):
    """タブIDとURL・タグ情報を紐づけて保存"""
    DEBUGLOG.info("録画タブ情報を保存中...")
    tab_info = {
        'tab_handle': tab_handle,
        'broadcast_id': broadcast_id,
        'target_url': target_url,
        'tag': tag,
        'start_time': recording_start_time,
        'created_at': time.time()
    }
    filename = f'recording_tab_{broadcast_id}.json'
    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(tab_info, f, ensure_ascii=False, indent=2)
    DEBUGLOG.info(f"録画タブ情報保存完了: {filename}")

def activate_and_click(x, y, description):
    """アクティブ化してからクリック"""
    DEBUGLOG.info(f"{description}クリック準備開始")
    if not setup_window_and_activate(driver):
        DEBUGLOG.warning(f"ウィンドウ設定に失敗しましたが{description}をクリックします")
    DEBUGLOG.info(f"{description}をクリック: ({x}, {y})")
    pyautogui.click(x, y)
    DEBUGLOG.info(f"{description}クリック完了")
    return True

def trigger_playback_if_needed():
    """必要に応じて再生促進クリック"""
    DEBUGLOG.info("再生促進処理開始")
    try:
        window_rect = driver.get_window_rect()
        center_x = window_rect['x'] + window_rect['width'] // 2
        center_y = window_rect['y'] + window_rect['height'] // 2
        DEBUGLOG.info(f"再生促進クリック: ({center_x}, {center_y})")
        pyautogui.click(center_x, center_y)
        time.sleep(2)
        DEBUGLOG.info("再生促進処理完了")
    except Exception as e:
        DEBUGLOG.warning(f"再生促進処理でエラー: {e}")

def full_screen_button_click():
    """フルスクリーンボタンをクリック"""
    DEBUGLOG.info("フルスクリーンボタンクリック開始")
    try:
        # Seleniumでクラス名が ___fullscreen-button___ で始まる要素を探してクリック
        button = driver.find_element("css selector", '[class^="___fullscreen-button___"]')
        button.click()
        DEBUGLOG.info("Seleniumでフルスクリーンボタンをクリックしました")
        time.sleep(2)
        DEBUGLOG.info("フルスクリーンボタンクリック完了")
    except Exception as e:
        DEBUGLOG.warning(f"フルスクリーンボタンクリックでエラー: {e}")
    
def play_button_clickI():
    """再生ボタンをクリック"""
    DEBUGLOG.info("再生ボタンクリック開始")
    try:
        # Seleniumでクラス名が ___play-button___ で始まる要素を探してクリック
        button = driver.find_element("css selector", '[class^="___play-button___"]')
        button.click()
        DEBUGLOG.info("Seleniumで再生ボタンをクリックしました")
        time.sleep(2)
        DEBUGLOG.info("再生ボタンクリック完了")
    except Exception as e:
        DEBUGLOG.warning(f"再生ボタンクリックでエラー: {e}")

def main():
    """メイン処理"""
    global recording_start_time, target_url, broadcast_id, broadcast_title, broadcaster_name, broadcaster_id, output_dir

    print("ニコニコ生放送録画システム")
    print("=" * 50)
    DEBUGLOG.info("録画システム起動")

    try:
        # 0) 引数パース & タグ分解（まず最初にやる）
        target_url, tag = parse_arguments()
        broadcast_id, broadcast_title, broadcaster_name, broadcaster_id = parse_broadcast_tag(tag)  # lv_no, lv_title, display_name, account_id

        # 1) ユーザー設定のロード
        user_cfg = load_user_config(broadcaster_id)
        platform_directory = None
        if user_cfg and isinstance(user_cfg, dict):
            basic = user_cfg.get('basic_settings', {}) or {}
            platform_directory = basic.get('platform_directory')
            DEBUGLOG.info(f"platform_directory: {platform_directory}")
        else:
            DEBUGLOG.warning("ユーザー設定が無い/不正のため、カレント配下に rec/ を作成して保存します")

        # 2) 保存先ディレクトリ作成: {platform_directory}/{account_id}_{display_name}/
        output_dir = ensure_output_dir(platform_directory, broadcaster_id, broadcaster_name)

        # 3) デバッグChrome準備・ウィンドウアクティブ化
        if not prepare_debug_chrome():
            DEBUGLOG.error("Chrome準備に失敗しました")
            # 失敗しても以降のチェッカー連携は実施するため処理は継続しない（このスクリプトは録画トリガ係）
            return False

        # 4) 新しいタブを作成
        tab_handle = create_new_recording_tab()

        # 5) 録画アイコン → Start クリック
        ext_x, ext_y = EXTENSION_COORDINATES['extension_icon']
        activate_and_click(ext_x, ext_y, "拡張機能アイコン")
        time.sleep(1)

        start_x, start_y = EXTENSION_COORDINATES['start_button']
        DEBUGLOG.info(f"スタートボタンをクリック: ({start_x}, {start_y})")
        pyautogui.click(start_x, start_y)
        DEBUGLOG.info("スタートボタンクリック完了")

        # 6) 録画開始時刻記録 & タブ情報保存
        recording_start_time = int(time.time())
        DEBUGLOG.info(f"録画開始時刻記録: {recording_start_time} (UNIX時間)")
        save_recording_tab_info(tab_handle, broadcast_id, target_url, tag)

        time.sleep(1)

        # 7) 配信ページに移動
        DEBUGLOG.info(f"配信ページに移動: {target_url}")
        driver.get(target_url)
        time.sleep(1)
        # trigger_playback_if_needed()  # 必要なら有効化

        print("録画が開始されました")
        print("手動で終了するか、別途停止スクリプトを実行してください")
        print(f"録画タブ情報: recording_tab_{broadcast_id}.json")
        DEBUGLOG.info(f"保存先: {output_dir}")

        time.sleep(5)  # ページが安定するまで少し待つ


        full_screen_button_click()  # フルスクリーンボタンをクリック
        time.sleep(1)

        play_button_clickI()  # 再生ボタンをクリック
        time.sleep(1)


        # main関数内で、run_broadcast_checkerを呼び出す前に追加
        # 8) ユーザー設定自動生成（必要な場合）
        create_user_config_if_needed(
            account_id=broadcaster_id,
            display_name=broadcaster_name,
            lv_no=broadcast_id,
            lv_title=broadcast_title,
            tab_id=tab_handle,
            start_time=recording_start_time
        )

        # 9) broadcast_checker起動
        run_broadcast_checker(
            lv_no=broadcast_id,
            account_id=broadcaster_id,
            lv_title=broadcast_title,
            display_name=broadcaster_name,
            tab_id=tab_handle,
            start_time=recording_start_time
        )

        return True

    except Exception as e:
        DEBUGLOG.error(f"メイン処理でエラーが発生: {e}", exc_info=True)
        return False

if __name__ == "__main__":
    success = main()
    if success:
        DEBUGLOG.info("録画開始処理完了")
    else:
        DEBUGLOG.error("録画開始処理失敗")
