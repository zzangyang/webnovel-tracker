"""
네이버시리즈 웹소설 랭킹 스크래퍼.

★ 중요: selector는 placeholder임. 실제 사용 전에 반드시 아래 작업 필요:
  1. 브라우저에서 네이버시리즈 웹소설 랭킹 페이지 열기
  2. F12 (개발자도구) > Elements 탭에서 랭킹 리스트의 실제 class/구조 확인
  3. 아래 SELECTORS 딕셔너리 값 교체
  4. 사이트 개편되면 이 파일도 다시 손봐야 함 (크롤러의 숙명)

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
from playwright.sync_api import sync_playwright

# TODO: 실제 랭킹 URL로 교체 (예: 장르별 베스트 랭킹, 급상승 랭킹 등)
RANKING_URL = "https://series.naver.com/novel/top100List.series"

# TODO: 실제 DOM 구조에 맞게 selector 교체
SELECTORS = {
    "item": ".rankingList li",       # 랭킹 리스트의 개별 항목
    "title": ".title",
    "author": ".author",
    "genre": ".genre",
    "link": "a",                     # href에서 작품 ID 추출
    "exclusive_badge": ".badge_exclusive",
}


def scrape_naver_ranking(headless=True):
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
            # TODO: 실제 URL 패턴에 맞게 ID 추출 로직 교체
            # 예: /novel/list?novelId=804489 -> "804489"
            work_id = href.split("=")[-1] if "=" in href else href

            results.append({
                "platform_work_id": work_id,
                "title": title_el.inner_text().strip(),
                "author": author_el.inner_text().strip() if author_el else None,
                "genre": genre_el.inner_text().strip() if genre_el else None,
                "url": href if href.startswith("http") else f"https://series.naver.com{href}",
                "is_exclusive": exclusive_el is not None,
                "rank": rank,
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_naver_ranking(headless=True)
    for d in data[:5]:
        print(d)
