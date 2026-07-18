"""
네이버시리즈 웹소설 랭킹 스크래퍼.

장르별 랭킹 URL이 categoryCode 파라미터로 구분되어 있어서, 장르 목록을
순회하며 각각 긁고 장르를 라벨링함 (2026-07 실제 확인된 코드 매핑).

selector는 실제 DevTools 확인을 거쳐 채운 값:
  - 랭킹 항목: ul.comic_top_lst > li
  - 순위 숫자: .top_numb
  - 제목+링크: h3 a (href에 productNo=숫자)
  - 작가명: p.info 안 span.ellipsis 중 첫 번째로 추정
  - 독점 여부: 제목 텍스트 안에 "[독점]" 포함 여부

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

BASE_URL = "https://series.naver.com/novel/top100List.series?rankingTypeCode=DAILY&categoryCode={code}"

GENRE_CODES = {
    "201": "로맨스",
    "207": "로판",
    "202": "판타지",
    "208": "현판",
    "206": "무협",
    "209": "BL",
}

SELECTORS = {
    "item": "ul.comic_top_lst > li",
    "rank": ".top_numb",
    "title_link": "h3 a",
    "info": "p.info",
}

SPAN_AUTHOR_INDEX = 0  # p.info 안 span.ellipsis(무료정보/회차정보 제외) 중 몇 번째가 작가명인지


def _scrape_single_genre(page, code, genre_label):
    results = []
    url = BASE_URL.format(code=code)
    page.goto(url, wait_until="networkidle", timeout=60000)

    items = page.query_selector_all(SELECTORS["item"])
    for idx, item in enumerate(items, start=1):
        rank_el = item.query_selector(SELECTORS["rank"])
        title_el = item.query_selector(SELECTORS["title_link"])
        info_el = item.query_selector(SELECTORS["info"])

        if not title_el:
            continue

        href = title_el.get_attribute("href") or ""
        id_match = re.search(r"productNo=(\d+)", href)
        work_id = id_match.group(1) if id_match else href

        title_text = title_el.inner_text().strip()
        is_exclusive = "독점" in title_text

        rank_digits = re.sub(r"\D", "", rank_el.inner_text()) if rank_el else ""
        rank_num = int(rank_digits) if rank_digits else idx

        author = None
        if info_el:
            ellipsis_spans = info_el.query_selector_all("span.ellipsis")
            candidates = [
                s.inner_text().strip() for s in ellipsis_spans
                if "free_info" not in (s.get_attribute("class") or "")
                and "화" not in s.inner_text()
            ]
            if candidates and len(candidates) > SPAN_AUTHOR_INDEX:
                author = candidates[SPAN_AUTHOR_INDEX]

        results.append({
            "platform_work_id": work_id,
            "title": title_text,
            "author": author,
            "genre": genre_label,
            "url": urljoin(url, href),
            "is_exclusive": is_exclusive,
            "rank": rank_num,
            "views": None,
        })
    return results


def scrape_naver_ranking(headless=True):
    all_results = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for code, genre_label in GENRE_CODES.items():
            genre_results = _scrape_single_genre(page, code, genre_label)
            for r in genre_results:
                if r["platform_work_id"] in seen_ids:
                    continue
                seen_ids.add(r["platform_work_id"])
                all_results.append(r)

        browser.close()
    return all_results


if __name__ == "__main__":
    data = scrape_naver_ranking(headless=True)
    for d in data[:5]:
        print(d)
