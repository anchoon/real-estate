"""공통 검색 결과 모델. 원본 API 필드는 raw에 보존하고 확인된 값만 정규화합니다."""

from datetime import datetime
from typing import Any, Literal

from pydantic import BaseModel, Field


class IntelligenceListing(BaseModel):
    source: Literal["real_estate", "court_auction", "onbid"]
    source_id: str
    address: str | None = None
    latitude: float | None = None
    longitude: float | None = None
    property_type: str | None = None
    area: float | None = None
    transaction_price: int | None = None
    appraisal_price: int | None = None
    minimum_price: int | None = None
    auction_status: str | None = None
    bid_date: datetime | None = None
    raw: dict[str, Any] = Field(default_factory=dict)
