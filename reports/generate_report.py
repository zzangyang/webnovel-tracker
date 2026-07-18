"""
이번 주 스냅샷과 직전 스냅샷을 비교해서
- 급상승 TOP N (순위가 가장 많이 오른 작품)
- 신규 진입작 (직전 스냅샷에 없던 작품)
을 뽑아 markdown 리포트로 저장.
"""
from pathlib import Path
from datetime import date
from scrapers.db_utils import get_connection

REPORTS_DIR = Path(__file__).parent


def _get_snapshot_dates(conn, before=None, limit=2):
    q = "SELECT DISTINCT snapshot_date FROM rank_snapshots"
    params = []
    if before:
        q += " WHERE snapshot_date <= ?"
        params.append(before)
    q += " ORDER BY snapshot_date DESC LIMIT ?"
    params.append(limit)
    rows = conn.execute(q, params).fetchall()
    return [r["snapshot_date"] for r in rows]


def generate_weekly_report(snapshot_date=None, top_n=10):
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    conn = get_connection()
    dates = _get_snapshot_dates(conn, before=snapshot_date, limit=2)

    if len(dates) < 1:
        print("스냅샷 데이터 없음 — 리포트 생략")
        return

    current_date = dates[0]
    prev_date = dates[1] if len(dates) > 1 else None

    current = conn.execute(
        """SELECT w.title, w.author, w.genre, w.platform, w.url, s.rank
           FROM rank_snapshots s JOIN works w ON w.id = s.work_id
           WHERE s.snapshot_date = ? AND s.rank_category = 'overall'
           ORDER BY s.rank ASC""",
        (current_date,),
    ).fetchall()

    prev_ranks = {}
    if prev_date:
        prev_rows = conn.execute(
            """SELECT w.id as work_id, s.rank
               FROM rank_snapshots s JOIN works w ON w.id = s.work_id
               WHERE s.snapshot_date = ? AND s.rank_category = 'overall'""",
            (prev_date,),
        ).fetchall()
        prev_ranks = {r["work_id"]: r["rank"] for r in prev_rows}

    # work_id 다시 조회 (rank 변화 계산용)
    current_full = conn.execute(
        """SELECT w.id as work_id, w.title, w.author, w.genre, w.platform, w.url, s.rank
           FROM rank_snapshots s JOIN works w ON w.id = s.work_id
           WHERE s.snapshot_date = ? AND s.rank_category = 'overall'
           ORDER BY s.rank ASC""",
        (current_date,),
    ).fetchall()

    rising = []
    new_entries = []
    for row in current_full:
        wid = row["work_id"]
        if wid in prev_ranks:
            delta = prev_ranks[wid] - row["rank"]  # 양수 = 순위 상승
            if delta > 0:
                rising.append((delta, row))
        else:
            new_entries.append(row)

    rising.sort(key=lambda x: -x[0])

    lines = [f"# 주간 리포트 — {current_date}", ""]
    lines.append(f"## 📈 급상승 TOP {top_n}")
    if rising:
        for delta, row in rising[:top_n]:
            lines.append(f"- {row['rank']}위 (+{delta}) [{row['platform']}] {row['title']} — {row['author'] or '작가 미상'} ({row['genre'] or '장르 미상'})")
    else:
        lines.append("_비교할 이전 스냅샷이 없거나 급상승작 없음._")

    lines.append("")
    lines.append(f"## 🆕 신규 진입작 ({len(new_entries)}건)")
    for row in new_entries[:20]:
        lines.append(f"- {row['rank']}위 [{row['platform']}] {row['title']} — {row['author'] or '작가 미상'}")

    out_path = REPORTS_DIR / f"{current_date}.md"
    out_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"리포트 저장: {out_path}")
    conn.close()


if __name__ == "__main__":
    generate_weekly_report()
