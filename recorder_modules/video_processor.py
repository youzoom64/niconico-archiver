import subprocess
import os
import json
import shutil
import time
import logging
import re
from typing import List, Dict, Any, Optional

DEBUGLOG = logging.getLogger(__name__)

class VideoProcessor:
    def __init__(self, tmp_dir: str, output_dir: str, download_directory: str):
        self.tmp_dir = tmp_dir
        self.output_dir = output_dir
        self.download_directory = download_directory

    def setup_tmp_directory(self):
        """一時作業ディレクトリのセットアップ"""
        try:
            os.makedirs(self.tmp_dir, exist_ok=True)
            DEBUGLOG.info(f"一時ディレクトリ準備完了: {self.tmp_dir}")
        except Exception as e:
            DEBUGLOG.error(f"一時ディレクトリ作成失敗: {self.tmp_dir} / {e}")
            raise

    def cleanup_tmp_directory(self):
        """一時作業ディレクトリのクリーンアップ"""
        if self.tmp_dir and os.path.exists(self.tmp_dir):
            try:
                shutil.rmtree(self.tmp_dir)
                DEBUGLOG.info(f"一時ディレクトリクリーンアップ完了: {self.tmp_dir}")
            except Exception as e:
                DEBUGLOG.warning(f"一時ディレクトリクリーンアップ失敗: {e}")

    def pick_and_wait_recording_file(self, start_time_unix: int, retries: int = 60, interval: int = 2, stable_checks: int = 3) -> Optional[str]:
        """recording-*.webm を探して start_time*1000 に最も近いものを選び、ファイルサイズが安定するまで待機"""
        if not os.path.isdir(self.download_directory):
            DEBUGLOG.error(f"download_directory が存在しない: {self.download_directory}")
            return None

        target_ms = start_time_unix * 1000
        rx = re.compile(r"^recording-(\d+)\.webm$", re.IGNORECASE)

        for attempt in range(retries):
            candidates = []
            for name in os.listdir(self.download_directory):
                m = rx.match(name)
                if not m:
                    continue
                full = os.path.join(self.download_directory, name)
                if os.path.isfile(full):
                    try:
                        stamp = int(m.group(1))
                        candidates.append((full, stamp))
                    except ValueError:
                        continue

            if candidates:
                candidates.sort(key=lambda x: abs(x[1] - target_ms))
                chosen, stamp = candidates[0]
                DEBUGLOG.info(f"録画ファイル候補: {os.path.basename(chosen)} (差={stamp - target_ms}ms)")

                last_size = -1
                stable_count = 0
                while True:
                    size = os.path.getsize(chosen)
                    if size == last_size and size > 0:
                        stable_count += 1
                        if stable_count >= stable_checks:
                            DEBUGLOG.info(f"録画ファイル安定化完了: {os.path.basename(chosen)}")
                            return chosen
                    else:
                        stable_count = 0
                    last_size = size
                    time.sleep(interval)
            else:
                DEBUGLOG.debug(f"録画ファイル未発見、リトライ {attempt+1}/{retries}")
                time.sleep(interval)

        DEBUGLOG.error(f"録画ファイルが見つからない/安定しない: start_time={start_time_unix}")
        return None

    def convert_webm_to_mp4(self, src_webm: str, dst_mp4: str) -> bool:
        """ffmpeg で webm -> mp4 へ変換"""
        cmd = [
            "ffmpeg",
            "-y",
            "-i", src_webm,
            "-c:v", "libx264",
            "-preset", "veryfast",
            "-crf", "18",
            "-c:a", "aac",
            "-b:a", "192k",
            dst_mp4
        ]
        DEBUGLOG.info(f"ffmpeg 変換開始: {os.path.basename(src_webm)} → {os.path.basename(dst_mp4)}")
        try:
            res = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="ignore")
            if res.returncode != 0:
                DEBUGLOG.error(f"ffmpeg 失敗: {res.stderr[:500]}")
                return False
            DEBUGLOG.info("ffmpeg 変換成功")
            return True
        except Exception as e:
            DEBUGLOG.error(f"ffmpeg 実行エラー: {e}")
            return False

    def create_gap_video(self, duration_seconds: int, output_path: str) -> bool:
        """指定秒数の黒画面動画を生成"""
        DEBUGLOG.info(f"隙間動画生成開始: {duration_seconds}秒 → {output_path}")
        
        cmd = [
            'ffmpeg', '-y',
            '-f', 'lavfi',
            '-i', f'color=c=black:s=1280x720:d={duration_seconds}',
            '-f', 'lavfi', 
            '-i', f'anullsrc=channel_layout=stereo:sample_rate=48000',
            '-c:v', 'libx264',
            '-c:a', 'aac',
            '-shortest',
            '-pix_fmt', 'yuv420p',
            output_path
        ]
        
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            if result.returncode == 0:
                DEBUGLOG.info(f"隙間動画生成成功: {output_path}")
                return True
            else:
                DEBUGLOG.error(f"隙間動画生成失敗: returncode={result.returncode}")
                if result.stderr:
                    DEBUGLOG.error(f"[ffmpeg stderr]\n{result.stderr}")
                return False
        except Exception as e:
            DEBUGLOG.error(f"隙間動画生成で例外: {e}")
            return False

    def create_concat_list(self, segments: List[Dict[str, Any]], gaps: List[int], output_path: str):
        """ffmpeg用の結合リストファイルを生成"""
        DEBUGLOG.info(f"結合リスト生成: {output_path}")
        
        with open(output_path, 'w', encoding='utf-8') as f:
            for i, segment in enumerate(segments):
                if segment['file'] and os.path.exists(os.path.join(self.output_dir, segment['file'])):
                    # セグメント動画
                    segment_path = os.path.join(self.output_dir, segment['file']).replace('\\', '/')
                    f.write(f"file '{segment_path}'\n")
                    
                    # 隙間動画（最後のセグメント以外）
                    if i < len(gaps):
                        gap_file = os.path.join(self.tmp_dir, f'gap_{gaps[i]}s.mp4').replace('\\', '/')
                        if os.path.exists(gap_file.replace('/', '\\')):  # Windowsパス用に戻して存在確認
                            f.write(f"file '{gap_file}'\n")
        
        DEBUGLOG.info(f"結合リスト生成完了: {output_path}")

    def merge_all_segments(self, broadcast_id: str, recording_segments: List[Dict[str, Any]], segment_gaps: List[int]) -> bool:
        """全セグメントと隙間を結合して最終動画を作成"""
        DEBUGLOG.info("最終動画結合処理開始")
        
        if not recording_segments:
            DEBUGLOG.warning("結合対象のセグメントがありません")
            return False
        
        try:
            # 隙間動画生成
            for i, gap_seconds in enumerate(segment_gaps):
                if gap_seconds > 0:
                    gap_file = os.path.join(self.tmp_dir, f'gap_{gap_seconds}s.mp4')
                    if not self.create_gap_video(gap_seconds, gap_file):
                        DEBUGLOG.error(f"隙間動画生成失敗: {gap_seconds}秒")
                        return False
            
            # 結合リスト作成
            concat_list = os.path.join(self.tmp_dir, 'concat_list.txt')
            self.create_concat_list(recording_segments, segment_gaps, concat_list)
            
            # 最終動画出力パス
            final_output = os.path.join(self.output_dir, f'{broadcast_id}_complete.mp4')
            
            # ffmpegで結合実行
            cmd = [
                'ffmpeg', '-y',
                '-f', 'concat',
                '-safe', '0',
                '-i', concat_list,
                '-c', 'copy',
                final_output
            ]
            
            DEBUGLOG.info(f"最終結合実行: {' '.join(cmd)}")
            result = subprocess.run(cmd, capture_output=True, text=True, encoding='utf-8', errors='ignore')
            
            if result.returncode == 0:
                DEBUGLOG.info(f"最終動画結合成功: {final_output}")
                
                # セグメント情報をJSONで保存
                segments_info = {
                    'broadcast_id': broadcast_id,
                    'total_segments': len(recording_segments),
                    'segments': recording_segments,
                    'gaps': segment_gaps,
                    'final_video': final_output,
                    'created_at': int(time.time())
                }
                
                info_file = os.path.join(self.output_dir, f'{broadcast_id}_segments_info.json')
                with open(info_file, 'w', encoding='utf-8') as f:
                    json.dump(segments_info, f, ensure_ascii=False, indent=2)
                
                DEBUGLOG.info(f"セグメント情報保存: {info_file}")
                return True
                
            else:
                DEBUGLOG.error(f"最終動画結合失敗: returncode={result.returncode}")
                if result.stderr:
                    DEBUGLOG.error(f"[ffmpeg stderr]\n{result.stderr}")
                return False
        
        except Exception as e:
            DEBUGLOG.error(f"最終動画結合で例外: {e}")
            return False

    def process_segment(self, segment_info: Dict[str, Any], lv_title: str) -> bool:
        """セグメント毎のファイル処理"""
        start_time = segment_info['start_time']
        segment_id = segment_info['segment_id']
        
        # 録画ファイル探索
        webm_path = self.pick_and_wait_recording_file(start_time)
        if not webm_path:
            DEBUGLOG.error(f"セグメント{segment_id}の録画ファイルが見つかりません")
            return False

        # 出力ファイル名生成
        output_filename = f"segment_{segment_id:03d}.mp4"
        output_path = os.path.join(self.output_dir, output_filename)

        # 変換
        if not self.convert_webm_to_mp4(webm_path, output_path):
            DEBUGLOG.error(f"セグメント{segment_id}の変換に失敗しました")
            return False

        DEBUGLOG.info(f"セグメント{segment_id}処理完了: {output_filename}")
        return True