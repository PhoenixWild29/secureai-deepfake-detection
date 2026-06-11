"""Modal orchestrator for the SecureAI deepfake TRAINING pipeline.

ONE command launches everything, fully unattended on a Modal cloud GPU:

    modal run modal_training/modal_app.py

The job: pull datasets from the user's AWS S3, extract aligned face crops,
train a strongly-generalizing detector, evaluate CROSS-DATASET, refit the
ensemble, write weights + metrics back to S3, and exit. Modal bills per-second,
so the function returns as soon as the work is done (no idle box).

Why Modal (not Kaggle/Colab notebooks): this is script/job based. You submit a
job from your laptop, Modal provisions a GPU, runs the Python, and tears it
down. Nothing interactive.

GPU choice
----------
Default is a single A100 (40GB) — comfortably fits EfficientNet-B4 @ 380px with
batch 24 in mixed precision, and is the best price/throughput for this size.
To go faster (larger batch / bigger backbone) change ``GPU`` to "H100" or use
"A100-80GB". To save money on small experiments use "L4" or "A10G" (reduce
batch size / image size accordingly). See the GPU constant below.

Cost note (approximate, check current Modal pricing): A100 is roughly
$3-4/hr on Modal. A full FF++ extraction + 30-epoch B4 run is typically a few
GPU-hours, i.e. low tens of dollars. Spot/preemptible pricing is cheaper and is
safe here because train.py checkpoints every epoch and resumes automatically.

Storage
-------
The data bucket is mounted read-only at /data via CloudBucketMount, the results
bucket at /outputs. A modal.Volume holds face crops + checkpoints so a
preempted spot instance resumes instead of restarting extraction/training.

Heavy imports (torch/timm/etc.) live INSIDE the remote function so this file
imports with only `modal` available locally.
"""

from __future__ import annotations

import modal

# ---------------------------------------------------------------------------
# Image: debian + system libs + python deps for training.
# ---------------------------------------------------------------------------
image = (
    modal.Image.debian_slim(python_version="3.11")
    .apt_install("ffmpeg", "libgl1", "libglib2.0-0")  # opencv/video runtime libs
    .pip_install(
        "torch",
        "torchvision",
        "timm>=0.9.12",
        "facenet-pytorch",
        "opencv-python-headless",
        "albumentations>=1.4",
        "scikit-learn",
        "scikit-image",
        "boto3",
        "numpy<2.0",          # ABI safety for facenet/opencv wheels
        "pandas",
        "tqdm",
        "Pillow",
        # open_clip is needed so the evaluate stage can recompute the legacy
        # CLIP/ResNet50/ConvNeXt/FFT detector columns (via ai_model's
        # EnhancedDetector) for a genuine ensemble refit. Without it the legacy
        # detectors degrade gracefully (omitted -> neutral-filled), which is
        # safe but makes the refit a no-op for those columns.
        "open-clip-torch>=2.20.0",
    )
    # Ship the training package source into the image so it's importable.
    .add_local_python_source("modal_training")
    # Ship ai_model too: the evaluate stage imports ai_model.enhanced_detector
    # (and its trained_models/*) to recompute legacy per-detector scores.
    .add_local_python_source("ai_model")
)

app = modal.App("secureai-deepfake-training")

# --- Storage handles --------------------------------------------------------
# CloudBucketMount surfaces the S3 buckets as local paths inside the container.
# Credentials come from the Modal Secret named "aws-creds" (AWS_ACCESS_KEY_ID,
# AWS_SECRET_ACCESS_KEY, AWS_REGION) — never hardcoded here.
AWS_SECRET = modal.Secret.from_name("aws-creds")

data_mount = modal.CloudBucketMount(
    bucket_name="secureai-deepfake-videos",
    secret=AWS_SECRET,
    read_only=True,
)
outputs_mount = modal.CloudBucketMount(
    bucket_name="secureai-deepfake-results",
    secret=AWS_SECRET,
)

# Persistent volume for face crops + checkpoints (survives preemption/retries).
cache_volume = modal.Volume.from_name("secureai-train-cache", create_if_missing=True)

# --- GPU selection (see module docstring to change) -------------------------
GPU = "A100"          # alternatives: "H100", "A100-80GB", "L4", "A10G"
TIMEOUT_SECONDS = 24 * 3600


@app.function(
    image=image,
    gpu=GPU,
    timeout=TIMEOUT_SECONDS,
    secrets=[AWS_SECRET],
    volumes={
        "/data": data_mount,
        "/outputs": outputs_mount,
        "/cache": cache_volume,
    },
    retries=modal.Retries(max_retries=2),  # spot-preemption safe (we resume)
)
def run_training_pipeline(stage: str = "all", backbone: str = None,
                          epochs: int = None) -> dict:
    """Run the end-to-end training pipeline on the GPU worker.

    Stages (run in order for ``stage='all'``):
      1. acquire   — verify datasets present on S3 (print instructions if not)
      2. extract   — extract aligned face crops for train + test datasets
      3. train     — train the backbone, select best by VAL AUC
      4. evaluate  — cross-dataset AUC/AP/EER/acc@FPR report
      5. ensemble  — refit the logistic ensemble incl. the new backbone
      6. upload    — push weights + metrics json to s3://.../training_runs/<id>

    ``stage`` may be a single stage name to run just that step (useful for
    debugging), or "all".
    """
    import os
    import json
    import time
    import shutil

    # Heavy imports live here so the module imports locally without torch.
    from modal_training.config import default_config
    from modal_training import data_acquire, face_extract, train as train_mod
    from modal_training import evaluate as eval_mod, ensemble_refit

    # Build config (env overrides + explicit args win).
    overrides = {}
    if backbone:
        overrides["backbone"] = backbone
    if epochs:
        overrides["epochs"] = epochs
    config = default_config(**overrides)
    if not config.run_id:
        config.run_id = time.strftime("run_%Y%m%d_%H%M%S", time.gmtime())

    # On Modal the buckets are mounted; point the config at the mounts.
    config.data_root = "/data"
    config.outputs_root = "/outputs"
    config.work_dir = "/cache"
    os.makedirs(config.crops_dir, exist_ok=True)
    os.makedirs(config.checkpoint_dir, exist_ok=True)

    import torch
    print(f"[modal] run_id={config.run_id} stage={stage} "
          f"cuda={torch.cuda.is_available()} gpu={GPU}")
    device = "cuda" if torch.cuda.is_available() else "cpu"

    results: dict = {"run_id": config.run_id, "backbone": config.backbone}
    do = lambda s: stage in ("all", s)

    # --- 1. acquire ---------------------------------------------------------
    if do("acquire"):
        results["acquire"] = data_acquire.acquire(config)

    # --- 2. extract aligned face crops -------------------------------------
    if do("extract") or do("all"):
        all_ds = sorted(set(config.train_datasets) | set(config.test_datasets))
        extract_stats = {}
        for ds in all_ds:
            spec = config.spec(ds)
            # Source videos/frames are under the mounted data bucket.
            # Layout on S3: datasets/<name>/{real,fake}/...
            src_root = os.path.join(config.data_root, "datasets", ds)
            dst_root = os.path.join(config.crops_dir, ds)
            if not os.path.isdir(src_root):
                print(f"[modal] WARNING: {src_root} not found on mount; "
                      f"skipping extraction for '{ds}'. "
                      f"Did you upload it? (see data_acquire instructions)")
                continue
            print(f"[modal] extracting faces for '{ds}' ({spec.kind}) ...")
            stats = face_extract.extract_dataset(
                src_root, dst_root, kind=spec.kind,
                frames_per_video=config.frames_per_video,
                out_size=config.image_size, margin=config.face_margin,
                device=device,
            )
            extract_stats[ds] = stats
            print(f"[modal]   {ds}: {stats}")
            cache_volume.commit()  # persist crops before training
        results["extract"] = extract_stats

    # --- 3. train -----------------------------------------------------------
    train_summary = None
    if do("train") or do("all"):
        train_summary = train_mod.train(config)
        results["train"] = {k: v for k, v in train_summary.items()
                            if k != "history"}
        cache_volume.commit()

    # --- 4. cross-dataset evaluation ---------------------------------------
    eval_report = None
    if do("evaluate") or do("all"):
        ckpt = (train_summary["best_checkpoint"] if train_summary
                else train_mod._ckpt_paths(config)["best"])
        model = train_mod.load_trained_model(ckpt, config)
        report_path = os.path.join(config.checkpoint_dir,
                                   f"cross_dataset_{config.run_id}.json")
        eval_report = eval_mod.cross_dataset_report(
            model, config, config.test_datasets, report_path
        )
        results["evaluate"] = {
            "mean_cross_dataset_auc": eval_report.get("mean_cross_dataset_auc"),
            "per_dataset": eval_report.get("per_dataset"),
        }
        cache_volume.commit()

    # --- 5. ensemble refit --------------------------------------------------
    if do("ensemble") or do("all"):
        scores_path = (eval_report["_scores_path"] if eval_report
                       else os.path.join(config.checkpoint_dir,
                                         f"cross_dataset_{config.run_id}_scores.json"))
        out_weights = os.path.join(config.checkpoint_dir,
                                   f"ensemble_weights_{config.run_id}.json")
        if os.path.exists(scores_path):
            weights = ensemble_refit.refit_from_eval_scores(
                scores_path, out_weights, C=config.ensemble_C
            )
            results["ensemble"] = {
                "weights_path": out_weights,
                "test_auc": weights.get("test_auc_at_this_C"),
                "detectors": weights.get("detectors"),
            }
        else:
            print(f"[modal] no scores file at {scores_path}; skipping ensemble.")

    # --- 6. upload artifacts to results bucket -----------------------------
    if do("upload") or do("all"):
        out_dir = os.path.join(config.outputs_root, config.output_prefix,
                               config.run_id)
        os.makedirs(out_dir, exist_ok=True)
        artifacts = []
        for fn in os.listdir(config.checkpoint_dir):
            if config.run_id in fn or fn.endswith("_best.pth") or fn.endswith("_meta.json"):
                src = os.path.join(config.checkpoint_dir, fn)
                dst = os.path.join(out_dir, fn)
                try:
                    shutil.copy2(src, dst)
                    artifacts.append(fn)
                except Exception as exc:
                    print(f"[modal] could not copy {fn}: {exc}")
        # write the run summary too
        with open(os.path.join(out_dir, "run_summary.json"), "w") as f:
            json.dump(results, f, indent=2, default=str)
        results["uploaded_to"] = f"s3://{config.results_bucket}/{config.output_prefix}/{config.run_id}/"
        results["artifacts"] = artifacts
        print(f"[modal] uploaded {len(artifacts)} artifacts -> {results['uploaded_to']}")

    return results


@app.local_entrypoint()
def main(stage: str = "all", backbone: str = "tf_efficientnet_b4_ns",
         epochs: int = 0):
    """Local entrypoint — submits the GPU job and prints a summary.

    Examples
    --------
    modal run modal_training/modal_app.py
    modal run modal_training/modal_app.py --backbone convnext_base --epochs 25
    modal run modal_training/modal_app.py --stage extract     # just extraction
    """
    eps = epochs if epochs and epochs > 0 else None
    print(f"Submitting SecureAI training job: stage={stage} backbone={backbone} "
          f"epochs={epochs or 'config-default'} gpu={GPU}")
    summary = run_training_pipeline.remote(stage=stage, backbone=backbone, epochs=eps)

    print("\n================ RUN SUMMARY ================")
    print(f"run_id   : {summary.get('run_id')}")
    print(f"backbone : {summary.get('backbone')}")
    if "train" in summary:
        print(f"best val AUC : {summary['train'].get('best_val_auc')}")
    if "evaluate" in summary:
        print(f"cross-dataset mean AUC : {summary['evaluate'].get('mean_cross_dataset_auc')}")
        for ds, m in (summary["evaluate"].get("per_dataset") or {}).items():
            if isinstance(m, dict) and "auc" in m:
                print(f"   {ds:16s} AUC={m['auc']:.4f}  AP={m['ap']:.4f}  "
                      f"EER={m['eer']:.4f}  acc@FPR10={m['acc_at_fpr10']:.4f}")
    if "ensemble" in summary:
        print(f"ensemble test AUC : {summary['ensemble'].get('test_auc')}")
    if "uploaded_to" in summary:
        print(f"artifacts -> {summary['uploaded_to']}")
    print("=============================================")
