# Autonomous Training on Modal — Setup & Run Guide

This pipeline trains the deepfake detector **fully unattended** on a Modal cloud GPU. No notebooks. You run one command from your laptop; Modal provisions a GPU, runs the job, writes weights + metrics to your S3, and shuts the GPU down (billed per-second, no idle charge).

```
modal run modal_training/modal_app.py
```

---

## One-time setup (≈15 min)

### 1. Create a Modal account
Go to https://modal.com and sign up (GitHub/Google login). New accounts get **$30/month in free compute credits** — enough for the first few training runs. *(I can't create the account for you — this is the only manual account step.)*

### 2. Install the Modal CLI and authenticate
On your machine (in the repo folder):
```bash
pip install modal
modal setup          # opens a browser to link the CLI to your account
```

### 3. Give Modal your AWS credentials (as a Modal Secret)
The job reads/writes your existing S3 buckets, so Modal needs AWS keys. Store them as a Modal Secret named **`aws-creds`** (never hardcoded in code):
```bash
modal secret create aws-creds \
  AWS_ACCESS_KEY_ID=<your-rotated-key> \
  AWS_SECRET_ACCESS_KEY=<your-rotated-secret> \
  AWS_REGION=us-east-2
```
> Use the **rotated** keys from the security cleanup — and ideally a *least-privilege* IAM user that can only read `secureai-deepfake-videos` and write `secureai-deepfake-results`.

---

## Get the datasets into S3

Cross-dataset generalization needs more than Celeb-DF. The big public benchmarks are **access-gated** (you must request them — I can't and shouldn't bypass that). `data_acquire.py` prints the exact steps and verifies your S3 layout. Run it to see status:
```bash
python modal_training/data_acquire.py --check
```

Expected S3 layout (the pipeline reads this):
```
s3://secureai-deepfake-videos/datasets/
  faceforensics/   real/  fake/      # FF++ — TRAIN source
  celeb_df_v2/     real/  fake/      # cross-dataset TEST
  dfdc/            real/  fake/      # cross-dataset TEST
  diffusion/       real/  fake/      # modern synthetic-face coverage
```

Access requests (do these once; approval is usually 1–2 days):
- **FaceForensics++** — request form + download script: https://github.com/ondyari/FaceForensics
- **Celeb-DF v2** — request form: https://github.com/yuezunli/celeb-deepfakeforensics (you already have these frames; `data_acquire.py` can sync them up)
- **DFDC** — Kaggle competition data (accept rules): https://www.kaggle.com/c/deepfake-detection-challenge/data
- **Diffusion faces** — freely scriptable; `data_acquire.py` can fetch a starter set

Once data is in S3, `data_acquire.py --sync <local_dir> <dataset>` uploads anything you have locally into the right layout.

---

## Run it

Full pipeline (acquire-check → face extraction → train → cross-dataset eval → ensemble refit → upload):
```bash
modal run modal_training/modal_app.py
```

Useful variants:
```bash
# Bigger/faster backbone, fewer epochs
modal run modal_training/modal_app.py --backbone convnext_base --epochs 25

# Just one stage (debugging)
modal run modal_training/modal_app.py --stage extract
modal run modal_training/modal_app.py --stage train
```

You can close your laptop — the job keeps running on Modal. Watch progress live in the Modal dashboard (logs stream there), or in the terminal.

---

## What you get back

Written to `s3://secureai-deepfake-results/training_runs/<run-id>/`:
- `model_best.pth` — the trained backbone (best checkpoint by **validation AUC**)
- `cross_dataset_report.json` — AUC / Average Precision / EER / accuracy@FPR=0.10 for each test dataset (this is the honest, sellable benchmark)
- `ensemble_weights.json` — refit ensemble including the new backbone
- `train_metadata.json` — config, real per-epoch metrics, timestamps

Drop `model_best.pth` + `ensemble_weights.json` into `ai_model/trained_models/` and the live API picks them up (the production path now loads from there).

---

## Cost & reliability

- **GPU default:** one A100 (~$3–4/hr on Modal). A full FF++ extraction + 30-epoch EfficientNet-B4 run is typically a few GPU-hours → **low tens of dollars**, and the first run is covered partly by free credits.
- **Cheaper:** edit the `GPU` constant in `modal_app.py` to `"L4"` or `"A10G"` for small experiments (reduce batch/image size to fit).
- **Faster:** `"H100"` or `"A100-80GB"`.
- **Spot-safe:** training checkpoints every epoch to a Modal Volume and auto-resumes, so preemption/retries don't lose work.

---

## Why this beats Kaggle/Colab for you
No interactive notebook to babysit, no session timeouts mid-train, no re-uploading data each time. It's a real job: submit, walk away, collect weights from S3. The same code also runs on SkyPilot/RunPod/SageMaker later if you ever want to switch — only `modal_app.py` is Modal-specific.
