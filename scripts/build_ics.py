#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
构建 iCalendar 文件，合并成都蓉城和国际米兰的赛程。
时间默认视为 Asia/Shanghai 时区，比赛持续时间为 2 小时。
"""

import csv
import uuid
from datetime import datetime, timedelta

TIMEZONE_NAME = "Asia/Shanghai"
UTC_OFFSET = "+0800"

def load_events(csv_file: str, team_name: str):
    events = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt_local = datetime.strptime(f"{row['date']} {row['time_local']}", "%Y-%m-%d %H:%M")
            dt_end = dt_local + timedelta(hours=2)
            opponent = row["opponent"]
            home = row["home_away"] == "Home"
            competition = row["competition"]
            stadium = row.get("stadium", "")
            # 生成标题
            if team_name == "成都蓉城":
                summary = f"成都蓉城 vs {opponent}" if home else f"{opponent} vs 成都蓉城"
            else:
                summary = f"Inter Milan vs {opponent}" if home else f"{opponent} vs Inter Milan"
            description = f"{competition} | {'主场' if home else '客场'}比赛"
            if stadium:
                description += f" | {stadium}"
            uid = uuid.uuid4().hex
            events.append({
                "uid": uid,
                "summary": summary,
                "description": description,
                "start": dt_local,
                "end": dt_end,
                "location": stadium or "",
            })
    return events

def format_dt(dt: datetime):
    return dt.strftime(f"%Y%m%dT%H%M%S{UTC_OFFSET}")

def build_calendar(events, outfile="calendar.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{TIMEZONE_NAME}",
        "PRODID:-//football-fixtures-2025//EN"
    ]
    for ev in events:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{ev['uid']}@football-fixtures",
            f"DTSTAMP:{format_dt(datetime.utcnow())}",
            f"DTSTART;TZID={TIMEZONE_NAME}:{format_dt(ev['start'])}",
            f"DTEND;TZID={TIMEZONE_NAME}:{format_dt(ev['end'])}",
            f"SUMMARY:{ev['summary']}",
            f"DESCRIPTION:{ev['description']}",
            f"LOCATION:{ev['location']}",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"Wrote {outfile} with {len(events)} events.")

if __name__ == "__main__":
    events = []
    events += load_events("data/chengdu.csv", "成都蓉城")
    events += load_events("data/inter.csv", "国际米兰")
    build_calendar(events, "calendar.ics")
