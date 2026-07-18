"""
카카오페이지 웹소설 랭킹 스크래퍼.

장르 탭 URL이 따로 없어서(클릭해도 주소 안 바뀜, 클라이언트 필터링 방식),
대신 각 항목의 data-t-obj JSON 안에 이미 장르(subcategory)가 박혀있는 걸
활용함 — 2026-07 실제 캡처로 "eventMeta" 키, "subcategory" 필드 확인됨.

aria-label 예시: "작품, {제목}, {태그}, 최신 회차 업데이트됨, {연령제한}, 랭킹 {N}위 {변동}, 버튼"
data-t-obj 예시: {"eventMeta": {"id": "...", "name": "{제목}", "series_id": "...",
                                "category": "웹소설", "subcategory": "{장르}"}, ...}

실행 전 설치:
  pip install playwright
  playwright install chromium
"""
import re
import json
from urllib.parse import urljoin
from playwright.sync_api import sync_playwright

RANKING_URL = "https://page.kakao.com/menu/10011/screen/94"


def scrape_kakao_ranking(headless=True):
    results = []
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=headless)
        page = browser.new_page()
        page.goto(RANKING_URL, wait_until="domcontentloaded", timeout=60000)
        try:
            page.wait_for_selector('a[href^="/content/"]', timeout=15000)
        except Exception:
            print("[kakao] 랭킹 리스트 로딩 실패 — 페이지 구조 변경 가능성")
            browser.close()
            return results

        links = page.query_selector_all('a[href^="/content/"]')
        for idx, link in enumerate(links, start=1):
            href = link.get_attribute("href") or ""
            id_match = re.search(r"/content/(\d+)", href)
            work_id = id_match.group(1) if id_match else href

            labeled_div = link.query_selector("[aria-label]")
            aria_label = labeled_div.get_attribute("aria-label") if labeled_div else None

            title = None
            genre = None
            rank_num = idx

            obj_div = link.query_selector("[data-t-obj]")
            if obj_div:
                raw = obj_div.get_attribute("data-t-obj")
                try:
                    data = json.loads(raw)
                    meta = data.get("eventMeta", data)
                    title = meta.get("name")
                    genre = meta.get("subcategory")
                except Exception:
                    pass

            if aria_label:
                parts = [p.strip() for p in aria_label.split(",")]
                if not title and len(parts) > 1:
                    title = parts[1]
                rank_match = re.search(r"랭킹\s*(\d+)위", aria_label)
                if rank_match:
                    rank_num = int(rank_match.group(1))

            if not title:
                continue

            results.append({
                "platform_work_id": work_id,
                "title": title,
                "author": None,
                "genre": genre,
                "url": urljoin(RANKING_URL, href),
                "is_exclusive": "독점" in title,
                "rank": rank_num,
                "views": None,
            })

        browser.close()
    return results


if __name__ == "__main__":
    data = scrape_kakao_ranking(headless=True)
    for d in data[:5]:
        print(d)
