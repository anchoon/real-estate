"""외부 API 설정을 한곳에서 관리합니다.

[사용 방법]
1. 프로젝트 루트의 .env.example을 .env로 복사합니다.
2. 공공데이터포털(data.go.kr)에서 발급받은 일반 인증키를 입력합니다.
3. 아래 URL/파라미터는 API 상품별 명세에 맞게 확인·수정합니다.

현재 키가 없거나 API가 응답하지 않으면 안전하게 샘플 데이터를 보여줍니다.
네이버·카카오 등 웹페이지를 무단 수집하지 않고 공식 API만 사용하세요.
"""

from dataclasses import dataclass
import os
from urllib.parse import unquote


def _env(name: str, default: str = "") -> str:
    value = os.getenv(name, default).strip()
    # .env.example 안내문이 실제 키로 오인되지 않도록 무효화합니다.
    if value.startswith("여기에_") or value.startswith("발급받은_"):
        return ""
    return value


def _transaction_endpoint(url: str) -> str:
    """공공데이터포털 서비스 기본 URL을 실제 호출 오퍼레이션 URL로 보정합니다."""
    url = url.rstrip("/")
    if url.endswith("/getRTMSDataSvcAptTrade") or url.endswith("/getRTMSDataSvcAptTradeDev"):
        return url
    if url.endswith("RTMSDataSvcAptTradeDev"):
        return f"{url}/getRTMSDataSvcAptTradeDev"
    if url.endswith("RTMSDataSvcAptTrade"):
        return f"{url}/getRTMSDataSvcAptTrade"
    return url


@dataclass(frozen=True)
class ApiConfig:
    # 무료 공공데이터 API 키: https://www.data.go.kr/
    data_go_kr_key: str = _env("DATA_GO_KR_KEY")

    # 국토교통부 아파트 매매 실거래가 API
    # 새 설정명(APT_TRADE_DETAIL_API_URL)을 우선 사용하고,
    # 기존 설정명(TRANSACTION_API_URL)도 호환합니다.
    transaction_url: str = _transaction_endpoint(_env(
        "APT_TRADE_DETAIL_API_URL",
        _env("TRANSACTION_API_URL", "https://apis.data.go.kr/1613000/RTMSDataSvcAptTradeDev"),
    ))

    transaction_basic_url: str = _env("APT_TRADE_API_URL")

    # 법원/공공데이터 경매 API URL을 발급받은 상품 명세로 교체하세요.
    # 공공데이터포털에서 '법원 경매', '부동산 경매'로 검색할 수 있습니다.
    # 실제 오퍼레이션 URL을 별도로 확인하기 전까지 온비드는 비활성화합니다.
    auction_url: str = _env("AUCTION_API_URL")

    # 실거래 조회 기본 지역코드(시군구 5자리)와 계약년월(YYYYMM)
    lawd_cd: str = _env("DEFAULT_LAWD_CD", "11440")
    deal_ymd: str = _env("DEFAULT_DEAL_YMD", "202609")

    # 전국 조회에 사용할 시군구 코드 목록. 실제 전국 조회가 필요하면
    # data.go.kr 법정동코드 기준으로 쉼표로 추가합니다.
    nationwide_lawd_codes: str = _env("NATIONWIDE_LAWD_CODES", "")

    # 오늘의 브리핑 뉴스: 공개 RSS 기본값 또는 승인받은 뉴스 API URL
    news_rss_url: str = _env("NEWS_RSS_URL", "https://news.google.com/rss/search?q=%EB%B6%80%EB%8F%99%EC%82%B0&hl=ko&gl=KR&ceid=KR:ko")

    # GPS 좌표를 시군구 코드로 바꾸는 카카오 로컬 REST API 키
    kakao_rest_api_key: str = _env("KAKAO_REST_API_KEY")

    # Google Maps JavaScript API 키: 위성지도 렌더링용
    google_maps_api_key: str = _env("GOOGLE_MAPS_API_KEY")

    # MongoDB Atlas 무료 M0 연결 문자열
    mongo_uri: str = _env("MONGODB_URI")
    mongo_database: str = _env("MONGODB_DATABASE", "real_estate_hub")

    timeout_seconds: float = float(os.getenv("API_TIMEOUT_SECONDS", "8"))


API = ApiConfig()


def is_configured() -> dict[str, bool]:
    return {
        "transaction_api": bool(API.data_go_kr_key),
        "auction_api": bool(API.data_go_kr_key and API.auction_url),
        "search_database": bool(API.mongo_uri),
        "gps_reverse_geocoding": bool(API.kakao_rest_api_key or API.google_maps_api_key),
        "satellite_map": bool(API.google_maps_api_key),
    }
