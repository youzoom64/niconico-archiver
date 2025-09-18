from user_config_ui import UserConfigWindow

# 統合管理スクリプトとして機能
# 既存のインポートをすべて新しいUIクラスにリダイレクト

# 既存のコードとの互換性維持
UserConfigWindow = UserConfigWindow

if __name__ == "__main__":
    # テスト用のスタンドアロン実行
    import tkinter as tk
    from config_manager import ConfigManager
    
    root = tk.Tk()
    root.withdraw()  # メインウィンドウを非表示
    
    config_manager = ConfigManager()
    
    def dummy_refresh():
        print("refresh callback called")
    
    app = UserConfigWindow(root, config_manager, dummy_refresh)
    root.mainloop()