"""
카카오페이지 웹소설 랭킹 스크래퍼.
★ naver_scraper.py와 동일하게 selector는 placeholder — F12로 직접 확인 후 교체할 것.
"""
from playwright.sync_api import sync_playwright

# TODO: 실제 랭킹 URL로 교체 (장르 탭별로 URL이 다를 수 있음, 그 경우 리스트로 관리)
RANKING_URL = "https://page.kakao.com/menu/10011/screen/94"

SELECTORS = {
    "item": "[class*='rank'] li",
    "title": "[class*='title']",
    "author": "[class*='author']",
    "genre": "[class*='genre']",
    "link": "a",
    "exclusive_badge": "[class*='exclusive']",
}


def scrape_kakao_ranking(headless=True):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(RANKING_URL, wait_until="networkidle")

        items = page.query_selector_all(SELECTORS["item"])
        for rank, item in enumerate(items, start=1):
            title_el = item.query_selector(SELECTORS["title"])
            author_el = item.query_selector(SELECTORS["author"])
            genre_el = item.query_selector(SELECTORS["genre"])
            link_el = item.query_selector(SELECTORS["link"])
            exclusive_el = item.query_selector(SELECTORS["exclusive_badge"])

            if not title_el or not link_el:
                continue

            href = link_el.get_attribute("href") or ""
            # TODO: 카카오페이지 URL 패턴에 맞게 작품 ID 추출 로직 교체
            work_id = href.rstrip("/").split("/")[-1]

            results.append({
                "platform_work_id": work_id,
                "title": title_el.inner_text().strip(),
                "author": author_el.inner_text().strip() if author_el else None,
                "genre": genre_el.inner_text().strip() if genre_el else None,
                "url": href if href.startswith("http") else f"https://page.kakao.com{href}",
                "is_exclusive": exclusive_el is not None,
                "rank": rank,
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_kakao_ranking(headless=True)
    for d in data[:5]:
        print(d)
