
from .window_manager import WindowManager

# 後方互換性のためUserConfigWindowとしてエクスポート
UserConfigWindow = WindowManager

__all__ = ['WindowManager', 'UserConfigWindow']