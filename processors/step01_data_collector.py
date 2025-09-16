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
import subprocess

# プロジェクトルート（このファイルの親の親をルートとする想定）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

FFMPEG_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffmpeg.exe")
FFPROBE_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffprobe.exe")


def process(pipeline_data):
    """Step01: 基本情報抽出とJSON作成"""
    try:
        lv_value = pipeline_data['lv_value']
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        ncv_directory = pipeline_data['ncv_directory']
        config = pipeline_data.get('config', {})

        # display_nameを取得（使っていないが将来用に保持）
        display_name = config.get('display_name', '')

        print(f"Step01 開始: {lv_value}")

        # 1. ディレクトリ構造作成
        account_dir = find_account_directory(platform_directory, account_id)
        broadcast_dir = os.path.join(account_dir, lv_value)
        os.makedirs(broadcast_dir, exist_ok=True)

        # 2. 元URLのHTML取得・保存とbeginTime抽出
        html_content, begin_time = fetch_and_save_html(lv_value, broadcast_dir)

        # 3. NCVのXMLファイル監視・解析（config.jsonの ncv_directory を直接探索）
        ncv_xml_path, ncv_data = wait_and_parse_ncv_xml(ncv_directory, lv_value, account_id, display_name)

        # 4. 動画ファイル名から server_time 取得
        platform_xml_path, server_time = get_server_time_from_filename(platform_directory, account_id, lv_value)

        # 5. 動画時間情報取得
        video_duration = get_video_duration(pipeline_data)

        # 6. 前回放送の要約文取得
        previous_summary = get_previous_broadcast_summary(platform_directory, account_id, lv_value)

        # 7. 統合JSON作成（beginTimeも含める）
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
        pattern = r'beginTime&quot;:(\d+)'
        match = re.search(pattern, html_content)
        if match:
            return int(match.group(1))
        # 代替パターン
        pattern2 = r'"beginTime":(\d+)'
        match2 = re.search(pattern2, html_content)
        if match2:
            return int(match2.group(1))
        return None
    except Exception as e:
        print(f"beginTime抽出エラー: {str(e)}")
        return None


def wait_and_parse_ncv_xml(ncv_directory, lv_value, account_id="", display_name=""):
    """NCVのXMLファイル監視・解析（config.jsonのncv_directoryを直接利用）"""
    actual_ncv_dir = ncv_directory  # そのまま使う

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
        account_dir = find_account_directory(platform_directory, account_id)
        xml_file = find_xml_file_containing_lv(account_dir, lv_value)

        if xml_file:
            tree = ET.parse(xml_file)
            root = tree.getroot()
            thread_elem = root.find('.//thread')  # （別形式用の古い互換・未使用想定）
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
    """指定ディレクトリ以下を再帰的に検索し、lv_valueを含むXMLファイルを探す"""
    try:
        if not os.path.exists(directory):
            return None

        for root, _, files in os.walk(directory):
            for filename in files:
                if filename.endswith('.xml') and lv_value in filename:
                    xml_path = os.path.join(root, filename)
                    print(f"XMLファイル発見: {xml_path}")
                    return xml_path
        return None

    except Exception as e:
        print(f"XMLファイル検索エラー: {str(e)}")
        return None


def parse_ncv_xml(xml_path):
    """NCVのXMLファイル解析（デフォルト名前空間対応版）"""
    try:
        tree = ET.parse(xml_path)
        root = tree.getroot()

        # デフォルト名前空間（commentlog）に対応
        ns = {'log': 'http://posite-c.jp/niconamacommentviewer/commentlog/'}

        def find_text(base, path, default=''):
            if base is None:
                return default
            elem = base.find(path, ns)
            return elem.text.strip() if (elem is not None and elem.text) else default

        # セクション取得
        live_info = root.find('.//log:LiveInfo', ns)
        player_status = root.find('.//log:PlayerStatus', ns)

        # 値取得
        live_num = find_text(root, './/log:LiveNum')
        elapsed_time = find_text(root, './/log:ElapsedTime')

        # ElapsedTime が空なら Start/End から計算
        if not elapsed_time:
            start_time = find_text(live_info, 'log:StartTime')
            end_time = find_text(live_info, 'log:EndTime')
            if start_time and end_time and start_time.isdigit() and end_time.isdigit():
                try:
                    duration_seconds = int(end_time) - int(start_time)
                    hours = duration_seconds // 3600
                    minutes = (duration_seconds % 3600) // 60
                    seconds = duration_seconds % 60
                    elapsed_time = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
                except ValueError:
                    elapsed_time = "不明"

        data = {
            'live_num': live_num,
            'elapsed_time': elapsed_time,
            'live_title': find_text(live_info, 'log:LiveTitle'),
            'broadcaster': find_text(live_info, 'log:Broadcaster'),
            'default_community': find_text(live_info, 'log:DefaultCommunity'),
            'community_name': find_text(live_info, 'log:CommunityName'),
            'open_time': find_text(live_info, 'log:OpenTime'),
            'start_time': find_text(live_info, 'log:StartTime'),
            'end_time': find_text(live_info, 'log:EndTime'),
            'watch_count': find_text(player_status, './/log:WatchCount'),   # PlayerStatus/Stream/WatchCount でも拾えるよう // を使用
            'comment_count': find_text(player_status, './/log:CommentCount'),
            'owner_id': find_text(player_status, './/log:OwnerId'),
            'owner_name': find_text(player_status, './/log:OwnerName'),
        }

        return data

    except Exception as e:
        print(f"NCVのXML解析エラー: {str(e)}")
        raise


def get_video_duration(pipeline_data):
    """動画時間情報取得"""
    try:
        platform_directory = pipeline_data['platform_directory']
        account_id = pipeline_data['account_id']
        lv_value = pipeline_data['lv_value']

        account_dir = find_account_directory(platform_directory, account_id)

        mp4_files = [
            os.path.join(account_dir, f)
            for f in os.listdir(account_dir)
            if f.endswith(".mp4") and lv_value in f
        ]

        if mp4_files:
            cmd = [
                FFPROBE_PATH,
                "-v", "quiet", "-show_entries",
                "format=duration", "-of", "csv=p=0", mp4_files[0]
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


def create_broadcast_json(lv_value, ncv_data, server_time, begin_time, video_duration,
                          previous_summary, broadcast_dir, ncv_xml_path, platform_xml_path, account_dir_path):
    """統合JSON作成"""

    # open_time と server_time の差を計算
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

        # NCVデータ（名前空間対応で正しく埋まる）
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
