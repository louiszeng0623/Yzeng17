import pandas as pd
from ics import Calendar, Event
from datetime import datetime

def make_calendar(team_name, input_file, output_file):
    try:
        df = pd.read_csv(input_file)
    except:
        print(f"⚠ 无法读取 {input_file}")
        return None

    c = Calendar()

    for _, row in df.iterrows():
        # 日期处理 —— 默认补全年份
        try:
            dt = datetime.strptime(row["日期时间"], "%m-%d %H:%M")
            dt = dt.replace(year=datetime.now().year)
        except:
            continue

        event = Event()

        # 如果比分未知，则用 vs 显示
        if row["比分"] in ["VS", "vs", "", None]:
            title = f"{row['主队']} vs {row['客队']}（{row['赛事']}）"
        else:
            title = f"{row['主队']} {row['比分']} {row['客队']}（{row['赛事']}）"

        event.name = title
        event.begin = dt
        c.events.add(event)

    with open(output_file, "w", encoding="utf-8") as f:
        f.writelines(c)

    print(f"✅ {team_name} 日历生成完成 → {output_file}")
    return c


# 生成两个球队 ICS
chengdu = make_calendar("成都蓉城", "data/chengdu.csv", "calendar_chengdu.ics")
inter = make_calendar("国际米兰", "data/inter.csv", "calendar_inter.ics")

# 合并
calendar_all = Calendar()
for cal in [chengdu, inter]:
    if cal is not None:
        calendar_all.events.update(cal.events)

with open("calendar.ics", "w", encoding="utf-8") as f:
    f.writelines(calendar_all)

print("🎉 已合并生成总日历 → calendar.ics")
