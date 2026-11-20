# QA 리포트 — HÖRU SS27 Lookbook (demo)

**총점 83.4 / 100 → FAIL** (합격선 85, 블로커 2건으로 불합격)

| 영역 | 점수 | 검사수 | 실패 |
|---|---|---|---|
| logo_realism | 24.0 / 30 | 5 | 1 |
| brand | 17.8 / 20 | 9 | 1 |
| compliance | 17.1 / 20 | 7 | 1 |
| image_quality | 14.1 / 15 | 16 | 1 |
| consistency | 6.7 / 10 | 6 | 2 |
| info | 3.8 / 5 | 4 | 1 |

## 실패 항목 (수정 필요)

| 페이지 | 영역 | 내용 |
|---|---|---|
| p02 | logo_realism | material 3/5 (기준 4) — 가공 방식 질감이 실물 같은가 (자수 실 결·볼륨 / 프린트 잉크 비침 / 각인 요철) |
| p05 | compliance | 금지어/좌표 발견: Sweden |
| p05 | image_quality | 해상도 1080x1350 (장변 최소 2000px) |
| p05 | info | 필수 필드 누락: scene_tag |
| p09 | brand | 컬러 #C0392B → 최근접 #A89C89 (ΔE 62.1, 허용 6) |
| p05 | consistency | model_id 'VM-B02' 미등록/누락 — 얼굴 일관성 보장 불가 |
| MODEL:VM-B01 | consistency | female 168cm/48kg (기준 170cm 이상·50kg 이하) |

## 전체 로그

- ✅ [p01] brand: 컬러 #A89C89 → 최근접 #A89C89 (ΔE 0.0, 허용 6)
- ✅ [p01] brand: 컬러 #1A1E36 → 최근접 #1A1E36 (ΔE 0.0, 허용 6)
- ✅ [p01] brand: 폰트 'Arial' 허용
- ✅ [p01] compliance: 금지어 없음
- ✅ [p01] image_quality: 해상도 3840x2160 (장변 최소 2000px)
- ✅ [p01] image_quality: 비율 1.778 vs 규격 16:9(1.778)
- ✅ [p01] image_quality: 하이라이트 클리핑 0.0% (상한 2%)
- ✅ [p01] image_quality: 선명도 693 (최소 60, 낮으면 블러 의심)
- ✅ [p01] info: 필수 필드 충족
- ✅ [p02] brand: 컬러 #1A1E36 → 최근접 #1A1E36 (ΔE 0.0, 허용 6)
- ✅ [p02] brand: 폰트 'Arial' 허용
- ✅ [p02] compliance: 금지어 없음
- ✅ [p02] image_quality: 해상도 3840x2160 (장변 최소 2000px)
- ✅ [p02] image_quality: 비율 1.778 vs 규격 16:9(1.778)
- ✅ [p02] image_quality: 하이라이트 클리핑 0.0% (상한 2%)
- ✅ [p02] image_quality: 선명도 710 (최소 60, 낮으면 블러 의심)
- ✅ [p02] info: 필수 필드 충족
- ✅ [p02] logo_realism: shape_fidelity 5/5 (기준 4) — 로고 형태·비율·Ö 점·부엉이 눈이 원본과 동일한가 (깨짐·누락·왜곡 없음)
- ✅ [p02] logo_realism: lighting 4/5 (기준 4) — 로고 명암이 주변 원단/재질의 빛·그림자와 같은 방향·세기인가
- ✅ [p02] logo_realism: surface_follow 4/5 (기준 4) — 주름·곡면·원근을 따라 휘고 가려지는가 (스티커처럼 떠 보이지 않음)
- ❌ [p02] logo_realism: material 3/5 (기준 4) — 가공 방식 질감이 실물 같은가 (자수 실 결·볼륨 / 프린트 잉크 비침 / 각인 요철)
- ✅ [p02] logo_realism: scale_position 5/5 (기준 4) — 벤치마크 상품의 로고 위치·크기와 같은가, 이음선·지퍼에 걸치지 않는가
- ❌ [p05] compliance: 금지어/좌표 발견: Sweden
- ❌ [p05] image_quality: 해상도 1080x1350 (장변 최소 2000px)
- ✅ [p05] image_quality: 비율 0.800 vs 규격 4:5(0.800)
- ✅ [p05] image_quality: 하이라이트 클리핑 0.0% (상한 2%)
- ✅ [p05] image_quality: 선명도 1708 (최소 60, 낮으면 블러 의심)
- ❌ [p05] info: 필수 필드 누락: scene_tag
- ✅ [p09] brand: 컬러 #040000 → 최근접 #040000 (ΔE 0.0, 허용 6)
- ❌ [p09] brand: 컬러 #C0392B → 최근접 #A89C89 (ΔE 62.1, 허용 6)
- ✅ [p09] brand: 폰트 'Cambria' 허용
- ✅ [p09] brand: 폰트 'Arial' 허용
- ✅ [p09] compliance: 금지어 없음
- ✅ [p09] compliance: C-COPY(long) 포함
- ✅ [p09] compliance: C-COPY(short) 포함
- ✅ [p09] image_quality: 해상도 3840x2160 (장변 최소 2000px)
- ✅ [p09] image_quality: 비율 1.778 vs 규격 16:9(1.778)
- ✅ [p09] image_quality: 하이라이트 클리핑 0.0% (상한 2%)
- ✅ [p09] image_quality: 선명도 708 (최소 60, 낮으면 블러 의심)
- ✅ [p09] info: 필수 필드 충족
- ✅ [p01] consistency: model_id 'VM-A01' 등록됨
- ✅ [p02] consistency: model_id 'VM-A01' 등록됨
- ❌ [p05] consistency: model_id 'VM-B02' 미등록/누락 — 얼굴 일관성 보장 불가
- ✅ [LINE:LINE_A] consistency: 라인 내 모델 2명 (VM-A01, VM-B02) — 3명 이상이면 일관성 저하
- ✅ [MODEL:VM-A01] consistency: female 178cm/49kg (기준 170cm 이상·50kg 이하)
- ❌ [MODEL:VM-B01] consistency: female 168cm/48kg (기준 170cm 이상·50kg 이하)
- ✅ [DOC] compliance: 클로징 페이지(T08_closing) 있음

> 자동 검수 범위 밖: AI 생성 결함(손·텍스트 왜곡), 로고 위치/보호공간, 무드 적합성 → 2·3차 검수에서 확인