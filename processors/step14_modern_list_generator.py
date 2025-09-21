import os
import json
import html
from datetime import datetime
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def process(pipeline_data):
    """Step14: モダンな一覧ページ生成"""
    try:
        account_id = pipeline_data['account_id']
        config = pipeline_data['config']
        
        print(f"Step14 モダン一覧ページ生成開始: {account_id}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(pipeline_data['platform_directory'], account_id)
        
        # 2. 全配信データを収集
        broadcast_list = collect_broadcast_data(account_dir)
        
        # 3. タグ処理
        tags_config = config.get('tags', [])
        processed_broadcasts = process_tags(broadcast_list, tags_config)
        
        # 4. モダン一覧ページ生成
        generate_modern_list_page(account_dir, processed_broadcasts, tags_config)
        
        print(f"Step14 完了: {account_id} - モダン一覧ページ生成完了")
        return {"modern_list_generated": True, "broadcast_count": len(processed_broadcasts)}
        
    except Exception as e:
        print(f"Step14 エラー: {str(e)}")
        import traceback
        traceback.print_exc()
        raise

def collect_broadcast_data(account_dir):
    """アカウントディレクトリから全配信データを収集"""
    broadcast_list = []
    
    try:
        for item in os.listdir(account_dir):
            item_path = os.path.join(account_dir, item)
            
            if os.path.isdir(item_path) and item.startswith('lv'):
                lv_value = item
                
                data_file = os.path.join(item_path, f"{lv_value}_data.json")
                if os.path.exists(data_file):
                    with open(data_file, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                    
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
                            'html_file': html_file,
                            'image_url': data.get('image_generation', {}).get('imgur_url', ''),
                            'music_urls': get_music_urls(data),
                            'transcript_segments': get_transcript_segments(item_path, lv_value),
                            'tags': []
                        }
                        broadcast_list.append(broadcast_info)
        
        broadcast_list.sort(key=lambda x: x['start_time'], reverse=True)
        print(f"配信データ収集完了: {len(broadcast_list)}件")
        
    except Exception as e:
        print(f"配信データ収集エラー: {str(e)}")
    
    return broadcast_list

def find_html_file(broadcast_dir, lv_value):
    """配信ディレクトリからHTMLファイルを検索"""
    for file in os.listdir(broadcast_dir):
        if file.startswith(lv_value) and file.endswith('.html'):
            return os.path.join(lv_value, file)
    return None

def get_music_urls(data):
    """音楽URL取得"""
    music_data = data.get('music_generation', {})
    songs = music_data.get('songs', [])
    urls = []
    for song in songs:
        if song.get('primary_url'):
            urls.append(song['primary_url'])
    return urls

def get_transcript_segments(broadcast_dir, lv_value):
    """文字起こしセグメントを取得"""
    transcript_file = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
    if os.path.exists(transcript_file):
        with open(transcript_file, 'r', encoding='utf-8') as f:
            transcript_data = json.load(f)
        
        transcripts = transcript_data.get('transcripts', [])
        segments = []
        for t in transcripts:
            text = t.get('text', '').strip()
            if text and len(segments) < 10:
                segments.append(text)
        return segments
    return []

def process_tags(broadcast_list, tags_config):
    """タグマッチング処理"""
    for broadcast in broadcast_list:
        search_text = f"{broadcast['title']} {broadcast['summary_text']}"
        if broadcast.get('transcript_segments'):
            search_text += " " + " ".join(broadcast['transcript_segments'])
        search_text = search_text.lower()
        
        for tag in tags_config:
            if tag.lower() in search_text:
                broadcast['tags'].append(tag)
    
    return broadcast_list

def generate_modern_list_page(account_dir, broadcast_list, tags_config):
    """モダンでインタラクティブな配信一覧ページ生成"""
    try:
        # JavaScriptデータ準備
        js_data = {}
        for broadcast in broadcast_list:
            js_data[broadcast['lv_value']] = {
                'title': broadcast['title'],
                'broadcaster': broadcast['broadcaster'],
                'summary': broadcast['summary_text'],
                'imageUrl': broadcast['image_url'],
                'musicUrls': broadcast['music_urls'],
                'transcriptSegments': broadcast['transcript_segments'],
                'tags': broadcast['tags']
            }
        
        html_content = f"""<!DOCTYPE html>
<html lang="ja">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>配信アーカイブ一覧</title>
    <style>
        * {{
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }}
        
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: #333;
        }}
        
        .container {{
            max-width: 1200px;
            margin: 0 auto;
            padding: 2rem;
        }}
        
        .header {{
            text-align: center;
            margin-bottom: 3rem;
            color: white;
        }}
        
        .header h1 {{
            font-size: 3rem;
            font-weight: 300;
            margin-bottom: 0.5rem;
            text-shadow: 0 2px 10px rgba(0,0,0,0.3);
        }}
        
        .header p {{
            font-size: 1.2rem;
            opacity: 0.9;
        }}
        
        .controls {{
            display: flex;
            justify-content: center;
            gap: 1rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .control-btn {{
            background: rgba(255,255,255,0.2);
            color: white;
            border: 2px solid rgba(255,255,255,0.3);
            padding: 0.8rem 1.5rem;
            border-radius: 50px;
            cursor: pointer;
            transition: all 0.3s ease;
            backdrop-filter: blur(10px);
            font-weight: 500;
            text-decoration: none;
            display: inline-block;
        }}
        
        .control-btn:hover, .control-btn.active {{
            background: rgba(255,255,255,0.3);
            border-color: rgba(255,255,255,0.5);
            transform: translateY(-2px);
            box-shadow: 0 5px 15px rgba(0,0,0,0.2);
        }}
        
        .tag-controls {{
            display: flex;
            justify-content: center;
            gap: 0.5rem;
            margin-bottom: 2rem;
            flex-wrap: wrap;
        }}
        
        .tag-btn {{
            background: rgba(255,255,255,0.1);
            color: white;
            border: 1px solid rgba(255,255,255,0.2);
            padding: 0.5rem 1rem;
            border-radius: 25px;
            cursor: pointer;
            transition: all 0.3s ease;
            font-size: 0.9rem;
            text-decoration: none;
        }}
        
        .tag-btn:hover, .tag-btn.active {{
            background: rgba(255,255,255,0.2);
            border-color: rgba(255,255,255,0.4);
        }}
        
        .broadcast-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fill, minmax(400px, 1fr));
            gap: 2rem;
        }}
        
        .broadcast-item {{
            position: relative;
            background: rgba(255,255,255,0.95);
            border-radius: 20px;
            overflow: hidden;
            box-shadow: 0 10px 30px rgba(0,0,0,0.2);
            transition: all 0.4s cubic-bezier(0.175, 0.885, 0.32, 1.275);
            cursor: pointer;
        }}
        
        .broadcast-item:hover {{
            transform: translateY(-10px) scale(1.02);
            box-shadow: 0 20px 50px rgba(0,0,0,0.3);
        }}
        
        .broadcast-item::before {{
            content: '';
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            height: 4px;
            background: linear-gradient(90deg, #667eea, #764ba2);
        }}
        
        .broadcast-content {{
            padding: 1.5rem;
        }}
        
        .broadcast-title {{
            font-size: 1.3rem;
            font-weight: 600;
            color: #333;
            margin-bottom: 1rem;
            line-height: 1.4;
            display: -webkit-box;
            -webkit-line-clamp: 2;
            -webkit-box-orient: vertical;
            overflow: hidden;
        }}
        
        .broadcast-meta {{
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 0.5rem;
            margin-bottom: 1rem;
            font-size: 0.9rem;
            color: #666;
        }}
        
        .meta-item {{
            display: flex;
            align-items: center;
            gap: 0.5rem;
        }}
        
        .broadcast-tags {{
            display: flex;
            flex-wrap: wrap;
            gap: 0.5rem;
            margin-top: 1rem;
        }}
        
        .broadcast-tag {{
            background: rgba(102, 126, 234, 0.1);
            color: #667eea;
            padding: 0.3rem 0.8rem;
            border-radius: 15px;
            font-size: 0.8rem;
            border: 1px solid rgba(102, 126, 234, 0.2);
        }}
        
        .comment-flow {{
            position: absolute;
            top: 0;
            left: 0;
            right: 0;
            bottom: 0;
            pointer-events: none;
            overflow: hidden;
            opacity: 0;
            transition: opacity 0.3s ease;
        }}
        
        .broadcast-item:hover .comment-flow {{
            opacity: 1;
        }}
        
        .flowing-comment {{
            position: absolute;
            background: rgba(102, 126, 234, 0.9);
            color: white;
            padding: 0.5rem 1rem;
            border-radius: 20px;
            font-size: 0.85rem;
            white-space: nowrap;
            animation: commentSlide 8s linear infinite;
            backdrop-filter: blur(5px);
            box-shadow: 0 2px 10px rgba(0,0,0,0.2);
        }}
        
        @keyframes commentSlide {{
            from {{
                transform: translateX(100%);
                opacity: 1;
            }}
            to {{
                transform: translateX(-100%);
                opacity: 0;
            }}
        }}
        
        .preview-popup {{
            position: fixed;
            background: white;
            border-radius: 15px;
            box-shadow: 0 20px 60px rgba(0,0,0,0.3);
            z-index: 1000;
            pointer-events: none;
            opacity: 0;
            transform: scale(0.8);
            transition: all 0.3s ease;
            max-width: 500px;
            overflow: hidden;
        }}
        
        .preview-popup.show {{
            opacity: 1;
            transform: scale(1);
        }}
        
        .preview-image {{
            width: 100%;
            height: 200px;
            object-fit: cover;
        }}
        
        .preview-content {{
            padding: 1.5rem;
        }}
        
        .preview-title {{
            font-weight: 600;
            margin-bottom: 1rem;
            color: #333;
        }}
        
        .preview-summary {{
            color: #666;
            line-height: 1.5;
            margin-bottom: 1rem;
            font-size: 0.9rem;
        }}
        
        .preview-audio {{
            width: 100%;
            height: 40px;
            border-radius: 20px;
        }}
        
        @media (max-width: 768px) {{
            .container {{
                padding: 1rem;
            }}
            
            .header h1 {{
                font-size: 2rem;
            }}
            
            .broadcast-grid {{
                grid-template-columns: 1fr;
                gap: 1rem;
            }}
            
            .broadcast-meta {{
                grid-template-columns: 1fr;
            }}
        }}
        
        .fade-in {{
            opacity: 0;
            transform: translateY(20px);
            animation: fadeInUp 0.6s ease forwards;
        }}
        
        @keyframes fadeInUp {{
            to {{
                opacity: 1;
                transform: translateY(0);
            }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header fade-in">
            <h1>配信アーカイブ</h1>
            <p>全{len(broadcast_list)}件の配信記録</p>
        </div>
        
        <div class="controls fade-in">
            <button class="control-btn active" data-action="all">すべて表示</button>
            <button class="control-btn" data-action="music" id="musicToggle">音楽プレビュー</button>
            <a href="index.html" class="control-btn">詳細一覧へ</a>
        </div>
        
        <div class="tag-controls fade-in">
            <button class="tag-btn active" data-tag="all">すべて</button>
            {generate_tag_buttons(tags_config)}
        </div>
        
        <div class="broadcast-grid">
            {generate_broadcast_cards(broadcast_list)}
        </div>
    </div>

    <div class="preview-popup" id="previewPopup">
        <img class="preview-image" id="previewImage" alt="配信画像">
        <div class="preview-content">
            <div class="preview-title" id="previewTitle"></div>
            <div class="preview-summary" id="previewSummary"></div>
            <audio class="preview-audio" id="previewAudio" controls style="display: none;">
                <source type="audio/mp3">
            </audio>
        </div>
    </div>

    <script>
        const broadcastData = {json.dumps(js_data, ensure_ascii=False, indent=2)};
        let musicEnabled = false;
        let commentIntervals = new Map();
        let previewPopup = null;
        
        document.addEventListener('DOMContentLoaded', function() {{
            // アニメーション遅延適用
            document.querySelectorAll('.broadcast-item').forEach((item, index) => {{
                item.style.animationDelay = `${{index * 0.1}}s`;
                item.classList.add('fade-in');
            }});
            
            // コントロールボタン
            document.getElementById('musicToggle').addEventListener('click', function() {{
                musicEnabled = !musicEnabled;
                this.textContent = musicEnabled ? '音楽プレビュー ON' : '音楽プレビュー';
                this.classList.toggle('active');
            }});
            
            // タグフィルター
            document.querySelectorAll('.tag-btn').forEach(btn => {{
                btn.addEventListener('click', function() {{
                    const selectedTag = this.dataset.tag;
                    filterByTag(selectedTag);
                    
                    document.querySelectorAll('.tag-btn').forEach(b => b.classList.remove('active'));
                    this.classList.add('active');
                }});
            }});
            
            // プレビューポップアップ要素
            previewPopup = document.getElementById('previewPopup');
            
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
                
                item.addEventListener('mousemove', updatePreviewPosition);
                
                item.addEventListener('click', function() {{
                    const link = this.querySelector('a');
                    if (link) link.click();
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
            
            // 画像設定
            const img = document.getElementById('previewImage');
            if (data.imageUrl) {{
                img.src = data.imageUrl;
                img.style.display = 'block';
            }} else {{
                img.style.display = 'none';
            }}
            
            // テキスト設定
            document.getElementById('previewTitle').textContent = data.title;
            document.getElementById('previewSummary').textContent = data.summary || '要約なし';
            
            // 音楽設定
            const audio = document.getElementById('previewAudio');
            if (musicEnabled && data.musicUrls && data.musicUrls.length > 0) {{
                audio.src = data.musicUrls[0];
                audio.style.display = 'block';
                audio.volume = 0.3;
            }} else {{
                audio.style.display = 'none';
            }}
            
            previewPopup.classList.add('show');
            updatePreviewPosition(event);
        }}
        
        function hidePreview() {{
            previewPopup.classList.remove('show');
            const audio = document.getElementById('previewAudio');
            audio.pause();
        }}
        
        function updatePreviewPosition(event) {{
            if (!previewPopup.classList.contains('show')) return;
            
            const x = Math.min(event.clientX + 20, window.innerWidth - previewPopup.offsetWidth - 20);
            const y = Math.max(event.clientY - previewPopup.offsetHeight - 20, 20);
            
            previewPopup.style.left = x + 'px';
            previewPopup.style.top = y + 'px';
        }}
        
        function startCommentFlow(item) {{
            const lvValue = item.dataset.lv;
            const data = broadcastData[lvValue];
            
            if (!data || !data.transcriptSegments || data.transcriptSegments.length === 0) return;
            
            const commentFlow = item.querySelector('.comment-flow');
            let commentIndex = 0;
            
            const interval = setInterval(() => {{
                const comment = document.createElement('div');
                comment.className = 'flowing-comment';
                comment.textContent = data.transcriptSegments[commentIndex % data.transcriptSegments.length];
                comment.style.top = Math.random() * 70 + '%';
                comment.style.animationDelay = '0s';
                
                commentFlow.appendChild(comment);
                
                setTimeout(() => {{
                    if (comment.parentNode) {{
                        comment.parentNode.removeChild(comment);
                    }}
                }}, 8000);
                
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
        
        list_file = os.path.join(account_dir, 'modern_list.html')
        with open(list_file, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        print(f"モダン一覧ページ生成: {list_file}")
        
    except Exception as e:
        print(f"一覧ページ生成エラー: {str(e)}")
        raise

def generate_tag_buttons(tags_config):
    """タグボタンHTML生成"""
    buttons = []
    for tag in tags_config:
        buttons.append(f'<a href="tags/tag_{html.escape(tag)}.html" class="tag-btn">{html.escape(tag)}</a>')
    return '\n            '.join(buttons)

def generate_broadcast_cards(broadcast_list):
    """配信カードHTML生成"""
    cards = []
    
    for i, broadcast in enumerate(broadcast_list):
        start_time_str = datetime.fromtimestamp(int(broadcast['start_time'])).strftime('%m/%d %H:%M') if broadcast['start_time'] else '不明'
        tags_str = ','.join(broadcast['tags'])
        tags_html = ''.join([f'<span class="broadcast-tag">{html.escape(tag)}</span>' for tag in broadcast['tags']])
        
        card_html = f"""
            <div class="broadcast-item" data-lv="{broadcast['lv_value']}" data-tags="{html.escape(tags_str)}" style="animation-delay: {i * 0.1}s;">
                <div class="broadcast-content">
                    <a href="{broadcast['html_file']}" style="text-decoration: none; color: inherit;">
                        <h3 class="broadcast-title">{html.escape(broadcast['title'])}</h3>
                    </a>
                    
                    <div class="broadcast-meta">
                        <div class="meta-item">
                            <span>👤</span>
                            <span>{html.escape(broadcast['broadcaster'])}</span>
                        </div>
                        <div class="meta-item">
                            <span>🕒</span>
                            <span>{start_time_str}</span>
                        </div>
                        <div class="meta-item">
                            <span>👥</span>
                            <span>{broadcast['watch_count']}人</span>
                        </div>
                        <div class="meta-item">
                            <span>💬</span>
                            <span>{broadcast['comment_count']}コメ</span>
                        </div>
                    </div>
                    
                    <div class="broadcast-tags">
                        {tags_html}
                    </div>
                </div>
                
                <div class="comment-flow"></div>
            </div>"""
        
        cards.append(card_html)
    
    return '\n        '.join(cards)