import requests
import csv
from datetime import datetime

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

def fetch_match(team_key):
    team = TEAMS[team_key]
    url = f"https://api.dongqiudi.com/data/v1/team/match/{team['id']}/schedule"
    r = requests.get(url, timeout=10).json()

    matches = []
    for m in r.get("matchSchedule", []):
        try:
            dt = datetime.fromtimestamp(m["matchTime"]).strftime("%Y-%m-%d %H:%M")
            home = m["homeTeam"]["name"]
            away = m["awayTeam"]["name"]
            comp = m["competitionName"]
            score = m.get("fullScore", "")
            matches.append([dt, comp, home, score, away])
        except:
            continue
    return matches

def save_csv(team_key):
    team = TEAMS[team_key]
    filename = f"data/{team_key}.csv"
    rows = fetch_match(team_key)

    with open(filename, "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.writer(f)
        writer.writerow(["时间", "赛事", "主队", "比分", "客队"])
        writer.writerows(rows)

    print(f"{team['name']} ✅ CSV 更新成功 → {filename}")

save_csv("chengdu")
save_csv("inter")

