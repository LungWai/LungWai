from __future__ import annotations

import json
import os
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).parent
PROJECTS = ROOT / "projects.json"
JSON_MIRROR = ROOT / "db_products.json"

DEFAULT_TABLE_NAME = os.getenv("NEON_TABLE", "products")


def _slugify(value: str) -> str:
    value = value.strip().lower()
    value = re.sub(r"[^a-z0-9]+", "-", value)
    value = re.sub(r"-+", "-", value).strip("-")
    return value or "item"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _format_ts(dt: datetime) -> str:
    # Match existing example format in db_products.json
    return dt.strftime("%Y-%m-%d %H:%M:%S.%f").rstrip("0").rstrip(".")


def _collect_projects(d: dict[str, Any]) -> list[dict[str, Any]]:
    sections: list[str] = [
        "saas_completed",
        "saas_in_progress",
        "dev_tools",
        "fun_projects",
    ]
    rows: list[dict[str, Any]] = []
    for key in sections:
        part = d.get(key) or []
        if isinstance(part, list):
            rows.extend([r for r in part if isinstance(r, dict)])
    return rows


def _project_to_product(row: dict[str, Any]) -> dict[str, Any]:
    db = row.get("db-attribute") or {}
    title_from_row = (db.get("title") or row.get("title") or row.get("name") or "").strip()
    ident = (db.get("id") or row.get("id") or f"product-{_slugify(title_from_row)[:64]}")
    description = (db.get("description") or row.get("description") or row.get("desc") or "").strip() or None
    url = db.get("url") or row.get("url") or row.get("deploy") or row.get("repo") or None
    now = _now()
    product = {
        "id": ident,
        "title": title_from_row or ident,
        "year": db.get("year") or row.get("year"),
        "description": description,
        "image": db.get("image") or row.get("image"),
        "preview_image": db.get("preview_image") or row.get("preview_image"),
        "url": url,
        "category": db.get("category") or row.get("category"),
        "created_at": now,
        "updated_at": now,
    }
    return product


def _load_projects_file() -> dict[str, Any]:
    tmp = Path("/tmp/projects.json")
    if tmp.exists():
        try:
            return json.loads(tmp.read_text(encoding="utf-8"))
        except Exception:
            pass
    return json.loads(PROJECTS.read_text(encoding="utf-8"))


def _prepare_records() -> list[dict[str, Any]]:
    data = _load_projects_file()
    items = _collect_projects(data)
    products = []
    for it in items:
        if not it.get("sync-with-db"):
            continue
        product = _project_to_product(it)
        products.append(product)
    return products


def _write_json_mirror(records: Iterable[dict[str, Any]]) -> None:
    serializable: list[dict[str, Any]] = []
    for r in records:
        serializable.append({
            **r,
            "created_at": _format_ts(r["created_at"]) if isinstance(r.get("created_at"), datetime) else r.get("created_at"),
            "updated_at": _format_ts(r["updated_at"]) if isinstance(r.get("updated_at"), datetime) else r.get("updated_at"),
        })
    JSON_MIRROR.write_text(json.dumps(serializable, ensure_ascii=False), encoding="utf-8")
    print(f"Wrote {len(serializable)} rows to {JSON_MIRROR} (mirror mode)")


def _normalize_neon_dsn(raw: str) -> str:
    """Normalize NEON_DATABASE_URL values copied from dashboards or CLI.

    Accepts:
    - postgres/postgresql URI: postgresql://user:pass@host:port/db?sslmode=require
    - accidentally copied `psql <uri>` strings (strips the leading `psql`)
    - quoted values (strips single/double quotes)
    """
    s = (raw or "").strip()
    if not s:
        return s
    # Strip surrounding quotes
    if (s.startswith("'") and s.endswith("'")) or (s.startswith('"') and s.endswith('"')):
        s = s[1:-1].strip()
    # Remove leading `psql` command if present
    if s.lower().startswith("psql "):
        s = s.split(None, 1)[1].strip()
    # If a full command was pasted, extract the URI portion
    for scheme in ("postgresql://", "postgres://"):
        idx = s.find(scheme)
        if idx != -1:
            s = s[idx:].strip()
            break
    return s


def _sync_neon(records: Iterable[dict[str, Any]], dsn: str, table: str) -> None:
    # Import locally so the script can run in mirror mode without psycopg installed
    import psycopg

    create_sql = f"""
    CREATE TABLE IF NOT EXISTS {table} (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        year TEXT,
        description TEXT,
        image TEXT,
        preview_image TEXT,
        url TEXT,
        category TEXT,
        created_at TIMESTAMPTZ,
        updated_at TIMESTAMPTZ
    );
    """

    insert_sql = f"""
    INSERT INTO {table} (
        id, title, year, description, image, preview_image, url, category, created_at, updated_at
    ) VALUES (
        %s,%s,%s,%s,%s,%s,%s,%s,%s,%s
    )
    ON CONFLICT (id) DO UPDATE SET
        title = EXCLUDED.title,
        year = EXCLUDED.year,
        description = EXCLUDED.description,
        image = EXCLUDED.image,
        preview_image = EXCLUDED.preview_image,
        url = EXCLUDED.url,
        category = EXCLUDED.category,
        updated_at = EXCLUDED.updated_at;
    """

    rows = list(records)
    with psycopg.connect(dsn) as conn:
        with conn.cursor() as cur:
            cur.execute(create_sql)
            for r in rows:
                cur.execute(
                    insert_sql,
                    (
                        r.get("id"),
                        r.get("title"),
                        r.get("year"),
                        r.get("description"),
                        r.get("image"),
                        r.get("preview_image"),
                        r.get("url"),
                        r.get("category"),
                        r.get("created_at"),
                        r.get("updated_at"),
                    ),
                )
    print(f"Upserted {len(rows)} rows into table '{table}'.")


def sync_from_env(strict: bool = False) -> bool:
    """Sync using NEON_* env vars.

    Returns True if a DB sync was attempted (and succeeded), False if mirrored or skipped.
    In strict mode, exceptions are raised to the caller.
    """
    records = _prepare_records()
    raw_dsn = os.getenv("NEON_DATABASE_URL", "").strip()
    dsn = _normalize_neon_dsn(raw_dsn)
    table = (os.getenv("NEON_TABLE") or DEFAULT_TABLE_NAME).strip()

    if not dsn:
        # No secret available; respect strict setting
        if strict:
            raise RuntimeError("NEON_DATABASE_URL not set")
        return False

    try:
        _sync_neon(records, dsn, table)
        return True
    except Exception:
        if strict:
            raise
        _write_json_mirror(records)
        return False


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Sync projects.json to Neon or mirror to JSON")
    parser.add_argument("--strict", action="store_true", help="Exit non-zero if DB sync fails instead of mirroring")
    args = parser.parse_args()

    print(f"Prepared {len(_prepare_records())} record(s) for DB sync from projects.json")

    raw_dsn = os.getenv("NEON_DATABASE_URL", "").strip()
    dsn = _normalize_neon_dsn(raw_dsn)
    if not dsn:
        msg = "NEON_DATABASE_URL not set"
        print(msg)
        if args.strict:
            raise SystemExit(msg)
        return

    try:
        _sync_neon(_prepare_records(), dsn, os.getenv("NEON_TABLE", DEFAULT_TABLE_NAME))
    except Exception as exc:  # pragma: no cover
        print(f"Error syncing Neon DB: {exc}")
        if args.strict:
            raise
        # Non-strict: no mirror fallback, just return non-zero via print
        print("Skipping mirror; strictness disabled.")


if __name__ == "__main__":
    main() 