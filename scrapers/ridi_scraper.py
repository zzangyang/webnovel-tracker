"""
리디북스 웹소설 랭킹 스크래퍼.

리디북스도 카카오페이지처럼 class명이 빌드마다 바뀌는 해시값
(예: fig-1g6ej4g)이라 그걸 selector로 못 씀.

대신 안정적인 두 가지를 이용:
  1. 작품 링크: href가 "/books/{숫자ID}"로 시작
  2. 작가 링크: href가 "/author/{숫자ID}"로 시작하고, 텍스트가 곧 작가명

제목은 여전히 해시 class라 확실한 selector가 없어서,
각 항목(li) 전체 텍스트를 줄 단위로 쪼개 첫 줄(또는 숫자면 둘째 줄)을
제목으로 추정하는 방식을 씀 — 이 부분만 페이지 개편에 약함.

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
import re
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

RANKING_URL = "https://ridibooks.com/bestsellers/serial"


def scrape_ridi_ranking(headless=True):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()

        # networkidle 대신 domcontentloaded: 광고/분석 스크립트가 계속 돌아서
        # networkidle은 영영 안 끝날 수 있음. 대신 실제 콘텐츠(책 링크)가
        # 뜰 때까지만 명시적으로 기다림.
        page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_selector('a[href*="/books/"]', timeout=15000)
        except Exception:
            print("[ridi] 랭킹 리스트 로딩 자체가 안 됨 — 페이지 구조가 바뀌었거나 접근 차단 가능성")
            browser.close()
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
                continue  # 썸네일 링크 + 텍스트 링크 중복 방지
            seen_ids.add(work_id)

            li = link.evaluate_handle("el => el.closest('li')")
            li_el = li.as_element()
            if not li_el:
                continue

            # 작가명: li 안에서 /author/ 링크 텍스트 그대로
            author_el = li_el.query_selector('a[href^="/author/"]')
            author = author_el.inner_text().strip() if author_el else None

            # 제목: li 전체 텍스트를 줄 단위로 쪼개서 추정
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
                "genre": None,  # 이 목록 페이지에서 확실한 장르 위치 못 찾음
                "url": urljoin(RANKING_URL, href),
                "is_exclusive": "독점" in title,
                "rank": len(seen_ids),
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_ridi_ranking(headless=True)
    for d in data[:5]:
        print(d)
