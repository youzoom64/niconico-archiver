import tkinter as tk

class ConfigLoader:
    """設定読み込み処理"""
    
    def __init__(self, config_manager, config_vars, special_users_manager, widgets):
        self.config_manager = config_manager
        self.config_vars = config_vars
        self.special_users_manager = special_users_manager
        self.widgets = widgets
    
    def load_user_config(self, account_id):
        """ユーザー設定を読み込み"""
        try:
            config = self.config_manager.load_user_config(account_id)
            
            # 基本設定
            self._load_basic_settings(config)
            
            # API設定
            self._load_api_settings(config)
            
            # 音声処理設定
            self._load_audio_settings(config)
            
            # 音楽設定
            self._load_music_settings(config)
            
            # プロンプト設定
            self._load_prompt_settings(config)
            
            # キャラクター設定
            self._load_character_settings(config)
            
            # AI機能
            self._load_ai_features(config)
            
            # 表示機能
            self._load_display_features(config)
            
            # スペシャルユーザー
            self._load_special_users(config)
            
            # タグ
            self._load_tags(config)
            
            # スペシャルユーザー詳細設定
            self._load_special_users_detail(config)
            
            print(f"設定読み込み完了: {account_id}")
            return config
            
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
            return None
    
    def _load_basic_settings(self, config):
        """基本設定を読み込み"""
        self.config_vars.get('display_name_var').set(config.get("display_name", ""))
        self.config_vars.get('account_var').set(config["basic_settings"]["account_id"])
        self.config_vars.get('platform_var').set(config["basic_settings"]["platform"])
        self.config_vars.get('platform_dir_var').set(config["basic_settings"]["platform_directory"])
        self.config_vars.get('ncv_dir_var').set(config["basic_settings"]["ncv_directory"])
    
    def _load_api_settings(self, config):
        """API設定を読み込み"""
        api_settings = config.get("api_settings", {})
        old_ai_model = api_settings.get("ai_model", "openai-gpt4o")
        
        self.config_vars.get('summary_ai_model_var').set(
            api_settings.get("summary_ai_model", old_ai_model))
        self.config_vars.get('conversation_ai_model_var').set(
            api_settings.get("conversation_ai_model", old_ai_model))
        self.config_vars.get('openai_api_key_var').set(
            api_settings.get("openai_api_key", ""))
        self.config_vars.get('google_api_key_var').set(
            api_settings.get("google_api_key", ""))
        self.config_vars.get('suno_api_key_var').set(
            api_settings.get("suno_api_key", ""))
        self.config_vars.get('imgur_api_key_var').set(
            api_settings.get("imgur_api_key", ""))
    
    def _load_audio_settings(self, config):
        """音声処理設定を読み込み"""
        audio_settings = config.get("audio_settings", {})
        self.config_vars.get('use_gpu_var').set(audio_settings.get("use_gpu", True))
        self.config_vars.get('whisper_model_var').set(audio_settings.get("whisper_model", "large-v3"))
        self.config_vars.get('cpu_threads_var').set(audio_settings.get("cpu_threads", 8))
        self.config_vars.get('beam_size_var').set(audio_settings.get("beam_size", 5))
    
    def _load_music_settings(self, config):
        """音楽設定を読み込み"""
        music_settings = config.get("music_settings", {})
        self.config_vars.get('music_style_var').set(music_settings.get("style", "J-Pop, Upbeat"))
        self.config_vars.get('music_model_var').set(music_settings.get("model", "V4"))
        self.config_vars.get('music_instrumental_var').set(music_settings.get("instrumental", False))
    
    def _load_prompt_settings(self, config):
        """プロンプト設定を読み込み"""
        ai_prompts = config.get("ai_prompts", {})
        prompts = [
            ('summary_prompt_var', "summary_prompt", "以下の配信内容を日本語で要約してください:"),
            ('intro_conversation_prompt_var', "intro_conversation_prompt", "配信開始前の会話として、以下の内容について話し合います:"),
            ('outro_conversation_prompt_var', "outro_conversation_prompt", "配信終了後の振り返りとして、以下の内容について話し合います:"),
            ('image_prompt_var', "image_prompt", "この配信の抽象的なイメージを生成してください:")
        ]
        
        for var_key, config_key, default_value in prompts:
            self.config_vars.get(var_key).set(ai_prompts.get(config_key, default_value))
    
    def _load_character_settings(self, config):
        """キャラクター設定を読み込み"""
        ai_prompts = config.get("ai_prompts", {})
        character_settings = [
            ('character1_name_var', "character1_name", "ニニちゃん"),
            ('character1_personality_var', "character1_personality", "ボケ役で標準語を話す明るい女の子"),
            ('character1_image_url_var', "character1_image_url", ""),
            ('character1_image_flip_var', "character1_image_flip", False),
            ('character2_name_var', "character2_name", "ココちゃん"),
            ('character2_personality_var', "character2_personality", "ツッコミ役で関西弁を話すしっかり者の女の子"),
            ('character2_image_url_var', "character2_image_url", ""),
            ('character2_image_flip_var', "character2_image_flip", False),
            ('conversation_turns_var', "conversation_turns", 5)
        ]
        
        for var_key, config_key, default_value in character_settings:
            self.config_vars.get(var_key).set(ai_prompts.get(config_key, default_value))
    
    def _load_ai_features(self, config):
        """AI機能を読み込み"""
        ai_features = config.get("ai_features", {})
        features = [
            ('summary_text_var', "enable_summary_text", True),
            ('summary_image_var', "enable_summary_image", True),
            ('ai_music_var', "enable_ai_music", True),
            ('ai_conversation_var', "enable_ai_conversation", True)
        ]
        
        for var_key, config_key, default_value in features:
            self.config_vars.get(var_key).set(ai_features.get(config_key, default_value))
    
    def _load_display_features(self, config):
        """表示機能を読み込み"""
        display_features = config.get("display_features", {})
        features = [
            ('emotion_scores_var', "enable_emotion_scores", True),
            ('comment_ranking_var', "enable_comment_ranking", True),
            ('word_ranking_var', "enable_word_ranking", True),
            ('thumbnails_var', "enable_thumbnails", True),
            ('audio_player_var', "enable_audio_player", True),
            ('timeshift_jump_var', "enable_timeshift_jump", True)
        ]
        
        for var_key, config_key, default_value in features:
            self.config_vars.get(var_key).set(display_features.get(config_key, default_value))
    
    def _load_special_users(self, config):
        """スペシャルユーザーを読み込み"""
        special_users = config.get("special_users", [])
        self.config_vars.get('special_users_var').set(", ".join(special_users))
    
    def _load_tags(self, config):
        """タグを読み込み"""
        tags = config.get("tags", [])
        self.config_vars.get('tags_var').set(", ".join(tags))
        
        # タグリストを更新
        tags_listbox = self.widgets.get('tags_listbox')
        if tags_listbox:
            tags_listbox.delete(0, tk.END)
            for i, tag in enumerate(tags, 1):
                tags_listbox.insert(tk.END, f"{i}. {tag}")
    
    def _load_special_users_detail(self, config):
        """スペシャルユーザー詳細設定を読み込み"""
        special_users_config = config.get("special_users_config", {})
        
        self.config_vars.get('default_analysis_enabled_var').set(
            special_users_config.get("default_analysis_enabled", True))
        self.config_vars.get('default_analysis_ai_model_var').set(
            special_users_config.get("default_analysis_ai_model", "openai-gpt4o"))
        
        default_prompt = special_users_config.get("default_analysis_prompt", 
                                                 "以下のユーザーのコメント履歴を分析してください")
        default_prompt_text = self.config_vars.get('default_analysis_prompt_text')
        if default_prompt_text:
            default_prompt_text.delete(1.0, tk.END)
            default_prompt_text.insert(1.0, default_prompt)
        
        self.config_vars.get('default_template_var').set(
            special_users_config.get("default_template", "user_detail.html"))
        
        # TreeViewに詳細ユーザー設定を読み込み
        if self.special_users_manager:
            self.special_users_manager.load_special_users_tree(
                special_users_config.get("users", {}))