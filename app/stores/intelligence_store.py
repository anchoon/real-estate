"""통합 검색용 원본 보존 저장소. 기존 검색/커뮤니티 컬렉션은 건드리지 않습니다."""

from datetime import datetime, timezone
from typing import Any

try:
    from ..search_store import get_database
except ImportError:
    from search_store import get_database

COLLECTIONS = {
    "real_estate_item": "real_estate_transactions",
    "court_auction_item": "court_auction",
    "court_auction_event": "court_auction_events",
    "onbid_item": "onbid_items",
    "onbid_notice": "onbid_notices",
    "onbid_bid_information": "onbid_bid_information",
    "onbid_result": "onbid_bid_results",
}


def save_source_records(kind: str, records: list[dict[str, Any]]) -> int:
    """식별 가능한 원본만 upsert합니다. 응답 필드를 추측하거나 덮어쓰지 않습니다."""
    collection_name = COLLECTIONS.get(kind)
    if not collection_name or not records:
        return 0
    db = get_database()
    if db is None:
        return 0
    collection = db[collection_name]
    collection.create_index("source_id", unique=True)
    now = datetime.now(timezone.utc)
    saved = 0
    for raw in records:
        source_id = raw.get("cltrMngNo") or raw.get("pbancMngNo") or raw.get("id")
        condition_id = raw.get("pbctCdtnNo")
        if not source_id:
            continue
        key = f"{kind}:{source_id}:{condition_id or ''}"
        document = {
            "source": "onbid" if kind.startswith("onbid_") else "real_estate" if kind == "real_estate_item" else kind,
            "source_id": key,
            "raw": raw,
            "updated_at": now,
        }
        collection.update_one(
            {"source_id": key},
            {"$set": document, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
        saved += 1
    return saved
