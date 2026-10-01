from fastapi.testclient import TestClient

import app.main as main
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


def test_nearby_returns_coordinates_without_calling_external_api(monkeypatch):
    monkeypatch.setattr(main, "reverse_geocode", lambda lat, lon: None)
    response = client.get("/api/nearby", params={"lat": 37.5665, "lon": 126.9780})
    assert response.status_code == 200
    assert "items" in response.json()


def test_map_config_is_safe_without_google_key():
    response = client.get("/api/map-config")
    assert response.status_code == 200
    assert response.json()["provider"] == "google"
    assert isinstance(response.json()["satellite"], bool)


def test_frontend_api_config_script_is_available():
    response = client.get("/api-config.js")
    assert response.status_code == 200
    assert "REAL_ESTATE_API_URL" in response.text


def test_news_returns_rss_items_and_replaces_query(monkeypatch):
    requested = {}

    class FakeResponse:
        content = b"<rss><channel><item><title>\xeb\xb6\x80\xeb\x8f\x99\xec\x82\xb0 \xeb\x89\xb4\xec\x8a\xa4</title><link>https://example.com/news</link><pubDate>today</pubDate></item></channel></rss>"

        def raise_for_status(self):
            return None

    def fake_get(url, **kwargs):
        requested["url"] = url
        return FakeResponse()

    monkeypatch.setattr(main.httpx, "get", fake_get)
    items = main.load_news("마포")

    assert items == [{"title": "부동산 뉴스", "link": "https://example.com/news", "date": "today"}]
    assert "q=%EB%A7%88%ED%8F%AC" in requested["url"]


def test_geocode_endpoint_returns_coordinates_for_a_found_address(monkeypatch):
    monkeypatch.setattr(main, "geocode_address", lambda query: {
        "lat": 37.55, "lon": 126.91, "name": "테스트 건물", "address": "서울 주소", "building_name": "테스트 건물"
    })

    response = client.get("/api/geocode", params={"q": "테스트 건물"})

    assert response.status_code == 200
    assert response.json()["location"]["building_name"] == "테스트 건물"
    assert response.json()["location"]["lat"] == 37.55


def test_nearby_includes_reverse_geocoded_address_and_transactions(monkeypatch):
    location = {"code": "11440", "name": "서울 마포구 아현동", "address": "서울 주소", "building_name": "우리 건물", "dong": "아현동"}
    monkeypatch.setattr(main, "reverse_geocode", lambda lat, lon: location)
    monkeypatch.setattr(main, "load_properties", lambda **kwargs: ([{"id": "p1"}], "국토교통부 실거래 API"))

    response = client.get("/api/nearby", params={"lat": 37.55, "lon": 126.91})

    assert response.status_code == 200
    assert response.json()["location"]["building_name"] == "우리 건물"
    assert response.json()["items"] == [{"id": "p1"}]
    assert response.json()["nearby_dongs"] == ["아현동"]


def test_community_posts_are_read_from_mongodb_store(monkeypatch):
    posts = [{"nickname": "동네친구", "title": "안녕하세요", "content": "반가워요", "created_at": "2026-10-01T00:00:00+00:00"}]
    monkeypatch.setattr(main, "list_posts", lambda limit, skip: (posts, 1))
    monkeypatch.setattr(main, "create_post", lambda **post: {**post, "created_at": "2026-10-01T00:00:00+00:00"})

    listed = client.get("/api/community/posts")
    created = client.post("/api/community/posts", json={"nickname": "동네친구", "title": "안녕하세요", "content": "반가워요"})

    assert listed.status_code == 200
    assert listed.json()["count"] == 1
    assert created.status_code == 201
    assert created.json()["item"]["title"] == "안녕하세요"


def test_community_post_rejects_blank_text():
    response = client.post("/api/community/posts", json={"nickname": "친구", "title": "   ", "content": "내용"})

    assert response.status_code == 422


def test_frontend_has_address_search_and_community_category():
    response = client.get("/")
    styles = client.get("/static/community.css")
    theme = client.get("/static/playful-theme.css")

    assert response.status_code == 200
    assert "자유게시판" in response.text
    assert "주소나 건물 이름" in response.text
    assert styles.status_code == 200
    assert "community-layout" in styles.text
    assert theme.status_code == 200
    assert "linear-gradient" in theme.text


def test_map_script_has_no_key_fallback_and_secure_location_message():
    script = client.get("/app.js")
    page = client.get("/")

    assert script.status_code == 200
    assert "function loadLeafletMap()" in script.text
    assert "tile.openstreetmap.org" in script.text
    assert "window.isSecureContext" in script.text
    assert "nearby-places-20261001" in page.text


def test_nearby_places_returns_sorted_openstreetmap_results(monkeypatch):
    request = {}

    class FakeResponse:
        def raise_for_status(self):
            return None

        def json(self):
            return {"elements": [
                {"type": "way", "id": 2, "center": {"lat": 37.58, "lon": 126.98}, "tags": {"name": "먼 유치원", "amenity": "kindergarten"}},
                {"type": "node", "id": 1, "lat": 37.567, "lon": 126.978, "tags": {"name": "가까운 학교", "amenity": "school", "addr:street": "꽃길"}},
                {"type": "way", "id": 3, "tags": {"name": "좌표 없는 학교", "amenity": "school"}},
            ]}

    def fake_post(url, **kwargs):
        request["url"] = url
        request["query"] = kwargs["data"]["data"]
        return FakeResponse()

    monkeypatch.setattr(main.httpx, "post", fake_post)
    response = client.get("/api/nearby-places", params={"lat": 37.5665, "lon": 126.978, "category": "school"})

    assert response.status_code == 200
    assert response.json()["items"][0]["name"] == "가까운 학교"
    assert response.json()["items"][0]["address"] == "꽃길"
    assert response.json()["items"][1]["name"] == "먼 유치원"
    assert response.json()["items"][0]["distance_m"] < response.json()["items"][1]["distance_m"]
    assert "amenity" in request["query"]
    assert request["url"].startswith("https://overpass-api.de/")


def test_nearby_places_rejects_unknown_category():
    response = client.get("/api/nearby-places", params={"lat": 37.5665, "lon": 126.978, "category": "mall"})

    assert response.status_code == 422


def test_page_exposes_nearby_place_categories():
    response = client.get("/")

    assert "data-place-category=\"school\"" in response.text
    assert "data-place-category=\"park\"" in response.text
    assert "data-place-category=\"library\"" in response.text
    assert "data-place-category=\"medical\"" in response.text
