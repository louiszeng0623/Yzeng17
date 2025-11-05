#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import csv, uuid
from datetime import datetime, timedelta

TIMEZONE_NAME = "Asia/Shanghai"
UTC_OFFSET = "+0800"  # ics 中写 +0800

def load_events(csv_file: str, team_name: str):
    events = []
    with open(csv_file, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            start = datetime.strptime(f"{row['date']} {row['time_local']}", "%Y-%m-%d %H:%M")
            end = start + timedelta(hours=2)
            opponent = row['opponent']
            home = row['home_away'] == 'Home'
            comp = row.get('competition', '')
            stadium = row.get('stadium', '')
            status = row.get('status', '').strip()

            summary = f"{team_name} vs {opponent}" if home else f"{opponent} vs {team_name}"
            if status:
                summary += f" {status}"
            desc = f"{comp} | {'主场' if home else '客场'}"
            if stadium:
                desc += f" | {stadium}"
            if status:
                desc += f" | 状态:{status}"

            events.append({
                "uid": uuid.uuid4().hex,
                "summary": summary,
                "description": desc,
                "start": start,
                "end": end,
                "location": stadium,
            })
    return events

def dtfmt(dt: datetime) -> str:
    return dt.strftime(f"%Y%m%dT%H%M%S{UTC_OFFSET}")

def build_calendar(events, outfile="calendar.ics"):
    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "CALSCALE:GREGORIAN",
        f"X-WR-TIMEZONE:{TIMEZONE_NAME}",
        "PRODID:-//auto-football-calendar//CN",
    ]
    now = datetime.utcnow()
    for e in events:
        lines += [
            "BEGIN:VEVENT",
            f"UID:{e['uid']}@fixtures",
            f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
            f"DTSTART;TZID={TIMEZONE_NAME}:{dtfmt(e['start'])}",
            f"DTEND;TZID={TIMEZONE_NAME}:{dtfmt(e['end'])}",
            f"SUMMARY:{e['summary']}",
            f"DESCRIPTION:{e['description']}",
            f"LOCATION:{e['location']}",
            "END:VEVENT",
        ]
    lines.append("END:VCALENDAR")
    with open(outfile, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"🧱 Wrote {outfile} with {len(events)} events.")

if __name__ == "__main__":
    ev = []
    ev += load_events("data/chengdu.csv", "成都蓉城")
    ev += load_events("data/inter.csv",   "国际米兰")
    # 开球先后排序（可选）
    ev.sort(key=lambda e: (e["start"], e["summary"]))
    build_calendar(ev, "calendar.ics")
