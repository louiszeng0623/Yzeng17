# -*- coding: utf-8 -*-
import pandas as pd
from ics import Calendar, Event
from datetime import datetime, timezone, timedelta

CST = timezone(timedelta(hours=8))  # Asia/Shanghai

def parse_dt(s: str) -> datetime:
    s = (s or "").strip()
    for fmt in ("%Y-%m-%d %H:%M", "%m-%d %H:%M", "%Y/%m/%d %H:%M"):
        try:
            dt = datetime.strptime(s, fmt)
            # 没有年份的，补今年
            if fmt == "%m-%d %H:%M":
                dt = dt.replace(year=datetime.now(CST).year)
            return dt.replace(tzinfo=CST)
        except Exception:
            continue
    # 兜底：当前时间
    return datetime.now(CST)

def make_calendar(team_name: str, csv_file: str, out_ics: str):
    try:
        df = pd.read_csv(csv_file)
    except Exception:
        df = pd.DataFrame(columns=["时间", "赛事", "主队", "比分", "客队"])

    cal = Calendar()
    for _, row in df.iterrows():
        t = parse_dt(str(row.get("时间", "")))
        home = str(row.get("主队", "") or "")
        away = str(row.get("客队", "") or "")
        comp = str(row.get("赛事", "") or "")
        score = str(row.get("比分", "") or "").strip()

        title = f"{home} vs {away}"
        if score and score not in ("", "VS", "vs"):
            title = f"{home} {score} {away}"
        if comp:
            title = f"{title} | {comp}"

        ev = Event()
        ev.name = f"{team_name}：{title}"
        ev.begin = t
        ev.duration = {"hours": 2}
        cal.events.add(ev)

    with open(out_ics, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())

    print(f"✅ {team_name} 日历生成 → {out_ics}（{len(cal.events)} 场）")

# 分开两个日历
make_calendar("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
make_calendar("国际米兰", "data/inter.csv", "calendar_inter.ics")
