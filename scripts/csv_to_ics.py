import pandas as pd
from ics import Calendar, Event
from datetime import datetime

def make_calendar(label, input_file, output_file):
    try:
        df = pd.read_csv(input_file)
    except:
        print(f"⚠ 文件缺失：{input_file}")
        return None

    calendar = Calendar()

    for _, row in df.iterrows():
        try:
            dt = datetime.strptime(row["日期时间"], "%m-%d %H:%M")
            dt = dt.replace(year=datetime.now().year)
        except:
            continue

        if row["比分"] in ["VS", "vs", "", None]:
            title = f"{row['主队']} vs {row['客队']}（{row['赛事']}） @ {row['球场']}"
        else:
            title = f"{row['主队']} {row['比分']} {row['客队']}（{row['赛事']}） @ {row['球场']}"

        event = Event()
        event.name = title
        event.begin = dt
        calendar.events.add(event)

    calendar.extra.append(("X-WR-CALNAME", "Louis_Zeng"))
    calendar.extra.append(("X-WR-TIMEZONE", "Asia/Shanghai"))

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(calendar)

    print(f"✅ {label} 完成 → {output_file}")
    return calendar


c1 = make_calendar("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
c2 = make_calendar("国际米兰", "data/inter.csv", "calendar_inter.ics")

final_cal = Calendar()
for c in (c1, c2):
    if c:
        final_cal.events.update(c.events)

final_cal.extra.append(("X-WR-CALNAME", "Louis_Zeng"))
with open("calendar.ics", "w", encoding="utf-8") as f:
    f.writelines(final_cal)

print("🎉 完成！总日历 → calendar.ics")
