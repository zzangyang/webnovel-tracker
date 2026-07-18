"""
주 1회 실행되는 메인 스크립트.
3개 플랫폼 크롤링 -> DB 저장 -> 급상승/신작 리포트 생성까지 한 번에.

로컬 실행:
    python main.py

GitHub Actions에서는 workflow 파일이 이 스크립트를 그대로 호출함.
"""
from datetime import date
from scrapers.db_utils import init_db, save_ranking_batch
from scrapers.naver_scraper import scrape_naver_ranking
from scrapers.kakao_scraper import scrape_kakao_ranking
from scrapers.ridi_scraper import scrape_ridi_ranking
from reports.generate_report import generate_weekly_report


def run():
    init_db()
    today = date.today().isoformat()

    scrapers = {
        "naver": scrape_naver_ranking,
        "kakao": scrape_kakao_ranking,
        "ridi": scrape_ridi_ranking,
    }

    for platform, fn in scrapers.items():
        try:
            data = fn(headless=True)
            if data:
                save_ranking_batch(platform, data, snapshot_date=today)
            else:
                print(f"[{platform}] 수집 결과 0건 — selector가 안 맞을 가능성 높음. F12로 확인 필요.")
        except Exception as e:
            print(f"[{platform}] 크롤링 실패: {e}")

    generate_weekly_report(snapshot_date=today)


if __name__ == "__main__":
    run()
