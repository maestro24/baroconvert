// 페이지 위젯 — 페어 변환기 / 환율 계산기
// 상대 경로: 이 모듈은 항상 <root>/js/app.js 로 로드되므로 import.meta.url 기준으로 루트 계산
const ROOT = new URL('..', import.meta.url);

async function loadJSON(rel) {
  const res = await fetch(new URL(rel, ROOT), { cache: 'no-cache' });
  if (!res.ok) throw new Error(`${rel}: ${res.status}`);
  return res.json();
}

// ── 페어 변환기 (허브 페이지) ──
export async function initConverter(fromU, toU) {
  const { convert, setData } = await import(new URL('js/convert.js', ROOT));
  const data = await loadJSON('data/units.json');
  setData(data);

  const $a = document.getElementById('in-a');
  const $b = document.getElementById('in-b');
  let [ua, ub] = [fromU, toU];

  const recalcFromA = () => {
    const v = parseFloat($a.value);
    $b.value = Number.isFinite(v) ? round(convert(v, ua, ub)) : '';
  };
  const recalcFromB = () => {
    const v = parseFloat($b.value);
    $a.value = Number.isFinite(v) ? round(convert(v, ub, ua)) : '';
  };
  $a.addEventListener('input', recalcFromA);
  $b.addEventListener('input', recalcFromB);
  document.getElementById('btn-swap')?.addEventListener('click', () => {
    [ua, ub] = [ub, ua];
    const [la, lb] = [$a.closest('.conv-cell').querySelector('label'), $b.closest('.conv-cell').querySelector('label')];
    [la.textContent, lb.textContent] = [lb.textContent, la.textContent];
    recalcFromA();
  });
  recalcFromA();
}

function round(v) {
  if (v == null || !Number.isFinite(v)) return '';
  const r = Math.abs(v) >= 1 ? Math.round(v * 10000) / 10000 : Math.round(v * 1e8) / 1e8;
  return String(r);
}

// ── 환율 페이지 ──
const CUR_NAME = { USD: '미국 달러', JPY: '일본 엔', EUR: '유로', CNY: '중국 위안', GBP: '영국 파운드', THB: '태국 바트' };

export async function initFxPage() {
  const { toKRW, fromKRW } = await import(new URL('js/fx.js', ROOT));
  let rates = null;
  let updated = null;
  try {
    const data = await loadJSON('data/rates.json');
    rates = data.rates;
    updated = data.updated;
  } catch { /* 준비 중 처리 */ }

  const $t = document.getElementById('fx-table');
  const $u = document.getElementById('fx-updated');
  if (!rates) {
    $t.innerHTML = '<div class="empty">환율 데이터 준비 중이에요 — 자동 수집이 시작되면 표시됩니다</div>';
    return;
  }
  if (updated) $u.textContent = `기준: ${updated.slice(0, 16).replace('T', ' ')} (ECB 고시, 실시간 아님)`;

  // 표
  const rows = Object.entries(rates).map(([cur, r]) =>
    `<tr><td>${CUR_NAME[cur] || cur} (${cur})</td><td>${r.toLocaleString('ko-KR', { maximumFractionDigits: 2 })}원</td></tr>`
  ).join('');
  $t.innerHTML = `<table class="tbl"><thead><tr><th>통화</th><th>1단위 = KRW</th></tr></thead><tbody>${rows}</tbody></table>`;

  // 계산기
  const $sel = document.getElementById('sel-cur');
  $sel.innerHTML = Object.keys(rates).map((c) => `<option value="${c}">${c} — ${CUR_NAME[c] || c}</option>`).join('');
  const $f = document.getElementById('in-foreign');
  const $k = document.getElementById('in-krw');
  const fromForeign = () => {
    const v = parseFloat($f.value);
    $k.value = Number.isFinite(v) ? Math.round(toKRW(v, $sel.value, rates)) : '';
  };
  const fromKrw = () => {
    const v = parseFloat($k.value);
    const r = Number.isFinite(v) ? fromKRW(v, $sel.value, rates) : null;
    $f.value = r == null ? '' : Math.round(r * 100) / 100;
  };
  $f.addEventListener('input', fromForeign);
  $k.addEventListener('input', fromKrw);
  $sel.addEventListener('change', fromForeign);
  fromForeign();
}
