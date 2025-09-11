import json
import os
from datetime import datetime

class ConfigManager:
    def __init__(self):
        # 絶対パスに変換
        self.config_dir = os.path.abspath("config")
        self.users_dir = os.path.join(self.config_dir, "users")
        self.current_users_file = os.path.join(self.config_dir, "current_users.json")
        self.ensure_directories()
    
    def ensure_directories(self):
        """必要なディレクトリを作成"""
        os.makedirs(self.users_dir, exist_ok=True)
        
        # デフォルト設定を作成
        if not os.path.exists(os.path.join(self.users_dir, "default.json")):
            self.create_default_config()
    
    def create_default_config(self):
        """デフォルト設定を作成"""
        default_config = {
            "account_id": "default",
            "display_name": "デフォルト設定",
            "basic_settings": {
                "platform": "niconico",
                "account_id": "default",
                "platform_directory": "rec",
                "ncv_directory": "ncv"
            },
            "audio_settings": {
                "use_gpu": True,
                "whisper_model": "large-v3",
                "cpu_threads": 8,
                "beam_size": 5
            },
            "api_settings": {
                "ai_model": "openai-gpt4o",
                "openai_api_key": "",
                "google_api_key": "",
                "suno_api_key": "",
                "imgur_api_key": ""
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
            "display_features": {
                "enable_emotion_scores": True,
                "enable_comment_ranking": True,
                "enable_word_ranking": True,
                "enable_thumbnails": True,
                "enable_audio_player": True,
                "enable_timeshift_jump": True
            },
            "special_users": [],
            "last_updated": datetime.now().isoformat()
        }
        self.save_user_config("default", default_config)
    
    def save_user_config(self, account_id, config):
        """ユーザー設定を保存（アカウントIDベース）"""
        config["last_updated"] = datetime.now().isoformat()
        config_path = os.path.join(self.users_dir, f"{account_id}.json")
        
        with open(config_path, 'w', encoding='utf-8') as f:
            json.dump(config, f, ensure_ascii=False, indent=2)
    
    def load_user_config(self, account_id):
        """ユーザー設定を読み込み（アカウントIDベース）"""
        config_path = os.path.join(self.users_dir, f"{account_id}.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    loaded_config = json.load(f)
                
                # デフォルト設定テンプレートを取得
                default_config = self.get_default_config_template()
                
                # 古い設定ファイルとの互換性を保つため、不足項目を補完
                merged_config = self._merge_config_deep(default_config, loaded_config)
                
                # special_users_configが存在しない場合は初期化
                if "special_users_config" not in merged_config:
                    merged_config["special_users_config"] = {
                        "default_analysis_enabled": True,
                        "default_analysis_ai_model": "openai-gpt4o",
                        "default_analysis_prompt": "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\n\n分析観点：\n- コメントの頻度と投稿タイミング\n- コメント内容の傾向（質問、感想、ツッコミなど）\n- 配信者との関係性\n- 他の視聴者との関わり\n- このユーザーの配信に対する貢献度\n- 特徴的な発言や行動パターン",
                        "default_template": "user_detail.html",
                        "users": {}
                    }
                
                # usersセクションが存在しない場合は初期化
                if "users" not in merged_config["special_users_config"]:
                    merged_config["special_users_config"]["users"] = {}
                
                # 各APIキーの存在チェックと初期化
                api_settings = merged_config.get("api_settings", {})
                if "summary_ai_model" not in api_settings:
                    api_settings["summary_ai_model"] = "openai-gpt4o"
                if "conversation_ai_model" not in api_settings:
                    api_settings["conversation_ai_model"] = "google-gemini-2.5-flash"
                
                # 音声設定の補完
                audio_settings = merged_config.get("audio_settings", {})
                if "use_gpu" not in audio_settings:
                    audio_settings["use_gpu"] = True
                if "whisper_model" not in audio_settings:
                    audio_settings["whisper_model"] = "large-v3"
                if "cpu_threads" not in audio_settings:
                    audio_settings["cpu_threads"] = 8
                if "beam_size" not in audio_settings:
                    audio_settings["beam_size"] = 5
                
                # キャラクター設定の補完
                ai_prompts = merged_config.get("ai_prompts", {})
                if "character1_image_url" not in ai_prompts:
                    ai_prompts["character1_image_url"] = ""
                if "character1_image_flip" not in ai_prompts:
                    ai_prompts["character1_image_flip"] = False
                if "character2_image_url" not in ai_prompts:
                    ai_prompts["character2_image_url"] = ""
                if "character2_image_flip" not in ai_prompts:
                    ai_prompts["character2_image_flip"] = False
                
                # tagsセクションの補完
                if "tags" not in merged_config:
                    merged_config["tags"] = []
                
                print(f"設定ファイル読み込み成功: {account_id}")
                return merged_config
                
            except json.JSONDecodeError as e:
                print(f"JSON読み込みエラー ({account_id}): {str(e)}")
                print(f"デフォルト設定で初期化します")
                return self.get_default_config_template()
            except Exception as e:
                print(f"設定ファイル読み込みエラー ({account_id}): {str(e)}")
                print(f"デフォルト設定で初期化します")
                return self.get_default_config_template()
        else:
            # 設定ファイルが存在しない場合
            if account_id == "default":
                # defaultファイルが存在しない場合は作成
                print(f"デフォルト設定ファイルが見つかりません。新規作成します。")
                default_config = self.get_default_config_template()
                self.save_user_config("default", default_config)
                return default_config
            else:
                # 他のアカウントの場合はdefaultをベースに作成
                print(f"設定ファイルが見つかりません: {account_id}")
                print(f"デフォルト設定をベースに初期化します")
                default_config = self.load_user_config("default")
                # アカウント固有の情報を更新
                default_config["account_id"] = account_id
                default_config["basic_settings"]["account_id"] = account_id
                default_config["display_name"] = ""
                return default_config

    def _merge_config_deep(self, default, loaded):
        """設定を深くマージして不足項目を補完"""
        result = default.copy()
        
        for key, value in loaded.items():
            if key in result:
                if isinstance(value, dict) and isinstance(result[key], dict):
                    # 辞書の場合は再帰的にマージ
                    result[key] = self._merge_config_deep(result[key], value)
                else:
                    # その他の場合は読み込んだ値で上書き
                    result[key] = value
            else:
                # 新しいキーの場合はそのまま追加
                result[key] = value
        
        return result
        
    def load_special_users_tree(self, users_config):
        """TreeViewにスペシャルユーザー設定を読み込み"""
        # 既存のアイテムをクリア
        for item in self.special_users_tree.get_children():
            self.special_users_tree.delete(item)
        
        # 新しいアイテムを追加
        for user_id, user_config in users_config.items():
            self.special_users_tree.insert("", tk.END, text=user_id,
                                        values=(user_config.get("display_name", ""),
                                                user_config.get("analysis_ai_model", "openai-gpt4o"),
                                                "有効" if user_config.get("analysis_enabled", True) else "無効",
                                                user_config.get("template", "user_detail.html")))
        
        print(f"詳細ユーザー設定読み込み: {len(users_config)}件")



    def get_default_config_template(self):
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
                "summary_ai_model": "openai-gpt4o",        # 追加
                "conversation_ai_model": "google-gemini-2.5-flash",  # 追加
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
                "character1_image_url": "",           # 追加
                "character1_image_flip": False,       # 追加
                "character2_name": "ココちゃん",
                "character2_personality": "ツッコミ役で関西弁を話すしっかり者の女の子",
                "character2_image_url": "",           # 追加
                "character2_image_flip": False,       # 追加
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
            "special_users": [],  # 後方互換性のため保持
            
            # スペシャルユーザー詳細設定を追加
            "special_users_config": {
                # グローバル設定（デフォルト値）
                "default_analysis_enabled": True,
                "default_analysis_ai_model": "openai-gpt4o",
                "default_analysis_prompt": "以下のユーザーのコメント履歴を分析して、このユーザーの特徴、傾向、配信との関わり方について詳しく分析してください。\n\n分析観点：\n- コメントの頻度と投稿タイミング\n- コメント内容の傾向（質問、感想、ツッコミなど）\n- 配信者との関係性\n- 他の視聴者との関わり\n- このユーザーの配信に対する貢献度\n- 特徴的な発言や行動パターン",
                "default_template": "user_detail.html",
                
                # 個別ユーザー設定
                "users": {
                    # 例：
                    # "12345": {
                    #     "user_id": "12345",
                    #     "display_name": "特別なユーザー",
                    #     "analysis_enabled": True,
                    #     "analysis_ai_model": "google-gemini-2.5-flash",
                    #     "analysis_prompt": "このユーザー専用の分析プロンプト...",
                    #     "template": "special_template.html",
                    #     "description": "このユーザーについてのメモ",
                    #     "tags": ["VIP", "古参"]
                    # }
                }
            }
        }
    
    def _merge_config(self, default, loaded):
        """設定をマージして不足項目を補完"""
        for key, value in loaded.items():
            if key in default:
                if isinstance(value, dict) and isinstance(default[key], dict):
                    self._merge_config(default[key], value)
                else:
                    default[key] = value
    
    def get_user_list(self):
        """ユーザーリストを取得（アカウントIDのリスト）"""
        if not os.path.exists(self.users_dir):
            return ["default"]
        
        account_ids = []
        for filename in os.listdir(self.users_dir):
            if filename.endswith('.json'):
                account_id = filename[:-5]  # .jsonを除去
                account_ids.append(account_id)
        
        return sorted(account_ids)
    
    def get_user_display_info(self):
        """ユーザー表示情報を取得（アカウントID + 表示名）"""
        user_info = []
        for account_id in self.get_user_list():
            config = self.load_user_config(account_id)
            display_name = config.get("display_name", "")
            platform = config["basic_settings"]["platform"]
            
            if display_name:
                label = f"{account_id} ({display_name})"
            else:
                label = account_id
            
            user_info.append({
                "account_id": account_id,
                "display_name": display_name,
                "platform": platform,
                "label": label
            })
        
        return user_info
    
    def delete_user(self, account_id):
        """ユーザー設定を削除"""
        if account_id == "default":
            return False
        
        config_path = os.path.join(self.users_dir, f"{account_id}.json")
        if os.path.exists(config_path):
            os.remove(config_path)
            return True
        return False
    
    def user_exists(self, account_id):
        """ユーザーが存在するかチェック"""
        config_path = os.path.join(self.users_dir, f"{account_id}.json")
        return os.path.exists(config_path)
    
    def save_current_users(self, active_users):
        """現在監視中のユーザーリストを保存"""
        data = {
            "active_users": active_users,
            "last_updated": datetime.now().isoformat()
        }
        
        with open(self.current_users_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    
    def load_current_users(self):
        """現在監視中のユーザーリストを読み込み"""
        if os.path.exists(self.current_users_file):
            with open(self.current_users_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                return data.get("active_users", [])
        return []
    
    def copy_user_config(self, source_account_id, target_account_id):
        """ユーザー設定を複製"""
        if self.user_exists(source_account_id) and not self.user_exists(target_account_id):
            config = self.load_user_config(source_account_id)
            config["account_id"] = target_account_id
            config["basic_settings"]["account_id"] = target_account_id
            self.save_user_config(target_account_id, config)
            return True
        return False