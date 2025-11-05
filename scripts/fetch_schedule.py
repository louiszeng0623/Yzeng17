#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
懂球帝 App API 稳定增强版
- 正确球队 ID（成都蓉城50016554，国际米兰50001752）
- 北京时间转换（Asia/Shanghai）
- 自动重试、防403（UA）
- 延期/取消/待定状态标注
- 仅保留未来比赛、排序去重
"""

import requests, csv, time, os
from datetime import datetime
from zoneinfo import ZoneInfo
from typing import List, Dict, Any

HEADERS = {
    "User-Agent": "dongqiudiApp/7.0.6 (iPhone; iOS 17.0.1; Scale/3.00)",
    "Referer": "https://m.dongqiudi.com/",
    "Accept-Encoding": "gzip, deflate, br",
}

TEAMS = {
    "chengdu": {"id": "50016554", "name": "成都蓉城", "csv": "data/chengdu.csv"},
    "inter":   {"id": "50001752", "name": "国际米兰", "csv": "data/inter.csv"},
}

API_URL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"
MAX_RETRIES = 3
RETRY_DELAY = 5
CST = ZoneInfo("Asia/Shanghai")

def safe_get_json(url: str) -> Dict[str, Any]:
    for i in range(1, MAX_RETRIES + 1):
        try:
            r = requests.get(url, headers=HEADERS, timeout=20)
            if r.status_code == 200:
                return r.json()
            print(f"⚠️ HTTP {r.status_code}（第 {i}/{MAX_RETRIES} 次）")
        except Exception as e:
            print(f"❌ 网络异常：{e}（第 {i}/{MAX_RETRIES} 次）")
        time.sleep(RETRY_DELAY)
    return {}

def pick_matches(payload: Dict[str, Any]) -> List[Dict[str, Any]]:
    """兼容不同返回结构：data(list) 或 data.matches(list)"""
    if not isinstance(payload, dict):
        return []
    d = payload.get("data")
    if isinstance(d, list):
        return d
    if isinstance(d, dict) and isinstance(d.get("matches"), list):
        return d["matches"]
    return []

def status_tag(status_name: str) -> str:
    s = (status_name or "").strip()
    if s in ("延期", "推迟", "暂停"):
        return "⚠️比赛延期"
    if s in ("取消",):
        return "❌比赛取消"
    if s in ("待定", "未开赛", "时间待定"):
        return "🕓时间待定"
    if s in ("完场", "已结束"):
        return "✅完场"
    return ""

def fetch_team(team_id: str, team_name: str) -> List[Dict[str, str]]:
    url = API_URL.format(team_id=team_id)
    print(f"\n📦 抓取 {team_name} …")
    js = safe_get_json(url)
    raw = pick_matches(js)

    now = datetime.now(CST)
    rows: List[Dict[str, str]] = []
    for it in raw:
        try:
            ts = int(it.get("start_play", 0))  # Unix 秒
            if ts <= 0:
                continue
            dt = datetime.fromtimestamp(ts, tz=CST)
            if dt <= now:
                continue  # 仅未来比赛

            is_home = bool(it.get("is_home"))
            home = it.get("home_name", "")
            away = it.get("away_name", "")
            opponent = away if is_home else home

            rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "time_local": dt.strftime("%H:%M"),
                "opponent": opponent,
                "home_away": "Home" if is_home else "Away",
                "competition": it.get("competition_name", ""),
                "stadium": it.get("stadium_name", ""),
                "status": status_tag(it.get("status_name")),
            })
        except Exception as e:
            print("解析错误：", e)

    # 去重+排序
    seen, out = set(), []
    for r in rows:
        key = (r["date"], r["time_local"], r["opponent"], r["competition"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    out.sort(key=lambda x: (x["date"], x["time_local"]))

    print(f"✅ {team_name} 获取到 {len(out)} 场未来比赛")
    return out

def save_csv(path: str, rows: List[Dict[str, str]]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["date", "time_local", "opponent", "home_away", "competition", "stadium", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"💾 已写入 {len(rows)} 条 → {path}")

def main():
    total = 0
    for _, info in TEAMS.items():
        rows = fetch_team(info["id"], info["name"])
        save_csv(info["csv"], rows)
        total += len(rows)
    print(f"\n🎯 总计写入 {total} 条，完成。")

if __name__ == "__main__":
    main()
