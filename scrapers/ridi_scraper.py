"""
리디북스 웹소설 랭킹 스크래퍼.

리디북스도 카카오페이지처럼 class명이 빌드마다 바뀌는 해시값
(예: fig-1g6ej4g)이라 그걸 selector로 못 씀.
대신 각 작품 링크가 "/books/{숫자ID}?..." 패턴을 갖는다는 점,
그리고 리스트 항목(li) 전체의 텍스트가
  제목
  작가 · 출판사 · 장르
  총 N화
  ★ 별점(리뷰수)
  ...설명...
순서로 나온다는 점을 이용해서 텍스트 파싱으로 제목/작가/장르를 뽑음.

★ 이 방식은 페이지 레이아웃이 조금만 바뀌어도 깨지기 쉬움 —
  실행해보고 title/author가 이상하게 나오면 li.inner_text()를 print해서
  실제 줄 구성 순서를 다시 확인할 것.

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
        page.goto(RANKING_URL, wait_until="networkidle")

        # /books/숫자 로 시작하는 링크를 가진 li를 랭킹 항목으로 간주
        book_links = page.query_selector_all('a[href*="/books/"]')
        seen_ids = set()

        for idx, link in enumerate(book_links, start=1):
            href = link.get_attribute("href") or ""
            id_match = re.search(r"/books/(\d+)", href)
            if not id_match:
                continue
            work_id = id_match.group(1)

            if work_id in seen_ids:
                continue  # 썸네일 링크 + 텍스트 링크로 중복 잡히는 것 방지
            seen_ids.add(work_id)

            # 링크를 감싸는 li까지 거슬러 올라가서 전체 텍스트 확보
            li = link.evaluate_handle("el => el.closest('li')")
            li_el = li.as_element()
            if not li_el:
                continue

            full_text = li_el.inner_text().strip()
            lines = [l.strip() for l in full_text.split("\n") if l.strip()]
            if not lines:
                continue

            # 첫 줄이 순위 숫자만 있는 경우(예: "1") 건너뛰고 다음 줄을 제목으로
            title_idx = 0
            if lines[0].isdigit():
                title_idx = 1
            title = lines[title_idx] if len(lines) > title_idx else None
            meta_line = lines[title_idx + 1] if len(lines) > title_idx + 1 else ""

            if not title:
                continue

            author = None
            genre = None
            if "·" in meta_line:
                meta_parts = [m.strip() for m in meta_line.split("·")]
                author = meta_parts[0] if len(meta_parts) > 0 else None
                genre = meta_parts[-1] if len(meta_parts) > 1 else None

            results.append({
                "platform_work_id": work_id,
                "title": title,
                "author": author,
                "genre": genre,
                "url": urljoin(RANKING_URL, href),
                "is_exclusive": "독점" in title,
                "rank": len(seen_ids),  # 등장 순서 = 랭킹 순서로 가정
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_ridi_ranking(headless=True)
    for d in data[:5]:
        print(d)
