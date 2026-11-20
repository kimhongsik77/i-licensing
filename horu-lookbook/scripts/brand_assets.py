#!/usr/bin/env python3
"""HÖRU 브랜드 에셋 생성기 — 로고·텍스트로고·슬로건·조합(lockup)을 투명 PNG로 만든다.

근거: HÖRU_StyleGuide_2026(최종) PART II 슬로건 시스템 (p.14~16)
  - 공식 슬로건 3종만 허용, 전부 대문자, 문구 변형·번역 금지
  - 서체: 디스플레이 Cambria / 본문 Arial
      → 작업환경 대체 서체: Caladea(Cambria와 글자폭 호환) / Liberation Sans(Arial과 글자폭 호환)
      → 실제 생산 파일은 정품 Cambria·Arial 또는 디자이너 SVG 아웃라인으로 교체할 것
  - 조합형: A 가로형(로고 좌·슬로건 우) / B 세로형(로고 상·슬로건 하)

사용 예:
  python3 horu-lookbook/scripts/brand_assets.py slogan --id SUB_B --lines 1 --out sub_b.png
  python3 horu-lookbook/scripts/brand_assets.py lockup --logo combined --id MAIN --layout B --out lockup.png
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
LOGO_DIR = ROOT / "assets" / "logo"
FONT_DIR_CANDIDATES = [Path("/usr/share/fonts/truetype/crosextra"), Path("/usr/share/fonts/truetype/liberation"),
                       ROOT / "assets" / "fonts"]

# 공식 슬로건 (스타일가이드 p.14) — 이 표 밖의 문구는 생성 불가
SLOGANS = {
    "MAIN":  {"text": "HARMONY OF ACTIVE AND NATURE",        "two_line": ["HARMONY OF ACTIVE", "AND NATURE"],
              "font": "display", "min_ratio_T": 0.3},
    "SUB_A": {"text": "THE SENSIBILITY AND WISDOM OF NORDIC", "two_line": ["THE SENSIBILITY AND", "WISDOM OF NORDIC"],
              "font": "display", "min_ratio_T": 0.2},
    "SUB_B": {"text": "LISTEN TO NATURE, MOVE WITH WISDOM",   "two_line": ["LISTEN TO NATURE,", "MOVE WITH WISDOM"],
              "font": "body", "min_ratio_T": 0.2},
}
FONTS = {"display": ["Cambria.ttf", "Caladea-Regular.ttf"], "body": ["Arial.ttf", "LiberationSans-Regular.ttf"],
         "display_bold": ["Cambria-Bold.ttf", "Caladea-Bold.ttf"], "body_bold": ["Arial-Bold.ttf", "LiberationSans-Bold.ttf"]}
LOGOS = {"combined": "combined_trim.png", "symbol": "symbol_trim.png", "wordmark": "wordmark_trim.png"}


def find_font(kind):
    for name in FONTS[kind]:
        for d in FONT_DIR_CANDIDATES:
            if (d / name).exists():
                return str(d / name), name
    sys.exit(f"[오류] {kind} 서체를 찾을 수 없습니다. assets/fonts/에 Cambria/Arial을 넣어 주세요.")


def render_text_lines(lines, kind, cap_px, tracking=0.12, color=(4, 0, 0, 255), align="center", leading=1.45):
    """대문자 줄들을 투명 PNG로. cap_px=대문자 높이(px), tracking=자간(대문자 높이 비율)."""
    path, used = find_font(kind)
    font = ImageFont.truetype(path, size=int(cap_px / 0.70))      # 대문자 높이 ≈ 글자크기 × 0.70
    track = cap_px * tracking

    def line_w(t):
        return sum(font.getlength(ch) for ch in t) + track * (len(t) - 1)

    widths = [line_w(t) for t in lines]
    W = int(max(widths) + cap_px)
    lh = int(cap_px * leading)
    H = int(lh * len(lines) + cap_px * 0.6)
    im = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    d = ImageDraw.Draw(im)
    for i, (t, w) in enumerate(zip(lines, widths)):
        x = (W - w) / 2 if align == "center" else cap_px / 2
        y = cap_px * 0.3 + i * lh
        for ch in t:
            d.text((x, y), ch, font=font, fill=color)
            x += font.getlength(ch) + track
    bbox = im.getbbox()
    return im.crop(bbox), used


def slogan_image(sid, lines=1, cap_px=120, color=(4, 0, 0, 255)):
    if sid not in SLOGANS:
        sys.exit(f"[중단] 공식 슬로건 ID가 아닙니다: {sid} (가능: {', '.join(SLOGANS)})")
    s = SLOGANS[sid]
    txt = [s["text"]] if lines == 1 else s["two_line"]
    assert all(t == t.upper() for t in txt), "슬로건은 대문자만 허용"
    return render_text_lines(txt, s["font"], cap_px, color=color)


def logo_image(name, color=None):
    im = Image.open(LOGO_DIR / LOGOS[name]).convert("RGBA")
    if color:
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (*Image.new("RGB", im.size, color[:3]).split(), a))
    return im


def lockup(logo, sid, layout="B", color=(4, 0, 0, 255)):
    """조합형: A 가로형(로고 좌·슬로건 우) / B 세로형(로고 상·슬로건 하). 슬로건 높이 ≥ T×비율 (T=HÖRU 글자 높이)."""
    lg = logo_image(logo, color)
    T = lg.height * (0.42 if logo == "combined" else 1.0 if logo == "wordmark" else 0.5)   # HÖRU 글자 높이 근사
    cap = max(T * SLOGANS[sid]["min_ratio_T"] * 1.15, 12)
    sl, used = slogan_image(sid, lines=2 if layout == "A" else 1, cap_px=cap, color=color)
    gap = int(T * 0.6)
    if layout == "A":
        W, H = lg.width + gap + sl.width, max(lg.height, sl.height)
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(lg, (0, (H - lg.height) // 2))
        out.alpha_composite(sl, (lg.width + gap, (H - sl.height) // 2))
    else:
        if sl.width > lg.width * 1.15:                           # 너무 길면 슬로건 폭을 로고의 1.15배로
            k = lg.width * 1.15 / sl.width
            sl = sl.resize((int(sl.width * k), int(sl.height * k)), Image.LANCZOS)
        W, H = max(lg.width, sl.width), lg.height + gap + sl.height
        out = Image.new("RGBA", (W, H), (0, 0, 0, 0))
        out.alpha_composite(lg, ((W - lg.width) // 2, 0))
        out.alpha_composite(sl, ((W - sl.width) // 2, lg.height + gap))
    return out, used


def main():
    ap = argparse.ArgumentParser(description="HÖRU 브랜드 에셋 생성기")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("slogan"); p.add_argument("--id", required=True); p.add_argument("--lines", type=int, default=1)
    p.add_argument("--cap", type=int, default=160); p.add_argument("--out", required=True)
    p = sp.add_parser("lockup"); p.add_argument("--logo", default="combined", choices=list(LOGOS))
    p.add_argument("--id", required=True); p.add_argument("--layout", default="B", choices=["A", "B"])
    p.add_argument("--out", required=True)
    a = ap.parse_args()
    if a.cmd == "slogan":
        im, used = slogan_image(a.id, a.lines, a.cap)
    else:
        im, used = lockup(a.logo, a.id, a.layout)
    im.save(a.out)
    note = "" if used.startswith(("Cambria", "Arial")) else f" (대체 서체 {used} — 생산 파일은 정품 서체로 교체)"
    print(f"[완료] {a.out} {im.size}{note}")


if __name__ == "__main__":
    main()
