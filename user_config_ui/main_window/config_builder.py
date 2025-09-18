class ConfigBuilder:
    """設定データの構築処理"""
    
    def __init__(self, config_vars, special_users_manager):
        self.config_vars = config_vars
        self.special_users_manager = special_users_manager
    
    def build_config(self):
        """現在の設定からconfigオブジェクトを構築"""
        return {
            "account_id": self.config_vars['account_var'].get(),
            "display_name": self.config_vars['display_name_var'].get(),
            "basic_settings": self._build_basic_settings(),
            "api_settings": self._build_api_settings(),
            "audio_settings": self._build_audio_settings(),
            "music_settings": self._build_music_settings(),
            "ai_features": self._build_ai_features(),
            "ai_prompts": self._build_ai_prompts(),
            "display_features": self._build_display_features(),
            "special_users": self._build_special_users(),
            "tags": self._build_tags(),
            "special_users_config": self._build_special_users_config()
        }
    
    def _build_basic_settings(self):
        """基本設定を構築"""
        return {
            "platform": self.config_vars['platform_var'].get(),
            "account_id": self.config_vars['account_var'].get(),
            "platform_directory": self.config_vars['platform_dir_var'].get(),
            "ncv_directory": self.config_vars['ncv_dir_var'].get()
        }
    
    def _build_api_settings(self):
        """API設定を構築"""
        return {
            "summary_ai_model": self.config_vars['summary_ai_model_var'].get(),
            "conversation_ai_model": self.config_vars['conversation_ai_model_var'].get(),
            "openai_api_key": self.config_vars['openai_api_key_var'].get(),
            "google_api_key": self.config_vars['google_api_key_var'].get(),
            "suno_api_key": self.config_vars['suno_api_key_var'].get(),
            "imgur_api_key": self.config_vars['imgur_api_key_var'].get()
        }
    
    def _build_audio_settings(self):
        """音声設定を構築"""
        return {
            "use_gpu": self.config_vars['use_gpu_var'].get(),
            "whisper_model": self.config_vars['whisper_model_var'].get(),
            "cpu_threads": self.config_vars['cpu_threads_var'].get(),
            "beam_size": self.config_vars['beam_size_var'].get()
        }
    
    def _build_music_settings(self):
        """音楽設定を構築"""
        return {
            "style": self.config_vars['music_style_var'].get(),
            "model": self.config_vars['music_model_var'].get(),
            "instrumental": self.config_vars['music_instrumental_var'].get()
        }
    
    def _build_ai_features(self):
        """AI機能設定を構築"""
        return {
            "enable_summary_text": self.config_vars['summary_text_var'].get(),
            "enable_summary_image": self.config_vars['summary_image_var'].get(),
            "enable_ai_music": self.config_vars['ai_music_var'].get(),
            "enable_ai_conversation": self.config_vars['ai_conversation_var'].get()
        }
    
    def _build_ai_prompts(self):
        """AIプロンプト設定を構築"""
        return {
            "summary_prompt": self.config_vars['summary_prompt_var'].get(),
            "intro_conversation_prompt": self.config_vars['intro_conversation_prompt_var'].get(),
            "outro_conversation_prompt": self.config_vars['outro_conversation_prompt_var'].get(),
            "image_prompt": self.config_vars['image_prompt_var'].get(),
            "character1_name": self.config_vars['character1_name_var'].get(),
            "character1_personality": self.config_vars['character1_personality_var'].get(),
            "character1_image_url": self.config_vars['character1_image_url_var'].get(),
            "character1_image_flip": self.config_vars['character1_image_flip_var'].get(),
            "character2_name": self.config_vars['character2_name_var'].get(),
            "character2_personality": self.config_vars['character2_personality_var'].get(),
            "character2_image_url": self.config_vars['character2_image_url_var'].get(),
            "character2_image_flip": self.config_vars['character2_image_flip_var'].get(),
            "conversation_turns": self.config_vars['conversation_turns_var'].get()
        }
    
    def _build_display_features(self):
        """表示機能設定を構築"""
        return {
            "enable_emotion_scores": self.config_vars['emotion_scores_var'].get(),
            "enable_comment_ranking": self.config_vars['comment_ranking_var'].get(),
            "enable_word_ranking": self.config_vars['word_ranking_var'].get(),
            "enable_thumbnails": self.config_vars['thumbnails_var'].get(),
            "enable_audio_player": self.config_vars['audio_player_var'].get(),
            "enable_timeshift_jump": self.config_vars['timeshift_jump_var'].get()
        }
    
    def _build_special_users(self):
        """スペシャルユーザーリストを構築"""
        users_text = self.config_vars['special_users_var'].get()
        return [user.strip() for user in users_text.split(",") if user.strip()]
    
    def _build_tags(self):
        """タグリストを構築"""
        tags_text = self.config_vars['tags_var'].get()
        return [tag.strip() for tag in tags_text.split(",") if tag.strip()]
    
    def _build_special_users_config(self):
        """スペシャルユーザー詳細設定を構築"""
        return {
            "default_analysis_enabled": self.config_vars['default_analysis_enabled_var'].get(),
            "default_analysis_ai_model": self.config_vars['default_analysis_ai_model_var'].get(),
            "default_analysis_prompt": self._get_default_analysis_prompt(),
            "default_template": self.config_vars['default_template_var'].get(),
            "users": self.special_users_manager.get_special_users_from_tree()
        }
    
    def _get_default_analysis_prompt(self):
        """デフォルト分析プロンプトを取得"""
        prompt_text_widget = self.config_vars.get('default_analysis_prompt_text')
        if prompt_text_widget:
            return prompt_text_widget.get(1.0, "end-1c").strip()
        return ""