#!/usr/bin/env python
import argparse
import csv
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Iterable, List, Optional

from sqlalchemy import create_engine, insert, text
from sqlalchemy.engine import Engine
from sqlalchemy.engine.url import make_url
from sqlalchemy.exc import SQLAlchemyError


def _repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def _parse_args(argv: List[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Initialize the medrecon table from datasets/medrecon.csv"
    )
    parser.add_argument(
        "--csv",
        dest="csv_path",
        default=str(_repo_root() / "datasets" / "medrecon.csv"),
        help="Path to medrecon.csv (default: datasets/medrecon.csv)",
    )
    parser.add_argument(
        "--database-url",
        dest="database_url",
        default=None,
        help="SQLAlchemy database URL override (default: app.config.settings.DATABASE_URL)",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=10_000,
        help="Rows per INSERT batch (default: 10000)",
    )
    parser.add_argument(
        "--commit-every",
        type=int,
        default=50_000,
        help="Commit every N inserted rows (default: 50000)",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Load only the first N rows (for testing)",
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Drop and recreate the medrecon table before loading",
    )
    parser.add_argument(
        "--append",
        action="store_true",
        help="Append into an existing non-empty table (default: refuse to avoid duplicates)",
    )
    parser.add_argument(
        "--sqlite-fast",
        action="store_true",
        help="Enable faster (less durable) SQLite PRAGMAs during load",
    )
    return parser.parse_args(argv)


def _make_engine(database_url: str) -> Engine:
    connect_args = {}
    if database_url.startswith("sqlite"):
        connect_args = {"check_same_thread": False}
    return create_engine(database_url, connect_args=connect_args, future=True)


def _resolve_database_url(database_url: str) -> str:
    """
    Ensure SQLite relative paths always point at the repo root.

    Without this, running the script from `scripts/` would create/use `scripts/app.db`
    for a URL like `sqlite:///app.db`.
    """
    try:
        url = make_url(database_url)
    except Exception:  # noqa: BLE001
        return database_url

    if not url.drivername.startswith("sqlite"):
        return database_url
    if not url.database or url.database == ":memory:":
        return database_url

    db_path = Path(url.database)
    if db_path.is_absolute():
        return database_url

    abs_db_path = (_repo_root() / db_path).resolve()
    return str(url.set(database=str(abs_db_path)))


def _apply_sqlite_pragmas(engine: Engine, fast: bool) -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    pragmas = [
        "PRAGMA foreign_keys=ON",
        "PRAGMA journal_mode=WAL",
        "PRAGMA synchronous=NORMAL",
    ]
    if fast:
        pragmas = [
            "PRAGMA foreign_keys=ON",
            "PRAGMA journal_mode=OFF",
            "PRAGMA synchronous=OFF",
            "PRAGMA temp_store=MEMORY",
        ]
    with engine.connect() as conn:
        for stmt in pragmas:
            conn.exec_driver_sql(stmt)
        conn.commit()


def _ensure_imports() -> None:
    repo_root = _repo_root()
    if str(repo_root) not in sys.path:
        sys.path.insert(0, str(repo_root))


def _maybe_empty(value: str) -> Optional[str]:
    v = value.strip()
    return v if v else None


def _iter_batches(
    csv_path: Path, batch_size: int, limit: Optional[int]
) -> Iterable[List[dict]]:
    with csv_path.open(newline="") as f:
        reader = csv.reader(f)
        header = next(reader, None)
        if header is None:
            return
        header = [h.strip() for h in header]
        expected = [
            "subject_id",
            "stay_id",
            "charttime",
            "name",
            "gsn",
            "ndc",
            "etc_rn",
            "etccode",
            "etcdescription",
        ]
        if header != expected:
            raise ValueError(
                f"Unexpected CSV header. Expected {expected!r} but got {header!r}"
            )

        batch: List[dict] = []
        for i, row in enumerate(reader, start=1):
            if limit is not None and i > limit:
                break

            try:
                subject_id = int(row[0])
                stay_id = int(row[1])
                charttime = datetime.fromisoformat(row[2])
                name = row[3].strip()
                gsn = _maybe_empty(row[4])
                ndc = _maybe_empty(row[5])
                etc_rn = int(row[6])
                etccode = _maybe_empty(row[7])
                etcdescription = _maybe_empty(row[8])
            except Exception as e:  # noqa: BLE001
                raise ValueError(f"Failed parsing CSV row {i}: {row!r}") from e

            batch.append(
                {
                    "subject_id": subject_id,
                    "stay_id": stay_id,
                    "charttime": charttime,
                    "name": name,
                    "gsn": gsn,
                    "ndc": ndc,
                    "etc_rn": etc_rn,
                    "etccode": etccode,
                    "etcdescription": etcdescription,
                }
            )
            if len(batch) >= batch_size:
                yield batch
                batch = []

        if batch:
            yield batch


def _table_row_count(engine: Engine) -> int:
    with engine.connect() as conn:
        result = conn.execute(text("SELECT COUNT(*) FROM medrecon"))
        return int(result.scalar_one())


def main(argv: List[str]) -> int:
    _ensure_imports()
    args = _parse_args(argv)

    from app.config import settings
    from app.models.medrecon import Medrecon

    if args.batch_size <= 0:
        print("--batch-size must be > 0", file=sys.stderr)
        return 2
    if args.commit_every <= 0:
        print("--commit-every must be > 0", file=sys.stderr)
        return 2

    csv_path = Path(args.csv_path)
    if not csv_path.is_absolute():
        csv_path = (_repo_root() / csv_path).resolve()
    if not csv_path.exists():
        print(f"CSV not found: {csv_path}", file=sys.stderr)
        return 2

    database_url_raw = args.database_url or settings.DATABASE_URL
    database_url = _resolve_database_url(database_url_raw)
    if database_url != database_url_raw:
        print(f"Resolved DATABASE_URL to: {database_url}")
    engine = _make_engine(database_url)

    try:
        _apply_sqlite_pragmas(engine, fast=args.sqlite_fast)

        if args.reset:
            Medrecon.__table__.drop(engine, checkfirst=True)
        Medrecon.__table__.create(engine, checkfirst=True)

        if not args.reset and not args.append:
            existing = _table_row_count(engine)
            if existing > 0:
                print(
                    f"Refusing to load: medrecon already has {existing} rows. "
                    "Use --reset to rebuild or --append to add more.",
                    file=sys.stderr,
                )
                return 3

        insert_stmt = insert(Medrecon.__table__)

        inserted = 0
        started = time.time()

        with engine.connect() as conn:
            tx = conn.begin()
            for batch in _iter_batches(csv_path, args.batch_size, args.limit):
                conn.execute(insert_stmt, batch)
                inserted += len(batch)

                if inserted % args.commit_every == 0:
                    tx.commit()
                    tx = conn.begin()
                    elapsed = max(time.time() - started, 0.001)
                    rate = int(inserted / elapsed)
                    print(f"Inserted {inserted:,} rows ({rate:,} rows/s)")

            tx.commit()

        total = _table_row_count(engine)
        elapsed = max(time.time() - started, 0.001)
        print(f"Done. Inserted {inserted:,} rows. Table now has {total:,} rows.")
        print(f"Elapsed: {elapsed:.1f}s")
        return 0
    except (OSError, ValueError, SQLAlchemyError) as e:
        print(f"Failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
