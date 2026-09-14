"""MongoDB에 검색 이력과 아파트별 검색 횟수를 저장합니다.

MongoDB가 설정되지 않았거나 잠시 중단되어도 화면은 샘플/실시간 API 기능을
계속 제공하도록 모든 저장 실패를 안전하게 무시합니다.
"""

from datetime import datetime, timezone
from typing import Any

try:
    from pymongo import DESCENDING, MongoClient
except ImportError:  # 의존성 설치 전에도 앱 import가 가능하도록 처리
    DESCENDING = None
    MongoClient = None

try:
    from .api_config import API
except ImportError:
    from api_config import API

_client = None
_db = None


def _database():
    global _client, _db
    if _db is not None or not API.mongo_uri or MongoClient is None:
        return _db
    try:
        _client = MongoClient(API.mongo_uri, serverSelectionTimeoutMS=1500)
        _client.admin.command("ping")
        _db = _client[API.mongo_database]
        _db.search_logs.create_index([("created_at", DESCENDING)])
        _db.property_search_counts.create_index("property_key", unique=True)
    except Exception:
        _client = None
        _db = None
    return _db


def record_search(query: str, properties: list[dict[str, Any]]) -> bool:
    db = _database()
    if db is None or not query.strip():
        return False
    try:
        now = datetime.now(timezone.utc)
        db.search_logs.insert_one({
            "query": query.strip(),
            "result_count": len(properties),
            "created_at": now,
            "property_keys": [str(item.get("id")) for item in properties],
        })
        for item in properties:
            key = str(item.get("id"))
            db.property_search_counts.update_one(
                {"property_key": key},
                {"$inc": {"search_count": 1}, "$set": {"name": item.get("name"), "region": item.get("region"), "updated_at": now}},
                upsert=True,
            )
        return True
    except Exception:
        return False


def search_stats() -> dict[str, Any]:
    db = _database()
    if db is None:
        return {"connected": False, "total_searches": 0, "top_properties": []}
    try:
        total = db.search_logs.count_documents({})
        top = list(db.property_search_counts.find({}, {"_id": 0}).sort("search_count", DESCENDING).limit(5))
        return {"connected": True, "total_searches": total, "top_properties": top}
    except Exception:
        return {"connected": False, "total_searches": 0, "top_properties": []}