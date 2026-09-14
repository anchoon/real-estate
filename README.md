# 집찾기 허브

부동산 실거래·매물과 법원 경매 정보를 한눈에 보는 FastAPI 대시보드입니다. 국토교통부 실거래 API 응답만 사용하고, 검색어·검색 결과 아파트·검색 횟수를 MongoDB에 저장할 수 있습니다. API 미설정 시에는 샘플 데이터를 만들지 않고 빈 결과를 표시합니다.

## 실행

PowerShell에서 프로젝트 폴더로 이동해 실행합니다.

```powershell
cd "c:\PYTHON\CODING\Employee list\real_estate_hub"
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn app.main:app --reload
```

브라우저에서 `http://127.0.0.1:8000`을 엽니다. API 문서는 `/docs`입니다.

## 무료 API 연결 위치

- `app/api_config.py`: 모든 키·URL·타임아웃을 한곳에서 관리합니다.
- `.env`: `GOOGLE_MAPS_API_KEY`에 Google Maps JavaScript API 키를 입력하면 위성지도와 실거래 마커 오버레이가 활성화됩니다.
- `.env`: `DATA_GO_KR_KEY`에 공공데이터포털 일반 인증키를 입력합니다.
- `.env`: `DEFAULT_LAWD_CD`에 시군구 법정동 코드 5자리, `DEFAULT_DEAL_YMD`에 조회 년월(YYYYMM)을 입력합니다. 예: 마포구 `11440`, 2026년 9월 `202609`.
- `app/main.py`의 `fetch_official_data()`와 `_parse_transactions()`가 국토교통부 아파트 매매 실거래가 API 호출·변환을 담당합니다.
- `.env`: `MONGODB_URI`에 MongoDB Atlas 무료 M0 연결 문자열을 입력합니다. 저장 컬렉션은 `search_logs`, `property_search_counts`입니다.
- `.env`: `AUCTION_API_URL`에는 공공데이터포털에서 승인받은 경매 API URL을 입력합니다. 비워 두면 `ONBID_BID_RESULT_API_URL`을 자동 사용합니다. 경매 상품의 응답 필드가 상품마다 달라 `app/main.py`의 `_parse_auctions()`에서 일반적인 필드명을 변환합니다.

추천 검색어: 공공데이터포털에서 `국토교통부 아파트 매매 실거래가`, `법원 경매`, `부동산 경매`.

## API와 NoSQL 설정 순서

1. [공공데이터포털](https://www.data.go.kr/) 회원가입 → `국토교통부 아파트 매매 실거래가 자료` 활용신청 → 인증키 복사.
2. [MongoDB Atlas](https://www.mongodb.com/atlas/database) 무료 M0 클러스터 생성 → Database Access 사용자 생성 → Network Access에서 현재 IP 허용 → Connect의 Python 연결 문자열 복사.
3. 프로젝트 루트 `real_estate_hub/.env`에 각각 `DATA_GO_KR_KEY`, `MONGODB_URI`를 입력합니다. 비밀번호에 `@`, `#` 등이 있으면 URL 인코딩이 필요합니다.
4. `DEFAULT_LAWD_CD`와 `DEFAULT_DEAL_YMD`를 바꾸고 서버를 재시작합니다.

검색이 발생하면 `GET /api/search?q=마포`가 실행되고 `search_logs`에 검색 1건, 결과 아파트마다 `property_search_counts.search_count`가 누적됩니다. `GET /api/search-stats`에서 통계를 확인할 수 있습니다. 대시보드의 지역별·관할구별·아파트별 집계는 현재 API 응답 행에서 실시간 계산됩니다.

## 위성지도 오버레이

1. [Google Cloud Console](https://console.cloud.google.com/)에서 프로젝트를 만들고 `Maps JavaScript API`와 `Geocoding API`를 활성화합니다.
2. API 키를 만들고 웹사이트 제한에 `http://localhost:8000/*`, `http://127.0.0.1:8000/*`를 등록합니다.
3. `real_estate_hub/.env`에 입력합니다.

```env
GOOGLE_MAPS_API_KEY=발급받은_구글_지도_키
```

지도는 위성 레이어로 표시되고, 국토부 실거래 응답의 주소를 Google Geocoder로 변환해 거래 마커를 표시합니다. Google 키가 없으면 지도 외의 검색·실거래 기능은 계속 작동하며 지도에는 설정 안내가 표시됩니다. Google Maps 키는 브라우저에 전달되므로 반드시 HTTP referrer 제한을 설정하세요.

## 지역 조회 방식

- `시·도`: 현재 서울 전체 25개 시군구 코드를 지원합니다.
- `관할구`: 시·도에 맞는 시군구를 선택하고 해당 구의 실거래 API를 조회합니다.
- `동`: 관할구 조회 결과에서 실제 API가 반환한 읍면동을 option으로 만들고 다시 필터링합니다.
- 검색창에 `서울`, `마포구`, `아현동`, 아파트명을 입력하면 해당 단어가 시도·구·동·단지·도로명 등 API 응답 전체에서 검색됩니다.
- 전국 전체는 시군구 코드가 많아 `NATIONWIDE_LAWD_CODES`에 공공 법정동 코드 5자리를 쉼표로 등록한 뒤 `전국`을 선택합니다. API 호출량과 공공데이터포털 제공 한도를 고려해 조회 월을 좁혀 사용하세요.

> 네이버·카카오·민간 사이트는 웹페이지 자동 수집 대신 공식 API와 이용약관을 준수하세요. 경매 물건은 반드시 법원 원문과 등기부를 확인해야 하며 투자·법률 자문이 아닙니다.

## 테스트

```powershell
pytest
```
