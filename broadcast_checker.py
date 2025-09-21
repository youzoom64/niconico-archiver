# broadcast_checker.py
# 外部起動用：配信終了を30秒ごとに監視し、終了時に
# 1) 指定のChromeタブを閉じる（ベストエフォート）
# 2) download_directory内の recording-*.webm を探す
# 3) ffmpegで .mp4 に変換し、{start_time}_{lv_no}_{lv_title}.mp4 に改名
# 4) {platform_directory}/{account_id}_{display_name}/ に移動
#
# 受け取る引数:
#   -lv_no         例: lv999999999
#   -account_id    例: 12345
#   -lv_title      例: テスト配信
#   -display_name  例: テスト配信者
#   -tab_id        （任意）Seleniumのwindow_handle（別プロセスからの完全一致は期待せずベストエフォート）
#   -start_time    録画開始UNIX時刻（秒）
#
# 依存:
#   pip: requests, selenium
#   PATH: ffmpeg
#
# 設定ファイル:
#   config/users/{account_id}.json
#   - basic_settings.download_directory  … ダウンロード保存元
#   - basic_settings.platform_directory  … 作品の最終移動先ルート

import argparse
import json
import logging
import os
import re
import shutil
import subprocess
import time
from datetime import datetime
from typing import Optional, Tuple

import requests

# Selenium は「該当タブを閉じる」ためのベストエフォート用途
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import WebDriverException


# ===== ログ設定 =====
os.makedirs('logs', exist_ok=True)
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler('logs/broadcast_checker.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
LOG = logging.getLogger("broadcast_checker")

# ====== ユーティリティ ======
def sanitize_path_component(name: str) -> str:
    invalid = '<>:"/\\|?*\t\r\n'
    table = str.maketrans({ch: "_" for ch in invalid})
    out = name.translate(table).strip().rstrip(".")
    return out or "unknown"

def load_user_config(account_id: str) -> Optional[dict]:
    path = os.path.join("config", "users", f"{account_id}.json")
    if not os.path.exists(path):
        LOG.error(f"ユーザー設定が見つかりません: {path}")
        return None
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        LOG.error(f"ユーザー設定読込失敗: {path} / {e}")
        return None

def ensure_output_dir(platform_directory: str, account_id: str, display_name: str) -> str:
    safe_name = sanitize_path_component(display_name)
    base = platform_directory or os.path.abspath(os.path.join(".", "rec"))
    out = os.path.join(base, f"{account_id}_{safe_name}")
    os.makedirs(out, exist_ok=True)
    return out

def attach_debug_chrome(debug_port: int = 9222) -> Optional[webdriver.Chrome]:
    """Chrome デバッグにアタッチ（起動していない場合は失敗）"""
    try:
        options = Options()
        options.add_experimental_option("debuggerAddress", f"127.0.0.1:{debug_port}")
        driver = webdriver.Chrome(options=options)
        LOG.info("Selenium: デバッグChromeに接続")
        return driver
    except WebDriverException as e:
        LOG.warning(f"Selenium接続失敗: {e}")
        return None

def close_target_tab_by_id_with_retry(driver: webdriver.Chrome, tab_id: str, max_retries: int = 3, retry_delay: int = 2) -> bool:
    """
    渡された tab_id でタブを閉じ、失敗時はリトライする
    
    Args:
        driver: Chromeドライバー
        tab_id: 閉じるタブのID
        max_retries: 最大リトライ回数
        retry_delay: リトライ間隔（秒）
    
    Returns:
        bool: 成功時True、失敗時False
    """
    import time
    
    for attempt in range(max_retries + 1):  # +1で初回実行を含む
        try:
            LOG.debug(f"タブクローズ試行 {attempt + 1}/{max_retries + 1}: {tab_id}")
            
            # 現在のタブ一覧を取得
            current_handles = set(driver.window_handles)
            LOG.debug(f"現在のwindow_handles: {current_handles}")
            
            if tab_id not in current_handles:
                LOG.info(f"タブは既に存在しません: {tab_id}")
                return True
            
            # タブをクローズ
            driver.switch_to.window(tab_id)
            driver.close()
            
            # クローズ確認のための待機
            time.sleep(1)
            
            # クローズ後のタブ一覧を取得
            after_handles = set(driver.window_handles)
            LOG.debug(f"クローズ後のwindow_handles: {after_handles}")
            
            # タブが実際に消えたかチェック
            if tab_id not in after_handles:
                LOG.info(f"タブクローズ成功: {tab_id} (試行 {attempt + 1})")
                return True
            else:
                LOG.warning(f"タブクローズ失敗（まだ存在）: {tab_id} (試行 {attempt + 1})")
                
                # 最後の試行でない場合はリトライ
                if attempt < max_retries:
                    LOG.info(f"{retry_delay}秒後にリトライします")
                    time.sleep(retry_delay)
                
        except Exception as e:
            LOG.error(f"タブクローズでエラー (試行 {attempt + 1}): {e}")
            
            # 最後の試行でない場合はリトライ
            if attempt < max_retries:
                LOG.info(f"{retry_delay}秒後にリトライします")
                time.sleep(retry_delay)
    
    LOG.error(f"タブクローズ最終失敗: {tab_id} (全{max_retries + 1}回試行)")
    return False

def close_target_tab_by_id(driver: webdriver.Chrome, tab_id: str) -> bool:
    """既存の関数をリトライ版に置き換え"""
    return close_target_tab_by_id_with_retry(driver, tab_id)

def read_recording_tab_json(lv_no: str) -> Tuple[Optional[str], Optional[int]]:
    """auto_recorder が出力した recording_tab_{lv_no}.json から target_url と start_time を拾う"""
    path = f"recording_tab_{lv_no}.json"
    if not os.path.exists(path):
        return None, None
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        target_url = data.get("target_url")
        start_time = data.get("start_time")
        return target_url, start_time
    except Exception:
        return None, None

def check_broadcast_end(lv_value: str) -> bool:
    """
    JSON-LDメタデータを使用した改善された終了検知
    """
    try:
        url = f"https://live.nicovideo.jp/watch/{lv_value}"
        headers = {
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/120.0.0.0 Safari/537.36"
            ),
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
            "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
        }
        
        resp = requests.get(url, timeout=30, headers=headers)
        resp.raise_for_status()
        resp.encoding = 'utf-8'
        html = resp.text

        # 方法1: JSON-LDメタデータから終了時刻を取得
        json_ld_matches = re.findall(r'<script[^>]*type=["\']application/ld\+json["\'][^>]*>([^<]*)</script>', html, re.IGNORECASE)
        
        for json_str in json_ld_matches:
            try:
                data = json.loads(json_str)
                if isinstance(data, dict) and data.get('@type') == 'BroadcastEvent':
                    end_date = data.get('endDate')
                    if end_date:
                        try:
                            # ISO形式の日時をパース
                            end_datetime = datetime.fromisoformat(end_date.replace('Z', '+00:00'))
                            current_datetime = datetime.now(end_datetime.tzinfo)
                            
                            if current_datetime > end_datetime:
                                LOG.info(f"[JSON-LD終了検知] {lv_value}: endDate={end_date}")
                                return True
                            else:
                                LOG.info(f"[JSON-LD継続中] {lv_value}: endDate={end_date}")
                                return False
                        except ValueError as ve:
                            LOG.debug(f"日時パース失敗: {end_date} / {ve}")
                            continue
            except (json.JSONDecodeError, KeyError) as je:
                LOG.debug(f"JSON-LD解析失敗: {je}")
                continue

        # 方法2: フォールバック - 従来の終了パターンチェック
        LOG.debug("JSON-LDで判定できないため従来方式で判定")
        
        end_patterns = [
            # 具体的な日本語メッセージ
            "タイムシフト非公開番組です",
            "タイムシフト非公開番組",
            "非公開番組です",
            "公開終了",
            "公開期間が終了",
            "配信終了",
            "放送は終了",
            "放送終了",
            "番組は終了",
            "番組終了",
            "視聴できません",
            "アクセスできません",
            "終了しました",
            
            # data-status 系
            'data-status="endPublication"',
            'data-status="ended"',
            'data-status="finished"',
            'data-status="closed"',
            
            # その他
            "endPublication",
            "タイムシフト再生中",
        ]
        
        for pattern in end_patterns:
            if pattern in html:
                LOG.info(f"[パターン終了検知] {lv_value}: pattern='{pattern}'")
                return True

        # 方法3: ライブ要素の存在チェック（継続中判定のため）
        live_indicators = [
            r'"isLive":\s*true',
            r'"status":\s*"ON_AIR"',
            r'class="[^"]*___player___[^"]*"',
            r'id="js-app"',
        ]
        
        live_found = False
        for pattern in live_indicators:
            if re.search(pattern, html, re.IGNORECASE):
                live_found = True
                break
        
        if not live_found:
            LOG.info(f"[ライブ要素不在] {lv_value}: ライブ要素が見つからないため終了判定")
            return True

        # 未終了
        LOG.info(f"[継続中] {lv_value}")
        return False

    except Exception as e:
        LOG.error(f"終了チェック失敗 {lv_value}: {e}")
        # エラー時は終了扱い
        return True

def pick_and_wait_recording_file(
    download_dir: str,
    start_time_unix: int,
    retries: int = 60,
    interval: int = 2,
    stable_checks: int = 3
) -> Optional[str]:
    """
    recording-*.webm を探して start_time*1000 に最も近いものを選び、
    ファイルサイズが安定するまで待機して返す。
    """
    if not os.path.isdir(download_dir):
        LOG.error(f"download_directory が存在しない: {download_dir}")
        return None

    target_ms = start_time_unix * 1000
    rx = re.compile(r"^recording-(\d+)\.webm$", re.IGNORECASE)

    for attempt in range(retries):
        candidates = []
        for name in os.listdir(download_dir):
            m = rx.match(name)
            if not m:
                continue
            full = os.path.join(download_dir, name)
            if os.path.isfile(full):
                try:
                    stamp = int(m.group(1))
                    candidates.append((full, stamp))
                except ValueError:
                    continue

        if candidates:
            candidates.sort(key=lambda x: abs(x[1] - target_ms))
            chosen, stamp = candidates[0]
            LOG.info(f"録画ファイル候補: {os.path.basename(chosen)} (差={stamp - target_ms}ms)")

            last_size = -1
            stable_count = 0
            while True:
                size = os.path.getsize(chosen)
                if size == last_size and size > 0:
                    stable_count += 1
                    if stable_count >= stable_checks:
                        LOG.info(f"録画ファイル安定化完了: {os.path.basename(chosen)}")
                        return chosen
                else:
                    stable_count = 0
                last_size = size
                time.sleep(interval)
        else:
            LOG.debug(f"録画ファイル未発見、リトライ {attempt+1}/{retries}")
            time.sleep(interval)

    LOG.error(f"録画ファイルが見つからない/安定しない: start_time={start_time_unix}")
    return None

def convert_webm_to_mp4(src_webm: str, dst_mp4: str) -> bool:
    """
    ffmpeg で webm -> mp4 へ変換。
    コンテナコピーは互換性でコケやすいので再エンコード（H.264/AAC）にする。
    """
    cmd = [
        "ffmpeg",
        "-y",
        "-i", src_webm,
        "-c:v", "libx264",
        "-preset", "veryfast",
        "-crf", "18",
        "-c:a", "aac",
        "-b:a", "192k",
        dst_mp4
    ]
    LOG.info("ffmpeg 変換開始")
    try:
        res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
        if res.returncode != 0:
            LOG.error(f"ffmpeg 失敗: {res.stderr[:500]}")
            return False
        LOG.info("ffmpeg 変換成功")
        return True
    except Exception as e:
        LOG.error(f"ffmpeg 実行エラー: {e}")
        return False

def move_to_library(src_path: str, platform_directory: str, account_id: str, display_name: str) -> Optional[str]:
    dst_dir = ensure_output_dir(platform_directory, account_id, display_name)
    dst_path = os.path.join(dst_dir, os.path.basename(src_path))
    try:
        shutil.move(src_path, dst_path)
        LOG.info(f"動画移動: {dst_path}")
        return dst_path
    except Exception as e:
        LOG.error(f"動画移動失敗: {e}")
        return None

# ===== メイン処理 =====
def main():
    parser = argparse.ArgumentParser(description="broadcast_checker: 配信終了検知と後処理")
    parser.add_argument("-lv_no", required=True)
    parser.add_argument("-account_id", required=True)
    parser.add_argument("-lv_title", required=True)
    parser.add_argument("-display_name", required=True)
    parser.add_argument("-tab_id", required=False, default=None)
    parser.add_argument("-start_time", required=True, type=int)
    parser.add_argument("-debug_port", required=False, type=int, default=9222)
    args = parser.parse_args()

    lv_no = args.lv_no
    account_id = args.account_id
    lv_title = args.lv_title
    display_name = args.display_name
    tab_id = args.tab_id
    start_time = args.start_time
    debug_port = args.debug_port

    LOG.info(f"開始: lv_no={lv_no}, account_id={account_id}, lv_title={lv_title}, display_name={display_name}, start_time={start_time}, tab_id={tab_id}")

    # 設定ロード
    user_cfg = load_user_config(account_id)
    if not user_cfg:
        return 1

    basic = user_cfg.get("basic_settings", {}) or {}
    download_directory = basic.get("download_directory")
    platform_directory = basic.get("platform_directory")

    if not download_directory:
        LOG.error("config から download_directory を取得できませんでした")
        return 2
    if not platform_directory:
        LOG.error("config から platform_directory を取得できませんでした")
        return 3

    # recording_tab_{lv_no}.json からURL（と開始時刻の補助）を拾う
    saved_target_url, saved_start_time = read_recording_tab_json(lv_no)
    if not start_time and saved_start_time:
        start_time = int(saved_start_time)

    # 30秒ごとの終了監視
    while True:
        ended = check_broadcast_end(lv_no)
        if ended:
            LOG.info("配信終了を検知")
            break
        LOG.info("継続中。30秒待機")
        time.sleep(30)

    # タブを閉じる（ベストエフォート）
    driver = attach_debug_chrome(debug_port=debug_port)
    if driver:
        try:
            if tab_id:
                closed = close_target_tab_by_id(driver, tab_id)
                if not closed:
                    LOG.error("tab_id で指定したタブを閉じられませんでした")
            else:
                LOG.error("tab_id が指定されていません。タブを閉じられません")
        finally:
            try:
                driver.quit()
            except Exception:
                pass

    time.sleep(3)  # タブクローズ後の安定化待ち

    # 録画ファイル探索
    webm_path = pick_and_wait_recording_file(download_directory, start_time)
    if not webm_path:
        return 4

    # 出力ファイル名生成
    safe_title = sanitize_path_component(lv_title)
    out_name = f"{start_time}_{lv_no}_{safe_title}.mp4"
    tmp_out = os.path.join(os.path.dirname(webm_path), out_name)

    # 変換
    ok = convert_webm_to_mp4(webm_path, tmp_out)
    if not ok:
        return 5

    # 移動
    final_path = move_to_library(tmp_out, platform_directory, account_id, display_name)
    if not final_path:
        return 6

    LOG.info("broadcast_checker: 完了")
    return 0

if __name__ == "__main__":
    raise SystemExit(main())