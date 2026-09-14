from fastapi.testclient import TestClient

from app.main import _location_codes, _parse_transactions, build_summary, app

client = TestClient(app)


def test_dashboard_uses_configured_api_data():
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert data["mode"] in {"국토교통부 실거래 API", "api-key-missing", "api-error"}
    assert data["auctions"] == []


def test_property_search():
    response = client.get("/api/properties", params={"search": "마포"})
    assert response.status_code == 200
    assert response.json()["source"] in {"국토교통부 실거래 API", "api-key-missing", "api-error"}


def test_auction_price_filter():
    response = client.get("/api/auctions", params={"max_minimum": 150000})
    assert response.status_code == 200
    assert response.json()["items"] == []


def test_search_endpoint_returns_results_without_database():
    response = client.get("/api/search", params={"q": "마포"})
    assert response.status_code == 200
    assert isinstance(response.json()["properties"], list)
    assert isinstance(response.json()["recorded"], bool)


def test_api_transactions_are_grouped_by_region_district_and_apartment():
    payload = {
        "response": {"body": {"items": {"item": [
            {"aptNm": "테스트아파트", "sggNm": "마포구", "umdNm": "아현동", "dealAmount": "100,000", "excluUseAr": "84.9", "floor": "10", "dealYear": "2026", "dealMonth": "9", "dealDay": "1"},
            {"aptNm": "테스트아파트", "sggNm": "마포구", "umdNm": "아현동", "dealAmount": "120,000", "excluUseAr": "84.9", "floor": "11", "dealYear": "2026", "dealMonth": "9", "dealDay": "2"},
        ]}}}}
    items = _parse_transactions(payload)
    summary = build_summary(items)
    assert summary["total_count"] == 2
    assert summary["districts"][0]["name"] == "마포구"
    assert summary["districts"][0]["count"] == 2
    assert summary["apartments"][0]["average_price"] == 110000


def test_region_options_include_nationwide_and_sido_hierarchy():
    data = client.get("/api/regions").json()
    assert "NATIONWIDE" not in {item["code"] for item in data["sidos"]}
    assert {item["code"] for item in data["sidos"]} >= {"SEOUL", "BUSAN", "GYEONGGI", "JEJU"}
    assert len(data["sidos"]) == 18  # 지역 선택 + 대한민국 17개 시·도
    assert any(item["name"] == "서울 마포구" for item in data["districts"])


def test_city_search_expands_to_all_known_city_codes():
    assert len(_location_codes(None, "서울 아파트")) == 25
    assert len(_location_codes(None, "부산 아파트")) == 16


def test_nearby_requires_reverse_geocoding_key_without_calling_external_api():
    response = client.get("/api/nearby", params={"lat": 37.5665, "lon": 126.9780})
    assert response.status_code == 200
    assert "items" in response.json()


def test_map_config_is_safe_without_google_key():
    response = client.get("/api/map-config")
    assert response.status_code == 200
    assert response.json()["provider"] == "google"
    assert isinstance(response.json()["satellite"], bool)
