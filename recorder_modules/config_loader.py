import json
import os
import logging
from typing import Optional, Dict, Any

DEBUGLOG = logging.getLogger(__name__)

def sanitize_path_component(name: str) -> str:
    invalid = '<>:"/\\|?*'
    table = str.maketrans({ch: '_' for ch in invalid})
    out = name.translate(table).strip().rstrip('.')
    return out or "unknown"

def load_user_config(account_id: str) -> Optional[Dict[str, Any]]:
    """ユーザー設定を読み込み"""
    user_path = os.path.join('config', 'users', f'{account_id}.json')
    tmpl_path = os.path.join('config', 'users', 'default_template.json')

    def _deep_merge(base: dict, override: dict) -> dict:
        from copy import deepcopy
        out = deepcopy(base) if base else {}
        for k, v in (override or {}).items():
            if isinstance(v, dict) and isinstance(out.get(k), dict):
                out[k] = _deep_merge(out[k], v)
            else:
                out[k] = v
        return out

    try:
        user = {}
        tmpl = {}
        if os.path.exists(tmpl_path):
            with open(tmpl_path, 'r', encoding='utf-8') as f:
                tmpl = json.load(f)
        if os.path.exists(user_path):
            with open(user_path, 'r', encoding='utf-8') as f:
                user = json.load(f)

        if tmpl:
            cfg = _deep_merge(tmpl, user)
        else:
            cfg = user

        if cfg:
            DEBUGLOG.info(f"ユーザー設定読込成功: {user_path if user else '(テンプレのみ)'}")
            return cfg
        else:
            DEBUGLOG.warning(f"ユーザー設定が見つかりません: {user_path}")
            return None
    except Exception as e:
        DEBUGLOG.error(f"ユーザー設定の読込に失敗: {account_id}.json / {e}")
        return None

def load_global_config() -> Dict[str, Any]:
    """グローバル設定読み込み"""
    path = os.path.join("config", "global_config.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"system": {"download_directory": "Downloads"}}

def ensure_output_dir(platform_directory: str, account_id: str, display_name: str) -> str:
    """保存ディレクトリの生成"""
    safe_name = sanitize_path_component(display_name)
    base = platform_directory or os.path.abspath(os.path.join('.', 'rec'))
    out = os.path.join(base, f"{account_id}_{safe_name}")
    try:
        os.makedirs(out, exist_ok=True)
        DEBUGLOG.info(f"保存ディレクトリ準備完了: {out}")
    except Exception as e:
        DEBUGLOG.error(f"保存ディレクトリ作成失敗: {out} / {e}")
        raise
    return out