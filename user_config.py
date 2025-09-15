import tkinter as tk
from tkinter import ttk, messagebox
import json
import tkinter.simpledialog
import os
import threading

class UserConfigWindow:
    def __init__(self, parent, config_manager, refresh_callback):
        self.config_manager = config_manager
        self.refresh_callback = refresh_callback
        
        # ニックネーム取得の重複実行を防ぐフラグを初期化
        self.nickname_fetching = False
        self.nickname_fetch_thread = None
        
        self.window = tk.Toplevel(parent)
        self.window.title("ユーザー設定管理")
        self.window.geometry("900x700")
        self.window.grab_set()
        
        self.current_config = None
        self.setup_ui()
        self.load_users()

    def fetch_nickname(self):
        """ニックネーム取得ボタンのコールバック"""
        account_id = self.account_var.get().strip()
        if not account_id:
            messagebox.showwarning("警告", "アカウントIDを入力してください")
            return
        
        if not account_id.isdigit():
            messagebox.showwarning("警告", "正しいアカウントIDを入力してください")
            return
        
        # 手動実行の場合は即座に実行
        self.fetch_nickname_async(account_id, force=True)


    def sync_tree_to_memory(self):
        """TreeViewの内容をメモリ(_tree_user_data)に反映 - 既存データを保持"""
        if not hasattr(self, '_tree_user_data'):
            self._tree_user_data = {}

        print("=== sync_tree_to_memory 開始 ===")
        
        # TreeViewの現在の表示データで基本情報のみ更新（詳細データは保持）
        tree_user_ids = set()
        for item in self.special_users_tree.get_children():
            user_id = self.special_users_tree.item(item)["text"]
            values = self.special_users_tree.item(item)["values"]
            tree_user_ids.add(user_id)

            if user_id in self._tree_user_data:
                # 既存データがある場合は表示項目のみ更新
                self._tree_user_data[user_id].update({
                    "display_name": values[0] if len(values) > 0 else "",
                    "analysis_ai_model": values[1] if len(values) > 1 else "openai-gpt4o",
                    "analysis_enabled": values[2] == "有効" if len(values) > 2 else True,
                    "template": values[3] if len(values) > 3 else "user_detail.html"
                })
                print(f"既存データ更新: {user_id}")
            else:
                print(f"警告: {user_id} の詳細データが見つかりません - 追加処理が必要")

        # TreeViewから削除されたユーザーをメモリからも削除
        users_to_remove = set(self._tree_user_data.keys()) - tree_user_ids
        for user_id in users_to_remove:
            del self._tree_user_data[user_id]
            print(f"削除されたユーザーをメモリからも削除: {user_id}")
        
        print("=== sync_tree_to_memory 完了 ===")

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
        
        # 基本設定 - ここでbasic_frameを正しく定義
        basic_frame = tk.LabelFrame(scrollable_frame, text="基本設定")
        basic_frame.pack(fill=tk.X, pady=5)
        
        # Account ID入力
        tk.Label(basic_frame, text="Account ID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=2)
        self.account_var = tk.StringVar()
        account_entry = tk.Entry(basic_frame, textvariable=self.account_var)
        account_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        account_entry.bind('<FocusOut>', self.on_account_id_changed)
        
        # ニックネーム取得ボタン
        tk.Button(basic_frame, text="ニックネーム取得", 
                command=self.fetch_nickname).grid(row=0, column=2, padx=5)
        
        # Platform設定
        tk.Label(basic_frame, text="Platform:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=2)
        self.platform_var = tk.StringVar(value="niconico")
        platform_combo = ttk.Combobox(basic_frame, textvariable=self.platform_var, 
                                    values=["niconico", "youtube", "twitch"])
        platform_combo.grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=2)
        
        # 監視Dir設定
        tk.Label(basic_frame, text="監視Dir:").grid(row=2, column=0, sticky=tk.W, padx=5, pady=2)
        dir_frame = tk.Frame(basic_frame)
        dir_frame.grid(row=2, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
        self.platform_dir_var = tk.StringVar(value="rec")
        tk.Entry(dir_frame, textvariable=self.platform_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(dir_frame, text="参照", command=lambda: self.browse_directory(self.platform_dir_var)).pack(side=tk.RIGHT, padx=(5,0))

        # NCVDir設定
        tk.Label(basic_frame, text="NCVDir:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=2)
        ncv_frame = tk.Frame(basic_frame)
        ncv_frame.grid(row=3, column=1, columnspan=2, sticky=tk.W+tk.E, padx=5, pady=2)
        self.ncv_dir_var = tk.StringVar(value="ncv")
        tk.Entry(ncv_frame, textvariable=self.ncv_dir_var).pack(side=tk.LEFT, fill=tk.X, expand=True)
        tk.Button(ncv_frame, text="参照", command=lambda: self.browse_directory(self.ncv_dir_var)).pack(side=tk.RIGHT, padx=(5,0))
                
        basic_frame.columnconfigure(1, weight=1)
        
        # 以下、残りの設定セクションは元のコードと同じ...
        # API設定
        api_frame = tk.LabelFrame(scrollable_frame, text="API設定")
        api_frame.pack(fill=tk.X, pady=5)


        # 要約AIモデル選択
        tk.Label(api_frame, text="要約AIモデル:").pack(anchor=tk.W)
        self.summary_ai_model_var = tk.StringVar(value="openai-gpt4o")
        summary_model_combo = ttk.Combobox(api_frame, textvariable=self.summary_ai_model_var, 
                                        values=["openai-gpt4o", "google-gemini-2.5-flash"], 
                                        state="readonly", width=30)
        summary_model_combo.pack(fill=tk.X, padx=5, pady=2)

        # 会話AIモデル選択
        tk.Label(api_frame, text="会話AIモデル:").pack(anchor=tk.W, pady=(10, 0))
        self.conversation_ai_model_var = tk.StringVar(value="google-gemini-2.5-flash")
        conversation_model_combo = ttk.Combobox(api_frame, textvariable=self.conversation_ai_model_var, 
                                            values=["openai-gpt4o", "google-gemini-2.5-flash"], 
                                            state="readonly", width=30)
        conversation_model_combo.pack(fill=tk.X, padx=5, pady=2)

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

        # 音楽設定セクション
        music_frame = tk.LabelFrame(scrollable_frame, text="音楽生成設定")
        music_frame.pack(fill=tk.X, pady=5)

        # 曲調設定
        tk.Label(music_frame, text="音楽スタイル:").pack(anchor=tk.W, pady=(5, 0))
        self.music_style_var = tk.StringVar(value="J-Pop, Upbeat")
        tk.Entry(music_frame, textvariable=self.music_style_var, width=60).pack(fill=tk.X, padx=5, pady=2)

        # モデル選択
        tk.Label(music_frame, text="モデル:").pack(anchor=tk.W, pady=(10, 0))
        self.music_model_var = tk.StringVar(value="V4")
        music_model_combo = ttk.Combobox(music_frame, textvariable=self.music_model_var,
                                        values=["V4", "V3"], state="readonly", width=20)
        music_model_combo.pack(anchor=tk.W, padx=5, pady=2)

        # ボーカル有無
        self.music_instrumental_var = tk.BooleanVar(value=False)
        tk.Checkbutton(music_frame, text="インストゥルメンタル（歌なし）", 
                    variable=self.music_instrumental_var).pack(anchor=tk.W, padx=5, pady=5)

        # プロンプト設定
        prompt_frame = tk.LabelFrame(scrollable_frame, text="AIプロンプト設定")
        prompt_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(prompt_frame, text="要約プロンプト:").pack(anchor=tk.W)
        self.summary_prompt_var = tk.StringVar(value="以下の配信内容を日本語で要約してください:")
        tk.Entry(prompt_frame, textvariable=self.summary_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="放送前会話プロンプト:").pack(anchor=tk.W)
        self.intro_conversation_prompt_var = tk.StringVar(value="配信開始前の会話として、以下の内容について話し合います:")
        tk.Entry(prompt_frame, textvariable=self.intro_conversation_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="放送後会話プロンプト:").pack(anchor=tk.W)
        self.outro_conversation_prompt_var = tk.StringVar(value="配信終了後の振り返りとして、以下の内容について話し合います:")
        tk.Entry(prompt_frame, textvariable=self.outro_conversation_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(prompt_frame, text="画像プロンプト:").pack(anchor=tk.W)
        self.image_prompt_var = tk.StringVar(value="この配信の抽象的なイメージを生成してください:")
        tk.Entry(prompt_frame, textvariable=self.image_prompt_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        # キャラクター設定セクションを追加
        character_frame = tk.LabelFrame(scrollable_frame, text="AI会話キャラクター設定")
        character_frame.pack(fill=tk.X, pady=5)
        
        # キャラクター1設定
        tk.Label(character_frame, text="キャラクター1名前:").pack(anchor=tk.W)
        self.character1_name_var = tk.StringVar(value="ニニちゃん")
        tk.Entry(character_frame, textvariable=self.character1_name_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(character_frame, text="キャラクター1性格:").pack(anchor=tk.W)
        self.character1_personality_var = tk.StringVar(value="ボケ役で標準語を話す明るい女の子")
        tk.Entry(character_frame, textvariable=self.character1_personality_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(character_frame, text="キャラクター1画像URL:").pack(anchor=tk.W)
        self.character1_image_url_var = tk.StringVar(value="")
        tk.Entry(character_frame, textvariable=self.character1_image_url_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        self.character1_image_flip_var = tk.BooleanVar(value=False)
        tk.Checkbutton(character_frame, text="キャラクター1画像を左右反転", variable=self.character1_image_flip_var).pack(anchor=tk.W, padx=5)
        
        # 区切り線
        tk.Frame(character_frame, height=2, bg="gray").pack(fill=tk.X, padx=5, pady=10)
        
        # キャラクター2設定
        tk.Label(character_frame, text="キャラクター2名前:").pack(anchor=tk.W)
        self.character2_name_var = tk.StringVar(value="ココちゃん")
        tk.Entry(character_frame, textvariable=self.character2_name_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(character_frame, text="キャラクター2性格:").pack(anchor=tk.W)
        self.character2_personality_var = tk.StringVar(value="ツッコミ役で関西弁を話すしっかり者の女の子")
        tk.Entry(character_frame, textvariable=self.character2_personality_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        tk.Label(character_frame, text="キャラクター2画像URL:").pack(anchor=tk.W)
        self.character2_image_url_var = tk.StringVar(value="")
        tk.Entry(character_frame, textvariable=self.character2_image_url_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        self.character2_image_flip_var = tk.BooleanVar(value=False)
        tk.Checkbutton(character_frame, text="キャラクター2画像を左右反転", variable=self.character2_image_flip_var).pack(anchor=tk.W, padx=5)
        
        # 会話設定
        tk.Label(character_frame, text="会話往復数:").pack(anchor=tk.W, pady=(10, 0))
        self.conversation_turns_var = tk.IntVar(value=5)
        tk.Spinbox(character_frame, from_=3, to=10, textvariable=self.conversation_turns_var, width=10).pack(anchor=tk.W, padx=5, pady=2)
        
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


        # スペシャルユーザー設定セクションを追加
        special_frame = tk.LabelFrame(scrollable_frame, text="スペシャルユーザー設定")
        special_frame.pack(fill=tk.X, pady=5)
        
        tk.Label(special_frame, text="特別処理対象ユーザーID (カンマ区切り):").pack(anchor=tk.W)
        self.special_users_var = tk.StringVar()
        tk.Entry(special_frame, textvariable=self.special_users_var, width=60).pack(fill=tk.X, padx=5, pady=2)
        
        # 同期ボタンを追加
        sync_button = tk.Button(special_frame, text="↓ 個別設定に反映", command=self.sync_special_users_to_tree)
        sync_button.pack(anchor=tk.W, padx=5, pady=2)
        
        # スペシャルユーザー一覧表示
        tk.Label(special_frame, text="登録済みスペシャルユーザー:").pack(anchor=tk.W, pady=(10, 0))
        self.special_users_listbox = tk.Listbox(special_frame, height=4)
        self.special_users_listbox.pack(fill=tk.X, padx=5, pady=2)

        # スペシャルユーザー詳細設定
        special_detail_frame = tk.LabelFrame(scrollable_frame, text="スペシャルユーザー詳細設定")
        special_detail_frame.pack(fill=tk.X, pady=5)

        # グローバル設定
        global_frame = tk.LabelFrame(special_detail_frame, text="デフォルト設定")
        global_frame.pack(fill=tk.X, padx=5, pady=5)

        # デフォルト分析有効/無効
        self.default_analysis_enabled_var = tk.BooleanVar(value=True)
        tk.Checkbutton(global_frame, text="デフォルトでAI分析を有効にする", 
                    variable=self.default_analysis_enabled_var).pack(anchor=tk.W, padx=5, pady=2)

        # デフォルトAIモデル
        tk.Label(global_frame, text="デフォルト分析AIモデル:").pack(anchor=tk.W, padx=5)
        self.default_analysis_ai_model_var = tk.StringVar(value="openai-gpt4o")
        default_model_combo = ttk.Combobox(global_frame, textvariable=self.default_analysis_ai_model_var,
                                        values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                        state="readonly", width=30)
        default_model_combo.pack(anchor=tk.W, padx=5, pady=2)

        # デフォルト分析プロンプト
        tk.Label(global_frame, text="デフォルト分析プロンプト:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.default_analysis_prompt_text = tk.Text(global_frame, height=4, wrap=tk.WORD)
        self.default_analysis_prompt_text.pack(fill=tk.X, padx=5, pady=2)

        # デフォルトテンプレート
        tk.Label(global_frame, text="デフォルトテンプレート:").pack(anchor=tk.W, padx=5, pady=(10, 0))
        self.default_template_var = tk.StringVar(value="user_detail.html")
        tk.Entry(global_frame, textvariable=self.default_template_var, width=40).pack(anchor=tk.W, padx=5, pady=2)

        # 個別ユーザー設定
        users_frame = tk.LabelFrame(special_detail_frame, text="個別ユーザー設定")
        users_frame.pack(fill=tk.BOTH, expand=True, padx=5, pady=5)

        # ユーザー一覧とボタン
        user_control_frame = tk.Frame(users_frame)
        user_control_frame.pack(fill=tk.X, padx=5, pady=5)

        tk.Button(user_control_frame, text="ユーザー追加", command=self.add_special_user).pack(side=tk.LEFT, padx=5)
        tk.Button(user_control_frame, text="編集", command=self.edit_special_user).pack(side=tk.LEFT, padx=5)
        tk.Button(user_control_frame, text="削除", command=self.remove_special_user).pack(side=tk.LEFT, padx=5)
        tk.Button(user_control_frame, text="複製", command=self.copy_special_user).pack(side=tk.LEFT, padx=5)
        # 逆方向の同期ボタンを追加
        tk.Button(user_control_frame, text="↑ テキストに反映", command=self.sync_tree_to_special_users).pack(side=tk.LEFT, padx=5)

        # ユーザー一覧TreeView
        self.special_users_tree = ttk.Treeview(users_frame, 
                                            columns=("display_name", "ai_model", "analysis_enabled", "template"),
                                            height=8)
        self.special_users_tree.heading("#0", text="ユーザーID")
        self.special_users_tree.heading("display_name", text="表示名")
        self.special_users_tree.heading("ai_model", text="AIモデル")
        self.special_users_tree.heading("analysis_enabled", text="分析有効")
        self.special_users_tree.heading("template", text="テンプレート")

        self.special_users_tree.column("#0", width=100)
        self.special_users_tree.column("display_name", width=120)
        self.special_users_tree.column("ai_model", width=120)
        self.special_users_tree.column("analysis_enabled", width=80)
        self.special_users_tree.column("template", width=120)

        # TreeViewスクロールバー
        tree_scrollbar = ttk.Scrollbar(users_frame, orient="vertical", command=self.special_users_tree.yview)
        self.special_users_tree.configure(yscrollcommand=tree_scrollbar.set)

        self.special_users_tree.pack(side="left", fill=tk.BOTH, expand=True, padx=5, pady=5)
        tree_scrollbar.pack(side="right", fill="y")
        
        # タグ設定セクションを追加
        tag_frame = tk.LabelFrame(scrollable_frame, text="タグ設定")
        tag_frame.pack(fill=tk.X, pady=5)

        tk.Label(tag_frame, text="タグ (カンマ区切り):").pack(anchor=tk.W)
        self.tags_var = tk.StringVar()
        tk.Entry(tag_frame, textvariable=self.tags_var, width=60).pack(fill=tk.X, padx=5, pady=2)

        tk.Label(tag_frame, text="登録済みタグ:").pack(anchor=tk.W, pady=(10, 0))
        self.tags_listbox = tk.Listbox(tag_frame, height=4)
        self.tags_listbox.pack(fill=tk.X, padx=5, pady=2)
        
        # 保存・キャンセルボタン
        button_frame = tk.Frame(scrollable_frame)
        button_frame.pack(fill=tk.X, pady=10)
        
        tk.Button(button_frame, text="保存", command=self.save_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="適用", command=self.apply_config).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.window.destroy).pack(side=tk.RIGHT, padx=5)
        
    def browse_directory(self, target_var):
        """フォルダ選択ダイアログを表示"""
        from tkinter import filedialog
        
        # 現在の値を初期ディレクトリとして使用
        current_path = target_var.get()
        if current_path and os.path.exists(current_path):
            initial_dir = current_path
        else:
            initial_dir = os.getcwd()
        
        # フォルダ選択ダイアログを表示
        selected_dir = filedialog.askdirectory(
            title="フォルダを選択してください",
            initialdir=initial_dir
        )
        
        if selected_dir:
            # 相対パスに変換するかユーザーに確認
            current_dir = os.getcwd()
            try:
                # 現在のディレクトリからの相対パスを計算
                rel_path = os.path.relpath(selected_dir, current_dir)
                
                # 相対パスが短い場合は相対パス、そうでなければ絶対パスを使用
                if len(rel_path) < len(selected_dir) and not rel_path.startswith('..'):
                    if messagebox.askyesno("パス形式選択", 
                        f"相対パス '{rel_path}' を使用しますか？\n\n"
                        f"「はい」: {rel_path}\n"
                        f"「いいえ」: {selected_dir}"):
                        target_var.set(rel_path)
                    else:
                        target_var.set(selected_dir)
                else:
                    target_var.set(selected_dir)
            except ValueError:
                # 相対パス計算に失敗した場合は絶対パスを使用
                target_var.set(selected_dir)

    def on_account_id_changed(self, event):
        """アカウントIDが変更されたときの処理"""
        account_id = self.account_var.get().strip()
        if account_id and account_id.isdigit():
            # 遅延実行で重複を防ぐ
            if hasattr(self, 'nickname_timer'):
                self.window.after_cancel(self.nickname_timer)
            self.nickname_timer = self.window.after(1000, lambda: self.fetch_nickname_async(account_id, force=False))

    def fetch_nickname_async(self, account_id, force=False):
        """非同期でニックネームを取得"""
        # 既に実行中かつ強制実行でない場合はスキップ
        if hasattr(self, 'nickname_fetching') and self.nickname_fetching and not force:
            print(f"ニックネーム取得スキップ (既に実行中): {account_id}")
            return
        
        # 前回のスレッドが残っている場合は適切に処理
        if hasattr(self, 'nickname_fetch_thread') and self.nickname_fetch_thread and self.nickname_fetch_thread.is_alive():
            if not force:
                print(f"ニックネーム取得スキップ (スレッド実行中): {account_id}")
                return
        
        self.nickname_fetching = True
        print(f"ニックネーム取得開始: {account_id} (force={force})")
        
        def fetch_thread():
            try:
                from utils import get_user_nickname_with_cache
                nickname = get_user_nickname_with_cache(account_id)
                
                # UIスレッドで結果を反映
                self.window.after(0, lambda: self.update_display_name_safe(nickname, account_id, force))
                
            except Exception as e:
                print(f"ニックネーム取得エラー (ID: {account_id}): {e}")
                # エラーメッセージは手動実行時のみ表示
                if force:
                    self.window.after(0, lambda: messagebox.showerror("エラー", f"ニックネーム取得に失敗しました: {e}"))
            finally:
                self.nickname_fetching = False
                print(f"ニックネーム取得完了: {account_id}")
        
        # 新しいスレッドで実行
        self.nickname_fetch_thread = threading.Thread(target=fetch_thread, daemon=True)
        self.nickname_fetch_thread.start()

    def update_display_name_safe(self, nickname, account_id, force=False):
        """安全にニックネームで表示名を更新"""
        # 現在のアカウントIDと一致するかチェック
        current_account_id = self.account_var.get().strip()
        if current_account_id != account_id:
            print(f"アカウントID不一致のためスキップ: {current_account_id} != {account_id}")
            return  # 別のアカウントIDに変更されている場合は無視
        
        if nickname:
            current_display_name = self.display_name_var.get().strip()
            if not current_display_name:  # 表示名が空の場合のみ自動設定
                self.display_name_var.set(nickname)
                if force:  # 手動実行時のみ成功メッセージ表示
                    messagebox.showinfo("成功", f"ニックネーム「{nickname}」を取得しました")
            elif force:  # 手動実行時のみ確認ダイアログ表示
                if messagebox.askyesno("確認", f"取得したニックネーム「{nickname}」で表示名を更新しますか？\n現在の表示名: {current_display_name}"):
                    self.display_name_var.set(nickname)
        elif force:  # 手動実行時のみエラーメッセージ表示
            messagebox.showwarning("警告", "ニックネームを取得できませんでした")

    def sync_special_users_to_tree(self):
        """テキストフィールドのユーザーIDをTreeViewに同期"""
        # テキストフィールドからユーザーIDを取得
        user_ids = [user.strip() for user in self.special_users_var.get().split(",") if user.strip()]
        
        # 現在のTreeViewのユーザーIDを取得
        existing_users = set()
        for item in self.special_users_tree.get_children():
            existing_users.add(self.special_users_tree.item(item)["text"])
        
        # 新しいユーザーIDをTreeViewに追加
        added_count = 0
        for user_id in user_ids:
            if user_id not in existing_users:
                # デフォルト設定でTreeViewに追加
                user_config = {
                    "user_id": user_id,
                    "display_name": f"ユーザー{user_id}",
                    "analysis_enabled": self.default_analysis_enabled_var.get(),
                    "analysis_ai_model": self.default_analysis_ai_model_var.get(),
                    "analysis_prompt": self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
                    "template": self.default_template_var.get(),
                    "description": "",
                    "tags": []
                }
                
                # メモリに保存
                if not hasattr(self, '_tree_user_data'):
                    self._tree_user_data = {}
                self._tree_user_data[user_id] = user_config
                
                # TreeViewに追加
                self.special_users_tree.insert("", tk.END, text=user_id,
                                            values=(user_config["display_name"],
                                                    user_config["analysis_ai_model"],
                                                    "有効" if user_config["analysis_enabled"] else "無効",
                                                    user_config["template"]))
                added_count += 1
        
        if added_count > 0:
            messagebox.showinfo("同期完了", f"{added_count}件のユーザーを個別設定に追加しました")
        else:
            messagebox.showinfo("同期完了", "追加するユーザーはありませんでした")

    def sync_tree_to_special_users(self):
        """TreeViewのユーザーIDをテキストフィールドに同期"""
        user_ids = []
        for item in self.special_users_tree.get_children():
            user_ids.append(self.special_users_tree.item(item)["text"])
        
        self.special_users_var.set(", ".join(user_ids))
        messagebox.showinfo("同期完了", f"{len(user_ids)}件のユーザーIDをテキストフィールドに反映しました")




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
            # 後方互換性のため、古い設定も確認
            old_ai_model = api_settings.get("ai_model", "openai-gpt4o")
            self.summary_ai_model_var.set(api_settings.get("summary_ai_model", old_ai_model))
            self.conversation_ai_model_var.set(api_settings.get("conversation_ai_model", old_ai_model))
            self.openai_api_key_var.set(api_settings.get("openai_api_key", ""))
            self.google_api_key_var.set(api_settings.get("google_api_key", ""))
            self.suno_api_key_var.set(api_settings.get("suno_api_key", ""))
            self.imgur_api_key_var.set(api_settings.get("imgur_api_key", ""))
            
            # 音声処理設定
            audio_settings = config.get("audio_settings", {})
            self.use_gpu_var.set(audio_settings.get("use_gpu", True))
            self.whisper_model_var.set(audio_settings.get("whisper_model", "large-v3"))
            self.cpu_threads_var.set(audio_settings.get("cpu_threads", 8))
            self.beam_size_var.set(audio_settings.get("beam_size", 5))

            # プロンプト設定
            ai_prompts = config.get("ai_prompts", {})
            self.summary_prompt_var.set(ai_prompts.get("summary_prompt", "以下の配信内容を日本語で要約してください:"))
            self.intro_conversation_prompt_var.set(ai_prompts.get("intro_conversation_prompt", "配信開始前の会話として、以下の内容について話し合います:"))
            self.outro_conversation_prompt_var.set(ai_prompts.get("outro_conversation_prompt", "配信終了後の振り返りとして、以下の内容について話し合います:"))
            self.image_prompt_var.set(ai_prompts.get("image_prompt", "この配信の抽象的なイメージを生成してください:"))
            
            # キャラクター設定
            self.character1_name_var.set(ai_prompts.get("character1_name", "ニニちゃん"))
            self.character1_personality_var.set(ai_prompts.get("character1_personality", "ボケ役で標準語を話す明るい女の子"))
            self.character1_image_url_var.set(ai_prompts.get("character1_image_url", ""))
            self.character1_image_flip_var.set(ai_prompts.get("character1_image_flip", False))
            self.character2_name_var.set(ai_prompts.get("character2_name", "ココちゃん"))
            self.character2_personality_var.set(ai_prompts.get("character2_personality", "ツッコミ役で関西弁を話すしっかり者の女の子"))
            self.character2_image_url_var.set(ai_prompts.get("character2_image_url", ""))
            self.character2_image_flip_var.set(ai_prompts.get("character2_image_flip", False))
            self.conversation_turns_var.set(ai_prompts.get("conversation_turns", 5))
            
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
            
            tags = config.get("tags", [])
            self.tags_var.set(", ".join(tags))
            self.update_tags_list(tags)

            # スペシャルユーザー詳細設定
            special_users_config = config.get("special_users_config", {})
            self.default_analysis_enabled_var.set(special_users_config.get("default_analysis_enabled", True))
            self.default_analysis_ai_model_var.set(special_users_config.get("default_analysis_ai_model", "openai-gpt4o"))

            default_prompt = special_users_config.get("default_analysis_prompt", "以下のユーザーのコメント履歴を分析してください")
            self.default_analysis_prompt_text.delete(1.0, tk.END)
            self.default_analysis_prompt_text.insert(1.0, default_prompt)

            self.default_template_var.set(special_users_config.get("default_template", "user_detail.html"))

            # TreeViewに詳細ユーザー設定を読み込み
            self.load_special_users_tree(special_users_config.get("users", {}))
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

    def update_tags_list(self, tags):
        """タグ一覧表示を更新"""
        self.tags_listbox.delete(0, tk.END)
        for i, tag in enumerate(tags, 1):
            self.tags_listbox.insert(tk.END, f"{i}. {tag}")


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
                "summary_ai_model": self.summary_ai_model_var.get(),
                "conversation_ai_model": self.conversation_ai_model_var.get(),
                "openai_api_key": self.openai_api_key_var.get(),
                "google_api_key": self.google_api_key_var.get(),
                "suno_api_key": self.suno_api_key_var.get(),
                "imgur_api_key": self.imgur_api_key_var.get()
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
            "music_settings": {
                "style": self.music_style_var.get(),
                "model": self.music_model_var.get(),
                "instrumental": self.music_instrumental_var.get()
            },

            "ai_prompts": {
                "summary_prompt": self.summary_prompt_var.get(),
                "intro_conversation_prompt": self.intro_conversation_prompt_var.get(),
                "outro_conversation_prompt": self.outro_conversation_prompt_var.get(),
                "image_prompt": self.image_prompt_var.get(),
                "character1_name": self.character1_name_var.get(),
                "character1_personality": self.character1_personality_var.get(),
                "character1_image_url": self.character1_image_url_var.get(),
                "character1_image_flip": self.character1_image_flip_var.get(),
                "character2_name": self.character2_name_var.get(),
                "character2_personality": self.character2_personality_var.get(),
                "character2_image_url": self.character2_image_url_var.get(),
                "character2_image_flip": self.character2_image_flip_var.get(),
                "conversation_turns": self.conversation_turns_var.get()
            },
            
            "display_features": {
                "enable_emotion_scores": self.emotion_scores_var.get(),
                "enable_comment_ranking": self.comment_ranking_var.get(),
                "enable_word_ranking": self.word_ranking_var.get(),
                "enable_thumbnails": self.thumbnails_var.get(),
                "enable_audio_player": self.audio_player_var.get(),
                "enable_timeshift_jump": self.timeshift_jump_var.get()
            },
            "special_users": [user.strip() for user in self.special_users_var.get().split(",") if user.strip()],
            "tags": [tag.strip() for tag in self.tags_var.get().split(",") if tag.strip()],
            "special_users_config": {
                "default_analysis_enabled": self.default_analysis_enabled_var.get(),
                "default_analysis_ai_model": self.default_analysis_ai_model_var.get(),
                "default_analysis_prompt": self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
                "default_template": self.default_template_var.get(),
                "users": self.get_special_users_from_tree()
            }
        }
        
    def get_special_users_from_tree(self):
        """TreeViewからスペシャルユーザー設定を取得"""
        users_config = {}
        
        if not hasattr(self, '_tree_user_data'):
            self._tree_user_data = {}
            print("警告: _tree_user_data が初期化されていません")
            return users_config
        
        for item in self.special_users_tree.get_children():
            user_id = self.special_users_tree.item(item)["text"]
            
            if user_id in self._tree_user_data:
                users_config[user_id] = self._tree_user_data[user_id].copy()
                prompt_len = len(users_config[user_id].get('analysis_prompt', ''))
                print(f"メモリからデータ取得: {user_id}, プロンプト長: {prompt_len}")
            else:
                print(f"警告: {user_id} のメモリデータなし - スキップ")
        
        print(f"保存対象ユーザー数: {len(users_config)}")
        return users_config

    def save_config(self):
        """設定保存時に詳細ユーザー設定も含める"""
        print("=== 保存処理開始 ===")
        print(f"保存前メモリデータ: {list(getattr(self, '_tree_user_data', {}).keys())}")
        
        # メモリデータの詳細確認
        if hasattr(self, '_tree_user_data'):
            for user_id, user_data in self._tree_user_data.items():
                prompt_len = len(user_data.get('analysis_prompt', ''))
                prompt_preview = user_data.get('analysis_prompt', '')[:50] + "..." if prompt_len > 50 else user_data.get('analysis_prompt', '')
                print(f"  {user_id}: プロンプト長={prompt_len}, 内容='{prompt_preview}'")
        
        self.sync_tree_to_memory()
        
        config = self.get_current_config()
        account_id = config["account_id"]
        
        special_users_config = config["special_users_config"]["users"]
        print(f"最終保存データ - ユーザー数: {len(special_users_config)}")
        for user_id, user_data in special_users_config.items():
            prompt_len = len(user_data.get('analysis_prompt', ''))
            print(f"  最終 {user_id}: プロンプト長={prompt_len}")
        
        if account_id:
            self.config_manager.save_user_config(account_id, config)
            print("=== ファイル保存完了 ===")
            self.load_users()
            self.refresh_callback()
            self.update_special_users_list(config["special_users"])
            messagebox.showinfo("保存完了", f"アカウント {account_id} の設定を保存しました")
        else:
            messagebox.showerror("エラー", "アカウントIDを入力してください")

    def get_complete_special_users_from_tree(self):
        """TreeViewと_tree_user_dataから完全なユーザー設定を取得"""
        users_config = {}
        
        if not hasattr(self, '_tree_user_data'):
            self._tree_user_data = {}
        
        for item in self.special_users_tree.get_children():
            user_id = self.special_users_tree.item(item)["text"]
            
            # メモリ上のデータがあれば使用
            if user_id in self._tree_user_data:
                users_config[user_id] = self._tree_user_data[user_id].copy()
            else:
                # TreeViewの表示データから基本情報のみ復元
                values = self.special_users_tree.item(item)["values"]
                users_config[user_id] = {
                    "user_id": user_id,
                    "display_name": values[0] if len(values) > 0 else "",
                    "analysis_ai_model": values[1] if len(values) > 1 else "openai-gpt4o",
                    "analysis_enabled": values[2] == "有効" if len(values) > 2 else True,
                    "template": values[3] if len(values) > 3 else "user_detail.html",
                    "analysis_prompt": self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
                    "description": "",
                    "tags": []
                }
        
        return users_config


    def apply_config(self):
        self.save_config()

    # === apply_config()メソッドの後に追加 ===
    def load_special_users_tree(self, users_config):
        """TreeViewにスペシャルユーザー設定を読み込み"""
        # 既存のアイテムをクリア
        for item in self.special_users_tree.get_children():
            self.special_users_tree.delete(item)
        
        # メモリ上のデータも初期化
        self._tree_user_data = {}
        
        # 新しいアイテムを追加
        for user_id, user_config in users_config.items():
            # メモリ上にデータを保存
            self._tree_user_data[user_id] = user_config.copy()
            
            # TreeViewに表示
            self.special_users_tree.insert("", tk.END, text=user_id,
                                        values=(user_config.get("display_name", ""),
                                                user_config.get("analysis_ai_model", "openai-gpt4o"),
                                                "有効" if user_config.get("analysis_enabled", True) else "無効",
                                                user_config.get("template", "user_detail.html")))
            
            prompt_len = len(user_config.get("analysis_prompt", ""))
            print(f"読み込み: {user_id}, プロンプト長: {prompt_len}")
        
        print(f"詳細ユーザー設定読み込み: {len(users_config)}件")

    def add_special_user(self):
        """スペシャルユーザー追加ダイアログ"""
        dialog = SpecialUserConfigDialog(
            self.window, 
            None, 
            self.default_analysis_ai_model_var.get(),
            self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
            self.default_template_var.get(),
            self.default_analysis_enabled_var.get()
        )
        
        if dialog.result:
            user_config = dialog.result
            user_id = user_config["user_id"]
            
            # メモリ上にデータを保存
            if not hasattr(self, '_tree_user_data'):
                self._tree_user_data = {}
            self._tree_user_data[user_id] = user_config
            
            # TreeViewに追加
            self.special_users_tree.insert("", tk.END, text=user_id,
                                        values=(user_config["display_name"], 
                                                user_config["analysis_ai_model"],
                                                "有効" if user_config["analysis_enabled"] else "無効",
                                                user_config["template"]))
            
            print(f"スペシャルユーザー追加: {user_id}, プロンプト長: {len(user_config.get('analysis_prompt', ''))}")

    def edit_special_user(self):
        """選択されたスペシャルユーザーを編集"""
        print("=== edit_special_user 開始 ===")
        
        selection = self.special_users_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "編集するユーザーを選択してください")
            return

        item = self.special_users_tree.item(selection[0])
        user_id = item["text"]
        print(f"編集対象ユーザー: {user_id}")

        # 既存の設定を取得
        current_config = self.get_special_user_config(user_id)
        print(f"編集前プロンプト長: {len(current_config.get('analysis_prompt', '')) if current_config else 0}")
        
        dialog = SpecialUserConfigDialog(
            self.window,
            current_config,
            self.default_analysis_ai_model_var.get(),
            self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
            self.default_template_var.get(),
            self.default_analysis_enabled_var.get()
        )

        print(f"ダイアログ完了 - 結果: {dialog.result is not None}")
        
        if dialog.result:
            user_config = dialog.result
            new_user_id = user_config["user_id"]
            
            print(f"編集後プロンプト長: {len(user_config.get('analysis_prompt', ''))}")
            print(f"編集後プロンプト内容（最初の100文字）: {user_config.get('analysis_prompt', '')[:100]}")

            # メモリデータを完全に更新
            if not hasattr(self, '_tree_user_data'):
                self._tree_user_data = {}
                print("_tree_user_data を初期化")

            print(f"更新前メモリデータ: {list(self._tree_user_data.keys())}")

            # 古いIDのデータを削除（IDが変更された場合）
            if user_id != new_user_id and user_id in self._tree_user_data:
                del self._tree_user_data[user_id]
                print(f"古いID削除: {user_id}")

            # 新しいデータを完全に保存
            self._tree_user_data[new_user_id] = user_config.copy()
            print(f"メモリに保存: {new_user_id}")
            print(f"保存後メモリ内プロンプト長: {len(self._tree_user_data[new_user_id].get('analysis_prompt', ''))}")

            # TreeViewの表示を更新
            self.special_users_tree.item(
                selection[0],
                text=new_user_id,
                values=(
                    user_config["display_name"],
                    user_config["analysis_ai_model"],
                    "有効" if user_config["analysis_enabled"] else "無効",
                    user_config["template"]
                )
            )
            print("TreeView更新完了")
        else:
            print("ダイアログがキャンセルされました")

        print("=== edit_special_user 終了 ===")

    def apply_current_special_user_changes(self):
        """現在のスペシャルユーザー変更を即座に設定ファイルに反映"""
        if not hasattr(self, 'current_config') or not self.current_config:
            return
        
        # 現在の設定を取得して、スペシャルユーザー部分だけ更新
        account_id = self.current_config["account_id"]
        
        # 既存の設定をベースに、スペシャルユーザー設定のみ更新
        updated_config = self.current_config.copy()
        
        # special_users_configを更新
        if "special_users_config" not in updated_config:
            updated_config["special_users_config"] = {}
        
        updated_config["special_users_config"]["users"] = self.get_special_users_from_tree()
        
        # ファイルに保存
        self.config_manager.save_user_config(account_id, updated_config)
        print(f"スペシャルユーザー設定を即座に保存: {account_id}")




    def remove_special_user(self):
        """選択されたスペシャルユーザーを削除"""
        selection = self.special_users_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "削除するユーザーを選択してください")
            return
        
        item = self.special_users_tree.item(selection[0])
        user_id = item["text"]
        display_name = item["values"][0] if item["values"] else ""
        
        if messagebox.askyesno("削除確認", f"スペシャルユーザー '{user_id} ({display_name})' を削除しますか？"):
            # TreeViewから削除
            self.special_users_tree.delete(selection[0])
            
            # メモリ上のデータからも削除
            if hasattr(self, '_tree_user_data') and user_id in self._tree_user_data:
                del self._tree_user_data[user_id]
            
            print(f"スペシャルユーザー削除・保存完了: {user_id}")

    def copy_special_user(self):
        """選択されたスペシャルユーザーを複製"""
        selection = self.special_users_tree.selection()
        if not selection:
            messagebox.showwarning("警告", "複製するユーザーを選択してください")
            return
        
        item = self.special_users_tree.item(selection[0])
        user_id = item["text"]
        
        # 既存の設定を取得
        current_config = self.get_special_user_config(user_id)
        if current_config:
            # ユーザーIDをクリアして複製
            current_config["user_id"] = ""
            current_config["display_name"] = f"{current_config['display_name']} のコピー"
            
            dialog = SpecialUserConfigDialog(
                self.window, 
                current_config,
                self.default_analysis_ai_model_var.get(),
                self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
                self.default_template_var.get(),
                self.default_analysis_enabled_var.get()
            )
            
            if dialog.result:
                user_config = dialog.result
                new_user_id = user_config["user_id"]
                
                # メモリ上にデータを保存（これが抜けていた）
                if not hasattr(self, '_tree_user_data'):
                    self._tree_user_data = {}
                self._tree_user_data[new_user_id] = user_config
                
                # TreeViewに追加
                self.special_users_tree.insert("", tk.END, text=new_user_id,
                                            values=(user_config["display_name"], 
                                                    user_config["analysis_ai_model"],
                                                    "有効" if user_config["analysis_enabled"] else "無効",
                                                    user_config["template"]))
                
                print(f"スペシャルユーザー複製完了: {user_id} -> {new_user_id}")
                    
           
    def get_special_user_config(self, user_id):
        """TreeViewからユーザー設定を取得"""
        print(f"=== get_special_user_config 開始: {user_id} ===")
        
        if hasattr(self, '_tree_user_data') and user_id in self._tree_user_data:
            config = self._tree_user_data[user_id]
            prompt_len = len(config.get('analysis_prompt', ''))
            print(f"メモリからデータ取得: {user_id}, プロンプト長: {prompt_len}")
            print(f"メモリ内プロンプト内容（最初の100文字）: {config.get('analysis_prompt', '')[:100]}")
            return config
        
        print(f"メモリにデータなし: {user_id}")
        print(f"現在のメモリキー: {list(getattr(self, '_tree_user_data', {}).keys())}")
        
        # TreeViewから基本データを取得
        for item in self.special_users_tree.get_children():
            if self.special_users_tree.item(item)["text"] == user_id:
                values = self.special_users_tree.item(item)["values"]
                default_config = {
                    "user_id": user_id,
                    "display_name": values[0] if len(values) > 0 else "",
                    "analysis_ai_model": values[1] if len(values) > 1 else "openai-gpt4o",
                    "analysis_enabled": values[2] == "有効" if len(values) > 2 else True,
                    "template": values[3] if len(values) > 3 else "user_detail.html",
                    "analysis_prompt": self.default_analysis_prompt_text.get(1.0, tk.END).strip(),
                    "description": "",
                    "tags": []
                }
                print(f"TreeViewからデータ復元: {user_id}, デフォルトプロンプト長: {len(default_config['analysis_prompt'])}")
                return default_config
        
        print(f"ユーザーが見つかりません: {user_id}")
        return None
    
class SpecialUserConfigDialog:
    def __init__(self, parent, existing_config, default_ai_model, default_prompt, default_template, default_enabled):
        self.result = None
        
        # ニックネーム取得の重複実行を防ぐフラグを初期化
        self.nickname_fetching = False
        self.nickname_fetch_thread = None
        
        self.dialog = tk.Toplevel(parent)
        self.dialog.title("スペシャルユーザー設定")
        self.dialog.geometry("600x600")
        self.dialog.grab_set()
        self.dialog.transient(parent)
        self.dialog.protocol("WM_DELETE_WINDOW", self.cancel_clicked)
        
        # UI要素の作成
        self.create_ui(existing_config, default_ai_model, default_prompt, default_template, default_enabled)
        
        # 最後にwait_windowを呼び出し
        self.dialog.wait_window()
    
    def create_ui(self, existing_config, default_ai_model, default_prompt, default_template, default_enabled):
        """UI要素を作成"""
        # 設定項目
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ユーザーID
        tk.Label(main_frame, text="ユーザーID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.user_id_var = tk.StringVar(value=existing_config["user_id"] if existing_config else "")
        user_id_entry = tk.Entry(main_frame, textvariable=self.user_id_var, width=30)
        user_id_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        user_id_entry.bind('<FocusOut>', self.on_user_id_changed)
        
        # ニックネーム取得ボタン
        tk.Button(main_frame, text="ニックネーム取得", 
                 command=self.fetch_nickname).grid(row=0, column=2, padx=5)
        
        # 表示名
        tk.Label(main_frame, text="表示名:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.display_name_var = tk.StringVar(value=existing_config["display_name"] if existing_config else "")
        tk.Entry(main_frame, textvariable=self.display_name_var, width=30).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 分析有効/無効
        self.analysis_enabled_var = tk.BooleanVar(value=existing_config["analysis_enabled"] if existing_config else default_enabled)
        tk.Checkbutton(main_frame, text="AI分析を有効にする", variable=self.analysis_enabled_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # AIモデル選択
        tk.Label(main_frame, text="分析AIモデル:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.ai_model_var = tk.StringVar(value=existing_config["analysis_ai_model"] if existing_config else default_ai_model)
        ai_model_combo = ttk.Combobox(main_frame, textvariable=self.ai_model_var,
                                    values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                    state="readonly")
        ai_model_combo.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 分析プロンプト
        tk.Label(main_frame, text="分析プロンプト:").grid(row=4, column=0, sticky=tk.W+tk.N, padx=5, pady=5)
        self.analysis_prompt_text = tk.Text(main_frame, height=8, wrap=tk.WORD)
        self.analysis_prompt_text.grid(row=4, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        prompt_value = existing_config["analysis_prompt"] if existing_config else default_prompt
        self.analysis_prompt_text.insert(1.0, prompt_value)
        
        # テンプレート
        tk.Label(main_frame, text="テンプレートファイル:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.template_var = tk.StringVar(value=existing_config["template"] if existing_config else default_template)
        tk.Entry(main_frame, textvariable=self.template_var, width=30).grid(row=5, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        
        # 説明
        tk.Label(main_frame, text="説明・メモ:").grid(row=6, column=0, sticky=tk.W+tk.N, padx=5, pady=5)
        self.description_text = tk.Text(main_frame, height=4, wrap=tk.WORD)
        self.description_text.grid(row=6, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        description_value = existing_config["description"] if existing_config else ""
        self.description_text.insert(1.0, description_value)
        
        # ボタン
        button_frame = tk.Frame(main_frame)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        tk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
        
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(6, weight=1)

    def on_user_id_changed(self, event):
        """ユーザーIDが変更されたときの処理"""
        user_id = self.user_id_var.get().strip()
        if user_id and user_id.isdigit():
            if hasattr(self, 'nickname_timer'):
                self.dialog.after_cancel(self.nickname_timer)
            self.nickname_timer = self.dialog.after(1000, lambda: self.fetch_nickname_async(user_id, force=False))

    def fetch_nickname(self):
        """ニックネーム取得ボタンのコールバック"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            messagebox.showwarning("警告", "ユーザーIDを入力してください")
            return
        
        if not user_id.isdigit():
            messagebox.showwarning("警告", "正しいユーザーIDを入力してください")
            return
        
        self.fetch_nickname_async(user_id, force=True)

    def fetch_nickname_async(self, user_id, force=False):
        """非同期でニックネーム取得"""
        if hasattr(self, 'nickname_fetching') and self.nickname_fetching and not force:
            return
        
        if hasattr(self, 'nickname_fetch_thread') and self.nickname_fetch_thread and self.nickname_fetch_thread.is_alive():
            if not force:
                return
        
        self.nickname_fetching = True
        
        def fetch_thread():
            try:
                from utils import get_user_nickname_with_cache
                nickname = get_user_nickname_with_cache(user_id)
                
                self.dialog.after(0, lambda: self.update_display_name_safe(nickname, user_id, force))
                
            except Exception as e:
                print(f"ニックネーム取得エラー (ID: {user_id}): {e}")
                if force:
                    self.dialog.after(0, lambda: messagebox.showerror("エラー", f"ニックネーム取得に失敗しました: {e}"))
            finally:
                self.nickname_fetching = False
        
        self.nickname_fetch_thread = threading.Thread(target=fetch_thread, daemon=True)
        self.nickname_fetch_thread.start()

    def update_display_name_safe(self, nickname, user_id, force=False):
        """安全に表示名を更新"""
        current_user_id = self.user_id_var.get().strip()
        if current_user_id != user_id:
            return
        
        if nickname:
            current_name = self.display_name_var.get().strip()
            if not current_name:
                self.display_name_var.set(nickname)
                if force:
                    messagebox.showinfo("成功", f"ニックネーム「{nickname}」を取得しました")
            elif force:
                if messagebox.askyesno("確認", f"表示名を「{nickname}」に更新しますか？\n現在: {current_name}"):
                    self.display_name_var.set(nickname)
        elif force:
            messagebox.showwarning("警告", "ニックネームを取得できませんでした")

    def ok_clicked(self):
        user_id = self.user_id_var.get().strip()
        if not user_id:
            messagebox.showerror("エラー", "ユーザーIDを入力してください")
            return
        
        self.result = {
            "user_id": user_id,
            "display_name": self.display_name_var.get().strip(),
            "analysis_enabled": self.analysis_enabled_var.get(),
            "analysis_ai_model": self.ai_model_var.get(),
            "analysis_prompt": self.analysis_prompt_text.get(1.0, tk.END).strip(),
            "template": self.template_var.get().strip(),
            "description": self.description_text.get(1.0, tk.END).strip(),
            "tags": []
        }
        self.dialog.destroy()

    def cancel_clicked(self):
        self.result = None
        self.dialog.destroy()