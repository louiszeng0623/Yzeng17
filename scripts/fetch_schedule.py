#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳态三源：懂球帝 API → 懂球帝网页 → 直播吧 data 网页
升级点：
- 直播吧 data 表格使用 BeautifulSoup + lxml 强容错解析
- 识别 “主队 | 比分/VS | 客队” 多种列位；比分支持 1-0 / 1:0 / VS / vs
- 队名别名匹配（国米/国际米兰，成都蓉城/蓉城）
- 扩大时间窗口，空数据不覆盖旧 CSV，并保留 debug 文件
"""

import os, re, csv, time, json, random, requests
from typing import List, Dict, Any, Optional
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ===================== 队伍配置 =====================
TEAMS = {
    "chengdu": {
        "name": "成都蓉城",
        "aliases": ["成都蓉城", "蓉城"],
        "csv": "data/chengdu.csv",
        "api_id": "50076899",
        "dqd_page": "https://www.dongqiudi.com/team/50076899.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E6%88%90%E9%83%BD%E8%93%89%E5%9F%8E",
    },
    "inter": {
        "name": "国际米兰",
        "aliases": ["国际米兰", "国米"],
        "csv": "data/inter.csv",
        "api_id": "50001042",
        "dqd_page": "https://www.dongqiudi.com/team/50001042.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E5%9B%BD%E9%99%85%E7%B1%B3%E5%85%B0",
    },
}

# ===================== 全局参数 =====================
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

# ===================== 小工具 =====================
def save_debug(path: str, content: str | bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
    with open(path, mode) as f:
        f.write(content)
    print(f"📝 debug → {path}")

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

# ===================== 懂球帝 API/网页解析（保持不变的稳态自适配） =====================
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
                    print(f"🔎 DQD HTML 提取 {len(found)} 条（via {pat}）")
                    return found
            except Exception:
                pass

    # 兜底：扫描较大的 JSON 片段
    found = []
    for blk in re.findall(r"\{.*?\}", html, flags=re.S):
        if ("home" in blk and "away" in blk) and ("start_play" in blk or "match_time" in blk):
            try:
                j = json.loads(blk)
                found.append(j)
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

    # 队名
    home = item.get("home_name") or item.get("home_team_name") or item.get("home") or ""
    away = item.get("away_name") or item.get("away_team_name") or item.get("away") or ""

    is_home = item.get("is_home")
    if is_home is None:
        if name_hit(home, aliases):
            is_home = True
        elif name_hit(away, aliases):
            is_home = False
        else:
            return None

    opponent = away if is_home else home
    comp = item.get("competition_name") or item.get("competition") or item.get("tournament_name") or ""
    stadium = item.get("stadium_name") or item.get("stadium") or ""

    status_name = (item.get("status_name") or item.get("status") or "").strip()
    if status_name in ("延期", "推迟", "暂停"):
        tag = "⚠️比赛延期"
    elif status_name in ("取消",):
        tag = "❌比赛取消"
    elif status_name in ("待定", "未开赛", "时间待定"):
        tag = "🕓时间待定"
    elif status_name in ("完场", "已结束"):
        tag = "✅完场"
    else:
        tag = ""

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

# ===================== 直播吧 data 强容错解析 =====================
SCORE_RE = re.compile(r"^\s*(\d+\s*[-:]\s*\d+|vs|VS)\s*$")

def looks_like_team(s: str) -> bool:
    s = s.strip()
    # 允许中文或字母，长度 1-20
    return bool(re.search(r"[\u4e00-\u9fa5A-Za-z]", s)) and 1 <= len(s) <= 20

def parse_zb8_html(html: str, aliases: List[str]) -> List[Dict]:
    soup = BeautifulSoup(html, "lxml")
    rows: List[Dict] = []

    # 找所有 table 的所有 tr，逐行容错
    for tr in soup.find_all("tr"):
        tds = [td.get_text(" ", strip=True) for td in tr.find_all("td")]
        if len(tds) < 4:
            continue

        line = " | ".join(tds)

        # 日期与时间
        m_date = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", line)
        if not m_date:
            continue
        date = m_date.group(1)
        m_time = re.search(r"(\d{1,2}:\d{2})", line)
        time_local = m_time.group(1) if m_time else "20:00"

        # 尝试定位比分/VS 单元格
        score_idx = None
        for i, cell in enumerate(tds):
            if SCORE_RE.match(cell):
                score_idx = i
                break

        home = away = comp = ""
        if score_idx is not None:
            # 典型： [日期] [时间/赛事] ... [主队] [比分/VS] [客队] ...
            if score_idx - 1 >= 0:
                home = tds[score_idx - 1]
            if score_idx + 1 < len(tds):
                away = tds[score_idx + 1]

            # 赛事：在前几列挑一个包含 “联/杯/甲/超/冠” 的
            for cell in tds[:score_idx]:
                if any(k in cell for k in ("联", "杯", "甲", "超", "冠")):
                    comp = cell
                    break
        else:
            # 没有明确比分，找 “队名 VS 队名” 两侧的队名
            vs_idx = None
            for i, cell in enumerate(tds):
                if cell.strip().lower() == "vs":
                    vs_idx = i
                    break
            if vs_idx is not None:
                if vs_idx - 1 >= 0:
                    home = tds[vs_idx - 1]
                if vs_idx + 1 < len(tds):
                    away = tds[vs_idx + 1]
                for cell in tds[:vs_idx]:
                    if any(k in cell for k in ("联", "杯", "甲", "超", "冠")):
                        comp = cell
                        break
            else:
                # 再兜底：整行包含别名，且这一行里有两个像队名的词
                if any(name_hit(c, aliases) for c in tds):
                    team_words = [c for c in tds if looks_like_team(c)]
                    if len(team_words) >= 2:
                        # 默认左为主右为客
                        home, away = team_words[0], team_words[1]
                        for cell in tds:
                            if any(k in cell for k in ("联", "杯", "甲", "超", "冠")):
                                comp = cell
                                break

        if not (home and away):
            continue

        # 判定主客
        if name_hit(home, aliases):
            my_is_home, opponent = True, away
        elif name_hit(away, aliases):
            my_is_home, opponent = False, home
        else:
            # 如果两端都不含别名，就跳过（避免错抓）
            continue

        rows.append({
            "date": date,
            "time_local": time_local,
            "opponent": opponent,
            "home_away": "Home" if my_is_home else "Away",
            "competition": comp,
            "stadium": "",
            "status": ""
        })

    print(f"🔎 ZB8 解析 {len(rows)} 条")
    return rows

# ===================== 主流程 =====================
def fetch_team(team_key: str, info: Dict) -> List[Dict]:
    aliases = info["aliases"]
    now = datetime.now(CST)
    start = (now - timedelta(days=PAST_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (now + timedelta(days=FUTURE_DAYS)).replace(hour=23, minute=59, second=59, microsecond=0)

    raw_list: List[Dict] = []

    # 1) DQD API
    api_id = info.get("api_id")
    if api_id:
        api_url = API_URL_TPL.format(team_id=api_id)
        print(f"\n📡 {info['name']} API：{api_url}")
        r = http_get(api_url, is_json=True)
        if r and r.status_code == 200:
            try:
                js = r.json()
                raw_list = api_pick_matches(js)
            except Exception as e:
                print("API JSON 解析失败：", e)
        if not raw_list and r is not None:
            save_debug(f"data/debug_{team_key}.json", r.text)

    # 2) DQD HTML
    if not raw_list and info.get("dqd_page"):
        print(f"🪂 DQD 回退：{info['dqd_page']}")
        hr = http_get(info["dqd_page"], is_json=False)
        if hr and hr.status_code == 200 and hr.text:
            save_debug(f"data/debug_{team_key}_dqd.html", hr.text[:200000].encode("utf-8", "ignore"))
            raw_list = parse_dqd_html(hr.text)

    # 3) ZB8 HTML
    zb8_rows: List[Dict] = []
    if not raw_list and info.get("zb8_page"):
        print(f"🪂 ZB8 回退：{info['zb8_page']}")
        zr = http_get(info["zb8_page"], is_json=False)
        if zr and zr.status_code == 200 and zr.text:
            save_debug(f"data/debug_{team_key}_zb8.html", zr.text[:200000].encode("utf-8", "ignore"))
            zb8_rows = parse_zb8_html(zr.text, aliases)

    # 归一化
    rows: List[Dict] = []
    if raw_list:
        for it in raw_list:
            row = normalize_row(it, aliases)
            if not row:
                continue
            if not (start <= row["_dt"] <= end):
                continue
            row.pop("_dt", None)
            rows.append(row)
    else:
        rows = zb8_rows

    rows.sort(key=lambda x: (x["date"], x["time_local"], x["opponent"], x["competition"]))
    out, seen = [], set()
    for r0 in rows:
        key = (r0["date"], r0["time_local"], r0["opponent"], r0["competition"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r0)

    print(f"✅ 最终可用条数：{len(out)}")
    return out

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

def main():
    total = 0
    for key, info in TEAMS.items():
        rows = fetch_team(key, info)
        if preserve_old_if_empty(info["csv"], rows):
            continue
        write_csv(info["csv"], rows)
        total += len(rows)
    print(f"\n🎯 本次可写入总计 {total} 条。")

if __name__ == "__main__":
    main()
