# bloadcast_checker.py
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
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
)
LOG = logging.getLogger("bloadcast_checker")

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

def close_target_tab_by_id(driver: webdriver.Chrome, tab_id: str) -> bool:
    """渡された tab_id でタブを閉じる。成功すれば True、失敗すれば False。"""
    LOG.debug(f"受け取った tab_id: {tab_id}")
    try:
        LOG.debug(f"現在の window_handles: {driver.window_handles}")
        driver.switch_to.window(tab_id)
        driver.close()
        LOG.info(f"tab_id でタブをクローズ成功: {tab_id}")
        return True
    except Exception as e:
        LOG.error(f"tab_id でのタブクローズ失敗: {e}")
        return False


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
    さっき提示の _check_broadcast_end をベースに単体関数化。
    ※ デバッグ用の「パターン未検出でもTrue」は安全のため外しています。
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
        html = resp.text

        end_patterns = [
            'data-status="endPublication"',
            "公開終了",
            'data-status="ended"',
            'data-status="finished"',
            "endPublication",
            "タイムシフト再生中",
            "放送は終了",
            "番組は終了",
            "配信終了",
            "視聴できません",
        ]
        for p in end_patterns:
            if p in html:
                LOG.info(f"[END DETECTED] {lv_value} : pattern='{p}'")
                return True

        # 未終了
        return False

    except Exception as e:
        LOG.error(f"終了チェック失敗 {lv_value}: {e}")
        # エラー時は「終了扱い」にするかは運用判断。ここでは終了扱いにする。
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
    parser = argparse.ArgumentParser(description="bloadcast_checker: 配信終了検知と後処理")
    parser.add_argument("-lv_no", required=True)
    parser.add_argument("-account_id", required=True)
    parser.add_argument("-lv_title", required=True)
    parser.add_argument("-display_name", required=True)
    parser.add_argument("-tab_id", required=False, default=None)   # 将来利用（現状はURL一致でクローズ）
    parser.add_argument("-start_time", required=True, type=int)    # UNIX秒
    parser.add_argument("-debug_port", required=False, type=int, default=9222)  # Chromeデバッグポート
    args = parser.parse_args()

    lv_no = args.lv_no
    account_id = args.account_id
    lv_title = args.lv_title
    display_name = args.display_name
    tab_id = args.tab_id  # 受けはするがハンドル一致は別プロセスでは保証不可
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
    # タブを閉じる（tab_id 必須）
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
                driver.quit()  # セッションを完全に終了
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

    # 元のwebmは残す/消すは方針次第。ここでは残す。消したいなら以下を有効化。
    # try:
    #     os.remove(webm_path)
    # except Exception:
    #     pass

    # 移動
    final_path = move_to_library(tmp_out, platform_directory, account_id, display_name)
    if not final_path:
        return 6

    LOG.info("bloadcast_checker: 完了")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
