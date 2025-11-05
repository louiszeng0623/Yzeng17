#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv
from datetime import datetime

TEAM_FILES = {
    "成都蓉城": "data/chengdu.csv",
    "国际米兰": "data/inter.csv",
}
README = "README.md"

def next_match(csv_path):
    try:
        with open(csv_path, encoding="utf-8") as f:
            r = csv.DictReader(f)
            now = datetime.now()
            for row in r:
                try:
                    when = datetime.strptime(f"{row['date']} {row['time_local']}", "%Y-%m-%d %H:%M")
                    if when > now:
                        return {
                            "competition": row.get("competition",""),
                            "opponent": row.get("opponent",""),
                            "when": when.strftime("%m-%d %H:%M"),
                            "venue": "主场" if row.get("home_away")=="Home" else "客场",
                            "status": row.get("status",""),
                        }
                except Exception:
                    continue
    except FileNotFoundError:
        return None
    return None

def build_table():
    lines = [
        "| 球队 | 赛事 | 对手 | 时间 | 主/客场 | 状态 |",
        "|------|------|------|------|--------|------|",
    ]
    for team, path in TEAM_FILES.items():
        m = next_match(path)
        if not m:
            lines.append(f"| {team} | - | - | - | - | - |")
        else:
            lines.append(f"| {team} | {m['competition']} | {m['opponent']} | {m['when']} | {m['venue']} | {m['status']} |")
    return "\n".join(lines)

def main():
    content = f"""# ⚽ GitHub 自动更新足球订阅日历

- 每天凌晨 04:00（北京时间）自动同步赛程
- iPhone 订阅链接：`https://louiszeng0623.github.io/Yzeng17/calendar.ics`

## 📊 最近一场（自动更新）
{build_table()}

> 更新时间：{datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
"""
    with open(README, "w", encoding="utf-8") as f:
        f.write(content)
    print("✅ README.md 已更新")

if __name__ == "__main__":
    main()
