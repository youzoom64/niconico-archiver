import argparse
import json
import os
from datetime import datetime
import logging

# ログ設定
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
DEBUGLOG = logging.getLogger(__name__)

def create_user_config():
    """コマンドライン引数からユーザー設定JSONを生成"""
    
    # 引数パース
    parser = argparse.ArgumentParser(description='ユーザー設定JSON自動生成')
    parser.add_argument('-lv_no', required=True, help='放送ID')
    parser.add_argument('-account_id', required=True, help='アカウントID')
    parser.add_argument('-lv_title', required=True, help='放送タイトル')
    parser.add_argument('-display_name', required=True, help='表示名')
    parser.add_argument('-tab_id', required=True, help='タブID')
    parser.add_argument('-start_time', required=True, help='開始時刻')
    
    args = parser.parse_args()
    
    DEBUGLOG.info(f"ユーザー設定生成開始: account_id={args.account_id}, display_name={args.display_name}")
    
    # config/usersディレクトリ作成
    config_dir = os.path.join('config', 'users')
    os.makedirs(config_dir, exist_ok=True)
    
    # JSONファイルパス
    json_path = os.path.join(config_dir, f'{args.account_id}.json')
    
    # 既存ファイルチェック
    if os.path.exists(json_path):
        DEBUGLOG.info(f"ユーザー設定が既に存在: {json_path}")
        return json_path
    
    # デフォルト設定テンプレート
    user_config = {
        "account_id": args.account_id,
        "display_name": args.display_name,
        "basic_settings": {
            "platform": "niconico",
            "account_id": args.account_id,
            "platform_directory": "C:\\project_root\\app_workspaces\\niconico-archiver\\rec",
            "ncv_directory": "C:\\Users\\youzo\\AppData\\Roaming\\posite-c\\NiconamaCommentViewer\\CommentLog",
            "download_directory": "C:\\Users\\youzo\\Downloads"
        },
        "api_settings": {
            "summary_ai_model": "",
            "conversation_ai_model": "",
            "openai_api_key": "",
            "google_api_key": "",
            "suno_api_key": "",
            "imgur_api_key": ""
        },
        "audio_settings": {
            "use_gpu": True,
            "whisper_model": "large-v3",
            "cpu_threads": 8,
            "beam_size": 5
        },
        "ai_features": {
            "enable_summary_text": False,
            "enable_summary_image": False,
            "enable_ai_music": False,
            "enable_ai_conversation": False
        },
        "music_settings": {
            "style": "",
            "model": "V4",
            "instrumental": False
        },
        "ai_prompts": {
            "summary_prompt": "",
            "intro_conversation_prompt": "",
            "outro_conversation_prompt": "",
            "image_prompt": "",
            "character1_name": "",
            "character1_personality": "",
            "character1_image_url": "",
            "character1_image_flip": True,
            "character2_name": "",
            "character2_personality": "",
            "character2_image_url": "",
            "character2_image_flip": False,
            "conversation_turns": 3
        },
        "display_features": {
            "enable_emotion_scores": False,
            "enable_comment_ranking": False,
            "enable_word_ranking": False,
            "enable_thumbnails": False,
            "enable_audio_player": False,
            "enable_timeshift_jump": False
        },
        "special_users": [],
        "tags": [],
        "special_users_config": {
            "default_analysis_enabled": False,
            "default_analysis_ai_model": "",
            "default_analysis_prompt": "",
            "default_template": "user_detail.html",
            "users": {}
        },
        "last_updated": datetime.now().isoformat()
    }
    
    # JSONファイル書き込み
    try:
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(user_config, f, ensure_ascii=False, indent=2)
        DEBUGLOG.info(f"ユーザー設定生成完了: {json_path}")
        return json_path
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定生成失敗: {e}")
        raise

if __name__ == "__main__":
    try:
        config_path = create_user_config()
        print(f"ユーザー設定ファイルを生成しました: {config_path}")
    except Exception as e:
        print(f"エラー: {e}")
        exit(1)