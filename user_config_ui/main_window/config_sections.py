import tkinter as tk
from tkinter import ttk

class ConfigSectionsManager:
    """設定セクション群の管理"""
    
    def __init__(self, parent_frame, config_vars):
        self.parent = parent_frame
        self.config_vars = config_vars
        self.widgets = {}
    
    def create_display_name_section(self):
        """表示名セクション"""
        name_frame = tk.Frame(self.parent)
        name_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(name_frame, text="表示名:").pack(side=tk.LEFT)
        tk.Entry(name_frame, textvariable=self.config_vars.get('display_name_var')).pack(
            side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
    
    def create_music_settings(self):
        """音楽設定セクション"""
        music_frame = tk.LabelFrame(self.parent, text="音楽生成設定")
        music_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(music_frame, text="音楽スタイル:").pack(anchor=tk.W, pady=(5, 0))
        tk.Entry(music_frame, textvariable=self.config_vars.get('music_style_var'), 
                width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(music_frame, text="モデル:").pack(anchor=tk.W, pady=(10, 0))
        music_model_combo = ttk.Combobox(music_frame, 
                                        textvariable=self.config_vars.get('music_model_var'),
                                        values=["V4", "V3"], state="readonly", width=20)
        music_model_combo.pack(anchor=tk.W, padx=5, pady=2)
        
        tk.Checkbutton(music_frame, text="インストゥルメンタル（歌なし）", 
                      variable=self.config_vars.get('music_instrumental_var')).pack(
                          anchor=tk.W, padx=5, pady=5)
    
    def create_prompt_settings(self):
        """プロンプト設定セクション"""
        prompt_frame = tk.LabelFrame(self.parent, text="AIプロンプト設定")
        prompt_frame.pack(fill=tk.X, pady=5)
        
        prompts = [
            ("要約プロンプト:", 'summary_prompt_var'),
            ("放送前会話プロンプト:", 'intro_conversation_prompt_var'),
            ("放送後会話プロンプト:", 'outro_conversation_prompt_var'),
            ("画像プロンプト:", 'image_prompt_var')
        ]
        
        for label, var_key in prompts:
            tk.Label(prompt_frame, text=label).pack(anchor=tk.W)
            tk.Entry(prompt_frame, textvariable=self.config_vars.get(var_key), 
                    width=60).pack(fill=tk.X, padx=5, pady=2)
    
    def create_character_settings(self):
        """キャラクター設定セクション"""
        character_frame = tk.LabelFrame(self.parent, text="AI会話キャラクター設定")
        character_frame.pack(fill=tk.X, pady=5)
        
        self._create_character_group(character_frame, "1", [
            ("キャラクター1名前:", 'character1_name_var'),
            ("キャラクター1性格:", 'character1_personality_var'),
            ("キャラクター1画像URL:", 'character1_image_url_var')
        ], 'character1_image_flip_var')
        
        # 区切り線
        tk.Frame(character_frame, height=2, bg="gray").pack(fill=tk.X, padx=5, pady=10)
        
        self._create_character_group(character_frame, "2", [
            ("キャラクター2名前:", 'character2_name_var'),
            ("キャラクター2性格:", 'character2_personality_var'),
            ("キャラクター2画像URL:", 'character2_image_url_var')
        ], 'character2_image_flip_var')
        
        # 会話設定
        tk.Label(character_frame, text="会話往復数:").pack(anchor=tk.W, pady=(10, 0))
        tk.Spinbox(character_frame, from_=3, to=10, 
                  textvariable=self.config_vars.get('conversation_turns_var'), 
                  width=10).pack(anchor=tk.W, padx=5, pady=2)
    
    def _create_character_group(self, parent, char_num, fields, flip_var_key):
        """キャラクター設定グループを作成"""
        for label, var_key in fields:
            tk.Label(parent, text=label).pack(anchor=tk.W)
            tk.Entry(parent, textvariable=self.config_vars.get(var_key), 
                    width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Checkbutton(parent, text=f"キャラクター{char_num}画像を左右反転", 
                      variable=self.config_vars.get(flip_var_key)).pack(anchor=tk.W, padx=5)
    
    def create_ai_features(self):
        """AI生成機能セクション"""
        ai_frame = tk.LabelFrame(self.parent, text="AI生成機能")
        ai_frame.pack(fill=tk.X, pady=5)
        
        features = [
            ("要約テキスト生成", 'summary_text_var'),
            ("抽象イメージ生成", 'summary_image_var'),
            ("AI音楽生成", 'ai_music_var'),
            ("AI会話生成", 'ai_conversation_var')
        ]
        
        for text, var_key in features:
            tk.Checkbutton(ai_frame, text=text, 
                          variable=self.config_vars.get(var_key)).pack(anchor=tk.W)
    
    def create_display_features(self):
        """表示機能セクション"""
        display_frame = tk.LabelFrame(self.parent, text="表示機能")
        display_frame.pack(fill=tk.X, pady=5)
        
        features = [
            ("感情スコア表示", 'emotion_scores_var'),
            ("コメントランキング", 'comment_ranking_var'),
            ("単語ランキング", 'word_ranking_var'),
            ("サムネイル表示", 'thumbnails_var'),
            ("音声プレイヤー", 'audio_player_var'),
            ("タイムシフトジャンプ", 'timeshift_jump_var')
        ]
        
        for text, var_key in features:
            tk.Checkbutton(display_frame, text=text, 
                          variable=self.config_vars.get(var_key)).pack(anchor=tk.W)
    
    def create_tag_settings(self):
        """タグ設定セクション"""
        tag_frame = tk.LabelFrame(self.parent, text="タグ設定")
        tag_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(tag_frame, text="タグ (カンマ区切り):").pack(anchor=tk.W)
        tk.Entry(tag_frame, textvariable=self.config_vars.get('tags_var'), 
                width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(tag_frame, text="登録済みタグ:").pack(anchor=tk.W, pady=(10, 0))
        self.widgets['tags_listbox'] = tk.Listbox(tag_frame, height=4)
        self.widgets['tags_listbox'].pack(fill=tk.X, padx=5, pady=2)
    
    def get_widget(self, name):
        """ウィジェットを取得"""
        return self.widgets.get(name)