"""MongoDB 기반 자유게시판 저장소."""

from datetime import datetime, timezone
from typing import Any

try:
    from .search_store import get_database
except ImportError:
    from search_store import get_database


def list_posts(limit: int = 20, skip: int = 0) -> tuple[list[dict[str, Any]], int]:
    db = get_database()
    if db is None:
        raise RuntimeError("MongoDB is not configured")
    collection = db.community_posts
    collection.create_index([("created_at", -1)])
    posts = list(collection.find({}, {"_id": 0}).sort("created_at", -1).skip(skip).limit(limit))
    return posts, collection.count_documents({})


def create_post(nickname: str, title: str, content: str) -> dict[str, Any]:
    db = get_database()
    if db is None:
        raise RuntimeError("MongoDB is not configured")
    post = {
        "nickname": nickname,
        "title": title,
        "content": content,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    db.community_posts.insert_one(post)
    return post
