"""PROPERTY INTELLIGENCE 신규 API. 기존 /api 라우트와 독립적으로 추가됩니다."""

from __future__ import annotations

import json
from typing import Any

import httpx
from fastapi import APIRouter, HTTPException, Query

try:
    from ..api_config import API
    from ..services.onbid_service import OnbidService, extract_items
    from ..stores.intelligence_store import save_source_records
except ImportError:
    from api_config import API
    from services.onbid_service import OnbidService, extract_items
    from stores.intelligence_store import save_source_records

router = APIRouter(prefix="/api/v1", tags=["Property Intelligence"])
onbid = OnbidService()


def _disabled_payload(source: str, reason: str) -> dict[str, Any]:
    return {"source": source, "configured": False, "items": [], "message": reason}


def _call(kind: str, operation: Any) -> dict[str, Any]:
    if not onbid.configured:
        return _disabled_payload("onbid", "온비드 API 발급 후 ONBID_API_KEY와 ONBID_ENABLED=true를 설정하세요.")
    try:
        payload = operation()
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=str(exc)) from exc
    except (httpx.HTTPError, RuntimeError, ValueError) as exc:
        raise HTTPException(status_code=502, detail="온비드 공식 API 호출에 실패했습니다.") from exc
    items = extract_items(payload)
    saved = save_source_records(kind, items)
    return {
        "source": "onbid",
        "configured": True,
        "count": len(items),
        "saved": saved,
        "items": items,
        "raw_response": payload if not items else None,
    }


@router.get("/sources")
def source_status() -> dict[str, Any]:
    return {
        "sources": {
            "real_estate": {"configured": bool(API.data_go_kr_key), "status": "ready" if API.data_go_kr_key else "needs_api_key"},
            "onbid": {"configured": onbid.configured, "status": "ready" if onbid.configured else "awaiting_api_key"},
            "court_auction": {"configured": False, "status": "awaiting_official_api_access", "message": "법원 연계 API 이용 권한과 경매 데이터 명세 확인 후 연결합니다. 크롤링은 사용하지 않습니다."},
        },
        "storage": {"database_configured": bool(API.mongo_uri), "collections": ["real_estate_transactions", "court_auction", "court_auction_events", "onbid_items", "onbid_notices", "onbid_bid_information", "onbid_bid_results"]},
    }


@router.get("/onbid/items")
def onbid_items(
    prpt_div_cd: str | None = Query(default=None, alias="prptDivCd"),
    pvct_trgt_yn: str | None = Query(default=None, alias="pvctTrgtYn"),
) -> dict[str, Any]:
    params = {"prptDivCd": prpt_div_cd, "pvctTrgtYn": pvct_trgt_yn}
    return _call("onbid_item", lambda: onbid.list_real_estate(params))


@router.get("/onbid/items/{cltr_mng_no}")
def onbid_item_detail(
    cltr_mng_no: str,
    pbct_cdtn_no: str | None = Query(default=None, alias="pbctCdtnNo"),
) -> dict[str, Any]:
    return _call("onbid_item", lambda: onbid.get_real_estate_detail(cltr_mng_no, pbct_cdtn_no))


@router.get("/onbid/notices")
def onbid_notices(
    cltr_type_cd: str | None = Query(default=None, alias="cltrTypeCd"),
    prpt_div_cd: str | None = Query(default=None, alias="prptDivCd"),
    opbd_dt_start: str | None = Query(default=None, alias="opbdDtStart"),
    opbd_dt_end: str | None = Query(default=None, alias="opbdDtEnd"),
) -> dict[str, Any]:
    params = {"cltrTypeCd": cltr_type_cd, "prptDivCd": prpt_div_cd, "opbdDtStart": opbd_dt_start, "opbdDtEnd": opbd_dt_end}
    return _call("onbid_notice", lambda: onbid.list_notices(params))


@router.get("/onbid/notices/{pbanc_mng_no}/bid-information")
def onbid_bid_information(pbanc_mng_no: str) -> dict[str, Any]:
    return _call("onbid_bid_information", lambda: onbid.get_bid_information(pbanc_mng_no))


@router.get("/onbid/results")
def onbid_results(
    cltr_type_cd: str | None = Query(default=None, alias="cltrTypeCd"),
    prpt_div_cd: str | None = Query(default=None, alias="prptDivCd"),
    opbd_dt_start: str | None = Query(default=None, alias="opbdDtStart"),
    opbd_dt_end: str | None = Query(default=None, alias="opbdDtEnd"),
) -> dict[str, Any]:
    params = {"cltrTypeCd": cltr_type_cd, "prptDivCd": prpt_div_cd, "opbdDtStart": opbd_dt_start, "opbdDtEnd": opbd_dt_end}
    return _call("onbid_result", lambda: onbid.list_bid_results(params))


@router.get("/onbid/results/{cltr_mng_no}")
def onbid_result_detail(
    cltr_mng_no: str,
    pbct_cdtn_no: str | None = Query(default=None, alias="pbctCdtnNo"),
) -> dict[str, Any]:
    return _call("onbid_result", lambda: onbid.get_bid_result_detail(cltr_mng_no, pbct_cdtn_no))


@router.get("/court-auctions")
def court_auctions() -> dict[str, Any]:
    return {
        "source": "court_auction",
        "configured": False,
        "items": [],
        "message": "법원 공식 연계 API의 이용 권한과 경매 데이터 제공 범위를 확인한 뒤 활성화합니다.",
    }


@router.get("/search")
def integrated_search(
    q: str | None = Query(default=None, max_length=100),
    lawd_cd: str | None = Query(default=None, min_length=5, max_length=10),
    deal_ymd: str | None = Query(default=None, min_length=6, max_length=6),
    dong: str | None = Query(default=None, max_length=80),
    prpt_div_cd: str | None = Query(default=None, alias="prptDivCd"),
    pvct_trgt_yn: str | None = Query(default=None, alias="pvctTrgtYn"),
) -> dict[str, Any]:
    # 기존 실거래 함수를 그대로 재사용하며 기존 endpoint나 저장 구조를 변경하지 않습니다.
    try:
        from ..main import load_properties
    except ImportError:
        from main import load_properties

    properties, real_estate_status = load_properties(search=q, lawd_cd=lawd_cd, deal_ymd=deal_ymd, dong=dong)
    onbid_result = _disabled_payload(
        "onbid",
        "온비드 API 설정 대기 중" if not onbid.configured else "재산유형 코드와 수의계약 가능 여부 코드를 입력하세요.",
    )
    onbid_result["configured"] = onbid.configured
    if onbid.configured and prpt_div_cd and pvct_trgt_yn:
        onbid_result = _call("onbid_item", lambda: onbid.list_real_estate({"prptDivCd": prpt_div_cd, "pvctTrgtYn": pvct_trgt_yn}))
    onbid_items = onbid_result.get("items", [])
    if q:
        keyword = q.casefold()
        onbid_items = [item for item in onbid_items if keyword in json.dumps(item, ensure_ascii=False).casefold()]
    save_source_records("real_estate_item", properties)
    return {
        "items": [{"source": "real_estate", **item} for item in properties] + [{"source": "onbid", "raw": item} for item in onbid_items],
        "sources": {
            "real_estate": {"configured": bool(API.data_go_kr_key), "status": real_estate_status},
            "onbid": {"configured": onbid.configured, "status": onbid_result.get("message", "ready")},
            "court_auction": {"configured": False, "status": "awaiting_official_api_access"},
        },
    }


@router.get("/comparables")
def real_estate_comparables(
    lawd_cd: str = Query(min_length=5, max_length=10),
    area: float = Query(gt=0),
    deal_ymd: str | None = Query(default=None, min_length=6, max_length=6),
    dong: str | None = Query(default=None, max_length=80),
    tolerance: float = Query(default=0.2, gt=0, le=0.5),
) -> dict[str, Any]:
    """지역·전용면적 범위가 확인된 실거래 비교. 좌표 근접성은 주장하지 않습니다."""
    try:
        from ..main import load_properties
    except ImportError:
        from main import load_properties

    items, status = load_properties(lawd_cd=lawd_cd, deal_ymd=deal_ymd, dong=dong)
    matches = [item for item in items if item.get("area") and abs(float(item["area"]) - area) / area <= tolerance]
    prices = [int(item["price"]) for item in matches if item.get("price")]
    return {
        "source": "real_estate",
        "status": status,
        "match_basis": "same_region_and_area_range",
        "area": area,
        "tolerance": tolerance,
        "count": len(matches),
        "average_price": round(sum(prices) / len(prices)) if prices else None,
        "items": matches,
    }


@router.get("/statistics")
def intelligence_statistics() -> dict[str, Any]:
    return {
        "status": "awaiting_result_field_mapping",
        "onbid": {"available": onbid.configured, "metrics": [], "message": "공식 응답 필드 확인 후 낙찰가율·유찰 통계를 계산합니다."},
        "court_auction": {"available": False, "metrics": [], "message": "법원 API 권한과 매각결과 명세 확인 대기 중"},
    }
