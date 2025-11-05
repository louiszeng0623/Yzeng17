import requests
import pandas as pd
from bs4 import BeautifulSoup

def fetch_schedule(team_name, url, output_csv):
    print(f"正在抓取 {team_name} 赛程...")

    r = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    r.encoding = "utf-8"
    soup = BeautifulSoup(r.text, "html.parser")

    table = soup.find("table")
    if table is None:
        print(f"❌ 未找到赛程表，请检查网址: {url}")
        return

    rows = []
    for tr in table.find_all("tr")[1:]:
        tds = [td.get_text(strip=True) for td in tr.find_all("td")]
        if len(tds) >= 7:
            date, time, comp, home, score, away, _round = tds[0], tds[1], tds[2], tds[3], tds[4], tds[5], tds[6]

            # 仅保留 VS 格式（便于日历显示）
            match = f"{home} vs {away}" if "VS" in score.upper() else f"{home} {score} {away}"

            rows.append([f"{date} {time}", comp, home, away, match])

    df = pd.DataFrame(rows, columns=["日期时间", "赛事", "主队", "客队", "对阵"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ {team_name} 赛程已保存至 {output_csv}")

# 成都蓉城
fetch_schedule(
    "成都蓉城",
    "https://www.dongqiudi.com/team/50076899.html",
    "data/chengdu.csv"
)

# 国际米兰
fetch_schedule(
    "国际米兰",
    "https://www.dongqiudi.com/team/50001042.html",
    "data/inter.csv"
)
