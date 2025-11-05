#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
稳态容错版：
- 主源：懂球帝 App API（UA 可配置 + 随机兜底）
- 自动重试、防 403、结构自适配（data / data.matches / list / matches / schedules）
- 时间统一为 Asia/Shanghai，保留 [今天起+365天] 与 [过去30天] 的比赛
- 抓空/403：不覆盖旧 CSV；原始 JSON 落盘 data/debug_*.json
"""

import os, csv, time, json, random, requests
from typing import List, Dict, Any
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

# ---------------- UA 可配置（推荐在 workflow 里用 env: DQD_USER_AGENT 指定） ----------------
DEFAULT_UAS = [
    "dongqiudiApp/7.1.0 (iPhone; iOS 17.5; Scale/3.00)",
    "dongqiudiApp/7.0.6 (iPhone; iOS 17.0.1; Scale/3.00)",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_5 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Mobile/15E148",
]
def pick_ua() -> str:
    ua_env = os.getenv("DQD_USER_AGENT", "").strip()
    return ua_env if ua_env else random.choice(DEFAULT_UAS)

def build_headers() -> Dict[str, str]:
    return {
        "User-Agent": pick_ua(),
        "Referer": "https://m.dongqiudi.com/",
        "Accept": "application/json,text/plain,*/*",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
    }

# ---------------- 队伍配置（ID 已校正） ----------------
TEAMS = {
    "chengdu": {"id": "50016554", "name": "成都蓉城", "csv": "data/chengdu.csv"},
    "inter":   {"id": "50001752", "name": "国际米兰", "csv": "data/inter.csv"},
}

API_URL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"
MAX_RETRIES, RETRY_DELAY = 3, 5
CST = ZoneInfo("Asia/Shanghai")

PAST_DAYS   = 30      # 保留过去 N 天（避免空表）
FUTURE_DAYS = 365     # 保留未来 N 天

# ---------------- HTTP with retry ----------------
def safe_get_json(url: str) -> Dict[str, Any]:
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=build_headers(), timeout=20)
            if r.status_code == 200:
                return r.json()
            print(f"⚠️ HTTP {r.status_code}（第 {i}/{MAX_RETRIES} 次）")
        except Exception as e:
            print(f"❌ 网络异常：{e}（第 {i}/{MAX_RETRIES} 次）")
        time.sleep(RETRY_DELAY)
    return {}

# ---------------- 结构自适配 ----------------
def pick_matches(payload: Any) -> List[Dict]:
    if not isinstance(payload, dict):
        return []
    # 1) data 为 list
    if isinstance(payload.get("data"), list):
        return payload["data"]
    # 2) data 为 dict，找常见键
    data = payload.get("data")
    if isinstance(data, dict):
        for key in ("matches", "list", "schedules"):
            v = data.get(key)
            if isinstance(v, list):
                return v
    # 3) 顶层兜底
    for key in ("matches", "list", "schedules"):
        v = payload.get(key)
        if isinstance(v, list):
            return v
    return []

# ---------------- 行归一化 ----------------
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
        # 兜底用名称匹配
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
        "_dt": dt,  # 排序/过滤用
    }

# ---------------- 抓取 + 过滤 + 去重 ----------------
def fetch_team(team_key: str, team_id: str, team_name: str) -> List[Dict]:
    url = API_URL.format(team_id=team_id)
    print(f"\n📡 {team_name}：{url}")
    raw_json = safe_get_json(url)
    raw_list = pick_matches(raw_json)
    print(f"↪ 原始条数：{len(raw_list)}")

    now = datetime.now(CST)
    start = (now - timedelta(days=PAST_DAYS)).replace(hour=0, minute=0, second=0, microsecond=0)
    end   = (now + timedelta(days=FUTURE_DAYS)).replace(hour=23, minute=59, second=59, microsecond=0)

    rows: List[Dict] = []
    for it in raw_list:
        row = normalize_row(it, team_name)
        if not row:
            continue
        if not (start <= row["_dt"] <= end):
            continue
        rows.append(row)

    # 排序 + 去重
    rows.sort(key=lambda x: (x["_dt"], x["opponent"], x["competition"]))
    out, seen = [], set()
    for r in rows:
        key = (r["date"], r["time_local"], r["opponent"], r["competition"])
        if key in seen:
            continue
        seen.add(key)
        r.pop("_dt", None)
        out.append(r)

    print(f"✅ 过滤后条数：{len(out)}")
    if not out:
        os.makedirs("data", exist_ok=True)
        with open(f"data/debug_{team_key}.json", "w", encoding="utf-8") as f:
            json.dump(raw_json, f, ensure_ascii=False, indent=2)
        print(f"⚠️ 无有效数据，已保存原始返回 data/debug_{team_key}.json")
    return out

# ---------------- CSV I/O ----------------
FIELDS = ["date", "time_local", "opponent", "home_away", "competition", "stadium", "status"]

def write_csv(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=FIELDS)
        w.writeheader()
        w.writerows(rows)
    print(f"💾 写入 {len(rows)} 条 → {path}")

def preserve_old_if_empty(path: str, new_rows: List[Dict]) -> bool:
    """
    如果 new_rows 为空且已有旧 CSV，则保持旧文件不动，返回 True（表示已保留旧数据）。
    """
    if new_rows:
        return False
    if os.path.exists(path) and os.path.getsize(path) > 0:
        print(f"🛟 新数据为空，保留旧文件：{path}")
        return True
    return False

# ---------------- main ----------------
def main():
    total = 0
    for key, info in TEAMS.items():
        rows = fetch_team(key, info["id"], info["name"])
        # 新数据为空 → 不覆盖旧 CSV（保证有数据）
        if preserve_old_if_empty(info["csv"], rows):
            continue
        write_csv(info["csv"], rows)
        total += len(rows)
    print(f"\n🎯 本次可写入总计 {total} 条。")

if __name__ == "__main__":
    main()
