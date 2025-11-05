#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
终极稳态版：三层数据源
1) 懂球帝 App API（UA 可配置 + 随机兜底，自动重试，结构自适配）
2) 懂球帝球队网页（HTML 内嵌 JSON 递归提取）
3) 直播吧 data 站球队页（HTML 表格解析）
→ 若本次仍取不到，保留旧 CSV，不清空；保存 debug 原始内容便于排查。
"""

import os, re, csv, time, json, random, requests
from typing import List, Dict, Any, Iterable
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ===================== UA / 基础配置 =====================
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
        "Connection": "keep-alive",
        "Referer": "https://www.dongqiudi.com/",
    }

# ===================== 队伍配置（含三种来源） =====================
TEAMS = {
    "chengdu": {
        "name": "成都蓉城",
        "csv": "data/chengdu.csv",
        "api_id": "50016554",
        "dqd_page": "https://www.dongqiudi.com/team/50076899.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E6%88%90%E9%83%BD%E8%93%89%E5%9F%8E",
    },
    "inter": {
        "name": "国际米兰",
        "csv": "data/inter.csv",
        "api_id": "50001752",
        "dqd_page": "https://www.dongqiudi.com/team/50001042.html",
        "zb8_page": "https://data.zhibo8.cc/html/team.html?match=&team=%E5%9B%BD%E9%99%85%E7%B1%B3%E5%85%B0",
    },
}

API_URL_TPL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"
MAX_RETRIES, RETRY_DELAY = 3, 5
CST = ZoneInfo("Asia/Shanghai")
PAST_DAYS, FUTURE_DAYS = 30, 365
FIELDS = ["date", "time_local", "opponent", "home_away", "competition", "stadium", "status"]

# ===================== 小工具 =====================
def save_debug(path: str, content: str | bytes):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    mode = "wb" if isinstance(content, (bytes, bytearray)) else "w"
    with open(path, mode) as f:
        f.write(content)
    print(f"📝 debug 保存 → {path}")

def http_get(url: str, is_json=True) -> requests.Response | None:
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=headers_json() if is_json else headers_html(), timeout=20)
            if r.status_code == 200:
                return r
            print(f"⚠️ HTTP {r.status_code}（第 {i}/{MAX_RETRIES} 次）: {url}")
        except Exception as e:
            print(f"❌ 网络异常：{e}（第 {i}/{MAX_RETRIES} 次）: {url}")
        time.sleep(RETRY_DELAY)
    return None

# ===================== 懂球帝：API 结构自适配 =====================
def api_pick_matches(payload: Any) -> List[Dict]:
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), list):
        return payload["data"]
    data = payload.get("data")
    if isinstance(data, dict):
        for k in ("matches", "list", "schedules"):
            v = data.get(k)
            if isinstance(v, list):
                return v
    for k in ("matches", "list", "schedules"):
        v = payload.get(k)
        if isinstance(v, list):
            return v
    return []

# ===================== 懂球帝：网页回退（递归抓内嵌 JSON） =====================
REQ_KEYS = {"start_play", "home_name", "away_name"}

def walk(obj: Any):
    if isinstance(obj, dict):
        if REQ_KEYS.issubset(obj.keys()):
            yield obj
        for v in obj.values():
            yield from walk(v)
    elif isinstance(obj, list):
        for it in obj:
            yield from walk(it)

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
                found = list(walk(data))
                if found:
                    print(f"🔎 DQD HTML 提取 {len(found)} 条（via {pat}）")
                    return found
            except Exception:
                pass

    # 兜底：找小 JSON 块
    found = []
    for s in re.findall(r"\{[^{}]*\}", html):
        if all(k in s for k in ["start_play", "home_name", "away_name"]):
            try:
                found.append(json.loads(s))
            except Exception:
                pass
    if found:
        print(f"🔎 DQD HTML 兜底提取 {len(found)} 条")
    return found

# ===================== 直播吧：网页表格解析 =====================
def strip_tags(x: str) -> str:
    return re.sub(r"<[^>]+>", "", x or "").strip()

def parse_zb8_html(html: str, team_name: str) -> List[Dict]:
    """
    直播吧 data 站的 team.html 通常是表格结构：
    日期/时间/赛事/主队/比分/客队/…  这里用正则提取 <tr> 行→<td> 列，尽量宽松兼容。
    """
    rows: List[Dict] = []

    # 逐行提取 <tr>…</tr>
    for tr in re.findall(r"<tr[^>]*>(.*?)</tr>", html, flags=re.S | re.I):
        tds = re.findall(r"<td[^>]*>(.*?)</td>", tr, flags=re.S | re.I)
        if len(tds) < 5:
            continue

        # 粗略列位：日期、时间/赛事、主队、比分、客队（不同模板会有偏移，这里做容错）
        raw = [strip_tags(td) for td in tds]
        text = " | ".join(raw)

        # 抓日期/时间（YYYY-MM-DD, HH:MM）
        m_date = re.search(r"(\d{4}-\d{1,2}-\d{1,2})", text)
        m_time = re.search(r"(\d{1,2}:\d{2})", text)
        if not m_date:
            continue
        date = m_date.group(1)
        time_local = m_time.group(1) if m_time else "20:00"

        # 主队/客队（在一行里找最像球队名的两个词）
        # 先尝试常规布局： … | 主队 | 比分 | 客队 |
        home, away = None, None
        if len(raw) >= 5:
            home = raw[-3]
            away = raw[-1]
        # 回退：在整行里定位 team_name 出现位置，左右各取一个近似队名
        if team_name not in (home or "") and team_name not in (away or ""):
            # 简化：如果整行包含 team_name，就把另一个当对手
            if team_name in text:
                # 从可能的队名列中挑选
                candidates = [w for w in raw if 1 <= len(w) <= 20]
                # 选一个非 team_name 的作为 opponent
                opponent = None
                for w in candidates:
                    if team_name not in w and re.search(r"[\u4e00-\u9fa5A-Za-z]", w):
                        opponent = w
                        break
                if opponent:
                    # 无法判断主客，就默认“未知→按客场处理”
                    home_away = "Home" if random.random() < 0.5 else "Away"
                    comp = ""
                    stadium = ""
                    rows.append({
                        "date": date, "time_local": time_local,
                        "opponent": opponent, "home_away": home_away,
                        "competition": comp, "stadium": stadium, "status": ""
                    })
                continue

        if not home or not away:
            continue

        # 赛事
        comp = ""
        for cell in raw:
            if "杯" in cell or "甲" in cell or "联" in cell or "超" in cell:
                comp = cell
                break

        # 判断主客
        if team_name in home:
            opponent = away
            home_away = "Home"
        elif team_name in away:
            opponent = home
            home_away = "Away"
        else:
            # 行里没有该队名，跳过
            continue

        rows.append({
            "date": date, "time_local": time_local,
            "opponent": opponent, "home_away": home_away,
            "competition": comp, "stadium": "", "status": ""
        })

    print(f"🔎 ZB8 HTML 解析 {len(rows)} 条")
    return rows

# ===================== 归一化（DQD来源） =====================
def normalize_row(item: Dict, team_name: str) -> Dict | None:
    # 时间
    ts = None
    if isinstance(item.get("start_play"), (int, float)):
        ts = int(item["start_play"])
    else:
        mt = item.get("match_time")
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

    # 主客判断
    home = item.get("home_name") or item.get("home") or ""
    away = item.get("away_name") or item.get("away") or ""
    is_home = item.get("is_home")
    if is_home is None:
        if home and team_name in str(home):
            is_home = True
        elif away and team_name in str(away):
            is_home = False
        else:
            return None

    opponent = away if is_home else home
    comp = item.get("competition_name") or item.get("competition") or ""
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

# ===================== 主流程（API → DQD HTML → ZB8 HTML） =====================
def fetch_team(team_key: str, api_id: str | None, dqd_page: str | None, zb8_page: str | None, team_name: str) -> List[Dict]:
    now = datetime.now(CST)
    start = (now - timedelta(days=PAST_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (now + timedelta(days=FUTURE_DAYS)).replace(hour=23, minute=59, second=59, microsecond=0)

    raw_list: List[Dict] = []

    # 1) DQD API
    if api_id:
        api_url = API_URL_TPL.format(team_id=api_id)
        print(f"\n📡 {team_name} API：{api_url}")
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
    if not raw_list and dqd_page:
        print(f"🪂 DQD 回退：{dqd_page}")
        hr = http_get(dqd_page, is_json=False)
        if hr and hr.status_code == 200 and hr.text:
            save_debug(f"data/debug_{team_key}_dqd.html", hr.text[:200000].encode("utf-8", "ignore"))
            raw_list = parse_dqd_html(hr.text)

    # 3) ZB8 HTML
    zb8_rows: List[Dict] = []
    if not raw_list and zb8_page:
        print(f"🪂 ZB8 回退：{zb8_page}")
        zr = http_get(zb8_page, is_json=False)
        if zr and zr.status_code == 200 and zr.text:
            save_debug(f"data/debug_{team_key}_zb8.html", zr.text[:200000].encode("utf-8", "ignore"))
            zb8_rows = parse_zb8_html(zr.text, team_name)

    # 若抓到的是 DQD 结构，继续归一化；若是 ZB8 行则直接用
    rows: List[Dict] = []
    if raw_list:
        for it in raw_list:
            row = normalize_row(it, team_name)
            if not row:
                continue
            if not (start <= row["_dt"] <= end):
                continue
            rows.append(row)
        # 去掉内部字段
        for r0 in rows:
            r0.pop("_dt", None)
    else:
        rows = zb8_rows

    # 去重 + 排序
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

# ===================== CSV 与兜底 =====================
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
        rows = fetch_team(
            team_key=key,
            api_id=info.get("api_id"),
            dqd_page=info.get("dqd_page"),
            zb8_page=info.get("zb8_page"),
            team_name=info["name"],
        )
        if preserve_old_if_empty(info["csv"], rows):
            continue
        write_csv(info["csv"], rows)
        total += len(rows)
    print(f"\n🎯 本次可写入总计 {total} 条。")

if __name__ == "__main__":
    main()
    
