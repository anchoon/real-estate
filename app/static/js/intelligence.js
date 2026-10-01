const piEscape = value => String(value ?? '').replace(/[&<>"']/g, char => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[char]);
const piState = { items: [], filter: 'all', map: null, markers: [] };
const piApi = async (path, options) => {
  const response = await fetch(path, options);
  const data = await response.json();
  if (!response.ok) throw new Error(data.detail || `API ${response.status}`);
  return data;
};

function initPiMap() {
  if (!window.L) {
    document.querySelector('#map-note').textContent = '지도를 불러오지 못했습니다.';
    return;
  }
  piState.map = L.map('property-map', { scrollWheelZoom: false }).setView([37.5665, 126.978], 11);
  L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '&copy; OpenStreetMap contributors',
  }).addTo(piState.map);
}

function renderSources(sources) {
  const labels = { real_estate: '국토부 실거래', onbid: '온비드 공매', court_auction: '법원경매' };
  document.querySelector('#source-status').innerHTML = Object.entries(sources).map(([key, value]) => {
    const stateClass = value.configured ? 'ready' : 'pending';
    const stateLabel = value.configured ? '연결 설정됨' : 'API 발급·접근 확인 대기';
    const note = value.message || value.status || '';
    return `<div class="pi-source-row"><strong>${labels[key] || piEscape(key)}</strong><span class="${stateClass}" title="${piEscape(note)}">${stateLabel}</span></div>`;
  }).join('');
}

function renderResults() {
  const filtered = piState.filter === 'all' ? piState.items : piState.items.filter(item => item.source === piState.filter);
  document.querySelector('#result-count').textContent = `${filtered.length}건`;
  const list = document.querySelector('#result-list');
  if (!filtered.length) {
    list.innerHTML = '<p class="pi-empty">조건에 맞는 확인된 데이터가 없습니다. 미발급 API의 샘플 물건은 표시하지 않습니다.</p>';
  } else {
    list.innerHTML = filtered.map(item => {
      const source = item.source === 'real_estate' ? '실거래' : item.source === 'onbid' ? '온비드' : '법원경매';
      const raw = item.raw || item;
      const title = item.name || item.title || item.address || raw.cltrMngNo || '공식 응답 물건';
      const price = item.transaction_price ?? item.price ?? item.minimum_price;
      const area = item.area;
      const location = item.address || item.region || item.neighborhood || '주소 필드 확인 대기';
      const amount = Number.isFinite(Number(price)) ? `${Number(price).toLocaleString('ko-KR')}만원` : '가격 필드 확인 대기';
      const detailButton = item.source === 'onbid' && raw.cltrMngNo
        ? `<button class="pi-detail-button" type="button" data-onbid-detail="${piEscape(raw.cltrMngNo)}" data-condition-id="${piEscape(raw.pbctCdtnNo || '')}">공식 상세 조회</button><div data-detail-container="${piEscape(raw.cltrMngNo)}"></div>`
        : '';
      return `<article class="pi-item"><div class="pi-item-top"><h3>${piEscape(title)}</h3><span class="pi-tag">${source}</span></div><p>${piEscape(location)}</p><p>${area ? `${piEscape(area)}㎡ · ` : ''}${piEscape(amount)}</p>${detailButton}<details><summary>원본 응답 보기</summary><pre>${piEscape(JSON.stringify(raw, null, 2))}</pre></details></article>`;
    }).join('');
    list.querySelectorAll('[data-onbid-detail]').forEach(button => button.addEventListener('click', async () => {
      const itemId = button.dataset.onbidDetail;
      const conditionId = button.dataset.conditionId;
      const params = conditionId ? `?pbctCdtnNo=${encodeURIComponent(conditionId)}` : '';
      const container = list.querySelector(`[data-detail-container="${CSS.escape(itemId)}"]`);
      button.disabled = true;
      button.textContent = '공식 상세 조회 중…';
      try {
        const detail = await piApi(`/api/v1/onbid/items/${encodeURIComponent(itemId)}${params}`);
        container.innerHTML = `<details open><summary>온비드 상세 응답</summary><pre>${piEscape(JSON.stringify(detail.items || detail.raw_response || detail, null, 2))}</pre></details>`;
      } catch (error) {
        container.innerHTML = `<p class="pi-footnote">${piEscape(error.message)}</p>`;
      } finally {
        button.disabled = false;
        button.textContent = '공식 상세 조회';
      }
    }));
  }
  renderMarkers(filtered);
}

function renderMarkers(items) {
  if (!piState.map) return;
  piState.markers.forEach(marker => marker.remove());
  piState.markers = [];
  for (const item of items) {
    const lat = Number(item.latitude ?? item.lat);
    const lon = Number(item.longitude ?? item.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) continue;
    const marker = L.marker([lat, lon]).bindPopup(piEscape(item.name || item.title || item.address || '부동산 물건'));
    marker.addTo(piState.map);
    piState.markers.push(marker);
  }
  document.querySelector('#map-note').textContent = piState.markers.length ? `좌표가 확인된 물건 ${piState.markers.length}건` : '좌표가 제공된 결과만 표시 · 현재 좌표 결과 없음';
}

async function loadSourceStatus() {
  const data = await piApi('/api/v1/sources');
  renderSources(data.sources || {});
}

async function searchIntelligence(event) {
  event?.preventDefault();
  const params = new URLSearchParams();
  const query = document.querySelector('#query').value.trim();
  const lawdCode = document.querySelector('#lawd-code').value.trim();
  const month = document.querySelector('#deal-month').value.trim();
  const dong = document.querySelector('#dong').value.trim();
  const propertyCode = document.querySelector('#property-code').value.trim();
  const contractCode = document.querySelector('#private-contract-code').value.trim();
  if (query) params.set('q', query);
  if (lawdCode) params.set('lawd_cd', lawdCode);
  if (month) params.set('deal_ymd', month);
  if (dong) params.set('dong', dong);
  if (propertyCode) params.set('prptDivCd', propertyCode);
  if (contractCode) params.set('pvctTrgtYn', contractCode);
  const list = document.querySelector('#result-list');
  list.innerHTML = '<p class="pi-empty">공식 데이터 소스를 조회하고 있습니다…</p>';
  try {
    const data = await piApi(`/api/v1/search?${params.toString()}`);
    piState.items = data.items || [];
    renderSources(data.sources || {});
    renderResults();
  } catch (error) {
    list.innerHTML = `<p class="pi-empty">검색에 실패했습니다: ${piEscape(error.message)}</p>`;
  }
}

function activateFilter(button) {
  document.querySelectorAll('[data-filter]').forEach(item => item.classList.toggle('active', item === button));
  piState.filter = button.dataset.filter;
  renderResults();
}

async function locateSearchAddress() {
  const query = document.querySelector('#query').value.trim();
  if (!query || !piState.map) return;
  try {
    const data = await piApi(`/api/geocode?q=${encodeURIComponent(query)}`);
    const point = data.location;
    const lat = Number(point.lat);
    const lon = Number(point.lon);
    if (!Number.isFinite(lat) || !Number.isFinite(lon)) return;
    piState.map.setView([lat, lon], 15);
    L.marker([lat, lon]).addTo(piState.map).bindPopup(piEscape(point.address || point.name || query)).openPopup();
    document.querySelector('#map-note').textContent = '검색 주소 위치 · 물건 좌표와는 별도 표시';
  } catch {
    // 지역·아파트명처럼 지오코딩되지 않는 검색어도 거래 검색은 계속 허용합니다.
  }
}

function bindIntelligencePage() {
  initPiMap();
  document.querySelector('#search-form').addEventListener('submit', async event => {
    await searchIntelligence(event);
    await locateSearchAddress();
  });
  document.querySelectorAll('[data-filter]').forEach(button => button.addEventListener('click', () => activateFilter(button)));
  document.querySelector('#query').addEventListener('keydown', event => {
    if (event.key === 'Enter') document.querySelector('#search-form').requestSubmit();
  });
  loadSourceStatus().catch(error => {
    document.querySelector('#source-status').innerHTML = `<p class="pi-empty">소스 상태 확인 실패: ${piEscape(error.message)}</p>`;
  });
  piApi('/api/v1/statistics').then(data => {
    document.querySelector('#statistics').innerHTML = `<p class="pi-empty">${piEscape(data.onbid.message)}<br>${piEscape(data.court_auction.message)}</p>`;
  }).catch(() => {});
}

bindIntelligencePage();
