#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import requests
import csv
from datetime import datetime

# === 配置 ===
HEADERS = {
    "User-Agent": "dongqiudiApp/7.0.6 (iPhone; iOS 17.0.1; Scale/3.00)",
    "Referer": "https://m.dongqiudi.com/",
    "Accept-Encoding": "gzip, deflate, br",
}

TEAMS = {
    "chengdu": {
        "id": "50001752",
        "name": "成都蓉城",
        "csv": "data/chengdu.csv",
    },
    "inter": {
        "id": "50000457",
        "name": "国际米兰",
        "csv": "data/inter.csv",
    },
}

API_URL = "https://api.dongqiudi.com/v3/team/schedule/list?team_id={team_id}"


def fetch_team_schedule(team_id: str, team_name: str):
    """获取懂球帝球队赛程"""
    url = API_URL.format(team_id=team_id)
    print(f"正在获取 {team_name} 的赛程数据...")
    resp = requests.get(url, headers=HEADERS, timeout=15)
    resp.raise_for_status()
    data = resp.json()

    matches = []
    for item in data.get("data", []):
        try:
            match_time = datetime.fromtimestamp(item["start_play"])
            date_str = match_time.strftime("%Y-%m-%d")
            time_str = match_time.strftime("%H:%M")
            opponent = item["away_name"] if item["is_home"] else item["home_name"]
            home_away = "Home" if item["is_home"] else "Away"
            competition = item.get("competition_name", "")
            stadium = item.get("stadium_name", "")
            matches.append(
                {
                    "date": date_str,
                    "time_local": time_str,
                    "opponent": opponent,
                    "home_away": home_away,
                    "competition": competition,
                    "stadium": stadium,
                }
            )
        except Exception as e:
            print(f"解析错误: {e}")

    print(f"{team_name} 共获取 {len(matches)} 场比赛。")
    return matches


def save_to_csv(matches, csv_path):
    """保存为 CSV 文件"""
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "time_local", "opponent", "home_away", "competition", "stadium"],
        )
        writer.writeheader()
        writer.writerows(matches)
    print(f"✅ 已保存至 {csv_path}")


def main():
    for key, team in TEAMS.items():
        matches = fetch_team_schedule(team["id"], team["name"])
        save_to_csv(matches, team["csv"])


if __name__ == "__main__":
    main()
