import os
import re
import json
import time
import xml.etree.ElementTree as ET
import requests
from datetime import datetime
import subprocess
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory


def process(pipeline_data):
    """Step01: 基本情報抽出とJSON作成"""
    try:
        lv_value = pipeline_data['lv_value']
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        ncv_directory = pipeline_data['ncv_directory']
        config = pipeline_data.get('config', {})
        
        # display_nameを取得
        display_name = config.get('display_name', '')
        
        print(f"Step01 開始: {lv_value}")
        
        # 1. ディレクトリ構造作成
        account_dir = find_account_directory(platform_directory, account_id)
        broadcast_dir = os.path.join(account_dir, lv_value)
        os.makedirs(broadcast_dir, exist_ok=True)

        # 2. 元URLのHTML取得・保存とbeginTime抽出
        html_content, begin_time = fetch_and_save_html(lv_value, broadcast_dir)
        
        # 3. NCVのXMLファイル監視・解析（新しい構造対応）
        ncv_xml_path, ncv_data = wait_and_parse_ncv_xml(ncv_directory, lv_value, account_id, display_name)

        # 4. 動画ファイル名からserver_time取得  
        platform_xml_path, server_time = get_server_time_from_filename(platform_directory, account_id, lv_value)
                
        # 5. 動画時間情報取得
        video_duration = get_video_duration(pipeline_data)
        
        # 6. 前回放送の要約文取得
        previous_summary = get_previous_broadcast_summary(platform_directory, account_id, lv_value)
        
        # 7. 統合JSON作成（beginTimeを追加）
        broadcast_data = create_broadcast_json(
            lv_value, ncv_data, server_time, begin_time, video_duration, 
            previous_summary, broadcast_dir, ncv_xml_path, platform_xml_path, account_dir
        )
        
        print(f"Step01 完了: {lv_value}")
        return broadcast_data
        
    except Exception as e:
        print(f"Step01 エラー: {str(e)}")
        raise

def get_server_time_from_filename(platform_directory, account_id, lv_value):
    """動画ファイル名からserver_time取得"""
    try:
        account_dir = find_account_directory(platform_directory, account_id)
        
        # 対象の動画ファイルを検索
        for filename in os.listdir(account_dir):
            if filename.endswith('.mp4') and lv_value in filename:
                # ファイル名からタイムスタンプ抽出
                pattern = r'lv\d+_(\d{4})_(\d{2})(\d{2})_(\d{2})(\d{2})(\d{2})_'
                match = re.search(pattern, filename)
                
                if match:
                    year = int(match.group(1))
                    month = int(match.group(2))
                    day = int(match.group(3))
                    hour = int(match.group(4))
                    minute = int(match.group(5))
                    second = int(match.group(6))
                    
                    dt = datetime(year, month, day, hour, minute, second)
                    server_time = str(int(dt.timestamp()))
                    
                    print(f"動画ファイル名からserver_time取得: {server_time}")
                    return "", server_time
        
        print(f"対象の動画ファイルが見つかりません: {lv_value}")
        return "", ""
        
    except Exception as e:
        print(f"ファイル名からserver_time取得エラー: {str(e)}")
        return "", ""


def fetch_and_save_html(lv_value, broadcast_dir):
    """元URLのHTML取得・保存とbeginTime抽出"""
    try:
        url = f"https://live.nicovideo.jp/watch/{lv_value}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        response = requests.get(url, headers=headers, timeout=30)
        response.raise_for_status()
        
        html_content = response.text
        
        # HTMLを保存
        html_path = os.path.join(broadcast_dir, f"{lv_value}.html")
        with open(html_path, 'w', encoding='utf-8') as f:
            f.write(html_content)
        
        # beginTimeを抽出
        begin_time = extract_begin_time(html_content)
        
        print(f"HTML保存完了: {html_path}")
        if begin_time:
            print(f"beginTime抽出: {begin_time}")
            
        return html_content, begin_time
        
    except Exception as e:
        print(f"HTML取得エラー: {str(e)}")
        return None, None

def extract_begin_time(html_content):
    """HTMLからbeginTimeを抽出"""
    try:
        import re
        # beginTime&quot;:数字 のパターンを検索
        pattern = r'beginTime&quot;:(\d+)'
        match = re.search(pattern, html_content)
        
        if match:
            return int(match.group(1))
        else:
            # 別のパターンも試す
            pattern2 = r'"beginTime":(\d+)'
            match2 = re.search(pattern2, html_content)
            if match2:
                return int(match2.group(1))
            
        return None
        
    except Exception as e:
        print(f"beginTime抽出エラー: {str(e)}")
        return None

def wait_and_parse_ncv_xml(ncv_directory, lv_value, account_id="", display_name=""):
    """NCVのXMLファイル監視・解析（新しいディレクトリ構造対応）"""
    
    # 新しいディレクトリ構造を考慮
    if account_id:
        from utils import find_ncv_directory
        actual_ncv_dir = find_ncv_directory(ncv_directory, account_id, display_name)
    else:
        actual_ncv_dir = ncv_directory
    
    for i in range(60):
        try:
            xml_file = find_xml_file_containing_lv(actual_ncv_dir, lv_value)
            if xml_file:
                ncv_data = parse_ncv_xml(xml_file)
                return xml_file, ncv_data
        except Exception as e:
            print(f"XML解析エラー(試行{i+1}): {str(e)}")
        time.sleep(1)
    
    raise Exception(f"NCVのXMLファイルが見つかりません: {lv_value}")

def get_server_time_from_xml(platform_directory, lv_value, account_id):
    """監視ディレクトリのXMLからserver_time取得（ファイル名部分一致対応）"""
    try:
        # アカウントディレクトリ内を検索
        account_dir = find_account_directory(platform_directory, account_id)
        xml_file = find_xml_file_containing_lv(account_dir, lv_value)
        
        if xml_file:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            
            # <thread>要素からserver_timeを取得
            thread_elem = root.find('.//thread')
            if thread_elem is not None:
                server_time = thread_elem.get('server_time', '')
                print(f"server_time取得成功: {server_time}")
                return xml_file, server_time
            else:
                print("thread要素が見つかりません")
        else:
            print(f"XMLファイルが見つかりません: {account_dir}")
        
        return "", ""
        
    except Exception as e:
        print(f"server_time取得エラー: {str(e)}")
        return "", ""

def find_xml_file_containing_lv(directory, lv_value):
    """指定ディレクトリでlv_valueを含むXMLファイルを検索"""
    try:
        if not os.path.exists(directory):
            return None
            
        for filename in os.listdir(directory):
            if filename.endswith('.xml') and lv_value in filename:
                xml_path = os.path.join(directory, filename)
                print(f"XMLファイル発見: {xml_path}")
                return xml_path
        
        return None
        
    except Exception as e:
        print(f"XMLファイル検索エラー: {str(e)}")
        return None

def parse_ncv_xml(xml_path):
    """NCVのXMLファイル解析"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()
        
        # 名前空間を考慮
        ns = {'ncv': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}
        
        # LiveInfo取得
        live_info = root.find('.//LiveInfo', ns) or root.find('.//LiveInfo')
        player_status = root.find('.//PlayerStatus', ns) or root.find('.//PlayerStatus')
        
        # elapsed_timeを取得、空の場合は計算する
        elapsed_time = get_text_content(root, './/ElapsedTime')
        if not elapsed_time:
            # ElapsedTimeが取得できない場合、StartTimeとEndTimeから計算
            start_time = get_text_content(live_info, './/StartTime')
            end_time = get_text_content(live_info, './/EndTime')
            if start_time and end_time:
                try:
                    duration_seconds = int(end_time) - int(start_time)
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    seconds = duration_seconds % 60
                    elapsed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except ValueError:
                    elapsed_time = "不明"
        
        data = {
            'live_num': get_text_content(root, './/LiveNum'),
            'elapsed_time': elapsed_time,
            'live_title': get_text_content(live_info, './/LiveTitle'),
            'broadcaster': get_text_content(live_info, './/Broadcaster'),
            'default_community': get_text_content(live_info, './/DefaultCommunity'),
            'community_name': get_text_content(live_info, './/CommunityName'),
            'open_time': get_text_content(live_info, './/OpenTime'),
            'start_time': get_text_content(live_info, './/StartTime'),
            'end_time': get_text_content(live_info, './/EndTime'),
            'watch_count': get_text_content(player_status, './/WatchCount'),
            'comment_count': get_text_content(player_status, './/CommentCount'),
            'owner_id': get_text_content(player_status, './/OwnerId'),
            'owner_name': get_text_content(player_status, './/OwnerName')
        }
        
        return data
        
    except Exception as e:
        print(f"NCVのXML解析エラー: {str(e)}")
        raise

def get_text_content(element, xpath):
    """XMLから安全にテキスト取得"""
    if element is None:
        return ""
    found = element.find(xpath)
    return found.text if found is not None and found.text else ""

def get_video_duration(pipeline_data):
    """動画時間情報取得"""
    try:
        platform_directory = pipeline_data['platform_directory']
        account_id = pipeline_data['account_id']
        lv_value = pipeline_data['lv_value']
        
        # アカウントディレクトリからMP4ファイルを探す
        account_dir = find_account_directory(platform_directory, account_id)
        
        mp4_files = []
        for file in os.listdir(account_dir):
            if file.endswith('.mp4') and lv_value in file:
                mp4_files.append(os.path.join(account_dir, file))
        
        if mp4_files:
            # ffprobeで動画時間取得
            cmd = [
                'ffprobe', '-v', 'quiet', '-show_entries', 
                'format=duration', '-of', 'csv=p=0', mp4_files[0]
            ]
            result = subprocess.run(cmd, capture_output=True, text=True)
            if result.returncode == 0:
                return float(result.stdout.strip())
        
        return 0.0
        
    except Exception as e:
        print(f"動画時間取得エラー: {str(e)}")
        return 0.0
    

def get_previous_broadcast_summary(platform_directory, account_id, current_lv_value):
    """前回放送の要約文取得"""
    try:
        account_dir = find_account_directory(platform_directory, account_id)
        
        # 現在のlv値から数値部分を抽出
        current_num = int(re.search(r'lv(\d+)', current_lv_value).group(1))
        
        # 一つ前の放送を探す
        for i in range(1, 100):
            prev_lv = f"lv{current_num - i}"
            prev_dir = os.path.join(account_dir, prev_lv)
            
            if os.path.exists(prev_dir):
                # JSONファイルを探す
                for file in os.listdir(prev_dir):
                    if file.endswith('.json'):
                        json_path = os.path.join(prev_dir, file)
                        with open(json_path, 'r', encoding='utf-8') as f:
                            data = json.load(f)
                            summary = data.get('summary_text', '')
                            if summary:
                                print(f"前回放送の要約取得: {prev_lv}")
                                return summary
        
        return ""
        
    except Exception as e:
        print(f"前回放送要約取得エラー: {str(e)}")
        return ""

def create_broadcast_json(lv_value, ncv_data, server_time, begin_time, video_duration, previous_summary, broadcast_dir, ncv_xml_path, platform_xml_path, account_dir_path):
    """統合JSON作成"""
    
    # open_timeとserver_timeの差を計算
    time_diff_seconds = calculate_time_difference(ncv_data.get('open_time', ''), server_time)
   
    broadcast_data = {
        'lv_value': lv_value,
        'timestamp': datetime.now().isoformat(),
        'server_time': server_time,
        'begin_time': begin_time,  # beginTimeを追加
        'video_duration': video_duration,
        'time_diff_seconds': time_diff_seconds,
        
        # ディレクトリパス
        'account_directory_path': account_dir_path,
        'broadcast_directory_path': broadcast_dir,
        
        # XMLファイルパス
        'ncv_xml_path': ncv_xml_path,
        'platform_xml_path': platform_xml_path,
        
        # NCVデータ
        'live_num': ncv_data.get('live_num', ''),
        'elapsed_time': ncv_data.get('elapsed_time', ''),
        'live_title': ncv_data.get('live_title', ''),
        'broadcaster': ncv_data.get('broadcaster', ''),
        'default_community': ncv_data.get('default_community', ''),
        'community_name': ncv_data.get('community_name', ''),
        'open_time': ncv_data.get('open_time', ''),
        'start_time': ncv_data.get('start_time', ''),
        'end_time': ncv_data.get('end_time', ''),
        'watch_count': ncv_data.get('watch_count', ''),
        'comment_count': ncv_data.get('comment_count', ''),
        'owner_id': ncv_data.get('owner_id', ''),
        'owner_name': ncv_data.get('owner_name', ''),
        
        # 前回放送情報
        'previous_summary': previous_summary,
        
        # 後で追加される項目（空で初期化）
        'summary_text': '',
        'intro_chat': [],
        'outro_chat': []
    }
    
    # JSON保存
    json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
    with open(json_path, 'w', encoding='utf-8') as f:
        json.dump(broadcast_data, f, ensure_ascii=False, indent=2)
    
    print(f"JSON保存完了: {json_path}")
    return broadcast_data

def calculate_time_difference(open_time, server_time):
    """open_timeとserver_timeの差を秒で計算"""
    try:
        if not open_time or not server_time:
            return 0
        
        open_time_int = int(open_time)
        server_time_int = int(server_time)
        
        diff_seconds = server_time_int - open_time_int
        return diff_seconds
        
    except (ValueError, TypeError) as e:
        print(f"時間差計算エラー: {str(e)}")
        return 0