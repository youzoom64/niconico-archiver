import os
import json
import math
import sys
import torch
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from faster_whisper import WhisperModel

# utils.pyからfind_account_directoryをインポート
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils import find_account_directory

def get_optimal_device_config():
    """最適なデバイスと設定を取得"""
    if torch.cuda.is_available():
        device = "cuda"
        compute_type = "float16"  # GPU用
        print(f"GPU利用可能: {torch.cuda.get_device_name()}")
        print(f"CUDA Version: {torch.version.cuda}")
    else:
        device = "cpu"
        compute_type = "int8"  # CPU用
        print("GPU利用不可、CPUモードで実行")
    
    return device, compute_type

def process(pipeline_data):
    """Step02: 音声抽出と文字起こし"""
    try:
        lv_value = pipeline_data['lv_value']
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        
        print(f"Step02 開始: {lv_value}")
        
        # 1. アカウントディレクトリ検索（utils.pyの関数を使用）
        account_dir = find_account_directory(platform_directory, account_id)
        
        # 2. 放送ディレクトリ取得
        broadcast_dir = os.path.join(account_dir, lv_value)
        
        # 3. MP4ファイル検索
        mp4_path = find_mp4_file(account_dir, lv_value)
        if not mp4_path:
            print(f"MP4ファイルが見つかりません: {lv_value} - 空の文字起こしを生成します")
            # MP4ファイルがなくても空のJSONを作成
            save_transcript_json(broadcast_dir, lv_value, [])
            return {"transcript_file": os.path.join(broadcast_dir, f"{lv_value}_transcript.json")}
        
        # 4. JSONからparsec取得
        parsec = get_time_diff_from_json(broadcast_dir, lv_value)
        
        # 5. 音声抽出・分割
        audio_files = extract_and_split_audio(mp4_path, broadcast_dir, lv_value, parsec)
        
        # 6. 文字起こし実行
        transcripts = transcribe_audio_files(audio_files, parsec, pipeline_data.get('config'))
        
        # 7. transcript.json保存（音声がなくても必ず実行）
        save_transcript_json(broadcast_dir, lv_value, transcripts)
        
        print(f"Step02 完了: {lv_value}")
        return {"transcript_file": os.path.join(broadcast_dir, f"{lv_value}_transcript.json")}
        
    except Exception as e:
        print(f"Step02 エラー: {str(e)} - 空の文字起こしを生成します")
        # エラー時も空のJSONを作成
        try:
            save_transcript_json(broadcast_dir, lv_value, [])
            return {"transcript_file": os.path.join(broadcast_dir, f"{lv_value}_transcript.json")}
        except:
            raise e

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
    """動画から音声抽出・分割（音声なし対応版）"""
    try:
        print(f"音声抽出開始: {mp4_path}")
        
        # 動画読み込み
        video = VideoFileClip(mp4_path)
        
        # 音声トラック存在チェック
        if video.audio is None:
            print("警告: 動画に音声トラックがありません - 空の文字起こしを生成します")
            video.close()
            return []  # 空のリストを返す
        
        audio = video.audio
        
        # 音声の長さチェック
        if audio.duration < 1.0:  # 1秒未満
            print("警告: 音声が短すぎます（1秒未満） - 空の文字起こしを生成します")
            video.close()
            audio.close()
            return []
        
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
        print(f"音声抽出エラー: {str(e)} - 空の文字起こしを生成します")
        return []  # エラー時も空のリストを返す

def transcribe_audio_files(audio_files, parsec, config=None):
    """音声ファイルリストを文字起こし（空リスト対応版）"""
    try:
        # 音声ファイルが空の場合の処理
        if not audio_files:
            print("音声ファイルがないため、空の文字起こし結果を返します")
            return []  # 空のリストを返す（後でJSONが生成される）
        
        print("Whisperモデル読み込み中...")
        
        # 設定から音声処理パラメータを取得
        if config:
            audio_settings = config.get('audio_settings', {})
            use_gpu = audio_settings.get('use_gpu', True)
            whisper_model = audio_settings.get('whisper_model', 'large-v3')
            cpu_threads = audio_settings.get('cpu_threads', 8)
            beam_size = audio_settings.get('beam_size', 5)
        else:
            use_gpu = True
            whisper_model = 'large-v3'
            cpu_threads = 8
            beam_size = 5
        
        # デバイス設定（ユーザー設定を考慮）
        device, compute_type = get_optimal_device_config()
        if not use_gpu:
            device = "cpu"
            compute_type = "int8"
            print("ユーザー設定によりCPUモードを強制使用")
        
        # モデル読み込み（設定値を使用）
        model = WhisperModel(
            whisper_model,
            device=device,
            compute_type=compute_type,
            num_workers=cpu_threads if device == "cpu" else 1,
            cpu_threads=cpu_threads if device == "cpu" else 0
        )
        
        all_transcripts = []
        
        for file_path, start_time in audio_files:
            print(f"文字起こし中: {os.path.basename(file_path)} (デバイス: {device}, モデル: {whisper_model})")
            
            # 設定に応じてパラメータを調整
            segments, info = model.transcribe(
                file_path,
                language="ja",
                no_speech_threshold=0.6,
                vad_filter=True,
                word_timestamps=False,
                beam_size=beam_size,  # 設定値を使用
                temperature=0.0
            )
            
            last_text = None
            segment_count = 0
            
            for segment in segments:
                current_text = segment.text.strip()
                if current_text and current_text != last_text and len(current_text) > 1:
                    # parsecにはtime_diff_secondsが既に含まれている
                    timestamp = math.ceil(segment.start + start_time + parsec)
                    timeline_block = (timestamp // 10) * 10
                    
                    transcript_entry = {
                        "timestamp": timestamp,
                        "timeline_block": timeline_block,
                        "text": current_text,
                        "positive_score": 0.0,
                        "center_score": 0.0,
                        "negative_score": 0.0
                    }
                    
                    all_transcripts.append(transcript_entry)
                    last_text = current_text
                    segment_count += 1
            
            print(f"  {segment_count}セグメント処理完了")
        
        all_transcripts.sort(key=lambda x: x['timestamp'])
        
        print(f"文字起こし完了: 総セグメント数 {len(all_transcripts)} (デバイス: {device})")
        return all_transcripts
        
    except Exception as e:
        print(f"文字起こしエラー: {str(e)} - 空の文字起こし結果を返します")
        # GPU失敗時はCPUで再試行
        if 'device' in locals() and device == "cuda":
            print("GPU処理失敗、CPUで再試行...")
            return transcribe_audio_files_cpu_fallback(audio_files, parsec)
        return []  # エラー時も空のリストを返す

def transcribe_audio_files_cpu_fallback(audio_files, parsec):
    """CPU フォールバック処理"""
    try:
        print("CPUモードで再実行中...")
        model = WhisperModel(
            "large-v2",  # CPU用はやや軽量モデル
            device="cpu",
            compute_type="int8",
            num_workers=4,
            cpu_threads=8
        )
        
        all_transcripts = []
        
        for file_path, start_time in audio_files:
            print(f"文字起こし中 (CPU): {os.path.basename(file_path)}")
            
            segments, info = model.transcribe(
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
                    # parsecにはtime_diff_secondsが既に含まれている
                    timestamp = math.ceil(segment.start + start_time + parsec)
                    timeline_block = (timestamp // 10) * 10
                    
                    transcript_entry = {
                        "timestamp": timestamp,
                        "timeline_block": timeline_block,
                        "text": current_text,
                        "positive_score": 0.0,
                        "center_score": 0.0,
                        "negative_score": 0.0
                    }
                    
                    all_transcripts.append(transcript_entry)
                    last_text = current_text
                    segment_count += 1
            
            print(f"  {segment_count}セグメント処理完了")
        
        all_transcripts.sort(key=lambda x: x['timestamp'])
        print(f"CPU文字起こし完了: 総セグメント数 {len(all_transcripts)}")
        return all_transcripts
        
    except Exception as e:
        print(f"CPU文字起こしエラー: {str(e)}")
        return []  # エラー時も空のリストを返す

def save_transcript_json(broadcast_dir, lv_value, transcripts):
    """transcript.json保存（空でも必ず保存）"""
    try:
        from datetime import datetime
        
        # 空の場合の特別なメタデータ
        if not transcripts:
            print("空の文字起こしデータでJSONを生成します")
            transcript_data = {
                "lv_value": lv_value,
                "total_segments": 0,
                "creation_time": datetime.now().isoformat(),
                "status": "no_audio_or_failed",  # ステータス追加
                "transcripts": []
            }
        else:
            transcript_data = {
                "lv_value": lv_value,
                "total_segments": len(transcripts),
                "creation_time": datetime.now().isoformat(),
                "status": "completed",  # 正常完了ステータス
                "transcripts": transcripts
            }
        
        # ディレクトリが存在しない場合は作成
        os.makedirs(broadcast_dir, exist_ok=True)
        
        json_path = os.path.join(broadcast_dir, f"{lv_value}_transcript.json")
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(transcript_data, f, ensure_ascii=False, indent=2)
        
        print(f"transcript.json保存完了: {json_path} (セグメント数: {len(transcripts)})")
        
    except Exception as e:
        print(f"transcript.json保存エラー: {str(e)}")
        raise