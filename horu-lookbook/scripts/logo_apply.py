#!/usr/bin/env python3
"""HÖRU 로고 실물 합성기 v2 — 로고·텍스트로고·슬로건·라벨을 상품 표면에 '입힌다' (크레딧 0, 로컬)

원칙 (2026-11-20 사장님: 품질 우선, 로고의 실제 상품 같은 자연스러움 최우선)
  - AI가 로고·글자를 생성하지 않는다 → BI 원본(SVG→PNG)과 공식 슬로건 렌더(brand_assets.py)만 사용
  - 로고 아트웍 자체(비율·회전·색)는 BI 규정 그대로, '물리적 표현'만 더한다
      ① 주름 따라가기  ② 빛 입히기  ③ 가공 방식별 소재감
  - 원본 PNG는 축소만 허용 (확대 금지)

가공 방식(technique)
  직접 가공 : print(나염) · reflective(반사 전사) · embroidery(자수) · emboss/deboss(형압) · engrave(레이저 각인)
  부착 가공 : woven_label(직조 라벨 봉제) · printed_label(라벨 부착 후 인쇄) · rubber_patch(러버 패치) · leather_patch(가죽 패치 형압)

에셋(asset): combined | symbol | wordmark | slogan:MAIN | slogan:SUB_A | slogan:SUB_B | lockup:<logo>:<SLOGAN>:<A|B> | 파일경로

예)
  python3 horu-lookbook/scripts/logo_apply.py --base in.png --asset symbol --center 1003 258 --width 46 \
      --technique embroidery --color tone --out out.png --zoom zoom.png
  python3 horu-lookbook/scripts/logo_apply.py --base in.png --asset wordmark --center 600 900 --width 80 \
      --technique woven_label --color "#FFFFFF" --label-color "#1A1E36" --out out.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    import cv2
    import numpy as np
    from PIL import Image
except ImportError as e:
    sys.exit(f"[오류] {e}. 'pip install numpy opencv-python-headless pillow' 후 실행하세요.")

sys.path.insert(0, str(Path(__file__).resolve().parent))
import brand_assets as BA  # noqa: E402

BI_COLORS = {"#040000", "#FFFFFF", "#1E5786", "#2E4032", "#1A1E36", "#A89C89"}
LABEL_TECHS = {"woven_label", "printed_label", "rubber_patch", "leather_patch"}
MIN_PX = {"combined": 100, "symbol": 40, "wordmark": 80}          # 스타일가이드 최소 규격(디지털)


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def gauss(img, sigma):
    if sigma <= 0:
        return img
    k = int(sigma * 4) | 1
    return cv2.GaussianBlur(img, (k, k), sigma)


# ---------- 에셋 → 알파 마스크 ----------
def asset_alpha(asset, width):
    if asset in BA.LOGOS:
        im = BA.logo_image(asset)
    elif asset.startswith("slogan:"):
        im, _ = BA.slogan_image(asset.split(":", 1)[1], lines=1, cap_px=200)
    elif asset.startswith("lockup:"):
        _, logo, sid, layout = asset.split(":")
        im, _ = BA.lockup(logo, sid, layout)
    else:
        im = Image.open(asset).convert("RGBA")
    if width > im.width:
        sys.exit(f"[중단] 원본({im.width}px)보다 크게 확대할 수 없습니다 — 더 큰 원본을 만드세요.")
    if asset in MIN_PX and width < MIN_PX[asset]:
        print(f"[경고] {asset} {width}px < 스타일가이드 디지털 최소 {MIN_PX[asset]}px — 실물 크기(mm) 기준 충족 여부 확인")
    h = round(im.height * width / im.width)                     # 비율 고정
    im = im.resize((width, h), Image.LANCZOS)
    return np.asarray(im, np.float32)[..., 3] / 255.0


def rounded_rect(h, w, r):
    m = np.zeros((h, w), np.uint8)
    cv2.rectangle(m, (r, 0), (w - r - 1, h - 1), 255, -1)
    cv2.rectangle(m, (0, r), (w - 1, h - r - 1), 255, -1)
    for cx, cy in ((r, r), (w - r - 1, r), (r, h - r - 1), (w - r - 1, h - r - 1)):
        cv2.circle(m, (cx, cy), r, 255, -1)
    return m.astype(np.float32) / 255.0


# ---------- 합성 ----------
def apply(base, art_a, cx, cy, technique, color, label_color=None, strength=1.0):
    H, W, _ = base.shape
    ah, aw = art_a.shape
    is_label = technique in LABEL_TECHS
    pad_l = int(max(aw, ah) * 0.22) if is_label else 0            # 라벨 여백
    lw, lh = aw + 2 * pad_l, ah + 2 * pad_l
    m = max(6, int(lw * 0.25))
    x0, y0 = int(cx - lw / 2) - m, int(cy - lh / 2) - m
    x1, y1 = x0 + lw + 2 * m, y0 + lh + 2 * m
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        sys.exit("[오류] 위치가 이미지 밖으로 나갑니다.")
    reg = base[y0:y1, x0:x1].copy()
    gh, gw = reg.shape[:2]

    logo = np.zeros((gh, gw), np.float32)
    logo[m + pad_l:m + pad_l + ah, m + pad_l:m + pad_l + aw] = art_a
    label = np.zeros((gh, gw), np.float32)
    if is_label:
        r = max(2, int(min(lw, lh) * (0.08 if technique in ("woven_label", "printed_label") else 0.22)))
        label[m:m + lh, m:m + lw] = rounded_rect(lh, lw, r)

    lum = reg @ np.array([0.299, 0.587, 0.114], np.float32)
    lum_s = gauss(lum, max(1.0, lw * 0.05))

    # ① 주름 따라가기
    gx = cv2.Sobel(lum_s, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum_s, cv2.CV_32F, 0, 1, ksize=3)
    gmax = max(1e-4, float(np.percentile(np.abs(np.stack([gx, gy])), 99)))
    amp = lw * (0.02 if is_label else 0.035) * strength           # 라벨은 원단보다 빳빳 → 덜 휨
    yy, xx = np.mgrid[0:gh, 0:gw].astype(np.float32)
    mapx, mapy = xx + gx / gmax * amp, yy + gy / gmax * amp
    logo = cv2.remap(logo, mapx, mapy, cv2.INTER_LINEAR, borderValue=0)
    label = cv2.remap(label, mapx, mapy, cv2.INTER_LINEAR, borderValue=0)

    # ② 빛 입히기
    cover = np.maximum(logo, label)
    inside = cover > 0.5
    ref = float(np.median(lum_s[inside])) if inside.any() else float(lum_s.mean())
    shade = np.clip(lum_s / max(ref, 1e-3), 0.45, 1.25)[..., None]
    texture = (lum - gauss(lum, 1.5))[..., None]
    base_col = np.median(reg[inside], axis=0) if inside.any() else reg.reshape(-1, 3).mean(0)
    light_bg = float(base_col.mean()) > 0.55

    def resolve(c, bg_light):
        if c == "tone":
            return base_col * (0.95 if light_bg else 0.78)
        if c == "tone_light":
            return np.clip(base_col * 1.10 + 0.04, 0, 1)
        if c == "auto":                                           # BI: 밝은 바탕→블랙, 어두운 바탕→화이트
            return hex_rgb("#040000") if bg_light else hex_rgb("#FFFFFF")
        return hex_rgb(c)

    col = np.broadcast_to(resolve(color, light_bg if not is_label else
                                  float(hex_rgb(label_color or "#FFFFFF").mean()) > 0.55), reg.shape).astype(np.float32)

    def relief_of(mask, s):
        hm = gauss(mask, max(0.6, lw * s))
        hx = cv2.Sobel(hm, cv2.CV_32F, 1, 0, ksize=3)
        hy = cv2.Sobel(hm, cv2.CV_32F, 0, 1, ksize=3)
        return np.clip(-(hx + hy) * 2.0, -1, 1)[..., None]         # 좌상단 광원

    a3 = logo[..., None]
    out = reg.copy()

    if technique in ("print", "reflective"):
        ink = col * 0.88 * shade + texture * 0.8
        if technique == "reflective":
            ink = ink + 0.12 * np.clip(shade - 1.0, 0, 1) * 4
        a_soft = gauss(logo, 0.7)[..., None] * 0.92
        out = reg * (1 - a_soft) + np.clip(ink, 0, 1) * a_soft

    elif technique == "embroidery":
        period = max(3.0, lw / 22.0)
        ang = np.deg2rad(38)
        stripes = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * np.cos(ang) + yy * np.sin(ang)) / period)
        noise = gauss(np.random.default_rng(7).normal(0, 1, (gh, gw)).astype(np.float32), 0.7)
        thread = (0.93 + 0.08 * stripes + 0.03 * noise)[..., None]
        relief = relief_of(logo, 0.012)
        dark_k = 0.10 if light_bg else 0.30
        sat = col * shade * thread * (1 + np.where(relief > 0, 0.25, dark_k) * relief)
        contact = gauss(np.roll(np.roll(logo, 1, 0), 1, 1), max(0.8, lw * 0.02))[..., None]
        out = reg * (1 - (0.06 if light_bg else 0.12) * contact * (1 - a3))
        a_e = np.clip(logo + 0.12 * noise * (logo > 0.05) * (logo < 0.95), 0, 1)[..., None]
        out = out * (1 - a_e) + np.clip(sat, 0, 1) * a_e

    elif technique in ("emboss", "deboss"):
        sign = 1 if technique == "emboss" else -1
        out = reg * (1 + 0.38 * sign * relief_of(logo, 0.012)) * (1 - 0.04 * a3)

    elif technique == "engrave":
        gray = (reg @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        etched = (gray * 0.55 + 0.06) * np.ones_like(reg)
        rel = relief_of(logo, 0.012)
        out = reg * (1 - a3) + etched * a3
        out = out * (1 - 0.25 * np.clip(-rel, 0, 1)) + 0.15 * np.clip(rel, 0, 1)

    elif is_label:
        lc = hex_rgb(label_color or ("#FFFFFF" if technique != "leather_patch" else "#A89C89"))
        l3 = label[..., None]
        noise = gauss(np.random.default_rng(3).normal(0, 1, (gh, gw)).astype(np.float32), 0.6)[..., None]
        if technique == "woven_label":                            # 직조: 가로·세로 결 + 테두리 봉제
            weave = 0.5 + 0.25 * (np.sin(2 * np.pi * xx / max(2.0, lw / 60)) + np.sin(2 * np.pi * yy / max(2.0, lw / 60)))
            surf = lc * (0.94 + 0.08 * weave[..., None] + 0.02 * noise)
            mark = col * (0.92 + 0.08 * weave[..., None])
        elif technique == "printed_label":                         # 라벨 부착 후 인쇄: 매끈한 새틴 + 잉크
            sheen = gauss(np.clip(shade[..., 0] - 1, 0, 1), lw * 0.05)[..., None] * 0.5   # 새틴 광택 (채널 유지)
            surf = lc * (0.97 + 0.02 * noise) + sheen
            mark = col * 0.9
        elif technique == "rubber_patch":                          # 러버: 두툼, 무광, 로고 양각
            surf = lc * (0.96 + 0.01 * noise)
            mark = col * (1 + 0.35 * relief_of(logo, 0.01))
        else:                                                      # 가죽 패치: 결 + 로고 형압(색 없음)
            grain = gauss(np.random.default_rng(5).normal(0, 1, (gh, gw)).astype(np.float32), 1.2)[..., None]
            surf = lc * (0.92 + 0.06 * grain)
            mark = surf * (1 - 0.30 * relief_of(logo, 0.012)) * 0.82
        label_shade = np.clip(shade, 0.7, 1.15)                    # 라벨은 원단보다 빛 변화가 덜함
        thick = 0.010 if "label" in technique else 0.03            # 두께 → 가장자리 입체·접촉 그림자
        edge = relief_of(label, thick)
        surf = surf * label_shade * (1 + 0.35 * edge)
        if technique in ("woven_label", "printed_label", "leather_patch"):  # 테두리 봉제선(점선)
            inner = cv2.erode((label > 0.5).astype(np.uint8), np.ones((3, 3), np.uint8),
                              iterations=max(2, int(min(lw, lh) * 0.07)))
            ring = cv2.morphologyEx(inner, cv2.MORPH_GRADIENT, np.ones((2, 2), np.uint8)).astype(np.float32)
            dash = (np.sin(2 * np.pi * (xx + yy) / max(3.0, lw / 30)) > 0).astype(np.float32)
            stitch = (ring * dash)[..., None]
            surf = surf * (1 - 0.35 * stitch)
        contact = gauss(np.roll(np.roll(label, 2, 0), 1, 1), max(1.0, lw * thick * 2))[..., None]
        out = reg * (1 - 0.28 * contact * (1 - l3))
        out = out * (1 - l3) + np.clip(surf, 0, 1) * l3
        a_m = gauss(logo, 0.5)[..., None] * l3
        out = out * (1 - a_m) + np.clip(mark * label_shade, 0, 1) * a_m
    else:
        sys.exit(f"[오류] 알 수 없는 technique: {technique}")

    res = base.copy()
    res[y0:y1, x0:x1] = np.clip(out, 0, 1)
    return res, (x0, y0, x1, y1)


def run(base_path, asset, center, width, technique, color, out, label_color=None, strength=1.0, zoom=None):
    """다른 스크립트(placement_matcher)에서 호출하는 진입점."""
    for c in (color, label_color):
        if c and c.startswith("#") and c.upper() not in BI_COLORS:
            sys.exit(f"[중단] {c}는 BI 허용색이 아닙니다: {', '.join(sorted(BI_COLORS))} 또는 tone/tone_light/auto")
    try:
        base = np.asarray(Image.open(base_path).convert("RGB"), np.float32) / 255.0
    except OSError as e:
        sys.exit(f"[오류] 바탕 이미지를 열 수 없습니다: {e}")
    alpha = asset_alpha(asset, int(width))
    res, (x0, y0, x1, y1) = apply(base, alpha, *center, technique, color, label_color, strength)
    img = Image.fromarray((res * 255 + 0.5).astype(np.uint8))
    img.save(out)
    if zoom:
        pad = (x1 - x0)
        box = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
        z = img.crop(box)
        z.resize((z.width * 4, z.height * 4), Image.LANCZOS).save(zoom)
    return out


def main():
    ap = argparse.ArgumentParser(description="HÖRU 로고 실물 합성기 v2")
    ap.add_argument("--base", required=True)
    ap.add_argument("--asset", default="symbol", help="combined|symbol|wordmark|slogan:ID|lockup:logo:ID:A|B|파일경로")
    ap.add_argument("--logo", help="(구버전 호환) 로고 PNG 경로")
    ap.add_argument("--center", nargs=2, type=float, required=True, metavar=("X", "Y"))
    ap.add_argument("--width", type=int, required=True)
    ap.add_argument("--technique", default="print",
                    choices=["print", "reflective", "embroidery", "emboss", "deboss", "engrave", *sorted(LABEL_TECHS)])
    ap.add_argument("--color", default="auto")
    ap.add_argument("--label-color")
    ap.add_argument("--strength", type=float, default=1.0)
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom")
    a = ap.parse_args()
    run(a.base, a.logo or a.asset, a.center, a.width, a.technique, a.color, a.out, a.label_color, a.strength, a.zoom)
    print(f"[완료] {a.logo or a.asset} / {a.technique} / {a.color} → {a.out}")


if __name__ == "__main__":
    main()
