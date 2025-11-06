import pandas as pd
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

def to_dt(s):
    return datetime.strptime(s, "%Y-%m-%d %H:%M").replace(tzinfo=CST)

def make(team_name, csv_path, ics_path):
    try:
        df = pd.read_csv(csv_path)
    except:
        df = pd.DataFrame(columns=["时间", "赛事", "主队", "比分", "客队"])

    cal = Calendar()
    for _, r in df.iterrows():
        title = f"{r['主队']} vs {r['客队']} | {r['赛事']}"
        ev = Event()
        ev.name = f"{team_name}：{title}"
        ev.begin = to_dt(r["时间"])
        ev.duration = {"hours": 2}
        cal.events.add(ev)

    with open(ics_path, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"📅 {team_name} 日历生成 → {ics_path}")

make("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
make("国际米兰", "data/inter.csv", "calendar_inter.ics")
