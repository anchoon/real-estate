from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

import app.main as main
import app.services.onbid_service as onbid_module
import app.routers.intelligence as intelligence_router
from app.main import app
from app.services.onbid_service import OnbidService, extract_items

client = TestClient(app)


def test_intelligence_page_and_source_status_are_available():
    page = client.get("/intelligence")
    status = client.get("/api/v1/sources")

    assert page.status_code == 200
    assert "PROPERTY INTELLIGENCE" in page.text
    assert status.status_code == 200
    sources = status.json()["sources"]
    assert {"real_estate", "onbid", "court_auction"} <= set(sources)
    assert sources["court_auction"]["configured"] is False


def test_court_auction_route_does_not_return_fake_records():
    response = client.get("/api/v1/court-auctions")

    assert response.status_code == 200
    assert response.json()["configured"] is False
    assert response.json()["items"] == []
    assert "공식" in response.json()["message"]


def test_onbid_response_items_preserve_unrecognized_fields():
    payload = {"response": {"body": {"items": {"item": {"cltrMngNo": "item-1", "opaqueField": "kept"}}}}}

    assert extract_items(payload) == [{"cltrMngNo": "item-1", "opaqueField": "kept"}]


def test_onbid_service_requires_official_listing_filters():
    service = OnbidService()

    with pytest.raises(ValueError, match="prptDivCd"):
        service.list_real_estate({})


def test_onbid_results_reject_future_end_date():
    service = OnbidService()

    with pytest.raises(ValueError, match="오늘 이후"):
        service.list_bid_results({
            "cltrTypeCd": "01",
            "prptDivCd": "01",
            "opbdDtStart": "20261001",
            "opbdDtEnd": "29991231",
        })


def test_onbid_notice_query_allows_future_bid_window():
    OnbidService._validate_date_range({
        "opbdDtStart": "20261001",
        "opbdDtEnd": "29991231",
    }, allow_future_end=True)


def test_onbid_service_calls_documented_operation_with_server_side_key(monkeypatch):
    requested = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"response": {"body": {"items": {"item": []}}}}

    class FakeClient:
        def get(self, url, params, timeout):
            requested.update(url=url, params=params, timeout=timeout)
            return FakeResponse()

    monkeypatch.setattr(
        onbid_module,
        "API",
        replace(onbid_module.API, onbid_enabled=True, onbid_api_key="server-only-test-key"),
    )
    service = OnbidService(client=FakeClient())
    service.list_real_estate({"prptDivCd": "01", "pvctTrgtYn": "N"})

    assert requested["url"].endswith("/OnbidRlstListSrvc2/getRlstCltrList2")
    assert requested["params"]["serviceKey"] == "server-only-test-key"
    assert requested["params"]["prptDivCd"] == "01"
    assert requested["params"]["_type"] == "json"


def test_integrated_search_preserves_existing_real_estate_service(monkeypatch):
    monkeypatch.setattr(main, "load_properties", lambda **kwargs: ([{"name": "테스트 아파트", "area": 84, "price": 100000}], "mocked-official-source"))
    monkeypatch.setattr(intelligence_router, "save_source_records", lambda *args: 0)

    response = client.get("/api/v1/search", params={"lawd_cd": "11440", "deal_ymd": "202609"})

    assert response.status_code == 200
    data = response.json()
    assert data["items"][0]["source"] == "real_estate"
    assert data["items"][0]["name"] == "테스트 아파트"
    assert data["sources"]["court_auction"]["configured"] is False
