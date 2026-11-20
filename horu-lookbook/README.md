# horu-lookbook

HÖRU 룩북·목업 자동화 작업 폴더.

| 파일 | 용도 |
|---|---|
| `PLAN.md` | 자동화·카테고리 확장·품질 업그레이드 전체 계획 |
| `config/brand_rules.yaml` | 브랜드 규칙 단일 기준 (팔레트·폰트·C-COPY·금지어·점수) |
| `config/lookbook_spec.yaml` | 템플릿 T01~T08 규격 + 카테고리 매트릭스 + 출력 프리셋 |
| `scripts/qa_check.py` | 1차 자동 QA 게이트 (점수 + 블로커) |
| `samples/` | 데모 manifest·합성 이미지·QA 리포트, SS27 합성 비교 이미지 |
| `assets/logo/` | BI 원본 로고(SVG) + 투명 PNG (심볼·워드마크·조합형), 자수 레퍼런스 |
| `scripts/brand_assets.py` | 공식 슬로건 3종·조합(lockup) 생성 — 공식 문구·대문자만 허용 |
| `scripts/logo_apply.py` | 로고 실물 합성기 v2 — 자수·프린트·반사·각인·형압 + 직조/인쇄 라벨·러버/가죽 패치 |
| `scripts/placement_matcher.py` | 상품·벤치마크·사진 정보 → 위치·크기·가공 자동 매칭 + 최소 규격 판정 + 합성 |
| `config/logo_placement_library.yaml` | 업계 표준 위치·크기·기법 최소 규격·벤치마크 레시피 |
| `config/slogan_rules.yaml` | 슬로건·텍스트로고 상황별 사용 규칙 |
| `research/06_logo_placement_research.md` | 로고 적용 사례 조사 원본 (출처 포함) |
| `config/model_registry.yaml` | 착장 가상모델 등록부 — 인종별 12명 (여 20세·남 23세, 체형 기준) |
| `scripts/model_prompts.py` | 모델 기준 시트·착장 컷 생성 프롬프트 (무지 의상, 로고는 후합성) |
| `daily/backlog.yaml` | 승인 대기 작업 목록 (매일 09:00 브리프에 보고) |
| `catalog/product_master.yaml/.csv` | 작업 품목 마스터 77품목 (공식 17개 카테고리 → 패션/패션잡화/라이프스타일) — 수정은 `catalog/build_catalog.py` |

실행:
```bash
pip install pillow pyyaml
python3 horu-lookbook/scripts/qa_check.py --manifest horu-lookbook/samples/sample_manifest.yaml \
  --rules horu-lookbook/config/brand_rules.yaml --spec horu-lookbook/config/lookbook_spec.yaml \
  --out horu-lookbook/samples/qa_report.md
```
