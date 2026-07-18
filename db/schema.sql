-- 웹소설 랭킹 트래커 DB 스키마
-- SQLite 기준

CREATE TABLE IF NOT EXISTS works (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    platform TEXT NOT NULL,           -- 'naver' | 'kakao' | 'ridi'
    platform_work_id TEXT,            -- 플랫폼 내부 작품 ID (URL에서 추출)
    title TEXT NOT NULL,
    author TEXT,
    genre TEXT,                       -- 판타지 / 로맨스 / 로판 / BL 등
    url TEXT,
    is_exclusive INTEGER DEFAULT 0,   -- 독점 여부
    first_seen_at TEXT DEFAULT (datetime('now')),
    UNIQUE(platform, platform_work_id)
);

CREATE TABLE IF NOT EXISTS rank_snapshots (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    work_id INTEGER NOT NULL REFERENCES works(id),
    snapshot_date TEXT NOT NULL,      -- 'YYYY-MM-DD' (매주 일요일 등 기준일)
    rank INTEGER NOT NULL,
    rank_category TEXT DEFAULT 'overall',  -- 'overall' | genre별 랭킹 등
    views INTEGER,                    -- 조회수 있으면 기록 (없으면 NULL)
    UNIQUE(work_id, snapshot_date, rank_category)
);

CREATE INDEX IF NOT EXISTS idx_snapshots_date ON rank_snapshots(snapshot_date);
CREATE INDEX IF NOT EXISTS idx_snapshots_work ON rank_snapshots(work_id);

-- 급상승 계산용 뷰: 직전 스냅샷 대비 순위 변동
-- (실제 계산은 Python 쪽에서 두 스냅샷 date를 비교해서 처리하는 게 더 유연함)
