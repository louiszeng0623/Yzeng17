#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, uuid
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
            opponent = row['opponent']
            home = row['home_away'] == 'Home'
            comp = row['competition']
            stadium = row.get('stadium', '')
            summary = f"{team_name} vs {opponent}" if home else f"{opponent} vs {team_name}"
            desc = f"{comp} | {'主场' if home else '客场'}比赛"
            if stadium: desc += f" | {stadium}"
            uid = uuid.uuid4().hex
            events.append({"uid":uid,"summary":summary,"description":desc,
                           "start":dt_local,"end":dt_end,"location":stadium})
    return events

def format_dt(dt:datetime):
    return dt.strftime(f"%Y%m%dT%H%M%S{UTC_OFFSET}")

def build_calendar(events, outfile="calendar.ics"):
    lines = ["BEGIN:VCALENDAR","VERSION:2.0","CALSCALE:GREGORIAN",
             f"X-WR-TIMEZONE:{TIMEZONE_NAME}","PRODID:-//football-fixtures//CN"]
    for e in events:
        lines.extend([
            "BEGIN:VEVENT",
            f"UID:{e['uid']}@fixtures",
            f"DTSTAMP:{format_dt(datetime.utcnow())}",
            f"DTSTART;TZID={TIMEZONE_NAME}:{format_dt(e['start'])}",
            f"DTEND;TZID={TIMEZONE_NAME}:{format_dt(e['end'])}",
            f"SUMMARY:{e['summary']}",
            f"DESCRIPTION:{e['description']}",
            f"LOCATION:{e['location']}",
            "END:VEVENT"
        ])
    lines.append("END:VCALENDAR")
    with open(outfile,'w',encoding='utf-8') as f:f.write("\n".join(lines))
    print(f"Wrote {outfile} with {len(events)} events.")

if __name__=="__main__":
    ev=[]
    ev+=load_events('data/chengdu.csv','成都蓉城')
    ev+=load_events('data/inter.csv','国际米兰')
    build_calendar(ev,'calendar.ics')
