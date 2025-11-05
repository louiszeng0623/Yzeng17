# -*- coding: utf-8 -*-
import pandas as pd
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))

def parse_dt(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            if fmt == "%m-%d %H:%M":
                dt = dt.replace(year=datetime.now(CST).year)
            return dt.replace(tzinfo=CST)
        except Exception:
            continue
    return datetime.now(CST)

def make_calendar(team_name: str, csv_file: str, out_ics: str):
    try:
        df = pd.read_csv(csv_file)
    except Exception:
        df = pd.DataFrame(columns=["时间", "赛事", "主队", "比分", "客队"])

    cal = Calendar()
    for _, row in df.iterrows():
        dt = parse_dt(str(row.get("时间", "")))
        comp = str(row.get("赛事", "") or "")
        home = str(row.get("主队", "") or "")
        away = str(row.get("客队", "") or "")
        score = str(row.get("比分", "") or "").strip()

        title = f"{home} vs {away}"
        if score and "-" in score:
            title = f"{home} {score} {away}"
        if comp:
            title += f" | {comp}"

        ev = Event()
        ev.name = f"{team_name}：{title}"
        ev.begin = dt
        ev.duration = {"hours": 2}
        cal.events.add(ev)

    with open(out_ics, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"✅ {team_name} 日历生成 → {out_ics}（{len(cal.events)} 场）")

make_calendar("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
make_calendar("国际米兰", "data/inter.csv", "calendar_inter.ics")

