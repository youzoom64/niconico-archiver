import tkinter as tk
from tkinter import ttk
from .utils import UIUtils

class ConfigForms:
    """設定フォーム群の管理"""
    
    def __init__(self, parent_frame):
        self.parent = parent_frame
        self.vars = {}
        self.widgets = {}
    
    def create_basic_settings(self, config_vars):
        """基本設定セクションを作成"""
        basic_frame = tk.LabelFrame(self.parent, text="基本設定")
        basic_frame.pack(fill=tk.X, pady=5)
        
        # Account ID
        tk.Label(basic_frame, text="Account ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        account_entry = tk.Entry(basic_frame, textvariable=config_vars['account_var'])
        account_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        # ニックネーム取得ボタン
        tk.Button(basic_frame, text="ニックネーム取得",
                command=config_vars.get('fetch_nickname_callback')).grid(row=0, column=2, padx=5)
        
        # Platform
        tk.Label(basic_frame, text="Platform:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        platform_combo = ttk.Combobox(basic_frame, textvariable=config_vars['platform_var'],
                                    values=["niconico", "youtube", "twitch"])
        platform_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        # 監視Dir
        self._create_directory_setting(basic_frame, "監視Dir:", 2, 
                                     config_vars['platform_dir_var'])
        
        # NCVDir
        self._create_directory_setting(basic_frame, "NCVDir:", 3, 
                                     config_vars['ncv_dir_var'])
        
        basic_frame.columnconfigure(1, weight=1)
        return basic_frame
    
    def _create_directory_setting(self, parent, label, row, var):
        """ディレクトリ設定行を作成"""
        tk.Label(parent, text=label).grid(row=row, column=0, sticky=tk.W, padx=5, pady=2)
        dir_frame = tk.Frame(parent)
        dir_frame.grid(row=row, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
        
        tk.Entry(dir_frame, textvariable=var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(dir_frame, text="参照",
                command=lambda: UIUtils.browse_directory(parent, var)).pack(side=tk.RIGHT, padx=(5,0))
    
    def create_api_settings(self, config_vars):
        """API設定セクションを作成"""
        api_frame = tk.LabelFrame(self.parent, text="API設定")
        api_frame.pack(fill=tk.X, pady=5)
        
        # 要約AIモデル
        tk.Label(api_frame, text="要約AIモデル:").pack(anchor=tk.W)
        summary_model_combo = ttk.Combobox(api_frame, 
                                         textvariable=config_vars['summary_ai_model_var'],
                                         values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                         state="readonly", width=30)
        summary_model_combo.pack(fill=tk.X, padx=5, pady=2)
        
        # 会話AIモデル
        tk.Label(api_frame, text="会話AIモデル:").pack(anchor=tk.W, pady=(10, 0))
        conversation_model_combo = ttk.Combobox(api_frame,
                                              textvariable=config_vars['conversation_ai_model_var'],
                                              values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                              state="readonly", width=30)
        conversation_model_combo.pack(fill=tk.X, padx=5, pady=2)
        
        # APIキー入力フィールド
        api_keys = [
            ("OpenAI API Key:", config_vars['openai_api_key_var']),
            ("Google API Key:", config_vars['google_api_key_var']),
            ("Suno API Key:", config_vars['suno_api_key_var']),
            ("Imgur API Key:", config_vars['imgur_api_key_var'])
        ]
        
        for label, var in api_keys:
            tk.Label(api_frame, text=label).pack(anchor=tk.W, pady=(10, 0))
            tk.Entry(api_frame, textvariable=var, show="*", width=60).pack(fill=tk.X, padx=5, pady=2)
        
        return api_frame
    
    def create_audio_settings(self, config_vars):
        """音声処理設定セクションを作成"""
        audio_frame = tk.LabelFrame(self.parent, text="音声処理設定")
        audio_frame.pack(fill=tk.X, pady=5)
        
        # GPU使用設定
        tk.Checkbutton(audio_frame, text="GPU使用 (利用可能な場合)", 
                      variable=config_vars['use_gpu_var']).pack(anchor=tk.W)
        
        # Whisperモデル選択
        tk.Label(audio_frame, text="Whisperモデル:").pack(anchor=tk.W)
        model_combo = ttk.Combobox(audio_frame, textvariable=config_vars['whisper_model_var'],
                                 values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                                 state="readonly", width=30)
        model_combo.pack(anchor=tk.W, padx=5, pady=2)
        
        # CPUスレッド数
        tk.Label(audio_frame, text="CPUスレッド数:").pack(anchor=tk.W, pady=(10, 0))
        cpu_spin = tk.Spinbox(audio_frame, from_=1, to=32, 
                             textvariable=config_vars['cpu_threads_var'], width=10)
        cpu_spin.pack(anchor=tk.W, padx=5, pady=2)
        
        # ビームサイズ
        tk.Label(audio_frame, text="ビームサイズ (GPU用):").pack(anchor=tk.W, pady=(10, 0))
        beam_spin = tk.Spinbox(audio_frame, from_=1, to=10, 
                              textvariable=config_vars['beam_size_var'], width=10)
        beam_spin.pack(anchor=tk.W, padx=5, pady=2)
        
        return audio_frame