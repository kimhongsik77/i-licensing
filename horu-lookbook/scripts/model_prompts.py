#!/usr/bin/env python3
"""모델 등록부 → 이미지 생성 프롬프트 (기준 시트·착장 컷). 어느 툴로 넘어가도 같은 문장을 쓰도록 고정.

예)
  python3 horu-lookbook/scripts/model_prompts.py sheet --id VM-F-EA01            # 정면·측면·후면 기준 시트 3개
  python3 horu-lookbook/scripts/model_prompts.py look --id VM-M-NE01 --outfit "navy half-zip windbreaker, beige chinos" \
      --pose "walking on a forest trail" --view front
  python3 horu-lookbook/scripts/model_prompts.py list [--priority P1]
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

REG = Path(__file__).resolve().parent.parent / "config" / "model_registry.yaml"


def load():
    try:
        return yaml.safe_load(REG.read_text(encoding="utf-8"))
    except (OSError, yaml.YAMLError) as e:
        sys.exit(f"[오류] 모델 등록부를 읽을 수 없습니다: {e}")


def prompt(reg, mid, view, outfit=None, pose=None):
    m = reg["models"].get(mid)
    if not m:
        sys.exit(f"[오류] 등록되지 않은 모델: {mid}")
    t = reg["prompt_template"]
    return t["base"].format(age=m["age"], ethnicity_en=m["ethnicity_en"], gender_en="woman" if m["gender"] == "female" else "man",
                            height_cm=m["height_cm"], build=m["build"], hair=m["hair"], face=m["face"], skin=m["skin"],
                            pose=pose or "standing straight, arms relaxed", view=view,
                            outfit=outfit or t["default_outfit"]), t["negative"]


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest="cmd", required=True)
    p = sp.add_parser("sheet"); p.add_argument("--id", required=True)
    p = sp.add_parser("look"); p.add_argument("--id", required=True); p.add_argument("--outfit", required=True)
    p.add_argument("--pose"); p.add_argument("--view", default="front")
    p = sp.add_parser("list"); p.add_argument("--priority")
    a = ap.parse_args()
    reg = load()
    if a.cmd == "list":
        for mid, m in reg["models"].items():
            if a.priority and m["priority"] != a.priority:
                continue
            print(f"{mid}\t{m['priority']}\t{m['ethnicity']}\t{m['gender']}\t{m['age']}세\t{m['height_cm']}cm/{m['weight_kg']}kg\t{m['status']}")
        return
    views = reg["prompt_template"]["views"] if a.cmd == "sheet" else [a.view]
    for v in views:
        pos, neg = prompt(reg, a.id, v, getattr(a, "outfit", None), getattr(a, "pose", None))
        print(f"--- {a.id} / {v} ---\nPROMPT: {pos}\nNEGATIVE: {neg}\n")


if __name__ == "__main__":
    main()
