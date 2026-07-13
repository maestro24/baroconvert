# 바로변환 — 단위 변환 프로그래매틱 SEO 사이트

units.json × Python 생성기 → 수백 개 정적 변환 페이지. 프레임워크·빌드도구 없음.

**운영 URL**: https://maestro24.github.io/baroconvert/

## 아키텍처

```
data/units.json          단위 정의 (소스 오브 트루스)
scripts/conversions.py   Python 변환 엔진 ─┐ 같은 JSON,
js/convert.js            JS 변환 엔진     ─┘ 교차 검증 테스트
scripts/generate.py      units.json × 템플릿 → convert/·c/·fx/ 페이지 + sitemap
                         (고아 페이지 0 검증, 파일럿 상한 600 강제)
scripts/fetch_rates.py   환율 수집 (frankfurter/ECB) → data/rates.json
.github/workflows/       환율 일일 크론 (07:00 KST)
```

## 명령

```bash
python scripts/generate.py            # 사이트 재생성 (units.json 수정 후)
python scripts/fetch_rates.py         # 환율 수동 갱신
python -m unittest discover tests     # Python 테스트
node tests/convert.test.mjs           # JS 엔진 + 교차 검증
node tests/fx.test.mjs
python -m http.server 8000            # 로컬 확인
```

## 단계 방출 원칙 (중요)

프로그래매틱 SEO 최대 리스크 = 구글 저품질 판정.
- 파일럿 ≤600 페이지 (generate.py가 강제)
- 확장 전 Search Console 색인율 확인 (색인율 <30%면 페이지 품질 재설계)
- 수치 페이지는 실검색 수요 값만 — units.json의 pairs[].values 편집으로 관리
