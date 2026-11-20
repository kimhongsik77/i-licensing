#!/usr/bin/env python3
"""HÖRU 일일 작업 설계기 — 매일 09:00 승인용 브리프 생성

쉬운 설명:
  1) 어제 실적(완성컷·실패컷·크레딧 사용)을 모아 리포트를 만든다.
  2) 툴별 '오늘 써도 되는 크레딧'을 계산한다 (= 남은 크레딧 ÷ 초기화까지 남은 날, 일일 상한 적용).
     → 크레딧이 초기화일까지 고르게 버티도록 '페이스 조절'.
  3) 그 크레딧으로 만들 수 있는 원본컷 + 로컬 합성컷 + 파생컷으로 50컷 달성 계획을 세운다.
  4) 사장님 승인 전에는 작업(relay 작업 카드 생성)이 잠겨 있다.

명령:
  brief   [--date 2026-11-21]                  # 전일 리포트 + 오늘 설계 → briefs/날짜.md
  approve --date 2026-11-21 [--note "..."]     # 승인 → 작업 시작 가능
  record  --date 2026-11-21 --tool Canva --ops 5 --finished 12 --failed 3 [--kind model_fit]
  status  [--date ...]
"""
from __future__ import annotations

import argparse
import json
import math
import sys
from datetime import date, datetime, timedelta
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("[오류] pyyaml이 필요합니다: pip install pyyaml")

ROOT = Path(__file__).resolve().parent.parent          # horu-lookbook/
CFG = ROOT / "config" / "daily_plan.yaml"
LADDER = ROOT / "relay" / "tool_ladder.yaml"
DAILY = ROOT / "daily"
PLANS, LOGS, BRIEFS = DAILY / "plans", DAILY / "logs", DAILY / "briefs"


def ly(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def jload(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def jsave(p, data):
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------- 1. 전일 리포트 ----------
def yesterday_report(d: date, cfg):
    prev = d - timedelta(days=1)
    logs = jload(LOGS / f"{prev}.json", [])
    plan = jload(PLANS / f"{prev}.json", None)
    fin = sum(x["finished"] for x in logs)
    fail = sum(x["failed"] for x in logs)
    by_tool = {}
    for x in logs:
        t = by_tool.setdefault(x["tool"], {"ops": 0, "finished": 0, "failed": 0})
        for k in ("ops", "finished", "failed"):
            t[k] += x[k]
    target = cfg["target_finished_cuts"]
    return {"date": str(prev), "has_data": bool(logs), "finished": fin, "failed": fail,
            "pass_rate": round(fin / (fin + fail), 2) if fin + fail else None,
            "target": target, "achieved": fin >= target, "by_tool": by_tool,
            "planned": plan["totals"]["finished_planned"] if plan else None}


def measured_yield(cfg, days=7):
    """최근 7일 실적 통과율 — 데이터 없으면 기본 가정값."""
    fin = fail = 0
    for p in sorted(LOGS.glob("*.json"))[-days:]:
        for x in jload(p, []):
            fin += x["finished"]
            fail += x["failed"]
    return (round(fin / (fin + fail), 2), "실적") if fin + fail >= 20 else (cfg["qa_yield_default"], "초기 가정")


# ---------- 2. 툴별 오늘 크레딧 예산 ----------
def tool_budgets(cfg, ladder, today: date):
    out = []
    for t in sorted(ladder["tools"], key=lambda t: t["order"]):
        if not t["enabled"]:
            continue
        a = cfg["capacity_assumptions"].get(t["name"], {})
        c = t.get("credit", {})
        remaining = c.get("remaining")
        src = "실측" if remaining is not None else "추정"
        per_period = c.get("per_period", a.get("per_period"))   # 새로 추가한 툴은 tool_ladder 값 사용
        if remaining is None:
            remaining = per_period
        days_left = c.get("days_until_reset") or c.get("period_days") or a.get("period_days") or 30
        cap = c.get("daily_cap", a.get("daily_cap"))
        if remaining is None:
            budget = 0
        else:
            budget = math.floor(remaining / max(1, days_left))      # 초기화일까지 균등 배분
            if budget == 0 and remaining > 0:                       # 하루 1회도 안 되는 소량 크레딧
                every = math.ceil(days_left / remaining)            # → N일에 1회씩 배정
                budget = 1 if today.toordinal() % every == 0 else 0
            if cap:
                budget = min(budget, cap)
        cost = {**a.get("cost", {}), **(c.get("cost") or {})}
        out.append({"tool": t["name"], "order": t["order"], "capabilities": t["capabilities"],
                    "credits_today": budget, "cost": cost, "source": src,
                    "note": a.get("note", ""), "remaining": remaining, "days_left": days_left})
    return out


# ---------- 3. 오늘 설계 ----------
def make_plan(d: date, cfg, ladder):
    budgets = tool_budgets(cfg, ladder, d)
    yld, yld_src = measured_yield(cfg)
    target = cfg["target_finished_cuts"]
    alloc, probes = [], []
    base_total = 0
    for b in budgets:
        credits = b["credits_today"]
        kinds = []                                    # 이 툴이 할 수 있는 AI 컷 유형 (비중 큰 순)
        for kind, ct in cfg["cut_types"].items():
            ops = ct.get("ops") or {}
            if not ops:
                continue
            op = next(iter(ops))
            if op in b["capabilities"]:
                kinds.append((kind, op, ct.get("share", 0)))
        kinds.sort(key=lambda k: -k[2])
        counts = {}
        for kind, op, share in kinds:
            unit = b["cost"].get(op)
            if unit is None:                          # 소모량 모름 → 시험 사용(실측), 툴·작업당 1회만
                if not any(x["tool"] == b["tool"] and x["op"] == op for x in probes):
                    n = cfg["probe_ops_when_cost_unknown"]
                    probes.append({"tool": b["tool"], "op": op, "count": n})
                    alloc.append({"tool": b["tool"], "kind": kind, "base_cuts": n, "credits": "실측"})
                    base_total += n
                continue
            n = min(math.floor(b["credits_today"] * share) // max(1, unit), credits // max(1, unit))
            counts[kind] = [n, unit]
            credits -= n * unit
        for kind, op, share in kinds:                 # 남은 크레딧 → 비중 큰 유형부터 추가 배정
            if kind in counts and credits >= counts[kind][1]:
                extra = credits // counts[kind][1]
                counts[kind][0] += extra
                credits -= extra * counts[kind][1]
        for kind, (n, unit) in counts.items():
            if n > 0:
                alloc.append({"tool": b["tool"], "kind": kind, "base_cuts": n, "credits": n * unit})
                base_total += n
    local = cfg["local_composite_daily_max"]
    passed_base = math.floor(base_total * yld)
    passed_local = math.floor(local * yld)
    direct = passed_base + passed_local
    max_derived_by_ratio = math.floor(target * cfg["max_derived_ratio"])
    derived = min(passed_base * cfg["derived_per_base"] + passed_local * 2,
                  max_derived_by_ratio, max(0, target - direct))
    finished = direct + derived
    shortfall = max(0, target - finished)
    return {"date": str(d), "status": "승인 대기", "created": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "yield": yld, "yield_source": yld_src, "budgets": budgets, "alloc": alloc, "probes": probes,
            "totals": {"base_ai": base_total, "local_composite": local, "passed_direct": direct,
                       "derived": derived, "finished_planned": finished, "target": target,
                       "shortfall": shortfall}}


def options_for_shortfall(plan, cfg):
    s = plan["totals"]["shortfall"]
    if not s:
        return []
    need_base = math.ceil(s / (cfg["derived_per_base"] + 1) / plan["yield"])
    return [
        "① 무료 디자인 AI 툴 추가 (사장님 계획) — `python3 horu-lookbook/relay/relay.py add-tool ...` 한 줄로 등록, 다음 브리프부터 자동 배치",
        f"② 실사 자산 합성 상한 확대 (현재 {cfg['local_composite_daily_max']}컷/일) — 크레딧 0, Product 폴더 자산 수 확인 필요",
        f"③ 유료 플랜 1개 추가 — 원본 약 {need_base}컷/일 추가 확보 시 부족분 해소 (추정)",
        "④ 사장님 PC에서 로컬 이미지 생성(무료·무제한, GPU 필요) 툴 추가",
        f"⑤ 파생컷 비중 상한 상향 (현재 {int(cfg['max_derived_ratio']*100)}%) — 컷 수는 늘지만 다양성 저하",
    ]


def write_brief(plan, rep, cfg):
    t = plan["totals"]
    L = [f"# HÖRU 일일 작업 브리프 — {plan['date']}", "",
         f"**승인 요청:** 오늘 완성컷 계획 **{t['finished_planned']}컷** (목표 {t['target']}컷"
         + (f", 부족 {t['shortfall']}컷 — 권장 목표라 승인·진행 가능" if t["shortfall"] and cfg.get("target_mode") == "soft"
            else f", **부족 {t['shortfall']}컷**" if t["shortfall"] else ", 달성 가능") + ")", "",
         "## 1. 전일 결과 리포트", ""]
    if rep["has_data"]:
        L += [f"| 항목 | 값 |", "|---|---|",
              f"| 날짜 | {rep['date']} |", f"| 완성컷 | {rep['finished']} / 목표 {rep['target']} ({'달성' if rep['achieved'] else '미달'}) |",
              f"| 계획 대비 | {str(rep['planned']) + '컷 계획' if rep['planned'] is not None else '계획 기록 없음'} |",
              f"| 실패컷 | {rep['failed']} |", f"| QA 통과율 | {rep['pass_rate']} |", "",
              "| 툴 | AI 작업 수 | 완성 | 실패 |", "|---|---|---|---|"]
        L += [f"| {k} | {v['ops']} | {v['finished']} | {v['failed']} |" for k, v in rep["by_tool"].items()]
    else:
        L += [f"- {rep['date']} 실적 기록 없음 (첫날이거나 record 미입력)"]
    L += ["", "## 2. 오늘 툴별 크레딧 예산 (초기화일까지 균등 배분)", "",
          "| 순서 | 툴 | 오늘 사용 가능 | 남은 크레딧 | 초기화까지 | 근거 |", "|---|---|---|---|---|---|"]
    for b in plan["budgets"]:
        L.append(f"| {b['order']} | {b['tool']} | {b['credits_today']} | {b['remaining']} | {b['days_left']}일 | {b['source']} — {b['note']} |")
    L += ["", "## 3. 작업 배치", "", "| 툴 | 컷 유형 | 원본컷 | 크레딧 |", "|---|---|---|---|"]
    for a in plan["alloc"]:
        L.append(f"| {a['tool']} | {cfg['cut_types'][a['kind']]['label']} | {a['base_cuts']} | {a['credits']} |")
    L.append(f"| 로컬 | {cfg['cut_types']['local_composite']['label']} | {t['local_composite']} | 0 |")
    L += ["", "## 4. 완성컷 산식", "",
          f"- 원본 AI {t['base_ai']} + 로컬 합성 {t['local_composite']} → QA 통과율 {plan['yield']}({plan['yield_source']}) 적용 → 직접 완성 **{t['passed_direct']}**",
          f"- 통과 원본 기반 파생(컬러·포맷) **{t['derived']}** (완성컷의 최대 {int(cfg['max_derived_ratio']*100)}%)",
          f"- 합계 **{t['finished_planned']}컷** / 목표 {t['target']}컷"]
    if plan["probes"]:
        L += ["", "## 5. 실측 필요", ""] + [f"- {p['tool']} {p['op']} {p['count']}회 시험 사용 → 1장당 크레딧 소모량 기록" for p in plan["probes"]]
    opts = options_for_shortfall(plan, cfg)
    if opts:
        L += ["", "## 6. 작업량 확대 선택지 (참고)", ""] + [f"- {o}" for o in opts]
    L += ["", "---", "승인: `python3 horu-lookbook/daily/planner.py approve --date " + plan["date"] + "` (또는 채팅으로 \"승인\")"]
    BRIEFS.mkdir(parents=True, exist_ok=True)
    out = BRIEFS / f"{plan['date']}.md"
    out.write_text("\n".join(L), encoding="utf-8")
    return out


# ---------- 명령 ----------
def cmd_brief(a):
    d = date.fromisoformat(a.date) if a.date else date.today()
    cfg, ladder = ly(CFG), ly(LADDER)
    plan = make_plan(d, cfg, ladder)
    rep = yesterday_report(d, cfg)
    jsave(PLANS / f"{d}.json", plan)
    out = write_brief(plan, rep, cfg)
    t = plan["totals"]
    print(f"[브리프] {out} — 계획 {t['finished_planned']}컷 / 목표 {t['target']} (부족 {t['shortfall']}) · 승인 대기")


def cmd_approve(a):
    p = PLANS / f"{a.date}.json"
    plan = jload(p, None)
    if not plan:
        sys.exit(f"[오류] {a.date} 설계가 없습니다. 먼저 brief를 실행하세요.")
    plan["status"], plan["approved_at"], plan["approval_note"] = "승인", datetime.now().strftime("%Y-%m-%d %H:%M"), a.note
    jsave(p, plan)
    print(f"[승인] {a.date} 작업 설계 승인 → 작업 시작 가능")


def cmd_record(a):
    p = LOGS / f"{a.date}.json"
    logs = jload(p, [])
    logs.append({"tool": a.tool, "kind": a.kind, "ops": a.ops, "finished": a.finished, "failed": a.failed,
                 "time": datetime.now().strftime("%H:%M")})
    jsave(p, logs)
    print(f"[기록] {a.date} {a.tool}: AI {a.ops}회 → 완성 {a.finished} / 실패 {a.failed}")


def cmd_status(a):
    d = a.date or str(date.today())
    plan = jload(PLANS / f"{d}.json", None)
    logs = jload(LOGS / f"{d}.json", [])
    fin = sum(x["finished"] for x in logs)
    print(f"{d}: 설계 {'없음' if not plan else plan['status']} | 진행 {fin}/{plan['totals']['target'] if plan else '-'}컷")


def approved_today() -> bool:
    """relay.py에서 호출 — 오늘 설계가 승인됐는지."""
    plan = jload(PLANS / f"{date.today()}.json", None)
    return bool(plan and plan.get("status") == "승인")


def main():
    ap = argparse.ArgumentParser(description="HÖRU 일일 작업 설계기")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("brief"); p.add_argument("--date")
    p = sp.add_parser("approve"); p.add_argument("--date", required=True); p.add_argument("--note", default="")
    p = sp.add_parser("record"); p.add_argument("--date", required=True); p.add_argument("--tool", required=True)
    p.add_argument("--ops", type=int, required=True); p.add_argument("--finished", type=int, required=True)
    p.add_argument("--failed", type=int, required=True); p.add_argument("--kind", default="mixed")
    p = sp.add_parser("status"); p.add_argument("--date")
    a = ap.parse_args()
    {"brief": cmd_brief, "approve": cmd_approve, "record": cmd_record, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
