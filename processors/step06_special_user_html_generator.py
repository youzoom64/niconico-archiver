import json
import os
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step06: HTML生成とスペシャルユーザー処理"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step06 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. 統合JSONファイル読み込み
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        
        # 3. NCVのXMLファイルを解析してスペシャルユーザーを検索
        special_users = get_special_users_from_config(config)
        found_special_users = find_special_users_in_ncv(broadcast_data.get('ncv_xml_path', ''), special_users)
        
        # 4. スペシャルユーザーが見つかった場合、ページを生成
        if found_special_users:
            for user_data in found_special_users:
                create_special_user_pages(user_data, broadcast_data, broadcast_dir, lv_value, config)  # configを追加
                
        print(f"Step06 完了: {lv_value} - 検出スペシャルユーザー数: {len(found_special_users)}")
        return {"special_users_found": len(found_special_users), "users": [u['user_id'] for u in found_special_users]}
        
    except Exception as e:
        print(f"Step06 エラー: {str(e)}")
        raise

def load_broadcast_data(broadcast_dir, lv_value):
    """統合JSONファイルを読み込み"""
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise Exception(f"統合JSONファイルが見つかりません: {json_path}")

def get_special_users_from_config(config):
    """設定からスペシャルユーザーリストを取得（詳細設定対応）"""
    # 新しい詳細設定から取得
    special_users_config = config.get("special_users_config", {})
    detailed_users = special_users_config.get("users", {})
    
    # 詳細設定があるユーザーIDを取得
    user_ids_from_detailed = list(detailed_users.keys())
    
    # 従来のsimple listも取得（後方互換性）
    user_ids_from_simple = config.get("special_users", [])
    
    # 両方をマージ（重複排除）
    all_user_ids = list(set(user_ids_from_detailed + user_ids_from_simple))
    
    print(f"詳細設定ユーザー: {user_ids_from_detailed}")
    print(f"シンプル設定ユーザー: {user_ids_from_simple}")
    print(f"統合ユーザーリスト: {all_user_ids}")
    
    return all_user_ids

def get_user_detail_config(config, user_id):
    """個別ユーザーの詳細設定を取得"""
    special_users_config = config.get("special_users_config", {})
    detailed_users = special_users_config.get("users", {})
    
    if user_id in detailed_users:
        return detailed_users[user_id]
    
    # デフォルト設定を返す
    return {
        "user_id": user_id,
        "display_name": f"ユーザー{user_id}",
        "analysis_enabled": special_users_config.get("default_analysis_enabled", True),
        "analysis_ai_model": special_users_config.get("default_analysis_ai_model", "openai-gpt4o"),
        "analysis_prompt": special_users_config.get("default_analysis_prompt", ""),
        "template": special_users_config.get("default_template", "user_detail.html"),
        "description": "",
        "tags": []
    }


def find_special_users_in_ncv(ncv_xml_path, special_users):
   """NCVのXMLファイルからスペシャルユーザーを検索"""
   if not ncv_xml_path or not os.path.exists(ncv_xml_path):
       print("NCVのXMLファイルが見つかりません")
       return []
   
   try:
       tree = ET.parse(ncv_xml_path)
       root = tree.getroot()
       
       found_users = {}
       
       # LiveCommentDataArrayから各chatを解析（名前空間対応）
       chat_elements = root.findall('.//chat')
       if not chat_elements:
           # 名前空間がある場合の検索
           namespaces = {'ncv': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}
           chat_elements = root.findall('.//ncv:chat', namespaces)
       
       print(f"検出したchat要素数: {len(chat_elements)}")
       
       for chat in chat_elements:
           user_id = chat.get('user_id', '')
           user_name = chat.get('name', '')
           
           # user_idから実際のIDを抽出（匿名ユーザーは除外）
           actual_user_id = extract_user_id(user_id)
           
           if actual_user_id and actual_user_id in special_users:
               if actual_user_id not in found_users:
                   found_users[actual_user_id] = {
                       'user_id': actual_user_id,
                       'user_name': user_name or f"ユーザー{actual_user_id}",
                       'comments': []
                   }
               
               # コメント情報を追加
               comment_data = {
                   'no': chat.get('no', ''),
                   'date': chat.get('date', ''),
                   'vpos': chat.get('vpos', ''),
                   'text': chat.text or '',
                   'premium': chat.get('premium', ''),
                   'name': chat.get('name', '')
               }
               found_users[actual_user_id]['comments'].append(comment_data)
               print(f"スペシャルユーザーコメント検出: {actual_user_id} - {comment_data['text'][:50]}")
       
       print(f"スペシャルユーザー検出: {list(found_users.keys())}")
       return list(found_users.values())
       
   except Exception as e:
       print(f"NCVのXML解析エラー: {str(e)}")
       import traceback
       traceback.print_exc()
       return []

def extract_user_id(user_id_str):
    """user_id文字列から実際のユーザーIDを抽出"""
    if not user_id_str:
        return None
    
    # 匿名ユーザー（a:〜、o:〜）は除外
    if user_id_str.startswith(('a:', 'o:')):
        return None
    
    # 数字のみのIDを返す
    if user_id_str.isdigit():
        return user_id_str
    
    return None

def create_special_user_pages(user_data, broadcast_data, broadcast_dir, lv_value, config=None):
    """スペシャルユーザーの一覧ページと個別ページを生成"""
    try:
        user_id = user_data['user_id']
        user_name = user_data['user_name']
        comments = user_data['comments']
        
        print(f"スペシャルユーザーページ生成中: {user_id} ({user_name})")
        
        # テンプレートディレクトリ
        template_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'templates')
        
        # アカウントディレクトリ直下にユーザーディレクトリ作成
        account_dir = os.path.dirname(broadcast_dir)
        user_output_dir = os.path.join(account_dir, f"special_user_{user_id}")
        os.makedirs(user_output_dir, exist_ok=True)
        
        # CSS/JSファイルをコピー
        copy_static_files(template_dir, user_output_dir)
        
        # 1. 個別ページ生成（configを渡す）
        create_user_detail_page(user_data, broadcast_data, template_dir, user_output_dir, lv_value, config)
        
        # 2. 一覧ページ生成または更新
        update_user_list_page(user_data, broadcast_data, template_dir, user_output_dir, lv_value)
        
        print(f"スペシャルユーザーページ生成完了: {user_output_dir}")
        
    except Exception as e:
        print(f"スペシャルユーザーページ生成エラー: {str(e)}")
        raise

def generate_analysis_text_with_config(comments, config, user_id):
    """詳細設定を考慮した分析テキストを生成"""
    user_detail_config = get_user_detail_config(config, user_id)
    
    if not user_detail_config.get("analysis_enabled", True):
        return "このユーザーの分析は無効化されています。"
    
    # 基本的な分析は既存の関数を使用
    basic_analysis = generate_analysis_text(comments)
    
    # 詳細設定がある場合は追加情報を付加
    if user_detail_config.get("description"):
        basic_analysis += f"<br><br><strong>メモ:</strong><br>{user_detail_config['description']}"
    
    return basic_analysis



def update_user_list_page(user_data, broadcast_data, template_dir, output_dir, lv_value):
    """一覧ページを生成または更新（複数放送対応）"""
    template_path = os.path.join(template_dir, 'user_list.html')
    list_file_path = os.path.join(output_dir, f"{user_data['user_id']}_list.html")
    
    # 既存の一覧ページがある場合は読み込み
    existing_items = []
    if os.path.exists(list_file_path):
        existing_items = load_existing_broadcast_items(list_file_path)
    
    # 新しい放送アイテムを追加
    new_item = generate_broadcast_items(user_data, broadcast_data, lv_value)
    existing_items.append(new_item)
    
    # テンプレートを読み込み
    if not os.path.exists(template_path):
        print(f"テンプレートファイルが見つかりません: {template_path}")
        return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # 全ての放送アイテムを結合
    all_items = '\n'.join(existing_items)
    
    # テンプレート変数を置換
    html_content = template.replace('{{broadcaster_name}}', user_data['user_name'])
    html_content = html_content.replace('{{thumbnail_url}}', get_user_icon_path(user_data['user_id']))
    html_content = html_content.replace('{{broadcast_items}}', all_items)
    
    # ファイル保存
    with open(list_file_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"一覧ページ更新: {list_file_path}")

def load_existing_broadcast_items(list_file_path):
    """既存の一覧ページから放送アイテムを抽出"""
    try:
        with open(list_file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # 簡単な方法：既存のlink-itemを抽出
        import re
        pattern = r'<div class="link-item">.*?</div>'
        matches = re.findall(pattern, content, re.DOTALL)
        return matches
        
    except Exception as e:
        print(f"既存アイテム読み込みエラー: {str(e)}")
        return []

def copy_static_files(template_dir, output_dir):
    """CSS/JSファイルを出力ディレクトリにコピー"""
    try:
        # cssディレクトリをコピー
        css_src = os.path.join(template_dir, 'css')
        css_dst = os.path.join(output_dir, 'css')
        if os.path.exists(css_src):
            shutil.copytree(css_src, css_dst, dirs_exist_ok=True)
        
        # jsディレクトリをコピー
        js_src = os.path.join(template_dir, 'js')
        js_dst = os.path.join(output_dir, 'js')
        if os.path.exists(js_src):
            shutil.copytree(js_src, js_dst, dirs_exist_ok=True)
        
        # assetsディレクトリをコピー
        assets_src = os.path.join(template_dir, 'assets')
        assets_dst = os.path.join(output_dir, 'assets')
        if os.path.exists(assets_src):
            shutil.copytree(assets_src, assets_dst, dirs_exist_ok=True)
            
    except Exception as e:
        print(f"静的ファイルコピーエラー: {str(e)}")


def create_user_detail_page(user_data, broadcast_data, template_dir, output_dir, lv_value, config=None):
    """個別ユーザーページを生成"""
    user_id = user_data['user_id']
    
    # ユーザーの詳細設定を取得
    if config:
        user_detail_config = get_user_detail_config(config, user_id)
        template_name = user_detail_config.get("template", "user_detail.html")
        print(f"ユーザー {user_id} のテンプレート: {template_name}")
    else:
        template_name = "user_detail.html"
    
    template_path = os.path.join(template_dir, template_name)
    if not os.path.exists(template_path):
        print(f"テンプレートファイルが見つかりません: {template_path}")
        # フォールバックでデフォルトテンプレートを使用
        template_path = os.path.join(template_dir, 'user_detail.html')
        if not os.path.exists(template_path):
            return
    
    with open(template_path, 'r', encoding='utf-8') as f:
        template = f.read()
    
    # コメント行を生成
    comment_rows = generate_comment_rows(user_data['comments'])
    
    # 分析テキストを生成（詳細設定を考慮）
    if config:
        analysis_text = generate_analysis_text_with_config(user_data['comments'], config, user_id)
    else:
        analysis_text = generate_analysis_text(user_data['comments'])
    
    # テンプレート変数を置換
    html_content = template.replace('{{broadcast_title}}', broadcast_data.get('live_title', 'タイトル不明'))
    html_content = html_content.replace('{{start_time}}', format_start_time(broadcast_data.get('start_time', '')))
    html_content = html_content.replace('{{user_avatar}}', get_user_icon_path(user_data['user_id']))

    html_content = html_content.replace('{{user_name}}', user_data['user_name'])
    html_content = html_content.replace('{{user_profile_url}}', f"https://www.nicovideo.jp/user/{user_data['user_id']}")
    html_content = html_content.replace('{{user_id}}', user_data['user_id'])
    html_content = html_content.replace('{{comment_rows}}', comment_rows)
    html_content = html_content.replace('{{analysis_text}}', analysis_text)
    
    # ファイル保存
    output_path = os.path.join(output_dir, f"{user_data['user_id']}_{lv_value}_detail.html")
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"個別ページ生成: {output_path}")
def get_user_icon_path(user_id):
    """ニコニコ動画のユーザーアイコンパスを生成"""
    if len(user_id) <= 4:
        # 4桁以下の場合はディレクトリなし
        return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{user_id}.jpg"
    else:
        # 5桁以上の場合は下4桁を除いた部分がディレクトリ
        path_prefix = user_id[:-4]
        return f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{path_prefix}/{user_id}.jpg"


def generate_comment_rows(comments):
    """コメントテーブルの行を生成"""
    rows = []
    for i, comment in enumerate(comments, 1):
        vpos = int(comment.get('vpos', 0))
        time_str = format_vpos_to_time(vpos)
        date_str = format_unix_time(comment.get('date', ''))
        
        row = f'''
        <tr>
            <td>{i}</td>
            <td>{time_str}</td>
            <td>{date_str}</td>
            <td><b style="font-size: 25px;">{escape_html(comment.get('text', ''))}</b></td>
        </tr>'''
        rows.append(row)
    
    return '\n'.join(rows)

def generate_analysis_text(comments):
    """簡単な分析テキストを生成"""
    if not comments:
        return "コメントがありません。"
    
    total_comments = len(comments)
    total_chars = sum(len(comment.get('text', '')) for comment in comments)
    avg_chars = total_chars / total_comments if total_comments > 0 else 0
    
    analysis = f"""
        - 総コメント数: {total_comments}件<br><br>
        - 平均文字数: {avg_chars:.1f}文字<br><br>
        - コメント傾向: 配信に対して積極的に参加している様子が伺えます。<br><br>
        - 参加時間帯: 配信全体を通してコメントを投稿しています。<br><br>
    """
    
    return analysis

def generate_broadcast_items(user_data, broadcast_data, lv_value):
    """放送アイテムリストを生成"""
    if not user_data['comments']:
        return "<p>コメントがありません</p>"
    
    first_comment = user_data['comments'][0].get('text', '') if user_data['comments'] else ''
    last_comment = user_data['comments'][-1].get('text', '') if user_data['comments'] else ''
    
    item = f'''
        <div class="link-item">
            <p class="separator">―――――――――――――――――――――――――――――――――――――――――――</p>
            <p class="start-time">開始時間: {format_start_time(broadcast_data.get('start_time', ''))}</p>
            <div class="comment-preview">
                <p>初コメ: {escape_html(first_comment)}</p>
                <p>最終コメ: {escape_html(last_comment)}</p>
            </div>
            
            <button onclick="toggleDiv('chat-data-{lv_value}')" class="toggle-button">
                コメントを表示:非表示
            </button>
            
            <div class="chat-data" id="chat-data-{lv_value}" style="display: none">
                <table border="1">
                    <thead>
                        <tr>
                            <th>コメント番号</th>
                            <th>放送内時間</th>
                            <th>日時</th>
                            <th>コメント内容</th>
                        </tr>
                    </thead>
                    <tbody>
                        {generate_comment_rows(user_data['comments'])}
                    </tbody>
                </table>
            </div>
            
            <div class="broadcast-link">
                <a href="{user_data['user_id']}_{lv_value}_detail.html">{broadcast_data.get('live_title', 'タイトル不明')}: における{user_data['user_name']}のコメント分析</a>
            </div>
        </div>
    '''
    
    return item

def format_vpos_to_time(vpos):
    """vpos（1/100秒単位）を時間表記に変換"""
    seconds = vpos // 100
    minutes = seconds // 60
    hours = minutes // 60
    
    return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"

def format_unix_time(unix_time_str):
    """UNIX時間を日時表記に変換"""
    try:
        unix_time = int(unix_time_str)
        dt = datetime.fromtimestamp(unix_time)
        return dt.strftime('%Y-%m-%d %H:%M:%S')
    except:
        return unix_time_str

def format_start_time(start_time_str):
    """開始時間をフォーマット"""
    try:
        unix_time = int(start_time_str)
        dt = datetime.fromtimestamp(unix_time)
        return dt.strftime('%Y/%m/%d(%a) %H:%M')
    except:
        return start_time_str

def escape_html(text):
    """HTMLエスケープ"""
    if not text:
        return ""
    return (text.replace('&', '&amp;')
                .replace('<', '&lt;')
                .replace('>', '&gt;')
                .replace('"', '&quot;')
                .replace("'", '&#x27;'))