import json
from datetime import datetime

def make_ics(input_file, output_file):
    with open(input_file, "r", encoding="utf-8") as f:
        matches = json.load(f)

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//LouisZeng Calendar//CN"
    ]

    for match in matches:
        dt = datetime.strptime(match["date"], "%Y-%m-%d %H:%M")
        dt_str = dt.strftime("%Y%m%dT%H%M00")

        title = f"{match['league']} {match['home']} vs {match['away']}"

        lines += [
            "BEGIN:VEVENT",
            f"DTSTART;TZID=Asia/Shanghai:{dt_str}",
            f"SUMMARY:{title}",
            "END:VEVENT"
        ]

    lines.append("END:VCALENDAR")

    with open(output_file, "w", encoding="utf-8") as f:
        f.write("\n".join(lines))

    print(f"✅ 已生成日历 → {output_file}")

make_ics("data/chengdu.json", "calendar_chengdu.ics")
make_ics("data/inter.json", "calendar_inter.ics")
