# -*- coding: utf-8 -*-
import requests
import csv
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

TEAMS = {
    "chengdu": {
        "name": "成都蓉城",
        "id": "50076899"
    },
    "inter": {
        "name": "国际米兰",
        "id": "50001042"
    }
}

def fetch(team_key):
    t = TEAMS[team_key]
    url = f"https://api.dongqiudi.com/v3/team/schedule?team_id={t['id']}"
    print(f"▶ 获取 {t['name']} API 数据…")

    r = requests.get(url, timeout=20)
    data = r.json()

    matches = data.get("data", {}).get("list", [])
    rows = []
    for m in matches:
        ts = m.get("match_time")
        dt = datetime.fromtimestamp(ts, tz=CST).strftime("%Y-%m-%d %H:%M")

        comp = m.get("competition_name", "")
        home = m.get("home_name", "")
        away = m.get("away_name", "")
        hs = m.get("home_score")
        as_ = m.get("away_score")
        score = f"{hs}-{as_}" if hs is not None and as_ is not None else ""

        rows.append([dt, comp, home, score, away])

    out = f"data/{team_key}.csv"
    with open(out, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f)
        w.writerow(["时间", "赛事", "主队", "比分", "客队"])
        w.writerows(rows)

    print(f"✅ {t['name']} 共 {len(rows)} 场 → {out}")

if __name__ == "__main__":
    fetch("chengdu")
    fetch("inter")


