# 집찾기 허브

부동산 실거래·매물과 법원 경매 정보를 한눈에 보는 FastAPI 대시보드입니다. 국토교통부 실거래 API 응답만 사용하고, 검색어·검색 결과·자유게시판 글을 MongoDB에 저장할 수 있습니다. API 미설정 시에는 샘플 데이터를 만들지 않고 빈 결과를 표시합니다.

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

## Cloudflare 정적 배포

이 프로젝트의 정적 화면은 `app/static`에 있습니다. 저장소 루트의 `wrangler.toml`이 이 디렉터리를 자산 전용 Cloudflare 배포 대상으로 지정하므로 Cloudflare Pages/Workers에서 `npx wrangler deploy`를 실행할 수 있습니다. 자산 전용 배포에서는 `binding`을 설정하지 않습니다.

Cloudflare 정적 주소에는 FastAPI 라우트(`/api/regions`, `/api/dashboard` 등)가 존재하지 않습니다. 따라서 FastAPI를 Render, Railway, Fly.io 또는 별도 서버에 배포한 뒤 `app/static/api-config.js`의 `window.REAL_ESTATE_API_URL`에 그 주소를 입력해야 합니다.

### Render 환경 변수

Render의 Web Service 설정에서 프로젝트 루트 디렉터리를 `real_estate_hub`로 지정하고, 빌드 명령 `pip install -r requirements.txt`, 시작 명령 `uvicorn app.main:app --host 0.0.0.0 --port $PORT`를 사용합니다. 로컬 `.env` 파일은 Render에 자동 복사되지 않으므로 Render 대시보드의 Environment에 필요한 값을 별도로 등록하세요.

- 필수: `DATA_GO_KR_KEY` (실거래 API)
- 지도 표시: `GOOGLE_MAPS_API_KEY` (Maps JavaScript API를 활성화하고 Cloudflare 사이트 referrer 제한 설정)
- 게시판 저장: `MONGODB_URI` (MongoDB Atlas 연결 문자열)
- 주소 검색·GPS 주소 확인: `KAKAO_REST_API_KEY` 또는 Google 지오코딩이 활성화된 `GOOGLE_MAPS_API_KEY`
- 선택: `AUCTION_API_URL` 또는 `ONBID_BID_RESULT_API_URL`

### PROPERTY INTELLIGENCE 확장

기존 화면과 API를 유지하면서 `/intelligence` 및 `/api/v1/*`에 통합검색·온비드 API 어댑터를 추가했습니다. 온비드는 코드의 API 키가 아니라 Render 환경변수에서 설정하며, 기본적으로 비활성화되어 있습니다.

- 온비드 상품별 활용 신청 후 `ONBID_API_KEY`와 `ONBID_ENABLED=true` 설정
- 키를 별도로 지정하지 않으면 기존 `DATA_GO_KR_KEY`를 사용할 수 있지만, `ONBID_ENABLED=true` 전에는 외부 호출하지 않습니다.
- 부동산 목록은 공식 명세의 `prptDivCd`, `pvctTrgtYn` 조건이 필요합니다. 잘 모르는 코드값은 넣지 말고 온비드 상품 가이드를 확인하세요.
- 법원 데이터는 사법정보공유포털의 이용권한과 경매 상세 제공 범위가 확인되기 전 비활성화되어 있습니다. 법원 사이트 크롤링은 하지 않습니다.
- 신규 저장소는 `onbid_items`, `onbid_notices`, `onbid_bid_information`, `onbid_bid_results`, `court_auction`, `court_auction_events`, `real_estate_transactions`로 분리되며 기존 검색·게시판 컬렉션은 변경하지 않습니다.
- `GET /api/v1/sources`에서 각 공급자의 설정 상태, `GET /api/v1/search`에서 실거래와 설정된 온비드 결과를 확인할 수 있습니다.
- 실거래 API의 현재 데이터에 좌표가 없으면 지도 마커로 표시하지 않습니다. 주소 좌표 보강은 결과 출처를 구분해 후속 연결해야 합니다.

배포 후 `https://<Render 서비스 주소>/api/health`의 `api` 상태를 확인하세요. `satellite_map`이 `false`이면 Render의 `GOOGLE_MAPS_API_KEY` 설정/재배포를 확인하고, `transaction_api`가 `false`이면 `DATA_GO_KR_KEY`를 확인합니다.

예:

```javascript
window.REAL_ESTATE_API_URL = "https://your-fastapi-service.example.com";
```

배포 후 브라우저 개발자 도구에 `/api/map-config` 또는 `/api/regions` 404가 보이면
FastAPI가 아니라 Cloudflare 정적 자산 주소로 API를 호출하고 있는 상태입니다.
`app/static/api-config.js`의 `REAL_ESTATE_API_URL`을 실제 FastAPI HTTPS 주소로 바꾸고
다시 배포하세요. FastAPI 서버에는 `/api/map-config`, `/api/regions`, `/api/dashboard`가
모두 있어야 하며, 정적 사이트 도메인을 CORS 허용 목록에 추가해야 합니다.

지도만 별도 정적 배포에서 표시해야 하고 FastAPI의 `/api/map-config`를 호출할 수 없다면,
`api-config.js`에 HTTP referrer 제한을 건 공개 Google Maps 키를 설정할 수 있습니다.
그래도 실거래·검색 API를 사용하려면 `REAL_ESTATE_API_URL`은 반드시 필요합니다.

FastAPI에는 Cloudflare 정적 도메인에서 호출할 수 있도록 CORS를 활성화했습니다. 운영 배포에서는 필요하면 `allow_origins`를 실제 Cloudflare 도메인으로 제한하세요.

> 주의: Cloudflare 정적 배포는 HTML/CSS/JavaScript 화면만 배포합니다. FastAPI와 Python API는 별도 서버에 배포해야 하며, 정적 화면의 API 주소를 운영 서버 주소로 설정하는 작업이 추가로 필요합니다.

## 무료 API 연결 위치

- `app/api_config.py`: 모든 키·URL·타임아웃을 한곳에서 관리합니다.
- `.env`: `GOOGLE_MAPS_API_KEY`에 Google Maps JavaScript API 키를 입력하면 건물·장소 라벨이 포함된 하이브리드 지도가 표시됩니다. 지도의 확대 수준과 Google 지도 데이터에 따라 라벨 표시 여부가 달라집니다.
- `.env`: `DATA_GO_KR_KEY`에 공공데이터포털 일반 인증키를 입력합니다.
- `.env`: `DEFAULT_LAWD_CD`에 시군구 법정동 코드 5자리, `DEFAULT_DEAL_YMD`에 조회 년월(YYYYMM)을 입력합니다. 예: 마포구 `11440`, 2026년 9월 `202609`.
- `app/main.py`의 `fetch_official_data()`와 `_parse_transactions()`가 국토교통부 아파트 매매 실거래가 API 호출·변환을 담당합니다.
- `.env`: `MONGODB_URI`에 MongoDB Atlas 연결 문자열을 입력합니다. 저장 컬렉션은 `search_logs`, `property_search_counts`, `community_posts`입니다.
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

지도는 하이브리드 레이어(위성사진+지도 라벨)로 표시됩니다. GPS로 현재 위치의 주소와 동을 확인하고, 주소·건물 이름 검색 결과는 지도 중심 이동과 핀으로 연결됩니다. 주소 검색/GPS 주소 변환은 카카오 REST 키를 우선 사용하고, Google Maps 키가 있으면 대체 경로로 사용할 수 있습니다. Google 키가 없거나 지도 인증에 실패하면 OpenStreetMap 기본 지도를 표시합니다. 위성사진은 Google Maps 키가 필요하며, 브라우저에 전달되는 키에는 HTTP referrer 제한을 설정하세요.

## 가까운 곳 찾아보기

- 내 위치를 확인한 뒤 `학교`, `공원·놀이터`, `도서관`, `병원·약국`을 눌러 반경 1.5km 안의 장소를 찾습니다.
- `GET /api/nearby-places?lat=37.5665&lon=126.978&category=school`로 조회합니다. `category`는 `school`, `park`, `library`, `medical` 중 하나입니다.
- OpenStreetMap의 Overpass 데이터를 사용하며 별도 API 키는 필요하지 않습니다. 가까운 장소 최대 20곳을 거리순으로 보여주고, `지도 보기`로 해당 위치에 이동합니다.
- 데이터 등록 여부와 Overpass 서비스 상태에 따라 결과가 없거나 조회가 늦을 수 있습니다. 장소 정보는 공식 운영시간·안전 인증 정보가 아니므로 방문 전 확인이 필요합니다.

## 자유게시판

- 게시판 탭에서 별명·제목·내용을 등록하며 글은 MongoDB `community_posts` 컬렉션에 시간순으로 누적됩니다.
- `GET /api/community/posts`로 글을 읽고 `POST /api/community/posts`로 새 글을 등록합니다. DB가 설정되지 않으면 화면에 설정 안내가 표시됩니다.
- 현재 게시판은 로그인 없이 공개됩니다. 운영 배포 전에는 로그인·신고/삭제·스팸 방지 정책을 추가하고, 개인정보나 집 주소를 게시하지 않도록 이용자에게 안내하세요.

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
