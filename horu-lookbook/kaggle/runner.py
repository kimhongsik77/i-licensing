#!/usr/bin/env python3
"""HÖRU ↔ Kaggle 실행기 — 대기열의 모델 컷을 Kaggle 무료 GPU로 생성하고 결과를 받아 로고 합성·검수까지 잇는다.

사전 조건: api.kaggle.com 토큰(환경 Network secrets, Bearer). 로컬 CLI는 더미 토큰으로 시작하고 프록시가 실제 토큰을 넣는다.
명령:
  whoami                         # 토큰·계정 확인
  prepare --n 2 [--model klein]  # 준비완료 모델 컷 N개 → jobs.json + 기준 시트 → kaggle/build/
  push                           # 데이터셋 업로드 + 커널 실행
  status                         # 실행 상태
  fetch                          # 결과 다운로드 → production/<날짜>/ , 이후 placement_matcher·qa_check 진행
"""
import argparse, json, os, shutil, subprocess, sys
from datetime import date
from pathlib import Path
import yaml

ROOT = Path(__file__).resolve().parent.parent
BUILD = ROOT / "kaggle" / "build"
KERNEL = ROOT / "kaggle" / "kernel"
MODELS = {"klein": "black-forest-labs/FLUX.2-klein-4B", "zimage": "Tongyi-MAI/Z-Image-Turbo"}
os.environ.setdefault("KAGGLE_API_TOKEN", "proxy-injected")   # 실제 값은 프록시가 주입


def kg(*args, check=True):
    r = subprocess.run(["kaggle", *args], capture_output=True, text=True)
    if check and r.returncode:
        sys.exit(f"[오류] kaggle {' '.join(args)}\n{r.stdout}\n{r.stderr}")
    return r.stdout


def username():
    out = kg("config", "view", check=False)
    for line in out.splitlines():
        if "username" in line and ":" in line:
            v = line.split(":", 1)[1].strip()
            if v and v.lower() != "none":
                return v
    sys.exit("[오류] Kaggle 사용자명을 확인할 수 없습니다 — 토큰 등록 여부 확인")


def prepare(n, model):
    sys.path.insert(0, str(ROOT / "scripts"))
    import model_prompts as MP
    reg = MP.load()
    q = yaml.safe_load((ROOT / "daily" / "work_queue.yaml").read_text(encoding="utf-8"))["shots"]
    pick = [s for s in q if s["상태"] == "준비완료" and s["모델"]][:n]
    if not pick:
        sys.exit("[중단] 준비완료 모델 컷 없음")
    shutil.rmtree(BUILD, ignore_errors=True); (BUILD / "refs").mkdir(parents=True)
    jobs = []
    for s in pick:
        m = reg["models"][s["모델"]]
        shutil.copy(ROOT / m["sheet"], BUILD / "refs" / f"{s['모델']}.png")
        outfit = {"bottom": "plain charcoal high-rise leggings and a plain ivory fitted top", "top": "plain ivory crew-neck top and plain beige wide trousers"}.get(s["매칭기유형"], "plain neutral outfit")
        pos, neg = MP.prompt(reg, s["모델"], "front", outfit + ", plain white sneakers")
        jobs.append({"shot_id": s["shot_id"], "prompt": "The same person as in the reference image. " + pos + ". Avoid: " + neg,
                     "refs": [f"refs/{s['모델']}.png"], "height": 1536, "width": 1152, "seed": 7})
    user = username()
    (BUILD / "jobs.json").write_text(json.dumps({"model": MODELS[model], "jobs": jobs}, ensure_ascii=False, indent=2), encoding="utf-8")
    (BUILD / "dataset-metadata.json").write_text(json.dumps({"title": "horu-jobs", "id": f"{user}/horu-jobs", "licenses": [{"name": "other"}]}), encoding="utf-8")
    meta = {"id": f"{user}/horu-gen", "title": "horu-gen", "code_file": "generate.py", "language": "python", "kernel_type": "script",
            "is_private": True, "enable_gpu": True, "enable_internet": True, "dataset_sources": [f"{user}/horu-jobs"]}
    (KERNEL / "kernel-metadata.json").write_text(json.dumps(meta, indent=2), encoding="utf-8")
    print(f"[준비] {len(jobs)}컷 → {BUILD} (모델 {MODELS[model]})")


def push():
    user = username()
    exists = kg("datasets", "status", f"{user}/horu-jobs", check=False)
    if "ready" in exists.lower():
        kg("datasets", "version", "-p", str(BUILD), "-m", "update", "-r", "zip")
    else:
        kg("datasets", "create", "-p", str(BUILD), "-r", "zip")
    print(kg("kernels", "push", "-p", str(KERNEL)))


def status():
    print(kg("kernels", "status", f"{username()}/horu-gen"))


def fetch():
    out = ROOT / "production" / date.today().isoformat() / "kaggle"
    out.mkdir(parents=True, exist_ok=True)
    kg("kernels", "output", f"{username()}/horu-gen", "-p", str(out))
    log = out / "run_log.json"
    print(log.read_text(encoding="utf-8") if log.exists() else "[경고] run_log.json 없음")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(); sp = ap.add_subparsers(dest="cmd", required=True)
    sp.add_parser("whoami"); p = sp.add_parser("prepare"); p.add_argument("--n", type=int, default=2)
    p.add_argument("--model", choices=list(MODELS), default="klein")
    sp.add_parser("push"); sp.add_parser("status"); sp.add_parser("fetch")
    a = ap.parse_args()
    {"whoami": lambda: print(username()), "prepare": lambda: prepare(a.n, a.model), "push": push,
     "status": status, "fetch": fetch}[a.cmd]()
