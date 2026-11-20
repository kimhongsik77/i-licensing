#!/usr/bin/env python3
"""품목 마스터(catalog) → 촬영 컷 대기열(daily/work_queue.yaml)

규칙
  - 상태 '작업대기열' 품목만 대상 (2026-11-20: Phase 1 28품목, 키즈 보류)
  - 촬영 방식별 컷 구성 (1컷 = 완성컷 1장 목표)
      착장       → 착장 풀샷 1 + 로고 디테일 1                (모델 필요)
      누끼+착장  → 누끼 정면 1 + 로고 디테일 1 + 착장 1        (착장만 모델 필요)
      누끼+연출  → 누끼 정면 1 + 로고 디테일 1 + 연출 1
      누끼       → 누끼 정면 1 + 로고 디테일 1
      연출       → 연출 2
  - 모델 컷은 BL-001(모델 기준 시트 확정) 전까지 '모델 확정 대기' → 모델 없는 컷부터 진행
  - 모델 배정: 여성 전용 품목은 여성 모델, 나머지는 P1 4명 순환
사용: python3 horu-lookbook/daily/build_queue.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
CAT = ROOT / "catalog" / "product_master.yaml"
REG = ROOT / "config" / "model_registry.yaml"
OUT = ROOT / "daily" / "work_queue.yaml"
FEMALE_ONLY = ("레깅스", "스포츠 브라", "스커트", "원피스 수영복")
SHOTS = {
    "착장": [("착장 풀샷", "T05", True), ("로고 디테일 클로즈업", "T04", True)],
    "누끼+착장": [("누끼 정면", "T06", False), ("로고 디테일 클로즈업", "T06", False), ("착장 컷", "T05", True)],
    "누끼+연출": [("누끼 정면", "T06", False), ("로고 디테일 클로즈업", "T06", False), ("연출 컷", "T03", False)],
    "누끼": [("누끼 정면", "T06", False), ("로고 디테일 클로즈업", "T06", False)],
    "연출": [("연출 컷 A", "T03", False), ("연출 컷 B", "T05", False)],
}


def main():
    try:
        items = yaml.safe_load(CAT.read_text(encoding="utf-8"))["items"]
        models = yaml.safe_load(REG.read_text(encoding="utf-8"))["models"]
    except (OSError, KeyError, yaml.YAMLError) as e:
        sys.exit(f"[오류] 품목 마스터/모델 등록부를 읽을 수 없습니다: {e}")
    p1 = [k for k, m in models.items() if m["priority"] == "P1"]
    p1_f = [k for k in p1 if models[k]["gender"] == "female"]
    approved = {k for k, m in models.items() if m.get("status") == "approved"}
    old = {s["shot_id"]: s for s in (yaml.safe_load(OUT.read_text(encoding="utf-8")) or {}).get("shots", [])} if OUT.exists() else {}

    shots, rot = [], 0
    for it in items:
        if it["상태"] != "작업대기열":
            continue
        recipe = SHOTS.get(it["촬영 방식"].split("(")[0])
        if not recipe:
            continue
        item_model = None                                   # 같은 품목 = 같은 모델 (품목 단위 배정)
        if any(r[2] for r in recipe):
            pool = p1_f if any(k in it["품목명"] for k in FEMALE_ONLY) else p1
            item_model = pool[rot % len(pool)]
            rot += 1
        for n, (label, tpl, needs_model) in enumerate(recipe, 1):
            sid = f"{it['품목ID']}-S{n}"
            model = item_model if needs_model else None
            ready = (not needs_model) or (model in approved)
            prev = old.get(sid, {})
            shots.append({"shot_id": sid, "품목ID": it["품목ID"], "품목명": it["품목명"], "카테고리": it["카테고리"],
                          "컷": label, "템플릿": tpl, "모델": model, "매칭기유형": it["매칭기유형"],
                          "벤치마크": it["벤치마크(글로벌/국내)"], "로고": it["로고 기본 적용"],
                          "상태": prev.get("상태") if prev.get("상태") in ("진행", "완료") else
                          ("준비완료" if ready else "모델 확정 대기(BL-001)")})
    # 정렬: 준비완료 먼저 → 카테고리 순 유지
    shots.sort(key=lambda s: (s["상태"] != "준비완료", s["상태"] == "완료"))
    OUT.write_text(yaml.safe_dump({"note": "자동 생성 — 수정은 catalog/build_catalog.py 또는 model_registry.yaml에서",
                                   "shots": shots}, allow_unicode=True, sort_keys=False), encoding="utf-8")
    from collections import Counter
    c = Counter(s["상태"] for s in shots)
    print(f"컷 {len(shots)}개 — " + ", ".join(f"{k} {v}" for k, v in c.items()))


if __name__ == "__main__":
    main()
