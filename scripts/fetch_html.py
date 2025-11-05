from playwright.sync_api import sync_playwright
import pandas as pd

TEAMS = {
    "chengdu": "https://www.dongqiudi.com/team/50076899.html",
    "inter": "https://www.dongqiudi.com/team/50001042.html",
}

def scrape_schedule(team, url, page):
    page.goto(url)
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

        data.append([date, match, home, score, away])

    df = pd.DataFrame(data, columns=["日期时间", "赛事", "主队", "比分", "客队"])
    df.to_csv(f"data/{team}.csv", index=False)
    print(f"✅ {team}.csv 更新完成，记录数量：{len(df)}")

with sync_playwright() as p:
    browser = p.chromium.launch(headless=True)
    page = browser.new_page()
    for key, url in TEAMS.items():
        scrape_schedule(key, url, page)
    browser.close()
