#!/usr/bin/env python3
"""HÖRU 그래픽 툴 이어달리기(Relay) 장부

쉬운 설명:
  - 실제 그림은 각 툴(Canva/Adobe/Figma…)에서 만든다.
  - 이 스크립트는 '지금 누가 뛸 차례인지(툴 선택)'와 '바통(작업 카드·인계 패키지)'만 관리하는 장부다.

명령:
  new   --task "애슬레저 LINE A 착용컷 4장" --need image_gen --prompt "..." [--ref 파일 ...]
  next  --job J001                      # 이 작업을 맡을 툴 추천
  credit-out --job J001 --tool Canva [--note "생성 3/4장 완료"]   # 크레딧 소진 → 다음 툴로 바통
  progress --job J001 --note "2/4장 완료" [--output 파일]          # 중간 결과 기록
  done  --job J001 --qa pass|fail      # 완료 + 품질검사 결과 기록 (단계 상향 판단에 사용)
  refill --tool Canva --remaining 50   # 크레딧 충전/초기화 반영 (다음 달 등)
  status [--job J001]                  # 현황 보기
"""
from __future__ import annotations

import argparse
import json
import sys
from datetime import datetime
from pathlib import Path

try:
    import yaml
except ImportError:
    sys.exit("[오류] pyyaml이 필요합니다: pip install pyyaml")

BASE = Path(__file__).parent
LADDER = BASE / "tool_ladder.yaml"
JOBS = BASE / "jobs"
HANDOFF = BASE / "handoff"
STATS = BASE / "stats.json"
LEVEL_TEXT = {0: "매번 승인 후 전환", 1: "자동 전환 후 알림", 2: "완전 자동"}


def now():
    return datetime.now().strftime("%Y-%m-%d %H:%M")


def load_yaml(p):
    return yaml.safe_load(p.read_text(encoding="utf-8"))


def save_yaml(p, data):
    p.write_text(yaml.safe_dump(data, allow_unicode=True, sort_keys=False), encoding="utf-8")


def load_job(jid):
    p = JOBS / f"{jid}.json"
    if not p.exists():
        sys.exit(f"[오류] 작업 카드 {jid} 없음")
    return json.loads(p.read_text(encoding="utf-8"))


def save_job(job):
    JOBS.mkdir(exist_ok=True)
    (JOBS / f"{job['id']}.json").write_text(json.dumps(job, ensure_ascii=False, indent=2), encoding="utf-8")


def stats():
    return json.loads(STATS.read_text(encoding="utf-8")) if STATS.exists() else {"clean_switches": 0, "qa_pass_streak": 0}


def save_stats(s):
    STATS.write_text(json.dumps(s, ensure_ascii=False, indent=2), encoding="utf-8")


def pick_tool(ladder, need, exclude):
    """역할(need)을 할 수 있고, 꺼져있지 않고, 크레딧이 0이 아닌 툴 중 순서가 가장 앞선 것."""
    cands = sorted((t for t in ladder["tools"]
                    if t["enabled"] and need in t["capabilities"] and t["name"] not in exclude
                    and t["credit"]["remaining"] != 0), key=lambda t: t["order"])
    return cands[0] if cands else None


def approval_gate():
    """매일 09:00 작업 설계 승인 전에는 새 작업을 만들 수 없다 (daily/planner.py)."""
    sys.path.insert(0, str(BASE.parent / "daily"))
    try:
        from planner import approved_today
    except ImportError:
        return
    if not approved_today():
        sys.exit("[잠김] 오늘 작업 설계가 아직 승인되지 않았습니다. 브리프 승인 후 작업을 시작하세요.")


def cmd_new(a):
    approval_gate()
    JOBS.mkdir(exist_ok=True)
    jid = f"J{len(list(JOBS.glob('J*.json'))) + 1:03d}"
    job = {"id": jid, "task": a.task, "need": a.need, "prompt": a.prompt, "refs": a.ref or [],
           "style_card": "style_card.yaml", "current_tool": None, "status": "대기",
           "progress": [], "outputs": [], "tool_history": [], "created": now()}
    save_job(job)
    print(f"[작업 카드 생성] {jid}: {a.task}")
    a.job = jid
    cmd_next(a)


def cmd_next(a):
    ladder, job = load_yaml(LADDER), load_job(a.job)
    used_out = [h["tool"] for h in job["tool_history"] if h["event"] == "credit_out"]
    tool = pick_tool(ladder, job["need"], used_out)
    if not tool:
        job["status"] = "정지 — 가능한 툴 없음"
        save_job(job)
        print("[정지] 크레딧이 남은 툴이 없습니다. 크레딧 초기화일을 기다리거나 툴 추가가 필요합니다.")
        return
    job["current_tool"], job["status"] = tool["name"], "진행"
    job["tool_history"].append({"time": now(), "tool": tool["name"], "event": "assigned"})
    save_job(job)
    warn = " (남은 크레딧 미확인 — 작업 전 계정에서 확인)" if tool["credit"]["remaining"] is None else ""
    print(f"[배정] {job['id']} → {tool['order']}번 주자 {tool['name']}{warn}")


def write_handoff(job, from_tool, to_tool, note):
    HANDOFF.mkdir(exist_ok=True)
    p = HANDOFF / f"{job['id']}_{from_tool.split('/')[0]}_to_{to_tool.split('/')[0]}.md".replace(" ", "")
    done = "\n".join(f"- {x['time']} {x['note']}" for x in job["progress"]) or "- (기록 없음)"
    outs = "\n".join(f"- {o}" for o in job["outputs"]) or "- (없음)"
    p.write_text(f"""# 인계 패키지 (바통) — {job['id']}
- 작업: {job['task']}
- 이전 툴: {from_tool} (크레딧 소진) → 다음 툴: {to_tool}
- 스타일 기준: {job['style_card']} (반드시 먼저 적용)

## 지시문 (그대로 사용)
{job['prompt']}

## 레퍼런스
{chr(10).join('- ' + r for r in job['refs']) or '- (없음)'}

## 지금까지 완료된 것
{done}

## 중간 결과물 (이어서 작업할 기준)
{outs}

## 남은 일
{note or '(이전 툴 메모 없음 — 완료 목록 기준으로 나머지 진행)'}
""", encoding="utf-8")
    return p


def cmd_credit_out(a):
    ladder, job = load_yaml(LADDER), load_job(a.job)
    for t in ladder["tools"]:
        if t["name"] == a.tool:
            t["credit"]["remaining"] = 0
    save_yaml(LADDER, ladder)
    job["tool_history"].append({"time": now(), "tool": a.tool, "event": "credit_out"})
    if a.note:
        job["progress"].append({"time": now(), "note": f"[{a.tool}] {a.note}"})
    used_out = [h["tool"] for h in job["tool_history"] if h["event"] == "credit_out"]
    nxt = pick_tool(ladder, job["need"], used_out)
    if not nxt:
        job["status"] = "정지 — 가능한 툴 없음"
        save_job(job)
        print(f"[정지] {a.tool} 크레딧 소진, 넘겨받을 툴이 없습니다.")
        return
    hp = write_handoff(job, a.tool, nxt["name"], a.note)
    lv = ladder["level"]
    if lv == 0:
        job["status"] = f"승인 대기 — {nxt['name']}로 전환"
        print(f"[승인 필요] {a.tool} 크레딧 소진 → {nxt['name']}로 넘길까요? 인계 패키지: {hp}")
    else:
        job["current_tool"], job["status"] = nxt["name"], "진행"
        job["tool_history"].append({"time": now(), "tool": nxt["name"], "event": "assigned"})
        print(f"[알림] {a.tool} 크레딧 소진 → {nxt['name']}로 자동 전환해 이어서 작업합니다. 인계 패키지: {hp}")
    job["last_switch"] = True
    save_job(job)


def cmd_progress(a):
    job = load_job(a.job)
    job["progress"].append({"time": now(), "note": f"[{job['current_tool']}] {a.note}"})
    if a.output:
        job["outputs"].append(a.output)
    save_job(job)
    print(f"[기록] {job['id']}: {a.note}")


def cmd_done(a):
    ladder, job, s = load_yaml(LADDER), load_job(a.job), stats()
    job["status"], job["qa"] = "완료", a.qa
    switched = job.pop("last_switch", False)
    if a.qa == "pass":
        s["qa_pass_streak"] += 1
        if switched:
            s["clean_switches"] += 1
    else:
        s["qa_pass_streak"] = 0
        if switched and ladder["level"] > 0:
            print(f"[단계 하향 제안] 툴 전환 후 품질검사 실패 → Lv.{ladder['level']} → Lv.{ladder['level'] - 1} 권장")
    save_job(job)
    save_stats(s)
    r, lv = ladder["upgrade_rules"], ladder["level"]
    if lv == 0 and s["clean_switches"] >= r["to_level_1"]["clean_switches"]:
        print("[단계 상향 제안] 무사고 전환 5회 달성 → Lv.1(전환 후 알림)로 올릴까요?")
    if lv == 1 and s["qa_pass_streak"] >= r["to_level_2"]["qa_pass_streak"]:
        print("[단계 상향 제안] 품질검사 10연속 통과 → Lv.2(완전 자동)로 올릴까요?")
    print(f"[완료] {job['id']} QA={a.qa} | 무사고 전환 {s['clean_switches']}회, 연속 통과 {s['qa_pass_streak']}회")


def cmd_refill(a):
    ladder = load_yaml(LADDER)
    hit = [t for t in ladder["tools"] if t["name"] == a.tool]
    if not hit:
        sys.exit(f"[오류] 툴 '{a.tool}' 없음")
    hit[0]["credit"]["remaining"] = a.remaining
    save_yaml(LADDER, ladder)
    print(f"[충전] {a.tool} 남은 크레딧 = {a.remaining} → 다시 순서에 복귀")


def cmd_status(a):
    ladder = load_yaml(LADDER)
    print(f"현재 단계: Lv.{ladder['level']} ({LEVEL_TEXT[ladder['level']]}) | 설정 상태: {ladder['status']}")
    for t in sorted(ladder["tools"], key=lambda t: t["order"]):
        rem = t["credit"]["remaining"]
        rem = "미확인" if rem is None else rem
        print(f"  {t['order']}. {t['name']:<28} {'사용' if t['enabled'] else '꺼짐'}  남은 크레딧: {rem}")
    jobs = [load_job(a.job)] if a.job else [json.loads(p.read_text(encoding='utf-8')) for p in sorted(JOBS.glob("J*.json"))]
    for j in jobs:
        print(f"  [{j['id']}] {j['task']} — {j['status']} / 담당 {j['current_tool']}")


def main():
    ap = argparse.ArgumentParser(description="HÖRU 툴 이어달리기 장부")
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("new"); p.add_argument("--task", required=True); p.add_argument("--need", required=True)
    p.add_argument("--prompt", required=True); p.add_argument("--ref", nargs="*")
    p = sp.add_parser("next"); p.add_argument("--job", required=True)
    p = sp.add_parser("credit-out"); p.add_argument("--job", required=True); p.add_argument("--tool", required=True); p.add_argument("--note")
    p = sp.add_parser("progress"); p.add_argument("--job", required=True); p.add_argument("--note", required=True); p.add_argument("--output")
    p = sp.add_parser("done"); p.add_argument("--job", required=True); p.add_argument("--qa", choices=["pass", "fail"], required=True)
    p = sp.add_parser("refill"); p.add_argument("--tool", required=True); p.add_argument("--remaining", type=int, required=True)
    p = sp.add_parser("status"); p.add_argument("--job")
    a = ap.parse_args()
    {"new": cmd_new, "next": cmd_next, "credit-out": cmd_credit_out, "progress": cmd_progress,
     "done": cmd_done, "refill": cmd_refill, "status": cmd_status}[a.cmd](a)


if __name__ == "__main__":
    main()
