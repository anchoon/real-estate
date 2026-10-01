from __future__ import annotations

import logging
from math import asin, cos, radians, sin, sqrt
from pathlib import Path
from typing import Any
from xml.etree import ElementTree

import httpx
from dotenv import load_dotenv
from urllib.parse import parse_qsl, unquote, urlencode, urlsplit, urlunsplit
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field

BASE_DIR = Path(__file__).resolve().parent
PROJECT_DIR = BASE_DIR.parent
load_dotenv(PROJECT_DIR / ".env")

try:
    # 패키지 실행: uvicorn app.main:app
    from .api_config import API, is_configured
except ImportError:
    # 파일 직접 실행: python app\main.py
    from api_config import API, is_configured

try:
    from .search_store import record_search, search_stats
except ImportError:
    from search_store import record_search, search_stats

try:
    from .community_store import create_post, list_posts
except ImportError:
    from community_store import create_post, list_posts

try:
    from .routers.intelligence import router as intelligence_router
except ImportError:
    from routers.intelligence import router as intelligence_router

app = FastAPI(
    title="집찾기 허브 API",
    description="공식·허가된 부동산 실거래와 경매 데이터를 한 화면에 제공하는 API",
    version="1.0.0",
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
app.include_router(intelligence_router)
logger = logging.getLogger(__name__)

REGIONS = [
    {"code": "11110", "name": "서울 종로구"}, {"code": "11140", "name": "서울 중구"},
    {"code": "11170", "name": "서울 용산구"}, {"code": "11200", "name": "서울 성동구"},
    {"code": "11215", "name": "서울 광진구"}, {"code": "11230", "name": "서울 동대문구"},
    {"code": "11260", "name": "서울 중랑구"}, {"code": "11290", "name": "서울 성북구"},
    {"code": "11305", "name": "서울 강북구"}, {"code": "11320", "name": "서울 도봉구"},
    {"code": "11350", "name": "서울 노원구"}, {"code": "11380", "name": "서울 은평구"},
    {"code": "11410", "name": "서울 서대문구"},
    {"code": "11680", "name": "서울 강남구"}, {"code": "11710", "name": "서울 송파구"},
    {"code": "11440", "name": "서울 마포구"},
    {"code": "11470", "name": "서울 양천구"}, {"code": "11500", "name": "서울 강서구"},
    {"code": "11530", "name": "서울 구로구"}, {"code": "11545", "name": "서울 금천구"},
    {"code": "11560", "name": "서울 영등포구"}, {"code": "11590", "name": "서울 동작구"},
    {"code": "11620", "name": "서울 관악구"}, {"code": "11650", "name": "서울 서초구"}, {"code": "11740", "name": "서울 강동구"},
    {"code": "41135", "name": "경기 성남시 분당구"},
    {"code": "41117", "name": "경기 수원시 영통구"}, {"code": "41360", "name": "경기 남양주시"},
    {"code": "28185", "name": "인천 연수구"}, {"code": "26110", "name": "부산 중구"},
    {"code": "26140", "name": "부산 서구"}, {"code": "26170", "name": "부산 동구"},
    {"code": "26200", "name": "부산 영도구"}, {"code": "26230", "name": "부산 부산진구"},
    {"code": "26260", "name": "부산 동래구"}, {"code": "26290", "name": "부산 남구"},
    {"code": "26320", "name": "부산 북구"}, {"code": "26350", "name": "부산 해운대구"},
    {"code": "26380", "name": "부산 사하구"}, {"code": "26410", "name": "부산 금정구"},
    {"code": "26440", "name": "부산 강서구"}, {"code": "26470", "name": "부산 연제구"},
    {"code": "26500", "name": "부산 수영구"}, {"code": "26530", "name": "부산 사상구"},
    {"code": "26710", "name": "부산 기장군"}, {"code": "30200", "name": "대전 유성구"},
    {"code": "36110", "name": "세종시"}, {"code": "27110", "name": "대구 중구"},
    {"code": "29110", "name": "광주 동구"}, {"code": "47110", "name": "경북 포항시"},
    {"code": "48120", "name": "경남 창원시"},
]
SEOUL_CODES = ["11110", "11140", "11170", "11200", "11215", "11230", "11260", "11290", "11305", "11320", "11350", "11380", "11410", "11440", "11470", "11500", "11530", "11545", "11560", "11590", "11620", "11650", "11680", "11710", "11740"]
SEOUL_DISTRICTS = {item["code"]: item["name"].replace("서울 ", "") for item in REGIONS if item["code"] in SEOUL_CODES}
SIDO_NAMES = {"SEOUL": "서울특별시", "BUSAN": "부산광역시", "DAEGU": "대구광역시", "INCHEON": "인천광역시", "GWANGJU": "광주광역시", "DAEJEON": "대전광역시", "ULSAN": "울산광역시", "SEJONG": "세종특별자치시", "GYEONGGI": "경기도", "GANGWON": "강원특별자치도", "CHUNGBUK": "충청북도", "CHUNGNAM": "충청남도", "JEONBUK": "전북특별자치도", "JEONNAM": "전라남도", "GYEONGBUK": "경상북도", "GYEONGNAM": "경상남도", "JEJU": "제주특별자치도"}
SIDO_ALIASES = {"서울": "SEOUL", "부산": "BUSAN", "대구": "DAEGU", "인천": "INCHEON", "광주": "GWANGJU", "대전": "DAEJEON", "울산": "ULSAN", "세종": "SEJONG", "경기": "GYEONGGI", "강원": "GANGWON", "충북": "CHUNGBUK", "충남": "CHUNGNAM", "전북": "JEONBUK", "전남": "JEONNAM", "경북": "GYEONGBUK", "경남": "GYEONGNAM", "제주": "JEJU"}
SIDO_PREFIXES = {"GYEONGGI": "41", "INCHEON": "28", "BUSAN": "26", "DAEJEON": "30", "SEJONG": "36", "DAEGU": "27", "GWANGJU": "29", "GYEONGBUK": "47", "GYEONGNAM": "48"}
SIDO_CODES = {"SEOUL": SEOUL_CODES}
for sido_code, prefix in SIDO_PREFIXES.items():
    SIDO_CODES[sido_code] = [item["code"] for item in REGIONS if item["code"].startswith(prefix)]

def _filter(items: list[dict[str, Any]], search: str | None) -> list[dict[str, Any]]:
    if not search:
        return items
    keyword = search.lower()
    return [item for item in items if keyword in " ".join(map(str, item.values())).lower()]


def _location_codes(value: str | None, search: str | None = None) -> list[str]:
    if value in SIDO_CODES:
        return SIDO_CODES[value]
    if value in SIDO_NAMES:
        return []
    if value:
        return [value]
    if search:
        for alias, sido_code in SIDO_ALIASES.items():
            if alias in search:
                return SIDO_CODES.get(sido_code, [])
    return [API.lawd_cd]


def _number(value: Any) -> int:
    try:
        return int(str(value).replace(",", "").replace(" ", ""))
    except (TypeError, ValueError):
        return 0


def _decimal(value: Any) -> float:
    try:
        return float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        return 0.0


def _api_items(payload: Any) -> list[dict[str, Any]]:
    """공공데이터포털 JSON의 표준 response.body.items.item을 목록으로 꺼냅니다."""
    try:
        items_container = payload["response"]["body"]["items"]
        if not isinstance(items_container, dict):
            return []
        items = items_container.get("item", [])
        return items if isinstance(items, list) else [items]
    except (KeyError, TypeError):
        return []


def _parse_transactions(payload: Any) -> list[dict[str, Any]]:
    parsed = []
    for index, item in enumerate(_api_items(payload), start=1):
        deal_amount = _number(item.get("dealAmount"))
        parsed.append({
            "id": f"api-{item.get('aptNm', 'unknown')}-{item.get('dealYear', '')}-{index}",
            "name": item.get("aptNm") or "단지명 미제공",
            "region": f"{item.get('sggNm', '')} {item.get('umdNm', '')}".strip() or "지역 미제공",
            "address": f"{item.get('estateAgentSggNm', item.get('sggNm', ''))} {item.get('umdNm', '')} {item.get('roadNm', '')} {item.get('roadNmBonbun', '')}".strip(),
            "sido": "서울" if str(item.get("sggCd", "")).startswith("11") else "기타",
            "district": item.get("sggNm") or SEOUL_DISTRICTS.get(str(item.get("sggCd")), "관할구 미제공"),
            "neighborhood": item.get("umdNm") or "지역 미제공",
            "type": "아파트",
            "deal": "매매",
            "price": deal_amount,
            "area": _decimal(item.get("excluUseAr")),
            "floor": f"{item.get('floor', '-')}층",
            "date": f"{item.get('dealYear', '')}.{item.get('dealMonth', '')}.{item.get('dealDay', '')}",
            "badge": "공공데이터",
        })
    return parsed


def _parse_auctions(payload: Any) -> list[dict[str, Any]]:
    """경매 API의 흔한 한글/영문 필드명을 화면 모델로 정규화합니다."""
    parsed = []
    for index, item in enumerate(_api_items(payload), start=1):
        get = lambda *names: next((item[name] for name in names if item.get(name) not in (None, "")), "")
        appraisal = _number(get("appraisal", "감정가", "감정평가액"))
        minimum = _number(get("minimum", "최저입찰가", "최저매각가격", "최저가"))
        parsed.append({
            "id": f"auction-api-{index}",
            "title": get("title", "물건명", "사건명", "물건소재지") or "경매 물건",
            "court": get("court", "법원명", "관할법원") or "법원 미제공",
            "status": get("status", "진행상태", "매각상태") or "상태 미제공",
            "appraisal": appraisal,
            "minimum": minimum,
            "discount": round((1 - minimum / appraisal) * 100) if appraisal and minimum else 0,
            "date": get("date", "입찰일", "매각기일") or "일자 미제공",
            "area": _decimal(get("area", "면적", "전용면적")),
        })
    return parsed


def load_properties(search: str | None = None, lawd_cd: str | None = None, deal_ymd: str | None = None, dong: str | None = None) -> tuple[list[dict[str, Any]], str]:
    """국토교통부 API 결과만 사용하며, 실패 시 빈 결과를 반환합니다."""
    if not API.data_go_kr_key:
        return [], "api-key-missing"
    try:
        codes = _location_codes(lawd_cd, search)
        if lawd_cd in SIDO_NAMES and not codes:
            return [], f"{SIDO_NAMES[lawd_cd]} 지역 코드 준비 필요"
        items = []
        for code in codes:
            try:
                payload = fetch_official_data(API.transaction_url, {"LAWD_CD": code, "DEAL_YMD": deal_ymd or API.deal_ymd})
                items.extend(_parse_transactions(payload))
            except (httpx.HTTPError, ValueError, KeyError):
                continue
        if dong:
            items = [item for item in items if item.get("neighborhood") == dong]
        return _filter(items, search), "국토교통부 실거래 API"
    except (httpx.HTTPError, ValueError, KeyError):
        return [], "api-error"


def load_auctions(search: str | None = None) -> tuple[list[dict[str, Any]], str]:
    if not API.data_go_kr_key or not API.auction_url:
        return [], "api-not-configured"
    try:
        # 온비드/공공데이터포털 공통 페이지 파라미터입니다.
        # 상품 명세에서 이름이 다르면 이 부분만 해당 명세에 맞게 조정합니다.
        payload = fetch_official_data(API.auction_url, {"pageNo": 1, "numOfRows": 100})
        return _filter(_parse_auctions(payload), search), "경매 공공 API"
    except (httpx.HTTPError, ValueError, KeyError):
        return [], "api-error"


def _group_average(items: list[dict[str, Any]], key: str) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for item in items:
        groups.setdefault(str(item.get(key) or "미제공"), []).append(item)
    return [
        {
            "name": name,
            "count": len(rows),
            "average_price": round(sum(row["price"] for row in rows) / len(rows)),
            "min_price": min(row["price"] for row in rows),
            "max_price": max(row["price"] for row in rows),
        }
        for name, rows in sorted(groups.items(), key=lambda group: len(group[1]), reverse=True)
    ]


def build_summary(items: list[dict[str, Any]]) -> dict[str, Any]:
    return {
        "total_count": len(items),
        "regions": _group_average(items, "neighborhood"),
        "districts": _group_average(items, "district"),
        "apartments": _group_average(items, "name"),
    }


def load_news(query: str = "부동산") -> list[dict[str, str]]:
    if not API.news_rss_url:
        return []
    try:
        parts = urlsplit(API.news_rss_url)
        params = dict(parse_qsl(parts.query, keep_blank_values=True))
        if "q" in params:
            params["q"] = query
        url = urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(params), parts.fragment))
        response = httpx.get(url, timeout=API.timeout_seconds, headers={"User-Agent": "real-estate-hub/1.0"})
        response.raise_for_status()
        root = ElementTree.fromstring(response.content)
        return [
            {"title": item.findtext("title", ""), "link": item.findtext("link", ""), "date": item.findtext("pubDate", "")}
            for item in root.findall(".//item")[:6]
        ]
    except (httpx.HTTPError, ElementTree.ParseError, ValueError):
        return []


def reverse_geocode(lat: float, lon: float) -> dict[str, str] | None:
    """좌표의 도로명/건물명과 국토부 조회에 필요한 시군구 코드를 얻습니다."""
    if API.kakao_rest_api_key:
        response = httpx.get("https://dapi.kakao.com/v2/local/geo/coord2regioncode.json", params={"x": lon, "y": lat}, headers={"Authorization": f"KakaoAK {API.kakao_rest_api_key}"}, timeout=API.timeout_seconds)
        if response.status_code not in {401, 403}:
            response.raise_for_status()
            documents = response.json().get("documents", [])
            if documents:
                item = next((doc for doc in documents if doc.get("region_type") == "H"), documents[0])
                address = item.get("address_name", "")
                building = "" 
                detail = httpx.get("https://dapi.kakao.com/v2/local/geo/coord2address.json", params={"x": lon, "y": lat}, headers={"Authorization": f"KakaoAK {API.kakao_rest_api_key}"}, timeout=API.timeout_seconds)
                if detail.status_code not in {401, 403}:
                    detail.raise_for_status()
                    docs = detail.json().get("documents", [])
                    if docs:
                        road = docs[0].get("road_address") or {}
                        building = road.get("building_name", "")
                        address = road.get("address_name") or docs[0].get("address", {}).get("address_name") or address
                return {"code": item.get("code", "")[:5], "name": address, "address": address, "building_name": building, "sido": item.get("region_1depth_name", ""), "district": item.get("region_2depth_name", ""), "dong": item.get("region_3depth_name", "")}
    if not API.google_maps_api_key:
        return None
    response = httpx.get("https://maps.googleapis.com/maps/api/geocode/json", params={"latlng": f"{lat},{lon}", "language": "ko", "key": API.google_maps_api_key}, timeout=API.timeout_seconds)
    response.raise_for_status()
    payload = response.json()
    if payload.get("status") != "OK" or not payload.get("results"):
        return None
    components = payload["results"][0].get("address_components", [])
    find = lambda kind: next((part["long_name"] for part in components if kind in part.get("types", [])), "")
    sido, district, dong = find("administrative_area_level_1"), find("administrative_area_level_2"), find("administrative_area_level_3")
    district_code = next((item["code"] for item in REGIONS if district in item["name"]), "")
    address = payload["results"][0].get("formatted_address", "")
    return {"code": district_code, "name": address, "address": address, "building_name": "", "sido": sido, "district": district, "dong": dong}


def geocode_address(query: str) -> dict[str, Any] | None:
    """카카오 또는 Google 공식 지오코딩 API로 주소/장소를 좌표로 변환합니다."""
    if API.kakao_rest_api_key:
        headers = {"Authorization": f"KakaoAK {API.kakao_rest_api_key}"}
        for endpoint in ("search/address.json", "search/keyword.json"):
            response = httpx.get(f"https://dapi.kakao.com/v2/local/{endpoint}", params={"query": query}, headers=headers, timeout=API.timeout_seconds)
            if response.status_code in {401, 403}:
                break
            response.raise_for_status()
            documents = response.json().get("documents", [])
            if documents:
                item = documents[0]
                address = item.get("address") or item.get("road_address") or {}
                road = item.get("road_address") or {}
                return {"lat": float(item.get("y") or address.get("y")), "lon": float(item.get("x") or address.get("x")), "name": item.get("place_name") or road.get("building_name") or query, "address": road.get("address_name") or address.get("address_name") or item.get("address_name") or query, "building_name": road.get("building_name", "")}
    if API.google_maps_api_key:
        response = httpx.get("https://maps.googleapis.com/maps/api/geocode/json", params={"address": query, "language": "ko", "key": API.google_maps_api_key}, timeout=API.timeout_seconds)
        response.raise_for_status()
        payload = response.json()
        if payload.get("status") == "OK" and payload.get("results"):
            item = payload["results"][0]
            point = item["geometry"]["location"]
            return {"lat": point["lat"], "lon": point["lng"], "name": item.get("formatted_address", query), "address": item.get("formatted_address", query), "building_name": ""}
    return None


@app.get("/api/nearby")
def nearby(
    lat: float = Query(ge=-90, le=90, description="GPS 위도"),
    lon: float = Query(ge=-180, le=180, description="GPS 경도"),
    deal_ymd: str | None = Query(default=None, min_length=6, max_length=6),
) -> dict[str, Any]:
    try:
        location = reverse_geocode(lat, lon)
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        location = None
    items: list[dict[str, Any]] = []
    source = "GPS 좌표 확인됨 · 주소 변환 API 설정 필요"
    if location:
        source = "GPS 주소 확인됨"
        if location.get("code") and API.data_go_kr_key:
            items, transaction_source = load_properties(lawd_cd=location["code"], deal_ymd=deal_ymd, dong=location.get("dong") or None)
            source = f"{location.get('name') or '현재 위치'} · {transaction_source}"
    return {
        "items": items,
        "count": len(items),
        "source": source,
        "location": location,
        "coordinates": {"lat": lat, "lon": lon},
        "nearby_dongs": [location["dong"]] if location and location.get("dong") else [],
    }


PLACE_CATEGORIES = {
    "school": {"tag": "amenity", "values": "school|kindergarten", "label": "학교·유치원"},
    "park": {"tag": "leisure", "values": "park|playground", "label": "공원·놀이터"},
    "library": {"tag": "amenity", "values": "library", "label": "도서관"},
    "medical": {"tag": "amenity", "values": "hospital|clinic|doctors|pharmacy", "label": "병원·약국"},
}
OVERPASS_ENDPOINTS = (
    "https://overpass-api.de/api/interpreter",
    "https://overpass.kumi.systems/api/interpreter",
    "https://overpass.private.coffee/api/interpreter",
)
 

def _distance_meters(lat1: float, lon1: float, lat2: float, lon2: float) -> int:
    """두 좌표 사이의 거리를 미터로 계산합니다."""
    lat_delta = radians(lat2 - lat1)
    lon_delta = radians(lon2 - lon1)
    value = sin(lat_delta / 2) ** 2 + cos(radians(lat1)) * cos(radians(lat2)) * sin(lon_delta / 2) ** 2
    return round(6_371_000 * 2 * asin(sqrt(min(1.0, value))))


def _parse_nearby_places(payload: Any, lat: float, lon: float, category: str) -> list[dict[str, Any]]:
    """Overpass 응답을 화면에 표시할 이름·좌표·거리로 정리합니다."""
    category_info = PLACE_CATEGORIES[category]
    places = []
    for element in payload.get("elements", []):
        tags = element.get("tags") or {}
        point = element if "lat" in element and "lon" in element else element.get("center") or {}
        if "lat" not in point or "lon" not in point:
            continue
        place_lat, place_lon = float(point["lat"]), float(point["lon"])
        address = " ".join(filter(None, (
            tags.get("addr:city") or tags.get("addr:district"),
            tags.get("addr:street"),
            tags.get("addr:housenumber"),
        )))
        places.append({
            "id": f"{element.get('type', 'place')}-{element.get('id', len(places))}",
            "name": tags.get("name") or f"이름이 등록되지 않은 {category_info['label']}",
            "category": category_info["label"],
            "lat": place_lat,
            "lon": place_lon,
            "distance_m": _distance_meters(lat, lon, place_lat, place_lon),
            "address": address,
        })
    return sorted(places, key=lambda place: place["distance_m"])[:20]


@app.get("/api/nearby-places")
def nearby_places(
    lat: float = Query(ge=-90, le=90, description="GPS 위도"),
    lon: float = Query(ge=-180, le=180, description="GPS 경도"),
    category: str = Query(default="school", description="school, park, library, medical 중 하나"),
) -> dict[str, Any]:
    if category not in PLACE_CATEGORIES:
        raise HTTPException(status_code=422, detail="지원하지 않는 장소 종류입니다.")
    radius_m = 1500
    category_info = PLACE_CATEGORIES[category]
    clauses = "\n".join(
        f'{element}(around:{radius_m},{lat},{lon})["{category_info["tag"]}"~"{category_info["values"]}"];'
        for element in ("node", "way", "relation")
    )
    query = f"[out:json][timeout:15];({clauses});out center 60;"
    items = None
    for endpoint in OVERPASS_ENDPOINTS:
        try:
            response = httpx.post(
                endpoint,
                data={"data": query},
                headers={"User-Agent": "real-estate-hub/1.0 (nearby places)"},
                timeout=max(API.timeout_seconds, 15),
            )
            response.raise_for_status()
            items = _parse_nearby_places(response.json(), lat, lon, category)
            break
        except (httpx.HTTPError, ValueError, KeyError, TypeError) as exc:
            logger.warning("Overpass 요청 실패 (%s): %s", endpoint, exc)
    if items is None:
        raise HTTPException(status_code=502, detail="주변 장소를 불러오지 못했어요. 잠시 후 다시 시도해 주세요.") from None
    return {
        "items": items,
        "count": len(items),
        "category": category,
        "radius_m": radius_m,
        "source": "OpenStreetMap 기여자 데이터",
    }


@app.get("/api/geocode")
def geocode(q: str = Query(min_length=2, max_length=100, description="주소 또는 건물명")) -> dict[str, Any]:
    try:
        location = geocode_address(q.strip())
    except (httpx.HTTPError, ValueError, KeyError, TypeError):
        location = None
    if not location:
        raise HTTPException(status_code=404, detail="주소나 건물 위치를 찾지 못했습니다. 더 자세한 주소로 다시 검색해 주세요.")
    return {"location": location}


class CommunityPostInput(BaseModel):
    nickname: str = Field(default="익명", min_length=1, max_length=20)
    title: str = Field(min_length=1, max_length=80)
    content: str = Field(min_length=1, max_length=3000)


@app.get("/api/community/posts")
def community_posts(limit: int = Query(default=20, ge=1, le=50), skip: int = Query(default=0, ge=0)) -> dict[str, Any]:
    try:
        posts, count = list_posts(limit=limit, skip=skip)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="게시판 DB에 연결할 수 없습니다. MONGODB_URI 설정을 확인해 주세요.") from exc
    return {"items": posts, "count": count, "connected": True}


@app.post("/api/community/posts", status_code=201)
def add_community_post(post: CommunityPostInput) -> dict[str, Any]:
    nickname, title, content = post.nickname.strip(), post.title.strip(), post.content.strip()
    if not nickname or not title or not content:
        raise HTTPException(status_code=422, detail="이름, 제목, 내용을 입력해 주세요.")
    try:
        saved = create_post(nickname=nickname, title=title, content=content)
    except Exception as exc:
        raise HTTPException(status_code=503, detail="게시글을 저장하지 못했습니다. MongoDB 연결을 확인해 주세요.") from exc
    return {"item": saved, "connected": True}


@app.get("/", include_in_schema=False)
def home() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "index.html")
 

@app.get("/intelligence", include_in_schema=False)
def property_intelligence() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "intelligence.html")

  
@app.get("/styles.css", include_in_schema=False)
def styles() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "styles.css", media_type="text/css")


@app.get("/app.js", include_in_schema=False)
def javascript() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "app.js", media_type="application/javascript")


@app.get("/api-config.js", include_in_schema=False)
def api_config_script() -> FileResponse:
    return FileResponse(BASE_DIR / "static" / "api-config.js", media_type="application/javascript")


@app.get("/api/dashboard")
def dashboard(
    lawd_cd: str | None = Query(default=None, min_length=5, max_length=10, description="시군구 법정동코드 또는 전국"),
    deal_ymd: str | None = Query(default=None, min_length=6, max_length=6, description="계약년월 YYYYMM"),
    search: str | None = Query(default=None, description="단지·동·구 검색"),
    dong: str | None = Query(default=None, description="읍면동"),
) -> dict[str, Any]:
    properties, source = load_properties(search=search, lawd_cd=lawd_cd, deal_ymd=deal_ymd, dong=dong)
    auctions, auction_source = load_auctions()
    return {"properties": properties, "auctions": auctions, "summary": build_summary(properties), "api": is_configured(), "mode": source, "auction_source": auction_source}


@app.get("/api/properties")
def properties(search: str | None = Query(default=None, description="단지·주소·지역"), deal: str | None = None) -> dict[str, Any]:
    items, source = load_properties(search)
    if deal:
        items = [item for item in items if item["deal"] == deal]
    return {"items": items, "count": len(items), "source": source}


@app.get("/api/regions")
def regions() -> dict[str, Any]:
    sidos = [{"code": "", "name": "지역 선택"}]
    sidos.extend({"code": code, "name": name} for code, name in SIDO_NAMES.items())
    return {"sidos": sidos, "districts": [{"code": item["code"], "name": item["name"]} for item in REGIONS]}


@app.get("/api/search")
def search(
    q: str = Query(min_length=1, description="검색어"),
    lawd_cd: str | None = Query(default=None, min_length=5, max_length=10),
    deal_ymd: str | None = Query(default=None, min_length=6, max_length=6),
    dong: str | None = Query(default=None),
) -> dict[str, Any]:
    properties, source = load_properties(q, lawd_cd, deal_ymd, dong)
    auctions, auction_source = load_auctions(q)
    saved = record_search(q, properties)
    return {"properties": properties, "auctions": auctions, "summary": build_summary(properties), "source": source, "auction_source": auction_source, "api": is_configured(), "recorded": saved, "stats": search_stats()}


@app.get("/api/search-stats")
def get_search_stats() -> dict[str, Any]:
    return search_stats()


@app.get("/api/news")
def news(q: str = Query(default="부동산", min_length=1)) -> dict[str, Any]:
    return {"items": load_news(q), "source": "공개 RSS"}


@app.get("/api/auctions")
def auctions(search: str | None = Query(default=None, description="물건·법원·지역"), max_minimum: int | None = Query(default=None, ge=0)) -> dict[str, Any]:
    items, source = load_auctions(search)
    if max_minimum is not None:
        items = [item for item in items if item["minimum"] <= max_minimum]
    return {"items": items, "count": len(items), "source": source}


@app.get("/api/health")
def health() -> dict[str, Any]:
    return {"status": "ok", "api": is_configured()}


@app.get("/api/map-config")
def map_config() -> dict[str, Any]:
    """프런트엔드 지도 로더에 공개 가능한 Google Maps 키만 전달합니다."""
    return {"provider": "google", "api_key": API.google_maps_api_key, "satellite": bool(API.google_maps_api_key)}


def fetch_official_data(url: str, params: dict[str, Any]) -> Any:
    """공식 API 호출 공통 함수. 실제 상품별 응답 파싱은 명세에 맞게 추가하세요."""
    if not API.data_go_kr_key or not url:
        return None
    # data.go.kr에서 복사한 인코딩 키(%2F, %3D)를 httpx가 이중 인코딩하지 않게 합니다.
    params = {**params, "serviceKey": unquote(API.data_go_kr_key), "_type": "json"}
    with httpx.Client(timeout=API.timeout_seconds) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()


if __name__ == "__main__":
    import uvicorn

    # 파일 직접 실행 시에는 현재 생성된 앱 객체를 사용해야 합니다.
    # 자동 재시작이 필요하면 프로젝트 루트에서 `uvicorn app.main:app --reload`를 사용하세요.
    uvicorn.run(app, host="127.0.0.1", port=8000)
