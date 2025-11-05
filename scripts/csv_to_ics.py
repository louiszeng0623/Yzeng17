import pandas as pd
from ics import Calendar, Event
from datetime import datetime

def make_calendar(team_name, csv_file, output_file):
    df = pd.read_csv(csv_file)
    cal = Calendar()

    for _, row in df.iterrows():
        dt = datetime.strptime(row["日期时间"], "%m-%d %H:%M")
        event = Event()
        event.name = f"{team_name} | {row['对阵']}"
        event.begin = dt.replace(year=datetime.now().year)
        cal.events.add(event)

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(cal.serialize_iter())
    print(f"✅ {team_name} 日历生成成功 → {output_file}")

make_calendar("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
make_calendar("国际米兰", "data/inter.csv", "calendar_inter.ics")
