import argparse
import datetime
import json
import os
import sqlite3
from urllib.parse import urlparse
from collections import defaultdict

from pymongo import MongoClient
from bson import ObjectId
from bson.dbref import DBRef


def _to_jsonable(value):
    if isinstance(value, ObjectId):
        return str(value)
    if isinstance(value, DBRef):
        return str(value.id)
    if isinstance(value, datetime.datetime):
        return value.isoformat()
    if isinstance(value, list):
        return [_to_jsonable(v) for v in value]
    if isinstance(value, dict):
        return {str(k): _to_jsonable(v) for k, v in value.items()}
    return value


def _extract_db_name(mongo_uri, fallback):
    parsed = urlparse(mongo_uri)
    path = (parsed.path or "").strip("/")
    if path:
        return path.split("?")[0]
    return fallback


def _ensure_sqlite_schema(sqlite_path):
    os.makedirs(os.path.dirname(os.path.abspath(sqlite_path)), exist_ok=True)
    conn = sqlite3.connect(sqlite_path)
    try:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS __documents (
                collection TEXT NOT NULL,
                id TEXT NOT NULL,
                data TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                PRIMARY KEY (collection, id)
            )
            """
        )
        conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_documents_collection ON __documents(collection)"
        )
        conn.commit()
    finally:
        conn.close()


def _load_rows(conn, collection):
    rows = conn.execute(
        "SELECT id, data, updated_at FROM __documents WHERE collection = ?",
        (collection,),
    ).fetchall()
    result = []
    for row in rows:
        payload = json.loads(row[1]) if row[1] else {}
        result.append({"id": row[0], "data": payload, "updated_at": row[2]})
    return result


def _email_key(doc):
    return str(doc.get("data", {}).get("email", "")).strip().lower()


def dedupe_users(sqlite_path, backup_path=None):
    """Keep one user document per email and back up removed duplicates."""
    conn = sqlite3.connect(sqlite_path)
    try:
        rows = _load_rows(conn, "users")
        grouped = defaultdict(list)
        for row in rows:
            email = _email_key(row)
            if email:
                grouped[email].append(row)

        removed = []
        for email, items in grouped.items():
            if len(items) < 2:
                continue

            def _sort_key(item):
                updated = item.get("updated_at") or ""
                created = item.get("data", {}).get("createdAt") or ""
                return (updated, created, item.get("id", ""))

            items.sort(key=_sort_key)
            keeper = items[-1]
            duplicates = items[:-1]

            for item in duplicates:
                removed.append({
                    "email": email,
                    "keptId": keeper.get("id"),
                    "removedId": item.get("id"),
                    "removedDoc": item,
                })
                conn.execute(
                    "DELETE FROM __documents WHERE collection = ? AND id = ?",
                    ("users", item.get("id")),
                )

        conn.commit()

        if backup_path and removed:
            os.makedirs(os.path.dirname(os.path.abspath(backup_path)), exist_ok=True)
            with open(backup_path, "w", encoding="utf-8") as handle:
                json.dump(removed, handle, ensure_ascii=False, indent=2)

        return len(removed)
    finally:
        conn.close()


def migrate(mongo_uri, sqlite_path, db_name=None, drop_existing=False):
    _ensure_sqlite_schema(sqlite_path)

    resolved_db_name = db_name or _extract_db_name(mongo_uri, "internship_reports")
    client = MongoClient(mongo_uri)
    db = client[resolved_db_name]

    conn = sqlite3.connect(sqlite_path)
    try:
        if drop_existing:
            conn.execute("DELETE FROM __documents")
            conn.commit()

        collections = [name for name in db.list_collection_names() if not name.startswith("system.")]
        total = 0

        for collection in collections:
            cursor = db[collection].find({})
            count = 0
            for raw_doc in cursor:
                doc = _to_jsonable(raw_doc)
                doc_id = str(doc.pop("_id"))
                payload = json.dumps(doc, ensure_ascii=False)
                conn.execute(
                    """
                    INSERT INTO __documents(collection, id, data, updated_at)
                    VALUES(?, ?, ?, ?)
                    ON CONFLICT(collection, id)
                    DO UPDATE SET data=excluded.data, updated_at=excluded.updated_at
                    """,
                    (collection, doc_id, payload, datetime.datetime.utcnow().isoformat()),
                )
                count += 1

            conn.commit()
            total += count
            print(f"Migrated {count} docs from collection '{collection}'")

        print(f"Done. Migrated {total} total documents into SQLite: {sqlite_path}")
    finally:
        conn.close()
        client.close()


def main():
    parser = argparse.ArgumentParser(description="Migrate MongoDB data into SQLite storage used by this app")
    parser.add_argument("--mongo-uri", default=os.getenv("MONGODB_URI", "mongodb://localhost:27017/internship_reports"))
    parser.add_argument("--db-name", default=os.getenv("MONGODB_DB"))
    parser.add_argument("--sqlite-path", default=os.getenv("SQLITE_PATH", os.path.join(os.path.dirname(__file__), "data", "app.db")))
    parser.add_argument("--drop-existing", action="store_true", help="Delete existing SQLite documents before migration")
    parser.add_argument("--dedupe-users", action="store_true", help="Keep only one SQLite user row per email and back up removed duplicates")
    parser.add_argument("--dedupe-backup", default=os.path.join(os.path.dirname(__file__), "data", "duplicate_users_backup.json"))
    args = parser.parse_args()

    migrate(
        mongo_uri=args.mongo_uri,
        sqlite_path=args.sqlite_path,
        db_name=args.db_name,
        drop_existing=args.drop_existing,
    )

    if args.dedupe_users:
        removed = dedupe_users(args.sqlite_path, args.dedupe_backup)
        print(f"Deduped {removed} duplicate user rows")


if __name__ == "__main__":
    main()
