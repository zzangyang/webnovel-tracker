"""
db/tracker.db에 쌓인 크롤링 데이터를 대시보드(docs/index.html)가 읽을 수 있는
JSON 형태로 뽑아서 docs/data.json으로 저장.

실제 수집되는 정보 한계 때문에 원래 설계(장르 점유율/인기 키워드)를
아래처럼 근사치로 대체함:
  - 장르 점유율 → 플랫폼 비중 (네이버 vs 카카오 건수 비율)
  - 인기 키워드 → 제목에서 자주 등장한 단어 빈도 (형태소 분석 아님, 단순 공백 split)
"""
import json
import re
from collections import Counter
from pathlib import Path
from scrapers.db_utils import get_connection

OUTPUT_PATH = Path(__file__).parent.parent / "docs" / "data.json"
REPORTS_DIR = Path(__file__).parent.parent / "reports"

# 웹소설에서 흔히 쓰이는 소재/트로프 키워드 — 제목에 이 단어가 포함되면 카운트.
# 단순 단어빈도(공백 split)는 한국어 제목 특성상(띄어쓰기 없는 한 단어 제목이 많음)
# 거의 안 겹쳐서 의미가 없었음 — 그래서 사전 정의 트로프 목록 매칭 방식으로 변경.
TROPE_KEYWORDS = [
    "회귀", "빙의", "환생", "각성", "헌터", "무협", "마법사", "아카데미",
    "재벌", "계약", "복수", "육아", "힐링", "착각", "완결", "독점",
    "최강", "폐급", "빌런", "천재", "black", "황후", "공작", "군주",
    "귀환", "리메이크", "서포터", "시한부", "선공개", "신점", "영지",
]


def export_dashboard_json():
    conn = get_connection()

    dates = [
        r["snapshot_date"] for r in conn.execute(
            "SELECT DISTINCT snapshot_date FROM rank_snapshots ORDER BY snapshot_date DESC LIMIT 2"
        ).fetchall()
    ]
    if not dates:
        print("스냅샷 데이터 없음 — data.json 생성 생략")
        return

    current_date = dates[0]
    prev_date = dates[1] if len(dates) > 1 else None

    current_rows = conn.execute(
        """SELECT w.id as work_id, w.platform, w.title, w.genre, w.is_exclusive, s.rank
           FROM rank_snapshots s JOIN works w ON w.id = s.work_id
           WHERE s.snapshot_date = ? AND s.rank_category = 'overall'
           ORDER BY s.rank ASC""",
        (current_date,),
    ).fetchall()

    prev_ranks = {}
    if prev_date:
        prev_rows = conn.execute(
            """SELECT work_id, rank FROM rank_snapshots
               WHERE snapshot_date = ? AND rank_category = 'overall'""",
            (prev_date,),
        ).fetchall()
        prev_ranks = {r["work_id"]: r["rank"] for r in prev_rows}

    # 급상승 TOP5
    rising = []
    for row in current_rows:
        if row["work_id"] in prev_ranks:
            delta = prev_ranks[row["work_id"]] - row["rank"]
            if delta > 0:
                rising.append({
                    "rank": row["rank"],
                    "delta": delta,
                    "title": row["title"],
                    "meta": f"{row['genre'] or row['platform']} · {row['platform']} · {'독점' if row['is_exclusive'] else '연재중'}",
                })
    rising.sort(key=lambda x: -x["delta"])
    rising = rising[:5]

    # 신규 진입작
    new_entries = []
    for row in current_rows:
        if row["work_id"] not in prev_ranks:
            new_entries.append({
                "genre": row["genre"] or row["platform"],  # 장르 없으면 플랫폼명으로 대체
                "title": row["title"],
                "platform": f"{row['platform']} · {'독점' if row['is_exclusive'] else '연재중'}",
            })
    new_entries = new_entries[:5]

    # 장르 점유율 (장르 없는 항목은 플랫폼명으로 집계)
    genre_counts = Counter((row["genre"] or row["platform"]) for row in current_rows)
    total = sum(genre_counts.values()) or 1
    genres = [
        {"name": g, "pct": round(c / total * 100)}
        for g, c in genre_counts.most_common()
    ]

    # 제목 속 트로프 키워드 빈도 (인기 키워드 대체)
    word_counter = Counter()
    for row in current_rows:
        title = row["title"]
        for kw in TROPE_KEYWORDS:
            if kw in title:
                word_counter[kw] += 1
    top_words = word_counter.most_common(11)
    size_tiers = ["k1", "k1", "k2", "k2", "k2", "k3", "k3", "k3", "k4", "k4", "k4"]
    keywords = [
        {"text": w, "size": size_tiers[i] if i < len(size_tiers) else "k4"}
        for i, (w, _) in enumerate(top_words)
    ]

    # 리포트 목록 (파일명 기준 최신 5개)
    reports = []
    if REPORTS_DIR.exists():
        report_files = sorted(REPORTS_DIR.glob("*.md"), reverse=True)[:5]
        reports = [
            {"date": f.stem, "title": f"{f.stem} 리포트"}
            for f in report_files
        ]

    output = {
        "generated_at": current_date,
        "rising": rising,
        "genres": genres,
        "newEntries": new_entries,
        "keywords": keywords,
        "reports": reports,
    }

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(OUTPUT_PATH, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    conn.close()
    print(f"대시보드 데이터 저장: {OUTPUT_PATH}")


if __name__ == "__main__":
    export_dashboard_json()
