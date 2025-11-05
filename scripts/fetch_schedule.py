#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
自动更新 README.md 显示最近赛程概览
"""

import csv
from datetime import datetime, timedelta

TEAM_CSV = {
    "成都蓉城": "data/chengdu.csv",
    "国际米兰": "data/inter.csv",
}

README_PATH = "README.md"


def load_next_match(csv_file):
    try:
        with open(csv_file, encoding="utf-8") as f:
            reader = csv.DictReader(f)
            now = datetime.now()
            for row in reader:
                try:
                    match_time = datetime.strptime(f"{row['date']} {row['time_local']}", "%Y-%m-%d %H:%M")
                    if match_time > now:
                        return {
                            "date": row['date'],
                            "time": row['time_local'],
                            "opponent": row['opponent'],
                            "home_away": "主场" if row['home_away'] == "Home" else "客场",
                            "status": row.get('status', ''),
                            "competition": row.get('competition', '')
                        }
                except Exception:
                    continue
    except FileNotFoundError:
        return None
    return None


def build_table():
    rows = []
    for team, path in TEAM_CSV.items():
        match = load_next_match(path)
        if match:
            rows.append(
                f"| {team} | {match['competition']} | {match['opponent']} | {match['date']} {match['time']} | {match['home_away']} | {match['status']} |"
            )
        else:
            rows.append(f"| {team} | 无数据 | - | - | - | - |")
    table = "\n".join(rows)
    return (
        "| 球队 | 赛事 | 对手 | 时间 | 主/客场 | 状态 |\n"
        "|------|------|------|------|--------|------|\n"
        + table
    )


def update_readme():
    new_table = build_table()
    content = f"""# ⚽ 自动更新足球赛程订阅日历

本项目会每日凌晨自动同步成都蓉城与国际米兰最新赛程信息，并生成 iPhone 可订阅日历文件。

## 📅 最新赛程预览（自动更新）

{new_table}

---
> 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    with open(README_PATH, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ README.md 已更新。")


if __name__ == "__main__":
    update_readme()
