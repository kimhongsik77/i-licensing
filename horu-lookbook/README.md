# horu-lookbook

HÖRU 룩북·목업 자동화 작업 폴더.

| 파일 | 용도 |
|---|---|
| `PLAN.md` | 자동화·카테고리 확장·품질 업그레이드 전체 계획 |
| `config/brand_rules.yaml` | 브랜드 규칙 단일 기준 (팔레트·폰트·C-COPY·금지어·점수) |
| `config/lookbook_spec.yaml` | 템플릿 T01~T08 규격 + 카테고리 매트릭스 + 출력 프리셋 |
| `scripts/qa_check.py` | 1차 자동 QA 게이트 (점수 + 블로커) |
| `samples/` | 데모 manifest·합성 이미지·QA 리포트 (실제 룩북 원본 아님) |

실행:
```bash
pip install pillow pyyaml
python3 horu-lookbook/scripts/qa_check.py --manifest horu-lookbook/samples/sample_manifest.yaml \
  --rules horu-lookbook/config/brand_rules.yaml --spec horu-lookbook/config/lookbook_spec.yaml \
  --out horu-lookbook/samples/qa_report.md
```
