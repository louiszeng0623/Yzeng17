#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
懂球帝 App API 稳定版爬虫
支持自动重试、日志记录、数据去重。
"""

import requests
import csv
import time
import os
from datetime import datetime
from typing import List, Dict

# ==========================
# 配置区
# ==========================
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
MAX_RETRIES = 3
RETRY_DELAY = 5


# ==========================
# 工具函数
# ==========================
def safe_request(url: str) -> Dict:
    """带重试机制的请求"""
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20)
            if resp.status_code == 200:
                return resp.json()
            else:
                print(f"⚠️ 请求失败({resp.status_code})，重试 {attempt}/{MAX_RETRIES}")
        except Exception as e:
            print(f"❌ 网络错误: {e}，重试 {attempt}/{MAX_RETRIES}")
        time.sleep(RETRY_DELAY)
    print("🚫 多次重试失败，跳过此队伍。")
    return {}


def fetch_team_schedule(team_id: str, team_name: str) -> List[Dict]:
    """获取懂球帝球队赛程"""
    url = API_URL.format(team_id=team_id)
    print(f"\n📦 正在抓取 {team_name} 赛程...")
    data = safe_request(url)
    matches = []

    for item in data.get("data", []):
        try:
            match_time = datetime.fromtimestamp(item["start_play"])
            date_str = match_time.strftime("%Y-%m-%d")
            time_str = match_time.strftime("%H:%M")
            opponent = item["away_name"] if item["is_home"] else item["home_name"]
            home_away = "Home" if item["is_home"] else "Away"
            comp = item.get("competition_name", "")
            stadium = item.get("stadium_name", "")
            matches.append(
                {
                    "date": date_str,
                    "time_local": time_str,
                    "opponent": opponent,
                    "home_away": home_away,
                    "competition": comp,
                    "stadium": stadium,
                }
            )
        except Exception as e:
            print(f"解析错误: {e}")

    print(f"✅ {team_name} 共获取 {len(matches)} 场比赛。")
    return matches


def deduplicate_matches(matches: List[Dict]) -> List[Dict]:
    """去重"""
    seen = set()
    unique = []
    for m in matches:
        key = (m["date"], m["opponent"], m["competition"])
        if key not in seen:
            unique.append(m)
            seen.add(key)
    return unique


def save_to_csv(matches: List[Dict], csv_path: str):
    """保存为 CSV 文件"""
    os.makedirs(os.path.dirname(csv_path), exist_ok=True)
    matches = deduplicate_matches(matches)
    with open(csv_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["date", "time_local", "opponent", "home_away", "competition", "stadium"],
        )
        writer.writeheader()
        writer.writerows(matches)
    print(f"💾 已保存 {len(matches)} 场比赛到 {csv_path}")


def main():
    all_total = 0
    for key, team in TEAMS.items():
        matches = fetch_team_schedule(team["id"], team["name"])
        save_to_csv(matches, team["csv"])
        all_total += len

