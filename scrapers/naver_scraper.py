"""
네이버시리즈 웹소설 랭킹 스크래퍼.

selector는 실제 DevTools 확인을 거쳐 채운 값 (2026-07 기준).
사이트 개편되면 다시 확인 필요.

작가명은 p.info 안의 span.ellipsis 중 첫 번째 항목으로 추정 — 별점 다음,
"총N화/완결여부" 앞에 오는 자리. 100% 확신은 아니라서 실행 후
author 값이 이상하면 (예: 장르나 날짜가 들어옴) SPAN_AUTHOR_INDEX 값을
0, 1 등으로 바꿔가며 확인할 것.

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
    "info": "p.info",
}

SPAN_AUTHOR_INDEX = 0  # p.info 안 span.ellipsis(무료정보 제외) 중 몇 번째가 작가명인지


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

            # 작가명 추출: p.info 안 "free_info"가 아닌 ellipsis span들 중 첫 번째
            author = None
            if info_el:
                ellipsis_spans = info_el.query_selector_all("span.ellipsis")
                candidates = [
                    s.inner_text().strip() for s in ellipsis_spans
                    if "free_info" not in (s.get_attribute("class") or "")
                    and "화" not in s.inner_text()  # "총N화/완결" 같은 회차정보 제외
                ]
                if candidates and len(candidates) > SPAN_AUTHOR_INDEX:
                    author = candidates[SPAN_AUTHOR_INDEX]

            results.append({
                "platform_work_id": work_id,
                "title": title_text,
                "author": author,
                "genre": None,   # 이 목록 페이지에는 장르 표시가 따로 없어 보임
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
