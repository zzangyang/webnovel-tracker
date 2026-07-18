"""
네이버시리즈 웹소설 랭킹 스크래퍼.

selector는 실제 DevTools 확인을 거쳐 채운 값 (2026-07 기준).
사이트 개편되면 다시 확인 필요.

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

RANKING_URL = "https://series.naver.com/novel/top100List.series"

SELECTORS = {
    "item": "ul.comic_top_lst > li",
    "rank": ".top_numb",
    "title_link": "h3 a",
}


def scrape_naver_ranking(headless=True):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(RANKING_URL, wait_until="networkidle")

        items = page.query_selector_all(SELECTORS["item"])
        for idx, item in enumerate(items, start=1):
            rank_el = item.query_selector(SELECTORS["rank"])
            title_el = item.query_selector(SELECTORS["title_link"])

            if not title_el:
                continue

            href = title_el.get_attribute("href") or ""
            id_match = re.search(r"productNo=(\d+)", href)
            work_id = id_match.group(1) if id_match else href

            title_text = title_el.inner_text().strip()
            is_exclusive = "독점" in title_text

            rank_digits = re.sub(r"\D", "", rank_el.inner_text()) if rank_el else ""
            rank_num = int(rank_digits) if rank_digits else idx

            results.append({
                "platform_work_id": work_id,
                "title": title_text,
                "author": None,
                "genre": None,
                "url": urljoin(RANKING_URL, href),
                "is_exclusive": is_exclusive,
                "rank": rank_num,
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_naver_ranking(headless=True)
    for d in data[:5]:
        print(d)
