import requests
from bs4 import BeautifulSoup
import csv

teams = {
    "chengdu": "https://www.dongqiudi.com/team/50076899.html",
    "inter": "https://www.dongqiudi.com/team/50001042.html"
}

def fetch_schedule(name, url):
    print(f"正在抓取 {name} 赛程 ...")

    resp = requests.get(url, headers={"User-Agent": "Mozilla/5.0"})
    resp.encoding = "utf-8"
    soup = BeautifulSoup(resp.text, "html.parser")

    rows = soup.select("table tr")
    data = []

    for tr in rows[1:]:  # 跳过表头
        tds = tr.find_all("td")
        if len(tds) < 5:
            continue

        dt = tds[0].get_text(strip=True)
        competition = tds[1].get_text(strip=True)
        home = tds[2].get_text(strip=True)
        score = tds[3].get_text(strip=True)
        away = tds[4].get_text(strip=True)

        data.append([dt, competition, home, score, away])

    with open(f"data/{name}.csv", "w", encoding="utf-8", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["时间", "赛事", "主队", "比分或VS", "客队"])
        writer.writerows(data)

    print(f"{name} ✅ 赛程写入完成 → data/{name}.csv")


def main():
    for name, url in teams.items():
        fetch_schedule(name, url)

if __name__ == "__main__":
    main()
