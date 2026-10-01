"""온비드 차세대 Open API 어댑터.

공식 명세가 확인된 operation만 호출하며, 응답 필드 매핑 전에는 원본을 보존합니다.
"""

from __future__ import annotations

import re
from datetime import date
from typing import Any
from urllib.parse import unquote

import httpx

try:
    from ..api_config import API
except ImportError:
    from api_config import API


ONBID_OPERATIONS = {
    "real_estate_list": "https://apis.data.go.kr/B010003/OnbidRlstListSrvc2/getRlstCltrList2",
    "real_estate_detail": "https://apis.data.go.kr/B010003/OnbidRlstDtlSrvc2/getRlstDtlInf2",
    "notice_list": "https://apis.data.go.kr/B010003/OnbidPbancListSrvc2/getPbancList2",
    "bid_information": "https://apis.data.go.kr/B010003/OnbidPbancBidDtlSrvc2/getPbancBidInf2",
    "bid_result_list": "https://apis.data.go.kr/B010003/OnbidCltrBidRsltListSrvc2/getCltrBidRsltList2",
    "bid_result_detail": "https://apis.data.go.kr/B010003/OnbidCltrBidRsltDtlSrvc2/getCltrBidRsltDtl2",
}


def extract_items(payload: Any) -> list[dict[str, Any]]:
    """공공데이터포털 표준 응답의 item을 추출하고, 알 수 없는 형식은 버리지 않습니다."""
    if isinstance(payload, list):
        return [item for item in payload if isinstance(item, dict)]
    if not isinstance(payload, dict):
        return []
    try:
        container = payload["response"]["body"]["items"]
        items = container.get("item", []) if isinstance(container, dict) else []
    except (KeyError, TypeError):
        return []
    if isinstance(items, dict):
        return [items]
    if isinstance(items, list):
        return [item for item in items if isinstance(item, dict)]
    return []


class OnbidService:
    def __init__(self, client: httpx.Client | None = None) -> None:
        self.client = client

    @property
    def configured(self) -> bool:
        return API.onbid_enabled and bool(API.onbid_api_key)

    def _request(self, operation: str, params: dict[str, Any]) -> Any:
        if not self.configured:
            raise RuntimeError("온비드 API가 비활성화되어 있습니다. API 키와 ONBID_ENABLED 설정을 확인하세요.")
        if operation not in ONBID_OPERATIONS:
            raise ValueError("등록되지 않은 온비드 API operation입니다.")
        query = {key: value for key, value in params.items() if value is not None and value != ""}
        query.update({"serviceKey": unquote(API.onbid_api_key), "_type": "json"})
        if self.client is not None:
            response = self.client.get(ONBID_OPERATIONS[operation], params=query, timeout=API.timeout_seconds)
            response.raise_for_status()
            return response.json()
        with httpx.Client(timeout=API.timeout_seconds) as client:
            response = client.get(ONBID_OPERATIONS[operation], params=query)
            response.raise_for_status()
            return response.json()

    @staticmethod
    def _required(params: dict[str, Any], names: tuple[str, ...]) -> None:
        missing = [name for name in names if not params.get(name)]
        if missing:
            raise ValueError(f"온비드 공식 명세상 필수 검색조건이 필요합니다: {', '.join(missing)}")

    @staticmethod
    def _validate_date_range(params: dict[str, Any], *, allow_future_end: bool) -> None:
        start = str(params.get("opbdDtStart", ""))
        end = str(params.get("opbdDtEnd", ""))
        if not re.fullmatch(r"\d{8}", start) or not re.fullmatch(r"\d{8}", end):
            raise ValueError("개찰일은 YYYYMMDD 형식으로 입력해야 합니다.")
        if start > end:
            raise ValueError("개찰 시작일은 종료일보다 늦을 수 없습니다.")
        if not allow_future_end and end > date.today().strftime("%Y%m%d"):
            raise ValueError("입찰결과 조회 종료일은 오늘 이후일 수 없습니다.")

    def list_real_estate(self, params: dict[str, Any]) -> Any:
        self._required(params, ("prptDivCd", "pvctTrgtYn"))
        return self._request("real_estate_list", params)

    def get_real_estate_detail(self, cltr_mng_no: str, pbct_cdtn_no: str | None = None) -> Any:
        params: dict[str, Any] = {"cltrMngNo": cltr_mng_no}
        if pbct_cdtn_no:
            params["pbctCdtnNo"] = pbct_cdtn_no
        return self._request("real_estate_detail", params)

    def list_notices(self, params: dict[str, Any]) -> Any:
        self._required(params, ("cltrTypeCd", "prptDivCd", "opbdDtStart", "opbdDtEnd"))
        self._validate_date_range(params, allow_future_end=True)
        return self._request("notice_list", params)

    def get_bid_information(self, pbanc_mng_no: str) -> Any:
        return self._request("bid_information", {"pbancMngNo": pbanc_mng_no})

    def list_bid_results(self, params: dict[str, Any]) -> Any:
        self._required(params, ("cltrTypeCd", "prptDivCd", "opbdDtStart", "opbdDtEnd"))
        self._validate_date_range(params, allow_future_end=False)
        return self._request("bid_result_list", params)

    def get_bid_result_detail(self, cltr_mng_no: str, pbct_cdtn_no: str | None = None) -> Any:
        params: dict[str, Any] = {"cltrMngNo": cltr_mng_no}
        if pbct_cdtn_no:
            params["pbctCdtnNo"] = pbct_cdtn_no
        return self._request("bid_result_detail", params)
