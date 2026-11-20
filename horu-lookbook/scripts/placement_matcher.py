#!/usr/bin/env python3
"""HÖRU 로고 배치 매칭기 — 상품·벤치마크·사진 정보를 넣으면 '어디에·무엇을·어떻게' 입힐지 정하고 합성까지 한다.

흐름
  1) 벤치마크 레시피(logo_placement_library.yaml > recipes)에서 상품 유형별 배치 후보를 가져온다
  2) 사진 방향(view)과 맞지 않는 위치는 제외 (정면 사진에 뒷목 로고 X)
  3) 실물 크기(cm) → 픽셀 환산 (px_per_cm), 기준점(landmark) + offset으로 위치 계산
  4) 가공 방식 최소 규격 검사: 로고 선 굵기·슬로건 글자 높이를 mm로 환산 → 미달이면 다음 에셋 후보로 대체
  5) 슬로건 규칙(slogan_rules.yaml): 같은 상품에 로고가 하나도 없으면 슬로건 단독 배치 금지
  6) logo_apply.run 으로 순서대로 합성, 계획서(JSON·MD) 저장

예)
  python3 horu-lookbook/scripts/placement_matcher.py --base p3.png --product top --benchmark lululemon --view front \
      --px-per-cm 7.7 --landmark neck=585,232 --landmark shoulder_left=760,300 --out p3_matched.png
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import numpy as np
import yaml
from PIL import Image
from scipy import ndimage

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_assets as BA  # noqa: E402
import logo_apply as LA    # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
LIB = yaml.safe_load((ROOT / "config" / "logo_placement_library.yaml").read_text(encoding="utf-8"))
RENDER = {"silicone": "print", "puff_embroidery": "embroidery"}      # 합성기 표현 방식으로 매핑


def asset_metrics(asset):
    """에셋의 '선 굵기/가로폭' 비율과 '글자(대문자) 높이/가로폭' 비율 — 실물 mm 환산용."""
    a = LA.asset_alpha(asset, min(1000, _native_width(asset))) > 0.5
    dist = ndimage.distance_transform_edt(a)
    ridge = dist[(dist >= ndimage.maximum_filter(dist, 3)) & (dist > 1)]
    stroke = float(np.median(ridge)) * 2 if ridge.size else 1.0
    w = a.shape[1]
    text_h = a.shape[0] if asset.startswith("slogan:") else None   # 한 줄 슬로건: 높이 ≈ 대문자 높이
    return stroke / w, (text_h / w if text_h else None)


def _native_width(asset):
    if asset in BA.LOGOS:
        return BA.logo_image(asset).width
    if asset.startswith("slogan:"):
        return BA.slogan_image(asset.split(":", 1)[1], 1, 200)[0].width
    if asset.startswith("lockup:"):
        _, lg, sid, lay = asset.split(":")
        return BA.lockup(lg, sid, lay)[0].width
    return Image.open(asset).width


def plan(product, benchmark, view, ppc, landmarks, size="mid"):
    if benchmark not in LIB["recipes"]:
        sys.exit(f"[오류] 레시피 없는 벤치마크: {benchmark} (가능: {', '.join(LIB['recipes'])})")
    recipe = LIB["recipes"][benchmark].get(product)
    if not recipe:
        sys.exit(f"[오류] {benchmark}에 {product} 레시피가 없습니다.")
    places = LIB["products"][product]["placements"]
    steps, skipped = [], []
    for item in recipe:
        p = places[item["placement"]]
        if p["view"] != view:
            skipped.append(f"{item['placement']}: 사진 방향 {view} ≠ 위치 방향 {p['view']} → 이 컷에선 생략")
            continue
        lm = landmarks.get(p["landmark"])
        if lm is None:
            skipped.append(f"{item['placement']}: 기준점 '{p['landmark']}' 좌표 없음 → 생략")
            continue
        lo, hi = p["width_cm"]
        width_cm = {"small": lo, "mid": (lo + hi) / 2, "large": hi}[size]
        tech = item["technique"]
        rule = LIB["techniques"][tech]
        chosen, reasons = None, []
        assets = list(item["assets"])
        if LIB.get("symbol_standalone") == "avoid" and "symbol" in assets:   # 부엉이 단독은 항상 최후 후보
            assets = [x for x in assets if x != "symbol"] + ["symbol"]
        for asset in assets:
            stroke_r, text_r = asset_metrics(asset)
            wcm = width_cm
            if "max_height_cm" in p:                                   # 높이 제한 (캡 등)
                h_ratio = LA.asset_alpha(asset, 400).shape[0] / 400
                wcm = min(wcm, p["max_height_cm"] / max(h_ratio, 1e-3))
            stroke_mm = stroke_r * wcm * 10
            text_mm = text_r * wcm * 10 if text_r else None
            if stroke_mm < rule["min_stroke_mm"]:
                reasons.append(f"{asset}: 선 굵기 {stroke_mm:.2f}mm < {tech} 최소 {rule['min_stroke_mm']}mm")
                continue
            if text_mm is not None and text_mm < rule["min_text_mm"]:
                reasons.append(f"{asset}: 글자 높이 {text_mm:.1f}mm < {tech} 최소 {rule['min_text_mm']}mm")
                continue
            chosen = (asset, wcm, stroke_mm, text_mm)
            break
        if not chosen:
            skipped.append(f"{item['placement']}: 모든 에셋이 {tech} 최소 규격 미달 — " + "; ".join(reasons))
            continue
        asset, wcm, stroke_mm, text_mm = chosen
        if asset == "symbol" and LIB.get("symbol_standalone") == "avoid":
            reasons.append("⚠ 부엉이 심볼 단독 사용(예외) — 다른 로고가 모두 규격 미달. 사장님 확인 필요")
        dx, dy = p["offset_cm"]
        sign = 1 if view in ("front", "side") else -1               # 정면: 착용자 왼쪽 = 화면 오른쪽
        if p.get("anchor") == "edge":                              # 가장자리 기준 → 로고 폭 절반만큼 더 안쪽
            dx = dx + (wcm / 2 if dx >= 0 else -wcm / 2)
        cx, cy = lm[0] + sign * dx * ppc, lm[1] + dy * ppc
        steps.append({"placement": item["placement"], "asset": asset, "technique": tech,
                      "render_as": RENDER.get(tech, tech), "color": item.get("color", "auto"),
                      "label_color": item.get("label_color"), "center_px": [round(cx), round(cy)],
                      "width_cm": round(wcm, 2), "width_px": max(8, round(wcm * ppc)),
                      "stroke_mm": round(stroke_mm, 2), "text_mm": round(text_mm, 1) if text_mm else None,
                      "replaced": reasons, "look": rule["look"], "src": p.get("src", "")})
    # 슬로건 단독 금지(해석 규칙): 로고가 하나도 없으면 슬로건 단계 제거
    if steps and all(s["asset"].startswith("slogan:") for s in steps):
        skipped += [f"{s['placement']}: 같은 상품에 로고 없이 슬로건 단독 → 제외" for s in steps]
        steps = []
    return steps, skipped


def garment_fit(base_path, cx, cy, w_px, h_px, toward_x):
    """로고 영역이 같은 원단 위에 있는지 검사. 중심부 원단 색과 크게 다른 픽셀(배경·손·이음선)이 많으면 침범.
    침범 시 toward_x 방향(의상 안쪽)으로 최대 12단계 이동해 들어맞는 위치를 찾는다."""
    im = np.asarray(Image.open(base_path).convert("RGB"), np.float32) / 255.0
    H, W, _ = im.shape

    def ratio(x, y):
        x0, x1 = int(x - w_px / 2), int(x + w_px / 2)
        y0, y1 = int(y - h_px / 2), int(y + h_px / 2)
        if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
            return 1.0
        reg = im[y0:y1, x0:x1]
        core = im[int(y - h_px / 4):int(y + h_px / 4) + 1, int(x - w_px / 6):int(x + w_px / 6) + 1].reshape(-1, 3)
        ref = np.median(core, axis=0)
        diff = np.abs(reg - ref).max(axis=2)
        return float((diff > 0.18).mean())

    r0 = ratio(cx, cy)
    if r0 <= 0.03:
        return cx, r0, 0
    step = max(2, w_px * 0.1)
    for k in range(1, 13):
        nx = cx + toward_x * step * k
        r = ratio(nx, cy)
        if r <= 0.03:
            return nx, r, k
    return cx, r0, -1


def main():
    ap = argparse.ArgumentParser(description="HÖRU 로고 배치 매칭기")
    ap.add_argument("--base", required=True)
    ap.add_argument("--product", required=True, choices=list(LIB["products"]))
    ap.add_argument("--benchmark", required=True)
    ap.add_argument("--view", default="front", choices=["front", "back", "side", "inside"])
    ap.add_argument("--px-per-cm", type=float, required=True, help="사진 속 1cm가 몇 px인지 (예: 어깨너비 px ÷ 실제 cm)")
    ap.add_argument("--landmark", action="append", default=[], help="이름=x,y (예: neck=585,232)")
    ap.add_argument("--size", default="mid", choices=["small", "mid", "large"])
    ap.add_argument("--out", required=True)
    ap.add_argument("--dry-run", action="store_true", help="계획만 출력")
    a = ap.parse_args()

    lms = {}
    for s in a.landmark:
        try:
            k, v = s.split("=")
            x, y = v.split(",")
            lms[k] = (float(x), float(y))
        except ValueError:
            sys.exit(f"[오류] landmark 형식: 이름=x,y — 받은 값: {s}")

    steps, skipped = plan(a.product, a.benchmark, a.view, a.px_per_cm, lms, a.size)
    out = Path(a.out)
    md = [f"# 로고 배치 계획 — {out.name}", "", f"- 상품 {a.product} / 벤치마크 {a.benchmark} / 사진 {a.view} / {a.px_per_cm}px=1cm", "",
          "| 위치 | 에셋 | 가공 | 실물폭 | 선굵기 | 글자높이 | 위치(px) |", "|---|---|---|---|---|---|---|"]
    md += [f"| {s['placement']} | {s['asset']} | {s['technique']} | {s['width_cm']}cm | {s['stroke_mm']}mm | "
           f"{s['text_mm'] or '-'}mm | {s['center_px']} |" for s in steps]
    if skipped:
        md += ["", "## 제외·대체 사유", ""] + [f"- {x}" for x in skipped]
    for s in steps:
        if s["replaced"]:
            md.append(f"- {s['placement']} 대체: " + "; ".join(s["replaced"]))
    out.with_suffix(".plan.md").write_text("\n".join(md), encoding="utf-8")
    out.with_suffix(".plan.json").write_text(json.dumps({"steps": steps, "skipped": skipped}, ensure_ascii=False, indent=2), encoding="utf-8")
    print("\n".join(md))
    if a.dry_run or not steps:
        return
    for s in steps:                                                # 의상 영역 침범 검사 (합성 전)
        hpx = max(4, round(s["width_px"] * LA.asset_alpha(s["asset"], 400).shape[0] / 400))
        img_w = Image.open(a.base).width
        toward = 1 if s["center_px"][0] < img_w / 2 else -1
        nx, r, k = garment_fit(a.base, s["center_px"][0], s["center_px"][1], s["width_px"], hpx, toward)
        if k > 0:
            print(f"[보정] {s['placement']}: 의상 밖 침범 → 안쪽으로 {k}단계 이동 (침범 {r:.0%})")
            s["center_px"][0] = round(nx)
        elif k < 0:
            print(f"[경고] {s['placement']}: 의상 영역 밖 침범 {r:.0%} — 자동 보정 실패, 위치·크기 수동 확인 필요")
    cur = a.base
    for s in steps:
        cur = LA.run(cur, s["asset"], s["center_px"], s["width_px"], s["render_as"], s["color"], str(out),
                     s["label_color"])
    print(f"\n[완료] {len(steps)}개 위치 합성 → {out}")


if __name__ == "__main__":
    main()
