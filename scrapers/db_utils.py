"""
DB 저장 공통 유틸.
각 플랫폼 스크래퍼가 뽑아온 랭킹 리스트를 여기로 넘기면 DB에 저장해줌.
"""
import sqlite3
from pathlib import Path
from datetime import date

DB_PATH = Path(__file__).parent.parent / "db" / "tracker.db"
SCHEMA_PATH = Path(__file__).parent.parent / "db" / "schema.sql"


def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_connection()
    with open(SCHEMA_PATH, "r", encoding="utf-8") as f:
        conn.executescript(f.read())
    conn.commit()
    conn.close()


def upsert_work(conn, platform, platform_work_id, title, author=None,
                 genre=None, url=None, is_exclusive=False):
    """작품이 없으면 새로 만들고, 있으면 기존 id 반환."""
    cur = conn.execute(
        "SELECT id FROM works WHERE platform=? AND platform_work_id=?",
        (platform, platform_work_id),
    )
    row = cur.fetchone()
    if row:
        return row["id"]

    cur = conn.execute(
        """INSERT INTO works (platform, platform_work_id, title, author, genre, url, is_exclusive)
           VALUES (?, ?, ?, ?, ?, ?, ?)""",
        (platform, platform_work_id, title, author, genre, url, int(is_exclusive)),
    )
    conn.commit()
    return cur.lastrowid


def save_snapshot(conn, work_id, snapshot_date, rank, rank_category="overall", views=None):
    conn.execute(
        """INSERT INTO rank_snapshots (work_id, snapshot_date, rank, rank_category, views)
           VALUES (?, ?, ?, ?, ?)
           ON CONFLICT(work_id, snapshot_date, rank_category)
           DO UPDATE SET rank=excluded.rank, views=excluded.views""",
        (work_id, snapshot_date, rank, rank_category, views),
    )
    conn.commit()


def save_ranking_batch(platform, ranking_list, snapshot_date=None, rank_category="overall"):
    """
    ranking_list: [
        {"platform_work_id": "...", "title": "...", "author": "...",
         "genre": "...", "url": "...", "is_exclusive": False,
         "rank": 1, "views": None},
        ...
    ]
    """
    if snapshot_date is None:
        snapshot_date = date.today().isoformat()

    conn = get_connection()
    for item in ranking_list:
        work_id = upsert_work(
            conn, platform,
            item["platform_work_id"], item["title"],
            item.get("author"), item.get("genre"),
            item.get("url"), item.get("is_exclusive", False),
        )
        save_snapshot(conn, work_id, snapshot_date, item["rank"], rank_category, item.get("views"))
    conn.close()
    print(f"[{platform}] {len(ranking_list)}건 저장 완료 ({snapshot_date})")
