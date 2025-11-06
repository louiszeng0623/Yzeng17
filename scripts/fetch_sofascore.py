import requests
import pandas as pd
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

teams = {
    "chengdu": {"id": 29335, "name": "成都蓉城"},
    "inter": {"id": 44, "name": "国际米兰"}
}

def fetch_events(team_id):
    urls = [
        f"https://api.sofascore.com/api/v1/team/{team_id}/events/next/0",
        f"https://api.sofascore.com/api/v1/team/{team_id}/events/last/0"
    ]
    events = []
    for url in urls:
        r = requests.get(url, timeout=15)
        data = r.json().get("events", [])
        events.extend(data)
    return events

def convert(team_key, team_data):
    print(f"▶ 正在更新：{team_data['name']}")
    events = fetch_events(team_data["id"])
    rows = []

    for m in events:
        ts = m.get("startTimestamp", 0)
        dt = datetime.fromtimestamp(ts, tz=CST).strftime("%Y-%m-%d %H:%M")

        comp = m.get("tournament", {}).get("name", "")
        home = m.get("homeTeam", {}).get("name", "")
        away = m.get("awayTeam", {}).get("name", "")
        score = m.get("homeScore", {}).get("current", None)
        score2 = m.get("awayScore", {}).get("current", None)

        if score is not None and score2 is not None:
            score = f"{score}-{score2}"
        else:
            score = "VS"

        rows.append([dt, comp, home, score, away])

    df = pd.DataFrame(rows, columns=["时间", "赛事", "主队", "比分", "客队"])
    df.to_csv(f"data/{team_key}.csv", index=False, encoding="utf-8-sig")
    print(f"✅ {team_data['name']} 完成，共 {len(df)} 场")

if __name__ == "__main__":
    for key, info in teams.items():
        convert(key, info)
