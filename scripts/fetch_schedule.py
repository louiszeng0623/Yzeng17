#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
懂球帝 App API 稳定增强版
- 正确球队 ID
- 北京时间转换（Asia/Shanghai）
- 自动重试、防403（UA）
- 延期/取消状态标注
- 仅保留未来比赛
"""

import requests, csv, time, os
from datetime import datetime, timezone
from zoneinfo import ZoneInfo
from typing import List, Dict

HEADERS = {
    "User-Agent": "dongqiudiApp/7.0.6 (iPhone; iOS 17.0.1; Scale/3.00)",
    "Referer": "https://m.dongqiudi.com/",
    "Accept-Encoding": "gzip, deflate, br",
}

# ✅ 校正后的球队 ID（这两个是导致你数据错乱的根因）
# 成都蓉城：50016554（你截图里也有这个）
# 国际米兰：50001752
TEAMS = {
    "chengdu": {"id": "50016554", "name": "成都蓉城", "csv": "data/chengdu.csv"},
    "inter":   {"id": "50001752", "name": "国际米兰", "csv": "data/inter.csv"},
}

API_URL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"
MAX_RETRIES = 3
RETRY_DELAY = 5
CST = ZoneInfo("Asia/Shanghai")


def safe_get_json(url: str) -> Dict:
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


def pick_matches(payload: Dict) -> List[Dict]:
    """兼容不同字段：有的返回 data(list)，有的在 data.matches"""
    if not isinstance(payload, dict):
        return []
    if isinstance(payload.get("data"), list):
        return payload["data"]
    if isinstance(payload.get("data"), dict) and isinstance(payload["data"].get("matches"), list):
        return payload["data"]["matches"]
    return []


def fetch_team(team_id: str, team_name: str) -> List[Dict]:
    url = API_URL.format(team_id=team_id)
    print(f"\n📦 抓取 {team_name} …")
    js = safe_get_json(url)
    raw = pick_matches(js)

    now = datetime.now(CST)
    rows: List[Dict] = []
    for it in raw:
        try:
            # 懂球帝 start_play 是 Unix 秒，按北京时间转换，避免 UTC 导致跨日
            ts = int(it.get("start_play", 0))
            if ts <= 0:
                continue
            dt = datetime.fromtimestamp(ts, tz=CST)
            if dt <= now:
                continue  # 仅未来比赛

            is_home = bool(it.get("is_home"))
            home = it.get("home_name", "")
            away = it.get("away_name", "")
            opponent = away if is_home else home
            comp = it.get("competition_name", "")
            stadium = it.get("stadium_name", "")

            # 状态标识
            status_name = (it.get("status_name") or "").strip()
            if status_name in ("延期", "推迟", "暂停"):
                tag = "⚠️比赛延期"
            elif status_name in ("取消",):
                tag = "❌比赛取消"
            elif status_name in ("待定", "未开赛", "时间待定"):
                tag = "🕓时间待定"
            elif status_name in ("完场", "已结束"):
                tag = "✅完场"
            else:
                tag = ""  # 正常未开赛

            rows.append({
                "date": dt.strftime("%Y-%m-%d"),
                "time_local": dt.strftime("%H:%M"),
                "opponent": opponent,
                "home_away": "Home" if is_home else "Away",
                "competition": comp,
                "stadium": stadium,
                "status": tag,
            })
        except Exception as e:
            print("解析错误：", e)

    print(f"✅ {team_name} 获取到 {len(rows)} 场未来比赛")
    return dedup(rows)


def dedup(items: List[Dict]) -> List[Dict]:
    seen, out = set(), []
    for r in items:
        key = (r["date"], r["time_local"], r["opponent"], r["competition"])
        if key in seen:
            continue
        seen.add(key)
        out.append(r)
    # 按时间排序
    out.sort(key=lambda x: (x["date"], x["time_local"]))
    return out


def save_csv(path: str, rows: List[Dict]):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    fields = ["date", "time_local", "opponent", "home_away", "competition", "stadium", "status"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)
    print(f"💾 已写入 {len(rows)} 条 → {path}")


def main():
    total = 0
    for key, info in TEAMS.items():
        rows = fetch_team(info["id"], info["name"])
        save_csv(info["csv"], rows)
        total += len(rows)
    print(f"\n🎯 总计写入 {total} 条，完成。")


if __name__ == "__main__":
    main()
    
