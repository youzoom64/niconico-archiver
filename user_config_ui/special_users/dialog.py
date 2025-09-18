import tkinter as tk
from tkinter import ttk, messagebox
from ..dialog_base import BaseDialog

class SpecialUserConfigDialog(BaseDialog):
    """スペシャルユーザー設定ダイアログ"""
    
    def __init__(self, parent, existing_config, default_ai_model, default_prompt, default_template, default_enabled):
        super().__init__(parent, "スペシャルユーザー設定", "600x600")
        
        self.create_ui(existing_config, default_ai_model, default_prompt, default_template, default_enabled)
        self.wait_for_result()
    
    def create_ui(self, existing_config, default_ai_model, default_prompt, default_template, default_enabled):
        """UI要素を作成"""
        main_frame = tk.Frame(self.dialog)
        main_frame.pack(fill=tk.BOTH, expand=True, padx=10, pady=10)
        
        # ユーザーID入力
        self._create_user_id_section(main_frame, existing_config)
        
        # 表示名入力
        self._create_display_name_section(main_frame, existing_config)
        
        # 分析設定
        self._create_analysis_settings(main_frame, existing_config, default_ai_model, default_enabled)
        
        # プロンプト設定
        self._create_prompt_section(main_frame, existing_config, default_prompt)
        
        # テンプレート設定
        self._create_template_section(main_frame, existing_config, default_template)
        
        # 説明欄
        self._create_description_section(main_frame, existing_config)
        
        # ボタン
        self._create_buttons(main_frame)
        
        # レイアウト調整
        main_frame.columnconfigure(1, weight=1)
        main_frame.rowconfigure(4, weight=1)
        main_frame.rowconfigure(6, weight=1)
    
    def _create_user_id_section(self, parent, existing_config):
        """ユーザーID入力セクション"""
        tk.Label(parent, text="ユーザーID:").grid(row=0, column=0, sticky=tk.W, padx=5, pady=5)
        self.user_id_var = tk.StringVar(value=existing_config["user_id"] if existing_config else "")
        user_id_entry = tk.Entry(parent, textvariable=self.user_id_var, width=30)
        user_id_entry.grid(row=0, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
        user_id_entry.bind('<FocusOut>', self.on_user_id_changed)
        
        # ニックネーム取得ボタン
        tk.Button(parent, text="ニックネーム取得", 
                 command=self.fetch_nickname).grid(row=0, column=2, padx=5)
    
    def _create_display_name_section(self, parent, existing_config):
        """表示名入力セクション"""
        tk.Label(parent, text="表示名:").grid(row=1, column=0, sticky=tk.W, padx=5, pady=5)
        self.display_name_var = tk.StringVar(value=existing_config["display_name"] if existing_config else "")
        tk.Entry(parent, textvariable=self.display_name_var, width=30).grid(row=1, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
    
    def _create_analysis_settings(self, parent, existing_config, default_ai_model, default_enabled):
        """分析設定セクション"""
        # 分析有効/無効
        self.analysis_enabled_var = tk.BooleanVar(value=existing_config["analysis_enabled"] if existing_config else default_enabled)
        tk.Checkbutton(parent, text="AI分析を有効にする", variable=self.analysis_enabled_var).grid(row=2, column=0, columnspan=2, sticky=tk.W, padx=5, pady=5)
        
        # AIモデル選択
        tk.Label(parent, text="分析AIモデル:").grid(row=3, column=0, sticky=tk.W, padx=5, pady=5)
        self.ai_model_var = tk.StringVar(value=existing_config["analysis_ai_model"] if existing_config else default_ai_model)
        ai_model_combo = ttk.Combobox(parent, textvariable=self.ai_model_var,
                                    values=["openai-gpt4o", "google-gemini-2.5-flash"],
                                    state="readonly")
        ai_model_combo.grid(row=3, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
    
    def _create_prompt_section(self, parent, existing_config, default_prompt):
        """プロンプト設定セクション"""
        tk.Label(parent, text="分析プロンプト:").grid(row=4, column=0, sticky=tk.W+tk.N, padx=5, pady=5)
        self.analysis_prompt_text = tk.Text(parent, height=8, wrap=tk.WORD)
        self.analysis_prompt_text.grid(row=4, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        prompt_value = existing_config["analysis_prompt"] if existing_config else default_prompt
        self.analysis_prompt_text.insert(1.0, prompt_value)
    
    def _create_template_section(self, parent, existing_config, default_template):
        """テンプレート設定セクション"""
        tk.Label(parent, text="テンプレートファイル:").grid(row=5, column=0, sticky=tk.W, padx=5, pady=5)
        self.template_var = tk.StringVar(value=existing_config["template"] if existing_config else default_template)
        tk.Entry(parent, textvariable=self.template_var, width=30).grid(row=5, column=1, sticky=tk.W+tk.E, padx=5, pady=5)
    
    def _create_description_section(self, parent, existing_config):
        """説明欄セクション"""
        tk.Label(parent, text="説明・メモ:").grid(row=6, column=0, sticky=tk.W+tk.N, padx=5, pady=5)
        self.description_text = tk.Text(parent, height=4, wrap=tk.WORD)
        self.description_text.grid(row=6, column=1, sticky=tk.W+tk.E+tk.N+tk.S, padx=5, pady=5)
        
        description_value = existing_config["description"] if existing_config else ""
        self.description_text.insert(1.0, description_value)
    
    def _create_buttons(self, parent):
        """ボタンセクション"""
        button_frame = tk.Frame(parent)
        button_frame.grid(row=7, column=0, columnspan=2, pady=10)
        
        tk.Button(button_frame, text="OK", command=self.ok_clicked).pack(side=tk.LEFT, padx=5)
        tk.Button(button_frame, text="キャンセル", command=self.cancel_clicked).pack(side=tk.LEFT, padx=5)
    
    def on_user_id_changed(self, event):
        """ユーザーIDが変更されたときの処理"""
        user_id = self.user_id_var.get().strip()
        if user_id and user_id.isdigit():
            if hasattr(self, 'nickname_timer'):
                self.dialog.after_cancel(self.nickname_timer)
            self.nickname_timer = self.dialog.after(1000, lambda: self.fetch_nickname_async(user_id, force=False, callback=self.update_display_name_safe))
    
    def fetch_nickname(self):
        """ニックネーム取得ボタンのコールバック"""
        user_id = self.user_id_var.get().strip()
        if not user_id:
            messagebox.showwarning("警告", "ユーザーIDを入力してください")
            return
        
        if not user_id.isdigit():
            messagebox.showwarning("警告", "正しいユーザーIDを入力してください")
            return
        
        self.fetch_nickname_async(user_id, force=True, callback=self.update_display_name_safe)
    
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
        """OK ボタンのクリック処理"""
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