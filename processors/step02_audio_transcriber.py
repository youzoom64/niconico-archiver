import os
import json
import math
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from faster_whisper import WhisperModel

def process(pipeline_data):
    """Step02: 音声抽出と文字起こし"""
    try:
        lv_value = pipeline_data['lv_value']
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        
        print(f"Step02 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索
        account_dir = find_account_directory(platform_directory, account_id)
        
        # 2. 放送ディレクトリ取得
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. MP4ファイル検索
        mp4_path = find_mp4_file(account_dir, lv_value)
        if not mp4_path:
            raise Exception(f"MP4ファイルが見つかりません: {lv_value}")
        
        # 4. JSONからparsec取得
        parsec = get_time_diff_from_json(broadcast_dir, lv_value)
        
        # 5. 音声抽出・分割
        audio_files = extract_and_split_audio(mp4_path, broadcast_dir, lv_value, parsec)
        
        # 6. 文字起こし実行
        transcripts = transcribe_audio_files(audio_files, parsec)
        
        # 7. transcript.json保存
        save_transcript_json(broadcast_dir, lv_value, transcripts)
        
        print(f"Step02 完了: {lv_value}")
        return {"transcript_file": os.path.join(broadcast_dir, f"{lv_value}_transcript.json")}
        
    except Exception as e:
        print(f"Step02 エラー: {str(e)}")
        raise

def find_account_directory(platform_directory, account_id):
    """アカウントIDを含むディレクトリを検索"""
    try:
        if not os.path.exists(platform_directory):
            raise Exception(f"監視ディレクトリが存在しません: {platform_directory}")
        
        # ディレクトリ一覧を取得
        for dirname in os.listdir(platform_directory):
            dir_path = os.path.join(platform_directory, dirname)
            
            if os.path.isdir(dir_path):
                # アンダースコア前の数字部分を抽出
                if '_' in dirname:
                    id_part = dirname.split('_')[0]
                else:
                    id_part = dirname
                
                # アカウントIDと一致するかチェック
                if id_part == account_id:
                    print(f"アカウントディレクトリ発見: {dir_path}")
                    return dir_path
        
        raise Exception(f"アカウントID {account_id} のディレクトリが見つかりません")
        
    except Exception as e:
        print(f"ディレクトリ検索エラー: {str(e)}")
        raise

def find_mp4_file(account_dir, lv_value):
    """MP4ファイルを検索"""
    if not os.path.exists(account_dir):
        return None
    
    for filename in os.listdir(account_dir):
        if filename.endswith('.mp4') and lv_value in filename:
            mp4_path = os.path.join(account_dir, filename)
            print(f"MP4ファイル発見: {mp4_path}")
            return mp4_path
    
    return None

def get_time_diff_from_json(broadcast_dir, lv_value):
    """JSONファイルからtime_diff_seconds取得"""
    try:
        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        if os.path.exists(json_path):
            with open(json_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                parsec = data.get('time_diff_seconds', 0)
                print(f"時間差（parsec）: {parsec}秒")
                return parsec
        
        print("JSONファイルが見つからないため、parsecを0に設定")
        return 0
        
    except Exception as e:
        print(f"parsec取得エラー: {str(e)}")
        return 0

def extract_and_split_audio(mp4_path, broadcast_dir, lv_value, parsec=0):
    """動画から音声抽出・分割"""
    try:
        print(f"音声抽出開始: {mp4_path}")
        
        # 動画読み込み
        video = VideoFileClip(mp4_path)
        audio = video.audio
        
        # 全体音声保存
        full_audio_path = os.path.join(broadcast_dir, f"{lv_value}_full_audio.mp3")
        audio.write_audiofile(full_audio_path, codec="mp3", verbose=False, logger=None)
        
        # 音声を読み込み
        audio_segment = AudioSegment.from_mp3(full_audio_path)
        
        # parsecが正の値の場合、先頭に無音追加
        if parsec > 0:
            print(f"先頭に{parsec}秒の無音を追加")
            silence = AudioSegment.silent(duration=parsec * 1000)
            audio_segment = silence + audio_segment
            
            # 無音追加版を保存
            silent_audio_path = os.path.join(broadcast_dir, f"{lv_value}_silent_audio.mp3")
            audio_segment.export(silent_audio_path, format="mp3")
        
        # 180分（10800秒）ごとに分割
        duration = 10800  # 180分
        audio_files = []
        
        total_length = len(audio_segment)
        print(f"音声総時間: {total_length/1000:.1f}秒")
        
        for start in range(0, total_length, duration * 1000):
            end = min(start + (duration * 1000), total_length)
            chunk_num = (start // (duration * 1000)) + 1
            chunk_path = os.path.join(broadcast_dir, f"{lv_value}_audio_chunk_{chunk_num}.mp3")
            
            audio_chunk = audio_segment[start:end]
            audio_chunk.export(chunk_path, format="mp3")
            
            start_seconds = start // 1000
            audio_files.append((chunk_path, start_seconds))
            print(f"音声チャンク保存: chunk_{chunk_num} (開始: {start_seconds}秒)")
        
        video.close()
        audio.close()
        
        return audio_files
        
    except Exception as e:
        print(f"音声抽出エラー: {str(e)}")
        raise

def transcribe_audio_files(audio_files, parsec):
    """音声ファイルリストを文字起こし"""
    try:
        print("Whisperモデル読み込み中...")
        model = WhisperModel("large-v2", device="cpu", compute_type="int8")
        all_transcripts = []
        
        for file_path, start_time in audio_files:
            print(f"文字起こし中: {os.path.basename(file_path)}")
            
            segments, _ = model.transcribe(
                file_path,
                language="ja",
                no_speech_threshold=0.6,
                vad_filter=True,
                word_timestamps=False
            )
            
            last_text = None
            segment_count = 0
            
            for segment in segments:
                current_text = segment.text.strip()
                if current_text and current_text != last_text and len(current_text) > 1:
                    # タイムスタンプ計算（parsecも考慮）
                    timestamp = math.ceil(segment.start + start_time + parsec)
                    
                    transcript_entry = {
                        "timestamp": timestamp,
                        "text": current_text,
                        "positive_score": 0.0,
                        "center_score": 0.0,
                        "negative_score": 0.0
                    }
                    
                    all_transcripts.append(transcript_entry)
                    last_text = current_text
                    segment_count += 1
            
            print(f"  {segment_count}セグメント処理完了")
        
        # タイムスタンプでソート
        all_transcripts.sort(key=lambda x: x['timestamp'])
        
        print(f"文字起こし完了: 総セグメント数 {len(all_transcripts)}")
        return all_transcripts
        
    except Exception as e:
        print(f"文字起こしエラー: {str(e)}")
        raise

def save_transcript_json(broadcast_dir, lv_value, transcripts):
    """transcript.json保存"""
    try:
        from datetime import datetime
        
        transcript_data = {
            "lv_value": lv_value,
            "total_segments": len(transcripts),
            "creation_time": datetime.now().isoformat(),
            "transcripts": transcripts
        }
        
        json_path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"transcript.json保存完了: {json_path}")
        
    except Exception as e:
        print(f"transcript.json保存エラー: {str(e)}")
        raise