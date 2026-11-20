#!/usr/bin/env python3
"""HÖRU 로고 실물 합성기 — 로고를 '그려 넣지' 않고 상품 표면에 '입힌다' (크레딧 0, 로컬 처리)

원칙 (사장님 지시 2026-11-20: 품질 우선, 로고의 실제 상품 같은 자연스러움 최우선)
  - AI에게 로고를 생성시키지 않는다 → 원본 BI 파일(SVG→PNG)만 사용 (글자·형태 깨짐 원천 차단)
  - 로고 형태 자체(비율·회전·색)는 BI 규정 그대로, '물리적 표현'만 더한다:
      ① 주름 따라가기   : 원단 밝기 기울기로 변위맵을 만들어 로고가 굴곡을 따라 휨
      ② 빛 입히기       : 원단에 떨어진 명암을 로고에도 곱해 같은 조명 아래 있게 함
      ③ 소재감          : 프린트=원단 결 비침 / 자수=실 결·입체감 / 반사=하이라이트 / 엠보·각인=색 없이 요철
  - 원본 PNG는 축소만 허용 (확대 금지 — BI 가이드 '번짐 방지')

사용 예:
  python3 horu-lookbook/scripts/logo_apply.py --base in.png --logo horu-lookbook/assets/logo/symbol_trim.png \
      --center 1030 255 --width 56 --technique embroidery --color tone --out out.png [--zoom zoom.png]

technique: print | embroidery | reflective | emboss | deboss | engrave
color    : '#040000' 등 HEX(BI 허용색) | tone(같은 계열 진하게) | tone_light(같은 계열 밝게)
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

BI_COLORS = {"#040000", "#FFFFFF", "#1E5786", "#2E4032", "#1A1E36", "#A89C89"}   # BI·스타일가이드 허용색


def hex_rgb(h):
    h = h.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def gauss(img, sigma):
    if sigma <= 0:
        return img
    k = int(sigma * 4) | 1
    return cv2.GaussianBlur(img, (k, k), sigma)


def load_logo_alpha(path, width):
    im = Image.open(path).convert("RGBA")
    if width > im.width:
        sys.exit(f"[중단] 로고 원본({im.width}px)보다 크게 확대할 수 없습니다 — SVG에서 더 큰 PNG를 만드세요.")
    h = round(im.height * width / im.width)                    # 비율 고정 (BI: 비율 변형 금지)
    im = im.resize((width, h), Image.LANCZOS)
    return np.asarray(im, np.float32)[..., 3] / 255.0


def apply(base_rgb, alpha_logo, cx, cy, technique, color, strength=1.0):
    H, W, _ = base_rgb.shape
    lh, lw = alpha_logo.shape
    m = max(6, int(lw * 0.25))                                  # 작업 여백
    x0, y0 = int(cx - lw / 2) - m, int(cy - lh / 2) - m
    x1, y1 = x0 + lw + 2 * m, y0 + lh + 2 * m
    if x0 < 0 or y0 < 0 or x1 > W or y1 > H:
        sys.exit("[오류] 로고 위치가 이미지 밖으로 나갑니다.")
    reg = base_rgb[y0:y1, x0:x1].copy()
    a = np.zeros(reg.shape[:2], np.float32)
    a[m:m + lh, m:m + lw] = alpha_logo

    lum = reg @ np.array([0.299, 0.587, 0.114], np.float32)
    lum_s = gauss(lum, max(1.0, lw * 0.05))

    # ① 주름 따라가기 — 밝기 기울기 방향으로 로고를 미세하게 밀어 굴곡을 표현
    gx = cv2.Sobel(lum_s, cv2.CV_32F, 1, 0, ksize=3)
    gy = cv2.Sobel(lum_s, cv2.CV_32F, 0, 1, ksize=3)
    gmax = max(1e-4, float(np.percentile(np.abs(np.stack([gx, gy])), 99)))
    amp = lw * 0.035 * strength
    yy, xx = np.mgrid[0:a.shape[0], 0:a.shape[1]].astype(np.float32)
    a = cv2.remap(a, xx + gx / gmax * amp, yy + gy / gmax * amp, cv2.INTER_LINEAR, borderValue=0)

    # ② 빛 입히기 — 원단 명암 비율을 로고에 곱함
    inside = a > 0.5
    ref = float(np.median(lum_s[inside])) if inside.any() else float(lum_s.mean())
    shade = np.clip(lum_s / max(ref, 1e-3), 0.45, 1.25)[..., None]
    texture = (lum - gauss(lum, 1.5))[..., None]                # 원단 결 (고주파)

    base_col = np.median(reg[inside], axis=0) if inside.any() else reg.reshape(-1, 3).mean(0)
    light_fabric = float(base_col.mean()) > 0.7
    if color == "tone":                                          # 같은 계열: 밝은 원단은 아주 살짝만 진하게
        col = base_col * (0.95 if light_fabric else 0.78)
    elif color == "tone_light":
        col = np.clip(base_col * 1.10 + 0.04, 0, 1)
    else:
        col = hex_rgb(color)
    col = np.broadcast_to(col, reg.shape).astype(np.float32)

    # 입체(높이) 맵 — 자수·엠보·각인 공통
    hmap = gauss(a, max(0.6, lw * 0.012))
    hx = cv2.Sobel(hmap, cv2.CV_32F, 1, 0, ksize=3)
    hy = cv2.Sobel(hmap, cv2.CV_32F, 0, 1, ksize=3)
    relief = np.clip(-(hx + hy) * 2.0, -1, 1)[..., None]         # 좌상단 광원

    out = reg.copy()
    a3 = a[..., None]
    if technique in ("print", "reflective"):
        ink = col * 0.88 * shade + texture * 0.8                 # 순색 대신 실제 잉크 톤, 원단 명암·결 반영
        if technique == "reflective":
            ink = ink + 0.12 * np.clip(shade - 1.0, 0, 1) * 4     # 빛 받는 부분만 은은한 반사
        a_soft = gauss(a, 0.7)[..., None] * 0.92                 # 잉크 경계는 살짝 부드럽게
        out = reg * (1 - a_soft) + np.clip(ink, 0, 1) * a_soft
    elif technique == "embroidery":
        period = max(3.0, lw / 22.0)                              # 실 굵기
        ang = np.deg2rad(38)
        stripes = 0.5 + 0.5 * np.sin(2 * np.pi * (xx * np.cos(ang) + yy * np.sin(ang)) / period)
        rng = np.random.default_rng(7)
        noise = gauss(rng.normal(0, 1, a.shape).astype(np.float32), 0.7)
        thread = (0.93 + 0.08 * stripes + 0.03 * noise)[..., None]
        dark_k = 0.10 if light_fabric else 0.30                 # 밝은 원단: 어두운 테두리 억제 (회색화 방지)
        sat = col * shade * thread * (1 + np.where(relief > 0, 0.25, dark_k) * relief)
        contact = gauss(np.roll(np.roll(a, 1, 0), 1, 1), max(0.8, lw * 0.02))[..., None]
        out = reg * (1 - (0.06 if light_fabric else 0.12) * contact * (1 - a3))              # 실이 원단 위에 올라온 접촉 음영
        a_e = np.clip(a + 0.12 * noise * (a > 0.05) * (a < 0.95), 0, 1)[..., None]  # 실 끝 보풀
        out = out * (1 - a_e) + np.clip(sat, 0, 1) * a_e
    elif technique in ("emboss", "deboss"):
        sign = 1 if technique == "emboss" else -1
        out = reg * (1 + 0.38 * sign * relief) * (1 - 0.04 * a3)  # 색 없이 요철만
    elif technique == "engrave":
        gray = (reg @ np.array([0.299, 0.587, 0.114], np.float32))[..., None]
        etched = (gray * 0.55 + 0.06) * np.ones_like(reg)         # 금속 각인: 어둡고 탈색
        out = reg * (1 - a3) + etched * a3
        out = out * (1 - 0.25 * np.clip(-relief, 0, 1)) + 0.15 * np.clip(relief, 0, 1)
    else:
        sys.exit(f"[오류] 알 수 없는 technique: {technique}")

    res = base_rgb.copy()
    res[y0:y1, x0:x1] = np.clip(out, 0, 1)
    return res, (x0, y0, x1, y1)


def main():
    ap = argparse.ArgumentParser(description="HÖRU 로고 실물 합성기")
    ap.add_argument("--base", required=True)
    ap.add_argument("--logo", required=True)
    ap.add_argument("--center", nargs=2, type=float, required=True, metavar=("X", "Y"))
    ap.add_argument("--width", type=int, required=True, help="로고 가로 px (원본보다 작게)")
    ap.add_argument("--technique", default="print",
                    choices=["print", "embroidery", "reflective", "emboss", "deboss", "engrave"])
    ap.add_argument("--color", default="tone")
    ap.add_argument("--strength", type=float, default=1.0, help="주름 따라가기 강도 (0=평면)")
    ap.add_argument("--out", required=True)
    ap.add_argument("--zoom", help="검수용 확대 이미지 저장 경로")
    a = ap.parse_args()

    if a.color.startswith("#") and a.color.upper() not in BI_COLORS:
        sys.exit(f"[중단] {a.color}는 BI 허용색이 아닙니다: {', '.join(sorted(BI_COLORS))} 또는 tone/tone_light")
    try:
        base = np.asarray(Image.open(a.base).convert("RGB"), np.float32) / 255.0
    except OSError as e:
        sys.exit(f"[오류] 바탕 이미지를 열 수 없습니다: {e}")
    alpha = load_logo_alpha(a.logo, a.width)
    res, (x0, y0, x1, y1) = apply(base, alpha, *a.center, a.technique, a.color, a.strength)
    img = Image.fromarray((res * 255 + 0.5).astype(np.uint8))
    img.save(a.out)
    if a.zoom:
        pad = (x1 - x0)
        box = (max(0, x0 - pad), max(0, y0 - pad), min(img.width, x1 + pad), min(img.height, y1 + pad))
        z = img.crop(box)
        z = z.resize((z.width * 4, z.height * 4), Image.LANCZOS)
        z.save(a.zoom)
    print(f"[완료] {a.technique}/{a.color} → {a.out}" + (f" (확대 검수: {a.zoom})" if a.zoom else ""))


if __name__ == "__main__":
    main()
