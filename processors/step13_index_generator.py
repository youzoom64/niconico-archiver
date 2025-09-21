import os
import json
import html
import re
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step13: 一覧ページ生成（index.html + タグページ）"""
    try:
        account_id = pipeline_data['account_id']
        config = pipeline_data['config']
        
        print(f"Step13 一覧ページ生成開始: {account_id}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], account_id)
        
        # 2. 全配信データを収集
        broadcast_list = collect_broadcast_data(account_dir)
        
        # 3. タグ処理
        tags_config = config.get('tags', [])
        processed_broadcasts = process_tags(broadcast_list, tags_config)
        
        # 4. メイン一覧ページ生成
        generate_index_page(account_dir, processed_broadcasts, config)
        
        # 5. タグページ生成
        generate_tag_pages(account_dir, processed_broadcasts, tags_config, config)
        
        print(f"Step13 完了: {account_id} - 一覧ページ生成完了")
        return {"index_generated": True, "tag_pages": len(tags_config)}
        
    except Exception as e:
        print(f"Step13 エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def collect_broadcast_data(account_dir):
    """アカウントディレクトリから全配信データを収集"""
    broadcast_list = []
    
    try:
        for item in os.listdir(account_dir):
            item_path = os.path.join(account_dir, item)
            
            # lv で始まるディレクトリのみ処理
            if os.path.isdir(item_path) and item.startswith('lv'):
                lv_value = item
                
                # データファイル読み込み
                data_file = os.path.join(item_path, f"{lv_value}_data.json")
                if os.path.exists(data_file):
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
                    # HTMLファイル検索
                    html_file = find_html_file(item_path, lv_value)
                    if html_file:
                        broadcast_info = {
                            'lv_value': lv_value,
                            'title': data.get('live_title', 'タイトル不明'),
                            'broadcaster': data.get('broadcaster', '不明'),
                            'start_time': data.get('start_time', 0),
                            'watch_count': data.get('watch_count', 0),
                            'comment_count': data.get('comment_count', 0),
                            'elapsed_time': data.get('elapsed_time', ''),
                            'summary_text': data.get('summary_text', ''),
                            'html_file': data.get('html_file_path', ''),
                            'image_url': data.get('image_generation', {}).get('imgur_url', ''),
                            'music_urls': get_music_urls_multiple(data),
                            'transcript_segments': get_transcript_segments(item_path, lv_value),
                            'tags': []
                        }
                        broadcast_list.append(broadcast_info)
        
        # 開始時間順でソート（新しい順）
        broadcast_list.sort(key=lambda x: x['start_time'], reverse=True)
        print(f"配信データ収集完了: {len(broadcast_list)}件")
        
    except Exception as e:
        print(f"配信データ収集エラー: {str(e)}")
    
    return broadcast_list

def get_music_urls_multiple(data):
    """音楽URLを複数取得"""
    music_data = data.get('music_generation', {})
    songs = music_data.get('songs', [])
    urls = []
    for song in songs:
        if song.get('primary_url'):
            urls.append(song['primary_url'])
    return urls


def find_html_file(broadcast_dir, lv_value):
    """配信ディレクトリからHTMLファイルを検索"""
    for file in os.listdir(broadcast_dir):
        if file.startswith(lv_value) and file.endswith('.html'):
            return file  # ファイル名のみを返す
    return None

def get_music_url(data):
    """音楽URLを取得"""
    music_data = data.get('music_generation', {})
    songs = music_data.get('songs', [])
    if songs and songs[0].get('primary_url'):
        return songs[0]['primary_url']
    return ''

def get_transcript_text(broadcast_dir, lv_value):
    """文字起こしテキストを取得"""
    transcript_file = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcripts = transcript_data.get('transcripts', [])
        return ' '.join([t.get('text', '') for t in transcripts])
    return ''

def process_tags(broadcast_list, tags_config):
    """タグマッチング処理"""
    for broadcast in broadcast_list:
        # 安全にフィールドを取得
        title = broadcast.get('title', '')
        summary_text = broadcast.get('summary_text', '')
        # transcript_segmentsから文字列を作成
        transcript_segments = broadcast.get('transcript_segments', [])
        transcript_text = ' '.join(transcript_segments) if transcript_segments else ''
        
        search_text = f"{title} {summary_text} {transcript_text}"
        search_text = search_text.lower()
        
        # 各タグをチェック
        for tag in tags_config:
            if tag.lower() in search_text:
                broadcast['tags'].append(tag)
    
    return broadcast_list

def generate_index_page(account_dir, broadcast_list, config):
    """メイン一覧ページ生成"""
    html_content = create_index_html(broadcast_list, config.get('tags', []))
    
    index_file = os.path.join(account_dir, 'index.html')
    with open(index_file, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"一覧ページ生成: {index_file}")

def generate_tag_pages(account_dir, broadcast_list, tags_config, config):
    """タグページ生成"""
    tags_dir = os.path.join(account_dir, 'tags')
    os.makedirs(tags_dir, exist_ok=True)
    
    for tag in tags_config:
        # そのタグを含む配信のみフィルタ
        filtered_broadcasts = [b for b in broadcast_list if tag in b['tags']]
        
        if filtered_broadcasts:
            html_content = create_tag_html(filtered_broadcasts, tag, config.get('tags', []))
            
            tag_file = os.path.join(tags_dir, f"tag_{tag}.html")
            with open(tag_file, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            print(f"タグページ生成: {tag_file} ({len(filtered_broadcasts)}件)")

def create_index_html(broadcast_list, all_tags):
    """メイン一覧HTML生成"""
    # JavaScript用データ準備
    js_data = {}
    for broadcast in broadcast_list:
        js_data[broadcast['lv_value']] = {
            'title': broadcast['title'],
            'broadcaster': broadcast['broadcaster'],
            'summary': broadcast['summary_text'],
            'imageUrl': broadcast['image_url'],
            'musicUrls': broadcast['music_urls'],  # 配列として渡す
            'comments': broadcast['transcript_segments']
        }
    
    html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配信アーカイブ一覧</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            background-color: white;
            padding: 20px;
            border-radius: 10px;
            box-shadow: 0 4px 8px rgba(0,0,0,0.1);
        }}
        .header {{
            text-align: center;
            margin-bottom: 30px;
            padding-bottom: 20px;
            border-bottom: 3px solid #007cba;
        }}
        .controls {{
            text-align: center;
            margin-bottom: 20px;
            padding: 15px;
            background-color: #f8f9fa;
            border-radius: 8px;
        }}
        .music-toggle {{
            display: inline-flex;
            align-items: center;
            gap: 10px;
            padding: 8px 15px;
            background-color: #007cba;
            color: white;
            border: none;
            border-radius: 20px;
            cursor: pointer;
            font-size: 14px;
            margin-right: 15px;
        }}
        .music-toggle.active {{
            background-color: #28a745;
        }}
        .tag-filter {{
            display: inline-block;
        }}
        .tag-button {{
            display: inline-block;
            padding: 5px 15px;
            margin: 5px;
            background-color: #007cba;
            color: white;
            text-decoration: none;
            border-radius: 15px;
            font-size: 0.9em;
            cursor: pointer;
            border: none;
        }}
        .tag-button:hover, .tag-button.active {{
            background-color: #005a8a;
        }}
        .broadcast-item {{
            position: relative;
            border: 1px solid #ddd;
            margin: 15px 0;
            padding: 20px;
            border-radius: 8px;
            background-color: #fafafa;
            transition: all 0.3s ease;
            overflow: hidden;
        }}
        .broadcast-item:hover {{
            border-color: #007cba;
            box-shadow: 0 4px 12px rgba(0,123,186,0.2);
        }}
        .broadcast-title {{
            font-size: 1.4em;
            font-weight: bold;
            color: #007cba;
            text-decoration: none;
            margin-bottom: 10px;
            display: block;
        }}
        .broadcast-title:hover {{
            color: #005a8a;
        }}
        .broadcast-info {{
            display: flex;
            gap: 30px;
            margin: 10px 0;
            flex-wrap: wrap;
        }}
        .info-item {{
            color: #666;
            font-size: 0.95em;
        }}
        .info-label {{
            font-weight: bold;
            color: #333;
        }}
        .broadcast-tags {{
            margin-top: 10px;
        }}
        .tag {{
            display: inline-block;
            background-color: #e3f2fd;
            color: #1976d2;
            padding: 3px 8px;
            margin: 2px;
            border-radius: 12px;
            font-size: 0.8em;
            border: 1px solid #bbdefb;
        }}
        .preview-popup {{
            position: absolute;
            background: white;
            border: 2px solid #007cba;
            border-radius: 10px;
            padding: 15px;
            box-shadow: 0 8px 16px rgba(0,0,0,0.3);
            z-index: 1000;
            width: 500px;
            pointer-events: none;
        }}
        .preview-image {{
            width: 100%;
            height: 250px;
            object-fit: cover;
            border-radius: 8px;
            margin-bottom: 15px;
        }}
        .preview-title {{
            font-weight: bold;
            color: #333;
            margin-bottom: 10px;
            font-size: 1.2em;
        }}
        .preview-summary {{
            color: #666;
            font-size: 0.9em;
            line-height: 1.5;
            max-height: 80px;
            overflow: hidden;
            margin-bottom: 15px;
        }}
        .preview-audio {{
            width: 100%;
            height: 30px;
        }}
        .comment-flow {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 100%;
            pointer-events: none;
            overflow: hidden;
        }}
        .comment {{
            position: absolute;
            background-color: rgba(173, 216, 230, 0.9);
            padding: 4px 10px;
            border-radius: 15px;
            font-size: 0.85em;
            white-space: nowrap;
            animation: commentFlow 10s linear infinite;
            box-shadow: 0 2px 4px rgba(0,0,0,0.2);
            max-width: 300px;
            overflow: hidden;
            text-overflow: ellipsis;
        }}
        @keyframes commentFlow {{
            from {{
                transform: translateX(100vw);
                opacity: 1;
            }}
            to {{
                transform: translateX(-100%);
                opacity: 0;
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>配信アーカイブ一覧</h1>
            <p>全{len(broadcast_list)}件の配信記録</p>
        </div>
        
        <div class="controls">
            <button class="music-toggle" id="musicToggle">
                音楽プレビュー: OFF
            </button>
            
            <div class="tag-filter">
                <button class="tag-button active" data-tag="all">すべて</button>
                {generate_tag_buttons(all_tags)}
            </div>
        </div>
        
        <div class="broadcast-list">
            {generate_broadcast_items(broadcast_list)}
        </div>
    </div>

    <script>
        const broadcastData = {json.dumps(js_data, ensure_ascii=False, indent=2)};
        
        let previewPopup = null;
        let commentIntervals = new Map();
        let musicEnabled = false;
        
        document.addEventListener('DOMContentLoaded', function() {{
            // 音楽トグル
            document.getElementById('musicToggle').addEventListener('click', function() {{
                musicEnabled = !musicEnabled;
                this.textContent = musicEnabled ? '音楽プレビュー: ON' : '音楽プレビュー: OFF';
                this.className = musicEnabled ? 'music-toggle active' : 'music-toggle';
            }});
            
            // タグフィルター
            document.querySelectorAll('.tag-button').forEach(button => {{
                button.addEventListener('click', function() {{
                    const selectedTag = this.dataset.tag;
                    filterByTag(selectedTag);
                    
                    document.querySelectorAll('.tag-button').forEach(btn => btn.classList.remove('active'));
                    this.classList.add('active');
                }});
            }});
            
            // 配信アイテムイベント
            document.querySelectorAll('.broadcast-item').forEach(item => {{
                item.addEventListener('mouseenter', function(e) {{
                    showPreview(this, e);
                    startCommentFlow(this);
                }});
                
                item.addEventListener('mouseleave', function() {{
                    hidePreview();
                    stopCommentFlow(this);
                }});
                
                item.addEventListener('mousemove', function(e) {{
                    updatePreviewPosition(e);
                }});
            }});
            document.addEventListener('DOMContentLoaded', function() {{
                // 既存のコード...
                
                // タグクリックイベント（追加）
                document.querySelectorAll('.tag').forEach(tag => {{
                    tag.addEventListener('click', function(e) {{
                        e.stopPropagation();
                        const tagName = this.dataset.tag;
                        window.location.href = `tags/tag_${{tagName}}.html`;
                    }});
                }});
            }});
        }});
        
        function filterByTag(tag) {{
            document.querySelectorAll('.broadcast-item').forEach(item => {{
                const itemTags = item.dataset.tags ? item.dataset.tags.split(',') : [];
                if (tag === 'all' || itemTags.includes(tag)) {{
                    item.style.display = 'block';
                }} else {{
                    item.style.display = 'none';
                }}
            }});
        }}
        
        function showPreview(item, event) {{
            const lvValue = item.dataset.lv;
            const data = broadcastData[lvValue];
            
            if (!data) return;
            
            previewPopup = document.createElement('div');
            previewPopup.className = 'preview-popup';
            
            if (data.imageUrl) {{
                const img = document.createElement('img');
                img.className = 'preview-image';
                img.src = data.imageUrl;
                img.onerror = function() {{
                    this.style.display = 'none';
                }};
                previewPopup.appendChild(img);
            }}
            
            const title = document.createElement('div');
            title.className = 'preview-title';
            title.textContent = data.title;
            previewPopup.appendChild(title);
            
            const summary = document.createElement('div');
            summary.className = 'preview-summary';
            summary.textContent = data.summary;
            previewPopup.appendChild(summary);
            
            if (musicEnabled && data.musicUrl) {{
                const audio = document.createElement('audio');
                audio.className = 'preview-audio';
                audio.controls = true;
                audio.volume = 0.3;
                
                const source = document.createElement('source');
                source.src = data.musicUrl;
                source.type = 'audio/mp3';
                audio.appendChild(source);
                
                previewPopup.appendChild(audio);
            }}
            
            document.body.appendChild(previewPopup);
            updatePreviewPosition(event);
        }}
        
        function hidePreview() {{
            if (previewPopup) {{
                const audio = previewPopup.querySelector('audio');
                if (audio) audio.pause();
                
                document.body.removeChild(previewPopup);
                previewPopup = null;
            }}
        }}
        
        function updatePreviewPosition(event) {{
            if (previewPopup) {{
                const mouseX = event.clientX;
                const mouseY = event.clientY;
                const popupWidth = previewPopup.offsetWidth;
                const popupHeight = previewPopup.offsetHeight;
                const windowWidth = window.innerWidth;
                const windowHeight = window.innerHeight;
                
                // X座標: マウスの左側に少し離して配置
                let x = mouseX - popupWidth - 20;  // マウスから20px左に離す
                
                // 左端が窮屈な場合は右側に表示
                if (x < 10) {{
                    x = mouseX + 20;  // マウスの右側に表示
                }}
                
                // 右端制限
                if (x + popupWidth > windowWidth - 10) {{
                    x = windowWidth - popupWidth - 10;
                }}
                
                // Y座標: マウスの中央（ポップアップの中央がマウス位置になるよう）
                let y = mouseY - (popupHeight / 2);
                
                // 上端制限
                if (y < 10) {{
                    y = 10;
                }}
                
                // 下端制限
                if (y + popupHeight > windowHeight - 10) {{
                    y = windowHeight - popupHeight - 10;
                }}
                
                previewPopup.style.left = x + 'px';
                previewPopup.style.top = y + 'px';
            }}
        }}
        
        function startCommentFlow(item) {{
            const lvValue = item.dataset.lv;
            const data = broadcastData[lvValue];
            
            if (!data || !data.comments || data.comments.length === 0) return;
            
            const commentFlow = item.querySelector('.comment-flow');
            let commentIndex = 0;
            
            const interval = setInterval(() => {{
                const comment = document.createElement('div');
                comment.className = 'comment';
                comment.textContent = data.comments[commentIndex % data.comments.length];
                comment.style.top = Math.random() * 80 + 'px';
                
                commentFlow.appendChild(comment);
                
                setTimeout(() => {{
                    if (comment.parentNode) {{
                        comment.parentNode.removeChild(comment);
                    }}
                }}, 10000);
                
                commentIndex++;
            }}, 1500);
            
            commentIntervals.set(lvValue, interval);
        }}
        
        function stopCommentFlow(item) {{
            const lvValue = item.dataset.lv;
            const interval = commentIntervals.get(lvValue);
            
            if (interval) {{
                clearInterval(interval);
                commentIntervals.delete(lvValue);
            }}
            
            const commentFlow = item.querySelector('.comment-flow');
            commentFlow.innerHTML = '';
        }}
    </script>
</body>
</html>"""
    
    return html_content

def generate_tag_buttons(tags):
    """タグボタンHTML生成"""
    buttons = []
    for tag in tags:
        buttons.append(f'<button class="tag-button" data-tag="{html.escape(tag)}">{html.escape(tag)}</button>')
    return '\n                '.join(buttons)

def generate_broadcast_items(broadcast_list):
    """配信アイテムHTML生成"""
    items = []
    for broadcast in broadcast_list:
        tags_str = ','.join(broadcast['tags'])
        
        # タグをクリック可能にしてdata-tag属性を追加
        tags_html = ''
        for tag in broadcast['tags']:
            tags_html += f'<span class="tag" data-tag="{html.escape(tag)}" style="cursor: pointer;">{html.escape(tag)}</span>'
        
        start_time_str = datetime.fromtimestamp(int(broadcast['start_time'])).strftime('%Y/%m/%d %H:%M') if broadcast['start_time'] else '不明'
        
        item_html = f"""
            <div class="broadcast-item" data-lv="{broadcast['lv_value']}" data-tags="{html.escape(tags_str)}">
                <a href="{broadcast['lv_value']}/{broadcast['html_file']}" class="broadcast-title">{html.escape(broadcast['title'])}</a>
                <div class="broadcast-info">
                    <div class="info-item">
                        <span class="info-label">配信者:</span> {html.escape(broadcast['broadcaster'])}
                    </div>
                    <div class="info-item">
                        <span class="info-label">開始時間:</span> {start_time_str}
                    </div>
                    <div class="info-item">
                        <span class="info-label">来場者数:</span> {broadcast['watch_count']}人
                    </div>
                    <div class="info-item">
                        <span class="info-label">コメント数:</span> {broadcast['comment_count']}コメ
                    </div>
                    <div class="info-item">
                        <span class="info-label">配信時間:</span> {broadcast['elapsed_time']}
                    </div>
                </div>
                <div class="broadcast-tags">
                    {tags_html}
                </div>
                <div class="comment-flow"></div>
            </div>"""
        items.append(item_html)
    
    return '\n        '.join(items)



def create_tag_html(filtered_broadcasts, tag, all_tags):
    """タグページHTML生成"""
    # メイン一覧と同じ構造だが、タイトルを変更
    html_content = create_index_html(filtered_broadcasts, all_tags)
    
    # タイトル部分を置換
    html_content = html_content.replace(
        '<h1>配信アーカイブ一覧</h1>',
        f'<h1>#{html.escape(tag)} の配信一覧</h1>'
    )
    html_content = html_content.replace(
        f'<p>全{len(filtered_broadcasts)}件の配信記録</p>',
        f'<p>タグ「{html.escape(tag)}」: {len(filtered_broadcasts)}件の配信</p>'
    )
    
    # 戻るリンク追加
    html_content = html_content.replace(
        '<div class="controls">',
        '<div style="margin-bottom: 20px;"><a href="../index.html" style="color: #007cba;">← 全配信一覧に戻る</a></div>\n        <div class="controls">'
    )
    
    return html_content

def get_transcript_segments(broadcast_dir, lv_value):
    """文字起こしセグメントを個別に取得"""
    transcript_file = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcripts = transcript_data.get('transcripts', [])
        # 空でないセグメントのみ取得、最大10個
        segments = []
        for t in transcripts:
            text = t.get('text', '').strip()
            if text and len(segments) < 10:
                segments.append(text)
        return segments
    return []