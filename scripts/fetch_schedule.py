#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
抓取顺序：直播吧（静态最稳） → 懂球帝球队页（网页内嵌 JSON） → 懂球帝 API（可用就用）
- 解析容错：支持表格解析和“全文兜底”正则，尽量把日期、时间、对手、主客、赛事抠出来
- CSV 字段：date,time_local,opponent,home_away,competition,stadium,status
- 生成 data/parse_report.txt 记录每步命中数
"""

import os, re, csv, time, json, random, requests
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ============= 你只需在这块更新 ID / URL（如果有变化） =============
TEAMS = {
    "chengdu": {
        "name": "成都蓉城",
        "aliases": ["成都蓉城", "蓉城", "Chengdu Rongcheng", "Rongcheng"],
        "csv": "data/chengdu.csv",
        "api_id": "50016554",  # 改成你的最新 ID
        "dqd_page": "https://www.dongqiudi.com/team/50076899.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E6%88%90%E9%83%BD%E8%93%89%E5%9F%8E",
    },
    "inter": {
        "name": "国际米兰",
        "aliases": ["国际米兰", "国米", "Inter", "Inter Milan", "Internazionale"],
        "csv": "data/inter.csv",
        "api_id": "50001752",  # 改成你的最新 ID
        "dqd_page": "https://www.dongqiudi.com/team/50001042.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E5%9B%BD%E9%99%85%E7%B1%B3%E5%85%B0",
    },
}
# ==========================================================

API_URL_TPL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"
MAX_RETRIES, RETRY_DELAY = 3, 5
CST = ZoneInfo("Asia/Shanghai")
PAST_DAYS, FUTURE_DAYS = 400, 500
FIELDS = ["date", "time_local", "opponent", "home_away", "competition", "stadium", "status"]

DEFAULT_UAS = [
    "dongqiudiApp/7.1.0 (iPhone; iOS 17.5; Scale/3.00)",
    "dongqiudiApp/7.0.6 (iPhone; iOS 17.0.1; Scale/3.00)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]

def pick_ua() -> str:
    ua_env = os.getenv("DQD_USER_AGENT", "").strip()
    return ua_env if ua_env else random.choice(DEFAULT_UAS)

def headers_json():
    return {
        "User-Agent": pick_ua(),
        "Referer": "https://m.dongqiudi.com/",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
    }

def headers_html():
    return {
        "User-Agent": random.choice([
            "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Mobile/15E148 Safari/604.1",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.5 Safari/605.1.15",
        ]),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Accept-Language": "zh-CN,zh;q=0.9",
        "Connection": "keep-alive",
        "Referer": "https://www.dongqiudi.com/",
    }

def save_debug(path: str, content: str | bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
    with open(path, mode) as f:
        f.write(content)

def http_get(url: str, is_json=True) -> Optional[requests.Response]:
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers_json() if is_json else headers_html(), timeout=25)
            if r.status_code == 200:
                return r
            print(f"⚠️ HTTP {r.status_code}（{i}/{MAX_RETRIES}）: {url}")
        except Exception as e:
            print(f"❌ 网络异常：{e}（{i}/{MAX_RETRIES}）: {url}")
        time.sleep(RETRY_DELAY)
    return None

def norm(s: str) -> str:
    return re.sub(r"\s+", "", (s or "")).strip()

def name_hit(name: str, aliases: List[str]) -> bool:
    n = norm(name)
    return any(a in n for a in [norm(x) for x in aliases])

def write_csv(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"💾 写入 {len(rows)} 条 → {path}")

def preserve_old_if_empty(path: str, new_rows: List[Dict]) -> bool:
    if new_rows:
        return False
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"🛟 新数据为空，保留旧文件：{path}")
        return True
    return False

def append_report(lines: List[str]):
    os.makedirs("data", exist_ok=True)
    with open("data/parse_report.txt", "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

# ===== 懂球帝 HTML JSON 抽取 =====
def api_pick_matches(payload: Any) -> List[Dict]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), list):
        return payload["data"]
    data = payload.get("data")
    if isinstance(data, dict):
        for k in ("matches", "list", "schedules", "items"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    for k in ("matches", "list", "schedules", "items"):
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []

def deep_walk(obj: Any):
    if isinstance(obj, dict):
        keys = set(obj.keys())
        if ("start_play" in keys or "match_time" in keys) and (
            {"home_name", "away_name"} & keys or {"home_team_name", "away_team_name"} & keys
        ):
            yield obj
        for v in obj.values():
            yield from deep_walk(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from deep_walk(it)

def parse_dqd_html(html: str) -> List[Dict]:
    patterns = [
        r"__NUXT__\s*=\s*(\{.*?\});",
        r"window\.__INITIAL_STATE__\s*=\s*(\{.*?\});",
        r"window\.__NUXT__\s*=\s*(\{.*?\});",
    ]
    for pat in patterns:
        m = re.search(pat, html, flags=re.S | re.M)
        if m:
            raw = m.group(1)
            try:
                data = json.loads(raw)
                found = list(deep_walk(data))
                if found:
                    print(f"🔎 DQD HTML 提取 {len(found)} 条")
                    return found
            except Exception:
                pass

    # 兜底扫描片段（不常走）
    found = []
    for blk in re.findall(r"\{.*?\}", html, flags=re.S):
        if ("home" in blk and "away" in blk) and ("start_play" in blk or "match_time" in blk):
            try:
                j = json.loads(blk); found.append(j)
            except Exception:
                continue
    if found:
        print(f"🔎 DQD HTML 片段兜底 {len(found)} 条")
    return found

def normalize_row(item: Dict, aliases: List[str]) -> Optional[Dict]:
    # 时间
    ts = None
    if isinstance(item.get("start_play"), (int, float)):
        ts = int(item["start_play"])
    else:
        mt = item.get("match_time") or item.get("startTime") or item.get("start_at")
        if isinstance(mt, str):
            try:
                dt_try = datetime.fromisoformat(mt.replace("Z", "+00:00"))
                ts = int(dt_try.timestamp())
            except Exception:
                pass
        elif isinstance(mt, (int, float)):
            ts = int(mt)
    if not ts:
        return None
    dt = datetime.fromtimestamp(ts, tz=CST)

    home = item.get("home_name") or item.get("home_team_name") or item.get("home") or ""
    away = item.get("away_name") or item.get("away_team_name") or item.get("away") or ""

    is_home = item.get("is_home")
    if is_home is None:
        if name_hit(home, aliases): is_home = True
        elif name_hit(away, aliases): is_home = False
        else: return None

    opponent = away if is_home else home
    comp = item.get("competition_name") or item.get("competition") or item.get("tournament_name") or ""
    stadium = item.get("stadium_name") or item.get("stadium") or ""

    status_name = (item.get("status_name") or item.get("status") or "").strip()
    if status_name in ("延期", "推迟", "暂停"): tag = "⚠️比赛延期"
    elif status_name in ("取消",):             tag = "❌比赛取消"
    elif status_name in ("待定", "未开赛", "时间待定"): tag = "🕓时间待定"
    elif status_name in ("完场", "已结束"):     tag = "✅完场"
    else:                                       tag = ""

    return {
        "date": dt.strftime("%Y-%m-%d"),
        "time_local": dt.strftime("%H:%M"),
        "opponent": opponent,
        "home_away": "Home" if is_home else "Away",
        "competition": comp,
        "stadium": stadium,
        "status": tag,
        "_dt": dt,
    }

# ===== 直播吧解析（表格 + 文本兜底） =====
SCORE_RE = re.compile(r"^\s*(\d+\s*[-:]\s*\d+|vs|VS)\s*$")
RE_DATE = re.compile(r"(\d{4}-\d{1,2}-\d{1,2})")
RE_TIME = re.compile(r"(\d{1,2}:\d{2})")
RE_VS   = re.compile(r"\b(VS|vs)\b")
RE_SCORE= re.compile(r"\b(\d+\s*[-:]\s*\d+)\b")

def looks_like_team(s: str) -> bool:
    s = s.strip()
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z]", s)) and 1 <= len(s) <= 25

def parse_zb8_table(html: str, aliases: List[str]) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    rows: List[Dict] = []
    for table in soup.find_all("table"):
        for tr in table.find_all("tr"):
            tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
            if len(tds) < 3:
                continue
            whole = " | ".join(tds)
            m_date = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", whole)
            if not m_date:
                continue
            date = m_date.group(1)
            m_time = re.search(r"(\d{1,2}:\d{2})", whole)
            time_local = m_time.group(1) if m_time else "20:00"

            score_idx = None
            for i, c in enumerate(tds):
                if SCORE_RE.match(c):
                    score_idx = i; break

            home = away = comp = ""
            if score_idx is not None:
                if score_idx - 1 >= 0: home = tds[score_idx - 1]
                if score_idx + 1 < len(tds): away = tds[score_idx + 1]
                for c in tds[:score_idx]:
                    if any(k in c for k in ("联", "杯", "甲", "超", "冠", "欧", "亚")):
                        comp = c; break
            else:
                vs_idx = next((i for i,c in enumerate(tds) if c.strip().lower()=="vs"), None)
                if vs_idx is not None:
                    if vs_idx - 1 >= 0: home = tds[vs_idx - 1]
                    if vs_idx + 1 < len(tds): away = tds[vs_idx + 1]
                    for c in tds[:vs_idx]:
                        if any(k in c for k in ("联", "杯", "甲", "超", "冠", "欧", "亚")):
                            comp = c; break
                else:
                    team_words = [c for c in tds if looks_like_team(c)]
                    if len(team_words) >= 2:
                        home, away = team_words[0], team_words[1]
                        for c in tds:
                            if any(k in c for k in ("联", "杯", "甲", "超", "冠", "欧", "亚")):
                                comp = c; break

            if not (home and away):
                continue

            if name_hit(home, aliases):
                my_is_home, opponent = True, away
            elif name_hit(away, aliases):
                my_is_home, opponent = False, home
            else:
                my_is_home, opponent = None, away

            rows.append({
                "date": date,
                "time_local": time_local,
                "opponent": opponent,
                "home_away": "Home" if my_is_home is True else ("Away" if my_is_home is False else "Unknown"),
                "competition": comp,
                "stadium": "",
                "status": ""
            })
    print(f"🔎 ZB8 表格解析 {len(rows)} 条")
    return rows

def parse_zb8_text_grep(html: str, aliases: List[str]) -> List[Dict]:
    text = BeautifulSoup(html, "lxml").get_text(" ", strip=True)
    rows: List[Dict] = []
    for m in RE_DATE.finditer(text):
        date = m.group(1)
        start = m.end()
        window = text[start:start+180]
        t = RE_TIME.search(window)
        time_local = t.group(1) if t else "20:00"
        vs = RE_VS.search(window)
        sc = RE_SCORE.search(window)

        def pick_team(chunk: str) -> Optional[str]:
            cands = re.findall(r"[\u4e00-\u9fa5A-Za-z]{2,25}", chunk)
            ban = {"年","月","日","直播","数据","赛","联赛","杯","甲","超","欧","亚","第","轮"}
            cands = [w for w in cands if w not in ban]
            return cands[-1] if cands else None

        home = away = None
        if vs:
            left = window[:vs.start()]; right = window[vs.end():]
            home = pick_team(left); away = pick_team(right)
        elif sc:
            left = window[:sc.start()]; right = window[sc.end():]
            home = pick_team(left); away = pick_team(right)
        if not (home and away):
            continue

        if name_hit(home, aliases):
            my_is_home, opponent = True, away
        elif name_hit(away, aliases):
            my_is_home, opponent = False, home
        else:
            my_is_home, opponent = None, away

        rows.append({
            "date": date,
            "time_local": time_local,
            "opponent": opponent,
            "home_away": "Home" if my_is_home is True else ("Away" if my_is_home is False else "Unknown"),
            "competition": "",
            "stadium": "",
            "status": ""
        })
    print(f"🔎 ZB8 文本兜底解析 {len(rows)} 条")
    return rows

# ===== 主流程：优先 ZB8 → DQD → API =====
def fetch_team(team_key: str, info: Dict) -> Tuple[List[Dict], List[str]]:
    report = [f"=== {info['name']} ==="]
    aliases = info["aliases"]
    now = datetime.now(CST)
    start = (now - timedelta(days=PAST_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (now + timedelta(days=FUTURE_DAYS)).replace(hour=23, minute=59, second=59, microsecond=0)

    rows_from_api: List[Dict] = []
    rows_from_dqd: List[Dict] = []
    rows_from_zb8: List[Dict] = []

    # 1) 直播吧
    if info.get("zb8_page"):
        print(f"\n🪂 ZB8 优先抓取：{info['zb8_page']}")
        zr = http_get(info["zb8_page"], is_json=False)
        if zr and zr.status_code == 200 and zr.text:
            save_debug(f"data/debug_{team_key}_zb8.html", zr.text[:200000].encode("utf-8", "ignore"))
            rows_from_zb8 = parse_zb8_table(zr.text, aliases)
            if not rows_from_zb8:
                rows_from_zb8 = parse_zb8_text_grep(zr.text, aliases)
        report.append(f"ZB8命中：{len(rows_from_zb8)}")

    # 2) 懂球帝网页
    if not rows_from_zb8 and info.get("dqd_page"):
        print(f"🪂 DQD 回退：{info['dqd_page']}")
        hr = http_get(info["dqd_page"], is_json=False)
        if hr and hr.status_code == 200 and hr.text:
            save_debug(f"data/debug_{team_key}_dqd.html", hr.text[:200000].encode("utf-8", "ignore"))
            dqd_items = parse_dqd_html(hr.text)
            for it in dqd_items:
                r = normalize_row(it, aliases)
                if r and ("_dt" in r) and (start <= r["_dt"] <= end):
                    r.pop("_dt", None); rows_from_dqd.append(r)
        report.append(f"DQD网页命中：{len(rows_from_dqd)}")

    # 3) 懂球帝 API
    if not rows_from_zb8 and not rows_from_dqd and info.get("api_id"):
        api_url = API_URL_TPL.format(team_id=info["api_id"])
        print(f"📡 API 兜底：{api_url}")
        r = http_get(api_url, is_json=True)
        if r and r.status_code == 200:
            try:
                js = r.json()
                for it in api_pick_matches(js):
                    rr = normalize_row(it, aliases)
                    if rr and ("_dt" in rr) and (start <= rr["_dt"] <= end):
                        rr.pop("_dt", None); rows_from_api.append(rr)
            except Exception as e:
                print("API JSON 解析失败：", e)
        if not rows_from_api and r is not None:
            save_debug(f"data/debug_{team_key}.json", r.text)
        report.append(f"API命中：{len(rows_from_api)}")

    rows = rows_from_zb8 or rows_from_dqd or rows_from_api

    rows.sort(key=lambda x: (x["date"], x["time_local"], x["opponent"], x["competition"]))
    out, seen = [], set()
    for r0 in rows:
        key = (r0["date"], r0["time_local"], r0["opponent"], r0["competition"])
        if key in seen: continue
        seen.add(key); out.append(r0)

    report.append(f"最终写入：{len(out)}")
    print(f"✅ 最终可用条数：{len(out)}")
    return out, report

def main():
    total = 0
    report_all: List[str] = []
    for key, info in TEAMS.items():
        rows, rpt = fetch_team(key, info)
        report_all.extend(rpt)
        if preserve_old_if_empty(info["csv"], rows):
            continue
        write_csv(info["csv"], rows)
        total += len(rows)
    report_all.append(f"总计写入：{total}")
    append_report(report_all)
    print("\n".join(report_all))
    print(f"\n🎯 本次可写入总计 {total} 条。")

if __name__ == "__main__":
    main()
    
