import os
import json
import math
import sys
import torch
from moviepy.editor import VideoFileClip
from pydub import AudioSegment
from faster_whisper import WhisperModel

# プロジェクトルート（このファイルの親の親をルートとする想定）
PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# ffmpeg / ffprobe のパス（リポジトリ直下の ffmpeg\bin を想定）
FFMPEG_PATH  = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffmpeg.exe")
FFPROBE_PATH = os.path.join(PROJECT_ROOT, "ffmpeg", "bin", "ffprobe.exe")

def _wire_ffmpeg():
    """pydub / moviepy / faster-whisper すべてが ffmpeg/ffprobe を見つけられるよう統一設定"""
    bin_dir = os.path.dirname(FFMPEG_PATH)

    if not os.path.isfile(FFMPEG_PATH):
        raise FileNotFoundError(f"ffmpeg.exe がありません: {FFMPEG_PATH}")
    if not os.path.isfile(FFPROBE_PATH):
        raise FileNotFoundError(f"ffprobe.exe がありません: {FFPROBE_PATH}")

    # PATH 先頭に ffmpeg/bin を追加（pydubのPopen対策）
    os.environ["PATH"] = bin_dir + os.pathsep + os.environ.get("PATH", "")

    # 各ライブラリが参照する環境変数を明示
    os.environ["FFMPEG_BINARY"]      = FFMPEG_PATH
    os.environ["FFPROBE_BINARY"]     = FFPROBE_PATH
    os.environ["IMAGEIO_FFMPEG_EXE"] = FFMPEG_PATH  # moviepy/imageio 用

    # pydub が直接参照するプロパティも設定
    AudioSegment.converter = FFMPEG_PATH
    AudioSegment.ffprobe   = FFPROBE_PATH

    print(f"FFmpeg:  {FFMPEG_PATH}")
    print(f"FFprobe: {FFPROBE_PATH}")

_wire_ffmpeg()

# （必要なら）utils の import はこの後でOK
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
        print(f"Step02 開始: {lv_value}")

        # ✅ Step01で保存した統合JSONを読み込む
        account_id = pipeline_data['account_id']
        platform_directory = pipeline_data['platform_directory']
        account_dir = find_account_directory(platform_directory, account_id)
        broadcast_dir = os.path.join(account_dir, lv_value)

        json_path = os.path.join(broadcast_dir, f"{lv_value}_data.json")
        if not os.path.exists(json_path):
            raise Exception(f"data.json が見つかりません: {json_path}")

        with open(json_path, "r", encoding="utf-8") as f:
            broadcast_data = json.load(f)

        # JSONから必要な情報を取り出す
        account_dir = broadcast_data["account_directory_path"]
        broadcast_dir = broadcast_data["broadcast_directory_path"]
        parsec = broadcast_data.get("time_diff_seconds", 0)

        # 1. MP4ファイル検索
        mp4_path = find_mp4_file(account_dir, lv_value)
        if not mp4_path:
            raise Exception(f"MP4ファイルが見つかりません: {lv_value}")

        # ✅ 絶対パスに変換（存在が確認できてから）
        mp4_path = os.path.abspath(mp4_path)
        print(f"MP4ファイル発見: {mp4_path}")

        # 2. 音声抽出・分割
        audio_files = extract_and_split_audio(mp4_path, broadcast_dir, lv_value, parsec)

        # 3. 文字起こし実行
        transcripts = transcribe_audio_files(audio_files, parsec, pipeline_data.get("config"))

        # 4. transcript.json保存
        save_transcript_json(broadcast_dir, lv_value, transcripts)

        print(f"Step02 完了: {lv_value}")
        return {"transcript_file": os.path.join(broadcast_dir, f"{lv_value}_transcript.json")}

    except Exception as e:
        print(f"Step02 エラー: {str(e)}")
        raise

# ▼ step02_audio_transcriber.py の末尾あたり（save_transcript_json直前）に追加

def pad_head_with_empty_segments(transcripts, pad_head_seconds=100, step=10):
    """
    transcripts の最小timestampより前を、空テキストのダミーセグメントで埋める。
    既定で 0～100秒(=1:40) を 10秒刻みで作る。
    """
    if not transcripts:
        # 何もない場合は 0～pad_head_seconds を空で作って返す
        out = []
        t = 0
        while t < pad_head_seconds:
            out.append({
                'id': f'pad_{t}',
                'start': float(t),
                'end': float(min(t+step, pad_head_seconds)),
                'text': '',
                'timestamp': int(t)
            })
            t += step
        return out

    # 実データの最小時刻
    min_ts = min(int(max(0, seg.get('timestamp', 0))) for seg in transcripts)
    target = max(pad_head_seconds, min_ts)  # 少なくとも pad_head_seconds までは埋める

    pads = []
    t = 0
    while t < target:
        pads.append({
            'id': f'pad_{t}',
            'start': float(t),
            'end': float(min(t+step, target)),
            'text': '',
            'timestamp': int(t)
        })
        t += step

    # 既存とマージ（同じtimestampの pad と本物が衝突しないよう pad を先頭に）
    merged = []
    seen = set()
    for p in pads:
        merged.append(p)
        seen.add(int(p['timestamp']))

    for seg in transcripts:
        ts = int(max(0, seg.get('timestamp', 0)))
        if ts in seen:
            # ちょうど同じ秒のpadはスキップ（本物を優先）
            continue
        merged.append(seg)

    merged.sort(key=lambda x: int(x.get('timestamp', 0)))
    return merged




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
    """動画から音声抽出・分割（WAVベース。pydub の ffprobe 依存を避ける）"""
    try:
        print(f"音声抽出開始: {mp4_path}")

        # 動画読み込み → WAV で書き出し（PCM16）
        video = VideoFileClip(mp4_path)
        audio = video.audio

        os.makedirs(broadcast_dir, exist_ok=True)
        full_wav_path = os.path.join(broadcast_dir, f"{lv_value}_full_audio.wav")

        # moviepy は ffmpeg を直接叩く。ここは既に動いている（ログ実績あり）
        audio.write_audiofile(
            full_wav_path,
            fps=44100,
            codec="pcm_s16le",
            verbose=False,
            logger=None
        )

        # pydub は WAV を素直に読める（ここで ffprobe を極力使わない）
        audio_segment = AudioSegment.from_wav(full_wav_path)

        # 先頭に無音を物理付与する必要は基本なし（parsecは後段でtimestamp補正）
        # どうしても物理付与したいなら以下を使う：
        if parsec > 0:
            print(f"先頭に{parsec}秒の無音を追加（WAV）")
            silence = AudioSegment.silent(duration=parsec * 1000)
            audio_segment = silence + audio_segment
            padded_wav_path = os.path.join(broadcast_dir, f"{lv_value}_silent_audio.wav")
            audio_segment.export(padded_wav_path, format="wav")

        # 180分ごとに分割（WAVで保持 ※mp3書き出しはffmpeg必須なので回避）
        duration_sec = 10800
        audio_files = []
        total_length_ms = len(audio_segment)
        print(f"音声総時間: {total_length_ms/1000:.1f}秒")

        for start in range(0, total_length_ms, duration_sec * 1000):
            end = min(start + duration_sec * 1000, total_length_ms)
            chunk_num = (start // (duration_sec * 1000)) + 1
            chunk_path = os.path.join(broadcast_dir, f"{lv_value}_audio_chunk_{chunk_num}.wav")

            audio_chunk = audio_segment[start:end]
            audio_chunk.export(chunk_path, format="wav")  # WAVならエンコード周りが安定

            start_seconds = start // 1000
            audio_files.append((chunk_path, start_seconds))
            print(f"音声チャンク保存: chunk_{chunk_num} (開始: {start_seconds}秒)")

        video.close()
        audio.close()

        return audio_files

    except Exception as e:
        print(f"音声抽出エラー: {str(e)}")
        raise

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

def transcribe_audio_files(audio_files, parsec, config=None):
    """音声ファイルリストを文字起こし"""
    try:
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
        print(f"文字起こしエラー: {str(e)}")
        # GPU失敗時はCPUで再試行
        if device == "cuda":
            print("GPU処理失敗、CPUで再試行...")
            return transcribe_audio_files_cpu_fallback(audio_files, parsec)
        raise

def transcribe_audio_files_cpu_fallback(audio_files, parsec, step_seconds=10, pad_silence_head=True):
    """
    CPU フォールバックで音声→文字起こしを行う。
    - audio_files: [(wav/mp3/m4a のパス, 録画基準での開始秒)] のリスト
    - parsec: 配信基準へのオフセット秒（録画→配信）。既に time_diff_seconds を渡す想定
    - step_seconds: タイムラインの丸め間隔（デフォ10秒）
    - pad_silence_head: True の場合、最初の発話ブロックより前を空テキストでパディング

    戻り値: transcripts(list[dict])  ※各要素は以下のキーを持つ
      - timestamp: 配信基準の秒（録画start + segment.start + parsec を ceil）
      - timeline_block: 上記 timestamp を step_seconds で丸め下げた秒
      - text: セグメント文字列（前後空白圧縮済み）
      - positive_score / center_score / negative_score: 0.0 初期値
    """
    import os
    import math
    import re
    from faster_whisper import WhisperModel

    def _norm_text(s: str) -> str:
        s = (s or "").strip()
        # 全角/半角スペース・改行などをまとめて1スペースへ
        s = re.sub(r"\s+", " ", s)
        return s

    try:
        print("CPUモードで再実行中...")

        threads = max(1, min(8, os.cpu_count() or 1))
        model = WhisperModel(
            "large-v2",
            device="cpu",
            compute_type="int8",
            cpu_threads=threads,
            num_workers=4,
        )

        all_transcripts = []
        earliest_ts = None
        last_text_global = None  # 連続重複除去（ファイル跨ぎ）

        for file_path, start_time in audio_files:
            print(f"文字起こし中 (CPU): {os.path.basename(file_path)}  start={start_time}s")

            # VAD あり・無音しきい値やや高め（無音を弾きやすく）
            segments, info = model.transcribe(
                file_path,
                language="ja",
                vad_filter=True,
                no_speech_threshold=0.6,
                word_timestamps=False,
            )

            seg_count = 0
            last_text_local = None  # 同一ファイル内の重複除去

            for seg in segments:
                text = _norm_text(getattr(seg, "text", ""))
                if not text or len(text) <= 1:
                    continue

                # 直前セグメントと同一文を弾く（ノイズでの重複出力対策）
                if text == last_text_local or text == last_text_global:
                    continue

                # 録画基準 start_time + seg.start に parsec（配信オフセット）を足し、ceil→int
                timestamp = int(math.ceil((seg.start or 0.0) + (start_time or 0.0) + (parsec or 0)))
                timeline_block = (timestamp // step_seconds) * step_seconds

                all_transcripts.append({
                    "timestamp": timestamp,
                    "timeline_block": timeline_block,
                    "text": text,
                    "positive_score": 0.0,
                    "center_score": 0.0,
                    "negative_score": 0.0,
                })

                if earliest_ts is None or timestamp < earliest_ts:
                    earliest_ts = timestamp

                last_text_local = text
                last_text_global = text
                seg_count += 1

            print(f"  {seg_count} セグメント追加")

        # タイムスタンプ順に整列
        all_transcripts.sort(key=lambda x: x["timestamp"])

        # 最初の発話より前を空でパディング（録画0秒→配信parsec秒 から始まる前提）
        if pad_silence_head and earliest_ts is not None:
            first_block = (earliest_ts // step_seconds) * step_seconds
            # 0 〜 (first_block - step_seconds) を空テキストで埋める（配信基準の秒）
            pad_transcripts = []
            # パディングは「録画0秒→配信parsec秒」から始まるので、配信基準で 0 から入れる
            # 0 から入れると “配信0秒” 起点になる。録画起点での 0〜 を表示したいなら
            # 表示側で「録画秒 = 配信秒 - parsec」を併記する現仕様で OK。
            for t in range(0, first_block, step_seconds):
                pad_transcripts.append({
                    "timestamp": t,
                    "timeline_block": t,  # すでに丸め位置
                    "text": "",           # 空（無言）
                    "positive_score": 0.0,
                    "center_score": 0.0,
                    "negative_score": 0.0,
                })
            if pad_transcripts:
                print(f"無音パディングを {len(pad_transcripts)} ブロック追加 (0s〜{first_block - step_seconds}s)")
                # 先頭に結合して再ソート（安全）
                all_transcripts = pad_transcripts + all_transcripts
                all_transcripts.sort(key=lambda x: x["timestamp"])

        print(f"CPU文字起こし完了: 総セグメント数 {len(all_transcripts)}")
        return all_transcripts

    except Exception as e:
        print(f"CPU文字起こしエラー: {str(e)}")
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