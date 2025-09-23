# nicolive_endcheck_discovery.py
# URLだけ受け取って「終了」を確実寄りに判定する。
# 1) ウォッチHTML → JSから /v*/programs/ のAPI URLを自動発見
# 2) 必須ヘッダ付きでJSON取得して status を読む
# 3) 404などで取れない時は HTML の JSON-LD/文言から endDate 等で終了判定（フォールバック）

import re, argparse, time, json
from urllib.parse import urljoin
import requests
from datetime import datetime

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120 Safari/537.36"
FIXED_INTERVAL_SEC = 60  # ループ間隔（固定）

def extract_lv(url: str) -> str:
    m = re.search(r"lv\d+", url)
    if not m:
        raise SystemExit("lv番号が見つからない")
    return m.group(0)

def get(url, headers=None, timeout=12):
    h = {"User-Agent": UA, "Accept-Language": "ja,en;q=0.8", "Cache-Control": "no-cache"}
    if headers: h.update(headers)
    r = requests.get(url, headers=h, timeout=timeout, allow_redirects=True)
    r.raise_for_status()
    return r

def extract_script_srcs(watch_html: str, base: str):
    srcs = []
    for m in re.finditer(r'<script[^>]+src="([^"]+)"', watch_html):
        src = m.group(1)
        srcs.append(urljoin(base, src))
    return srcs

def discover_program_api_base(watch_html: str, script_urls):
    # 1) HTML直書き
    m = re.search(r'https://[^"\'\s]+/v\d+/programs/', watch_html)
    if m:
        return m.group(0)
    # 2) 外部JSの中から探す
    pat = re.compile(r'https://[^"\'\s]+/v\d+/programs/')
    for js_url in script_urls:
        try:
            js_txt = get(js_url).text
            m = pat.search(js_txt)
            if m:
                return m.group(0)
        except Exception:
            continue
    return None

def read_status_from_api(api_base: str, lv: str, referer: str) -> str:
    api_url = api_base + lv

    headers_try = [
        {  # PCフロント
            "User-Agent": UA,
            "Referer": referer,
            "Origin": "https://live.nicovideo.jp",
            "Accept": "application/json",
            "X-Frontend-Id": "9",
        },
        {  # SPフロント
            "User-Agent": UA,
            "Referer": referer.replace("https://live.nicovideo.jp", "https://sp.live.nicovideo.jp"),
            "Origin": "https://sp.live.nicovideo.jp",
            "Accept": "application/json",
            "X-Frontend-Id": "6",
        },
        {  # 予備（Originなし）
            "User-Agent": UA,
            "Referer": referer,
            "Accept": "application/json",
        },
    ]

    for headers in headers_try:
        try:
            r = requests.get(api_url, headers=headers, timeout=12)
            if r.status_code == 404:
                continue
            if 200 <= r.status_code < 300:
                body = r.text.strip()

                # JSONじゃなくても中に "status":"..." が埋まってるなら拾う
                m = re.search(r'"status"\s*:\s*"(ENDED|ON_AIR|RESERVED|TIMESHIFT)"', body)
                if m:
                    return m.group(1)

                # 先頭にXSSIガード等があれば剥がしてからJSONを試す
                for prefix in (")]}',", "throw 1; < don't be evil >",):
                    if body.startswith(prefix):
                        body = body[len(prefix):].lstrip()

                # 形だけでもJSONっぽければパースを試す
                if body.startswith("{") or body.startswith("["):
                    try:
                        data = json.loads(body)
                        prog = data.get("data", {}).get("program") or data.get("program") or {}
                        st = prog.get("status")
                        if st:
                            return st
                    except Exception:
                        pass

                # ここまで取れなければUNKNOWN継続
                return "UNKNOWN"
        except Exception:
            continue

    return "NOT_FOUND"



def infer_status_from_html(html: str) -> str:
    # JSON-LD から status / endDate
    for m in re.finditer(r'<script[^>]+type="application/(?:ld\+json|json)"[^>]*>(.*?)</script>', html, re.S):
        blob = m.group(1).strip()
        try:
            data = json.loads(blob)
        except Exception:
            continue
        txt = json.dumps(data, ensure_ascii=False)
        ms = re.search(r'"status"\s*:\s*"(ENDED|ON_AIR|RESERVED|TIMESHIFT)"', txt)
        if ms:
            return ms.group(1)
        me = re.search(r'"endDate"\s*:\s*"([^"]+)"', txt)
        if me:
            try:
                dt = datetime.fromisoformat(me.group(1))
                if dt.tzinfo and dt.timestamp() <= time.time():
                    return "ENDED"
            except Exception:
                pass

    # 終了系ワード（優先）
    ended_keys = ["タイムシフト非公開番組です", "タイムシフト再生中はコメントできません", "この番組は終了しました", "放送は終了", "配信は終了", "公開期間が終了", "視聴期間が終了", 'data-status="ended"']
    for kw in ended_keys:
        if kw in html:
            return "ENDED"

    # 放送中の手掛かり（最後に判定）
    onair_keys = ["ただいま放送中", "ライブ配信", "視聴する", 'isLiveBroadcast":true']
    if any(kw in html for kw in onair_keys):
        return "ON_AIR"

    return "UNKNOWN"


def main():
    ap = argparse.ArgumentParser(description="ニコ生 終了検知（API自動発見＋HTMLフォールバック）")
    ap.add_argument("-url", required=True, help="https://live.nicovideo.jp/watch/lvXXXX")
    args = ap.parse_args()

    lv = extract_lv(args.url)
    while True:
        try:
            # 1) ウォッチHTML取得
            watch = get(args.url)
            html = watch.text

            # 2) <script src> 抽出
            scripts = extract_script_srcs(html, watch.url)

            # 3) JSから /vX/programs/ の完全URLを特定
            api_base = discover_program_api_base(html, scripts)
            status = "UNKNOWN"
            if api_base:
                status = read_status_from_api(api_base, lv, referer=watch.url)

            if status == "NOT_FOUND" or status == "UNKNOWN":
                # 4) 取れない時は HTML から推定（endDate / 文言）
                fb = infer_status_from_html(html)
                status = fb if fb != "UNKNOWN" else status

            print(f"[CHECK] {lv}: {status}")
            if status == "ENDED":
                print("放送終了を検知")
                break
        except Exception as e:
            print(f"[ERROR] {e}")

        time.sleep(FIXED_INTERVAL_SEC)

if __name__ == "__main__":
    main()
