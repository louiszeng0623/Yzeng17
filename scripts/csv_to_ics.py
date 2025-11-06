import csv
from ics import Calendar, Event
from datetime import datetime

def make_ics(name):
    c = Calendar()

    with open(f"data/{name}.csv", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            dt = row["时间"].replace(" ", "T") + ":00"
            try:
                start = datetime.fromisoformat(dt)
            except:
                continue

            title = f"{row['主队']} vs {row['客队']} ({row['赛事']})"
            e = Event(name=title, begin=start)
            c.events.add(e)

    with open(f"calendar_{name}.ics", "w", encoding="utf-8") as f:
        f.writelines(c)

    print(f"✅ calendar_{name}.ics 已生成")


def main():
    make_ics("chengdu")
    make_ics("inter")

if __name__ == "__main__":
    main()
