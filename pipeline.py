import sys
import json
import os
from datetime import datetime
import importlib

def load_user_config(user_name):
    """ユーザー設定を読み込む"""
    config_path = f"config/users/{user_name}.json"
    if os.path.exists(config_path):
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def should_run_step(config, step_name):
    """設定に基づいてステップを実行するかチェック"""
    step_mapping = {
        'step02_transcript': config['ai_features']['enable_summary_text'],
        'step03_comment': config['display_features']['enable_comment_ranking'],
        'step04_emotion': config['display_features']['enable_emotion_scores'],
        'step05_screenshot': config['display_features']['enable_thumbnails'],
        'step06_summary': config['ai_features']['enable_summary_text'],
        'step07_image': config['ai_features']['enable_summary_image'],
        'step08_music': config['ai_features']['enable_ai_music'],
        'step09_html': True,  # 常に実行
        'step10_cleanup': True  # 常に実行
    }
    return step_mapping.get(step_name, True)

def run_pipeline(platform, account_id, platform_directory, ncv_directory, lv_value, user_name):
    """パイプライン処理を実行"""
    try:
        # ユーザー設定を読み込み
        config = load_user_config(user_name)
        if not config:
            raise Exception(f"ユーザー設定が見つかりません: {user_name}")
        
        print(f"[{user_name}] パイプライン開始: {lv_value}")
        
        # 処理データを準備
        pipeline_data = {
            'platform': platform,
            'account_id': account_id,
            'platform_directory': platform_directory,
            'ncv_directory': ncv_directory,
            'lv_value': lv_value,
            'user_name': user_name,
            'config': config,
            'start_time': datetime.now(),
            'results': {}
        }
        
        # 各ステップを順次実行
        steps = [
            'step01_extract',
            'step02_transcript',
            'step03_comment',
            'step04_emotion',
            'step05_screenshot',
            'step06_summary',
            'step07_image',
            'step08_music',
            'step09_html',
            'step10_cleanup'
        ]
        
        for step_name in steps:
            if should_run_step(config, step_name):
                print(f"[{user_name}] 実行中: {step_name}")
                
                try:
                    # ステップモジュールを動的読み込み
                    module = importlib.import_module(f"processors.{step_name}")
                    
                    # process関数を実行
                    if hasattr(module, 'process'):
                        result = module.process(pipeline_data)
                        pipeline_data['results'][step_name] = result
                        print(f"[{user_name}] 完了: {step_name}")
                    else:
                        print(f"[{user_name}] スキップ: {step_name} (process関数なし)")
                        
                except ImportError:
                    print(f"[{user_name}] スキップ: {step_name} (モジュールなし)")
                except Exception as e:
                    print(f"[{user_name}] エラー: {step_name} - {str(e)}")
                    # エラーが発生してもパイプラインは継続
                    
            else:
                print(f"[{user_name}] スキップ: {step_name} (設定により無効)")
        
        print(f"[{user_name}] パイプライン完了: {lv_value}")
        return 0
        
    except Exception as e:
        print(f"[{user_name}] パイプライン失敗: {str(e)}", file=sys.stderr)
        return 1

def main():
    """メイン関数"""
    if len(sys.argv) != 7:
        print("使用方法: python pipeline.py platform account_id platform_directory ncv_directory lv_value user_name", file=sys.stderr)
        return 1
    
    platform = sys.argv[1]
    account_id = sys.argv[2]
    platform_directory = sys.argv[3]
    ncv_directory = sys.argv[4]
    lv_value = sys.argv[5]
    user_name = sys.argv[6]
    
    return run_pipeline(platform, account_id, platform_directory, ncv_directory, lv_value, user_name)

if __name__ == "__main__":
    sys.exit(main())