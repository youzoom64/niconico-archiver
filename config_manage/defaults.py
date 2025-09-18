from datetime import datetime

class DefaultConfigProvider:
    @staticmethod
    def get_template():
        """デフォルト設定テンプレートを取得"""
        return {
            "account_id": "",
            "display_name": "",
            "basic_settings": {
                "platform": "niconico",
                "account_id": "",
                "platform_directory": "rec",
                "ncv_directory": "ncv"
            },
            "api_settings": {
                "summary_ai_model": "openai-gpt4o",
                "conversation_ai_model": "google-gemini-2.5-flash",
                "ai_model": "openai-gpt4o",
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
            "music_settings": {
                "style": "J-Pop, Upbeat",
                "model": "V4",
                "instrumental": False
            },
            "ai_features": {
                "enable_summary_text": True,
                "enable_summary_image": True,
                "enable_ai_music": True,
                "enable_ai_conversation": True
            },
            "ai_prompts": {
                "summary_prompt": "以下の配信内容を日本語で要約してください:",
                "intro_conversation_prompt": "配信開始前の会話として、以下の内容について話し合います:",
                "outro_conversation_prompt": "配信終了後の振り返りとして、以下の内容について話し合います:",
                "image_prompt": "この配信の抽象的なイメージを生成してください:",
                "character1_name": "ニニちゃん",
                "character1_personality": "ボケ役で標準語を話す明るい女の子",
                "character1_image_url": "",
                "character1_image_flip": False,
                "character2_name": "ココちゃん",
                "character2_personality": "ツッコミ役で関西弁を話すしっかり者の女の子",
                "character2_image_url": "",
                "character2_image_flip": False,
                "conversation_turns": 5
            },
            "tags": [],
            "display_features": {
                "enable_emotion_scores": True,
                "enable_comment_ranking": True,
                "enable_word_ranking": True,
                "enable_thumbnails": True,
                "enable_audio_player": True,
                "enable_timeshift_jump": True
            },
            "special_users": [],
            "special_users_config": {
                "default_analysis_enabled": True,
                "default_analysis_ai_model": "openai-gpt4o",
                "default_analysis_prompt": "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\n\n分析観点：\n- コメントの頻度と投稿タイミング\n- コメント内容の傾向（質問、感想、ツッコミなど）\n- 配信者との関係性\n- 他の視聴者との関わり\n- このユーザーの配信に対する貢献度\n- 特徴的な発言や行動パターン",
                "default_template": "user_detail.html",
                "users": {}
            },
            # 引数設定を追加
            "arguments_config": {
                "enabled_arguments": {
                    "type": {
                        "required": True,
                        "choices": ["user", "video", "data", "config"],
                        "help": "処理タイプを指定"
                    },
                    "name": {
                        "required": False,
                        "type": "str",
                        "help": "名前を指定"
                    },
                    "email": {
                        "required": False,
                        "type": "str",
                        "help": "メールアドレスを指定"
                    },
                    "age": {
                        "required": False,
                        "type": "int",
                        "help": "年齢を指定"
                    },
                    "output": {
                        "required": False,
                        "choices": ["json", "csv", "db"],
                        "default": "json",
                        "help": "出力形式"
                    }
                }
            }
        }