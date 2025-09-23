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
import threading
import tempfile
import shutil
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
        logging.FileHandler('logs/niconico_recorder.log', encoding='utf-8'),
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
TARGET_MONITOR = 3

# 録画管理用グローバル変数
recording_start_time = None
target_url = None
broadcast_id = None
broadcast_title = None
broadcaster_name = None
broadcaster_id = None
driver = None
current_tab_handle = None
output_dir = None

# 30分録画用グローバル変数
recording_segments = []  # セグメント情報
segment_gaps = []        # セグメント間隙間時間
current_segment = 0      # 現在のセグメント番号
segment_timer = None     # 30分タイマー
recording_active = False # 録画状態フラグ
tmp_dir = None          # 一時作業ディレクトリ

# 30分 = 1800秒
SEGMENT_DURATION = 30 * 60

def _sanitize_path_component(name: str) -> str:
    invalid = '<>:"/\\|?*'
    table = str.maketrans({ch: '_' for ch in invalid})
    out = name.translate(table).strip().rstrip('.')
    return out or "unknown"

def load_user_config(account_id: str):
    """ユーザー設定を読み込み"""
    user_path = os.path.join('config', 'users', f'{account_id}.json')
    tmpl_path = os.path.join('config', 'users', 'default_template.json')

    def _deep_merge(base: dict, override: dict) -> dict:
        from copy import deepcopy
        out = deepcopy(base) if base else {}
        for k, v in (override or {}).items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    try:
        user = {}
        tmpl = {}
        if os.path.exists(tmpl_path):
            with open(tmpl_path, 'r', encoding='utf-8') as f:
                tmpl = json.load(f)
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as f:
                user = json.load(f)

        if tmpl:
            cfg = _deep_merge(tmpl, user)
        else:
            cfg = user

        if cfg:
            DEBUGLOG.info(f"ユーザー設定読込成功: {user_path if user else '(テンプレのみ)'}")
            return cfg
        else:
            DEBUGLOG.warning(f"ユーザー設定が見つかりません: {user_path}")
            return None
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定の読込に失敗: {account_id}.json / {e}")
        return None

def create_user_config_if_needed(account_id: str, display_name: str, lv_no: str, lv_title: str, tab_id: str, start_time: int):
    """ユーザー設定が存在しない場合は自動生成、存在する場合は更新"""
    config_path = os.path.join('config', 'users', f'{account_id}.json')
    
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
    
    if os.path.exists(config_path):
        DEBUGLOG.info(f"既存設定を更新: {config_path}")
        cmd.append('-update_existing')
    else:
        DEBUGLOG.info(f"新規設定を生成: {config_path}")
    
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if res.returncode == 0:
            DEBUGLOG.info("ユーザー設定処理成功")
        else:
            DEBUGLOG.error(f"ユーザー設定処理失敗: returncode={res.returncode}")
            if res.stderr:
                DEBUGLOG.error(f"[stderr]\n{res.stderr}")
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定スクリプト起動失敗: {e}")

def ensure_output_dir(platform_directory: str, account_id: str, display_name: str) -> str:
    """保存ディレクトリの生成"""
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

def setup_tmp_directory():
    """一時作業ディレクトリのセットアップ"""
    global tmp_dir
    tmp_dir = os.path.join('.', 'tmp')
    try:
        os.makedirs(tmp_dir, exist_ok=True)
        DEBUGLOG.info(f"一時ディレクトリ準備完了: {tmp_dir}")
    except Exception as e:
        DEBUGLOG.error(f"一時ディレクトリ作成失敗: {tmp_dir} / {e}")
        raise

def cleanup_tmp_directory():
    """一時作業ディレクトリのクリーンアップ"""
    global tmp_dir
    if tmp_dir and os.path.exists(tmp_dir):
        try:
            shutil.rmtree(tmp_dir)
            DEBUGLOG.info(f"一時ディレクトリクリーンアップ完了: {tmp_dir}")
        except Exception as e:
            DEBUGLOG.warning(f"一時ディレクトリクリーンアップ失敗: {e}")

def run_broadcast_checker(lv_no: str, account_id: str, lv_title: str, display_name: str,
                          tab_id: str, start_time: int):
    """broadcast_checker呼び出し"""
    script = 'broadcast_checker.py'
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
    broadcast_id = parts[0]
    broadcast_title = parts[1]
    broadcaster_name = parts[2]
    broadcaster_id = parts[3]
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

def _pick_monitor_by_windows_number(target_number: int):
    mons = get_monitors()
    if not mons:
        raise RuntimeError("モニター情報を取得できません")
    
    index = target_number - 1
    if 0 <= index < len(mons):
        return mons[index]
    return mons[0]

def setup_window_and_activate(driver):
    """ウィンドウ設定・アクティブ化"""
    DEBUGLOG.debug("ウィンドウ設定・アクティブ化開始")

    mons = get_monitors()
    DEBUGLOG.info(f"利用可能モニター数: {len(mons)}")
    for i, m in enumerate(mons):
        DEBUGLOG.info(f"モニター{i}: x={m.x}, y={m.y}, width={m.width}, height={m.height}, primary={getattr(m, 'is_primary', False)}")
    
    DEBUGLOG.info(f"TARGET_MONITOR設定値: {TARGET_MONITOR}")
    
    mon = _pick_monitor_by_windows_number(TARGET_MONITOR)
    DEBUGLOG.info(f"選択されたモニター: x={mon.x}, y={mon.y}, width={mon.width}, height={mon.height}")
    
    target_x, target_y = mon.x, mon.y
    w, h = 650, 500

    DEBUGLOG.info(f"ウィンドウ設定: 位置({target_x}, {target_y}), サイズ({w}x{h})")
    driver.set_window_position(target_x, target_y)
    driver.set_window_size(w, h)
    time.sleep(1)
    
    actual_rect = driver.get_window_rect()
    DEBUGLOG.info(f"実際のウィンドウ位置: x={actual_rect['x']}, y={actual_rect['y']}")
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

def get_adjusted_coordinates(base_x, base_y):
    """ターゲットモニターに配置されたウィンドウの座標に基づいてマウス座標を調整"""
    try:
        window_rect = driver.get_window_rect()
        window_x = window_rect['x']
        window_y = window_rect['y']
        
        adjusted_x = window_x + base_x
        adjusted_y = window_y + base_y
        
        DEBUGLOG.debug(f"座標調整: 基準({base_x}, {base_y}) → 調整後({adjusted_x}, {adjusted_y})")
        return adjusted_x, adjusted_y
    except Exception as e:
        DEBUGLOG.error(f"座標調整でエラー: {e}")
        return base_x, base_y

def activate_and_click(base_x, base_y, description):
    """アクティブ化してからクリック（座標調整版）"""
    DEBUGLOG.info(f"{description}クリック準備開始")
    if not setup_window_and_activate(driver):
        DEBUGLOG.warning(f"ウィンドウ設定に失敗しましたが{description}をクリックします")
    
    adjusted_x, adjusted_y = get_adjusted_coordinates(base_x, base_y)
    
    DEBUGLOG.info(f"{description}をクリック: ({adjusted_x}, {adjusted_y})")
    pyautogui.click(adjusted_x, adjusted_y)
    DEBUGLOG.info(f"{description}クリック完了")
    return True

def full_screen_button_click():
    """フルスクリーンボタンをクリック"""
    DEBUGLOG.info("フルスクリーンボタンクリック開始")
    try:
        button = driver.find_element("css selector", '[class^="___fullscreen-button___"]')
        button.click()
        DEBUGLOG.info("Seleniumでフルスクリーンボタンをクリックしました")
        time.sleep(2)
        DEBUGLOG.info("フルスクリーンボタンクリック完了")
    except Exception as e:
        DEBUGLOG.warning(f"フルスクリーンボタンクリックでエラー: {e}")
    
def play_button_click():
    """再生ボタンをクリック"""
    DEBUGLOG.info("再生ボタンクリック開始")
    try:
        button = driver.find_element("css selector", '[class^="___play-button___"]')
        button.click()
        DEBUGLOG.info("Seleniumで再生ボタンをクリックしました")
        time.sleep(2)
        DEBUGLOG.info("再生ボタンクリック完了")
    except Exception as e:
        DEBUGLOG.warning(f"再生ボタンクリックでエラー: {e}")

def start_recording():
    """録画開始"""
    global recording_active
    DEBUGLOG.info("録画開始処理")
    
    # 拡張機能アイコンクリック
    ext_x, ext_y = EXTENSION_COORDINATES['extension_icon']
    activate_and_click(ext_x, ext_y, "拡張機能アイコン")
    time.sleep(1)

    # スタートボタンクリック
    start_x, start_y = EXTENSION_COORDINATES['start_button']
    adjusted_start_x, adjusted_start_y = get_adjusted_coordinates(start_x, start_y)
    DEBUGLOG.info(f"スタートボタンをクリック: ({adjusted_start_x}, {adjusted_start_y})")
    pyautogui.click(adjusted_start_x, adjusted_start_y)
    DEBUGLOG.info("スタートボタンクリック完了")
    
    recording_active = True
    time.sleep(1)

def stop_recording():
    """録画停止"""
    global recording_active
    DEBUGLOG.info("録画停止処理")
    
    # 拡張機能アイコンクリック
    ext_x, ext_y = EXTENSION_COORDINATES['extension_icon']
    activate_and_click(ext_x, ext_y, "拡張機能アイコン")
    time.sleep(1)

    # ストップボタンクリック
    stop_x, stop_y = EXTENSION_COORDINATES['stop_button']
    adjusted_stop_x, adjusted_stop_y = get_adjusted_coordinates(stop_x, stop_y)
    DEBUGLOG.info(f"ストップボタンをクリック: ({adjusted_stop_x}, {adjusted_stop_y})")
    pyautogui.click(adjusted_stop_x, adjusted_stop_y)
    DEBUGLOG.info("ストップボタンクリック完了")
    
    recording_active = False
    time.sleep(1)

def switch_recording_segment():
    """録画セグメント切り替え（30分タイマー用）"""
    global current_segment, segment_timer, recording_segments, segment_gaps
    
    if not recording_active:
        DEBUGLOG.warning("録画が非アクティブのため、セグメント切り替えをスキップ")
        return
    
    # 現在のセグメント終了時刻記録
    end_time = int(time.time())
    if current_segment < len(recording_segments):
        recording_segments[current_segment]['end_time'] = end_time
        recording_segments[current_segment]['file'] = f"segment_{current_segment:03d}.mp4"
        DEBUGLOG.info(f"セグメント{current_segment}終了時刻記録: {end_time}")
    
    # 録画停止
    stop_recording()
    
    # 次のセグメント準備
    current_segment += 1
    start_time = int(time.time())
    
    # 隙間時間計算
    if len(recording_segments) > 0:
        gap_seconds = start_time - end_time
        segment_gaps.append(gap_seconds)
        DEBUGLOG.info(f"セグメント間隙間時間: {gap_seconds}秒")
    
    # 新しいセグメント情報追加
    new_segment = {
        'segment_id': current_segment,
        'start_time': start_time,
        'end_time': None,
        'file': None
    }
    recording_segments.append(new_segment)
    
    # 録画再開
    start_recording()
    
    DEBUGLOG.info(f"セグメント{current_segment}開始: {start_time}")
    
    # 次の30分タイマー設定
    schedule_next_segment_switch()

def schedule_next_segment_switch():
    """次のセグメント切り替えをスケジュール"""
    global segment_timer
    
    if segment_timer:
        segment_timer.cancel()
    
    segment_timer = threading.Timer(SEGMENT_DURATION, switch_recording_segment)
    segment_timer.start()
    DEBUGLOG.info(f"次のセグメント切り替えを{SEGMENT_DURATION}秒後にスケジュール")

def create_gap_video(duration_seconds: int, output_path: str):
    """指定秒数の黒画面動画を生成"""
    DEBUGLOG.info(f"隙間動画生成開始: {duration_seconds}秒 → {output_path}")
    
    cmd = [
        'ffmpeg', '-y',
        '-f', 'lavfi',
        '-i', f'color=c=black:s=1280x720:d={duration_seconds}',
        '-f', 'lavfi', 
        '-i', f'anullsrc=channel_layout=stereo:sample_rate=48000',
        '-c:v', 'libx264',
        '-c:a', 'aac',
        '-shortest',
        '-pix_fmt', 'yuv420p',
        output_path
    ]
    
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if result.returncode == 0:
            DEBUGLOG.info(f"隙間動画生成成功: {output_path}")
        else:
            DEBUGLOG.error(f"隙間動画生成失敗: returncode={result.returncode}")
            if result.stderr:
                DEBUGLOG.error(f"[ffmpeg stderr]\n{result.stderr}")
    except Exception as e:
        DEBUGLOG.error(f"隙間動画生成で例外: {e}")

def create_concat_list(segments: list, gaps: list, output_path: str):
    """ffmpeg用の結合リストファイルを生成"""
    DEBUGLOG.info(f"結合リスト生成: {output_path}")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        for i, segment in enumerate(segments):
            if segment['file'] and os.path.exists(os.path.join(output_dir, segment['file'])):
                # セグメント動画
                segment_path = os.path.join(output_dir, segment['file']).replace('\\', '/')
                f.write(f"file '{segment_path}'\n")
                
                # 隙間動画（最後のセグメント以外）
                if i < len(gaps):
                    gap_file = os.path.join(tmp_dir, f'gap_{gaps[i]}s.mp4').replace('\\', '/')
                    if os.path.exists(gap_file.replace('/', '\\')):  # Windowsパス用に戻して存在確認
                        f.write(f"file '{gap_file}'\n")
    
    DEBUGLOG.info(f"結合リスト生成完了: {output_path}")

def merge_all_segments():
    """全セグメントと隙間を結合して最終動画を作成"""
    global recording_segments, segment_gaps, tmp_dir, output_dir
    
    DEBUGLOG.info("最終動画結合処理開始")
    
    if not recording_segments:
        DEBUGLOG.warning("結合対象のセグメントがありません")
        return
    
    try:
        # 隙間動画生成
        for i, gap_seconds in enumerate(segment_gaps):
            if gap_seconds > 0:
                gap_file = os.path.join(tmp_dir, f'gap_{gap_seconds}s.mp4')
                create_gap_video(gap_seconds, gap_file)
        
        # 結合リスト作成
        concat_list = os.path.join(tmp_dir, 'concat_list.txt')
        create_concat_list(recording_segments, segment_gaps, concat_list)
        
        # 最終動画出力パス
        final_output = os.path.join(output_dir, f'{broadcast_id}_complete.mp4')
        
        # ffmpegで結合実行
        cmd = [
            'ffmpeg', '-y',
            '-f', 'concat',
            '-safe', '0',
            '-i', concat_list,
            '-c', 'copy',
            final_output
        ]
        
        DEBUGLOG.info(f"最終結合実行: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        
        if result.returncode == 0:

            DEBUGLOG.info(f"最終動画結合成功: {final_output}")
            
            # セグメント情報をJSONで保存
            segments_info = {
                'broadcast_id': broadcast_id,
                'total_segments': len(recording_segments),
                'segments': recording_segments,
                'gaps': segment_gaps,
                'final_video': final_output,
                'created_at': int(time.time())
            }
            
            info_file = os.path.join(output_dir, f'{broadcast_id}_segments_info.json')
            with open(info_file, 'w', encoding='utf-8') as f:
                json.dump(segments_info, f, ensure_ascii=False, indent=2)
            
            DEBUGLOG.info(f"セグメント情報保存: {info_file}")
            
        else:
            DEBUGLOG.error(f"最終動画結合失敗: returncode={result.returncode}")
            if result.stderr:
                DEBUGLOG.error(f"[ffmpeg stderr]\n{result.stderr}")
    
    except Exception as e:
        DEBUGLOG.error(f"最終動画結合で例外: {e}")
    
    finally:
        # 一時ディレクトリクリーンアップ
        cleanup_tmp_directory()

def stop_all_recording():
    """全録画停止と最終処理"""
    global segment_timer, recording_active, current_segment
    
    DEBUGLOG.info("全録画停止処理開始")
    
    # タイマー停止
    if segment_timer:
        segment_timer.cancel()
        segment_timer = None
    
    # 最後のセグメント終了処理
    if recording_active:
        end_time = int(time.time())
        if current_segment < len(recording_segments):
            recording_segments[current_segment]['end_time'] = end_time
            recording_segments[current_segment]['file'] = f"segment_{current_segment:03d}.mp4"
            DEBUGLOG.info(f"最終セグメント{current_segment}終了時刻記録: {end_time}")
        
        # 録画停止
        stop_recording()
    
    # 最終動画結合
    merge_all_segments()
    
    DEBUGLOG.info("全録画停止処理完了")

def load_global_config():
    """グローバル設定読み込み"""
    path = os.path.join("config", "global_config.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"system": {"download_directory": "Downloads"}}

def main():
    """メイン処理"""
    global recording_start_time, target_url, broadcast_id, broadcast_title, broadcaster_name, broadcaster_id, output_dir
    global current_segment, recording_segments

    print("ニコニコ生放送録画システム（30分セグメント対応）")
    print("=" * 60)
    DEBUGLOG.info("録画システム起動")

    try:
        # グローバル設定読み込み
        global_cfg = load_global_config()
        download_directory = global_cfg["system"]["download_directory"]
        
        # 引数パース & タグ分解
        target_url, tag = parse_arguments()
        broadcast_id, broadcast_title, broadcaster_name, broadcaster_id = parse_broadcast_tag(tag)

        # ユーザー設定のロード
        user_cfg = load_user_config(broadcaster_id)
        platform_directory = None
        if user_cfg and isinstance(user_cfg, dict):
            basic = user_cfg.get('basic_settings', {}) or {}
            platform_directory = basic.get('platform_directory')
            DEBUGLOG.info(f"platform_directory: {platform_directory}")
        else:
            DEBUGLOG.warning("ユーザー設定が無い/不正のため、カレント配下に rec/ を作成して保存します")

        # 保存先ディレクトリ作成
        output_dir = ensure_output_dir(platform_directory, broadcaster_id, broadcaster_name)
        
        # 一時作業ディレクトリセットアップ
        setup_tmp_directory()

        # デバッグChrome準備・ウィンドウアクティブ化
        if not prepare_debug_chrome():
            DEBUGLOG.error("Chrome準備に失敗しました")
            return False

        # 新しいタブを作成
        tab_handle = create_new_recording_tab()

        # 配信ページに移動
        DEBUGLOG.info(f"配信ページに移動: {target_url}")
        driver.get(target_url)
        time.sleep(3)

        # フルスクリーンボタンと再生ボタンクリック
        full_screen_button_click()
        time.sleep(1)
        play_button_click()
        time.sleep(2)

        # 最初のセグメント情報作成
        recording_start_time = int(time.time())
        current_segment = 0
        first_segment = {
            'segment_id': current_segment,
            'start_time': recording_start_time,
            'end_time': None,
            'file': None
        }
        recording_segments.append(first_segment)

        # 録画開始
        start_recording()
        
        DEBUGLOG.info(f"セグメント{current_segment}録画開始: {recording_start_time}")
        DEBUGLOG.info(f"保存先: {output_dir}")

        # 30分タイマー開始
        schedule_next_segment_switch()

        # ユーザー設定自動生成
        create_user_config_if_needed(
            account_id=broadcaster_id,
            display_name=broadcaster_name,
            lv_no=broadcast_id,
            lv_title=broadcast_title,
            tab_id=tab_handle,
            start_time=recording_start_time
        )

        # broadcast_checker起動
        run_broadcast_checker(
            lv_no=broadcast_id,
            account_id=broadcaster_id,
            lv_title=broadcast_title,
            display_name=broadcaster_name,
            tab_id=tab_handle,
            start_time=recording_start_time
        )

        print("30分セグメント録画が開始されました")
        print("手動で終了するか、Ctrl+Cで停止してください")
        print(f"セグメント間隔: {SEGMENT_DURATION}秒（{SEGMENT_DURATION//60}分）")
        print(f"保存先: {output_dir}")

        # メインループ（Ctrl+C待機）
        try:
            while True:
                time.sleep(10)
                if not recording_active:
                    DEBUGLOG.warning("録画が非アクティブになりました")
                    break
        except KeyboardInterrupt:
            DEBUGLOG.info("ユーザーによる停止要求を受信")
            stop_all_recording()

        return True

    except Exception as e:
        DEBUGLOG.error(f"メイン処理でエラーが発生: {e}", exc_info=True)
        
        # エラー時も最終処理実行
        try:
            stop_all_recording()
        except:
            pass
        
        return False

if __name__ == "__main__":
    try:
        success = bool(main())
        if success:
            DEBUGLOG.info("録画システム正常終了")
        else:
            DEBUGLOG.error("録画システム異常終了")
    except KeyboardInterrupt:
        DEBUGLOG.info("キーボード割り込みによる終了")
        try:
            stop_all_recording()
        except:
            pass
    except Exception as e:
        DEBUGLOG.error(f"予期しないエラー: {e}", exc_info=True)
        try:
            stop_all_recording()
        except:
            pass