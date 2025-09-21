# create_user_config.py
import argparse, os, json, datetime
from copy import deepcopy

TEMPLATE_PATH = os.path.join('config', 'users', 'default_template.json')
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

def _build_user_config(template: dict, account_id: str, display_name: str) -> dict:
    cfg = deepcopy(template) if template else {}
    # 動的差し込み
    cfg['account_id'] = account_id
    cfg['display_name'] = display_name
    cfg.setdefault('basic_settings', {})
    cfg['basic_settings']['account_id'] = account_id

    # スペシャルユーザー 2525 をテスト用として固定で入れる
    cfg.setdefault('special_users', [])
    if '2525' not in cfg['special_users']:
        cfg['special_users'] = ['2525']  # テスト運用なので上書きで一本化

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
    args = ap.parse_args()

    os.makedirs(OUT_DIR, exist_ok=True)

    template = {}
    if os.path.exists(TEMPLATE_PATH):
        template = _load_json(TEMPLATE_PATH)

    user_cfg = _build_user_config(template, args.account_id, args.display_name)

    out_path = os.path.join(OUT_DIR, f'{args.account_id}.json')
    with open(out_path, 'w', encoding='utf-8') as f:
        json.dump(user_cfg, f, ensure_ascii=False, indent=2)
    print(f'ユーザー設定生成: {out_path}')
    return 0

if __name__ == '__main__':
    raise SystemExit(main())
