#!/usr/bin/env python3
"""HÖRU 룩북·목업 자동 QA 게이트 (1차 자동 검수)

사용:
    python3 horu-lookbook/scripts/qa_check.py \
        --manifest horu-lookbook/samples/sample_manifest.yaml \
        --rules horu-lookbook/config/brand_rules.yaml \
        --spec horu-lookbook/config/lookbook_spec.yaml \
        --out horu-lookbook/samples/qa_report.md

검사 항목 (점수 가중치는 brand_rules.yaml > scoring):
  brand        : 그래픽/텍스트 컬러가 6색 팔레트 내인지(ΔE), 폰트가 Cambria/Arial인지
  compliance   : 국가명·좌표·경쟁사 문구, 클로징 페이지 C-COPY 포함 여부
  image_quality: 해상도, 템플릿 비율 일치, 하이라이트 클리핑, 선명도(블러 의심)
  consistency  : 모델 템플릿의 model_id 등록 여부, 라인 내 모델 일관성
  info         : 템플릿별 필수 필드 누락

종료코드: 0 = 통과(pass_score 이상), 1 = 불합격, 2 = 입력 오류
※ AI 생성 결함(깨진 텍스트·손가락 등)은 이 스크립트로 판별 불가 → 2차 비전 검수/사람 검수 단계에서 확인
"""
from __future__ import annotations

import argparse
import json
import math
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path

try:
    import yaml
    from PIL import Image, ImageFilter, ImageStat
except ImportError as e:  # 기본 에러 처리: 의존성 안내
    sys.exit(f"[오류] 필요한 패키지가 없습니다: {e}. 'pip install pillow pyyaml' 후 다시 실행하세요.")


# ---------- 유틸 ----------
def hex_to_lab(hex_color: str) -> tuple[float, float, float]:
    """HEX → CIE Lab (D65). 팔레트 근접도(ΔE76) 계산용."""
    h = hex_color.lstrip("#")
    rgb = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    lin = [((c + 0.055) / 1.055) ** 2.4 if c > 0.04045 else c / 12.92 for c in rgb]
    x = (lin[0] * 0.4124 + lin[1] * 0.3576 + lin[2] * 0.1805) / 0.95047
    y = (lin[0] * 0.2126 + lin[1] * 0.7152 + lin[2] * 0.0722) / 1.0
    z = (lin[0] * 0.0193 + lin[1] * 0.1192 + lin[2] * 0.9505) / 1.08883
    f = lambda t: t ** (1 / 3) if t > 0.008856 else 7.787 * t + 16 / 116  # noqa: E731
    fx, fy, fz = f(x), f(y), f(z)
    return 116 * fy - 16, 500 * (fx - fy), 200 * (fy - fz)


def delta_e(a: str, b: str) -> float:
    la, lb = hex_to_lab(a), hex_to_lab(b)
    return math.dist(la, lb)


def parse_ratio(r: str) -> float:
    w, h = r.split(":")
    return float(w) / float(h)


@dataclass
class Result:
    page: str
    category: str
    ok: bool
    message: str


@dataclass
class Report:
    results: list[Result] = field(default_factory=list)

    def add(self, page, category, ok, message):
        self.results.append(Result(page, category, ok, message))


# ---------- 검사 ----------
def check_brand(page, rules, rep):
    pid = page["id"]
    palette = list(rules["palette"].values())
    tol = rules["palette_tolerance_deltaE"]
    for c in page.get("graphic_colors", []):
        nearest = min(palette, key=lambda p: delta_e(c, p))
        d = delta_e(c, nearest)
        rep.add(pid, "brand", d <= tol,
                f"컬러 {c} → 최근접 {nearest} (ΔE {d:.1f}, 허용 {tol})")
    allowed = {rules["typography"]["display"], rules["typography"]["body"]}
    for f in page.get("fonts", []):
        rep.add(pid, "brand", f in allowed, f"폰트 '{f}' {'허용' if f in allowed else '규정 외 (Cambria/Arial만 허용)'}")


def check_compliance(page, rules, rep):
    pid = page["id"]
    text = page.get("text", "") or ""
    comp = rules["compliance"]
    def term_re(t):  # 영문 금지어는 단어 경계로 검사 (예: EMIS가 premise에 오탐되지 않게)
        return rf"\b{re.escape(t)}\b" if t.isascii() else re.escape(t)
    hits = [t for t in comp["forbidden_terms"] + comp.get("competitor_terms", [])
            if re.search(term_re(t), text, re.IGNORECASE)]
    hits += [m.group(0) for p in comp["forbidden_patterns"] for m in re.finditer(p, text)]
    rep.add(pid, "compliance", not hits,
            "금지어 없음" if not hits else f"금지어/좌표 발견: {', '.join(hits)}")
    if page["template"] in rules["c_copy"]["required_on_templates"]:
        for key in ("long", "short"):
            phrase = rules["c_copy"][key]
            rep.add(pid, "compliance", phrase in text, f"C-COPY({key}) {'포함' if phrase in text else '누락'}")


def check_image(page, rules, spec, base, preset, rep):
    pid = page["id"]
    img_path = page.get("image")
    if not img_path:
        rep.add(pid, "image_quality", False, "이미지 경로 없음")
        return
    path = (base / img_path).resolve()
    if not path.exists():
        rep.add(pid, "image_quality", False, f"파일 없음: {img_path}")
        return
    try:
        im = Image.open(path)
        im.load()
    except Exception as e:  # 손상 파일
        rep.add(pid, "image_quality", False, f"이미지 열기 실패: {e}")
        return

    w, h = im.size
    need = rules["image"]["min_long_edge_px"][preset]
    rep.add(pid, "image_quality", max(w, h) >= need, f"해상도 {w}x{h} (장변 최소 {need}px)")

    tpl = spec["templates"].get(page["template"], {})
    if "aspect" in tpl:
        target = parse_ratio(tpl["aspect"])
        actual = w / h
        ok = abs(actual - target) / target <= 0.02
        rep.add(pid, "image_quality", ok, f"비율 {actual:.3f} vs 규격 {tpl['aspect']}({target:.3f})")

    gray = im.convert("L")
    gray.thumbnail((1024, 1024))
    hist = gray.histogram()
    clipped = sum(hist[250:]) / max(1, sum(hist))
    lim = rules["image"]["max_clipped_highlight_ratio"]
    rep.add(pid, "image_quality", clipped <= lim, f"하이라이트 클리핑 {clipped:.1%} (상한 {lim:.0%})")

    lap = gray.filter(ImageFilter.Kernel((3, 3), [0, 1, 0, 1, -4, 1, 0, 1, 0], scale=1, offset=128))
    sharp = ImageStat.Stat(lap).var[0]
    smin = rules["image"]["min_sharpness"]
    rep.add(pid, "image_quality", sharp >= smin, f"선명도 {sharp:.0f} (최소 {smin}, 낮으면 블러 의심)")


def check_consistency(pages, spec, registry, rep):
    line_models: dict[str, set] = {}
    for page in pages:
        tpl_key = page["template"].split("_")[0]
        needs_model = tpl_key in ("T01", "T02", "T04", "T05")
        if not needs_model:
            continue
        mid = page.get("model_id")
        ok = bool(mid) and mid in registry
        rep.add(page["id"], "consistency", ok,
                f"model_id '{mid}' {'등록됨' if ok else '미등록/누락 — 얼굴 일관성 보장 불가'}")
        if page.get("line") and mid:
            line_models.setdefault(page["line"], set()).add(mid)
    for line, models in line_models.items():
        rep.add(f"LINE:{line}", "consistency", len(models) <= 2,
                f"라인 내 모델 {len(models)}명 ({', '.join(sorted(models))}) — 3명 이상이면 일관성 저하")


def check_model_specs(registry, rules, rep):
    """모델 레지스트리의 체형이 body_spec(성별별 최소 키·최대 몸무게)을 충족하는지 검사."""
    spec = rules.get("virtual_model_policy", {}).get("body_spec")
    if not spec or not isinstance(registry, dict):
        return
    for mid, m in registry.items():
        g = (m or {}).get("gender")
        if g not in spec:
            rep.add(f"MODEL:{mid}", "consistency", False, f"성별 미기재/알 수 없음 '{g}' — female/male로 등록 필요")
            continue
        h, w = m.get("height_cm"), m.get("weight_kg")
        need = spec[g]
        ok = h is not None and w is not None and h >= need["min_height_cm"] and w <= need["max_weight_kg"]
        rep.add(f"MODEL:{mid}", "consistency", ok,
                f"{g} {h}cm/{w}kg (기준 {need['min_height_cm']}cm 이상·{need['max_weight_kg']}kg 이하)")


def check_logo_review(page, rules, rep):
    """로고 자연스러움 2차 검수 결과(1~5점) 확인 — 로고가 들어간 페이지는 필수, 항목당 4점 미만이면 블로커."""
    q = rules.get("quality_first", {})
    items = q.get("logo_review", {})
    if not items or not page.get("has_logo"):
        return
    review = page.get("logo_review") or {}
    need = q.get("pass_min_each", 4)
    for key, desc in items.items():
        v = review.get(key)
        ok = isinstance(v, (int, float)) and v >= need
        rep.add(page["id"], "logo_realism", ok,
                f"{key} {v if v is not None else '미검수'}/5 (기준 {need}) — {desc}")


def check_info(page, spec, rep):
    tpl = spec["templates"].get(page["template"])
    if tpl is None:
        rep.add(page["id"], "info", False, f"알 수 없는 템플릿 '{page['template']}'")
        return
    fields = page.get("fields", {}) or {}
    missing = [f for f in tpl.get("fields", []) if not fields.get(f)]
    rep.add(page["id"], "info", not missing,
            "필수 필드 충족" if not missing else f"필수 필드 누락: {', '.join(missing)}")


def check_document(pages, rules, rep):
    req = rules["c_copy"]["required_on_templates"]
    has = any(p["template"] in req for p in pages)
    rep.add("DOC", "compliance", has, f"클로징 페이지({', '.join(req)}) {'있음' if has else '없음 — C-COPY 누락'}")


# ---------- 점수 ----------
def score(rep, rules):
    weights = rules["scoring"]["weights"]
    detail = {}
    total = 0.0
    for cat, wgt in weights.items():
        items = [r for r in rep.results if r.category == cat]
        ratio = (sum(r.ok for r in items) / len(items)) if items else 1.0
        detail[cat] = {"score": round(wgt * ratio, 1), "max": wgt, "checks": len(items),
                       "fails": sum(not r.ok for r in items)}
        total += wgt * ratio
    return round(total, 1), detail


def verdict(total, rep, rules):
    """합격 판정: 점수 + 블로커(예: 컴플라이언스) 동시 충족해야 PASS."""
    blockers = rules["scoring"].get("blockers", [])
    blocked = [r for r in rep.results if r.category in blockers and not r.ok]
    return total >= rules["scoring"]["pass_score"] and not blocked, blocked


def write_markdown(out, doc_title, total, detail, rep, pass_score, passed, blocked):
    lines = [f"# QA 리포트 — {doc_title}", "",
             f"**총점 {total} / 100 → {'PASS' if passed else 'FAIL'}** (합격선 {pass_score}"
             + (f", 블로커 {len(blocked)}건으로 불합격" if blocked else "") + ")", "",
             "| 영역 | 점수 | 검사수 | 실패 |", "|---|---|---|---|"]
    for cat, d in detail.items():
        lines.append(f"| {cat} | {d['score']} / {d['max']} | {d['checks']} | {d['fails']} |")
    lines += ["", "## 실패 항목 (수정 필요)", "", "| 페이지 | 영역 | 내용 |", "|---|---|---|"]
    fails = [r for r in rep.results if not r.ok]
    lines += [f"| {r.page} | {r.category} | {r.message} |" for r in fails] or ["| - | - | 없음 |"]
    lines += ["", "## 전체 로그", ""]
    lines += [f"- {'✅' if r.ok else '❌'} [{r.page}] {r.category}: {r.message}" for r in rep.results]
    lines += ["", "> 자동 검수 범위 밖: AI 생성 결함(손·텍스트 왜곡), 로고 위치/보호공간, 무드 적합성 → 2·3차 검수에서 확인"]
    out.write_text("\n".join(lines), encoding="utf-8")


def main():
    ap = argparse.ArgumentParser(description="HÖRU 룩북 자동 QA")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--rules", required=True)
    ap.add_argument("--spec", required=True)
    ap.add_argument("--out", default="qa_report.md")
    args = ap.parse_args()

    try:
        manifest = yaml.safe_load(Path(args.manifest).read_text(encoding="utf-8"))
        rules = yaml.safe_load(Path(args.rules).read_text(encoding="utf-8"))
        spec = yaml.safe_load(Path(args.spec).read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        print(f"[오류] 입력 파일을 읽을 수 없습니다: {e}", file=sys.stderr)
        return 2

    base = Path(args.manifest).parent
    doc = manifest.get("document", {})
    preset = doc.get("preset", "web")
    raw_registry = manifest.get("model_registry", []) or []
    registry = set(raw_registry)  # list 또는 dict(id → 체형정보) 모두 지원
    pages = manifest.get("pages", [])
    if not pages:
        print("[오류] manifest에 pages가 없습니다.", file=sys.stderr)
        return 2

    rep = Report()
    for p in pages:
        check_brand(p, rules, rep)
        check_compliance(p, rules, rep)
        check_image(p, rules, spec, base, preset, rep)
        check_info(p, spec, rep)
        check_logo_review(p, rules, rep)
    check_consistency(pages, spec, registry, rep)
    check_model_specs(raw_registry, rules, rep)
    check_document(pages, rules, rep)

    total, detail = score(rep, rules)
    pass_score = rules["scoring"]["pass_score"]
    passed, blocked = verdict(total, rep, rules)
    out = Path(args.out)
    write_markdown(out, doc.get("title", "untitled"), total, detail, rep, pass_score, passed, blocked)
    out.with_suffix(".json").write_text(json.dumps(
        {"total": total, "pass": passed, "blockers": len(blocked), "detail": detail,
         "results": [r.__dict__ for r in rep.results]}, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"총점 {total} ({'PASS' if passed else 'FAIL'}, 블로커 {len(blocked)}건) → {out}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
