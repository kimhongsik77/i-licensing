# HÖRU Kaggle 생성 노트북 (스크립트 커널) — Kaggle 무료 GPU(T4/P100 16GB)에서 실행
# 입력: /kaggle/input/<dataset>/jobs.json + 모델 기준 시트(refs/*.png)
# 출력: /kaggle/working/out/<shot_id>.png + run_log.json
# 라이선스: FLUX.2 klein 4B(Apache 2.0)만 사용. klein 9B 계열은 비상업 → 코드에서 차단.
import subprocess, sys, json, time, glob, os
subprocess.run([sys.executable, "-m", "pip", "install", "-q", "diffusers==0.43.0", "transformers", "accelerate", "sentencepiece"], check=True)
import torch
from PIL import Image
from diffusers import Flux2KleinPipeline, ZImagePipeline

ALLOWED = {"black-forest-labs/FLUX.2-klein-4B", "Tongyi-MAI/Z-Image-Turbo"}
inp = glob.glob("/kaggle/input/*/jobs.json")
if not inp:
    sys.exit("jobs.json 없음 — 데이터셋 연결 확인")
base = os.path.dirname(inp[0])
cfg = json.load(open(inp[0]))
model_id = cfg.get("model", "black-forest-labs/FLUX.2-klein-4B")
if model_id not in ALLOWED:
    sys.exit(f"허용되지 않은 모델(라이선스): {model_id}")
dtype = torch.bfloat16 if torch.cuda.is_bf16_supported() else torch.float16   # T4/P100은 bf16 미지원 → fp16
os.makedirs("/kaggle/working/out", exist_ok=True)
log = {"model": model_id, "dtype": str(dtype), "gpu": torch.cuda.get_device_name(0), "items": []}
t0 = time.time()
if "klein" in model_id:
    pipe = Flux2KleinPipeline.from_pretrained(model_id, torch_dtype=dtype)
else:
    pipe = ZImagePipeline.from_pretrained(model_id, torch_dtype=dtype)
pipe.enable_model_cpu_offload()                     # 16GB 안에서 텍스트 인코더+트랜스포머 교대 적재
log["load_sec"] = round(time.time() - t0, 1)
for job in cfg["jobs"]:
    t = time.time()
    try:
        kw = dict(prompt=job["prompt"], height=job.get("height", 1536), width=job.get("width", 1152),
                  num_inference_steps=job.get("steps", 4 if "klein" in model_id else 8),
                  guidance_scale=job.get("guidance", 1.0 if "klein" in model_id else 0.0),
                  generator=torch.Generator("cuda").manual_seed(job.get("seed", 7)))
        refs = [Image.open(os.path.join(base, r)).convert("RGB") for r in job.get("refs", [])]
        if refs and "klein" in model_id:
            kw["image"] = refs                          # 기준 시트 → 얼굴·체형 유지
        img = pipe(**kw).images[0]
        img.save(f"/kaggle/working/out/{job['shot_id']}.png")
        log["items"].append({"shot_id": job["shot_id"], "ok": True, "sec": round(time.time() - t, 1), "size": img.size})
    except Exception as e:
        log["items"].append({"shot_id": job["shot_id"], "ok": False, "error": repr(e)[:400]})
log["total_sec"] = round(time.time() - t0, 1)
json.dump(log, open("/kaggle/working/run_log.json", "w"), ensure_ascii=False, indent=2)
print(json.dumps(log, ensure_ascii=False))
