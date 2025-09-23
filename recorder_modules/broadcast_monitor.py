import threading
import time
import logging
import requests
import json
import re
from urllib.parse import urljoin
from typing import Optional
from logger import Logger

DEBUGLOG = logging.getLogger(__name__)

class BroadcastMonitor:
    def __init__(self, lv_no: str, check_interval: int = 30):
        self.lv_no = lv_no
        self.check_interval = check_interval
        self.broadcast_ended = threading.Event()
        self.monitor_thread = None
        self.running = False

    def start_monitoring(self):
        """監視開始"""
        if self.running:
            DEBUGLOG.warning("既に監視中です")
            return
        
        self.running = True
        self.broadcast_ended.clear()
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        DEBUGLOG.info(f"配信終了監視開始: {self.lv_no} (間隔: {self.check_interval}秒)")

    def stop_monitoring(self):
        """監視停止"""
        self.running = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=5)
        DEBUGLOG.info("配信終了監視停止")

    def is_broadcast_ended(self) -> bool:
        """配信終了状態を取得"""
        return self.broadcast_ended.is_set()

    def wait_for_broadcast_end(self, timeout: Optional[float] = None) -> bool:
        """配信終了まで待機"""
        return self.broadcast_ended.wait(timeout)

    def _monitor_loop(self):
        """監視ループ（別スレッドで実行）"""
        while self.running:
            try:
                if self._check_broadcast_end():
                    DEBUGLOG.info("配信終了を検知")
                    self.broadcast_ended.set()
                    break
                
                DEBUGLOG.debug("配信継続中")
                time.sleep(self.check_interval)
                
            except Exception as e:
                DEBUGLOG.error(f"監視ループでエラー: {e}")
                time.sleep(self.check_interval)

    def _check_broadcast_end(self) -> bool:
        """配信終了チェック（nicolive_endcheck_discovery.pyロジック使用）"""
        try:
            url = f"https://live.nicovideo.jp/watch/{self.lv_no}"
            headers = {
                "User-Agent": (
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                    "AppleWebKit/537.36 (KHTML, like Gecko) "
                    "Chrome/120.0.0.0 Safari/537.36"
                ),
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                "Accept-Language": "ja,en-US;q=0.9,en;q=0.8",
                "Cache-Control": "no-cache"
            }
            
            resp = requests.get(url, timeout=30, headers=headers, allow_redirects=True)
            resp.raise_for_status()
            resp.encoding = 'utf-8'
            html = resp.text

            # <script src> 抽出
            script_urls = self._extract_script_srcs(html, resp.url)

            # /v*/programs/ API URLを自動発見
            api_base = self._discover_program_api_base(html, script_urls)
            status = "UNKNOWN"
            
            if api_base:
                status = self._read_status_from_api(api_base, self.lv_no, referer=resp.url)
                DEBUGLOG.debug(f"[API検知] {self.lv_no}: status={status}")

            # API取得失敗時はHTMLフォールバック
            if status in ("NOT_FOUND", "UNKNOWN"):
                fallback_status = self._infer_status_from_html(html)
                status = fallback_status if fallback_status != "UNKNOWN" else status
                DEBUGLOG.debug(f"[HTML検知] {self.lv_no}: status={status}")

            # 終了判定
            is_ended = (status == "ENDED")
            return is_ended

        except Exception as e:
            DEBUGLOG.error(f"終了チェック失敗 {self.lv_no}: {e}")
            return True  # エラー時は終了扱い

    def _extract_script_srcs(self, html: str, base_url: str) -> list:
        """HTML内の<script src>を抽出"""
        srcs = []
        for m in re.finditer(r'<script[^>]+src="([^"]+)"', html):
            src = m.group(1)
            srcs.append(urljoin(base_url, src))
        return srcs

    def _discover_program_api_base(self, html: str, script_urls: list) -> str:
        # HTML直書きから探す
        m = re.search(r'https://[^"\'\s&]+/v\d+/programs/', html)  # &を除外
        if m:
            api_url = m.group(0)
            # エスケープ文字が含まれている場合は最初の有効部分だけ取得
            if '&' in api_url:
                api_url = api_url.split('&')[0]
            DEBUGLOG.debug(f"HTMLからAPI発見: {api_url}")
            return api_url

    def _read_status_from_api(self, api_base: str, lv: str, referer: str) -> str:
        """API から status を取得"""
        api_url = api_base + lv
        
        headers_try = [
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Referer": referer,
                "Origin": "https://live.nicovideo.jp",
                "Accept": "application/json",
                "X-Frontend-Id": "9",
            },
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Referer": referer.replace("https://live.nicovideo.jp", "https://sp.live.nicovideo.jp"),
                "Origin": "https://sp.live.nicovideo.jp", 
                "Accept": "application/json",
                "X-Frontend-Id": "6",
            },
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0",
                "Referer": referer,
                "Accept": "application/json",
            },
        ]

        for i, headers in enumerate(headers_try):
            try:
                DEBUGLOG.debug(f"API試行 {i+1}/{len(headers_try)}: {api_url}")
                r = requests.get(api_url, headers=headers, timeout=12)
                
                if r.status_code == 404:
                    DEBUGLOG.debug(f"API 404: {api_url}")
                    continue
                    
                if 200 <= r.status_code < 300:
                    body = r.text.strip()
                    
                    # 正規表現でstatusを直接抽出
                    m = re.search(r'"status"\s*:\s*"(ENDED|ON_AIR|RESERVED|TIMESHIFT)"', body)
                    if m:
                        status = m.group(1)
                        DEBUGLOG.debug(f"API成功: status={status}")
                        return status

                    # XSSIガード等を剥がしてJSONパース試行
                    for prefix in (")]}',", "throw 1; < don't be evil >"):
                        if body.startswith(prefix):
                            body = body[len(prefix):].lstrip()

                    if body.startswith("{") or body.startswith("["):
                        try:
                            data = json.loads(body)
                            prog = data.get("data", {}).get("program") or data.get("program") or {}
                            st = prog.get("status")
                            if st:
                                DEBUGLOG.debug(f"JSON解析成功: status={st}")
                                return st
                        except json.JSONDecodeError:
                            pass
                    
            except Exception as e:
                DEBUGLOG.debug(f"API呼び出し失敗 {i+1}: {e}")
                continue

        DEBUGLOG.warning(f"全API試行失敗: {api_url}")
        return "NOT_FOUND"

    def _infer_status_from_html(self, html: str) -> str:
        """HTMLから status を推定（フォールバック）"""
        import time
        from datetime import datetime
        
        # JSON-LD から status / endDate
        for m in re.finditer(r'<script[^>]+type="application/(?:ld\+json|json)"[^>]*>(.*?)</script>', html, re.S):
            blob = m.group(1).strip()
            try:
                data = json.loads(blob)
                txt = json.dumps(data, ensure_ascii=False)
                
                # status直接取得
                ms = re.search(r'"status"\s*:\s*"(ENDED|ON_AIR|RESERVED|TIMESHIFT)"', txt)
                if ms:
                    DEBUGLOG.debug(f"JSON-LD status: {ms.group(1)}")
                    return ms.group(1)
                
                # endDate判定
                me = re.search(r'"endDate"\s*:\s*"([^"]+)"', txt)
                if me:
                    try:
                        dt = datetime.fromisoformat(me.group(1).replace('Z', '+00:00'))
                        if dt.tzinfo and dt.timestamp() <= time.time():
                            DEBUGLOG.debug(f"JSON-LD endDate終了: {me.group(1)}")
                            return "ENDED"
                    except Exception:
                        pass
            except json.JSONDecodeError:
                continue

        # 終了系ワード
        ended_patterns = [
            "タイムシフト非公開番組です",
            "タイムシフト再生中はコメントできません", 
            "この番組は終了しました",
            "放送は終了",
            "配信は終了",
            "公開期間が終了",
            "視聴期間が終了",
            'data-status="ended"',
            'data-status="endPublication"',
            "endPublication"
        ]
        
        for pattern in ended_patterns:
            if pattern in html:
                DEBUGLOG.debug(f"終了パターン検知: {pattern}")
                return "ENDED"

        # 放送中の手掛かり
        onair_patterns = [
            "ただいま放送中",
            "ライブ配信", 
            "視聴する",
            'isLiveBroadcast":true',
            '"isLive":true',
            '"status":"ON_AIR"'
        ]
        
        if any(pattern in html for pattern in onair_patterns):
            DEBUGLOG.debug("放送中パターン検知")
            return "ON_AIR"

        DEBUGLOG.debug("HTMLからstatus判定不可")
        return "UNKNOWN"