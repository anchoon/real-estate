// Cloudflare 정적 배포에서는 반드시 배포된 FastAPI 주소를 입력하세요.
// 예: https://real-estate-api.example.com
// 로컬 실행은 빈 문자열 그대로 두면 현재 도메인의 /api를 사용합니다.
window.REAL_ESTATE_API_URL = "";

// 선택 사항: FastAPI의 /api/map-config를 사용할 수 없는 정적 배포에서만
// Google Maps JavaScript API용 공개 키를 입력하세요. HTTP referrer 제한을 꼭 설정하세요.
// window.REAL_ESTATE_MAPS_API_KEY = "AIza...";