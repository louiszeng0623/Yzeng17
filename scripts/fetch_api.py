import requests
import pandas as pd
from bs4 import BeautifulSoup

def fetch(team_name, url, output_csv):
    print(f"正在抓取 {team_name} 赛程...")

    headers = {
        "User-Agent": "Mozilla/5.0",
        "Referer": url
    }
    r = requests.get(url, headers=headers, timeout=10)
    r.encoding = 'utf-8'
    soup = BeautifulSoup(r.text, "html.parser")

    match_list = soup.find_all("div", class_="match-list-item")
    if not match_list:
        print(f"❌ 未找到赛程数据，请检查网址: {url}")
        return False

    rows = []
    for item in match_list:
        date = item.find("div", class_="time").get_text(strip=True)
        comp = item.find("div", class_="match-event-name").get_text(strip=True)
        home = item.find("div", class_="team-home").get_text(strip=True)
        score = item.find("div", class_="score").get_text(strip=True)
        away = item.find("div", class_="team-away").get_text(strip=True)

        rows.append([date, comp, home, score, away])

    df = pd.DataFrame(rows, columns=["日期时间", "赛事", "主队", "比分", "客队"])
    df.to_csv(output_csv, index=False, encoding="utf-8-sig")

    print(f"✅ {team_name} 数据已成功写入 → {output_csv}")
    return True


fetch("成都蓉城", "https://www.dongqiudi.com/team/50076899.html", "data/chengdu.csv")
fetch("国际米兰", "https://www.dongqiudi.com/team/50001042.html", "data/inter.csv")
