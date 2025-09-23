import argparse
import time
import logging
import os
import json
import subprocess
from recorder_modules.config_loader import load_user_config, load_global_config, ensure_output_dir
from recorder_modules.chrome_manager import ChromeManager
from recorder_modules.recording_controller import RecordingController
from recorder_modules.segment_manager import SegmentManager
from recorder_modules.broadcast_monitor import BroadcastMonitor
from recorder_modules.video_processor import VideoProcessor

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

# 設定定数
CHROME_PATH = r"C:\Program Files\Google\Chrome\Application\chrome.exe"
USER_DATA_DIR = r"C:\ChromeDebug"
PROFILE_NAME = "Default"
DEBUG_PORT = "9222"
TARGET_MONITOR = 3

EXTENSION_COORDINATES = {
    'extension_icon': (360, 65),
    'start_button': (310, 160),
    'stop_button': (325, 165),
}

def parse_arguments():
    """コマンドライン引数をパース"""
    parser = argparse.ArgumentParser(description='ニコニコ生放送録画システム（30分セグメント対応）')
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

def create_user_config_if_needed(account_id: str, display_name: str, lv_no: str, lv_title: str, tab_id: str, start_time: int):
    """ユーザー設定処理（エラー時は無視して録画継続）"""
    try:
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
        
        res = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
        if res.returncode == 0:
            DEBUGLOG.info("ユーザー設定処理成功")
        else:
            DEBUGLOG.warning("ユーザー設定処理でエラーが発生しましたが、録画は継続します")
            
    except Exception as e:
        DEBUGLOG.warning(f"ユーザー設定処理をスキップ: {e}")

def main():
    """メイン処理"""
    print("ニコニコ生放送録画システム（30分セグメント対応）")
    print("=" * 60)
    DEBUGLOG.info("録画システム起動")

    try:
        # 引数パース & タグ分解
        target_url, tag = parse_arguments()
        broadcast_id, broadcast_title, broadcaster_name, broadcaster_id = parse_broadcast_tag(tag)

        # グローバル設定読み込み
        global_cfg = load_global_config()
        download_directory = global_cfg["system"]["download_directory"]

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
        
        # 一時作業ディレクトリ
        tmp_dir = os.path.join('.', 'tmp')

        # 各マネージャーの初期化（順序重要）
        chrome_manager = ChromeManager(CHROME_PATH, USER_DATA_DIR, PROFILE_NAME, DEBUG_PORT, TARGET_MONITOR)
        recording_controller = RecordingController(chrome_manager, EXTENSION_COORDINATES)
        video_processor = VideoProcessor(tmp_dir, output_dir, download_directory)
        segment_manager = SegmentManager(recording_controller, video_processor)
        broadcast_monitor = BroadcastMonitor(broadcast_id)

        # 一時ディレクトリセットアップ
        video_processor.setup_tmp_directory()

        # Chrome準備
        if not chrome_manager.prepare_debug_chrome():
            DEBUGLOG.error("Chrome準備に失敗しました")
            return False

        # 新しいタブを作成してページ移動
        tab_handle = chrome_manager.create_new_recording_tab()
        chrome_manager.navigate_to_url(target_url)

        # 1. 画面サイズ650px
        chrome_manager.driver.set_window_size(650, 500)
        time.sleep(0.3)

        # 配信終了監視開始
        broadcast_monitor.start_monitoring()

        # 2. 録画アイコンクリック → スタートクリック
        recording_start_time = segment_manager.start_segment_recording(broadcast_id, broadcast_title)

        # 3. 画面サイズ200px x 200px
        time.sleep(0.3)
        chrome_manager.driver.set_window_size(200, 400)
        time.sleep(0.3)

        # 4. 再生ボタンクリック
        chrome_manager.click_play_button()
        time.sleep(0.3)

        # 5. フルスクリーンボタンクリック
        chrome_manager.click_fullscreen_button()

        print("30分セグメント録画が開始されました")
        print("配信終了まで自動録画を継続します")
        print(f"セグメント間隔: 30分")
        print(f"保存先: {output_dir}")
        DEBUGLOG.info(f"保存先: {output_dir}")

        # ユーザー設定自動生成
        create_user_config_if_needed(
            account_id=broadcaster_id,
            display_name=broadcaster_name,
            lv_no=broadcast_id,
            lv_title=broadcast_title,
            tab_id=tab_handle,
            start_time=recording_start_time
        )

        # メインループ（配信終了まで待機）
        try:
            while not broadcast_monitor.is_broadcast_ended():
                time.sleep(5)  # 5秒間隔でチェック
                
                # セグメント状態確認
                if not segment_manager.is_segment_active():
                    DEBUGLOG.warning("セグメントが非アクティブになりました")
                    break
            
            DEBUGLOG.info("配信終了を検知、録画停止処理開始")
            
        except KeyboardInterrupt:
            DEBUGLOG.info("ユーザーによる停止要求を受信")

        # 録画停止・後処理
        broadcast_monitor.stop_monitoring()
        segment_manager.stop_all_segments()

        # セグメント毎のファイル処理
        segments_info = segment_manager.get_segments_info()
        recording_segments = segments_info['segments']
        segment_gaps = segments_info['gaps']

        DEBUGLOG.info(f"録画されたセグメント数: {len(recording_segments)}")
        DEBUGLOG.info(f"セグメント間隙間数: {len(segment_gaps)}")

        # 各セグメントの動画ファイル処理（バックグラウンド処理で既に完了済み）
        # 追加処理が必要な場合のみ実行
        for segment in recording_segments:
            if segment['end_time'] and not segment.get('processed', False):
                if not video_processor.process_segment(segment, broadcast_title):
                    DEBUGLOG.error(f"セグメント{segment['segment_id']}の処理に失敗")

        # 最終動画結合
        if recording_segments:
            if video_processor.merge_all_segments(broadcast_id, recording_segments, segment_gaps):
                DEBUGLOG.info("最終動画結合成功")
            else:
                DEBUGLOG.error("最終動画結合失敗")

        return True

    except Exception as e:
        DEBUGLOG.error(f"メイン処理でエラーが発生: {e}", exc_info=True)
        return False
    
    finally:
        # クリーンアップ
        try:
            video_processor.cleanup_tmp_directory()
        except:
            pass

if __name__ == "__main__":
    try:
        success = bool(main())
        if success:
            DEBUGLOG.info("録画システム正常終了")
        else:
            DEBUGLOG.error("録画システム異常終了")
    except KeyboardInterrupt:
        DEBUGLOG.info("キーボード割り込みによる終了")
    except Exception as e:
        DEBUGLOG.error(f"予期しないエラー: {e}", exc_info=True)