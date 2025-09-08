import tkinter as tk
from tkinter import ttk, messagebox
import json
import tkinter.simpledialog

class UserConfigWindow:
    def __init__(self, parent, config_manager, refresh_callback):
        self.config_manager = config_manager
        self.refresh_callback = refresh_callback
        
        self.window = tk.Toplevel(parent)
        self.window.title("ユーザー設定管理")
        self.window.geometry("900x700")
        self.window.grab_set()
        
        self.current_config = None
        self.setup_ui()
        self.load_users()
        
    def setup_ui(self):
        main_frame = tk.Frame(self.window)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # 左側: ユーザー一覧
        left_frame = tk.Frame(main_frame)
        left_frame.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 10))
        
        tk.Label(left_frame, text="アカウント一覧", font=("", 12, "bold")).pack()
        
        self.user_listbox = tk.Listbox(left_frame, width=25)
        self.user_listbox.pack(fill=tk.Y, expand=True, pady=5)
        self.user_listbox.bind("<<ListboxSelect>>", self.on_user_select)
        
        btn_frame = tk.Frame(left_frame)
        btn_frame.pack(fill=tk.X, pady=5)
        
        tk.Button(btn_frame, text="新規作成", command=self.create_user).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="複製", command=self.copy_user).pack(fill=tk.X, pady=2)
        tk.Button(btn_frame, text="削除", command=self.delete_user).pack(fill=tk.X, pady=2)
        
        # 右側: 設定詳細（スクロール可能）
        right_frame = tk.Frame(main_frame)
        right_frame.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True)
        
        # スクロールバー付きキャンバス
        canvas = tk.Canvas(right_frame)
        scrollbar = ttk.Scrollbar(right_frame, orient="vertical", command=canvas.yview)
        scrollable_frame = tk.Frame(canvas)
        
        scrollable_frame.bind(
            "<Configure>",
            lambda e: canvas.configure(scrollregion=canvas.bbox("all"))
        )
        
        canvas.create_window((0, 0), window=scrollable_frame, anchor="nw")
        canvas.configure(yscrollcommand=scrollbar.set)
        
        # マウスホイール対応
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)
        
        canvas.pack(side="left", fill="both", expand=True)
        scrollbar.pack(side="right", fill="y")
        
        # 設定項目を配置
        tk.Label(scrollable_frame, text="設定詳細", font=("", 12, "bold")).pack()
        
        # 表示名
        name_frame = tk.Frame(scrollable_frame)
        name_frame.pack(fill=tk.X, pady=5)
        tk.Label(name_frame, text="表示名:").pack(side=tk.LEFT)
        self.display_name_var = tk.StringVar()
        tk.Entry(name_frame, textvariable=self.display_name_var).pack(side=tk.RIGHT, fill=tk.X, expand=True, padx=(10, 0))
        
        # 基本設定
        basic_frame = tk.LabelFrame(scrollable_frame, text="基本設定")
        basic_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(basic_frame, text="Account ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.account_var = tk.StringVar()
        tk.Entry(basic_frame, textvariable=self.account_var).grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        tk.Label(basic_frame, text="Platform:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.platform_var = tk.StringVar(value="niconico")
        platform_combo = ttk.Combobox(basic_frame, textvariable=self.platform_var, 
                                     values=["niconico", "youtube", "twitch"])
        platform_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        tk.Label(basic_frame, text="監視Dir:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        self.platform_dir_var = tk.StringVar(value="rec")
        tk.Entry(basic_frame, textvariable=self.platform_dir_var).grid(row=2, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        tk.Label(basic_frame, text="NCVDir:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        self.ncv_dir_var = tk.StringVar(value="ncv")
        tk.Entry(basic_frame, textvariable=self.ncv_dir_var).grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        basic_frame.columnconfigure(1, weight=1)
        
        # API設定
        api_frame = tk.LabelFrame(scrollable_frame, text="API設定")
        api_frame.pack(fill=tk.X, pady=5)

        # AIモデル選択
        tk.Label(api_frame, text="要約AIモデル:").pack(anchor=tk.W)
        self.ai_model_var = tk.StringVar(value="openai-gpt4o")
        model_frame = tk.Frame(api_frame)
        model_frame.pack(fill=tk.X, padx=5, pady=2)

        model_combo = ttk.Combobox(model_frame, textvariable=self.ai_model_var, 
                                values=["openai-gpt4o", "google-gemini-2.5-flash"], 
                                state="readonly", width=30)
        model_combo.pack(side=tk.LEFT)

        # OpenAI API Key
        tk.Label(api_frame, text="OpenAI API Key:").pack(anchor=tk.W, pady=(10, 0))
        self.openai_api_key_var = tk.StringVar()
        tk.Entry(api_frame, textvariable=self.openai_api_key_var, show="*", width=60).pack(fill=tk.X, padx=5, pady=2)

        # Google API Key
        tk.Label(api_frame, text="Google API Key:").pack(anchor=tk.W, pady=(10, 0))
        self.google_api_key_var = tk.StringVar()
        tk.Entry(api_frame, textvariable=self.google_api_key_var, show="*", width=60).pack(fill=tk.X, padx=5, pady=2)

        # Suno API Key
        tk.Label(api_frame, text="Suno API Key:").pack(anchor=tk.W, pady=(10, 0))
        self.suno_api_key_var = tk.StringVar()
        tk.Entry(api_frame, textvariable=self.suno_api_key_var, show="*", width=60).pack(fill=tk.X, padx=5, pady=2)

        # Imgur API Key
        tk.Label(api_frame, text="Imgur API Key:").pack(anchor=tk.W, pady=(10, 0))
        self.imgur_api_key_var = tk.StringVar()
        tk.Entry(api_frame, textvariable=self.imgur_api_key_var, show="*", width=60).pack(fill=tk.X, padx=5, pady=2)

        # 音声処理設定セクションを追加
        audio_frame = tk.LabelFrame(scrollable_frame, text="音声処理設定")
        audio_frame.pack(fill=tk.X, pady=5)

        # GPU使用設定
        self.use_gpu_var = tk.BooleanVar(value=True)
        tk.Checkbutton(audio_frame, text="GPU使用 (利用可能な場合)", variable=self.use_gpu_var).pack(anchor=tk.W)

        # Whisperモデル選択
        tk.Label(audio_frame, text="Whisperモデル:").pack(anchor=tk.W)
        self.whisper_model_var = tk.StringVar(value="large")
        model_combo = ttk.Combobox(audio_frame, textvariable=self.whisper_model_var,
                                values=["tiny", "base", "small", "medium", "large", "large-v2", "large-v3"],
                                state="readonly", width=30)
        model_combo.pack(anchor=tk.W, padx=5, pady=2)

        # CPUスレッド数設定を追加
        tk.Label(audio_frame, text="CPUスレッド数:").pack(anchor=tk.W, pady=(10, 0))
        self.cpu_threads_var = tk.IntVar(value=8)
        cpu_spin = tk.Spinbox(audio_frame, from_=1, to=32, textvariable=self.cpu_threads_var, width=10)
        cpu_spin.pack(anchor=tk.W, padx=5, pady=2)

        # ビームサイズ設定を追加
        tk.Label(audio_frame, text="ビームサイズ (GPU用):").pack(anchor=tk.W, pady=(10, 0))
        self.beam_size_var = tk.IntVar(value=5)
        beam_spin = tk.Spinbox(audio_frame, from_=1, to=10, textvariable=self.beam_size_var, width=10)
        beam_spin.pack(anchor=tk.W, padx=5, pady=2)


        # プロンプト設定
        prompt_frame = tk.LabelFrame(scrollable_frame, text="AIプロンプト設定")
        prompt_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(prompt_frame, text="要約プロンプト:").pack(anchor=tk.W)
        self.summary_prompt_var = tk.StringVar(value="以下の配信内容を日本語で要約してください:")
        tk.Entry(prompt_frame, textvariable=self.summary_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="放送前会話プロンプト:").pack(anchor=tk.W)
        self.intro_conversation_prompt_var = tk.StringVar(value="配信開始前の会話として、以下の内容について2人のAIが話します:")
        tk.Entry(prompt_frame, textvariable=self.intro_conversation_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="放送後会話プロンプト:").pack(anchor=tk.W)
        self.outro_conversation_prompt_var = tk.StringVar(value="配信終了後の振り返りとして、以下の内容について2人のAIが話します:")
        tk.Entry(prompt_frame, textvariable=self.outro_conversation_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="画像プロンプト:").pack(anchor=tk.W)
        self.image_prompt_var = tk.StringVar(value="この配信の抽象的なイメージを生成してください:")
        tk.Entry(prompt_frame, textvariable=self.image_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        # AI生成機能
        ai_frame = tk.LabelFrame(scrollable_frame, text="AI生成機能")
        ai_frame.pack(fill=tk.X, pady=5)
        
        self.summary_text_var = tk.BooleanVar(value=True)
        self.summary_image_var = tk.BooleanVar(value=True)
        self.ai_music_var = tk.BooleanVar(value=True)
        self.ai_conversation_var = tk.BooleanVar(value=True)
        
        tk.Checkbutton(ai_frame, text="要約テキスト生成", variable=self.summary_text_var).pack(anchor=tk.W)
        tk.Checkbutton(ai_frame, text="抽象イメージ生成", variable=self.summary_image_var).pack(anchor=tk.W)
        tk.Checkbutton(ai_frame, text="AI音楽生成", variable=self.ai_music_var).pack(anchor=tk.W)
        tk.Checkbutton(ai_frame, text="AI会話生成", variable=self.ai_conversation_var).pack(anchor=tk.W)
        
        # 表示機能
        display_frame = tk.LabelFrame(scrollable_frame, text="表示機能")
        display_frame.pack(fill=tk.X, pady=5)

        self.emotion_scores_var = tk.BooleanVar(value=True)
        self.comment_ranking_var = tk.BooleanVar(value=True)
        self.word_ranking_var = tk.BooleanVar(value=True)
        self.thumbnails_var = tk.BooleanVar(value=True)
        self.audio_player_var = tk.BooleanVar(value=True)
        self.timeshift_jump_var = tk.BooleanVar(value=True)

        tk.Checkbutton(display_frame, text="感情スコア表示", variable=self.emotion_scores_var).pack(anchor=tk.W)
        tk.Checkbutton(display_frame, text="コメントランキング", variable=self.comment_ranking_var).pack(anchor=tk.W)
        tk.Checkbutton(display_frame, text="単語ランキング", variable=self.word_ranking_var).pack(anchor=tk.W)
        tk.Checkbutton(display_frame, text="サムネイル表示", variable=self.thumbnails_var).pack(anchor=tk.W)
        tk.Checkbutton(display_frame, text="音声プレイヤー", variable=self.audio_player_var).pack(anchor=tk.W)
        tk.Checkbutton(display_frame, text="タイムシフトジャンプ", variable=self.timeshift_jump_var).pack(anchor=tk.W)  


        # スペシャルユーザー設定
        special_frame = tk.LabelFrame(scrollable_frame, text="スペシャルユーザー設定")
        special_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(special_frame, text="特別処理対象ユーザーID (カンマ区切り):").pack(anchor=tk.W)
        self.special_users_var = tk.StringVar()
        tk.Entry(special_frame, textvariable=self.special_users_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        # スペシャルユーザー一覧表示
        tk.Label(special_frame, text="登録済みスペシャルユーザー:").pack(anchor=tk.W, pady=(10, 0))
        self.special_users_listbox = tk.Listbox(special_frame, height=4)
        self.special_users_listbox.pack(fill=tk.X, padx=5, pady=2)
        
        # 保存・キャンセルボタン
        button_frame = tk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="適用", command=self.apply_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        
    def load_users(self):
        user_info = self.config_manager.get_user_display_info()
        self.user_listbox.delete(0, tk.END)
        for info in user_info:
            self.user_listbox.insert(tk.END, info["label"])
            
    def on_user_select(self, event):
        selection = self.user_listbox.curselection()
        if selection:
            # 選択された表示ラベルからアカウントIDを抽出
            selected_label = self.user_listbox.get(selection[0])
            account_id = selected_label.split(" ")[0]  # "12345 (表示名)" から "12345" を抽出
            self.load_user_config(account_id)
            
    def load_user_config(self, account_id):
        try:
            config = self.config_manager.load_user_config(account_id)
            self.current_config = config
            self.current_account_id = account_id
            
            # 基本設定
            self.display_name_var.set(config.get("display_name", ""))
            self.account_var.set(config["basic_settings"]["account_id"])
            self.platform_var.set(config["basic_settings"]["platform"])
            self.platform_dir_var.set(config["basic_settings"]["platform_directory"])
            self.ncv_dir_var.set(config["basic_settings"]["ncv_directory"])
            
            # API設定
            api_settings = config.get("api_settings", {})
            self.ai_model_var.set(config["api_settings"].get("ai_model", "openai-gpt4o"))
            self.openai_api_key_var.set(config["api_settings"].get("openai_api_key", ""))
            self.google_api_key_var.set(config["api_settings"].get("google_api_key", ""))
            self.suno_api_key_var.set(config["api_settings"].get("suno_api_key", ""))
            self.imgur_api_key_var.set(config["api_settings"].get("imgur_api_key", ""))  # 追加
            
            # 音声処理設定
            audio_settings = config.get("audio_settings", {})
            self.use_gpu_var.set(audio_settings.get("use_gpu", True))
            self.whisper_model_var.set(audio_settings.get("whisper_model", "large-v3"))
            self.cpu_threads_var.set(audio_settings.get("cpu_threads", 8))
            self.beam_size_var.set(audio_settings.get("beam_size", 5))

            # プロンプト設定
            ai_prompts = config.get("ai_prompts", {})
            self.summary_prompt_var.set(ai_prompts.get("summary_prompt", "以下の配信内容を日本語で要約してください:"))
            self.intro_conversation_prompt_var.set(ai_prompts.get("intro_conversation_prompt", "配信開始前の会話として、以下の内容について2人のAIが話します:"))
            self.outro_conversation_prompt_var.set(ai_prompts.get("outro_conversation_prompt", "配信終了後の振り返りとして、以下の内容について2人のAIが話します:"))
            self.image_prompt_var.set(ai_prompts.get("image_prompt", "この配信の抽象的なイメージを生成してください:"))
            
            # AI機能
            ai_features = config.get("ai_features", {})
            self.summary_text_var.set(ai_features.get("enable_summary_text", True))
            self.summary_image_var.set(ai_features.get("enable_summary_image", True))
            self.ai_music_var.set(ai_features.get("enable_ai_music", True))
            self.ai_conversation_var.set(ai_features.get("enable_ai_conversation", True))
            
            
            # 表示機能
            display_features = config.get("display_features", {})
            self.emotion_scores_var.set(display_features.get("enable_emotion_scores", True))
            self.comment_ranking_var.set(display_features.get("enable_comment_ranking", True))
            self.word_ranking_var.set(display_features.get("enable_word_ranking", True))
            self.thumbnails_var.set(display_features.get("enable_thumbnails", True))
            self.audio_player_var.set(display_features.get("enable_audio_player", True))
            self.timeshift_jump_var.set(display_features.get("enable_timeshift_jump", True))
            
            # スペシャルユーザー
            special_users = config.get("special_users", [])
            self.special_users_var.set(", ".join(special_users))
            self.update_special_users_list(special_users)
            
            print(f"設定読み込み完了: {account_id}")
            
        except Exception as e:
            print(f"設定読み込みエラー: {e}")
            import traceback
            traceback.print_exc()
        
    def update_special_users_list(self, special_users):
        """スペシャルユーザー一覧表示を更新"""
        self.special_users_listbox.delete(0, tk.END)
        for i, user in enumerate(special_users, 1):
            self.special_users_listbox.insert(tk.END, f"{i}. {user}")
        
    def create_user(self):
        account_id = self.account_var.get().strip()
        
        if not account_id:
            messagebox.showerror("エラー", "アカウントIDを入力してください")
            return
            
        if account_id in self.config_manager.get_user_list():
            messagebox.showerror("エラー", f"アカウントID '{account_id}' は既に存在します")
            return
        
        config = self.get_current_config()
        self.config_manager.save_user_config(account_id, config)
        self.load_users()
        
        messagebox.showinfo("作成完了", f"アカウント '{account_id}' を作成しました")
                
    def copy_user(self):
        selection = self.user_listbox.curselection()
        if not selection:
            messagebox.showerror("エラー", "複製元のアカウントを選択してください")
            return
            
        new_account_id = self.account_var.get().strip()
        if not new_account_id:
            messagebox.showerror("エラー", "新しいアカウントIDを入力してください")
            return
            
        if new_account_id in self.config_manager.get_user_list():
            messagebox.showerror("エラー", f"アカウントID '{new_account_id}' は既に存在します")
            return
        
        source_label = self.user_listbox.get(selection[0])
        source_account_id = source_label.split(" ")[0]
        
        if self.config_manager.copy_user_config(source_account_id, new_account_id):
            self.load_users()
            messagebox.showinfo("複製完了", f"'{source_account_id}' から '{new_account_id}' を作成しました")
        else:
            messagebox.showerror("エラー", "複製に失敗しました")
                
    def delete_user(self):
        selection = self.user_listbox.curselection()
        if selection:
            selected_label = self.user_listbox.get(selection[0])
            account_id = selected_label.split(" ")[0]
            
            if messagebox.askyesno("削除確認", f"アカウント {account_id} を削除しますか？"):
                if self.config_manager.delete_user(account_id):
                    self.load_users()
                    messagebox.showinfo("削除完了", f"アカウント {account_id} を削除しました")
                else:
                    messagebox.showerror("エラー", "削除に失敗しました")
                
    def get_current_config(self):
        return {
            "account_id": self.account_var.get(),
            "display_name": self.display_name_var.get(),
            "basic_settings": {
                "platform": self.platform_var.get(),
                "account_id": self.account_var.get(),
                "platform_directory": self.platform_dir_var.get(),
                "ncv_directory": self.ncv_dir_var.get()
            },
            "api_settings": {
                "ai_model": self.ai_model_var.get(),
                "openai_api_key": self.openai_api_key_var.get(),
                "google_api_key": self.google_api_key_var.get(),
                "suno_api_key": self.suno_api_key_var.get(),
                "imgur_api_key": self.imgur_api_key_var.get()  # 追加
            },
            "audio_settings": {
            "use_gpu": self.use_gpu_var.get(),
            "whisper_model": self.whisper_model_var.get(),
            "cpu_threads": self.cpu_threads_var.get(),
            "beam_size": self.beam_size_var.get()
            },
            "ai_features": {
                "enable_summary_text": self.summary_text_var.get(),
                "enable_summary_image": self.summary_image_var.get(),
                "enable_ai_music": self.ai_music_var.get(),
                "enable_ai_conversation": self.ai_conversation_var.get()
            },
            "ai_prompts": {
                "summary_prompt": self.summary_prompt_var.get(),
                "intro_conversation_prompt": self.intro_conversation_prompt_var.get(),
                "outro_conversation_prompt": self.outro_conversation_prompt_var.get(),
                "image_prompt": self.image_prompt_var.get()
            },
            "display_features": {
                "enable_emotion_scores": self.emotion_scores_var.get(),
                "enable_comment_ranking": self.comment_ranking_var.get(),
                "enable_word_ranking": self.word_ranking_var.get(),
                "enable_thumbnails": self.thumbnails_var.get(),
                "enable_audio_player": self.audio_player_var.get(),
                "enable_timeshift_jump": self.timeshift_jump_var.get()
            },
            "special_users": [user.strip() for user in self.special_users_var.get().split(",") if user.strip()]
        }
        
    def save_config(self):
        config = self.get_current_config()
        account_id = config["account_id"]
        if account_id:
            self.config_manager.save_user_config(account_id, config)
            self.load_users()
            self.refresh_callback()
            self.update_special_users_list(config["special_users"])
            messagebox.showinfo("保存完了", f"アカウント {account_id} の設定を保存しました")
        else:
            messagebox.showerror("エラー", "アカウントIDを入力してください")
            
    def apply_config(self):
        self.save_config()