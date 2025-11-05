#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, uuid
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

TIMEZONE_NAME = "Asia/Shanghai"
TZ = ZoneInfo(TIMEZONE_NAME)
FIELDS = ["date","time_local","opponent","home_away","competition","stadium","status"]

def load(csv_file: str, team_name: str):
    events = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        r = csv.DictReader(f)
        for row in r:
            try:
                dt_local = datetime.strptime(f"{row['date']} {row['time_local'] or '20:00'}", "%Y-%m-%d %H:%M").replace(tzinfo=TZ)
            except Exception:
                continue
            dt_end = dt_local + timedelta(hours=2)
            opponent = row["opponent"]
            home = (row.get("home_away") or "Home") == "Home"
            comp = row.get("competition","")
            stadium = row.get("stadium","")
            status = row.get("status","")
            summary = f"{team_name} vs {opponent}" if home else f"{opponent} vs {team_name}"
            desc = f"{comp} | {'主场' if home else '客场'}"
            if stadium: desc += f" | {stadium}"
            if status: desc += f" | {status}"
            events.append({
                "uid": uuid.uuid4().hex,
                "start": dt_local, "end": dt_end,
                "summary": summary, "desc": desc, "loc": stadium
            })
    return events

def fmt(dt: datetime) -> str:
    return dt.strftime("%Y%m%dT%H%M%S")

def build(ev, outfile="calendar.ics"):
    lines = [
        "BEGIN:VCALENDAR","VERSION:2.0","CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{TIMEZONE_NAME}","PRODID:-//football-fixtures//CN"
    ]
    now = datetime.now(TZ)
    for e in ev:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{e['uid']}@fixtures",
            f"DTSTAMP;TZID={TIMEZONE_NAME}:{fmt(now)}",
            f"DTSTART;TZID={TIMEZONE_NAME}:{fmt(e['start'])}",
            f"DTEND;TZID={TIMEZONE_NAME}:{fmt(e['end'])}",
            f"SUMMARY:{e['summary']}",
            f"DESCRIPTION:{e['desc']}",
            f"LOCATION:{e['loc']}",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    with open(outfile,'w',encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"✅ 生成 {outfile}（{len(ev)} 条事件）")

if __name__ == "__main__":
    all_ev = []
    all_ev += load("data/chengdu.csv","成都蓉城")
    all_ev += load("data/inter.csv","国际米兰")
    build(all_ev,"calendar.ics")
