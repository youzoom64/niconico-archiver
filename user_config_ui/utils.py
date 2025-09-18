import tkinter as tk
from tkinter import filedialog, messagebox
import os

class UIUtils:
    @staticmethod
    def browse_directory(parent, target_var):
        """フォルダ選択ダイアログを表示"""
        current_path = target_var.get()
        initial_dir = current_path if current_path and os.path.exists(current_path) else os.getcwd()
        
        selected_dir = filedialog.askdirectory(
            title="フォルダを選択してください",
            initialdir=initial_dir
        )
        
        if selected_dir:
            current_dir = os.getcwd()
            try:
                rel_path = os.path.relpath(selected_dir, current_dir)
                
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
                target_var.set(selected_dir)
    
    @staticmethod
    def create_scrollable_frame(parent):
        """スクロール可能フレームを作成"""
        canvas = tk.Canvas(parent)
        scrollbar = tk.Scrollbar(parent, orient="vertical", command=canvas.yview)
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
        
        return scrollable_frame
    
    @staticmethod
    def setup_mousewheel(canvas):
        """マウスホイール設定"""
        def _on_mousewheel(event):
            canvas.yview_scroll(int(-1*(event.delta/120)), "units")
        
        def _bind_to_mousewheel(event):
            canvas.bind_all("<MouseWheel>", _on_mousewheel)
        
        def _unbind_from_mousewheel(event):
            canvas.unbind_all("<MouseWheel>")
        
        canvas.bind('<Enter>', _bind_to_mousewheel)
        canvas.bind('<Leave>', _unbind_from_mousewheel)