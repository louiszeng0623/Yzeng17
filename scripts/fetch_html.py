from playwright.sync_api import sync_playwright
import pandas as pd

TEAMS = {
    "chengdu": {
        "url": "https://www.dongqiudi.com/team/50076899.html",
        "home": "五粮液文化体育中心"
    },
    "inter": {
        "url": "https://www.dongqiudi.com/team/50001042.html",
        "home": "圣西罗球场"
    },
}

def scrape(team_key, config, page):
    page.goto(config["url"])
    page.click("text=赛程")

    rows = page.locator("table tr").all()
    data = []

    for row in rows[1:]:
        cells = row.locator("td").all()
        if len(cells) < 5:
            continue

        date = cells[0].inner_text().strip()
        match = cells[1].inner_text().strip()
        home = cells[2].inner_text().strip()
        score = cells[3].inner_text().strip()
        away = cells[4].inner_text().strip()

        # 判断是否为本队主场
        stadium = config["home"] if team_key in home else f"{away} 主场"

        data.append([date, match, home, score, away, stadium])

    df = pd.DataFrame(data, columns=["日期时间", "赛事", "主队", "比分", "客队", "球场"])
    df.to_csv(f"data/{team_key}.csv", index=False)
    print(f"✅ {team_key}.csv 更新完成：{len(df)} 场")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for team_key, config in TEAMS.items():
        scrape(team_key, config, page)
    browser.close()
