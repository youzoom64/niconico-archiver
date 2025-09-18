import tkinter as tk

class ConfigVarsManager:
    """設定変数の管理"""
    
    def __init__(self, fetch_nickname_callback=None):
        self.vars = {}
        self.fetch_nickname_callback = fetch_nickname_callback
        self.init_vars()
    
    def init_vars(self):
        """設定変数を初期化"""
        self.vars = {
            # 基本設定
            'display_name_var': tk.StringVar(),
            'account_var': tk.StringVar(),
            'platform_var': tk.StringVar(value="niconico"),
            'platform_dir_var': tk.StringVar(value="rec"),
            'ncv_dir_var': tk.StringVar(value="ncv"),
            
            # API設定
            'summary_ai_model_var': tk.StringVar(value="openai-gpt4o"),
            'conversation_ai_model_var': tk.StringVar(value="google-gemini-2.5-flash"),
            'openai_api_key_var': tk.StringVar(),
            'google_api_key_var': tk.StringVar(),
            'suno_api_key_var': tk.StringVar(),
            'imgur_api_key_var': tk.StringVar(),
            
            # 音声設定
            'use_gpu_var': tk.BooleanVar(value=True),
            'whisper_model_var': tk.StringVar(value="large-v3"),
            'cpu_threads_var': tk.IntVar(value=8),
            'beam_size_var': tk.IntVar(value=5),
            
            # 音楽設定
            'music_style_var': tk.StringVar(value="J-Pop, Upbeat"),
            'music_model_var': tk.StringVar(value="V4"),
            'music_instrumental_var': tk.BooleanVar(value=False),
            
            # プロンプト設定
            'summary_prompt_var': tk.StringVar(value="以下の配信内容を日本語で要約してください:"),
            'intro_conversation_prompt_var': tk.StringVar(value="配信開始前の会話として、以下の内容について話し合います:"),
            'outro_conversation_prompt_var': tk.StringVar(value="配信終了後の振り返りとして、以下の内容について話し合います:"),
            'image_prompt_var': tk.StringVar(value="この配信の抽象的なイメージを生成してください:"),
            
            # キャラクター設定
            'character1_name_var': tk.StringVar(value="ニニちゃん"),
            'character1_personality_var': tk.StringVar(value="ボケ役で標準語を話す明るい女の子"),
            'character1_image_url_var': tk.StringVar(),
            'character1_image_flip_var': tk.BooleanVar(value=False),
            'character2_name_var': tk.StringVar(value="ココちゃん"),
            'character2_personality_var': tk.StringVar(value="ツッコミ役で関西弁を話すしっかり者の女の子"),
            'character2_image_url_var': tk.StringVar(),
            'character2_image_flip_var': tk.BooleanVar(value=False),
            'conversation_turns_var': tk.IntVar(value=5),
            
            # AI機能
            'summary_text_var': tk.BooleanVar(value=True),
            'summary_image_var': tk.BooleanVar(value=True),
            'ai_music_var': tk.BooleanVar(value=True),
            'ai_conversation_var': tk.BooleanVar(value=True),
            
            # 表示機能
            'emotion_scores_var': tk.BooleanVar(value=True),
            'comment_ranking_var': tk.BooleanVar(value=True),
            'word_ranking_var': tk.BooleanVar(value=True),
            'thumbnails_var': tk.BooleanVar(value=True),
            'audio_player_var': tk.BooleanVar(value=True),
            'timeshift_jump_var': tk.BooleanVar(value=True),
            
            # スペシャルユーザー
            'special_users_var': tk.StringVar(),
            'default_analysis_enabled_var': tk.BooleanVar(value=True),
            'default_analysis_ai_model_var': tk.StringVar(value="openai-gpt4o"),
            'default_template_var': tk.StringVar(value="user_detail.html"),
            
            # タグ
            'tags_var': tk.StringVar(),
            
            # コールバック
            'fetch_nickname_callback': self.fetch_nickname_callback
        }
    
    def get(self, key):
        """変数を取得"""
        return self.vars.get(key)
    
    def get_all(self):
        """すべての変数を取得"""
        return self.vars
    
    def set_trace(self, key, callback):
        """変数の変更を監視"""
        if key in self.vars:
            self.vars[key].trace('w', callback)