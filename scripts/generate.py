# -*- coding: utf-8 -*-
"""바로변환 정적 사이트 생성기.

units.json × 템플릿 → 페어 허브 / 수치 페이지 / 카테고리 허브 / 사이트맵.
- 고아 페이지 0 원칙: 방출한 모든 페이지가 링크 그래프에 연결됐는지 검증
- 단계 방출: MAX_PAGES 초과 시 생성 거부 (구글 저품질 리스크 관리)

실행: python scripts/generate.py  (저장소 루트 기준)
"""
from __future__ import annotations

import json
import os
import shutil
import sys

sys.path.insert(0, os.path.dirname(__file__))
import conversions  # noqa: E402  (Agent 산출물 — 동일 units.json 사용)

ROOT = os.path.normpath(os.path.join(os.path.dirname(__file__), ".."))
SITE_URL = "https://maestro24.github.io/baroconvert"
MAX_PAGES = 600  # 파일럿 상한 — 확장은 색인율 확인 후 (docs/PLAN.md §12)

CAT_ICON = {"length": "📏", "weight": "⚖️", "temperature": "🌡️", "area": "🏠", "volume": "🧪"}

# 쿠팡 파트너스 다이나믹 배너 — 페어 허브·환율 페이지에만 (수치 페이지 제외: 씬 페이지+광고 = 저품질 신호)
DISCLOSURE = "이 포스팅은 쿠팡 파트너스 활동의 일환으로, 이에 따른 일정액의 수수료를 제공받습니다."


def promo_html(_cat=None):
    return ("""<aside class="promo" data-coupang>
  <div class="coupang-wrap">
    <a href="https://link.coupang.com/a/flCfhuxEJM" target="_blank" rel="sponsored noopener" referrerpolicy="unsafe-url"><img src="https://ads-partners.coupang.com/banners/1006097?trackingCode=AF8748009&subId=&traceId=V0-301-879dd1202e5c73b2-I1006097&w=728&h=90" alt="쿠팡 파트너스 배너" style="max-width:100%;height:auto" loading="lazy"></a>
  </div>
  <p class="promo-disclosure">""" + DISCLOSURE + """</p>
</aside>
<script>
  // 광고 미표시(차단기 등) 시 빈 카드 숨김
  setTimeout(function () {
    document.querySelectorAll('[data-coupang]').forEach(function (el) {
      var f = el.querySelector('iframe');
      var m = el.querySelector('img');
      var ok = (f && f.getBoundingClientRect().height >= 10) || (m && m.complete && m.naturalWidth > 0);
      if (!ok) el.hidden = true;
    });
  }, 4000);
</script>""")


RAILS = """<div class="side-rail side-l" data-coupang>
  <script src="https://ads-partners.coupang.com/g.js"></script>
  <script>new PartnersCoupang.G({ id: 1006093, template: "carousel", trackingCode: "AF8748009", width: "160", height: "600", tsource: "" });</script>
</div>
<div class="side-rail side-r" data-coupang>
  <script>new PartnersCoupang.G({ id: 1006093, template: "carousel", trackingCode: "AF8748009", width: "160", height: "600", tsource: "" });</script>
</div>
"""


def add_rails(html):
    return html.replace("</body>", RAILS + "</body>", 1)
CAT_DESC = {
    "length": "키, 모니터, 거리 — 피트·인치·마일을 미터법으로",
    "weight": "직구, 요리, 금 시세 — 파운드·온스·근·돈",
    "temperature": "해외 날씨, 오븐 온도 — 화씨·섭씨",
    "area": "부동산 필수 — 평과 제곱미터",
    "volume": "레시피 계량 — 컵·큰술·갤런·리터",
}

FAVICON = "data:image/svg+xml,<svg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 100 100'><defs><linearGradient id='g' x1='0' y1='0' x2='0' y2='1'><stop offset='0' stop-color='%231FBFAE'/><stop offset='1' stop-color='%23108577'/></linearGradient></defs><rect width='100' height='100' rx='18' fill='url(%23g)'/><path d='M28 38h28m0 0l-9-9m9 9l-9 9' stroke='white' stroke-width='7' fill='none' stroke-linecap='round' stroke-linejoin='round'/><path d='M72 62H44m0 0l9-9m-9 9l9 9' stroke='white' stroke-width='7' fill='none' stroke-linecap='round' stroke-linejoin='round' opacity='.85'/></svg>"


def fmt(v):
    return conversions.format_result(v)


# ── 공통 셸 ─────────────────────────────────────────
def shell(*, title, desc, canonical, depth, body, jsonld=None, seo_html=""):
    p = "../" * depth
    ld = f'<script type="application/ld+json">{json.dumps(jsonld, ensure_ascii=False)}</script>' if jsonld else ""
    return f"""<!doctype html>
<html lang="ko">
<head>
<meta charset="utf-8" />
<meta name="viewport" content="width=device-width, initial-scale=1" />
<title>{title}</title>
<meta name="description" content="{desc}" />
<link rel="canonical" href="{canonical}" />
<meta property="og:title" content="{title}" />
<meta property="og:description" content="{desc}" />
<meta property="og:type" content="website" />
<meta property="og:url" content="{canonical}" />
<meta property="og:locale" content="ko_KR" />
<meta name="theme-color" content="#f6f9f9" />
<link rel="icon" href="{FAVICON}" />
{ld}
<link rel="stylesheet" href="{p}css/style.css" />
</head>
<body>
<div id="app">
<header class="header">
  <a class="brand" href="{p}index.html">🔁 바로변환</a>
</header>
<main class="main">
{body}
</main>
{seo_html}
<footer class="footer">
  <a href="{p}index.html">홈</a>
  <a href="{p}fx/index.html">환율</a>
  <span>계산 결과는 참고용입니다.</span>
</footer>
</div>
</body>
</html>"""


class Site:
    """페이지 방출 + 링크 그래프 추적"""

    def __init__(self):
        self.pages = {}   # path -> html
        self.links = set()  # (from_path, to_path)

    def emit(self, path, html):
        if path in self.pages:
            raise SystemExit(f"중복 페이지: {path}")
        self.pages[path] = html

    def link(self, src, dst):
        self.links.add((src, dst))

    def verify(self):
        if len(self.pages) > MAX_PAGES:
            raise SystemExit(f"페이지 {len(self.pages)}개 > 상한 {MAX_PAGES} — 단계 방출 원칙 위반")
        linked = {dst for _, dst in self.links}
        orphans = [p for p in self.pages if p != "index.html" and p not in linked]
        if orphans:
            raise SystemExit(f"고아 페이지 {len(orphans)}개: {orphans[:5]}")

    def write(self):
        for path, html in self.pages.items():
            full = os.path.join(ROOT, path.replace("/", os.sep))
            os.makedirs(os.path.dirname(full), exist_ok=True)
            with open(full, "w", encoding="utf-8") as f:
                f.write(html)


def pair_dir(a, b):
    return f"convert/{a}-to-{b}"


def unit_label(data, cat, u):
    info = data["categories"][cat]["units"][u]
    return info["nameKo"], info.get("symbol", u)


def find_category(data, u):
    for cat, cinfo in data["categories"].items():
        if u in cinfo["units"]:
            return cat
    raise SystemExit(f"단위 카테고리 없음: {u}")


# ── 페어 허브 페이지 ────────────────────────────────
def build_pair_hub(site, data, pair, all_pairs):
    a, b = pair["from"], pair["to"]
    cat = find_category(data, a)
    an, asym = unit_label(data, cat, a)
    bn, bsym = unit_label(data, cat, b)
    path = f"{pair_dir(a, b)}/index.html"
    canonical = f"{SITE_URL}/{pair_dir(a, b)}/"
    one = conversions.convert(1, a, b)

    rows = []
    for v in pair["values"]:
        r = conversions.convert(v, a, b)
        vslug = str(v)
        site.link(path, f"{pair_dir(a, b)}/{vslug}/index.html")
        rows.append(
            f'<tr><td><a href="{vslug}/index.html">{fmt(v)} {asym}</a></td>'
            f"<td>{fmt(r)} {bsym}</td></tr>"
        )

    # 역변환 + 같은 카테고리 관련 페어
    rel = []
    rev = next((p for p in all_pairs if p["from"] == b and p["to"] == a), None)
    if rev:
        site.link(path, f"{pair_dir(b, a)}/index.html")
        rel.append(f'<a class="rel-link" href="../{b}-to-{a}/index.html">{bn} → {an} 역변환</a>')
    for p in all_pairs:
        if p is pair or (rev and p is rev):
            continue
        if find_category(data, p["from"]) == cat and len(rel) < 7:
            pn, _ = unit_label(data, cat, p["from"])
            qn, _ = unit_label(data, cat, p["to"])
            site.link(path, f"{pair_dir(p['from'], p['to'])}/index.html")
            rel.append(f'<a class="rel-link" href="../{p["from"]}-to-{p["to"]}/index.html">{pn} → {qn}</a>')
    site.link(path, f"c/{cat}/index.html")

    uinfo = data["categories"][cat]["units"]
    formula = (
        f"{bn} = {an} × <b>{fmt(one)}</b>"
        if "affine" not in uinfo[a] and "affine" not in uinfo[b]
        else "온도 변환: °F = °C × 9/5 + 32"
    )

    faq = {
        "@context": "https://schema.org",
        "@type": "FAQPage",
        "mainEntity": [
            {"@type": "Question", "name": f"1{an}는 몇 {bn}인가요?",
             "acceptedAnswer": {"@type": "Answer", "text": f"1{an}({asym})는 {fmt(one)}{bn}({bsym})입니다."}},
            {"@type": "Question", "name": f"{an}를 {bn}로 바꾸는 공식은?",
             "acceptedAnswer": {"@type": "Answer", "text": f"{an} 값에 {fmt(one)}을(를) 곱하면 {bn} 값이 됩니다." if "affine" not in uinfo[a] and "affine" not in uinfo[b] else "섭씨 = (화씨 − 32) × 5/9, 화씨 = 섭씨 × 9/5 + 32 입니다."}},
        ],
    }

    body = f"""<nav class="crumb"><a href="../../index.html">홈</a> › <a href="../../c/{cat}/index.html">{data['categories'][cat]['nameKo']}</a> › {an} → {bn}</nav>
<div>
  <h1 class="page-title">{an}({asym}) → {bn}({bsym}) 변환기</h1>
  <p class="page-desc">숫자를 입력하면 바로 변환돼요. 표에서 자주 찾는 값도 확인하세요.</p>
</div>
<div class="card conv" data-from="{a}" data-to="{b}" id="converter">
  <div class="conv-row">
    <div class="conv-cell"><label>{an} ({asym})</label><input type="number" id="in-a" value="1" inputmode="decimal" /></div>
    <button class="swap-btn" id="btn-swap" aria-label="방향 바꾸기">⇄</button>
    <div class="conv-cell"><label>{bn} ({bsym})</label><input type="number" id="in-b" inputmode="decimal" /></div>
  </div>
  <div class="formula">{formula}</div>
</div>
<div class="card">
  <h2 style="font-size:1rem;margin-bottom:10px">{an} → {bn} 변환표</h2>
  <table class="tbl"><thead><tr><th>{an}</th><th>{bn}</th></tr></thead><tbody>
  {''.join(rows)}
  </tbody></table>
</div>
<div class="card">
  <h2 style="font-size:1rem;margin-bottom:10px">관련 변환</h2>
  <div class="rel-grid">{''.join(rel)}</div>
</div>
{promo_html(cat)}"""

    seo = f"""<section class="seo-content">
<h2>{an}에서 {bn}로 어떻게 바꾸나요?</h2>
<p>{'%s 1단위는 %s %s입니다. %s 값에 %s을(를) 곱하면 %s 값을 얻습니다.' % (an, fmt(one), bn, an, fmt(one), bn) if 'affine' not in uinfo[a] and 'affine' not in uinfo[b] else '화씨(°F)와 섭씨(°C)는 곱셈만으로 바꿀 수 없는 단위입니다. 섭씨 = (화씨 − 32) × 5/9 공식을 사용하며, 예를 들어 화씨 100도는 섭씨 약 37.8도입니다.'} 위 변환기는 입력 즉시 계산되며, 반대 방향 입력도 지원합니다.</p>
</section>"""

    site.emit(path, shell(
        title=f"{an} {bn} 변환 — {asym} to {bsym} 계산기 | 바로변환",
        desc=f"{an}({asym})를 {bn}({bsym})로 즉시 변환. 1{asym} = {fmt(one)}{bsym}. 자주 찾는 값 변환표와 공식까지.",
        canonical=canonical, depth=2, body=body, jsonld=faq, seo_html=seo,
    ))

    # 허브 페이지에 변환기 JS + 사이드 레일 주입
    site.pages[path] = add_rails(site.pages[path].replace(
        "</body>",
        f"""<script type="module">
import {{ initConverter }} from '../../js/app.js';
initConverter('{a}', '{b}');
</script>
</body>""",
    ))


# ── 수치 페이지 ─────────────────────────────────────
def build_value_page(site, data, pair, v):
    a, b = pair["from"], pair["to"]
    cat = find_category(data, a)
    an, asym = unit_label(data, cat, a)
    bn, bsym = unit_label(data, cat, b)
    r = conversions.convert(v, a, b)
    vslug = str(v)
    path = f"{pair_dir(a, b)}/{vslug}/index.html"
    canonical = f"{SITE_URL}/{pair_dir(a, b)}/{vslug}/"

    # 근처 수치 표 (현재 값 하이라이트)
    rows = []
    for w in pair["values"]:
        res = conversions.convert(w, a, b)
        cls = ' class="hl"' if w == v else ""
        cell = f"{fmt(w)} {asym}" if w == v else f'<a href="../{w}/index.html">{fmt(w)} {asym}</a>'
        if w != v:
            site.link(path, f"{pair_dir(a, b)}/{w}/index.html")
        rows.append(f"<tr{cls}><td>{cell}</td><td>{fmt(res)} {bsym}</td></tr>")
    site.link(path, f"{pair_dir(a, b)}/index.html")

    body = f"""<nav class="crumb"><a href="../../../index.html">홈</a> › <a href="../index.html">{an} → {bn} 변환기</a> › {fmt(v)}{asym}</nav>
<div class="answer">
  <div class="eq">{fmt(v)} {asym} = <b>{fmt(r)} {bsym}</b></div>
  <div class="sub">{an} {fmt(v)}{asym}는 {bn}로 {fmt(r)}{bsym}입니다</div>
</div>
<div class="card">
  <h2 style="font-size:1rem;margin-bottom:10px">근처 값 변환표</h2>
  <table class="tbl"><thead><tr><th>{an}</th><th>{bn}</th></tr></thead><tbody>
  {''.join(rows)}
  </tbody></table>
</div>
<div class="card">
  <p style="font-size:0.9rem">다른 값을 바꾸려면 <a href="../index.html"><b>{an} → {bn} 변환기</b></a>에서 직접 입력하세요.</p>
</div>"""

    site.emit(path, shell(
        title=f"{fmt(v)}{asym}는 몇 {bsym}? = {fmt(r)}{bsym} | 바로변환",
        desc=f"{an} {fmt(v)}{asym}는 {bn}로 {fmt(r)}{bsym}입니다. 근처 값 변환표와 즉시 계산기 제공.",
        canonical=canonical, depth=3, body=body,
    ))


# ── 카테고리 허브 ───────────────────────────────────
def build_category_hub(site, data, cat, pairs):
    cinfo = data["categories"][cat]
    path = f"c/{cat}/index.html"
    cards = []
    for p in pairs:
        if find_category(data, p["from"]) != cat:
            continue
        an, asym = unit_label(data, cat, p["from"])
        bn, bsym = unit_label(data, cat, p["to"])
        site.link(path, f"{pair_dir(p['from'], p['to'])}/index.html")
        cards.append(
            f'<a class="cat-card" href="../../{pair_dir(p["from"], p["to"])}/index.html">'
            f'<span class="name">{an} → {bn}</span>'
            f'<span class="desc">{asym} to {bsym}</span></a>'
        )
    body = f"""<nav class="crumb"><a href="../../index.html">홈</a> › {cinfo['nameKo']}</nav>
<div>
  <h1 class="page-title">{CAT_ICON.get(cat, '')} {cinfo['nameKo']} 단위 변환</h1>
  <p class="page-desc">{CAT_DESC.get(cat, '')}</p>
</div>
<div class="cat-grid">{''.join(cards)}</div>"""
    site.emit(path, shell(
        title=f"{cinfo['nameKo']} 단위 변환 — {CAT_DESC.get(cat, '')} | 바로변환",
        desc=f"{cinfo['nameKo']} 단위 변환기 모음. {CAT_DESC.get(cat, '')}.",
        canonical=f"{SITE_URL}/c/{cat}/", depth=2, body=body,
    ))


# ── 루트 허브 ───────────────────────────────────────
def build_index(site, data, pairs):
    path = "index.html"
    cats = []
    for cat, cinfo in data["categories"].items():
        site.link(path, f"c/{cat}/index.html")
        cats.append(
            f'<a class="cat-card" href="c/{cat}/index.html">'
            f'<span class="icon">{CAT_ICON.get(cat, "🔁")}</span>'
            f'<span class="name">{cinfo["nameKo"]}</span>'
            f'<span class="desc">{CAT_DESC.get(cat, "")}</span></a>'
        )
    site.link(path, "fx/index.html")
    popular = []
    for p in pairs[:8]:
        cat = find_category(data, p["from"])
        an, _ = unit_label(data, cat, p["from"])
        bn, _ = unit_label(data, cat, p["to"])
        site.link(path, f"{pair_dir(p['from'], p['to'])}/index.html")
        popular.append(f'<a class="rel-link" href="{pair_dir(p["from"], p["to"])}/index.html">{an} → {bn}</a>')

    body = f"""<div>
  <h1 class="page-title">단위 변환, 검색보다 빠르게</h1>
  <p class="page-desc">피트·인치·평·온스·화씨 — 헷갈리는 단위를 즉시 변환하세요.</p>
</div>
<div class="card">
  <h2 style="font-size:1rem;margin-bottom:10px">인기 변환</h2>
  <div class="rel-grid">{''.join(popular)}</div>
</div>
<div class="cat-grid">
{''.join(cats)}
<a class="cat-card" href="fx/index.html"><span class="icon">💱</span><span class="name">환율</span><span class="desc">달러·엔·유로 → 원화, 매일 갱신</span></a>
</div>"""

    seo = """<section class="seo-content">
<h2>바로변환은 어떤 서비스인가요?</h2>
<p>바로변환은 길이·무게·온도·넓이·부피 등 일상에서 마주치는 단위를 한국어로 즉시 변환하는 무료 도구입니다. 해외직구의 파운드와 온스, 부동산의 평과 제곱미터, 미국 날씨의 화씨, 레시피의 컵과 큰술까지 — 정확한 국제 표준 계수로 계산합니다. 설치와 회원가입 없이 브라우저에서 바로 사용하세요.</p>
<h2>자주 묻는 질문</h2>
<dl>
<dt>변환 결과는 정확한가요?</dt>
<dd>모든 계수는 국제 표준값(예: 1인치 = 정확히 2.54cm, 1파운드 = 정확히 453.59237g)을 사용하며, 자동 테스트로 검증됩니다.</dd>
<dt>환율은 실시간인가요?</dt>
<dd>아니요. 유럽중앙은행(ECB) 고시 기준으로 하루 한 번 갱신되며 기준 시각을 함께 표시합니다. 송금·환전 실거래는 은행 고시 환율을 확인하세요.</dd>
</dl>
</section>"""

    site.emit(path, shell(
        title="바로변환 — 단위 변환기 (평·피트·온스·화씨·환율)",
        desc="피트↔cm, 평↔제곱미터, 온스↔그램, 화씨↔섭씨, 달러↔원까지. 한국인이 자주 찾는 단위 변환을 즉시. 무료, 설치 불필요.",
        canonical=f"{SITE_URL}/", depth=0, body=body, seo_html=seo,
        jsonld={"@context": "https://schema.org", "@type": "WebSite", "url": f"{SITE_URL}/",
                "name": "바로변환", "description": "단위 변환기 — 평·피트·온스·화씨·환율", "inLanguage": "ko"},
    ))


# ── 환율 페이지 ─────────────────────────────────────
def build_fx(site):
    path = "fx/index.html"
    body = """<nav class="crumb"><a href="../index.html">홈</a> › 환율</nav>
<div>
  <h1 class="page-title">💱 환율 계산기 — 원화 기준</h1>
  <p class="page-desc">달러·엔·유로·위안을 원화로. 유럽중앙은행 고시 기준, 매일 갱신.</p>
</div>
<div class="card conv">
  <div class="conv-row">
    <div class="conv-cell"><label>외화</label><input type="number" id="in-foreign" value="1" inputmode="decimal" /></div>
    <div class="conv-cell"><label>통화</label><select id="sel-cur"></select></div>
    <div class="conv-cell"><label>원화 (KRW)</label><input type="number" id="in-krw" inputmode="decimal" /></div>
  </div>
  <div class="fx-updated" id="fx-updated"></div>
</div>
<div class="card">
  <h2 style="font-size:1rem;margin-bottom:10px">주요 통화 환율표</h2>
  <div id="fx-table"><div class="empty">환율 데이터를 불러오는 중…</div></div>
</div>
""" + promo_html()
    seo = """<section class="seo-content">
<h2>이 환율은 어디서 오나요?</h2>
<p>유럽중앙은행(ECB)이 고시하는 기준 환율을 매일 한 번 수집해 표시합니다. 실시간 시세가 아니며, 은행 환전·해외 송금에는 각 은행의 고시 환율과 수수료가 적용됩니다. 대략적인 금액 감을 잡는 용도로 활용하세요.</p>
</section>"""
    html = shell(
        title="환율 계산기 — 달러·엔·유로 원화 변환 | 바로변환",
        desc="1달러 몇 원? 달러·엔·유로·위안 → 원화 즉시 계산. ECB 기준 매일 갱신, 기준 시각 표시.",
        canonical=f"{SITE_URL}/fx/", depth=1, body=body, seo_html=seo,
    ).replace("</body>", """<script type="module">
import { initFxPage } from '../js/app.js';
initFxPage();
</script>
</body>""")
    site.emit(path, add_rails(html))


# ── 사이트맵 ────────────────────────────────────────
def build_sitemap(site):
    urls = []
    for path in sorted(site.pages):
        loc = SITE_URL + "/" + path.replace("index.html", "").rstrip("/")
        loc = loc if loc.endswith("/") or "." in loc.rsplit("/", 1)[-1] else loc + "/"
        if path == "index.html":
            loc = SITE_URL + "/"
        urls.append(f"<url><loc>{loc}</loc></url>")
    xml = ('<?xml version="1.0" encoding="UTF-8"?>\n'
           '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
           + "\n".join(urls) + "\n</urlset>\n")
    with open(os.path.join(ROOT, "sitemap.xml"), "w", encoding="utf-8") as f:
        f.write(xml)
    return len(urls)


def main():
    with open(os.path.join(ROOT, "data", "units.json"), encoding="utf-8") as f:
        data = json.load(f)
    pairs = data["pairs"]

    # 기존 생성물 정리 (생성 대상 디렉토리만)
    for d in ("convert", "c", "fx"):
        shutil.rmtree(os.path.join(ROOT, d), ignore_errors=True)

    site = Site()
    build_index(site, data, pairs)
    for cat in data["categories"]:
        build_category_hub(site, data, cat, pairs)
    for pair in pairs:
        build_pair_hub(site, data, pair, pairs)
        for v in pair["values"]:
            build_value_page(site, data, pair, v)
    build_fx(site)

    site.verify()
    site.write()
    n = build_sitemap(site)
    print(f"[generate] 페이지 {len(site.pages)}개 생성, sitemap {n} URL, 고아 0 검증 통과")


if __name__ == "__main__":
    main()
