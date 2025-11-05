#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动从懂球帝 API 获取 成都蓉城 & 国际米兰 的赛程数据
生成 CSV 并供 build_ics.py 使用
作者：Louis Zeng 自动日历系统
"""

import requests, csv
from datetime import datetime
from zoneinfo import ZoneInfo

HEADERS = {"User-Agent": "Mozilla/5.0 (Louis-Auto-Calendar)"}
CST = ZoneInfo("Asia/Shanghai")

# 懂球帝球队ID（最新）
TEAMS = {
    "chengdu": {"id": 50016554, "name": "成都蓉城"},
    "inter": {"id": 50001752, "name": "国际米兰"}
}

def fetch_team_schedule(team_id: int):
    """从懂球帝API获取指定球队的未来赛程"""
    url = f"https://api.dongqiudi.com/v1/team/schedule?team_id={team_id}"
    r = requests.get(url, headers=HEADERS, timeout=20)
    r.raise_for_status()
    data = r.json()
    if "list" not in data:
        print(f"⚠️ API 无有效返回: {url}")
        return []
    games = []
    now = datetime.now(CST)
    team_name = data.get("team_name", "")
    for match in data["list"]:
        try:
            t = datetime.fromisoformat(
                match["match_time"].replace("Z", "+00:00")
            ).astimezone(CST)
            if t < now:
                continue
            comp = match.get("competition_name", "")
            home = match.get("home_name", "")
            away = match.get("away_name", "")
            opponent = away if home == team_name else home
            home_away = "Home" if home == team_name else "Away"
            stadium = match.get("stadium", "")
            games.append({
                "date": t.strftime("%Y-%m-%d"),
                "time_local": t.strftime("%H:%M"),
                "opponent": opponent,
                "home_away": home_away,
                "competition": comp,
                "stadium": stadium
            })
        except Exception as e:
            print("解析错误:", e)
    return games

def write_csv(path, rows):
    fieldnames = ["date", "time_local", "opponent", "home_away", "competition", "stadium"]
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)
    print(f"✅ 写入 {path} ({len(rows)} 场比赛)")

def main():
    all_ok = True
    for key, info in TEAMS.items():
        try:
            rows = fetch_team_schedule(info["id"])
            if not rows:
                print(f"⚠️ 未抓到 {info['name']} 的数据")
                all_ok = False
            write_csv(f"data/{key}.csv", rows)
        except Exception as e:
            print(f"❌ 抓取 {info['name']} 失败: {e}")
            all_ok = False
    if all_ok:
        print("🎯 全部数据更新完毕，可生成 calendar.ics")

if __name__ == "__main__":
    main()
