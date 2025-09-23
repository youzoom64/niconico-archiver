import threading
import time
import logging
from typing import List, Dict, Any, Optional
from .recording_controller import RecordingController

DEBUGLOG = logging.getLogger(__name__)

class SegmentManager:
    def __init__(self, recording_controller: RecordingController, video_processor, segment_duration: int = 1800):
        self.recording_controller = recording_controller
        self.video_processor = video_processor  # VideoProcessorインスタンス
        self.segment_duration = segment_duration  # 30分 = 1800秒
        self.recording_segments = []
        self.segment_gaps = []
        self.current_segment = 0
        self.segment_timer = None
        self.segment_active = False
        self.processing_threads = []  # バックグラウンド処理用
        self.broadcast_title = ""  # 放送タイトル保存用

    def start_segment_recording(self, broadcast_id: str, broadcast_title: str = "") -> int:
        """最初のセグメント録画開始"""
        start_time = int(time.time())
        self.broadcast_title = broadcast_title
        
        # 最初のセグメント情報作成
        first_segment = {
            'segment_id': self.current_segment,
            'start_time': start_time,
            'end_time': None,
            'file': None,
            'broadcast_id': broadcast_id
        }
        self.recording_segments.append(first_segment)
        
        # 録画開始
        self.recording_controller.start_recording()
        self.segment_active = True
        
        # 30分タイマー開始
        self._schedule_next_segment_switch()
        
        DEBUGLOG.info(f"セグメント{self.current_segment}録画開始: {start_time}")
        return start_time

    def stop_all_segments(self):
        """全セグメント録画停止"""
        DEBUGLOG.info("全セグメント録画停止処理開始")
        
        # タイマー停止
        if self.segment_timer:
            self.segment_timer.cancel()
            self.segment_timer = None
        
        # 最後のセグメント終了処理
        if self.segment_active and self.recording_controller.is_recording():
            end_time = int(time.time())
            last_segment = None
            
            if self.current_segment < len(self.recording_segments):
                self.recording_segments[self.current_segment]['end_time'] = end_time
                self.recording_segments[self.current_segment]['file'] = f"segment_{self.current_segment:03d}.mp4"
                last_segment = self.recording_segments[self.current_segment].copy()
                DEBUGLOG.info(f"最終セグメント{self.current_segment}終了時刻記録: {end_time}")
            
            # 録画停止
            self.recording_controller.stop_recording()
            self.segment_active = False
            
            # 最後のセグメントも処理
            if last_segment:
                thread = threading.Thread(
                    target=self._process_segment_background,
                    args=(last_segment,),
                    daemon=True
                )
                thread.start()
                self.processing_threads.append(thread)
        
        # バックグラウンド処理の完了を待機
        DEBUGLOG.info("バックグラウンド処理の完了を待機中...")
        for i, thread in enumerate(self.processing_threads):
            DEBUGLOG.info(f"バックグラウンド処理{i+1}/{len(self.processing_threads)}の完了待機中...")
            thread.join(timeout=60)  # 最大60秒待機
            if thread.is_alive():
                DEBUGLOG.warning(f"バックグラウンド処理{i+1}がタイムアウトしました")
        
        DEBUGLOG.info("全セグメント録画停止処理完了")

    def _switch_recording_segment(self):
        """録画セグメント切り替え（30分タイマー用）"""
        if not self.segment_active:
            DEBUGLOG.warning("セグメントが非アクティブのため、切り替えをスキップ")
            return
        
        # 現在のセグメント終了時刻記録
        end_time = int(time.time())
        completed_segment = None
        
        if self.current_segment < len(self.recording_segments):
            self.recording_segments[self.current_segment]['end_time'] = end_time
            self.recording_segments[self.current_segment]['file'] = f"segment_{self.current_segment:03d}.mp4"
            completed_segment = self.recording_segments[self.current_segment].copy()
            DEBUGLOG.info(f"セグメント{self.current_segment}終了時刻記録: {end_time}")
        
        # 録画停止
        self.recording_controller.stop_recording()
        
        # 完了したセグメントをバックグラウンドで処理
        if completed_segment:
            thread = threading.Thread(
                target=self._process_segment_background,
                args=(completed_segment,),
                daemon=True
            )
            thread.start()
            self.processing_threads.append(thread)
            DEBUGLOG.info(f"セグメント{self.current_segment}のバックグラウンド処理を開始")
        
        # 次のセグメント準備
        self.current_segment += 1
        start_time = int(time.time())
        
        # 隙間時間計算
        if len(self.recording_segments) > 0:
            gap_seconds = start_time - end_time
            self.segment_gaps.append(gap_seconds)
            DEBUGLOG.info(f"セグメント間隙間時間: {gap_seconds}秒")
        
        # 新しいセグメント情報追加
        new_segment = {
            'segment_id': self.current_segment,
            'start_time': start_time,
            'end_time': None,
            'file': None,
            'broadcast_id': self.recording_segments[0]['broadcast_id']
        }
        self.recording_segments.append(new_segment)
        
        # 録画再開
        self.recording_controller.start_recording()
        
        DEBUGLOG.info(f"セグメント{self.current_segment}開始: {start_time}")
        
        # 次の30分タイマー設定
        self._schedule_next_segment_switch()

    def _process_segment_background(self, segment_info: Dict[str, Any]):
        """セグメント処理をバックグラウンドで実行"""
        try:
            segment_id = segment_info['segment_id']
            DEBUGLOG.info(f"バックグラウンド処理開始: セグメント{segment_id}")
            
            # webm→mp4変換処理
            success = self.video_processor.process_segment(segment_info, self.broadcast_title)
            
            if success:
                DEBUGLOG.info(f"バックグラウンド処理完了: セグメント{segment_id}")
            else:
                DEBUGLOG.error(f"バックグラウンド処理失敗: セグメント{segment_id}")
                
        except Exception as e:
            DEBUGLOG.error(f"バックグラウンド処理でエラー: セグメント{segment_info.get('segment_id', 'unknown')} / {e}")

    def _schedule_next_segment_switch(self):
        """次のセグメント切り替えをスケジュール"""
        if self.segment_timer:
            self.segment_timer.cancel()
        
        self.segment_timer = threading.Timer(self.segment_duration, self._switch_recording_segment)
        self.segment_timer.start()
        DEBUGLOG.info(f"次のセグメント切り替えを{self.segment_duration}秒後にスケジュール")

    def cancel_segment_timer(self):
        """セグメントタイマーをキャンセル"""
        if self.segment_timer:
            self.segment_timer.cancel()
            self.segment_timer = None
            DEBUGLOG.info("セグメントタイマーをキャンセルしました")

    def get_segments_info(self) -> Dict[str, Any]:
        """セグメント情報を取得"""
        return {
            'segments': self.recording_segments,
            'gaps': self.segment_gaps,
            'current_segment': self.current_segment,
            'segment_active': self.segment_active,
            'processing_threads_count': len([t for t in self.processing_threads if t.is_alive()])
        }

    def get_recording_segments(self) -> List[Dict[str, Any]]:
        """録画セグメントリストを取得"""
        return self.recording_segments

    def get_segment_gaps(self) -> List[int]:
        """セグメント間隙間リストを取得"""
        return self.segment_gaps

    def is_segment_active(self) -> bool:
        """セグメント録画の状態を取得"""
        return self.segment_active

    def get_processed_segments(self) -> List[Dict[str, Any]]:
        """処理完了したセグメントのリストを取得"""
        processed = []
        for segment in self.recording_segments:
            if segment['end_time'] and segment['file']:
                # ファイルが実際に存在するかチェック
                if hasattr(self.video_processor, 'output_dir'):
                    import os
                    file_path = os.path.join(self.video_processor.output_dir, segment['file'])
                    if os.path.exists(file_path):
                        processed.append(segment)
        return processed

    def get_active_processing_count(self) -> int:
        """アクティブな処理スレッド数を取得"""
        return len([t for t in self.processing_threads if t.is_alive()])

    def wait_for_all_processing(self, timeout: Optional[float] = None):
        """全てのバックグラウンド処理の完了を待機"""
        DEBUGLOG.info(f"全バックグラウンド処理の完了待機開始 (タイムアウト: {timeout}秒)")
        
        for i, thread in enumerate(self.processing_threads):
            if thread.is_alive():
                DEBUGLOG.info(f"処理{i+1}/{len(self.processing_threads)}の完了待機中...")
                thread.join(timeout=timeout)
                
                if thread.is_alive():
                    DEBUGLOG.warning(f"処理{i+1}がタイムアウトしました")
                else:
                    DEBUGLOG.info(f"処理{i+1}完了")
        
        active_count = self.get_active_processing_count()
        if active_count == 0:
            DEBUGLOG.info("全バックグラウンド処理が完了しました")
        else:
            DEBUGLOG.warning(f"{active_count}個の処理がまだ実行中です")

    def force_stop_all_processing(self):
        """全バックグラウンド処理を強制停止（デーモンスレッドなので自動終了）"""
        active_count = self.get_active_processing_count()
        if active_count > 0:
            DEBUGLOG.warning(f"{active_count}個のバックグラウンド処理を強制終了します")
        
        # デーモンスレッドなのでメインプロセス終了時に自動的に終了
        self.processing_threads.clear()