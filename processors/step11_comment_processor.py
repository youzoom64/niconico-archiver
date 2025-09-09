import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step11: コメントデータ処理"""
    try:
        lv_value = pipeline_data['lv_value']
        
        print(f"Step11 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. 統合JSONからNCVのXMLパスとStartTimeを取得
        broadcast_data = load_broadcast_data(broadcast_dir, lv_value)
        ncv_xml_path = broadcast_data.get('ncv_xml_path', '')
        start_time = int(broadcast_data.get('start_time', 0))
        
        if not ncv_xml_path or not os.path.exists(ncv_xml_path):
            raise Exception(f"NCVのXMLファイルが見つかりません: {ncv_xml_path}")
        
        # 3. XMLからコメントデータを解析
        comments_data = parse_comments_from_xml(ncv_xml_path, start_time)
        
        # 4. コメントランキングを生成
        ranking_data = generate_comment_ranking(comments_data)
        
        # 5. ファイル保存
        comments_file = save_comments_json(broadcast_dir, lv_value, comments_data)
        ranking_file = save_ranking_json(broadcast_dir, lv_value, ranking_data)
        
        print(f"Step11 完了: {lv_value} - コメント数: {len(comments_data)}, ランキング: {len(ranking_data)}")
        return {
            "comments_count": len(comments_data),
            "ranking_count": len(ranking_data),
            "comments_file": comments_file,
            "ranking_file": ranking_file
        }
        
    except Exception as e:
        print(f"Step11 エラー: {str(e)}")
        raise

def load_broadcast_data(broadcast_dir, lv_value):
    """統合JSONファイルを読み込み"""
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    if os.path.exists(json_path):
        with open(json_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    raise Exception(f"統合JSONファイルが見つかりません: {json_path}")

def parse_comments_from_xml(xml_path, start_time):
    """NCVのXMLからコメントデータを解析"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        comments = []
        
        # chat要素を検索（名前空間対応）
        chat_elements = root.findall('.//chat')
        if not chat_elements:
            # 名前空間がある場合
            namespaces = {'ncv': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}
            chat_elements = root.findall('.//ncv:chat', namespaces)
        
        print(f"XMLから{len(chat_elements)}個のコメントを検出")
        
        for chat in chat_elements:
            try:
                comment_date = int(chat.get('date', 0))
                if comment_date == 0:
                    continue
                
                # 配信開始からの秒数を計算
                broadcast_seconds = comment_date - start_time
                
                # 負の値（配信開始前）はスキップ
                if broadcast_seconds < 0:
                    continue
                
                # タイムブロック計算（10秒刻み）
                timeline_block = (broadcast_seconds // 10) * 10
                
                # コメントデータを構築
                comment_data = {
                    "no": int(chat.get('no', 0)),
                    "user_id": chat.get('user_id', ''),
                    "user_name": chat.get('name', ''),
                    "text": chat.text or '',
                    "date": comment_date,
                    "broadcast_seconds": broadcast_seconds,
                    "timeline_block": timeline_block,
                    "premium": int(chat.get('premium', 0)),
                    "anonymity": 'anonymity' in chat.attrib
                }
                
                comments.append(comment_data)
                
            except (ValueError, TypeError) as e:
                print(f"コメント解析エラー: {str(e)}")
                continue
        
        # 時系列順にソート
        comments.sort(key=lambda x: x['broadcast_seconds'])
        
        print(f"有効なコメント: {len(comments)}個")
        return comments
        
    except Exception as e:
        print(f"XML解析エラー: {str(e)}")
        raise

def generate_comment_ranking(comments_data):
    """コメントランキングを生成"""
    try:
        user_stats = {}
        
        # ユーザー別にコメントを集計
        for comment in comments_data:
            user_id = comment['user_id']
            
            if user_id not in user_stats:
                user_stats[user_id] = {
                    "user_id": user_id,
                    "user_name": comment['user_name'],
                    "comment_count": 0,
                    "first_comment": "",
                    "first_comment_time": 0,
                    "last_comment": "",
                    "last_comment_time": 0,
                    "premium": comment['premium'],
                    "anonymity": comment['anonymity']
                }
            
            user_stat = user_stats[user_id]
            user_stat["comment_count"] += 1
            
            # 初回コメント
            if user_stat["comment_count"] == 1:
                user_stat["first_comment"] = comment['text']
                user_stat["first_comment_time"] = comment['broadcast_seconds']
            
            # 最新コメント（常に更新）
            user_stat["last_comment"] = comment['text']
            user_stat["last_comment_time"] = comment['broadcast_seconds']
        
        # コメント数順にソート
        ranking = sorted(user_stats.values(), key=lambda x: x['comment_count'], reverse=True)
        
        # ランク付け
        for i, user in enumerate(ranking, 1):
            user["rank"] = i
        
        print(f"コメントランキング: {len(ranking)}ユーザー")
        return ranking
        
    except Exception as e:
        print(f"ランキング生成エラー: {str(e)}")
        raise

def save_comments_json(broadcast_dir, lv_value, comments_data):
    """コメントJSONを保存"""
    try:
        comments_file = os.path.join(broadcast_dir, f"{lv_value}_comments.json")
        
        with open(comments_file, 'w', encoding='utf-8') as f:
            json.dump({
                "lv_value": lv_value,
                "total_comments": len(comments_data),
                "created_at": datetime.now().isoformat(),
                "comments": comments_data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"コメントJSON保存: {comments_file}")
        return comments_file
        
    except Exception as e:
        print(f"コメントJSON保存エラー: {str(e)}")
        raise

def save_ranking_json(broadcast_dir, lv_value, ranking_data):
    """ランキングJSONを保存"""
    try:
        ranking_file = os.path.join(broadcast_dir, f"{lv_value}_comment_ranking.json")
        
        with open(ranking_file, 'w', encoding='utf-8') as f:
            json.dump({
                "lv_value": lv_value,
                "total_users": len(ranking_data),
                "created_at": datetime.now().isoformat(),
                "ranking": ranking_data
            }, f, ensure_ascii=False, indent=2)
        
        print(f"ランキングJSON保存: {ranking_file}")
        return ranking_file
        
    except Exception as e:
        print(f"ランキングJSON保存エラー: {str(e)}")
        raise