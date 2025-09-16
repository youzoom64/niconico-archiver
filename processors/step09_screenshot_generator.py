# processors/step09_screenshot_generator.py
import os
import json
import math
import subprocess
from datetime import datetime
import sys

# utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

# プロジェクトルート（このファイルの親の親をルートとする想定）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
FFMPEG_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffmpeg.exe") if os.name == "nt" else "ffmpeg"

STEP_DEFAULT = 10  # 10秒刻み

def process(pipeline_data):
    """Step09: スクリーンショット生成"""
    try:
        lv_value = pipeline_data['lv_value']
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        config = pipeline_data.get('config', {})

        print(f"Step09 開始: {lv_value}")

        # 機能ON/OFF
        if not config.get("display_features", {}).get("enable_thumbnails", True):
            print("サムネイル生成機能が無効です。処理をスキップします。")
            return {"screenshot_generated": False, "reason": "feature_disabled"}

        # 間隔（秒）
        step_seconds = int(config.get("display_features", {}).get("thumbnail_interval_seconds", STEP_DEFAULT))

        # ディレクトリ系
        account_dir = find_account_directory(platform_directory, account_id)
        broadcast_dir = os.path.join(account_dir, lv_value)
        os.makedirs(broadcast_dir, exist_ok=True)

        # MP4 検索
        mp4_path = find_mp4_file(account_dir, lv_value)
        if not mp4_path:
            raise Exception(f"MP4ファイルが見つかりません: {lv_value}")
        print(f"MP4ファイル発見: {mp4_path}")

        # 統合JSON
        data = load_broadcast_data(broadcast_dir, lv_value)
        video_duration = float(data.get("video_duration", 0.0))  # 録画の長さ（秒）
        time_diff_seconds = int(data.get("time_diff_seconds", 0))  # 録画→配信のオフセット

        # スクショ保存先
        screenshot_dir = os.path.join(broadcast_dir, "screenshot", lv_value)
        os.makedirs(screenshot_dir, exist_ok=True)

        # 最初の発話(配信基準) → 録画基準に変換して開始点を決める
        earliest_speech_ts_broadcast = load_earliest_transcript_ts(broadcast_dir, lv_value)
        # 録画基準秒に戻す（負にはしない）
        start_recording_seconds = max(0, earliest_speech_ts_broadcast - time_diff_seconds)
        # 10秒グリッドに揃える（floor）
        start_recording_seconds = (start_recording_seconds // step_seconds) * step_seconds

        # 上限（録画の最終秒・floor）
        end_recording_seconds = int(math.floor(video_duration))

        # 生成
        count = generate_screenshots(
            mp4_path=mp4_path,
            screenshot_dir=screenshot_dir,
            start_recording_seconds=start_recording_seconds,
            end_recording_seconds=end_recording_seconds,
            step_seconds=step_seconds,
            time_diff_seconds=time_diff_seconds
        )

        print(f"Step09 完了: {lv_value} - スクリーンショット生成数: {count}")
        return {
            "screenshot_generated": True,
            "screenshot_count": count,
            "screenshot_dir": screenshot_dir
        }

    except Exception as e:
        print(f"Step09 エラー: {str(e)}")
        raise


# ---------------------- helpers ----------------------

def find_mp4_file(account_dir, lv_value):
    """アカウント配下で lv を含む MP4 を1つ返す（最初に見つかったもの）"""
    if not os.path.exists(account_dir):
        return None
    for filename in os.listdir(account_dir):
        if filename.endswith(".mp4") and lv_value in filename:
            return os.path.join(account_dir, filename)
    return None


def load_broadcast_data(broadcast_dir, lv_value):
    """統合JSON"""
    path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    if not os.path.exists(path):
        raise Exception(f"統合JSONファイルが見つかりません: {path}")
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def load_earliest_transcript_ts(broadcast_dir, lv_value):
    """
    文字起こしJSONから最初(最小)のtimestamp（配信基準秒）を返す。無ければ0。
    """
    path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
    try:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts_list = []
            for t in data.get("transcripts", []):
                ts = t.get("timestamp")
                if isinstance(ts, (int, float)):
                    ts_list.append(int(ts))
            if ts_list:
                ts_min = max(0, min(ts_list))
                return ts_min
    except Exception:
        pass
    return 0


def generate_screenshots(
    mp4_path,
    screenshot_dir,
    start_recording_seconds,
    end_recording_seconds,
    step_seconds,
    time_diff_seconds
):
    """
    ffmpegでサムネイル生成。
    - 既存PNGがあればスキップ（上書きしない）
    - ffmpeg出力は text=False（バイナリ） & -loglevel error で CP932 デコード事故回避
    - ログは「録画秒 → 配信秒 → タイムブロック秒 → パス」
    """
    saved_count = 0

    for recording_seconds in range(start_recording_seconds, end_recording_seconds + 1, step_seconds):
        # 配信基準秒へ
        broadcast_seconds = recording_seconds + time_diff_seconds
        # 10秒ブロックへ ceil
        timeline_block = int(math.ceil(broadcast_seconds / step_seconds) * step_seconds)

        out_file = os.path.join(screenshot_dir, f"{recording_seconds}.png")

        # 既存ならスキップ
        if os.path.exists(out_file) and os.path.getsize(out_file) > 0:
            print(f"録画{recording_seconds}秒 → 配信{broadcast_seconds}秒 → タイムブロック{timeline_block}秒 → 既存のためスキップ")
            continue

        # ffmpeg 実行（-ss を -i の前に置いて高速シーク）
        cmd = [
            FFMPEG_PATH,
            "-loglevel", "error",
            "-ss", str(recording_seconds),
            "-i", mp4_path,
            "-frames:v", "1",
            "-y",  # 出力が壊れている/0byteの時だけ上書きさせたいので -y 付ける。正常ファイルは上の存在チェックでスキップ済み
            out_file,
        ]

        try:
            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=False,  # ← バイナリで読む（CP932事故回避）
                creationflags=(0x08000000 if os.name == "nt" else 0)
            )
            if result.returncode == 0 and os.path.exists(out_file) and os.path.getsize(out_file) > 0:
                print(f"録画{recording_seconds}秒 → 配信{broadcast_seconds}秒 → タイムブロック{timeline_block}秒 → {out_file}")
                saved_count += 1
            else:
                err = (result.stderr or b"")[:200].decode("utf-8", errors="ignore")
                print(f"FFmpeg失敗@{recording_seconds}s: {err}")
                # 失敗時は壊れた出力を消す
                try:
                    if os.path.exists(out_file) and os.path.getsize(out_file) == 0:
                        os.remove(out_file)
                except Exception:
                    pass

        except Exception as e:
            print(f"スクリーンショット生成エラー (録画{recording_seconds}秒): {str(e)}")
            try:
                if os.path.exists(out_file) and os.path.getsize(out_file) == 0:
                    os.remove(out_file)
            except Exception:
                pass

    return saved_count
