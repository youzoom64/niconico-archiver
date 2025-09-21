import os
import json
import html
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory
from datetime import datetime, timezone, timedelta


def process(pipeline_data):
    """Step12: 完全版HTML生成（全機能統合）"""
    try:
        lv_value = pipeline_data['lv_value']
        config = pipeline_data['config']
        
        print(f"Step12 完全版開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], pipeline_data['account_id'])
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 2. 全データファイル読み込み
        broadcast_data = load_json_file(broadcast_dir, f"{lv_value}_data.json")
        transcript_data = load_json_file(broadcast_dir, f"{lv_value}_transcript.json")
        comments_data = load_json_file(broadcast_dir, f"{lv_value}_comments.json")
        ranking_data = load_json_file(broadcast_dir, f"{lv_value}_comment_ranking.json")
        
        # 3. 各種データ準備
        timeline_data = create_timeline_blocks(transcript_data, comments_data, lv_value, broadcast_data)
        transcript_blocks = timeline_data['transcript_blocks']
        comment_blocks = timeline_data['comment_blocks']
        word_ranking = prepare_word_ranking(broadcast_data)
        comment_ranking = prepare_comment_ranking(ranking_data, account_dir, lv_value)
        ai_chats = prepare_ai_chats(broadcast_data, config)
        
        # 4. 完全版HTMLを生成
        html_content = generate_complete_html(
            timeline_data, broadcast_data, word_ranking, 
            comment_ranking, ai_chats, config, lv_value
        )
        
        # 5. HTMLファイル保存
        html_file = save_html_file(broadcast_dir, lv_value, broadcast_data.get('live_title', 'タイトル不明'), html_content)
        
        # 6. 統合JSONにHTMLパスを追加
        broadcast_data['html_file_path'] = os.path.basename(html_file)  # ファイル名のみ
        
        # JSONを再保存
        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
        
        print(f"Step12 完全版完了: {lv_value} - 完全HTML生成: {html_file}")
        return {"html_generated": True, "html_file": html_file}
        
    except Exception as e:
        print(f"Step12 エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def load_json_file(directory, filename):
    """JSONファイルを読み込み"""
    file_path = os.path.join(directory, filename)
    if os.path.exists(file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}

def create_timeline_blocks(transcript_data, comments_data, lv_value, broadcast_data):
    """タイムラインブロックを文字起こしとコメントで分離して作成"""
    try:
        # elapsed_timeから最大時間を計算
        elapsed_time = broadcast_data.get('elapsed_time', '')
        max_seconds = parse_elapsed_time_to_seconds(elapsed_time)
        
        print(f"elapsed_time: {elapsed_time}, 最大秒数: {max_seconds}")
        
        # 0秒からelapsed_time分まで全タイムブロックを生成
        all_time_blocks = set(range(0, max_seconds + 1, 10))
        
        # 文字起こし用ブロック辞書
        transcript_blocks = {}
        # コメント用ブロック辞書  
        comment_blocks = {}
        
        print(f"文字起こしデータ: {len(transcript_data.get('transcripts', []))}件")
        print(f"コメントデータ: {len(comments_data.get('comments', []))}件")
        print(f"生成する全タイムブロック数: {len(all_time_blocks)}")
        
        # まず全タイムブロックを空で初期化
        for block_time in all_time_blocks:
            transcript_blocks[block_time] = {
                'start_seconds': block_time,
                'end_seconds': block_time + 10,
                'time_range': format_time_range(block_time, block_time + 10),
                'transcript': '',  # 空で初期化
                'center_score': 0.0,
                'positive_score': 0.0,
                'negative_score': 0.0,
                'screenshot_path': f"./screenshot/{lv_value}/{timeline_block}.jpg"  # .png → .jpg
            }
            
            comment_blocks[block_time] = {
                'start_seconds': block_time,
                'end_seconds': block_time + 10,
                'time_range': format_time_range(block_time, block_time + 10),
                'comments': []  # 空で初期化
            }
        
        # 文字起こしデータを適切なブロックに配置
        transcripts = transcript_data.get('transcripts', [])
        for segment in transcripts:
            timestamp = segment.get('timestamp', 0)
            timeline_block = (timestamp // 10) * 10
            
            # elapsed_time範囲内のデータのみ処理
            if timeline_block in transcript_blocks:
                transcript_blocks[timeline_block].update({
                    'transcript': html.escape(segment.get('text', '')),
                    'center_score': round(segment.get('center_score', 0), 3),
                    'positive_score': round(segment.get('positive_score', 0), 3),
                    'negative_score': round(segment.get('negative_score', 0), 3),
                })
        
        # コメントデータを適切なブロックに配置
        comments = comments_data.get('comments', [])
        for comment in comments:
            timeline_block = comment.get('timeline_block', 0)
            
            # elapsed_time範囲内のデータのみ処理
            if timeline_block in comment_blocks:
                user_url = ""
                if not comment.get('anonymity', False) and comment.get('user_id', ''):
                    user_url = f"https://www.nicovideo.jp/user/{comment.get('user_id', '')}"
                
                comment_data = {
                    'index': comment.get('no', 0),
                    'time': format_seconds_to_time(comment.get('broadcast_seconds', 0)),
                    'user_name': html.escape(comment.get('user_name', '')),
                    'user_url': user_url,
                    'text': html.escape(comment.get('text', '')),
                    'icon_url': f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{comment.get('user_id', '')[:4]}/{comment.get('user_id', '')}.jpg"
                }
                
                comment_blocks[timeline_block]['comments'].append(comment_data)
        
        # ソートして配列に変換
        transcript_timeline = []
        comment_timeline = []
        
        for block_time in sorted(all_time_blocks):
            transcript_timeline.append(transcript_blocks[block_time])
            
            block = comment_blocks[block_time]
            block['comments'].sort(key=lambda x: x.get('time', ''))
            comment_timeline.append(block)
        
        print(f"文字起こしブロック作成完了: {len(transcript_timeline)}ブロック")
        print(f"コメントブロック作成完了: {len(comment_timeline)}ブロック")
        
        return {
            'transcript_blocks': transcript_timeline,
            'comment_blocks': comment_timeline
        }
        
    except Exception as e:
        print(f"タイムライン作成エラー: {str(e)}")
        return {
            'transcript_blocks': [],
            'comment_blocks': []
        }

def parse_elapsed_time_to_seconds(elapsed_time_str):
    """elapsed_time文字列を秒数に変換"""
    try:
        # "01:32:11.6330331" -> 秒数に変換
        if not elapsed_time_str:
            return 0
            
        time_parts = elapsed_time_str.split(':')
        if len(time_parts) != 3:
            return 0
            
        hours = int(time_parts[0])
        minutes = int(time_parts[1])
        seconds = float(time_parts[2])
        
        total_seconds = hours * 3600 + minutes * 60 + seconds
        return int(total_seconds)
        
    except (ValueError, IndexError, AttributeError) as e:
        print(f"elapsed_time解析エラー: {elapsed_time_str} - {str(e)}")
        return 0


def prepare_word_ranking(broadcast_data):
    """単語ランキングデータを準備"""
    try:
        word_ranking = []
        for word_item in broadcast_data.get('word_ranking', []):
            word_ranking.append({
                'word': html.escape(word_item.get('word', '')),
                'count': word_item.get('count', 0),
                'font_size': word_item.get('font_size', 16)
            })
        print(f"単語ランキング準備: {len(word_ranking)}語")
        return word_ranking
    except Exception as e:
        print(f"単語ランキング準備エラー: {str(e)}")
        return []

def prepare_comment_ranking(ranking_data, account_dir, lv_value):
    """コメントランキングデータを準備（全コメント含む）"""
    try:
        comment_ranking = []
        
        # 正しいパス: account_dir配下のlvディレクトリ
        broadcast_dir = os.path.join(account_dir, lv_value)
        comments_file = os.path.join(broadcast_dir, f"{lv_value}_comments.json")
        
        print(f"DEBUGLOG: コメントファイルパス: {comments_file}")
        print(f"DEBUGLOG: ファイル存在確認: {os.path.exists(comments_file)}")
        
        all_comments = {}
        if os.path.exists(comments_file):
            # 以下は既存のコード
            with open(comments_file, 'r', encoding='utf-8') as f:
                comments_data = json.load(f)

            # ユーザーID別にコメントをグループ化
            for comment in comments_data.get('comments', []):
                user_id = comment.get('user_id', '')
                if user_id not in all_comments:
                    all_comments[user_id] = []
                all_comments[user_id].append({
                    'index': comment.get('no', 0),  # indexを追加
                    'text': html.escape(comment.get('text', '')),
                    'time': format_seconds_to_time(comment.get('broadcast_seconds', 0)),
                    'broadcast_seconds': comment.get('broadcast_seconds', 0)
                })
        
        for rank_data in ranking_data.get('ranking', []):
            user_id = rank_data.get('user_id', '')
            user_name = html.escape(rank_data.get('user_name', ''))
            
            # スペシャルユーザーページ確認
            special_user_dir = os.path.join(account_dir, f"special_user_{user_id}")
            detail_file = os.path.join(special_user_dir, f"{user_id}_{lv_value}_detail.html")
            
            if os.path.exists(detail_file):
                user_name_display = f'<a href="../special_user_{user_id}/{user_id}_{lv_value}_detail.html" target="_blank">{user_name}</a>'
            else:
                user_name_display = user_name
            
            user_url = ""
            if not rank_data.get('anonymity', False) and user_id:
                user_url = f"https://www.nicovideo.jp/user/{user_id}"
            
            # そのユーザーの全コメントを取得
            user_comments = all_comments.get(user_id, [])
            # 時間順にソート
            user_comments.sort(key=lambda x: x['broadcast_seconds'])
            
            comment_ranking.append({
                'rank': rank_data.get('rank', 0),
                'user_id': user_id,
                'user_name': user_name_display,
                'user_url': user_url,
                'icon_url': f"https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/{user_id[:-4]}/{user_id}.jpg",
                'comment_count': rank_data.get('comment_count', 0),
                'first_comment': html.escape(rank_data.get('first_comment', '')),
                'first_comment_time': format_seconds_to_time(rank_data.get('first_comment_time', 0)),
                'last_comment': html.escape(rank_data.get('last_comment', '')),
                'last_comment_time': format_seconds_to_time(rank_data.get('last_comment_time', 0)),
                'comments': user_comments  # キー名をcommentsに統一
            })
        
        print(f"コメントランキング準備: {len(comment_ranking)}ユーザー")
        return comment_ranking
    except Exception as e:
        print(f"コメントランキング準備エラー: {str(e)}")
        return []
    
def prepare_ai_chats(broadcast_data, config):
    """AI会話データを準備"""
    try:
        ai_prompts = config.get('ai_prompts', {})
        char1_name = ai_prompts.get('character1_name', 'ニニちゃん')
        char1_image = ai_prompts.get('character1_image_url', '')
        char1_flip = ai_prompts.get('character1_image_flip', False)
        char2_name = ai_prompts.get('character2_name', 'ココちゃん')
        char2_image = ai_prompts.get('character2_image_url', '')
        char2_flip = ai_prompts.get('character2_image_flip', False)
        
        def get_character_info(name):
            if name == char1_name:
                return {'icon': char1_image, 'flip': char1_flip}
            elif name == char2_name:
                return {'icon': char2_image, 'flip': char2_flip}
            return {'icon': '', 'flip': False}
        
        intro_chat = []
        for chat in broadcast_data.get('intro_chat', []):
            char_info = get_character_info(chat.get('name', ''))
            intro_chat.append({
                'name': html.escape(chat.get('name', '')),
                'dialogue': html.escape(chat.get('dialogue', '')),
                'icon': char_info['icon'],
                'flip': char_info['flip']
            })
        
        outro_chat = []
        for chat in broadcast_data.get('outro_chat', []):
            char_info = get_character_info(chat.get('name', ''))
            outro_chat.append({
                'name': html.escape(chat.get('name', '')),
                'dialogue': html.escape(chat.get('dialogue', '')),
                'icon': char_info['icon'],
                'flip': char_info['flip']
            })
        
        print(f"AI会話準備: 開始前{len(intro_chat)}件, 終了後{len(outro_chat)}件")
        return {'intro': intro_chat, 'outro': outro_chat}
    except Exception as e:
        print(f"AI会話準備エラー: {str(e)}")
        return {'intro': [], 'outro': []}
        

def generate_complete_html(timeline_data, broadcast_data, word_ranking, comment_ranking, ai_chats, config, lv_value):
    """完全版HTMLを生成（全機能統合）"""
    try:
        # timeline_dataから文字起こしとコメントブロックを取得
        transcript_blocks = timeline_data['transcript_blocks']
        comment_blocks = timeline_data['comment_blocks']
        
        html_parts = []
        
        sentiment_stats = broadcast_data.get('sentiment_stats', {})
        music_data = broadcast_data.get('music_generation', {})
        image_data = broadcast_data.get('image_generation', {})
        
        # JavaScript用データ準備
        segments_js = ','.join([str(block['start_seconds']) for block in transcript_blocks])
        positive_data_js = ','.join([str(block['positive_score']) for block in transcript_blocks])
        center_data_js = ','.join([str(block['center_score']) for block in transcript_blocks])
        negative_data_js = ','.join([str(block['negative_score']) for block in transcript_blocks])
        
        # HTMLヘッダー
        html_parts.append(f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(broadcast_data.get('live_title', ''))}</title>
    <link rel="stylesheet" href="css/archive-style.css" />
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background: #f4f4f4; padding: 20px; margin-bottom: 20px; border-radius: 5px; }}
        .stats {{ display: flex; gap: 20px; margin: 10px 0; flex-wrap: wrap; }}
        .stat-item {{ background: white; padding: 10px; border-radius: 3px; border-left: 3px solid #007cba; flex: 1; min-width: 150px; }}
        .section {{ margin: 30px 0; padding: 20px; background: #fafafa; border-radius: 5px; }}
        .section h2 {{ color: #333; border-bottom: 2px solid #007cba; padding-bottom: 10px; }}
        .chat-container {{
            margin: 20px auto; 
            max-width: 800px; 
            padding: 0 20px; 
        }}

        .chat-message {{ 
            display: flex; 
            margin: 15px 0; 
            align-items: flex-start; 
            gap: 10px; 
            max-width: 600px; 
            margin-left: auto; 
            margin-right: auto; 
        }}

        /* スマホ対応 */
        @media (max-width: 768px) {{
            .chat-container {{
                max-width: 100%;
                padding: 0 10px;
            }}
            
            .chat-message {{
                max-width: 100%;
            }}
        }}
        .chat-avatar {{ width: 50px; height: 50px; border-radius: 50%; }}
        .chat-bubble {{ background: #e3f2fd; padding: 10px 15px; border-radius: 15px; max-width: 70%; }}
        .ranking-list {{ list-style: none; padding: 0; }}
        .ranking-item {{
            background: white;
            margin: 10px 0;
            padding: 15px;
            border-radius: 5px;
            border-left: 4px solid #007cba; /* デフォルト色（青） */
        }}
        /* 1〜3位だけ色変更 */
        .rank-1 {{
            border-left-color: gold;       /* 金メダル風 */
        }}
        .rank-2 {{
            border-left-color: silver;     /* 銀メダル風 */
        }}
        .rank-3 {{
            border-left-color: #cd7f32;    /* ブロンズ */
        }}
        .word-list {{ display: flex; flex-wrap: wrap; gap: 10px; }}
        .word-item {{ background: #007cba; color: white; padding: 5px 10px; border-radius: 15px; }}
        .summary-section {{
            background: white;                    /* 背景色を白に設定 */
            color: #333;                         /* 文字色を濃いグレーに設定 */
            padding: 30px;                       /* 内側の余白を上下左右30px */
            border-radius: 10px;                 /* 角を10px丸める */
            border: 1px solid #ddd;              /* 1px幅の薄いグレーの枠線 */
            box-shadow: 0 2px 4px rgba(0,0,0,0.1); /* 軽い影をつける（右に0px、下に2px、ぼかし4px、10%透明の黒） */
        }}
        .audio-player {{ margin: 20px 0; }}
        .summary-image {{ text-align: center; margin: 20px 0; }}
        .summary-image img {{ max-width: 400px; border-radius: 10px; box-shadow: 0 4px 8px rgba(0,0,0,0.3); }}
        
        .container {{ display: flex; gap: 20px; margin: 20px 0; }}
        .timeline {{ flex: 1; }}
        .timeline h2 {{ text-align: center; margin-bottom: 20px; }}
        .time-block {{ 
            position: relative; 
            height: 180px; 
            border: 1px solid #ddd; 
            margin: 10px 0; 
            padding: 10px; 
            border-radius: 5px; 
            overflow: hidden;
        }}
        .time-block strong {{ 
            display: block; 
            font-size: 1.1em; 
            color: #007cba; 
            margin-bottom: 10px; 
        }}
        .comment {{ 
            background: #f0f8ff; 
            padding: 8px; 
            margin: 5px 0; 
            border-radius: 3px; 
            font-size: 0.9em;
            max-height: 80px;
            overflow-y: auto;
        }}
        .score-container {{ 
            margin: 5px 0; 
            font-size: 0.8em; 
        }}
        .center-score {{ color: #2196F3; font-weight: bold; }}
        .positive-score {{ color: #4CAF50; font-weight: bold; }}
        .negative-score {{ color: #F44336; font-weight: bold; }}
        .play-button {{ 
            position: absolute; 
            top: 5px; 
            right: 5px; 
            background: #007cba; 
            color: white; 
            padding: 5px 10px; 
            border-radius: 3px; 
            cursor: pointer; 
            font-size: 0.8em;
        }}
        .img_container {{
            position: absolute; 
            bottom: 5px; 
            right: 5px; 
            width: 80px;
            height: 60px;
        }}
        .img_container img {{ 
            width: 100%; 
            height: 100%; 
            object-fit: cover; 
            border-radius: 3px; 
            border: 1px solid #ddd;
        }}
        .nico-jump {{ 
            position: absolute; 
            left: 5px; 
            bottom: 5px; 
        }}
        .nico-jump button {{ 
            background: #ff6b35; 
            color: white; 
            border: none; 
            padding: 3px 8px; 
            border-radius: 3px; 
            font-size: 0.7em; 
            cursor: pointer;
        }}
        .comment-list {{ 
            max-height: 120px; 
            overflow-y: auto; 
            font-size: 0.8em;
        }}
        .comment-item {{ 
            margin: 3px 0; 
            padding: 3px; 
            border-bottom: 1px dotted #ccc; 
        }}
        .comment-item:last-child {{ border-bottom: none; }}
        .flash-fade-out {{ border: 3px solid #ff6b35 !important; transition: border 1s ease-out; }}
        
        #controls-container {{
            position: fixed;
            bottom: 20px;
            left: 20px;
            right: 20px;
            background: white;
            border: 2px solid #007cba;
            border-radius: 10px;
            padding: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
            z-index: 1000;
            display: flex;
            align-items: center;
            gap: 15px;
        }}
        #controls-container audio {{ flex: 1; margin: 0; }}
        #seekbar {{ flex: 1; margin: 0; }}
        #controls-container label, #controls-container input[type="checkbox"] {{ margin: 0; }}
        
        #gaugeBarContainer {{
            position: fixed;
            top: 20px;
            right: 20px;
            background: white;
            border: 1px solid #ddd;
            border-radius: 5px;
            padding: 10px;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
            z-index: 1000;
        }}
        
        .graph-container {{ margin: 20px 0; text-align: center; }}
        .graph-container canvas {{ max-width: 100%; height: auto; }}
        # HTMLヘッダーのスタイル部分に追加
        .ranking-header {{
            display: flex;
            align-items: center;
            margin-bottom: 5px;
        }}
        .ranking-summary {{
            margin-bottom: 10px;
        }}
        .toggle-comments-btn:hover {{
            background-color: #005a8a;
        }}
        .comment-entry:last-child {{
            border-bottom: none;
        }}
        .flip-horizontal {{
        transform: scaleX(-1);
        }}
        .char1-bubble {{
            background: #e3f2fd; /* 青系 */
            border-left: 3px solid #2196f3;
        }}
        .char2-bubble {{
            background: #fce4ec; /* 薄いピンク */
            border-right: 3px solid #e91e63;
        }}
        .flip-horizontal {{
            transform: scaleX(-1);
        }}
        .section {{
            margin-bottom: 100px;
        }}
    </style>
</head>
<body>
    <script>
      window.NICO_ARCHIVE_CONFIG = {{
          lvValue: "{lv_value}",
          duration: {int(broadcast_data.get('video_duration', 0))},
          segments: [{segments_js}],
          emotionData: {{
              positive: [{positive_data_js}],
              center: [{center_data_js}],
              negative: [{negative_data_js}]
          }},
          screenshotPath: "./screenshot/{lv_value}",
          broadcast: {{
              title: "{html.escape(broadcast_data.get('live_title', ''))}",
              broadcaster: "{html.escape(broadcast_data.get('broadcaster', ''))}",
              community: "{broadcast_data.get('default_community', '')}"
          }}
      }};
    </script>
""")

        # JST (UTC+9) のタイムゾーンを定義
        jst = timezone(timedelta(hours=9))

        # ヘッダー情報のHTML生成部分を修正
        start_time_jst = datetime.fromtimestamp(int(broadcast_data.get('start_time', 0)), tz=jst)
        end_time_jst = datetime.fromtimestamp(int(broadcast_data.get('end_time', 0)), tz=jst)

        html_parts.append(f"""
            <div class="header">
                <h1>{html.escape(broadcast_data.get('live_title', ''))}</h1>
                <div class="stats">
                    <div class="stat-item">
                        <strong>配信者:</strong> {html.escape(broadcast_data.get('broadcaster', ''))}
                    </div>
                    <div class="stat-item">
                        <strong>開始時間:</strong> {start_time_jst.strftime('%Y/%m/%d %H:%M')}
                    </div>
                    <div class="stat-item">
                        <strong>終了時間:</strong> {end_time_jst.strftime('%Y/%m/%d %H:%M')}
                    </div>
                    <div class="stat-item">
                        <strong>来場者数:</strong> {broadcast_data.get('watch_count', '0')}人
                    </div>
                    <div class="stat-item">
                        <strong>コメント数:</strong> {broadcast_data.get('comment_count', '0')}コメ
                    </div>
                    <div class="stat-item">
                        <strong>配信時間:</strong> {broadcast_data.get('elapsed_time', '')}
                    </div>
                </div>
            </div>
        """)

        # 開始前AI会話
        if ai_chats['intro']:
            html_parts.append("""
        <div class="section">
            <h2>開始前会話</h2>
            <div class="chat-container">
        """)
            char1_name = config.get('ai_prompts', {}).get('character1_name', 'ニニちゃん')
            char2_name = config.get('ai_prompts', {}).get('character2_name', 'ココちゃん')
            
            for i, chat in enumerate(ai_chats['intro']):
                side = 'left' if i % 2 == 0 else 'right'
                flip_class = ' flip-horizontal' if chat.get('flip', False) else ''
                
                # キャラクターごとに異なるCSSクラスを適用
                if chat['name'] == char1_name:
                    bubble_class = 'chat-bubble char1-bubble'
                elif chat['name'] == char2_name:
                    bubble_class = 'chat-bubble char2-bubble'
                else:
                    bubble_class = 'chat-bubble'
                    
                html_parts.append(f"""
                <div class="chat-message" style="flex-direction: {'row' if side == 'left' else 'row-reverse'};">
                    <img src="{chat['icon']}" alt="{chat['name']}" class="chat-avatar{flip_class}" onerror="this.style.display='none'">
                    <div class="{bubble_class}">
                        <strong>{chat['name']}:</strong><br>
                        {chat['dialogue']}
                    </div>
                </div>
        """)
            html_parts.append("    </div>\n</div>\n")

        # コメントランキング部分の修正版
        if comment_ranking:
            html_parts.append("""
                    <div class="section">
                        <h2>🏆 コメントランキング</h2>
                        <ul class="ranking-list">
                    """)
            for user in comment_ranking:
                # ランク別のクラスと見た目設定
                rank_class_map = {
                    1: ("rank-1", 60, "1.4em"),
                    2: ("rank-2", 45, "1.2em"),
                    3: ("rank-3", 36, "1.1em"),
                }
                rank_class, img_size, font_size = rank_class_map.get(user['rank'], ("rank-other", 30, "1em"))

                user_display = (
                    f'<a href="{user["user_url"]}" target="_blank">{user["user_name"]}</a>'
                    if user['user_url'] else user['user_name']
                )

                html_parts.append(f"""
                        <li class="ranking-item {rank_class}">
                            <div class="ranking-header" style="font-size:{font_size};">
                                <strong>{user['rank']}位:</strong>
                                <img src="{user['icon_url']}"
                                    style="width:{img_size}px; height:{img_size}px; border-radius:50%; vertical-align:middle; margin:0 5px;"
                                    onerror="this.onerror=null; this.src='https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/defaults/blank.jpg';">
                                {user_display} - {user['comment_count']}コメント
                                <button class="toggle-comments-btn" data-user-id="{user['user_id']}"
                                    style="margin-left:10px; padding:3px 8px; background:#007cba; color:white; border:none; border-radius:3px; cursor:pointer; font-size:0.8em;">
                                    全コメント表示
                                </button>
                            </div>
                            <div class="ranking-summary">
                                <small>初コメント ({user['first_comment_time']}): {user['first_comment']}</small><br>
                                <small>最終コメント ({user['last_comment_time']}): {user['last_comment']}</small>
                            </div>
                            <div class="user-comments" id="comments-{user['user_id']}"
                                style="display:none; margin-top:10px; max-height:300px; overflow-y:auto; background:#f8f9fa; padding:10px; border-radius:5px;">
                        """)

                # ユーザーの全コメントを表示
                for comment in user.get('comments', []):
                    html_parts.append(f"""
                                <div class="comment-entry" style="margin: 5px 0; padding: 5px; border-bottom: 1px dotted #ccc;">
                                    <span style="color: #666; font-size: 0.8em;">[{comment['time']}]</span>
                                    <span style="margin-left: 5px;">{comment['text']}</span>
                                </div>
                            """)

                html_parts.append("""
                            </div>
                        </li>
                        """)

            html_parts.append("""
                        </ul>
                    </div>
                    """)

        # 要約セクション
        html_parts.append(f"""
    <div class="summary-section">
        <h2>要約</h2>
        <p><strong>要約:</strong> {html.escape(broadcast_data.get('summary_text', ''))}</p>
        <p><strong>感情分析:</strong> 
           ポジティブ: {round(sentiment_stats.get('avg_positive', 0), 3)} | 
           センター: {round(sentiment_stats.get('avg_center', 0), 3)} | 
           ネガティブ: {round(sentiment_stats.get('avg_negative', 0), 3)}
        </p>
""")

        # AI音楽（複数曲対応）
        if music_data.get('songs'):
            html_parts.append("""
                <div class="audio-player">
                    <h3>要約を歌詞とした音楽</h3>
        """)
            
            for i, song in enumerate(music_data['songs']):
                if song.get('primary_url'):
                    song_title = f"楽曲 {i+1}"
                    html_parts.append(f"""
                    <div style="margin: 10px 0;">
                        <h4>{song_title}</h4>
                        <audio controls style="width: 100%;">
                            <source src="{song['primary_url']}" type="audio/mp3">
                        </audio>
                    </div>
        """)
            
            html_parts.append("        </div>\n")

        # 要約画像
        if image_data.get('imgur_url'):
            html_parts.append(f"""
        <div class="summary-image">
            <h3>要約を元に生成した画像</h3>
            <a href="{image_data['imgur_url']}" target="_blank">
                <img src="{image_data['imgur_url']}" alt="配信の抽象化イメージ">
            </a>
        </div>
""")

        # 感情分析グラフ
        html_parts.append("""
        <div class="emotion-chart-card">
            <h3>感情分析グラフ</h3>
            <div class="graph-container"></div>
        </div>
""")
        html_parts.append("    </div>\n")

        # 単語ランキング
        if word_ranking:
            html_parts.append("""
    <div class="section">
        <h2>単語使用頻度ランキング</h2>
        <div class="word-list">
""")
            for word in word_ranking:
                html_parts.append(f"""
            <span class="word-item" style="font-size: {min(word['font_size'], 32)}px;">
                {word['word']}: {word['count']}回
            </span>
""")
            html_parts.append("        </div>\n    </div>\n")

        # 横並びタイムライン
        html_parts.append("""
    <div class="container">
        <!-- 放送者タイムライン -->
        <div class="timeline" id="timeline1">
            <h2>放送者文字おこしのタイムライン</h2>
""")

        # 文字起こしタイムライン
        for block in transcript_blocks:
            html_parts.append(f"""
            <div class="time-block" id="time_block_{block['start_seconds']}" style="position: relative; height: 180px;">
                <strong>{block['time_range']}</strong>
                <div>
                    <p class="comment">{block['transcript']}</p>
                </div>
                <div class="score-container">
                    <span class="center-score">center:{block['center_score']}</span>
                    <span class="positive-score">positive:{block['positive_score']}</span>
                    <span class="negative-score">negative:{block['negative_score']}</span>
                </div>
                <div class="play-button">PLAY▶</div>
                <div class="img_container">
                    <img src="{block['screenshot_path']}" alt="動画のスクリーンショット {block['start_seconds']}秒">
                </div>
                <div class="nico-jump">
                    <button>タイムシフトにジャンプ</button>
                </div>
            </div>
""")

        html_parts.append("""
        </div>
        
        <!-- コメントタイムライン -->
        <div class="timeline" id="timeline2">
            <h2>コメントのタイムライン</h2>
""")

        # コメントタイムライン - 全時間範囲をカバー
        # まず全時間ブロックを取得
        all_time_blocks = set()
        for block in transcript_blocks:
            all_time_blocks.add(block['start_seconds'])
        for block in comment_blocks:
            all_time_blocks.add(block['start_seconds'])

        # 全時間ブロックに対してコメントブロックを表示
        for time_second in sorted(all_time_blocks):
            # その時間にコメントがあるかチェック
            comment_block = next((b for b in comment_blocks if b['start_seconds'] == time_second), None)
            
            html_parts.append(f"""
                    <div class="time-block" id="time_block_{time_second}" style="height: 180px;">
                        <strong>{format_time_range(time_second, time_second + 10)}</strong>
                        <div class="comment-list">
        """)
            
            if comment_block:
                # コメントがある場合
                for comment in comment_block['comments']:
                    user_display = f'<a href="{comment["user_url"]}" target="_blank">{comment["user_name"]}</a>' if comment['user_url'] else comment['user_name']
                    html_parts.append(f"""
                            <p class="comment-item">
                                {comment['index']} | {comment['time']} - {user_display} :
                                <img src="{comment['icon_url']}"
                                    style="width: 20px; height: 20px; vertical-align: middle; margin-left: 5px;"
                                    onerror="this.onerror=null; this.src='https://secure-dcdn.cdn.nimg.jp/nicoaccount/usericon/defaults/blank.jpg';">
                                {comment['text']}<br>
                            </p>
                    """)

            else:
                # コメントがない場合
                html_parts.append("""
                            <p style="color: #999; font-style: italic; text-align: center; margin-top: 50px;">コメントなし</p>
        """)
            
            html_parts.append("""
                        </div>
                    </div>
        """)

        html_parts.append("""
                </div>
            </div>
        """)

        # 終了後AI会話
        if ai_chats['outro']:
            html_parts.append("""
        <div class="section">
            <h2>終了後会話</h2>
            <div class="chat-container">
        """)
            for i, chat in enumerate(ai_chats['outro']):
                side = 'left' if i % 2 == 0 else 'right'
                flip_class = ' flip-horizontal' if chat.get('flip', False) else ''
                
                # キャラクターごとに異なるCSSクラスを適用
                if chat['name'] == char1_name:
                    bubble_class = 'chat-bubble char1-bubble'
                elif chat['name'] == char2_name:
                    bubble_class = 'chat-bubble char2-bubble'
                else:
                    bubble_class = 'chat-bubble'
                    
                html_parts.append(f"""
                <div class="chat-message" style="flex-direction: {'row' if side == 'left' else 'row-reverse'};">
                    <img src="{chat['icon']}" alt="{chat['name']}" class="chat-avatar{flip_class}" onerror="this.style.display='none'">
                    <div class="{bubble_class}">
                        <strong>{chat['name']}:</strong><br>
                        {chat['dialogue']}
                    </div>
                </div>
        """)
            html_parts.append("    </div>\n</div>\n")

        # プレイヤーコントロール
        html_parts.append(f"""
    <div id="controls-container">
        <label for="autoJumpToggle">Auto-Jump:</label>
        <input checked id="autoJumpToggle" name="autoJumpToggle" type="checkbox" />
        <audio controls id="audioPlayer">
            <source src="./{lv_value}_silent_audio.mp3" type="audio/mp3" />
            Your browser does not support the audio element.
        </audio>
        <input id="seekbar" max="{int(broadcast_data.get('video_duration', 0))}" min="0" step="1" type="range" value="0" />
        <label for="gaugeBar">高さ:</label>
        <input id="gaugeBar" max="800" min="100" type="range" value="180" style="width: 100px;" />
    </div>
""")


        # メタデータ
        html_parts.append(f"""
            <div class="section">
                <h2>メタデータ</h2>
                <ul>
                    <li>LiveNum: {broadcast_data.get('lv_value', '')}</li>
                    <li>配信時間: {broadcast_data.get('elapsed_time', '')}</li>
                    <li>コミュニティ: {html.escape(broadcast_data.get('community_name', ''))}</li>
                    <li>開始時刻: {start_time_jst.strftime('%Y-%m-%d %H:%M:%S JST')}</li>
                    <li>終了時刻: {end_time_jst.strftime('%Y-%m-%d %H:%M:%S JST')}</li>
                    <li>配信者ID: {broadcast_data.get('owner_id', '')}</li>
                </ul>
            </div>
        """)

        # JavaScript
        html_parts.append(f"""
    <script src="https://cdn.jsdelivr.net/npm/chart.js@2.9.4"></script>
    <script>
    document.addEventListener("DOMContentLoaded", function () {{
        const audioPlayer = document.getElementById("audioPlayer");
        const seekbar = document.getElementById("seekbar");
        const autoJumpToggle = document.getElementById("autoJumpToggle");
        const timeBlocks = document.querySelectorAll("#timeline1 .time-block");
        
        // 音声プレイヤー初期化
        if (audioPlayer && seekbar) {{
            audioPlayer.onloadedmetadata = function () {{
                seekbar.max = audioPlayer.duration;
            }};
            
            seekbar.addEventListener("input", function () {{
                audioPlayer.currentTime = this.value;
                if (autoJumpToggle.checked) {{
                    scrollToCurrentTimeBlock();
                }}
            }});
            
            audioPlayer.addEventListener("timeupdate", function () {{
                seekbar.value = audioPlayer.currentTime;
                if (autoJumpToggle.checked) {{
                    scrollToCurrentTimeBlock();
                }}
            }});
        }}
        
        // PLAYボタンのイベントリスナー設定
        timeBlocks.forEach(block => {{
            const playButton = block.querySelector('.play-button');
            if (playButton) {{
                const blockId = block.id;
                const timeIndex = blockId.split('_')[2];
                playButton.addEventListener('click', function() {{
                    const seekTime = parseInt(timeIndex, 10);
                    if (audioPlayer) {{
                        audioPlayer.currentTime = seekTime;
                        audioPlayer.play();
                        if (autoJumpToggle.checked) {{
                            scrollToCurrentTimeBlock();
                        }}
                    }}
                }});
            }}
        }});
        
        // タイムシフトジャンプボタン
        document.querySelectorAll('.nico-jump button').forEach(button => {{
            button.addEventListener('click', function() {{
                const timeBlock = this.closest('.time-block');
                const videoSecond = timeBlock.id.replace('time_block_', '');
                const jumpUrl = 'https://live.nicovideo.jp/watch/{lv_value}#' + videoSecond;
                window.open(jumpUrl, '_blank');
            }});
        }});
        
        // コメント表示/非表示トグル機能
        document.querySelectorAll('.toggle-comments-btn').forEach(button => {{
            button.addEventListener('click', function() {{
                const userId = this.dataset.userId;
                const commentsDiv = document.getElementById('comments-' + userId);
                
                if (commentsDiv.style.display === 'none') {{
                    commentsDiv.style.display = 'block';
                    this.textContent = '全コメント非表示';
                    this.style.backgroundColor = '#dc3545';
                }} else {{
                    commentsDiv.style.display = 'none';
                    this.textContent = '全コメント表示';
                    this.style.backgroundColor = '#007cba';
                }}
            }});
        }});
        
        let lastFlashedBlock = null;
        
        function scrollToCurrentTimeBlock() {{
            if (!audioPlayer) return;
            const currentBlock = Math.floor(audioPlayer.currentTime / 10) * 10;
            const timeBlockId = `time_block_${{currentBlock}}`;
            const timeBlock1 = document.getElementById(timeBlockId);
            const timeBlock2 = document.querySelector(`#timeline2 .time-block[id="${{timeBlockId}}"]`);
            
            if (timeBlock1 && lastFlashedBlock !== currentBlock) {{
                timeBlock1.scrollIntoView({{
                    behavior: "smooth",
                    block: "center"
                }});
                
                timeBlock1.classList.add('flash-fade-out');
                if (timeBlock2) {{
                    timeBlock2.classList.add('flash-fade-out');
                }}
                
                setTimeout(() => {{
                    timeBlock1.classList.remove('flash-fade-out');
                    if (timeBlock2) {{
                        timeBlock2.classList.remove('flash-fade-out');
                    }}
                }}, 1000);
                
                lastFlashedBlock = currentBlock;
            }}
        }}
        
        // 高さ調整機能
        function equalizeHeights() {{
            const timeline1Blocks = document.querySelectorAll('#timeline1 .time-block');
            const timeline2Blocks = document.querySelectorAll('#timeline2 .time-block');
            
            for(let i = 0; i < Math.min(timeline1Blocks.length, timeline2Blocks.length); i++) {{
                const block1 = timeline1Blocks[i];
                const block2 = timeline2Blocks[i];
                const maxHeight = Math.max(block1.clientHeight, block2.clientHeight);
                block1.style.height = maxHeight + 'px';
                block2.style.height = maxHeight + 'px';
            }}
        }}
        
        window.addEventListener('load', equalizeHeights);
        window.addEventListener('resize', equalizeHeights);
        
        // ゲージバー機能
        document.getElementById('gaugeBar').addEventListener('input', function() {{
            const gaugeValue = this.value;
            const nearestBlockId = getNearestTimeBlockId();
            const nearestBlock = nearestBlockId ? document.getElementById(nearestBlockId) : null;
            const offsetTop = nearestBlock ? nearestBlock.getBoundingClientRect().top : 0;
            
            document.querySelectorAll('.time-block').forEach(block => {{
                block.style.height = `${{gaugeValue}}px`;
            }});
            
            if (nearestBlock) {{
                window.scrollBy(0, nearestBlock.getBoundingClientRect().top - offsetTop);
            }}
        }});
        
        function getNearestTimeBlockId() {{
            const timeBlocks = document.querySelectorAll('.time-block');
            let nearestBlockId = null;
            let nearestDistance = Infinity;
            
            timeBlocks.forEach(block => {{
                const rect = block.getBoundingClientRect();
                const distance = Math.abs(rect.top);
                
                if (distance < nearestDistance) {{
                    nearestDistance = distance;
                    nearestBlockId = block.id;
                }}
            }});
            
            return nearestBlockId;
        }}
        
        // 感情分析グラフ
        var segments = [{segments_js}];
        var positiveData = [{positive_data_js}];
        var centerData = [{center_data_js}];
        var negativeData = [{negative_data_js}];
        
        function createTooltipText(dataIndex) {{
            var timeBlockID = segments[dataIndex];
            var commentElement = document.getElementById('time_block_' + timeBlockID);
            if (commentElement && commentElement.querySelector('.comment')) {{
                var htmlContent = commentElement.querySelector('.comment').innerHTML;
                return htmlContent.replace(/<[^>]*>/g, '').trim();
            }}
            return '';
        }}
        
        function jumpToTimeBlock(dataIndex) {{
            var timeBlockID = segments[dataIndex];
            var timeBlockElement = document.getElementById('time_block_' + timeBlockID);
            if (timeBlockElement) {{
                timeBlockElement.scrollIntoView({{behavior: 'smooth', block: 'center'}});
            }}
        }}
        
        // Chart.js でグラフ作成
        var ctx = document.createElement('canvas');
        ctx.width = 800;
        ctx.height = 300;
        document.querySelector('.graph-container').appendChild(ctx);
        
        var sentimentChart = new Chart(ctx.getContext('2d'), {{
            type: 'line',
            data: {{
                labels: segments.map(s => Math.floor(s/60) + ':' + (s%60).toString().padStart(2,'0')),
                datasets: [
                    {{ 
                        label: 'Positive', 
                        data: positiveData,
                        borderColor: '#4CAF50',
                        backgroundColor: 'rgba(76, 175, 80, 0.1)',
                        fill: false
                    }},
                    {{ 
                        label: 'Center', 
                        data: centerData,
                        borderColor: '#2196F3',
                        backgroundColor: 'rgba(33, 150, 243, 0.1)',
                        fill: false
                    }},
                    {{ 
                        label: 'Negative', 
                        data: negativeData,
                        borderColor: '#F44336',
                        backgroundColor: 'rgba(244, 67, 54, 0.1)',
                        fill: false
                    }}
                ]
            }},
            options: {{
                responsive: true,
                tooltips: {{
                    enabled: true,
                    mode: 'index',
                    intersect: false,
                    callbacks: {{
                        beforeBody: function(tooltipItems, data) {{
                            var segmentIndex = tooltipItems[0].index;
                            return createTooltipText(segmentIndex);
                        }},
                        label: function(tooltipItem, data) {{
                            var label = data.datasets[tooltipItem.datasetIndex].label;
                            var value = tooltipItem.yLabel.toFixed(3);
                            return label + ': ' + value;
                        }}
                    }}
                }},
                onClick: function(evt) {{
                    var activePoints = sentimentChart.getElementsAtEvent(evt);
                    if (activePoints.length > 0) {{
                        var dataIndex = activePoints[0]._index;
                        jumpToTimeBlock(dataIndex);
                    }}
                }},
                scales: {{
                    yAxes: [{{
                        ticks: {{
                            beginAtZero: true,
                            max: 1.0
                        }}
                    }}]
                }}
            }}
        }});
    }});
    </script>
</body>
</html>""")
        return ''.join(html_parts)
        
    except Exception as e:
        print(f"完全HTML生成エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        return "<html><body>HTML生成エラー</body></html>"

def format_time_range(start_seconds, end_seconds):
    """時間範囲を表記"""
    start_time = format_seconds_to_time(start_seconds)
    end_time = format_seconds_to_time(end_seconds)
    return f"{start_time} - {end_time}"

def format_seconds_to_time(seconds):
    """秒数を時間表記に変換"""
    try:
        seconds = int(seconds)
        minutes = seconds // 60
        hours = minutes // 60
        return f"{hours:02d}:{minutes%60:02d}:{seconds%60:02d}"
    except:
        return "00:00:00"

def save_html_file(broadcast_dir, lv_value, live_title, html_content):
    """HTMLファイルを保存"""
    try:
        filename = f"{lv_value}_{live_title}.html"
        invalid_chars = '<>:"/\\|?*'
        for char in invalid_chars:
            filename = filename.replace(char, '_')
        filename = filename.strip('. ')
        if len(filename) > 200:
            filename = filename[:200]
        
        html_file = os.path.join(broadcast_dir, filename)
        
        with open(html_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"完全HTML保存完了: {html_file}")
        return html_file
    except Exception as e:
        print(f"HTML保存エラー: {str(e)}")
        raise