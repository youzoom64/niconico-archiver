# create_user_config.py
import argparse, os, json, datetime
from copy import deepcopy

OUT_DIR = os.path.join('config', 'users')

def _load_json(path):
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _deep_merge(base: dict, override: dict) -> dict:
    out = deepcopy(base)
    for k, v in (override or {}).items():
        if isinstance(v, dict) and isinstance(out.get(k), dict):
            out[k] = _deep_merge(out[k], v)
        else:
            out[k] = v
    return out

def load_global_config():
    path = os.path.join("config", "global_config.json")
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {"system": {"download_directory": "Downloads"}}

def _build_user_config(template: dict, global_cfg: dict, account_id: str, display_name: str, existing_cfg: dict = None) -> dict:
    # 既存設定があればそれをベースにする
    if existing_cfg:
        cfg = deepcopy(existing_cfg)
        DEBUGLOG.info("既存設定をベースに更新")
    else:
        cfg = deepcopy(template) if template else {}
        DEBUGLOG.info("新規設定を作成")
    
    # 基本情報は常に更新
    cfg['account_id'] = account_id
    cfg['display_name'] = display_name
    cfg.setdefault('basic_settings', {})
    cfg['basic_settings']['account_id'] = account_id
    cfg['basic_settings'].setdefault('platform_directory', 'rec')
    cfg['basic_settings'].setdefault('ncv_directory', 'ncv')
    
    # server_settingsをグローバル設定から追加/更新
    if 'server_settings' in global_cfg:
        cfg['server_settings'] = deepcopy(global_cfg['server_settings'])
        DEBUGLOG.info("server_settingsを追加/更新")
    
    # スペシャルユーザー設定は既存設定を尊重
    cfg.setdefault('special_users', [])
    if '2525' not in cfg['special_users']:
        cfg['special_users'].append('2525')

    su = cfg.setdefault('special_users_config', {})
    users = su.setdefault('users', {})
    if '2525' not in users:
        users['2525'] = {
            "user_id": "2525",
            "display_name": "スペシャルユーザー2525",
            "analysis_enabled": su.get('default_analysis_enabled', True),
            "analysis_ai_model": su.get('default_analysis_ai_model', "openai-gpt4o"),
            "analysis_prompt": su.get('default_analysis_prompt', "以下のユーザーのコメント履歴を分析してください。"),
            "template": su.get('default_template', "user_detail.html"),
            "description": "",
            "tags": []
        }

    cfg['last_updated'] = datetime.datetime.now().isoformat()
    return cfg

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-lv_no', required=True)
    ap.add_argument('-account_id', required=True)
    ap.add_argument('-lv_title', required=True)
    ap.add_argument('-display_name', required=True)
    ap.add_argument('-tab_id', required=True)
    ap.add_argument('-start_time', required=True)
    ap.add_argument('-update_existing', action='store_true', help='既存設定を更新')
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # グローバル設定を読み込み
    global_cfg = load_global_config()

    # 既存設定があれば読み込み
    existing_cfg = None
    out_path = os.path.join(OUT_DIR, f'{args.account_id}.json')
    if args.update_existing and os.path.exists(out_path):
        existing_cfg = _load_json(out_path)

    # テンプレート読み込み
    template = {}
    template_path = os.path.join('config', 'users', 'default_template.json')
    if os.path.exists(template_path):
        template = _load_json(template_path)

    user_cfg = _build_user_config(template, global_cfg, args.account_id, args.display_name, existing_cfg)

    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(user_cfg, f, ensure_ascii=False, indent=2)
    
    action = "更新" if existing_cfg else "生成"
    print(f'ユーザー設定{action}: {out_path}')
    return 0

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('-lv_no', required=True)
    ap.add_argument('-account_id', required=True)
    ap.add_argument('-lv_title', required=True)
    ap.add_argument('-display_name', required=True)
    ap.add_argument('-tab_id', required=True)
    ap.add_argument('-start_time', required=True)
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    # グローバル設定を読み込み
    global_cfg = load_global_config()

    # テンプレート読み込み（defaults.pyの内容を使用）
    template = {}
    template_path = os.path.join('config', 'users', 'default_template.json')
    if os.path.exists(template_path):
        template = _load_json(template_path)

    user_cfg = _build_user_config(template, global_cfg, args.account_id, args.display_name)

    out_path = os.path.join(OUT_DIR, f'{args.account_id}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(user_cfg, f, ensure_ascii=False, indent=2)
    print(f'ユーザー設定生成: {out_path}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())