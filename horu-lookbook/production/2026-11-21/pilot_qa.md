# QA 리포트 — Phase 1 시범 생산 FA-ATH-001-S1

**총점 70.2 / 100 → FAIL** (합격선 85, 블로커 2건으로 불합격)

| 영역 | 점수 | 검사수 | 실패 |
|---|---|---|---|
| logo_realism | 24.0 / 30 | 5 | 1 |
| brand | 20.0 / 20 | 0 | 0 |
| compliance | 10.0 / 20 | 2 | 1 |
| image_quality | 3.8 / 15 | 4 | 3 |
| consistency | 10.0 / 10 | 13 | 0 |
| info | 2.5 / 5 | 2 | 1 |

## 실패 항목 (수정 필요)

| 페이지 | 영역 | 내용 |
|---|---|---|
| FA-ATH-001-S1 | image_quality | 해상도 960x1280 (장변 최소 2000px) |
| FA-ATH-001-S1 | image_quality | 비율 0.750 vs 규격 4:5(0.800) |
| FA-ATH-001-S1 | image_quality | 하이라이트 클리핑 6.2% (상한 2%) |
| FA-ATH-001-S1 | logo_realism | material 3/5 (기준 4) — 가공 방식 질감이 실물 같은가 (자수 실 결·볼륨 / 프린트 잉크 비침 / 각인 요철) |
| FA-ATH-001-S1 | info | AI 생성 표기 없음 — 캡션·하단에 'AI 생성 이미지' 표기 권장 |
| DOC | compliance | 클로징 페이지(T08_closing) 없음 — C-COPY 누락 |

## 전체 로그

- ✅ [FA-ATH-001-S1] compliance: 금지어 없음
- ❌ [FA-ATH-001-S1] image_quality: 해상도 960x1280 (장변 최소 2000px)
- ❌ [FA-ATH-001-S1] image_quality: 비율 0.750 vs 규격 4:5(0.800)
- ❌ [FA-ATH-001-S1] image_quality: 하이라이트 클리핑 6.2% (상한 2%)
- ✅ [FA-ATH-001-S1] image_quality: 선명도 132 (최소 60, 낮으면 블러 의심)
- ✅ [FA-ATH-001-S1] info: 필수 필드 충족
- ✅ [FA-ATH-001-S1] logo_realism: shape_fidelity 4/5 (기준 4) — 로고 형태·비율·Ö 점·부엉이 눈이 원본과 동일한가 (깨짐·누락·왜곡 없음)
- ✅ [FA-ATH-001-S1] logo_realism: lighting 4/5 (기준 4) — 로고 명암이 주변 원단/재질의 빛·그림자와 같은 방향·세기인가
- ✅ [FA-ATH-001-S1] logo_realism: surface_follow 4/5 (기준 4) — 주름·곡면·원근을 따라 휘고 가려지는가 (스티커처럼 떠 보이지 않음)
- ❌ [FA-ATH-001-S1] logo_realism: material 3/5 (기준 4) — 가공 방식 질감이 실물 같은가 (자수 실 결·볼륨 / 프린트 잉크 비침 / 각인 요철)
- ✅ [FA-ATH-001-S1] logo_realism: scale_position 5/5 (기준 4) — 벤치마크 상품의 로고 위치·크기와 같은가, 이음선·지퍼에 걸치지 않는가
- ❌ [FA-ATH-001-S1] info: AI 생성 표기 없음 — 캡션·하단에 'AI 생성 이미지' 표기 권장
- ✅ [FA-ATH-001-S1] consistency: model_id 'VM-F-EA01' 등록됨
- ✅ [MODEL:VM-F-EA01] consistency: female 20세 172cm/50kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-EA01] consistency: male 23세 186cm/73kg (기준 23세·185cm 이상·74kg 이하)
- ✅ [MODEL:VM-F-NE01] consistency: female 20세 174cm/50kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-NE01] consistency: male 23세 188cm/74kg (기준 23세·185cm 이상·74kg 이하)
- ✅ [MODEL:VM-F-AF01] consistency: female 20세 175cm/50kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-AF01] consistency: male 23세 189cm/74kg (기준 23세·185cm 이상·74kg 이하)
- ✅ [MODEL:VM-F-SA01] consistency: female 20세 171cm/49kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-SA01] consistency: male 23세 185cm/72kg (기준 23세·185cm 이상·74kg 이하)
- ✅ [MODEL:VM-F-SEA01] consistency: female 20세 170cm/48kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-SEA01] consistency: male 23세 185cm/70kg (기준 23세·185cm 이상·74kg 이하)
- ✅ [MODEL:VM-F-LA01] consistency: female 20세 173cm/50kg (기준 20세·170cm 이상·50kg 이하)
- ✅ [MODEL:VM-M-LA01] consistency: male 23세 187cm/74kg (기준 23세·185cm 이상·74kg 이하)
- ❌ [DOC] compliance: 클로징 페이지(T08_closing) 없음 — C-COPY 누락

> 자동 검수 범위 밖: AI 생성 결함(손·텍스트 왜곡), 로고 위치/보호공간, 무드 적합성 → 2·3차 검수에서 확인