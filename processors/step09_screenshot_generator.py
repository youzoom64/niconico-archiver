import os
import json
from datetime import datetime
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory
import math

def process(pipeline_data):
    """Step09: スクリーンショット生成"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step09 開始: {lv_value}")
        
        # 1. サムネイル生成機能が有効か確認
        if not config["display_features"].get("enable_thumbnails", True):
            print("サムネイル生成機能が無効です。処理をスキップします。")
            return {"screenshot_generated": False, "reason": "feature_disabled"}
        
        # 2. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. MP4ファイル検索
        mp4_path = find_mp4_file(account_dir, lv_value)
        if not mp4_path:
            raise Exception(f"MP4ファイルが見つかりません: {lv_value}")
        
        # 4. 統合JSONから動画時間とtime_diff_seconds取得
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        video_duration = broadcast_data.get('video_duration', 0.0)
        time_diff_seconds = broadcast_data.get('time_diff_seconds', 0)
        
        # 5. スクリーンショットディレクトリ作成
        screenshot_dir = os.path.join(broadcast_dir, "screenshot", lv_value)
        os.makedirs(screenshot_dir, exist_ok=True)
        
        # 6. スクリーンショット生成
        screenshot_count = generate_screenshots(mp4_path, screenshot_dir, video_duration, time_diff_seconds)
        
        print(f"Step09 完了: {lv_value} - スクリーンショット生成数: {screenshot_count}")
        return {
            "screenshot_generated": True, 
            "screenshot_count": screenshot_count, 
            "screenshot_dir": screenshot_dir
        }
        
    except Exception as e:
        print(f"Step09 エラー: {str(e)}")
        raise

def find_mp4_file(account_dir, lv_value):
    """MP4ファイルを検索"""
    if not os.path.exists(account_dir):
        return None
    
    for filename in os.listdir(account_dir):
        if filename.endswith('.mp4') and lv_value in filename:
            mp4_path = os.path.join(account_dir, filename)
            print(f"MP4ファイル発見: {mp4_path}")
            return mp4_path
    
    return None

def load_broadcast_data(broadcast_dir, lv_value):
    """統合JSONファイルを読み込み"""
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise Exception(f"統合JSONファイルが見つかりません: {json_path}")

def generate_screenshots(mp4_path, screenshot_dir, video_duration, time_diff_seconds):
    """録画ファイルから10秒刻みでスクリーンショット生成"""
    try:
        screenshot_count = 0
        
        for recording_seconds in range(0, int(video_duration) + 1, 10):
            if recording_seconds > video_duration:
                break
                
            # 配信時間を計算
            broadcast_seconds = recording_seconds + time_diff_seconds
            
            # タイムブロック位置を計算（10の倍数に切り上げ）
            timeline_position = math.ceil(broadcast_seconds / 10.0) * 10
            
            output_path = os.path.join(screenshot_dir, f"{recording_seconds}.png")
            
            # ffmpegでスクリーンショット生成
            cmd = [
                'ffmpeg', '-y',
                '-ss', str(recording_seconds),
                '-i', mp4_path,
                '-vframes', '1',
                '-q:v', '2',
                '-f', 'image2',
                output_path
            ]
            
            try:
                result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore', timeout=30)
                if result.returncode == 0:
                    screenshot_count += 1
                    print(f"録画{recording_seconds}秒 → 配信{broadcast_seconds}秒 → タイムブロック{timeline_position}秒 → {output_path}")
                else:
                    print(f"スクリーンショット生成失敗 (録画{recording_seconds}秒): {result.stderr}")
                    
            except subprocess.TimeoutExpired:
                print(f"スクリーンショット生成タイムアウト: 録画{recording_seconds}秒")
            except Exception as e:
                print(f"スクリーンショット生成エラー (録画{recording_seconds}秒): {str(e)}")
        
        return screenshot_count
        
    except Exception as e:
        print(f"スクリーンショット生成処理エラー: {str(e)}")
        return 0