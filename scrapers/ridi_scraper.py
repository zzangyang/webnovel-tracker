"""
리디북스 웹소설 랭킹 스크래퍼.

장르별 베스트 URL이 따로 있어서(URL 슬러그 자체가 장르명), 4개를 순회하며
각각 긁고 장르를 라벨링함.

작품 링크: href가 "/books/{숫자ID}"로 시작
작가 링크: href가 "/author/{숫자ID}"로 시작하고, 텍스트가 곧 작가명
제목: class명이 빌드마다 바뀌는 해시값이라, li 전체 텍스트를 줄 단위로 쪼개서 추정
      (첫 줄이 숫자면 그다음 줄을 제목으로 — 페이지 개편에 약한 부분)

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

GENRE_URLS = {
    "로맨스판타지": "https://ridibooks.com/bestsellers/romance_fantasy_serial",
    "로맨스": "https://ridibooks.com/bestsellers/romance_serial",
    "판타지": "https://ridibooks.com/bestsellers/fantasy_serial",
    "BL": "https://ridibooks.com/bestsellers/bl-webnovel",
}


def _scrape_single_genre(page, url, genre_label):
    results = []
    page.goto(url, wait_until="domcontentloaded", timeout=60000)
    try:
        page.wait_for_selector('a[href*="/books/"]', timeout=15000)
    except Exception:
        print(f"[ridi/{genre_label}] 랭킹 리스트 로딩 실패")
        return results

    book_links = page.query_selector_all('a[href*="/books/"]')
    seen_ids = set()

    for link in book_links:
        href = link.get_attribute("href") or ""
        id_match = re.search(r"/books/(\d+)", href)
        if not id_match:
            continue
        work_id = id_match.group(1)

        if work_id in seen_ids:
            continue
        seen_ids.add(work_id)

        li = link.evaluate_handle("el => el.closest('li')")
        li_el = li.as_element()
        if not li_el:
            continue

        author_el = li_el.query_selector('a[href^="/author/"]')
        author = author_el.inner_text().strip() if author_el else None

        full_text = li_el.inner_text().strip()
        lines = [l.strip() for l in full_text.split("\n") if l.strip()]
        if not lines:
            continue

        title_idx = 1 if lines[0].isdigit() else 0
        title = lines[title_idx] if len(lines) > title_idx else None
        if not title:
            continue

        results.append({
            "platform_work_id": work_id,
            "title": title,
            "author": author,
            "genre": genre_label,
            "url": urljoin(url, href),
            "is_exclusive": "독점" in title,
            "rank": len(seen_ids),
            "views": None,
        })
    return results


def scrape_ridi_ranking(headless=True):
    all_results = []
    seen_ids = set()

    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        for genre_label, url in GENRE_URLS.items():
            genre_results = _scrape_single_genre(page, url, genre_label)
            for r in genre_results:
                if r["platform_work_id"] in seen_ids:
                    continue
                seen_ids.add(r["platform_work_id"])
                all_results.append(r)

        browser.close()
    return all_results


if __name__ == "__main__":
    data = scrape_ridi_ranking(headless=True)
    for d in data[:5]:
        print(d)
