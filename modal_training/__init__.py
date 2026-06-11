"""SecureAI Modal-based deepfake-detection training pipeline.

This package contains a fully autonomous, script/job-based training pipeline
designed to run unattended on a Modal cloud GPU. It pulls datasets from the
user's AWS S3, extracts aligned face crops, trains a strongly-generalizing
deepfake detector, evaluates CROSS-DATASET (the metric that actually matters
for a product), refits the logistic-regression ensemble, and writes weights +
metrics back to S3.

Launch (one command):

    modal run modal_training/modal_app.py

The whole point of this package is CROSS-DATASET generalization
(train FF++ -> test Celeb-DF/DFDC), not in-domain accuracy. Identity-disjoint
splits and val-AUC model selection are mandatory here to avoid the leakage that
previously produced a fake "100%" model.
"""

__all__ = [
    "config",
    "face_extract",
    "sbi",
    "dataset",
    "train",
    "evaluate",
    "ensemble_refit",
    "data_acquire",
]

__version__ = "0.1.0"
