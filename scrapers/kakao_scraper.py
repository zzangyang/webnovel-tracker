"""
카카오페이지 웹소설 랭킹 스크래퍼.

카카오페이지는 Next.js 기반이라 class명이 빌드마다 바뀌는 해시값
(예: jsx-2792908821)이라 그걸로는 못 잡음.
대신 각 작품 링크의 aria-label / data-t-obj 속성에 제목·순위·장르가
텍스트/JSON으로 들어있어서 그걸 파싱하는 방식으로 감.

aria-label 예시: "작품, {제목}, {태그}, 최신 회차 업데이트됨, {연령제한}, 랭킹 {N}위 {변동}, 버튼"
data-t-obj 예시: {"eventMeta": {"id": "...", "name": "{제목}", "series_id": "...",
                                "category": "웹소설", "subcategory": "{장르}"}, ...}

★ data-t-obj의 최상위 키("eventMeta")는 화면 캡처에서 줄바꿈 때문에 확실치 않음 —
  실행해보고 안 맞으면 print(raw)로 실제 키 확인해서 고칠 것.

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
        page.goto(RANKING_URL, wait_until="networkidle")

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

            # 1순위: data-t-obj JSON에서 제목/장르 파싱 시도
            obj_div = link.query_selector("[data-t-obj]")
            if obj_div:
                raw = obj_div.get_attribute("data-t-obj")
                try:
                    data = json.loads(raw)
                    meta = data.get("eventMeta", data)
                    title = meta.get("name")
                    genre = meta.get("subcategory")
                except Exception:
                    pass  # JSON 파싱 실패하면 아래 aria-label 파싱으로 대체

            # 2순위: aria-label 텍스트 파싱 (title 없을 때 + 순위는 항상 여기서)
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
