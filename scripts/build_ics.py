#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, uuid
from datetime import datetime, timedelta

TIMEZONE_NAME = "Asia/Shanghai"
UTC_OFFSET = "+0800"

FIELDS = ["date","time_local","opponent","home_away","competition","stadium","status"]

def load_events(csv_file: str, team_name: str):
    events = []
    try:
        with open(csv_file, newline='', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if not row.get("date"): 
                    continue
                try:
                    dt_local = datetime.strptime(f"{row['date']} {row.get('time_local','20:00')}", "%Y-%m-%d %H:%M")
                except Exception:
                    # 没时间就默认 20:00
                    dt_local = datetime.strptime(f"{row['date']} 20:00", "%Y-%m-%d %H:%M")
                dt_end = dt_local + timedelta(hours=2)

                opponent = row.get('opponent',"")
                ha = (row.get('home_away') or "").lower()
                home = True if ha == 'home' else False if ha == 'away' else None
                comp = row.get('competition',"")
                stadium = row.get('stadium',"")
                status = row.get('status',"").strip()

                if home is True:
                    summary = f"{team_name} vs {opponent}"
                elif home is False:
                    summary = f"{opponent} vs {team_name}"
                else:
                    summary = f"{team_name} - {opponent}"

                desc_parts = []
                if comp: desc_parts.append(comp)
                if home is True: desc_parts.append("主场")
                elif home is False: desc_parts.append("客场")
                if status: desc_parts.append(status)
                description = " | ".join(desc_parts)

                uid = uuid.uuid4().hex
                events.append({
                    "uid": uid,
                    "summary": summary,
                    "description": description,
                    "start": dt_local,
                    "end": dt_end,
                    "location": stadium
                })
    except FileNotFoundError:
        pass
    return events

def format_dt(dt:datetime):
    # 直接写本地偏移，保持 iPhone 显示为北京时间
    return dt.strftime(f"%Y%m%dT%H%M%S{UTC_OFFSET}")

def build_calendar(events, outfile="calendar.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{TIMEZONE_NAME}",
        "PRODID:-//football-fixtures//CN"
    ]
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
    with open(outfile,'w',encoding='utf-8') as f:
        f.write("\n".join(lines))
    print(f"🧾 写出 {outfile}，事件数：{len(events)}")

if __name__=="__main__":
    ev=[]
    ev+=load_events('data/chengdu.csv','成都蓉城')
    ev+=load_events('data/inter.csv','国际米兰')
    ev.sort(key=lambda x: (x["start"], x["summary"]))
    build_calendar(ev,'calendar.ics')
